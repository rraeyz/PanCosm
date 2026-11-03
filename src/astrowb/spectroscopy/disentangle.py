"""Spectral disentangling of a double-lined binary: the two stars' own spectra from a series of composite
spectra with known radial velocities (iterative shift-and-add, González & Levato 2006, A&A 448, 283).

On a logarithmic wavelength grid a velocity is a plain shift. Starting with an empty secondary, each star's
spectrum is the average of the observed spectra with the other star removed, shifted to its rest frame; a
few tens of iterations converge. The result is in line depth relative to the joint continuum; with the light
ratio L2/L1 each star is put on its own continuum. Velocities must be those measured on these spectra
(observed, not barycentric-corrected). Different velocities across the series are what makes it work: at
least a few spectra near both quadratures.
"""

import numpy as np

from .rv import C_KMS, ln_from_v


def _shift(grid_ln, values, v):
    """values(ln lambda) seen moving at v (km/s)."""
    return np.interp(grid_ln - ln_from_v(v), grid_ln, values, left=0.0, right=0.0)


def disentangle(waves, fluxes, v1, v2, light_ratio=None, iterations=40, step_kms=None):
    """waves, fluxes: continuum-normalised spectra; v1, v2: velocities of the stars in each (km/s).
    Returns (wave, spectrum of star 1, spectrum of star 2), each on its own continuum when light_ratio
    (L2/L1) is given, else as line depths added to 1 (the composite's continuum)."""
    lo = max(np.log(w[0]) for w in waves) + max(np.abs(v1).max(), np.abs(v2).max()) / C_KMS
    hi = min(np.log(w[-1]) for w in waves) - max(np.abs(v1).max(), np.abs(v2).max()) / C_KMS
    step = (step_kms or C_KMS * min(np.median(np.diff(np.log(w))) for w in waves)) / C_KMS
    grid = np.arange(lo, hi, step)
    if len(grid) < 50:
        raise ValueError("the spectra hardly overlap")
    depth = np.array([np.interp(grid, np.log(w), f) - 1.0 for w, f in zip(waves, fluxes, strict=True)])
    a, b = np.zeros(len(grid)), np.zeros(len(grid))
    for _ in range(iterations):
        a = np.mean([_shift(grid, d - _shift(grid, b, v), -u) for d, u, v in zip(depth, v1, v2, strict=True)], axis=0)
        b = np.mean([_shift(grid, d - _shift(grid, a, u), -v) for d, u, v in zip(depth, v1, v2, strict=True)], axis=0)
        b -= np.median(b)  # the continuum level cannot be split between the stars: give it to star 1
    edge = int(np.ceil(max(np.ptp(v1), np.ptp(v2)) / (step * C_KMS))) + 1  # ends seen by too few spectra
    grid, a, b = grid[edge:-edge], a[edge:-edge], b[edge:-edge]
    if light_ratio:
        l1 = 1.0 / (1.0 + light_ratio)
        return np.exp(grid), 1.0 + a / l1, 1.0 + b / (1.0 - l1)
    return np.exp(grid), 1.0 + a, 1.0 + b
