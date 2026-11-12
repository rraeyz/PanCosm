"""Magnetic cycles as the alternative to a light-time orbit (plans/oc.md OC-9): is the active star able to drive
the observed period modulation by the Applegate mechanism? Written from Völschow et al. 2016 (A&A 587, A34):

    ΔP / P = 4π K / P_mod                                   (their eq. 43; K the O−C semi-amplitude)
    E_sec = P_mod L_sec                                     (eq. 44: the energy the star radiates in one cycle)
    Tian et al. 2009 (eq. 7): ΔE / E_sec = 0.233 (M/M☉)³ (R/R☉)⁻¹⁰ (T/6000 K)⁻⁴ (a/R☉)⁴ (ΔP/s)² (P_mod/yr)⁻¹
    two-zone model (eq. 35): ΔE / E_sec = k₁ M R² / (P² P_mod L) (1 − √(1 − k₂ G a² M P² (ΔP/P) / R⁵))²,
        k₁ = 0.133, k₂ = 3.42 (ξ = 4/3, λ = 0.0096); no real solution when the root's argument is negative
        (the Applegate parameter A > 1: the star cannot drive the change at any energy).

Units: cgs inside; masses, radii, separations and luminosities solar, P in days, P_mod in years, K in seconds.
"""

import numpy as np

G = 6.674e-8
M_SUN, R_SUN, L_SUN = 1.989e33, 6.957e10, 3.828e33
YEAR, DAY = 3.15576e7, 86400.0
K1, K2 = 0.133, 3.42


def dp_over_p(k_seconds, p_mod_years):
    return 4 * np.pi * k_seconds / (p_mod_years * YEAR)


def energy(m_sec, r_sec, t_sec, l_sec, a_bin, p_bin_days, dpp, p_mod_years):
    """{"E_sec" (erg), "tian" (ΔE/E_sec), "two_zone" (ΔE/E_sec, None when no solution), "A" (the Applegate
    parameter), "feasible" (the two-zone ratio below 1)}."""
    e_sec = p_mod_years * YEAR * l_sec * L_SUN
    dp_s = dpp * p_bin_days * DAY
    tian = 0.233 * m_sec**3 * r_sec**-10 * (t_sec / 6000) ** -4 * a_bin**4 * dp_s**2 / p_mod_years
    m, r, a, p = m_sec * M_SUN, r_sec * R_SUN, a_bin * R_SUN, p_bin_days * DAY
    big_a = K2 * G * a * a * m * p * p * dpp / r**5
    two = None
    if big_a <= 1:
        two = K1 * m * r * r / (p * p) * (1 - np.sqrt(1 - big_a)) ** 2 / e_sec
    return {"E_sec": e_sec, "tian": tian, "two_zone": two, "A": big_a,
            "feasible": two is not None and two < 1}  # fmt: skip
