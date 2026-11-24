from conftest import ECTOPIA, EYE, FINGERS, LENS
from rarediag.next_question import best_questions, entropy, presence_probability
from rarediag.simulate import PatientSimulator, Scenario

import numpy as np
import pytest


def test_simulation_deterministe(toy):
    sc = Scenario("t", n_terms=2, imprecision=0.5, noise=1)
    a = PatientSimulator(toy, seed=1).cohort(sc, 3)
    b = PatientSimulator(toy, seed=1).cohort(sc, 3)
    assert [(p.disease_id, p.terms) for p in a] == [(p.disease_id, p.terms) for p in b]


def test_simulation_sans_bruit_ni_imprecision(toy):
    sim = PatientSimulator(toy, seed=0, min_terms=1)
    p = sim.patient("ORPHA:1", Scenario("t", n_terms=3))
    assert set(p.terms) == set(toy.diseases["ORPHA:1"].phenotypes)


def test_bruit_hors_maladie_et_imprecision_vers_ancetre(toy):
    sim = PatientSimulator(toy, seed=3, min_terms=1)
    clo = toy.closure[toy.index_of["ORPHA:1"]]
    for _ in range(20):
        p = sim.patient("ORPHA:1", Scenario("t", n_terms=3, imprecision=1.0, noise=1))
        for t, kind in p.origin.items():
            if kind == "bruit":
                assert t not in clo
            else:
                assert t in clo                     # un ancêtre d'une vraie annotation


def test_signes_absents_compatibles_avec_la_maladie(real):
    sim = PatientSimulator(real, seed=5)
    for p in sim.cohort(Scenario("t", n_terms=3, n_absent=3), 20):
        for x in p.absent:
            assert x not in real.closure[real.index_of[p.disease_id]]


def test_entropie():
    assert entropy(np.array([0.5, 0.5])) == pytest.approx(1.0)
    assert entropy(np.array([1.0, 0.0])) == pytest.approx(0.0)


def test_question_suivante(toy):
    assert presence_probability(toy, "ORPHA:1", EYE) == 0.9          # via Ectopia
    assert presence_probability(toy, "ORPHA:3", "HP:9000040") == 0.0  # NOT explicite
    # Patient « anomalie du cristallin » : ORPHA:1 et ORPHA:4 sont en tête, une seule a des doigts longs
    qs = best_questions(toy, [LENS], k=4, temperature=0.5)
    assert qs and qs[0].gain > 0
    assert all(q.term not in toy.onto.ancestors(LENS) for q in qs)   # pas de question déjà connue
    assert {q.term for q in qs} & {ECTOPIA, FINGERS}
