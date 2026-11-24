"""Méthodes de référence (baselines) auxquelles on compare la similarité sémantique.

* `keywords`    : recouvrement de mots-clés entre libellés (Jaccard sur les mots) ;
* `exact`       : recouvrement des identifiants HPO exacts (Jaccard), sans hiérarchie ;
* `graph_jaccard` : Jaccard sur les fermetures (utilise la hiérarchie mais pas l'IC). Sert à
  isoler l'apport de l'information content par rapport à la seule hiérarchie.
"""
from __future__ import annotations

import re

import numpy as np

from .similarity import SemanticIndex

STOPWORDS = {
    "abnormality", "abnormal", "of", "the", "and", "in", "to", "a", "an", "with", "or",
    "morphology", "physiology", "increased", "decreased",
}


def tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 2}


class Baselines:
    def __init__(self, index: SemanticIndex):
        self.index = index
        onto = index.onto
        self.disease_words = [
            set().union(*(tokenize(onto.name(t)) for t in index.diseases[d].phenotypes))
            for d in index.disease_ids
        ]
        self.disease_terms = [set(index.diseases[d].phenotypes) for d in index.disease_ids]

    def keywords(self, query: list[str]) -> np.ndarray:
        q = set().union(*(tokenize(self.index.onto.name(t)) for t in query)) if query else set()
        return np.array([len(q & w) / len(q | w) if (q | w) else 0.0 for w in self.disease_words])

    def exact(self, query: list[str]) -> np.ndarray:
        q = set(query)
        return np.array([len(q & t) / len(q | t) for t in self.disease_terms])

    def graph_jaccard(self, query: list[str]) -> np.ndarray:
        q = self.index.query_closure(query)
        return np.array([len(q & c) / len(q | c) for c in self.index.closure])
