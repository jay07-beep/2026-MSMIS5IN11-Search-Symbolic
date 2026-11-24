"""Chargement de la Human Phenotype Ontology (format OBO) et navigation dans la hiérarchie.

On écrit un petit parseur OBO dédié plutôt que d'utiliser `pronto` dans le code principal :
il est ~10x plus rapide sur hp.obo et n'a aucune dépendance. Le vérificateur indépendant
(`verifier/verify.py`) utilise, lui, `pronto`, ce qui permet de recouper les deux lectures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PHENOTYPIC_ABNORMALITY = "HP:0000118"


@dataclass
class Term:
    id: str
    name: str = ""
    parents: list[str] = field(default_factory=list)
    alt_ids: list[str] = field(default_factory=list)
    obsolete: bool = False
    replaced_by: str | None = None
    definition: str = ""


def parse_obo(path: str | Path) -> dict[str, Term]:
    """Lit les stanzas [Term] d'un fichier OBO. Ne garde que id, name, is_a, alt_id, obsolescence."""
    terms: dict[str, Term] = {}
    current: Term | None = None
    in_term = False
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line.startswith("["):
                if current is not None:
                    terms[current.id] = current
                current = None
                in_term = line == "[Term]"
                continue
            if not in_term or not line or ":" not in line:
                continue
            key, _, value = line.partition(": ")
            if key == "id":
                current = Term(id=value)
            elif current is None:
                continue
            elif key == "name":
                current.name = value
            elif key == "is_a":
                current.parents.append(value.split(" ! ")[0].split()[0])
            elif key == "alt_id":
                current.alt_ids.append(value)
            elif key == "is_obsolete" and value == "true":
                current.obsolete = True
            elif key == "replaced_by":
                current.replaced_by = value
            elif key == "def":
                current.definition = value.split('"')[1] if '"' in value else value
    if current is not None:
        terms[current.id] = current
    return terms


class Ontology:
    """Hiérarchie is_a de HPO restreinte à un sous-arbre (par défaut « Phenotypic abnormality »)."""

    def __init__(self, terms: dict[str, Term], root: str = PHENOTYPIC_ABNORMALITY, version: str = ""):
        self.version = version
        self.root = root
        live = {tid: t for tid, t in terms.items() if not t.obsolete}
        # Table de correspondance identifiants secondaires / obsolètes -> identifiant courant
        self._alias: dict[str, str] = {}
        for t in live.values():
            for alt in t.alt_ids:
                self._alias[alt] = t.id
        for t in terms.values():
            if t.obsolete and t.replaced_by and t.replaced_by in live:
                self._alias[t.id] = t.replaced_by

        children: dict[str, list[str]] = {tid: [] for tid in live}
        for t in live.values():
            for p in t.parents:
                if p in children:
                    children[p].append(t.id)

        # Restriction au sous-arbre de `root` (parcours en largeur)
        keep = {root}
        stack = [root]
        while stack:
            for c in children[stack.pop()]:
                if c not in keep:
                    keep.add(c)
                    stack.append(c)
        self.terms = {tid: live[tid] for tid in keep}
        self.parents = {tid: [p for p in live[tid].parents if p in keep] for tid in keep}
        self.children = {tid: [c for c in children[tid] if c in keep] for tid in keep}
        self._anc: dict[str, frozenset[str]] = {}
        self._depth: dict[str, int] = {}

    @classmethod
    def from_obo(cls, path: str | Path, root: str = PHENOTYPIC_ABNORMALITY) -> "Ontology":
        version = ""
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("data-version:"):
                    version = line.split(":", 1)[1].strip()
                    break
                if line.startswith("[Term]"):
                    break
        return cls(parse_obo(path), root=root, version=version)

    # --- accès -------------------------------------------------------------------------
    def __contains__(self, tid: str) -> bool:
        return tid in self.terms

    def __len__(self) -> int:
        return len(self.terms)

    def resolve(self, tid: str) -> str | None:
        """Renvoie l'identifiant courant d'un terme (gère alt_id et replaced_by), ou None."""
        if tid in self.terms:
            return tid
        new = self._alias.get(tid)
        return new if new in self.terms else None

    def name(self, tid: str) -> str:
        return self.terms[tid].name if tid in self.terms else tid

    def ancestors(self, tid: str) -> frozenset[str]:
        """Ancêtres de `tid` dans le sous-arbre, `tid` inclus (fermeture réflexive-transitive de is_a)."""
        cached = self._anc.get(tid)
        if cached is not None:
            return cached
        result = {tid}
        for p in self.parents[tid]:
            result |= self.ancestors(p)
        frozen = frozenset(result)
        self._anc[tid] = frozen
        return frozen

    def descendants(self, tid: str) -> set[str]:
        result, stack = {tid}, [tid]
        while stack:
            for c in self.children[stack.pop()]:
                if c not in result:
                    result.add(c)
                    stack.append(c)
        return result

    def depth(self, tid: str) -> int:
        """Longueur du plus court chemin vers la racine."""
        if tid not in self._depth:
            self._depth[tid] = 0 if tid == self.root else 1 + min(self.depth(p) for p in self.parents[tid])
        return self._depth[tid]

    def is_descendant(self, tid: str, ancestor: str) -> bool:
        return ancestor in self.ancestors(tid)

    def search(self, text: str, limit: int = 10) -> list[tuple[str, str]]:
        """Recherche naïve d'un terme par sous-chaîne dans le libellé (pour l'interface)."""
        text = text.lower()
        hits = [(tid, t.name) for tid, t in self.terms.items() if text in t.name.lower()]
        hits.sort(key=lambda x: (not x[1].lower().startswith(text), len(x[1])))
        return hits[:limit]
