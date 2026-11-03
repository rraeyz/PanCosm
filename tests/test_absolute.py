"""MOD-15: the IAU nominal values and what follows from M, R, Teff."""

import pytest

from astrowb.models import absolute as ab


def test_the_sun_and_a_distance():
    sun = ab.derived(1.0, 1.0, 5772.0, period_days=25.38)
    assert sun["L"] == pytest.approx(1.0) and sun["Mbol"] == pytest.approx(4.74, abs=0.001)
    assert sun["logg"] == pytest.approx(4.438, abs=0.001) and sun["density"] == pytest.approx(1.41, abs=0.01)
    assert sun["vsync"] == pytest.approx(1.99, abs=0.01)
    # the Sun at 10 pc with BC_V = −0.08 appears at V = 4.82
    assert ab.distance(4.82, 4.74, -0.08) == pytest.approx(10.0, rel=1e-6)
    assert ab.distance(4.82 + 5, 4.74, -0.08, extinction=0.0) == pytest.approx(100.0, rel=1e-6)
    assert ab.combined_magnitude(10.0, 10.0) == pytest.approx(10.0 - 2.5 * 0.30103, abs=1e-4)
    sigma, line = ab.against_parallax(205.0, 8.0, 5.0, 0.05)
    assert sigma == pytest.approx(0.6, abs=0.05) and line.startswith("205 ± 8 pc against Gaia's 200 ± 2 pc")
