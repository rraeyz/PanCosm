"""IMG-5: the frame's zero point and colour term from catalogue stars, outliers (a variable, a blend) clipped."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.io import zeropoint


def test_zero_point_and_colour_term():
    rng = np.random.default_rng(3)
    n = 80
    cat = rng.uniform(11, 16, n)
    colour = rng.uniform(0.2, 1.6, n)
    err = 0.005 + 0.01 * 10 ** (0.4 * (cat - 16))
    inst = cat - 22.3 - 0.05 * colour + rng.normal(0, err)
    inst[:3] += 0.4  # a variable and two blends
    zp = zeropoint.fit(inst, cat, colour, err)
    assert abs(zp["zp"] - 22.3) < 3 * zp["zp_err"] and abs(zp["colour_term"] - 0.05) < 3 * zp["colour_term_err"]
    assert not zp["used"][:3].any() and zp["used"][3:].sum() >= n - 6
    plain = zeropoint.fit(inst, cat)
    assert plain["zp"] == pytest.approx(22.3 + 0.05 * np.median(colour), abs=0.02)
    h = zeropoint.write(fits.Header(), zp, "Gaia DR3")
    assert h["ZPCAT"] == "Gaia DR3" and h["MAGZP"] == pytest.approx(22.3, abs=0.01) and "MAGZPCT" in h
    with pytest.raises(ValueError):
        zeropoint.fit([1.0, 2.0], [3.0, 4.0])
