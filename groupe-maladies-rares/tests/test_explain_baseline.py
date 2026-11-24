import numpy as np
import pytest

from conftest import ECTOPIA, EYE, FINGERS, LENS, MYOPIA, SKIN, TALL
from rarediag.baseline import Baselines, tokenize
from rarediag.evaluate import tie_aware_rank
from rarediag.explain import explain, explain_text


def test_types_d_appariement(toy):
    m = {x.patient_term: x for x in explain(toy, [ECTOPIA, EYE, SKIN, TALL], "ORPHA:4")}
    assert m[ECTOPIA].kind == "plus_general"      # Ectopia (patient) plus précis que Lens (maladie)
    assert m[EYE].kind == "plus_specifique"       # la maladie précise « œil » en « cristallin »
    assert m[SKIN].kind == "aucun"
    m1 = {x.patient_term: x for x in explain(toy, [ECTOPIA, MYOPIA], "ORPHA:1")}
    assert m1[ECTOPIA].kind == "exact" and m1[ECTOPIA].frequency == 0.9
    assert m1[MYOPIA].kind == "apparente" and m1[MYOPIA].mica == EYE


def test_contributions_somment_au_score(toy):
    q = [ECTOPIA, MYOPIA, FINGERS]
    for did in toy.disease_ids:
        total = sum(m.contribution for m in explain(toy, q, did))
        assert total == pytest.approx(toy.score_one(q, did))
    assert "Marfan-like" in explain_text(toy, q, "ORPHA:1")


def test_baselines(toy):
    b = Baselines(toy)
    assert tokenize("Abnormality of the lens") == {"lens"}
    i = toy.index_of
    assert b.exact([ECTOPIA])[i["ORPHA:1"]] == pytest.approx(1 / 3)
    assert b.exact([ECTOPIA])[i["ORPHA:4"]] == 0                 # aucun terme exact commun
    assert b.keywords([LENS])[i["ORPHA:4"]] == 1.0
    assert b.graph_jaccard([LENS])[i["ORPHA:4"]] == 1.0


def test_rang_avec_ex_aequo():
    s = np.array([3.0, 2.0, 2.0, 2.0, 1.0])
    assert tie_aware_rank(s, 0) == 1
    assert tie_aware_rank(s, 2) == 3          # 1 meilleur + (3 ex æquo -> rang moyen 2..4)
    assert tie_aware_rank(s, 4) == 5
