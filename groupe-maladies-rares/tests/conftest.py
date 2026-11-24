import math
from pathlib import Path

import pytest

from rarediag.annotations import load_annotations
from rarediag.ontology import Ontology
from rarediag.similarity import SemanticIndex

FIX = Path(__file__).parent / "fixtures"
DATA = Path(__file__).resolve().parents[1] / "data"

# Identifiants de la mini-ontologie
ROOT, EYE, LENS, ECTOPIA, MYOPIA = "HP:0000118", "HP:9000010", "HP:9000011", "HP:9000012", "HP:9000013"
SKEL, FINGERS, TALL, GROWTH, SKIN = "HP:9000020", "HP:9000021", "HP:9000022", "HP:9000030", "HP:9000040"
LN = math.log


@pytest.fixture(scope="session")
def toy_onto():
    return Ontology.from_obo(FIX / "toy.obo")


@pytest.fixture(scope="session")
def toy_diseases(toy_onto):
    return load_annotations(FIX / "toy.hpoa", toy_onto)


@pytest.fixture(scope="session")
def toy(toy_onto, toy_diseases):
    return SemanticIndex(toy_onto, toy_diseases)


@pytest.fixture(scope="session")
def real():
    if not (DATA / "hp.obo").exists() or not (DATA / "phenotype.hpoa").exists():
        pytest.skip("données HPO absentes (python scripts/download_data.py)")
    from rarediag import load_index
    return load_index(DATA)
