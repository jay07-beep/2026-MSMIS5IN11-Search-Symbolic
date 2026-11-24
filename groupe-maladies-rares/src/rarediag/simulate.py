"""Patients simulés, selon le protocole de Köhler et al. (AJHG 2009).

À partir d'une maladie connue, on tire quelques-uns de ses phénotypes (pondérés par leur
fréquence), puis on dégrade le profil :

* imprécision : un signe est remplacé par un de ses ancêtres (le clinicien note un terme
  plus général, p. ex. « anomalie du cristallin » au lieu de « ectopie du cristallin ») ;
* bruit : on ajoute des signes tirés au hasard, sans rapport avec la maladie.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .similarity import SemanticIndex


@dataclass
class SimulatedPatient:
    disease_id: str
    terms: list[str]
    absent: list[str] = field(default_factory=list)
    origin: dict[str, str] = field(default_factory=dict)   # terme -> "vrai" | "imprecis" | "bruit"


@dataclass
class Scenario:
    name: str
    n_terms: int = 5
    imprecision: float = 0.0    # probabilité de remplacer chaque signe par un ancêtre
    imprecision_steps: int = 1  # nombre de niveaux remontés
    noise: int = 0              # nombre de signes aléatoires ajoutés
    n_absent: int = 0           # nombre de signes absents (extension)
    absent_mode: str = "differential"  # "differential" : signes des diagnostics concurrents ; "random"


class PatientSimulator:
    def __init__(self, index: SemanticIndex, seed: int = 0, min_terms: int = 3):
        self.index = index
        self.rng = random.Random(seed)
        self.eligible = [d for d in index.disease_ids if len(index.diseases[d].phenotypes) >= min_terms]
        self.noise_pool = list(index.annotated_terms)

    def _weighted_sample(self, items: list[str], weights: list[float], k: int) -> list[str]:
        """Tirage sans remise proportionnel aux poids (méthode d'Efraimidis-Spirakis)."""
        keys = [(self.rng.random() ** (1.0 / max(w, 1e-6)), it) for it, w in zip(items, weights)]
        keys.sort(reverse=True)
        return [it for _, it in keys[:k]]

    def _generalize(self, t: str, steps: int) -> str:
        onto = self.index.onto
        for _ in range(steps):
            parents = [p for p in onto.parents[t] if p != onto.root]
            if not parents:
                break
            t = self.rng.choice(sorted(parents))
        return t

    def patient(self, disease_id: str, sc: Scenario) -> SimulatedPatient:
        d = self.index.diseases[disease_id]
        items = sorted(d.phenotypes)
        chosen = self._weighted_sample(items, [d.phenotypes[t] for t in items], min(sc.n_terms, len(items)))
        terms, origin = [], {}
        for t in chosen:
            if self.rng.random() < sc.imprecision:
                g = self._generalize(t, sc.imprecision_steps)
                kind = "imprecis" if g != t else "vrai"
                t = g
            else:
                kind = "vrai"
            if t not in terms:
                terms.append(t)
                origin[t] = kind
        closure = self.index.closure[self.index.index_of[disease_id]]
        added = 0
        while added < sc.noise:
            t = self.rng.choice(self.noise_pool)
            if t not in closure and t not in terms:   # vrai bruit : sans rapport avec la maladie
                terms.append(t)
                origin[t] = "bruit"
                added += 1
        absent = self._absent_signs(disease_id, terms, sc) if sc.n_absent else []
        return SimulatedPatient(disease_id, terms, absent, origin)

    def _absent_signs(self, disease_id: str, terms: list[str], sc: Scenario) -> list[str]:
        """Signes que le clinicien a vérifiés et trouvés absents.

        Mode « differential » (réaliste) : le clinicien vérifie les signes des diagnostics
        concurrents ; on tire donc parmi les phénotypes des 10 maladies les mieux classées
        (hors bonne maladie), pondérés par leur fréquence. Mode « random » : signes au hasard.
        Dans les deux cas, un signe absent ne doit ni annoter la vraie maladie ni être un
        ancêtre d'une de ses annotations.
        """
        d = self.index.diseases[disease_id]
        onto = self.index.onto

        def compatible(t: str) -> bool:
            return not any(t in onto.ancestors(p) for p in d.phenotypes) and t not in terms

        if sc.absent_mode == "differential":
            ranking = self.index.rank(terms, top=11)
            pool: dict[str, float] = {}
            for did, _ in ranking:
                if did == disease_id:
                    continue
                for t, f in self.index.diseases[did].phenotypes.items():
                    if compatible(t):
                        pool[t] = max(f, pool.get(t, 0.0))
            items = sorted(pool)
            return self._weighted_sample(items, [pool[t] for t in items], min(sc.n_absent, len(items)))
        absent: list[str] = []
        while len(absent) < sc.n_absent:
            t = self.rng.choice(self.noise_pool)
            if compatible(t) and t not in absent:
                absent.append(t)
        return absent

    def cohort(self, sc: Scenario, n: int) -> list[SimulatedPatient]:
        diseases = self.rng.sample(self.eligible, min(n, len(self.eligible)))
        return [self.patient(d, sc) for d in diseases]
