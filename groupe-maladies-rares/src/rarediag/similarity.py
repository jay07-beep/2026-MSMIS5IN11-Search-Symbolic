"""Similarité sémantique : information content (IC), mesure de Resnik, score patient/maladie.

Rappels (Resnik 1995 ; Köhler et al., AJHG 2009) :

* annotations propagées (« true path rule ») : une maladie annotée par t l'est aussi par tous
  les ancêtres de t ;
* p(t) = proportion des maladies annotées (après propagation) par t ; IC(t) = -log p(t) ;
* Resnik(t1, t2) = IC(MICA(t1, t2)), MICA = ancêtre commun d'IC maximal ;
* score(Q -> D) = moyenne, sur les signes q du patient, de max_{t in D} Resnik(q, t)
  (« best-match average », mesure asymétrique utilisée par le Phenomizer) ;
* score symétrique = moyenne de score(Q -> D) et score(D -> Q).

Optimisation clé : max_{t in D} Resnik(q, t) = max { IC(a) : a ancêtre de q ET a dans la
fermeture des annotations de D }. On évite donc toute comparaison paire à paire.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np

from .annotations import Disease
from .ontology import Ontology


class SemanticIndex:
    def __init__(self, ontology: Ontology, diseases: dict[str, Disease]):
        self.onto = ontology
        self.diseases = diseases
        self.disease_ids: list[str] = sorted(diseases)
        self.index_of = {d: i for i, d in enumerate(self.disease_ids)}
        n = len(self.disease_ids)

        # Fermeture (annotations propagées) de chaque maladie
        self.closure: list[frozenset[str]] = []
        counts: dict[str, int] = {}
        for did in self.disease_ids:
            clo: set[str] = set()
            for t in diseases[did].phenotypes:
                clo |= ontology.ancestors(t)
            fz = frozenset(clo)
            self.closure.append(fz)
            for t in fz:
                counts[t] = counts.get(t, 0) + 1
        self.counts = counts

        # IC. Convention : un terme jamais annoté reçoit l'IC maximal possible (comme s'il
        # n'annotait qu'une seule maladie) : il est au moins aussi spécifique que ses descendants
        # annotés, ce qui préserve la monotonie IC(enfant) >= IC(parent).
        max_ic = math.log(n)
        self.ic: dict[str, float] = {
            t: (-math.log(counts[t] / n) if counts.get(t) else max_ic) for t in ontology.terms
        }
        self.max_ic = max_ic

        # Index inversé : ancêtre -> indices des maladies dont la fermeture le contient
        self.inverted: dict[str, np.ndarray] = {}
        tmp: dict[str, list[int]] = {}
        for i, clo in enumerate(self.closure):
            for t in clo:
                tmp.setdefault(t, []).append(i)
        self.inverted = {t: np.asarray(v, dtype=np.int32) for t, v in tmp.items()}

        # Structure plate (maladie, terme direct) pour la direction D -> Q
        self.annotated_terms: list[str] = sorted({t for d in diseases.values() for t in d.phenotypes})
        term_pos = {t: j for j, t in enumerate(self.annotated_terms)}
        pairs_d, pairs_t = [], []
        for i, did in enumerate(self.disease_ids):
            for t in diseases[did].phenotypes:
                pairs_d.append(i)
                pairs_t.append(term_pos[t])
        self._pair_d = np.asarray(pairs_d, dtype=np.int32)
        self._pair_t = np.asarray(pairs_t, dtype=np.int32)
        self._n_terms = np.bincount(self._pair_d, minlength=n).astype(float)

        self._anc_sorted: dict[str, tuple[str, ...]] = {}

    # ----------------------------------------------------------------------------------
    # Briques élémentaires
    # ----------------------------------------------------------------------------------
    def ancestors_by_ic(self, t: str) -> tuple[str, ...]:
        """Ancêtres de t (t inclus) triés par IC décroissant, puis par identifiant (déterminisme)."""
        res = self._anc_sorted.get(t)
        if res is None:
            res = tuple(sorted(self.onto.ancestors(t), key=lambda a: (-self.ic[a], a)))
            self._anc_sorted[t] = res
        return res

    def mica(self, t1: str, t2: str) -> str:
        """Ancêtre commun le plus informatif (most informative common ancestor)."""
        anc2 = self.onto.ancestors(t2)
        for a in self.ancestors_by_ic(t1):
            if a in anc2:
                return a
        return self.onto.root

    def resnik(self, t1: str, t2: str) -> float:
        return self.ic[self.mica(t1, t2)]

    def best_in_closure(self, t: str, closure: frozenset[str] | set[str]) -> str:
        """Ancêtre de t d'IC maximal présent dans une fermeture donnée."""
        for a in self.ancestors_by_ic(t):
            if a in closure:
                return a
        return self.onto.root

    def query_closure(self, query: Iterable[str]) -> set[str]:
        clo: set[str] = set()
        for q in query:
            clo |= self.onto.ancestors(q)
        return clo

    # ----------------------------------------------------------------------------------
    # Scores pour toutes les maladies d'un coup (vectorisé)
    # ----------------------------------------------------------------------------------
    def scores_query_to_disease(self, query: list[str]) -> np.ndarray:
        """score(Q -> D) pour toutes les maladies D."""
        n = len(self.disease_ids)
        total = np.zeros(n)
        for q in query:
            best = np.zeros(n)
            # Ancêtres par IC croissant : les plus informatifs écrasent les moins informatifs
            for a in reversed(self.ancestors_by_ic(q)):
                idx = self.inverted.get(a)
                if idx is not None:
                    best[idx] = self.ic[a]
            total += best
        return total / max(len(query), 1)

    def scores_disease_to_query(self, query: list[str]) -> np.ndarray:
        """score(D -> Q) : pour chaque phénotype de la maladie, meilleur match dans le profil patient."""
        qclo = self.query_closure(query)
        m = np.array([self.ic[self.best_in_closure(t, qclo)] for t in self.annotated_terms])
        sums = np.bincount(self._pair_d, weights=m[self._pair_t], minlength=len(self.disease_ids))
        return sums / self._n_terms

    def scores(self, query: list[str], method: str = "resnik") -> np.ndarray:
        """method : 'resnik' (asymétrique Q->D, Köhler 2009) ou 'resnik_sym' (symétrique)."""
        query = self.clean_query(query)
        if not query:
            return np.zeros(len(self.disease_ids))
        a = self.scores_query_to_disease(query)
        if method == "resnik":
            return a
        if method == "resnik_sym":
            return 0.5 * (a + self.scores_disease_to_query(query))
        raise ValueError(f"méthode inconnue : {method}")

    def absent_penalty(self, absent: list[str]) -> np.ndarray:
        """Pénalité (extension « signes absents »).

        Pour chaque signe x déclaré absent chez le patient, une maladie qui possède x (ou un
        descendant de x) avec la fréquence f est pénalisée de f * IC(x) : plus le signe est
        fréquent dans la maladie et spécifique, plus son absence est un argument contre elle.
        """
        n = len(self.disease_ids)
        pen = np.zeros(n)
        absent = self.clean_query(absent)
        for x in absent:
            for i in self.inverted.get(x, ()):   # seules les maladies dont la fermeture contient x
                did = self.disease_ids[i]
                f = max(fr for t, fr in self.diseases[did].phenotypes.items()
                        if x in self.onto.ancestors(t))
                pen[i] += f * self.ic[x]
        return pen / max(len(absent), 1)

    def clean_query(self, query: Iterable[str]) -> list[str]:
        """Résout les identifiants, retire les inconnus et les doublons (ordre conservé)."""
        out: list[str] = []
        for q in query:
            r = self.onto.resolve(q)
            if r is not None and r not in out:
                out.append(r)
        return out

    def rank(self, query: list[str], method: str = "resnik", absent: list[str] | None = None,
             absent_weight: float = 1.0, top: int | None = None) -> list[tuple[str, float]]:
        s = self.scores(query, method)
        if absent:
            s = s - absent_weight * self.absent_penalty(absent)
        order = np.lexsort((np.arange(len(s)), -s))   # score décroissant, puis ordre stable
        if top is not None:
            order = order[:top]
        return [(self.disease_ids[i], float(s[i])) for i in order]

    # ----------------------------------------------------------------------------------
    # Version « une seule maladie », non vectorisée (utilisée par l'explication)
    # ----------------------------------------------------------------------------------
    def score_one(self, query: list[str], did: str, method: str = "resnik") -> float:
        query = self.clean_query(query)
        clo = self.closure[self.index_of[did]]
        a = sum(self.ic[self.best_in_closure(q, clo)] for q in query) / len(query)
        if method == "resnik":
            return a
        qclo = self.query_closure(query)
        terms = self.diseases[did].phenotypes
        b = sum(self.ic[self.best_in_closure(t, qclo)] for t in terms) / len(terms)
        return 0.5 * (a + b)
