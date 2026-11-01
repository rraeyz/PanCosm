"""Light curves of detached eclipsing binaries and transiting planets: two limb-darkened spheres on a
Keplerian orbit (the spherical-star approximation of EBOP/JKTEBOP; written from the geometry, no code
from other programs).

Units: radii r1, r2 as fractions of the semi-major axis a. Star 2 moves on the relative orbit
    rho = (1 - e^2) / (1 + e cos nu),  projected separation  d = rho sqrt(1 - sin^2 i sin^2(nu + omega))
and is in front when sin(nu + omega) > 0 (omega of the primary; primary eclipse at nu = 90 deg - omega).
Surface brightness: I(mu) = I0 [1 - u1 (1 - mu) - u2 (1 - mu)^2] (quadratic limb darkening), disc flux
pi r^2 I0 (1 - u1/3 - u2/6); J = I0_2 / I0_1 is the central surface-brightness ratio.
Eclipsed flux of a star of radius rb behind a disc of radius ra at separation d:
    loss = int_0^rb I(x) 2 x theta(x) dx,  theta(x) = arccos((x^2 + d^2 - ra^2) / (2 x d))
the half-angle of the circle of radius x that lies behind the occulting disc (0 or pi outside the
partial range), integrated with Gauss-Legendre nodes in a cosine variable on each smooth piece.
Not modelled (well-detached systems only): tidal distortion, reflection, gravity darkening, light time.
"""

import numpy as np

from ..spectroscopy.orbit import eccentric_anomaly


def true_anomaly(t, period, t_peri, e):
    ecc = eccentric_anomaly(2 * np.pi * (np.asarray(t, float) - t_peri) / period, e)
    return 2 * np.arctan2(np.sqrt(1 + e) * np.sin(ecc / 2), np.sqrt(1 - e) * np.cos(ecc / 2))


def t_peri_from_t0(t0, period, e, omega_deg):
    """Periastron time from the time of primary minimum (nu = 90 deg - omega)."""
    nu = np.radians(90.0 - omega_deg)
    ecc = 2 * np.arctan2(np.sqrt(1 - e) * np.sin(nu / 2), np.sqrt(1 + e) * np.cos(nu / 2))
    m = ecc - e * np.sin(ecc)
    return t0 - period * m / (2 * np.pi)


def eclipsed_fraction(d, ra, rb, u1=0.0, u2=0.0):
    """Fraction of the flux of a limb-darkened star (radius rb) hidden by a disc (radius ra) at separation d."""
    from ..occult.flux import occulted_fraction

    return occulted_fraction(np.asarray(d, float) / rb, ra / rb, "quadratic", (u1, u2))


def light_curve(
    t,
    period,
    t0,
    r1,
    r2,
    incl_deg,
    j=1.0,
    e=0.0,
    omega_deg=90.0,
    ld1=(0.0, 0.0),
    ld2=(0.0, 0.0),
    l3=0.0,
):
    """Normalised flux (1 outside eclipses, third light l3 as a fraction of the total)."""
    t = np.asarray(t, float)
    tp = t_peri_from_t0(t0, period, e, omega_deg)
    nu = true_anomaly(t, period, tp, e)
    rho = (1 - e * e) / (1 + e * np.cos(nu))
    s = np.sin(np.radians(incl_deg))
    arg = nu + np.radians(omega_deg)
    d = rho * np.sqrt(np.clip(1 - s * s * np.sin(arg) ** 2, 0, None))
    f1 = r1 * r1 * (1 - ld1[0] / 3 - ld1[1] / 6)
    f2 = j * r2 * r2 * (1 - ld2[0] / 3 - ld2[1] / 6)
    front2 = np.sin(arg) > 0
    loss1 = np.where(front2, eclipsed_fraction(d, r2, r1, *ld1), 0.0) * f1
    loss2 = np.where(~front2, eclipsed_fraction(d, r1, r2, *ld2), 0.0) * f2
    flux = (f1 + f2 - loss1 - loss2) / (f1 + f2)
    return (1 - l3) * flux + l3


def light_ratio(r1, r2, j, ld1=(0.0, 0.0), ld2=(0.0, 0.0)):
    """L2 / L1 in the band."""
    return j * (r2 / r1) ** 2 * (1 - ld2[0] / 3 - ld2[1] / 6) / (1 - ld1[0] / 3 - ld1[1] / 6)
