"""Extension : raisonnement OWL (owlready2 + HermiT) sur un sous-domaine de maladies.

On traduit un sous-domaine (plan B du sujet : quelques centaines de maladies) en ontologie OWL :

* chaque terme HPO utilisé devient une classe, avec ses axiomes `SubClassOf` (hiérarchie is_a) ;
* chaque maladie devient une classe, sous-classe de `Disease`, avec un axiome
  `Maladie SubClassOf hasPhenotype some T` par phénotype annoté ;
* une annotation « NOT » devient `Maladie SubClassOf not (hasPhenotype some T)`.

Un patient devient une classe définie (équivalence) :

    Compatible ≡ Disease and (hasPhenotype some Q1) and ... and (hasPhenotype some Qn)

Le raisonneur classe alors automatiquement sous `Compatible` toutes les maladies qui présentent
chaque signe Qi ou un de ses sous-types : c'est l'inférence par la hiérarchie, faite par un
raisonneur de logique de description et non par notre code. On vérifie que le résultat coïncide
avec le calcul par fermetures de `SemanticIndex` et on montre les limites du tout-ou-rien logique :
un seul signe bruité suffit à exclure la bonne maladie, d'où l'intérêt d'une similarité graduée.

Le monde ouvert d'OWL empêche par ailleurs de conclure qu'une maladie n'a pas un signe
simplement parce qu'il n'est pas annoté : seules les annotations NOT explicites permettent
d'exclure une maladie (classe `Excluded` ci-dessous).

Bonus : le raisonneur détecte les maladies dont les annotations sont contradictoires (un signe
annoté présent alors qu'un de ses ancêtres est annoté NOT) : ce sont des classes insatisfiables.
`contradictory_annotations` fait le même contrôle sans raisonneur, sur toute la base.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .similarity import SemanticIndex


def _cls_name(tid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", tid)


@dataclass
class OwlResult:
    compatible: list[str]          # maladies classées sous Compatible par le raisonneur
    unsatisfiable: list[str]       # maladies aux annotations contradictoires (classes insatisfiables)
    excluded: list[str]            # maladies incohérentes avec le profil (NOT explicite)
    expected_compatible: list[str]  # même calcul par fermetures (contrôle)
    reasoning_time_s: float
    n_classes: int
    n_axioms: int


def topological_order(index: SemanticIndex, terms: set[str]) -> list[str]:
    """Ordre dans lequel chaque terme apparaît après tous ses parents (`terms` clos par ancêtres)."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(t: str) -> None:
        if t in seen:
            return
        seen.add(t)
        for p in index.onto.parents[t]:
            visit(p)
        order.append(t)

    for t in sorted(terms):
        visit(t)
    return order


def subdomain(index: SemanticIndex, root: str, max_diseases: int | None = None) -> list[str]:
    """Maladies dont la fermeture contient `root` (p. ex. HP:0003549, tissu conjonctif)."""
    ids = [d for i, d in enumerate(index.disease_ids) if root in index.closure[i]]
    return ids[:max_diseases] if max_diseases else ids


def build_and_reason(index: SemanticIndex, disease_ids: list[str], query: list[str],
                     absent: list[str] | None = None, save_path: str | None = None) -> OwlResult:
    import owlready2 as owl

    absent = index.clean_query(absent or [])
    query = index.clean_query(query)
    world = owl.World()
    onto = world.get_ontology("http://example.org/rarediag.owl")

    terms: set[str] = set(query) | set(absent)
    for d in disease_ids:
        terms |= set(index.diseases[d].phenotypes) | index.diseases[d].excluded
    closure: set[str] = set()
    for t in terms:
        closure |= index.onto.ancestors(t)

    n_axioms = 0
    with onto:
        class Phenotype(owl.Thing):
            pass

        class Disease(owl.Thing):
            pass

        class hasPhenotype(owl.ObjectProperty):
            domain = [Disease]
            range = [Phenotype]

        owl.AllDisjoint([Phenotype, Disease])
        cls: dict[str, type] = {}
        # Création des classes dans un ordre topologique (tous les parents avant l'enfant).
        # Attention : trier par profondeur minimale ne suffit pas en multi-héritage.
        for t in topological_order(index, closure):
            parents = [cls[p] for p in index.onto.parents[t]] or [Phenotype]
            c = owl.types.new_class(_cls_name(t), tuple(parents))
            c.label = [index.onto.name(t)]
            cls[t] = c
            n_axioms += len(parents)

        dcls: dict[str, type] = {}
        for d in disease_ids:
            c = owl.types.new_class(_cls_name(d), (Disease,))
            c.label = [index.diseases[d].name]
            for t in index.diseases[d].phenotypes:
                c.is_a.append(hasPhenotype.some(cls[t]))
            for t in index.diseases[d].excluded:
                c.is_a.append(owl.Not(hasPhenotype.some(cls[t])))
            n_axioms += 1 + len(index.diseases[d].phenotypes) + len(index.diseases[d].excluded)
            dcls[d] = c

        class Compatible(owl.Thing):
            pass
        Compatible.equivalent_to.append(
            owl.And([Disease] + [hasPhenotype.some(cls[q]) for q in query]))

        # Maladies exclues : elles interdisent explicitement un signe observé chez le patient
        class Excluded(owl.Thing):
            pass
        if query:
            Excluded.equivalent_to.append(
                owl.And([Disease, owl.Or([hasPhenotype.only(owl.Not(cls[q])) for q in query])]))
        # Signes déclarés absents chez le patient : une maladie qui les a obligatoirement (axiome
        # hasPhenotype some X) est reconnue par la classe AbsentSignPresent
        class AbsentSignPresent(owl.Thing):
            pass
        if absent:
            AbsentSignPresent.equivalent_to.append(
                owl.And([Disease, owl.Or([hasPhenotype.some(cls[x]) for x in absent])]))
        n_axioms += 3

    t0 = time.time()
    owl.sync_reasoner_hermit(world, infer_property_values=False, debug=0)
    elapsed = time.time() - t0

    inv = {v: k for k, v in dcls.items()}
    # Une classe insatisfiable (équivalente à owl:Nothing) est sous-classe de tout : on l'isole.
    unsat = sorted(inv[c] for c in world.inconsistent_classes() if c in inv)
    compatible = sorted(inv[c] for c in Compatible.descendants() if c in inv and inv[c] not in unsat)
    excluded = sorted(inv[c] for c in Excluded.descendants() if c in inv and inv[c] not in unsat)
    absent_hit = sorted(inv[c] for c in AbsentSignPresent.descendants() if c in inv) if absent else []
    compatible = [d for d in compatible if d not in absent_hit]

    expected = [d for d in disease_ids if d not in unsat
                and all(q in index.closure[index.index_of[d]] for q in query)
                and not any(x in index.closure[index.index_of[d]] for x in absent)]
    if save_path:
        onto.save(file=save_path, format="rdfxml")
    return OwlResult(compatible, unsat, excluded, sorted(expected), elapsed, len(cls) + len(dcls), n_axioms)


def contradictory_annotations(index: SemanticIndex) -> list[tuple[str, str, str]]:
    """(maladie, terme NOT, terme positif descendant) : contradictions logiques dans les annotations."""
    out = []
    for i, d in enumerate(index.disease_ids):
        dis = index.diseases[d]
        for x in sorted(dis.excluded):
            if x in index.closure[i]:
                for t in sorted(dis.phenotypes):
                    if x in index.onto.ancestors(t):
                        out.append((d, x, t))
    return out
