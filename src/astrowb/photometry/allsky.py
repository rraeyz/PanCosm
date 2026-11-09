"""All-sky photometry: the night's solution from standard stars (plans/photometry.md PHO-28; the method of IRAF
photcal's fitparams and Harris, Fitzgerald & Reed 1981).

Per filter, standards observed over a range of airmass X and colour C give

    M − m = Z − k′ X + T C − k″ X C + d (t − t0)

(M standard, m instrumental magnitude; Z zero point, k′ first-order extinction, T colour term, k″ second-order
extinction, d a drift of the zero point through the night; the last two optional). Fitted by weighted least squares
with 3σ clipping; the covariance gives each coefficient's error. `apply` turns programme stars' instrumental
magnitudes into standard ones (with two filters the colour is iterated), with the fit's error included;
`night_quality` says whether the night was photometric.
"""

from dataclasses import dataclass, field

import numpy as np

TERMS = ("zero_point", "extinction", "colour", "second_order", "drift")


@dataclass
class Solution:
    coef: dict  # term -> value
    error: dict  # term -> 1σ
    covariance: np.ndarray
    terms: tuple
    rms: float
    used: np.ndarray
    t0: float = 0.0
    residuals: np.ndarray = field(default_factory=lambda: np.zeros(0))

    def correction(self, airmass, colour, time=None):
        """M − m for the given airmass, colour (and time)."""
        X, C = np.asarray(airmass, float), np.asarray(colour, float)
        cols = _columns(self.terms, X, C, np.zeros_like(X) if time is None else np.asarray(time, float) - self.t0)
        return sum(self.coef[t] * c for t, c in zip(self.terms, cols, strict=True))

    def correction_error(self, airmass, colour, time=None):
        X, C = np.asarray(airmass, float), np.asarray(colour, float)
        cols = np.array(_columns(self.terms, X, C, np.zeros_like(X) if time is None else np.asarray(time) - self.t0))
        return np.sqrt(np.einsum("i...,ij,j...->...", cols, self.covariance, cols))


def _columns(terms, X, C, dt):
    one = np.ones_like(X)
    by = {"zero_point": one, "extinction": -X, "colour": C, "second_order": -X * C, "drift": dt}
    return [by[t] for t in terms]


def fit(inst, std, airmass, colour, err=None, time=None, second_order=False, drift=False, clip=3.0):
    """The night's solution for one filter from standard-star measurements (arrays of equal length)."""
    m, M, X, C = (np.asarray(v, float) for v in (inst, std, airmass, colour))
    t = np.zeros_like(X) if time is None else np.asarray(time, float)
    t0 = float(np.nanmean(t))
    terms = tuple(k for k in TERMS if k not in ("second_order", "drift") or (k == "second_order" and second_order)
                  or (k == "drift" and drift))  # fmt: skip
    y = M - m
    w = np.ones_like(y) if err is None else 1.0 / np.square(np.asarray(err, float))
    ok = np.isfinite(y) & np.isfinite(X) & np.isfinite(C) & np.isfinite(w)
    A = np.array(_columns(terms, X, C, t - t0)).T
    for _ in range(10):
        sw = np.sqrt(w[ok])
        coef, *_ = np.linalg.lstsq(A[ok] * sw[:, None], y[ok] * sw, rcond=None)
        res = y - A @ coef
        scale = np.sqrt(np.sum(w[ok] * res[ok] ** 2) / max(ok.sum() - len(terms), 1))
        keep = ok & (np.abs(res) * np.sqrt(w) <= clip * scale)
        if np.array_equal(keep, ok):
            break
        ok = keep
    sw = np.sqrt(w[ok])
    cov = np.linalg.inv((A[ok] * sw[:, None]).T @ (A[ok] * sw[:, None])) * scale**2
    rms = float(np.sqrt(np.mean(res[ok] ** 2)))
    return Solution(dict(zip(terms, coef, strict=True)), dict(zip(terms, np.sqrt(np.diag(cov)), strict=True)), cov,
                    terms, rms, ok, t0, res)  # fmt: skip


def apply(solution, inst, airmass, colour, inst_err=None, time=None):
    """Standard magnitudes (and errors) of programme stars with a known colour."""
    m = np.asarray(inst, float)
    out = m + solution.correction(airmass, colour, time)
    e = solution.correction_error(airmass, colour, time)
    return out, e if inst_err is None else np.hypot(e, np.asarray(inst_err, float))


def apply_pair(sol_a, sol_b, inst_a, inst_b, airmass_a, airmass_b, iterations=8, time_a=None, time_b=None):
    """Two filters (e.g. B and V, colour B − V) of the same programme stars: the colour iterated from the
    transformed magnitudes. Returns (A, B, colour)."""
    colour = np.asarray(inst_a, float) - np.asarray(inst_b, float)  # the first guess: the instrumental colour
    for _ in range(iterations):
        a, _ = apply(sol_a, inst_a, airmass_a, colour, time=time_a)
        b, _ = apply(sol_b, inst_b, airmass_b, colour, time=time_b)
        colour = a - b
    return a, b, colour


def night_quality(solution, limit=0.03):
    """{"photometric": bool, "rms", "drift" (mag over the night, when fitted)}: the standards' scatter about the
    solution (and the zero point's drift) small enough for all-sky magnitudes."""
    drift = abs(solution.coef.get("drift", 0.0))
    return {"photometric": bool(solution.rms < limit), "rms": solution.rms, "drift": drift}
