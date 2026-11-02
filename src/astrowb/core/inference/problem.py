"""A problem for the samplers (EXO-5 item 2): named parameters with priors, start values and scales, a
log-likelihood of the dict of values. Fixed parameters are passed to the likelihood but not sampled."""

import numpy as np

from .priors import Fixed


class Problem:
    def __init__(self, parameters, log_likelihood, derived_priors=(), labels=None, units=None, vectorized=False):
        """parameters: {name: (prior, start, scale)}; log_likelihood(values: dict) → float. vectorized: the
        likelihood takes a dict of arrays (one entry per point) and returns an array; the samplers then evaluate
        whole sets of points at once."""
        self.vectorized = vectorized
        self.all = dict(parameters)
        self.names = [n for n, (p, _s, _c) in self.all.items() if not isinstance(p, Fixed)]
        self.fixed = {n: p.value for n, (p, _s, _c) in self.all.items() if isinstance(p, Fixed)}
        self.priors = [self.all[n][0] for n in self.names]
        self.start = np.array([self.all[n][1] for n in self.names], float)
        self.scale = np.array([self.all[n][2] for n in self.names], float)
        self.log_likelihood = log_likelihood
        self.derived_priors = list(derived_priors)
        self.labels = labels or {}
        self.units = units or {}

    @property
    def dim(self):
        return len(self.names)

    def values(self, theta):
        theta = np.asarray(theta, float)
        return {**self.fixed, **dict(zip(self.names, theta.T, strict=True))}

    def log_prior(self, theta):
        """Of one point (d,) or of points (k, d)."""
        theta = np.asarray(theta, float)
        lp = np.sum([p.logpdf(x) for p, x in zip(self.priors, theta.T, strict=True)], axis=0)
        if self.derived_priors:
            values = self.values(theta)
            with np.errstate(all="ignore"):
                lp = lp + np.sum([d.logpdf(values) for d in self.derived_priors], axis=0)
        return lp

    def _one(self, theta, lp):
        if not np.isfinite(lp):
            return -np.inf
        try:
            ll = float(self.log_likelihood(self.values(theta)))
        except (ValueError, FloatingPointError, ZeroDivisionError):
            return -np.inf
        return lp + ll if np.isfinite(ll) else -np.inf

    def __call__(self, theta):
        """The log-probability, prior plus likelihood, of one point or (k, d) points; −inf outside the prior or
        where the likelihood fails."""
        theta = np.asarray(theta, float)
        lp = self.log_prior(theta)
        if theta.ndim == 1:
            return self._one(theta, float(lp))
        if not self.vectorized:
            return np.array([self._one(t, x) for t, x in zip(theta, lp, strict=True)])
        out = np.full(len(theta), -np.inf)
        ok = np.isfinite(lp)
        if ok.any():
            with np.errstate(all="ignore"):
                ll = np.asarray(self.log_likelihood(self.values(theta[ok])), float)
            out[ok] = np.where(np.isfinite(ll), lp[ok] + ll, -np.inf)
        return out
