"""EXO-14: precision, detectability, ranking."""

import math

import pytest

from astrowb.exoplanets import observability as ob


def test_precision_and_detectability():
    # a bright star on a small telescope is limited by scintillation: halving the aperture raises it by 2^(2/3)
    small = ob.scintillation(20, 1.2, 0, 60)
    assert ob.scintillation(10, 1.2, 0, 60) == pytest.approx(small * 2 ** (2 / 3))
    bright = ob.precision(60, 9.0, 22.0, 20)
    assert bright == pytest.approx(math.hypot(1 / 23000, small) * math.sqrt(4 / 3), rel=0.5)
    faint = ob.precision(60, 15.0, 22.0, 20)
    assert faint > bright
    snr = ob.detectability(0.02, 0.002, 60, 2.5, 2.0)
    assert snr == pytest.approx(0.02 / (0.002 * math.sqrt(1 / 150 + 1 / 120)))


def test_ranking():
    events = [{"name": "a", "snr": 2.0, "drift": 20}, {"name": "b", "snr": 30, "drift": 1},
              {"name": "c", "snr": 10, "drift": 10}]  # fmt: skip
    assert [e["name"] for e in ob.rank(events)] == ["c", "b", "a"]
    assert [e["name"] for e in ob.rank(events, (1.0, 0.0))] == ["b", "c", "a"]
