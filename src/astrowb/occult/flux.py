"""The fraction of a limb-darkened star's flux hidden by an opaque disc (plans/exoplanets.md EXO-1 item 2), for any
law in occult.laws: the radial integral

    loss = ∫₀¹ I(r) 2 r θ(r) dr / (π · disc_flux),  θ(r) = arccos((r² + z² − k²) / (2 r z)),

with z the sky-projected separation and k the radius ratio (both in stellar radii), θ the half-angle of the ring of
radius r behind the occulter. The integral is split at the kinks |z − k| and z + k, and each piece is integrated
by Gauss–Legendre on a cosine-clustered variable (the square-root behaviour at both ends): within 2e-9 of the
uniform-disc closed form for k from 0.001 to 2 (tests).
"""

import numpy as np

from .laws import disc_flux, intensity

_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(24)


def _theta(x, d, ra):
    """Half-angle of the circle of radius x (centred on the eclipsed star) behind the occulter."""
    with np.errstate(invalid="ignore", divide="ignore"):
        c = (x * x + d * d - ra * ra) / (2 * x * d)
    th = np.arccos(np.clip(c, -1, 1))
    th = np.where(x + d <= ra, np.pi, th)  # the whole circle behind the occulter
    th = np.where((x >= d + ra) | (d >= x + ra), 0.0, th)
    return np.where(d == 0, np.where(x < ra, np.pi, 0.0), th)


def occulted_fraction(z, k, law="quadratic", coeffs=(0.0, 0.0)):
    """Fraction of the star's flux hidden at separations z (array) by a disc of radius ratio k."""
    z = np.atleast_1d(np.abs(np.asarray(z, float)))
    out = np.zeros(z.shape)
    hit = z < k + 1
    if not hit.any() or k <= 0:
        return out
    dd = z[hit][:, None]
    lo_k = np.clip(np.abs(dd - k), 0, 1)
    hi_k = np.clip(dd + k, 0, 1)
    edges = np.sort(np.concatenate([np.zeros_like(dd), lo_k, hi_k, np.ones_like(dd)], axis=1), axis=1)
    total = np.zeros(len(dd))
    phi = 0.5 * np.pi * (_NODES[None, :] + 1)
    for j in range(edges.shape[1] - 1):
        a, b = edges[:, j : j + 1], edges[:, j + 1 : j + 2]
        x = a + 0.5 * (b - a) * (1 - np.cos(phi))  # dx = (b − a)/2 sin φ dφ
        mu = np.sqrt(np.clip(1 - x * x, 0, 1))
        f = intensity(mu, law, coeffs) * 2 * x * _theta(x, dd, k) * 0.5 * (b - a) * np.sin(phi)
        total += np.sum(f * _WEIGHTS[None, :], axis=1) * 0.5 * np.pi
    out[hit] = total / (np.pi * disc_flux(law, coeffs))
    return out
