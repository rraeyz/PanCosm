"""EXO-6: Torres et al. 2010's relations give their own numbers for the Sun."""

import pytest

from astrowb.stars import relations


def test_the_sun_as_torres_et_al_give_it():
    m, sm, r, sr = relations.torres(5772, 4.438, 0.0)
    assert m == pytest.approx(1.051, abs=0.003) and r == pytest.approx(1.018, abs=0.003)
    assert sm == pytest.approx(m * 0.027 * 2.3026, rel=0.1) and sr == pytest.approx(r * 0.014 * 2.3026, rel=0.1)
    _m, sm2, _r, sr2 = relations.torres(5772, 4.438, 0.0, errors=(100, 0.1, 0.1))
    assert sm2 > sm and sr2 > sr
