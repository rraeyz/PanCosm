"""The global fit of transits and velocities (plans/exoplanets.md EXO-7): planets shared by every data set,
a baseline polynomial per transit night and a zero point per velocity instrument solved exactly inside every
evaluation, a jitter per instrument sampled with the rest, then the shared inference engine's posterior.

The likelihood, data set by data set (written here as EXO-7 asks):
- transit night: Gaussian in the stated errors; model = Π_planets transit(t) × baseline polynomial (least squares);
- velocity instrument: Gaussian with σ² + s², s its jitter; model = Σ_planets Keplerian + γ (γ the weighted mean of
  the residuals for the current s: the exact maximum);
- priors: flat within the bounds (0 < k < 0.5, a/R★ > 1, 0 ≤ b < 1 + k, e < 0.95, K ≥ 0), as the parameters below.

Per planet: P, tc (relative to t_ref), k = Rp/R★, ln a/R★, b, √e cos ω, √e sin ω, K. The impact parameter is at
transit: cos i = b / a/R★ · (1 + e sin ω) / (1 − e²).
"""

import numpy as np

from ..occult.model import transit
from .rv import Planet
from .rv import model as rv_model

PLANET = ("period", "tc", "k", "ln_a", "b", "secosw", "sesinw", "K")


class Model:
    def __init__(self, nights, rv_sets, n_planets, ld, t_ref, order=1):
        self.nights = [tuple(np.asarray(v, float) for v in n[:3]) + (n[3],) for n in nights]
        self.rv = [tuple(np.asarray(v, float) for v in r) for r in rv_sets]
        self.n, self.ld, self.t_ref, self.order = n_planets, ld, t_ref, order

    def names(self):
        out = [f"{p}_{i + 1}" for i in range(self.n) for p in PLANET]
        return out + [f"ln_jitter_{j + 1}" for j in range(len(self.rv))]

    def planets(self, x):
        out = []
        for i in range(self.n):
            per, tc, k, ln_a, b, c, s, kk = x[8 * i : 8 * i + 8]
            out.append({"period": per, "tc": tc, "k": k, "a_rs": np.exp(ln_a), "b": b, "secosw": c, "sesinw": s,
                        "K": kk})  # fmt: skip
        return out

    @staticmethod
    def valid(p):
        e = p["secosw"] ** 2 + p["sesinw"] ** 2
        return 0 < p["k"] < 0.5 and p["a_rs"] > 1 and 0 <= p["b"] < 1 + p["k"] and e < 0.95 and p["K"] >= 0

    @staticmethod
    def geometry(p):
        e = p["secosw"] ** 2 + p["sesinw"] ** 2
        w = np.degrees(np.arctan2(p["sesinw"], p["secosw"])) if e > 0 else 90.0
        cos_i = p["b"] / p["a_rs"] * (1 + e * np.sin(np.radians(w))) / (1 - e * e)
        return e, w, np.degrees(np.arccos(np.clip(cos_i, -1, 1)))

    def transit_residuals(self, planets):
        out = []
        for t, f, err, band in self.nights:
            m = np.ones_like(t)
            for p in planets:
                e, w, inc = self.geometry(p)
                law, coeffs = self.ld[band]
                m = m * transit(t - self.t_ref, p["period"], p["tc"], p["k"], p["a_rs"], inc, law, coeffs, e, w)
            x = t - t.mean()
            a = np.column_stack([m * x**j for j in range(self.order + 1)]) / err[:, None]
            coef, *_ = np.linalg.lstsq(a, f / err, rcond=None)
            out.append(f / err - a @ coef)
        return np.concatenate(out) if out else np.zeros(0)

    def rv_terms(self, planets, jitters):
        """(whitened residuals, Σ ln 2π(σ² + s²)) of every instrument, γ solved."""
        res, norm = [], 0.0
        pl = [Planet(p["period"], p["tc"] + self.t_ref, p["secosw"], p["sesinw"], p["K"]) for p in planets]
        for (t, v, err), s in zip(self.rv, jitters, strict=True):
            r = v - rv_model(t, pl, np.zeros(len(t), int), [0.0])
            var = err**2 + s**2
            gamma = np.sum(r / var) / np.sum(1 / var)
            res.append((r - gamma) / np.sqrt(var))
            norm += float(np.sum(np.log(2 * np.pi * var)))
        return (np.concatenate(res) if res else np.zeros(0)), norm

    def log_likelihood(self, x):
        planets = self.planets(x)
        if not all(self.valid(p) for p in planets):
            return -np.inf
        jit = np.exp(x[8 * self.n :])
        rt = self.transit_residuals(planets)
        rr, norm = self.rv_terms(planets, jit)
        return float(-0.5 * (rt @ rt + rr @ rr + norm))


def fit(nights, rv_sets, starts, ld, order=1, steps=0, seed=1):
    """starts: one dict per planet with period, tc (absolute), k, a_rs, b and optionally secosw, sesinw, K.
    Returns {"best": {name: value}, "posterior": results.Posterior or None, "model": Model}."""
    from scipy.optimize import least_squares

    from ..core.inference import mcmc
    from ..core.inference.priors import Flat
    from ..core.inference.problem import Problem

    t_ref = float(starts[0]["tc"])
    m = Model(nights, rv_sets, len(starts), ld, t_ref, order)
    x0 = []
    for s in starts:
        x0 += [s["period"], s["tc"] - t_ref, s["k"], np.log(s["a_rs"]), s["b"], s.get("secosw", 0.0),
               s.get("sesinw", 0.0), s.get("K", 10.0)]  # fmt: skip
    x0 += [np.log(np.median(r[2])) for r in rv_sets]
    x0 = np.array(x0, float)

    def whitened(x):  # least squares on everything but the jitters' normalisation: a start
        planets = m.planets(x)
        if not all(m.valid(p) for p in planets):
            return np.full(sum(len(n[0]) for n in m.nights) + sum(len(r[0]) for r in m.rv), 1e3)
        return np.concatenate([m.transit_residuals(planets), m.rv_terms(planets, np.exp(x[8 * m.n :]))[0]])

    k = 8 * m.n
    sol = least_squares(lambda y: whitened(np.r_[y, x0[k:]]), x0[:k])  # x_scale="jac" stalled at tc = e = 0
    x = np.r_[sol.x, x0[k:]]
    names = m.names()
    best = dict(zip(names, map(float, x), strict=True))
    post = None
    if steps:
        scale = np.r_[np.sqrt(np.clip(np.diag(np.linalg.pinv(sol.jac.T @ sol.jac)), 1e-14, None)),
                      np.full(len(rv_sets), 0.3)]  # fmt: skip
        problem = Problem({n: (Flat(), v, s) for n, v, s in zip(names, x, scale, strict=True)},
                          lambda vals: m.log_likelihood(np.array([vals[n] for n in names])))  # fmt: skip
        post = mcmc.run(problem, seed=seed, max_steps=steps, check_every=100)
    return {"best": best, "posterior": post, "model": m}
