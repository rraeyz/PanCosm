"""Roche geometry of a binary (plans/models.md MOD-1, items 1–2 and the volume radius): the modified Kopal potential
of Wilson 1979, written from the paper, in units of the separation D (D = 1 for circular orbits):

    Ω(r, λ, ν) = 1/r + q [1/√(D² + r² − 2 D r λ) − λ r / D²] + F² (1 + q) r² (1 − ν²) / 2

r from the centre of star 1, λ and ν the direction cosines towards star 2 (x) and along the orbital axis (z),
q = M2/M1, F the ratio of rotation to orbital angular velocity. Star 2 uses the same function with q → 1/q and
Ω → Ω/q + (q − 1)/(2q) (circular, synchronous). L1 lies between the stars, L2 behind the less massive star,
L3 behind the more massive; Ω_in = Ω(L1) bounds the detached lobes, Ω_out = Ω(L2) the common envelope.
"""

import numpy as np
from scipy.optimize import brentq

_X, _WX = np.polynomial.legendre.leggauss(24)  # cos θ nodes for the volume integral
_PHI = np.linspace(0, 2 * np.pi, 48, endpoint=False)


def omega(r, lam, nu, q, d=1.0, f=1.0):
    r = np.asarray(r, float)
    return (
        1 / r
        + q * (1 / np.sqrt(d * d + r * r - 2 * d * r * lam) - lam * r / (d * d))
        + 0.5 * f * f * (1 + q) * r * r * (1 - nu * nu)
    )


def _dx(x, q, d=1.0, f=1.0):
    """∂Ω/∂x on the line of centres (y = z = 0), x signed from star 1."""
    return -np.sign(x) / x**2 + q * (-(np.sign(x - d)) / (x - d) ** 2 - 1 / d**2) + f * f * (1 + q) * x


def _omega_x(x, q, d=1.0, f=1.0):
    """Ω at the point x of the line of centres (any sign)."""
    return 1 / abs(x) + q * (1 / abs(d - x) - x / d**2) + 0.5 * f * f * (1 + q) * x * x


def lagrange(q, d=1.0, f=1.0):
    """(x_L1, x_L2, x_L3) on the line of centres, star 1 at 0 and star 2 at d; L2 is beyond the less massive star."""
    eps = 1e-9
    l1 = brentq(_dx, eps, d - eps, args=(q, d, f))
    beyond2 = brentq(_dx, d + eps, 3 * d, args=(q, d, f))
    behind1 = brentq(_dx, -2 * d, -eps, args=(q, d, f))
    return (l1, beyond2, behind1) if q <= 1 else (l1, behind1, beyond2)


def critical(q, d=1.0, f=1.0):
    """(Ω_in, Ω_out) for star 1: the potentials at L1 and at L2."""
    l1, l2, _l3 = lagrange(q, d, f)
    return float(_omega_x(l1, q, d, f)), float(_omega_x(l2, q, d, f))


def fillout(om, q):
    """f = (Ω_in − Ω) / (Ω_in − Ω_out): negative detached, 0 at the Roche lobe, 1 at the outer contact surface."""
    om_in, om_out = critical(q)
    return (om_in - om) / (om_in - om_out)


def omega_from_fillout(fill, q):
    om_in, om_out = critical(q)
    return om_in - fill * (om_in - om_out)


def radius(om, q, lam, nu, d=1.0, f=1.0):
    """r of the equipotential Ω along the direction (λ, ν); up to the L1 distance towards the companion."""
    l1, l2, _l3 = lagrange(q, d, f)
    if om < _omega_x(l2, q, d, f):
        raise ValueError("the potential is below the critical one: the surface is not closed")
    top = l1 if lam > 0.999999 else 3 * d  # towards the companion no further than L1

    def g(r):
        return omega(r, lam, nu, q, d, f) - om

    # Ω falls from +∞ at r → 0; the first crossing is the star's own surface
    grid = np.geomspace(1e-6, top, 400)
    vals = g(grid)
    k = int(np.argmax(vals < 0)) if np.any(vals < 0) else None
    if k is None or k == 0:
        raise ValueError("the potential is below the critical one: the surface is not closed")
    return float(brentq(g, grid[k - 1], grid[k]))


def radii(om, q, d=1.0, f=1.0):
    """{"pole", "side", "back", "point", "volume"}: the fractional radii of star 1's surface Ω."""
    out = {"pole": radius(om, q, 0.0, 1.0, d, f), "side": radius(om, q, 0.0, 0.0, d, f),
           "back": radius(om, q, -1.0, 0.0, d, f), "point": radius(om, q, 1.0, 0.0, d, f)}  # fmt: skip
    out["volume"] = volume_radius(om, q, d, f)
    return out


def volume_radius(om, q, d=1.0, f=1.0):
    """The radius of the sphere of the same volume: V = ⅓ ∫ r³ dΩ over directions (Gauss in cos θ, even in φ)."""
    total = 0.0
    for nu, w in zip(_X, _WX, strict=True):
        s = np.sqrt(1 - nu * nu)
        r3 = [radius(om, q, s * np.cos(p), nu, d, f) ** 3 for p in _PHI]
        total += w * np.mean(r3) * 2 * np.pi
    return float((total / 3 / (4 * np.pi / 3)) ** (1 / 3))


def omega_for_volume_radius(r_vol, q, d=1.0, f=1.0):
    """The potential whose surface has this volume-equivalent radius (inside the Roche lobe)."""
    om_in = critical(q, d, f)[0]
    return float(brentq(lambda om: volume_radius(om, q, d, f) - r_vol, om_in * (1 + 1e-9), 1 / max(r_vol, 1e-6) * 50))
