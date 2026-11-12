"""Orbit and timing terms of the binary model (plans/models.md MOD-5): the ephemeris with a period change, the
phases of the two conjunctions of an eccentric orbit, the pseudo-synchronous rotation, exposure integration and
Doppler boosting.

Conjunctions (star 2 in front at ν = 90° − ω, behind at ν = 270° − ω; ω of star 1's orbit as models.eb): their mean
anomalies follow from the true ones through the eccentric anomaly, so the phase of the secondary minimum after the
primary is exact for any e — the classic 0.5 + (2/π) e cos ω (1 + …) is only its first-order term.
"""

import numpy as np


def _mean_anomaly(nu, e):
    ecc = 2 * np.arctan2(np.sqrt(1 - e) * np.sin(nu / 2), np.sqrt(1 + e) * np.cos(nu / 2))
    return ecc - e * np.sin(ecc)


def conjunction_phases(e, omega_deg):
    """(phase of the secondary minimum after the primary, phase of periastron after the primary), both in 0 … 1."""
    w = np.radians(omega_deg)
    m1 = _mean_anomaly(np.pi / 2 - w, e)
    m2 = _mean_anomaly(3 * np.pi / 2 - w, e)
    return float(((m2 - m1) / (2 * np.pi)) % 1.0), float((-m1 / (2 * np.pi)) % 1.0)


def cycle(t, t0, period, dpde=0.0):
    """The (fractional) cycle number of times t on the ephemeris T = t0 + P E + ½ (dP/dE) E² (dP/dE in days per
    cycle; the period at cycle E is P + (dP/dE) E)."""
    x = (np.asarray(t, float) - t0) / period
    if dpde == 0:
        return x
    a = 0.5 * dpde / period
    return (-1 + np.sqrt(1 + 4 * a * x)) / (2 * a)  # the root that tends to x as dP/dE → 0


def phase(t, t0, period, dpde=0.0):
    return cycle(t, t0, period, dpde) % 1.0


def pseudo_synchronous(e):
    """F = Ω_rot / Ω_orbit that tides drive an eccentric orbit to (Hut 1981, A&A 99, 126, eq. 42), relative to the
    mean motion."""
    e2 = np.asarray(e, float) ** 2
    num = 1 + 7.5 * e2 + 45 / 8 * e2**2 + 5 / 16 * e2**3
    den = (1 + 3 * e2 + 3 / 8 * e2**2) * (1 - e2) ** 1.5
    return num / den


def integrate_exposure(model, t, exposure, n=None, tol=1e-6):
    """The mean of model over each exposure by the midpoint rule with n sub-samples (model takes an array of
    times). n None: doubled from 8 until two successive answers differ by less than tol / 3 (the midpoint rule's
    error falls fourfold per doubling, so the last answer is within tol), at most 1024."""
    t = np.atleast_1d(np.asarray(t, float))

    def mean(k):
        offsets = ((np.arange(k) + 0.5) / k - 0.5) * exposure
        return np.asarray(model((t[:, None] + offsets).ravel()), float).reshape(len(t), k).mean(axis=1)

    if n:
        return mean(n)
    k, last = 8, mean(8)
    while k < 1024:
        k *= 2
        now = mean(k)
        if np.max(np.abs(now - last)) < tol / 3:
            return now
        last = now
    return last


def boosting(flux, v_radial_kms, coefficient):
    """Doppler boosting (Loeb & Gaudi 2003): F (1 − B v_r / c) with B the band's boosting factor (≈ 3 − α, α the
    spectral index of the band); v_r positive away from the observer."""
    return np.asarray(flux, float) * (1 - coefficient * np.asarray(v_radial_kms, float) / 299792.458)
