from conftest import ECTOPIA, EYE, FINGERS, GROWTH, LENS, MYOPIA, ROOT, SKEL, TALL


def test_restriction_au_sous_arbre(toy_onto):
    assert ROOT in toy_onto
    assert "HP:0000001" not in toy_onto          # au-dessus de la racine
    assert "HP:0000005" not in toy_onto          # hors « Phenotypic abnormality »
    assert len(toy_onto) == 10


def test_ancetres_reflexifs_et_multi_heritage(toy_onto):
    assert toy_onto.ancestors(ECTOPIA) == {ECTOPIA, LENS, EYE, ROOT}
    assert toy_onto.ancestors(TALL) == {TALL, SKEL, GROWTH, ROOT}


def test_descendants(toy_onto):
    assert toy_onto.descendants(EYE) == {EYE, LENS, ECTOPIA, MYOPIA}


def test_profondeur(toy_onto):
    assert toy_onto.depth(ROOT) == 0
    assert toy_onto.depth(ECTOPIA) == 3


def test_resolution_alt_id_et_obsolete(toy_onto):
    assert toy_onto.resolve("HP:9000098") == ECTOPIA     # alt_id
    assert toy_onto.resolve("HP:9000099") == MYOPIA      # obsolète remplacé
    assert toy_onto.resolve("HP:1234567") is None
    assert toy_onto.resolve("HP:0000005") is None        # hors sous-arbre


def test_recherche(toy_onto):
    assert toy_onto.search("lens")[0][0] == LENS
    assert toy_onto.name(FINGERS) == "Long fingers"
    assert toy_onto.version == "toy/2026-01-01"
