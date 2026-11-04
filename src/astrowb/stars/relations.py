"""Empirical masses and radii from Teff, log g and [Fe/H] (Torres, Andersen & Giménez 2010, A&ARv 18, 67, their
Table 1, read 2026-11-12 from arXiv:0908.2624):

    log M = a₁ + a₂X + a₃X² + a₄X³ + a₅(log g)² + a₆(log g)³ + a₇[Fe/H],  X = log Teff − 4.1, likewise log R with b,

with intrinsic scatters σ_logM = 0.027 and σ_logR = 0.014, for main-sequence and evolved stars above 0.6 M☉ (not
for pre-main-sequence stars)."""

import numpy as np

from ..core.citations import cites

A = (1.5689, 1.3787, 0.4243, 1.139, -0.1425, 0.01969, 0.1010)
B = (2.4427, 0.6679, 0.1771, 0.705, -0.21415, 0.02306, 0.04173)
SCATTER = (0.027, 0.014)


def _poly(c, teff, logg, feh):
    x = np.log10(teff) - 4.1
    return c[0] + c[1] * x + c[2] * x**2 + c[3] * x**3 + c[4] * logg**2 + c[5] * logg**3 + c[6] * feh


@cites("torres2010")
def torres(teff, logg, feh, errors=(0.0, 0.0, 0.0), n=20000, seed=1):
    """(M, σ_M, R, σ_R) in solar units: the inputs' errors drawn and the calibration's scatter added."""
    rng = np.random.default_rng(seed)
    t = teff + errors[0] * rng.normal(size=n)
    g = logg + errors[1] * rng.normal(size=n)
    f = feh + errors[2] * rng.normal(size=n)
    m = 10 ** (_poly(A, t, g, f) + SCATTER[0] * rng.normal(size=n))
    r = 10 ** (_poly(B, t, g, f) + SCATTER[1] * rng.normal(size=n))
    return 10 ** _poly(A, teff, logg, feh), float(np.std(m)), 10 ** _poly(B, teff, logg, feh), float(np.std(r))
