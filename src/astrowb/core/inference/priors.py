"""Priors (EXO-5 item 1): each with logpdf, sample, transform from the unit cube (nested sampling) and a one-line
description for the interface. Derived puts a prior on a function of the parameters (e.g. on ρ★)."""

import numpy as np
from scipy import special, stats


class Uniform:
    def __init__(self, lo, hi):
        if not hi > lo:
            raise ValueError("the upper limit must be above the lower one")
        self.lo, self.hi = float(lo), float(hi)

    def logpdf(self, x):
        x = np.asarray(x, float)
        return np.where((x >= self.lo) & (x <= self.hi), -np.log(self.hi - self.lo), -np.inf)

    def transform(self, u):
        return self.lo + (self.hi - self.lo) * np.asarray(u, float)

    def sample(self, rng, n):
        return self.transform(rng.random(n))

    def describe(self):
        return f"uniform between {self.lo:g} and {self.hi:g}"


class LogUniform(Uniform):
    def __init__(self, lo, hi):
        if not lo > 0:
            raise ValueError("a log-uniform prior needs a positive lower limit")
        super().__init__(lo, hi)

    def logpdf(self, x):
        x = np.asarray(x, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            inside = (x >= self.lo) & (x <= self.hi)
            return np.where(inside, -np.log(x) - np.log(np.log(self.hi / self.lo)), -np.inf)

    def transform(self, u):
        return self.lo * (self.hi / self.lo) ** np.asarray(u, float)

    def describe(self):
        return f"log-uniform between {self.lo:g} and {self.hi:g}"


class Flat:
    """Constant inside the limits (which may be infinite): improper, so not for nested sampling."""

    def __init__(self, lo=-np.inf, hi=np.inf):
        if not hi > lo:
            raise ValueError("the upper limit must be above the lower one")
        self.lo, self.hi = float(lo), float(hi)

    def logpdf(self, x):
        x = np.asarray(x, float)
        return np.where((x > self.lo) & (x < self.hi), 0.0, -np.inf)

    def describe(self):
        return f"flat between {self.lo:g} and {self.hi:g}"


class Gaussian:
    def __init__(self, mu, sigma):
        if not sigma > 0:
            raise ValueError("the width of a Gaussian prior must be positive")
        self.mu, self.sigma = float(mu), float(sigma)

    def logpdf(self, x):
        z = (np.asarray(x, float) - self.mu) / self.sigma
        return -0.5 * z * z - np.log(self.sigma * np.sqrt(2 * np.pi))

    def transform(self, u):
        return self.mu + self.sigma * np.sqrt(2) * special.erfinv(2 * np.asarray(u, float) - 1)

    def sample(self, rng, n):
        return rng.normal(self.mu, self.sigma, n)

    def describe(self):
        return f"Gaussian {self.mu:g} ± {self.sigma:g}"


class TruncatedGaussian(Gaussian):
    def __init__(self, mu, sigma, lo=-np.inf, hi=np.inf):
        super().__init__(mu, sigma)
        self.lo, self.hi = float(lo), float(hi)
        self._dist = stats.truncnorm((self.lo - mu) / sigma, (self.hi - mu) / sigma, loc=mu, scale=sigma)

    def logpdf(self, x):
        return self._dist.logpdf(np.asarray(x, float))

    def transform(self, u):
        return self._dist.ppf(np.asarray(u, float))

    def sample(self, rng, n):
        return self.transform(rng.random(n))

    def describe(self):
        return f"Gaussian {self.mu:g} ± {self.sigma:g} between {self.lo:g} and {self.hi:g}"


class Fixed:
    """Not a free parameter: the problem leaves it out of the sampled vector."""

    def __init__(self, value):
        self.value = float(value)

    def describe(self):
        return f"fixed at {self.value:g}"


class Derived:
    """A prior on f(parameters): logpdf takes the dict of parameter values."""

    def __init__(self, label, function, prior):
        self.label, self.function, self.prior = label, function, prior

    def logpdf(self, values):
        return self.prior.logpdf(self.function(values))

    def describe(self):
        return f"{self.label}: {self.prior.describe()}"
