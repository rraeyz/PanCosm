"""Spectral disentangling of a double-lined binary: the two stars' own spectra from a series of composite
spectra with known radial velocities (iterative shift-and-add, González & Levato 2006, A&A 448, 283).

On a logarithmic wavelength grid a velocity is a plain shift. Starting with an empty secondary, each star's
spectrum is the average of the observed spectra with the other star removed, shifted to its rest frame; a
few tens of iterations converge. The result is in line depth relative to the joint continuum; with the light
ratio L2/L1 each star is put on its own continuum. Velocities must be those measured on these spectra
(observed, not barycentric-corrected). Different velocities across the series are what makes it work: at
least a few spectra near both quadratures.

Outliers (cosmic rays, the spikes of some pipelines' merged orders, NaN) would be shifted into both stars' spectra:
every 10 iterations the pixels more than 5 robust sigma above the current model are masked and each mean is taken
over the spectra that see that pixel (all of them where the mask would leave none). A median instead of the mean
was tried: it is noisier and drifts with more iterations (synthetic tests, HANDOFF).

What the velocities can separate: a feature of the two stars is told apart only if the velocity separation v1 - v2
changes by more than about its width across the series. `separable_width` gives that change; broader features
(Balmer-line wings, the continuum) are not determined by the data and come out as whatever the iteration started
with — do not read them (or a spectral type that rests on them) from the components. Synthetic test with AI Phe's
real ESO epochs (the separation changes by 58 km/s): the F star's Balmer wings come out wrong and its MK type is
nonsense, although its narrow lines are recovered; with ten epochs over the whole orbit both types come out right.
"""

import numpy as np

from .rv import C_KMS, ln_from_v


def _shift(grid_ln, values, v):
    """values(ln lambda) seen moving at v (km/s)."""
    return np.interp(grid_ln - ln_from_v(v), grid_ln, values, left=0.0, right=0.0)


def separable_width(v1, v2):
    """Change of the velocity separation across the series (km/s): features narrower than this are separated."""
    sep = np.asarray(v1, float) - np.asarray(v2, float)
    return float(np.ptp(sep))


def disentangle(waves, fluxes, v1, v2, light_ratio=None, iterations=40, step_kms=None, clip=5.0):
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
    good = np.isfinite(depth)
    depth = np.where(good, depth, 0.0)
    weight = good.astype(float)

    def mean(values, frame):  # each pixel averaged over the spectra that see it, in the star's rest frame
        out = np.zeros(len(grid))
        for ws in (good.astype(float), weight):  # the unmasked mean where the mask would leave no spectrum
            num = sum(_shift(grid, w * x, -u) for x, w, u in zip(values, ws, frame, strict=True))
            den = sum(_shift(grid, w, -u) for w, u in zip(ws, frame, strict=True))
            out = np.where(den > 0.5, num / np.maximum(den, 1e-12), out)
        return out

    a, b = np.zeros(len(grid)), np.zeros(len(grid))
    for i in range(iterations):
        a = mean([d - _shift(grid, b, v) for d, v in zip(depth, v2, strict=True)], v1)
        b = mean([d - _shift(grid, a, u) for d, u in zip(depth, v1, strict=True)], v2)
        b -= np.median(b)  # the continuum level cannot be split between the stars: give it to star 1
        if clip and i % 10 == 9 and i < iterations - 1:
            resid = depth - np.array([_shift(grid, a, u) + _shift(grid, b, v) for u, v in zip(v1, v2, strict=True)])
            sigma = 1.4826 * np.median(np.abs(resid[good].reshape(-1)))
            bad = resid > clip * sigma  # spikes and cosmic rays are bright; a line core the model misses is not one
            bad[:, 1:] |= bad[:, :-1]  # a spike's wings too
            bad[:, :-1] |= bad[:, 1:]
            weight = (good & ~bad).astype(float)
    edge = int(np.ceil(max(np.ptp(v1), np.ptp(v2)) / (step * C_KMS))) + 1  # ends seen by too few spectra
    grid, a, b = grid[edge:-edge], a[edge:-edge], b[edge:-edge]
    if light_ratio:
        l1 = 1.0 / (1.0 + light_ratio)
        return np.exp(grid), 1.0 + a / l1, 1.0 + b / (1.0 - l1)
    return np.exp(grid), 1.0 + a, 1.0 + b
