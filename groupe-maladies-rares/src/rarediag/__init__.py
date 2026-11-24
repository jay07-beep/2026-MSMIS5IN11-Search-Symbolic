"""rarediag — diagnostic différentiel des maladies rares par similarité sémantique sur HPO."""
from __future__ import annotations

import os
from pathlib import Path

from .annotations import Disease, annotations_version, load_annotations
from .ontology import Ontology
from .similarity import SemanticIndex

__all__ = ["Ontology", "Disease", "SemanticIndex", "load_annotations", "load_index", "DATA_DIR"]
__version__ = "1.0.0"

DATA_DIR = Path(os.environ.get("RAREDIAG_DATA", Path(__file__).resolve().parents[2] / "data"))


def load_index(data_dir: str | Path | None = None, prefix: str = "ORPHA:") -> SemanticIndex:
    """Charge hp.obo + phenotype.hpoa et construit l'index sémantique (≈ 5 s)."""
    data_dir = Path(data_dir or DATA_DIR)
    obo, hpoa = data_dir / "hp.obo", data_dir / "phenotype.hpoa"
    if not obo.exists() or not hpoa.exists():
        raise FileNotFoundError(
            f"Données absentes dans {data_dir}. Lancez d'abord : python scripts/download_data.py"
        )
    onto = Ontology.from_obo(obo)
    diseases = load_annotations(hpoa, onto, prefix=prefix)
    index = SemanticIndex(onto, diseases)
    index.annotations_version = annotations_version(hpoa)
    return index
