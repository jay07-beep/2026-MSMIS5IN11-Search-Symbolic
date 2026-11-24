"""Lecture des annotations maladie -> phénotype (fichier `phenotype.hpoa` de la distribution HPO)."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .ontology import Ontology

# Codes de fréquence HPO -> fréquence moyenne de la classe (voir HP:0040279 « Frequency »)
FREQUENCY_CODES = {
    "HP:0040280": 1.00,   # Obligate (100 %)
    "HP:0040281": 0.90,   # Very frequent (80-99 %)
    "HP:0040282": 0.55,   # Frequent (30-79 %)
    "HP:0040283": 0.17,   # Occasional (5-29 %)
    "HP:0040284": 0.025,  # Very rare (1-4 %)
    "HP:0040285": 0.00,   # Excluded (0 %)
}
DEFAULT_FREQUENCY = 0.5   # quand la fréquence n'est pas renseignée


def parse_frequency(value: str) -> float:
    """Convertit le champ `frequency` (code HPO, « n/m » ou « x% ») en probabilité."""
    value = (value or "").strip()
    if not value:
        return DEFAULT_FREQUENCY
    if value in FREQUENCY_CODES:
        return FREQUENCY_CODES[value]
    try:
        if value.endswith("%"):
            return float(value[:-1]) / 100.0
        if "/" in value:
            n, m = value.split("/")
            return int(n) / int(m) if int(m) else DEFAULT_FREQUENCY
    except ValueError:
        pass
    return DEFAULT_FREQUENCY


@dataclass
class Disease:
    id: str
    name: str
    phenotypes: dict[str, float] = field(default_factory=dict)   # terme -> fréquence
    excluded: set[str] = field(default_factory=set)               # annotations qualifier = NOT


def load_annotations(path: str | Path, ontology: Ontology, prefix: str = "ORPHA:") -> dict[str, Disease]:
    """Charge les maladies dont l'identifiant commence par `prefix`, aspect P uniquement.

    Les identifiants HPO secondaires/obsolètes sont résolus vers l'identifiant courant ;
    les termes hors du sous-arbre « Phenotypic abnormality » sont ignorés.
    """
    diseases: dict[str, Disease] = {}
    with open(path, encoding="utf-8") as fh:
        rows = (line for line in fh if not line.startswith("#"))
        reader = csv.DictReader(rows, delimiter="\t")
        for row in reader:
            did = row["database_id"]
            if not did.startswith(prefix) or row["aspect"] != "P":
                continue
            tid = ontology.resolve(row["hpo_id"])
            if tid is None:
                continue
            d = diseases.setdefault(did, Disease(did, row["disease_name"]))
            freq = parse_frequency(row["frequency"])
            if row["qualifier"] == "NOT" or freq == 0.0:
                d.excluded.add(tid)
            else:
                # Si un terme est annoté plusieurs fois, on garde la fréquence la plus élevée
                d.phenotypes[tid] = max(freq, d.phenotypes.get(tid, 0.0))
    # Une maladie sans aucun phénotype positif est inutilisable pour le classement
    return {k: v for k, v in diseases.items() if v.phenotypes}


def annotations_version(path: str | Path) -> str:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#version:"):
                return line.split(":", 1)[1].strip()
            if not line.startswith("#"):
                break
    return ""
