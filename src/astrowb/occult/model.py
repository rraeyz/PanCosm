"""A transiting planet's light curve (plans/exoplanets.md EXO-1 items 3–4): the orbit gives the sky-projected
separation z(t) in stellar radii, occult.flux the dimming; exposures are integrated by sub-samples, third light
dilutes, and the planet's own light disappears behind the star (the occultation, a uniform disc).

    flux = transit(t, period, tc, k=0.1, a_rs=8.0, inc=88.0, law="quadratic", coeffs=(0.4, 0.2))

Orbit convention as models.eb (one geometry for binaries and planets): tc is the time of the transit (inferior
conjunction), ω the argument of periastron of the star's orbit with the transit at ν = 90° − ω.
"""

import numpy as np

from ..models.eb import t_peri_from_t0, true_anomaly
from .flux import occulted_fraction


def separation(t, period, tc, a_rs, inc, e=0.0, w=90.0):
    """(z in stellar radii, True where the planet is in front of the star)."""
    nu = true_anomaly(np.asarray(t, float), period, t_peri_from_t0(tc, period, e, w), e)
    rho = a_rs * (1 - e * e) / (1 + e * np.cos(nu))
    arg = nu + np.radians(w)
    s = np.sin(np.radians(inc))
    return rho * np.sqrt(np.clip(1 - s * s * np.sin(arg) ** 2, 0, None)), np.sin(arg) > 0


def sub_samples(exposure, period, k, a_rs):
    """Enough sub-samples that each spans a twentieth of the ingress (≈ P k / (π a/R★)) at most, 1 … 101: the
    midpoint rule's error then stays below 1e-6 of the flux (tests)."""
    if not exposure:
        return 1
    ingress = period * k / (np.pi * a_rs)
    return int(np.clip(np.ceil(20 * exposure / max(ingress, 1e-9)), 1, 101)) | 1  # odd: one at the mid-time


def transit(t, period, tc, k, a_rs, inc, law="quadratic", coeffs=(0.0, 0.0), e=0.0, w=90.0, exposure=None,
            n_sub=None, third_light=0.0, occultation=0.0):  # fmt: skip
    """Relative flux (1 out of events). exposure: the integration time in the units of t (None: instantaneous);
    third_light: the fraction of the total light from other sources; occultation: the planet's light as a
    fraction of the star's (the depth of the secondary eclipse)."""
    t = np.atleast_1d(np.asarray(t, float))
    n = n_sub or sub_samples(exposure, period, k, a_rs)
    offsets = (np.arange(n) - (n - 1) / 2) / n * (exposure or 0.0)
    tt = (t[:, None] + offsets[None, :]).ravel()
    z, front = separation(tt, period, tc, a_rs, inc, e, w)
    star = 1 - np.where(front, occulted_fraction(z, k, law, coeffs), 0.0)
    planet = occultation * (1 - np.where(~front, occulted_fraction(z / k, 1 / k, "uniform", ()), 0.0))
    flux = ((star + planet) / (1 + occultation)).reshape(len(t), n).mean(axis=1)
    return (1 - third_light) * flux + third_light
