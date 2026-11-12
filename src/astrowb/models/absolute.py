"""What follows from masses and radii (plans/models.md MOD-15), with the IAU 2015 nominal solar values
(Resolution B3: R☉ = 6.957e8 m, L☉ = 3.828e26 W, T_eff☉ = 5772 K, GM☉ = 1.3271244e20 m³ s⁻²; Resolution B2: the
bolometric magnitude zero point L₀ = 3.0128e28 W, so M_bol☉ = 4.74). The masses and radii themselves come from
models.fit.absolute_dimensions (light curve + double-lined orbit)."""

import numpy as np

R_SUN = 6.957e8
L_SUN = 3.828e26
T_SUN = 5772.0
GM_SUN = 1.3271244e20
L_ZERO = 3.0128e28
G = 6.67430e-11


def derived(m, r, teff, period_days=None):
    """{"logg" (cgs), "density" (g cm⁻³), "L" (L☉), "Mbol", "vsync" (km/s, the synchronous equatorial velocity
    when the period is given)} for a star of mass m (M☉), radius r (R☉) and temperature teff."""
    gm = GM_SUN * np.asarray(m, float)
    rad = np.asarray(r, float) * R_SUN
    lum = np.asarray(r, float) ** 2 * (np.asarray(teff, float) / T_SUN) ** 4
    out = {"logg": np.log10(gm / rad**2 * 100), "density": gm / G / (4 / 3 * np.pi * rad**3) / 1000,
           "L": lum, "Mbol": -2.5 * np.log10(lum * L_SUN / L_ZERO)}  # fmt: skip
    if period_days:
        out["vsync"] = 2 * np.pi * rad / (period_days * 86400) / 1000
    return out


def distance(v_mag, mbol, bc, extinction=0.0):
    """Distance in parsecs from the apparent magnitude in a band, the bolometric magnitude, the band's bolometric
    correction (BC = M_bol − M_band) and the extinction in that band."""
    absolute = mbol - bc
    return 10 ** ((v_mag - extinction - absolute + 5) / 5)


def combined_magnitude(m1, m2):
    return -2.5 * np.log10(10 ** (-0.4 * np.asarray(m1)) + 10 ** (-0.4 * np.asarray(m2)))


def against_parallax(d_pc, d_err, parallax_mas, parallax_err):
    """The difference from Gaia's distance in σ (1 / parallax, both errors), and its line."""
    gaia = 1000.0 / parallax_mas
    gaia_err = gaia * parallax_err / parallax_mas
    sigma = (d_pc - gaia) / np.hypot(d_err, gaia_err)
    return float(sigma), f"{d_pc:.0f} ± {d_err:.0f} pc against Gaia's {gaia:.0f} ± {gaia_err:.0f} pc: {sigma:+.1f}σ"
