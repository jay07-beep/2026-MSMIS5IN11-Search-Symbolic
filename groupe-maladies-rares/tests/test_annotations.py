import pytest

from conftest import ECTOPIA, FINGERS, LENS, MYOPIA, SKIN, TALL
from rarediag.annotations import parse_frequency


@pytest.mark.parametrize("value,expected", [
    ("HP:0040280", 1.0), ("HP:0040281", 0.9), ("HP:0040285", 0.0),
    ("1/2", 0.5), ("3/4", 0.75), ("25%", 0.25), ("", 0.5), ("n'importe quoi", 0.5),
])
def test_frequences(value, expected):
    assert parse_frequency(value) == pytest.approx(expected)


def test_filtrage_orpha_aspect_p(toy_diseases):
    assert set(toy_diseases) == {"ORPHA:1", "ORPHA:2", "ORPHA:3", "ORPHA:4"}   # ni OMIM ni aspect C


def test_contenu(toy_diseases):
    d1 = toy_diseases["ORPHA:1"]
    assert d1.phenotypes == {ECTOPIA: 0.9, FINGERS: 0.9, TALL: 0.5}            # alt_id résolu
    assert set(toy_diseases["ORPHA:2"].phenotypes) == {MYOPIA, SKIN}          # obsolète résolu
    assert toy_diseases["ORPHA:3"].excluded == {SKIN}                          # qualifier NOT
    assert toy_diseases["ORPHA:3"].phenotypes == {FINGERS: 0.5}
    assert toy_diseases["ORPHA:4"].phenotypes == {LENS: 0.17}
