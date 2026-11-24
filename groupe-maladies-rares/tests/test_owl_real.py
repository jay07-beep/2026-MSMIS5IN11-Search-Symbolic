import shutil

import pytest

from conftest import ECTOPIA, EYE, FINGERS, SKIN
from rarediag.owl_reasoning import build_and_reason, contradictory_annotations, topological_order

pytestmark = pytest.mark.skipif(shutil.which("java") is None, reason="Java requis pour HermiT")


def test_ordre_topologique(toy):
    order = topological_order(toy, set(toy.onto.terms))
    pos = {t: i for i, t in enumerate(order)}
    for t in order:
        for p in toy.onto.parents[t]:
            assert pos[p] < pos[t]


def test_hermit_egal_fermetures(toy):
    r = build_and_reason(toy, toy.disease_ids, [EYE])
    assert r.compatible == r.expected_compatible == ["ORPHA:1", "ORPHA:2", "ORPHA:4"]
    r = build_and_reason(toy, toy.disease_ids, [EYE, FINGERS])
    assert r.compatible == ["ORPHA:1"]


def test_hermit_exclusion_not(toy):
    r = build_and_reason(toy, toy.disease_ids, [SKIN])
    assert r.excluded == ["ORPHA:3"]                # annotation NOT explicite
    assert r.compatible == ["ORPHA:2"]


def test_hermit_signe_absent(toy):
    r = build_and_reason(toy, toy.disease_ids, [EYE], absent=[ECTOPIA])
    assert r.compatible == ["ORPHA:2", "ORPHA:4"]


def test_aucune_contradiction_jouet(toy):
    assert contradictory_annotations(toy) == []


# ----- données réelles (ignorés si les données ne sont pas téléchargées) -----
MARFAN = ["HP:0001166", "HP:0001083", "HP:0002616", "HP:0000098"]   # arachnodactylie, ectopie, anévrisme racine aortique, grande taille


def test_marfan_premier(real):
    assert real.rank(MARFAN, "resnik_sym", top=1)[0][0] == "ORPHA:558"


def test_taille_des_donnees(real):
    assert len(real.disease_ids) > 4000 and len(real.onto) > 15000


def test_contradictions_detectees_par_hermit(real):
    contra = {d for d, _, _ in contradictory_annotations(real)}
    if not contra:
        pytest.skip("aucune contradiction dans cette version des annotations")
    did = sorted(contra)[0]
    r = build_and_reason(real, [did], [])
    assert r.unsatisfiable == [did]
