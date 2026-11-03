"""Header numbers as real capture programs write them."""

import math

import pytest
from astropy.io import fits

from astrowb.hdr import get, number


@pytest.mark.parametrize(
    "value, expected",
    [
        (12.5, 12.5),
        (3, 3.0),
        ("2496.00 / Meters", 2496.0),
        ("10 s", 10.0),
        ("-95.5C", -95.5),
        ("1,5", 1.5),
        (" +1.2E3 ", 1200.0),
        ("1.0D-3", 0.001),
        (".5", 0.5),
        ("N/A", None),
        ("", None),
        (None, None),
        (True, None),
        (math.nan, None),
        ("NaN", None),
    ],
)
def test_number(value, expected):
    assert number(value) == expected


def test_get_takes_the_first_key_with_a_number():
    h = fits.Header({"EGAIN": "unknown", "GAIN": "1.6 e-/ADU"})
    assert get(h, "EGAIN", "GAIN", default=1.0) == 1.6
    assert get(h, "RDNOISE", default=7.0) == 7.0
