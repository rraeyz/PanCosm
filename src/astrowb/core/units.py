"""Named conversions used everywhere (plans/architecture.md ARC-15). No Qt here.

airmass(altitude, formula): the air mass of a line of sight at a true (geometric) altitude in degrees. Young (1994)
is the default; sec z is 3 % too large at 10° and grows without limit towards the horizon. The formula's name is
written beside every airmass column (AIRMASS_NOTE).
"""

import numpy as np

AIRMASS_FORMULAS = ("young1994", "secz", "hardie1962", "kastenyoung1989", "pickering2002")
AIRMASS_NOTE = {
    "young1994": "Young (1994, Appl. Opt. 33, 1108)",
    "secz": "sec z (plane-parallel)",
    "hardie1962": "Hardie (1962)",
    "kastenyoung1989": "Kasten & Young (1989, Appl. Opt. 28, 4735)",
    "pickering2002": "Pickering (2002, DIO 12, 3)",
}


def airmass(altitude_deg, formula="young1994"):
    """Air mass at the true altitude (degrees, scalar or array); NaN at or below the horizon."""
    h = np.asarray(altitude_deg, float)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        z = np.radians(90.0 - h)
        c = np.cos(z)
        if formula == "young1994":
            x = (1.002432 * c**2 + 0.148386 * c + 0.0096467) / (c**3 + 0.149864 * c**2 + 0.0102963 * c + 0.000303978)
        elif formula == "secz":
            x = 1.0 / c
        elif formula == "hardie1962":
            s = 1.0 / c - 1.0
            x = 1.0 / c - 0.0018167 * s - 0.002875 * s**2 - 0.0008083 * s**3
        elif formula == "kastenyoung1989":
            x = 1.0 / (c + 0.50572 * (96.07995 - (90.0 - h)) ** -1.6364)
        elif formula == "pickering2002":
            x = 1.0 / np.sin(np.radians(h + 244.0 / (165.0 + 47.0 * np.abs(h) ** 1.1)))
        else:
            raise ValueError(f"unknown airmass formula {formula}")
        x = np.where(h > 0, x, np.nan)
    return float(x) if np.ndim(x) == 0 else x
