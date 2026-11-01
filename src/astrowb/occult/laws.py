"""Limb-darkening laws (plans/exoplanets.md EXO-1 item 1): I(μ) / I(1) for μ = cos of the angle from the disc
centre, each written from its definition.

    uniform: 1;  linear: 1 − u(1 − μ);  quadratic: 1 − u1(1 − μ) − u2(1 − μ)²;
    square-root: 1 − c(1 − μ) − d(1 − √μ);  logarithmic: 1 − c(1 − μ) − d μ ln μ;
    power-2 (Hestroffer 1997; Maxted & Gill 2019): 1 − c(1 − μ^α);
    nonlinear (Claret 2000): 1 − Σₖ aₖ(1 − μ^(k/2)), k = 1 … 4.
"""

import numpy as np

COUNT = {"uniform": 0, "linear": 1, "quadratic": 2, "sqrt": 2, "log": 2, "power2": 2, "nonlinear": 4}
_MU, _W = np.polynomial.legendre.leggauss(64)
_MU, _W = 0.5 * (_MU + 1), 0.5 * _W  # Gauss–Legendre on 0 … 1


def intensity(mu, law, coeffs=()):
    """I(μ) / I(1) of the law with its coefficients."""
    mu = np.clip(np.asarray(mu, float), 0.0, 1.0)
    c = tuple(coeffs)
    need = COUNT[law]
    if len(c) != need:
        raise ValueError(f"the {law} law takes {need} coefficients")
    if law == "uniform":
        return np.ones_like(mu)
    if law == "linear":
        return 1 - c[0] * (1 - mu)
    if law == "quadratic":
        return 1 - c[0] * (1 - mu) - c[1] * (1 - mu) ** 2
    if law == "sqrt":
        return 1 - c[0] * (1 - mu) - c[1] * (1 - np.sqrt(mu))
    if law == "log":
        with np.errstate(divide="ignore", invalid="ignore"):
            return 1 - c[0] * (1 - mu) - c[1] * np.where(mu > 0, mu * np.log(mu), 0.0)
    if law == "power2":
        return 1 - c[0] * (1 - mu ** c[1])
    return 1 - sum(a * (1 - mu ** (k / 2)) for k, a in enumerate(c, 1))  # nonlinear


def disc_flux(law, coeffs=()):
    """∫ I(μ) 2μ dμ over the unit disc divided by π: the disc's flux in units of π I(1) R²."""
    return float(np.sum(_W * intensity(_MU, law, coeffs) * 2 * _MU))


def problem(law, coeffs=()):
    """Why these coefficients make no physical star (negative or limb-brightened intensity), or None."""
    mu = np.linspace(0, 1, 201)
    i = intensity(mu, law, coeffs)
    if np.any(i < -1e-12):
        return "the limb-darkening coefficients make the intensity negative near the limb"
    if np.any(np.diff(i) < -1e-12):
        return "the limb-darkening coefficients make the limb brighter than the centre"
    return None


def u_to_q(u1, u2):
    """Kipping 2013 (MNRAS 435, 2152): quadratic (u1, u2) → (q1, q2) in the unit square for physical laws."""
    s = u1 + u2
    return s * s, u1 / (2 * s) if s else 0.0


def q_to_u(q1, q2):
    r = np.sqrt(q1)
    return 2 * r * q2, r * (1 - 2 * q2)
