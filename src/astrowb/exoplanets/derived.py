"""What follows from a planet's fitted parameters (plans/exoplanets.md EXO-4), each a pure function with its source;
they work on numbers or on arrays of posterior samples alike. Units: days, stellar radii, degrees, km/s, solar and
Jupiter units from the IAU 2015 B3 nominal values (astropy.constants).

Geometry (Winn 2010, in Seager ed. "Exoplanets", eqs. 7, 8, 14, 15, 16, 30, 9):
    b = a/R★ cos i (1 − e²) / (1 ± e sin ω)                      (+ transit, − occultation)
    T14 = P/π arcsin[ R★/a √((1 + k)² − b²) / sin i ] · √(1 − e²) / (1 + e sin ω),  T23 with (1 − k)²
    ρ★ = 3π (a/R★)³ / (G P²)                                       (Seager & Mallén-Ornelas 2003)
    P_transit = (1 + k) R★/a · (1 + e sin ω) / (1 − e²)
Planet: Mp sin i from the mass function solved for Mp; g_p = 2π/P √(1 − e²) K / ((Rp/a)² sin i) without the
star's mass (Southworth, Wheatley & Sams 2007, eq. 4); T_eq = T_eff √(R★/a) [f (1 − A)]^¼ with f = ¼ for full
redistribution; Safronov number Θ = (a/Rp)(Mp/M★) (Hansen & Barman 2007); TSM (Kempton et al. 2018, eq. 1).
"""

import numpy as np
from astropy import constants as c

G = c.G.value
R_SUN, M_SUN = c.R_sun.value, c.M_sun.value  # IAU 2015 B3 nominal (astropy's default)
R_JUP, M_JUP = c.R_jup.value, c.M_jup.value
R_EARTH, M_EARTH = c.R_earth.value, c.M_earth.value
AU, DAY = c.au.value, 86400.0
SIGMA_SB = c.sigma_sb.value
S_EARTH = 1361.0  # W m⁻², the solar constant (IAU 2015 B3)


def density_from_a(a_rs, period):
    """ρ★ (g cm⁻³) from a/R★ and P (days)."""
    return 3 * np.pi * np.asarray(a_rs) ** 3 / (G * (np.asarray(period) * DAY) ** 2) / 1000.0


def a_from_density(rho, period):
    """a/R★ from ρ★ (g cm⁻³) and P (days)."""
    return (np.asarray(rho) * 1000.0 * G * (np.asarray(period) * DAY) ** 2 / (3 * np.pi)) ** (1 / 3)


def impact_parameter(a_rs, inc, e=0.0, w=90.0, occultation=False):
    sign = -1 if occultation else 1
    s = np.sin(np.radians(w))
    return a_rs * np.cos(np.radians(inc)) * (1 - e * e) / (1 + sign * e * s)


def _duration(period, a_rs, inc, k, e, w, edge):
    b = impact_parameter(a_rs, inc, e, w)
    arg = np.sqrt(np.clip(edge**2 - b**2, 0, None)) / (a_rs * np.sin(np.radians(inc)))
    return period / np.pi * np.arcsin(np.clip(arg, 0, 1)) * np.sqrt(1 - e * e) / (1 + e * np.sin(np.radians(w)))


def t14(period, a_rs, inc, k, e=0.0, w=90.0):
    """Total transit duration (first to fourth contact), days."""
    return _duration(period, a_rs, inc, k, e, w, 1 + k)


def t23(period, a_rs, inc, k, e=0.0, w=90.0):
    """Full-transit duration (second to third contact), days; 0 for a grazing transit."""
    return _duration(period, a_rs, inc, k, e, w, 1 - k)


def transit_probability(a_rs, k, e=0.0, w=90.0):
    return (1 + k) / a_rs * (1 + e * np.sin(np.radians(w))) / (1 - e * e)


def planet_mass(k_rv, period, m_star, e=0.0, inc=90.0, iterations=30):
    """Mp (M_J) from K (km/s), P (days), M★ (M☉), e and i, solving the mass function with Mp in the total mass."""
    f = (k_rv * 1e3) ** 3 * period * DAY * (1 - e * e) ** 1.5 / (2 * np.pi * G)  # (Mp sin i)³ / (M★ + Mp)²
    ms = np.asarray(m_star) * M_SUN
    mp = (f * ms**2) ** (1 / 3)
    for _ in range(iterations):
        mp = (f * (ms + mp) ** 2) ** (1 / 3)
    return mp / np.sin(np.radians(inc)) / M_JUP


def surface_gravity(k_rv, period, rp_a, inc, e=0.0):
    """g_p (m s⁻²) from K, P, Rp/a and i alone (Southworth et al. 2007)."""
    return 2 * np.pi / (period * DAY) * np.sqrt(1 - e * e) * k_rv * 1e3 / (rp_a**2 * np.sin(np.radians(inc)))


def equilibrium_temperature(teff, a_rs, albedo=0.0, f=0.25):
    """T_eq (K); f = ¼ for heat spread over the whole planet, ½ for the day side only."""
    return teff * np.sqrt(1 / np.asarray(a_rs, float)) * (f * (1 - albedo)) ** 0.25


def incident_flux(teff, a_rs):
    """(W m⁻², in units of the Earth's) the planet receives."""
    s = SIGMA_SB * np.asarray(teff, float) ** 4 / np.asarray(a_rs, float) ** 2
    return s, s / S_EARTH


def safronov(a_rs, k, mp_mj, m_star):
    """Θ = (a/Rp)(Mp/M★)."""
    return a_rs / k * (mp_mj * M_JUP) / (m_star * M_SUN)


def tsm(rp_earth, mp_earth, teq, r_star, j_mag):
    """Transmission spectroscopy metric (Kempton et al. 2018): the scale factor of the planet's size class."""
    scale = np.select([rp_earth < 1.5, rp_earth < 2.75, rp_earth < 4.0], [0.190, 1.26, 1.28], 1.15)
    return scale * rp_earth**3 * teq / (mp_earth * r_star**2) * 10 ** (-j_mag / 5)
