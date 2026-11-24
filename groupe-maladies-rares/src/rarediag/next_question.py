"""Extension : quelle est la question suivante la plus discriminante ?

On transforme les scores des K premiers candidats en distribution de probabilité
p(d) ∝ exp(score(d) / T). Pour un signe x non encore renseigné :

    P(x présent | d) = fréquence de x (ou d'un de ses descendants) dans d, sinon epsilon

Le gain d'information attendu est l'entropie actuelle moins l'entropie moyenne après la
réponse (présent / absent). On propose le signe de gain maximal : c'est celui qui sépare le
mieux les hypothèses restantes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .similarity import SemanticIndex

EPSILON = 0.01   # probabilité d'observer un signe non annoté (annotations incomplètes)


def entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


@dataclass
class Question:
    term: str
    name: str
    gain: float          # en bits
    p_yes: float


def candidate_distribution(scores: np.ndarray, temperature: float) -> np.ndarray:
    z = (scores - scores.max()) / temperature
    w = np.exp(z)
    return w / w.sum()


def presence_probability(index: SemanticIndex, did: str, x: str) -> float:
    d = index.diseases[did]
    if x in d.excluded:
        return 0.0
    if x not in index.closure[index.index_of[did]]:
        return EPSILON
    return max((f for t, f in d.phenotypes.items() if x in index.onto.ancestors(t)), default=EPSILON)


def best_questions(index: SemanticIndex, query: list[str], absent: list[str] | None = None,
                   k: int = 20, temperature: float = 0.3, n: int = 5,
                   method: str = "resnik") -> list[Question]:
    absent = absent or []
    ranking = index.rank(query, method=method, absent=absent, top=k)
    dids = [d for d, _ in ranking]
    p = candidate_distribution(np.array([s for _, s in ranking]), temperature)
    h0 = entropy(p)

    known = index.query_closure(query) | set(index.clean_query(absent))
    candidates = sorted({t for d in dids for t in index.diseases[d].phenotypes} - known)
    out = []
    for x in candidates:
        lik = np.array([presence_probability(index, d, x) for d in dids])
        p_yes = float((p * lik).sum())
        if p_yes <= 0 or p_yes >= 1:
            continue
        post_yes = p * lik / p_yes
        post_no = p * (1 - lik) / (1 - p_yes)
        gain = h0 - (p_yes * entropy(post_yes) + (1 - p_yes) * entropy(post_no))
        out.append(Question(x, index.onto.name(x), gain, p_yes))
    out.sort(key=lambda q: (-q.gain, q.term))
    return out[:n]
