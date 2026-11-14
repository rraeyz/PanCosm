"""When a third star is close, its pull changes the binary's period itself, and the eclipse times move by more than
the light-travel time (plans/oc.md OC-10; Borkovits et al. 2015, MNRAS 448, 946; 2016, MNRAS 455, 4136):

    A_dyn  = (1 / 2π) · (m_C / m_ABC) · (P₁² / P₂) · (1 − e₂²)^(−3/2)           (the quadrupole dynamical delay)
    A_LTTE = (a₂ sin i₂ / c) · (m_C / m_ABC) · √(1 − e₂² cos² ω₂),  a₂³ = G m_ABC P₂² / 4π²

A light-time fit (timeseries/ltte.py) is only the whole story while A_dyn ≪ A_LTTE: `check` gives both amplitudes
and a warning when the dynamical one reaches a tenth of the light-time one — compact triples (P₂ of tens of days
for P₁ of a day) are then fitted wrongly by LTTE alone.
"""

import numpy as np

G = 2.9591220828559115e-4  # AU³ / (M☉ d²)
C = 173.1446326846693  # AU / d


def amplitudes(p1, p2, m_ab=2.0, m_c=1.0, e2=0.0, sin_i2=1.0, omega2=90.0):
    """(A_dyn, A_LTTE) in days for inner period p1, outer period p2 (days), masses in M☉."""
    m_abc = m_ab + m_c
    a_dyn = (m_c / m_abc) * p1**2 / p2 * (1 - e2**2) ** -1.5 / (2 * np.pi)
    a2 = (G * m_abc * p2**2 / (4 * np.pi**2)) ** (1 / 3)
    a_ltte = a2 * sin_i2 / C * (m_c / m_abc) * np.sqrt(1 - e2**2 * np.cos(np.radians(omega2)) ** 2)
    return float(a_dyn), float(a_ltte)


def check(p1, p2, m_ab=2.0, m_c=1.0, e2=0.0, sin_i2=1.0, omega2=90.0, limit=0.1):
    """{"a_dyn", "a_ltte" (days), "ratio", "warn"}: warn when the dynamical delay is ≥ limit × the light-time one."""
    a_dyn, a_ltte = amplitudes(p1, p2, m_ab, m_c, e2, sin_i2, omega2)
    ratio = a_dyn / a_ltte if a_ltte > 0 else np.inf
    return {"a_dyn": a_dyn, "a_ltte": a_ltte, "ratio": float(ratio), "warn": bool(ratio >= limit)}


def for_ltte_fit(fit, m12=2.0):
    """check() for a light-time fit (oc_models.LTTEFit): the inner period, P₃, e and ω from the fit, the third
    star's mass the smallest the mass function allows with M₁ + M₂ = m12 (sin i₃ = 1)."""
    from scipy.optimize import brentq

    f_m = fit.mass_function
    m3 = float(brentq(lambda m: m**3 / (m12 + m) ** 2 - f_m, 1e-6, 1e4)) if f_m > 0 else 0.0
    return check(fit.period, fit.p3, m12, m3, fit.e, 1.0, fit.omega) | {"m3": m3}
