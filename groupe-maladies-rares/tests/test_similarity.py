import itertools

import numpy as np
import pytest

from conftest import ECTOPIA, EYE, FINGERS, GROWTH, LENS, LN, MYOPIA, ROOT, SKEL, SKIN, TALL

N = 4  # maladies Orphanet dans le jeu jouet


def test_ic_valeurs_calculees_a_la_main(toy):
    assert toy.ic[ROOT] == pytest.approx(0.0)
    assert toy.ic[EYE] == pytest.approx(-LN(3 / N))
    assert toy.ic[LENS] == pytest.approx(-LN(2 / N))
    assert toy.ic[ECTOPIA] == pytest.approx(LN(N))
    assert toy.ic[SKEL] == pytest.approx(-LN(2 / N))
    assert toy.ic[GROWTH] == pytest.approx(LN(N))


def test_ic_monotone(toy):
    for t in toy.onto.terms:
        for p in toy.onto.parents[t]:
            assert toy.ic[t] >= toy.ic[p] - 1e-12


def test_ic_monotone_donnees_reelles(real):
    for t in real.onto.terms:
        for p in real.onto.parents[t]:
            assert real.ic[t] >= real.ic[p] - 1e-12


def test_mica_et_resnik(toy):
    assert toy.mica(ECTOPIA, MYOPIA) == EYE
    assert toy.mica(ECTOPIA, LENS) == LENS
    assert toy.mica(TALL, FINGERS) == SKEL
    assert toy.mica(ECTOPIA, SKIN) == ROOT
    assert toy.resnik(ECTOPIA, MYOPIA) == pytest.approx(-LN(3 / 4))


def test_resnik_proprietes(toy):
    terms = list(toy.onto.terms)
    for a, b in itertools.product(terms, terms):
        s = toy.resnik(a, b)
        assert s == pytest.approx(toy.resnik(b, a))            # symétrie
        assert 0 <= s <= min(toy.ic[a], toy.ic[b]) + 1e-12     # bornes
    for a in terms:
        assert toy.resnik(a, a) == pytest.approx(toy.ic[a])    # identité


def score_naif(toy, query, did, symmetric=False):
    """Définition directe (paire par paire) pour contrôler la version vectorisée."""
    terms = list(toy.diseases[did].phenotypes)
    a = np.mean([max(toy.resnik(q, t) for t in terms) for q in query])
    if not symmetric:
        return a
    b = np.mean([max(toy.resnik(t, q) for q in query) for t in terms])
    return (a + b) / 2


@pytest.mark.parametrize("query", [[ECTOPIA], [MYOPIA, FINGERS], [LENS, TALL, SKIN], [EYE]])
@pytest.mark.parametrize("method", ["resnik", "resnik_sym"])
def test_vectorise_egal_naif(toy, query, method):
    s = toy.scores(query, method)
    for i, did in enumerate(toy.disease_ids):
        expected = score_naif(toy, query, did, method == "resnik_sym")
        assert s[i] == pytest.approx(expected)
        assert toy.score_one(query, did, method) == pytest.approx(expected)


def test_classement(toy):
    r = toy.rank([ECTOPIA, TALL])
    assert r[0][0] == "ORPHA:1"
    assert [d for d, _ in toy.rank([MYOPIA, SKIN])][0] == "ORPHA:2"


def test_requete_nettoyee(toy):
    assert toy.clean_query(["HP:9000098", ECTOPIA, "HP:0000000", "HP:0000005"]) == [ECTOPIA]
    assert np.all(toy.scores(["HP:0000000"]) == 0)


def test_signes_absents(toy):
    # Long fingers absent : ORPHA:1 (fréquence 0.9) et ORPHA:3 (0.5) sont pénalisées
    pen = toy.absent_penalty([FINGERS])
    i = toy.index_of
    assert pen[i["ORPHA:1"]] == pytest.approx(0.9 * toy.ic[FINGERS])
    assert pen[i["ORPHA:3"]] == pytest.approx(0.5 * toy.ic[FINGERS])
    assert pen[i["ORPHA:2"]] == 0 and pen[i["ORPHA:4"]] == 0
    r = toy.rank([LENS], absent=[FINGERS])
    assert r[0][0] == "ORPHA:4"
