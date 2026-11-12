"""Radial velocities of a star with planets (plans/exoplanets.md EXO-2): a sum of Keplerians, a zero point and a
jitter per instrument, a linear and quadratic trend (Fulton et al. 2018, RadVel's bases and likelihood, written from
the paper).

    pl = [Planet(P, tc, secosw, sesinw, K), ...]
    v = model(t, pl, inst, gammas, trend=(0.0, 0.0), t_ref)
    fit = fit_rv(t, v, err, inst, [Planet(...) guesses])     # maximum likelihood with jitter; errors from the Hessian

Each planet: period P, time of transit (inferior conjunction) tc, √e cos ω and √e sin ω (no bias towards e > 0 near
circular orbits), semi-amplitude K; ω of the star's orbit with the transit at ν = 90° − ω, as occult.model.
Likelihood: ln L = −½ Σ [r² / (σ² + s_j²) + ln 2π(σ² + s_j²)] with s_j the jitter of instrument j.
"""

from dataclasses import dataclass

import numpy as np

from ..models.eb import t_peri_from_t0
from ..spectroscopy.orbit import rv_model


@dataclass
class Planet:
    period: float
    tc: float
    secosw: float = 0.0
    sesinw: float = 0.0
    k: float = 0.0

    @property
    def e(self):
        return self.secosw**2 + self.sesinw**2

    @property
    def omega(self):
        return float(np.degrees(np.arctan2(self.sesinw, self.secosw))) if self.e > 0 else 90.0

    @property
    def t_peri(self):
        return t_peri_from_t0(self.tc, self.period, self.e, self.omega)


def model(t, planets, inst, gammas, trend=(0.0, 0.0), t_ref=0.0):
    """Velocities at times t observed with instruments inst (integer index per point) of zero points gammas."""
    t = np.asarray(t, float)
    v = np.asarray(gammas, float)[np.asarray(inst, int)] + trend[0] * (t - t_ref) + trend[1] * (t - t_ref) ** 2
    for p in planets:
        v = v + rv_model(t, p.period, p.t_peri, p.e, p.omega, p.k, 0.0)
    return v


def log_likelihood(t, v, err, inst, planets, gammas, jitters, trend=(0.0, 0.0), t_ref=0.0):
    s2 = np.asarray(err, float) ** 2 + np.asarray(jitters, float)[np.asarray(inst, int)] ** 2
    r = np.asarray(v, float) - model(t, planets, inst, gammas, trend, t_ref)
    return float(-0.5 * np.sum(r * r / s2 + np.log(2 * np.pi * s2)))


def _unpack(x, n_planets, n_inst, t_ref=0.0):
    planets = [Planet(x[5 * i], x[5 * i + 1] + t_ref, *x[5 * i + 2 : 5 * i + 5]) for i in range(n_planets)]
    o = 5 * n_planets
    return planets, x[o : o + n_inst], np.exp(x[o + n_inst : o + 2 * n_inst]), tuple(x[o + 2 * n_inst :])


def fit_rv(t, v, err, inst, guesses, trend=False, t_ref=None):
    """Maximum likelihood: {"planets", "gammas", "jitters", "trend", "errors" (the planets' and zero points' 1σ from
    the inverse Hessian of −ln L), "log_likelihood", "t_ref"}. guesses: Planets with starting values (P and tc
    matter most). First weighted least squares with each instrument's jitter taken from its residuals (three
    rounds), then the likelihood itself with the jitters free."""
    from scipy.optimize import least_squares, minimize

    t, v, err = (np.asarray(a, float) for a in (t, v, err))
    inst = np.asarray(inst, int)
    n_inst, n_pl = int(inst.max()) + 1, len(guesses)
    t_ref = float(np.median(t)) if t_ref is None else t_ref
    x = np.r_[[a for p in guesses for a in (p.period, p.tc - t_ref, p.secosw, p.sesinw, p.k)],
              [np.median(v[inst == j]) for j in range(n_inst)], [0.0, 0.0] if trend else []]  # fmt: skip
    jit = np.zeros(n_inst)
    n_trend = 2 if trend else 0

    def resid(y, jitters):
        full = np.r_[y[: 5 * n_pl + n_inst], np.log(np.maximum(jitters, 1e-9)), y[5 * n_pl + n_inst :]]
        planets, gammas, _j, tr = _unpack(full, n_pl, n_inst, t_ref)
        return (v - model(t, planets, inst, gammas, tr or (0.0, 0.0), t_ref)) / np.hypot(err, jitters[inst])

    lo = np.r_[[a for _ in range(n_pl) for a in (0, -np.inf, -0.97, -0.97, 0)], [-np.inf] * (n_inst + n_trend)]
    hi = np.r_[[a for _ in range(n_pl) for a in (np.inf, np.inf, 0.97, 0.97, np.inf)], [np.inf] * (n_inst + n_trend)]
    for _ in range(3):
        x = least_squares(resid, np.clip(x, lo + 1e-9, hi - 1e-9), args=(jit,), bounds=(lo, hi), x_scale="jac").x
        r = resid(x, np.zeros(n_inst)) * err
        jit = np.array([np.sqrt(max(np.var(r[inst == j]) - np.mean(err[inst == j] ** 2), 1e-6)) for j in range(n_inst)])
    x0 = np.r_[x[: 5 * n_pl + n_inst], np.log(jit), x[5 * n_pl + n_inst :]]

    def nll(y):
        planets, gammas, jitters, tr = _unpack(y, n_pl, n_inst, t_ref)
        if any(p.e >= 0.95 or p.k < 0 for p in planets):
            return 1e30
        return -log_likelihood(t, v, err, inst, planets, gammas, jitters, tr or (0.0, 0.0), t_ref)

    best = minimize(nll, x0, method="BFGS")
    errors = np.sqrt(np.clip(np.diag(np.linalg.pinv(_hessian(nll, best.x))), 0, None))
    planets, gammas, jitters, tr = _unpack(best.x, n_pl, n_inst, t_ref)
    o = 5 * n_pl
    e_pl = [Planet(*errors[5 * i : 5 * i + 5]) for i in range(n_pl)]
    return {"planets": planets, "gammas": list(gammas), "jitters": list(jitters), "trend": tr,
            "errors": {"planets": e_pl, "gammas": list(errors[o : o + n_inst]),
                       "jitters": list(errors[o + n_inst : o + 2 * n_inst] * jitters),
                       "trend": tuple(errors[o + 2 * n_inst :])},
            "log_likelihood": -float(best.fun), "t_ref": t_ref}  # fmt: skip


def _hessian(f, x, rel=1e-5):
    """Central-difference Hessian with steps relative to each parameter's size."""
    h = rel * np.maximum(np.abs(x), 1e-2)
    n = len(x)
    out = np.empty((n, n))
    for i in range(n):
        for j in range(i, n):
            e_i, e_j = np.eye(n)[i] * h[i], np.eye(n)[j] * h[j]
            out[i, j] = out[j, i] = (f(x + e_i + e_j) - f(x + e_i - e_j) - f(x - e_i + e_j) + f(x - e_i - e_j)) / (
                4 * h[i] * h[j]
            )
    return out
