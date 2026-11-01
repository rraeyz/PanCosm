"""Radiation of a distorted star (plans/models.md MOD-2, the parts without atmosphere tables): local temperatures
from gravity darkening, and the blackbody intensity through a passband.

Gravity darkening (von Zeipel 1924 for radiative envelopes, β = 0.25; Lucy 1967 for convective, β = 0.08):
T_local = T_pole (g / g_pole)^β, with T_pole set so that the area-weighted mean of T⁴ equals T_eff⁴ (the star's
effective temperature is its total flux over its area). Limb darkening: occult.laws (shared with the transits).
"""

import numpy as np

H, C, K_B = 6.62607015e-34, 2.99792458e8, 1.380649e-23


def temperatures(gravity, area, teff, beta=0.25):
    """Local temperatures of surface elements of given gravity and area, their flux-weighted mean equal to teff."""
    g = np.asarray(gravity, float)
    rel = (g / g.max()) ** beta  # T / T_pole
    t_pole = teff * (np.sum(np.asarray(area) * rel**4) / np.sum(area)) ** -0.25
    return t_pole * rel


def planck(wavelength_nm, t):
    """B_λ (W m⁻² m⁻¹ sr⁻¹)."""
    lam = np.asarray(wavelength_nm, float) * 1e-9
    return 2 * H * C**2 / lam**5 / np.expm1(H * C / (lam * K_B * np.asarray(t, float)))


def band_intensity(t, wavelength_nm, response):
    """The blackbody's normal intensity through a passband: ∫ B_λ R dλ / ∫ R dλ, the response linear between its
    tabulated points (integrated exactly on a refined grid, Simpson on 64 sub-steps per interval)."""
    w = np.asarray(wavelength_nm, float)
    r = np.asarray(response, float)
    fine = np.concatenate([np.linspace(a, b, 129)[:-1] for a, b in zip(w[:-1], w[1:], strict=True)] + [w[-1:]])
    rf = np.interp(fine, w, r)
    from scipy.integrate import simpson

    t = np.atleast_1d(np.asarray(t, float))
    num = np.array([simpson(planck(fine, ti) * rf, x=fine) for ti in t])
    out = num / simpson(rf, x=fine)
    return out if out.size > 1 else float(out[0])
