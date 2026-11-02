"""Transit timing in the O−C machinery (plans/oc.md OC-13): mid-times on a refined ephemeris with its drift into
the future, orbital decay with the tidal quality factor, periodic TTVs. The fits are ephemeris_models'."""

import numpy as np

from . import ephemeris_models as em

MS_PER_YEAR = 1000 * em.SECONDS_PER_YEAR


def epochs(times, t0, period):
    return np.round((np.asarray(times, float) - t0) / period)


def drift(f, epochs_ahead):
    """The 1σ uncertainty (days) of transits at these epochs from a linear fit's T0, P and their covariance."""
    e = np.asarray(epochs_ahead, float)
    c = f["cov"]
    return np.sqrt(c[0, 0] + e * e * c[1, 1] + 2 * e * c[0, 1])


def decay(times, errors, t0, period):
    """Linear against quadratic: {"linear", "quadratic", "dp_dt_ms_yr", "dp_dt_err", "delta_bic", "f_test_p"}."""
    e = epochs(times, t0, period)
    lin = em.fit(times, e, errors, 1)
    quad = em.fit(times, e, errors, 2)
    rate, err, _ = em.dp_dt(quad)  # seconds per year
    return {"linear": lin, "quadratic": quad, "dp_dt_ms_yr": rate * 1000, "dp_dt_err": err * 1000,
            "delta_bic": quad["bic"] - lin["bic"], "f_test_p": em.f_test(lin, quad)[1]}  # fmt: skip


def tidal_q(dp_dt_ms_yr, period_days, m_planet_mjup, m_star, r_star, a_au):
    """Q′★ = −27π / (2 Ṗ) (M_p / M★) (R★ / a)⁵ (Goldreich & Soter 1966; as Patra et al. 2017, eq. 4), Ṗ
    dimensionless; masses in M_Jup and M☉, R★ in R☉, a in AU."""
    pdot = dp_dt_ms_yr / 1000 / em.SECONDS_PER_YEAR  # s per s
    q_mass = m_planet_mjup * 9.5458e-4 / m_star
    ratio = r_star * 6.957e8 / (a_au * 1.495978707e11)
    return -27 * np.pi / (2 * pdot) * q_mass * ratio**5
