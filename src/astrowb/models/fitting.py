"""Fitting a system, with a history the user can walk (plans/models.md MOD-12).

Objective: Σ over data sets of ((model − data) / σ)² with each set's noise scale, plus Gaussian prior terms. The
light curves' flux scale and the velocities' zero point are solved exactly inside every evaluation (least squares
of one linear parameter), so they never enter the search. σ: the stated errors, or (weights="scatter") each set's
own residual scatter from the start, as WD's curve-dependent weights.

Optimisers: "lm" (bounded trust-region least squares with finite differences), "nelder_mead", "powell", "de"
(differential evolution within the limits), "basin" (local fits from kicked starts, PHOEBE 1's kicking), and
"careful" (DE over the parameters given as geometric, then lm over all). Every run is a history row that can be
restored exactly.

model(values, dataset) → the model at the data set's times (before its linear scale or zero point); for a data set
of kind "minima" the times of minimum at its epochs. system.constraints: (label, function(values), mean, σ) —
Gaussian constraints on derived quantities (a spectroscopic light ratio, a known third light, a parallax).
"""

import time
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import differential_evolution, least_squares, minimize


@dataclass
class Row:
    optimiser: str
    free: list
    chi2_before: float
    chi2_after: float
    seconds: float
    values: dict  # every parameter's value after the run
    errors: dict = field(default_factory=dict)


@dataclass
class History:
    rows: list = field(default_factory=list)

    def restore(self, system, index):
        for k, v in self.rows[index].values.items():
            system.params[k].value = v
        system.apply()


def _sigmas(system, model, weights):
    out = []
    for d in system.data:
        if weights == "errors" and d.error is not None:
            out.append(np.asarray(d.error, float) * d.noise_scale)
        else:
            vals = {k: p.value for k, p in system.params.items()}
            r = _linear(d, np.asarray(model(vals, d), float))[1]
            out.append(np.full(len(d.time), max(np.std(r), 1e-12)))
    return out


def _linear(d, m):
    """The data set's linear term solved: a flux scale for light curves, a zero point for velocities, none for
    times of minimum (the model gives the times themselves); (model, resid)."""
    y = np.asarray(d.value, float)
    if d.kind == "lc":
        scale = (m @ y) / max(m @ m, 1e-300)
        fitted = scale * m
    elif d.kind == "minima":
        fitted = m
    else:
        fitted = m + np.mean(y - m)
    return fitted, y - fitted


def residuals(system, model, sigmas, free, x):
    vals = {k: p.value for k, p in system.params.items()} | dict(zip(free, x, strict=True))
    out = [_linear(d, np.asarray(model(vals, d), float))[1] / s for d, s in zip(system.data, sigmas, strict=True)]
    for k in free:
        prior = system.params[k].prior
        if prior and prior[0] == "gaussian":
            out.append(np.array([(vals[k] - prior[1]) / prior[2]]))
    for _label, function, mu, sigma in getattr(system, "constraints", ()):  # MOD-17: a light ratio, l₃, a distance
        out.append(np.array([(function(vals) - mu) / sigma]))
    return np.concatenate(out)


def fit(system, model, optimiser="lm", free=None, weights="errors", history=None, geometric=(), seed=1, kicks=8):
    """Fit the free parameters; returns the history row (and appends it to history)."""
    began = time.monotonic()
    free = list(free or system.free())
    sigmas = _sigmas(system, model, weights)
    lo = np.array([system.params[k].lower for k in free])
    hi = np.array([system.params[k].upper for k in free])
    x0 = np.clip([system.params[k].value for k in free], lo, hi)

    def res(x):
        return residuals(system, model, sigmas, free, x)

    def chi2(x):
        r = res(x)
        return float(r @ r) if np.all(np.isfinite(r)) else 1e300

    before = chi2(x0)
    finite = np.isfinite(lo) & np.isfinite(hi)
    if optimiser == "lm":
        x = least_squares(res, x0, bounds=(lo, hi)).x
    elif optimiser in ("nelder_mead", "powell"):
        method = "Nelder-Mead" if optimiser == "nelder_mead" else "Powell"
        opts = {"maxiter": 20000, "xatol": 1e-10, "fatol": 1e-10} if method == "Nelder-Mead" else {}
        x = minimize(chi2, x0, method=method, bounds=list(zip(lo, hi, strict=True)), options=opts).x
    elif optimiser == "de":
        if not finite.all():
            raise ValueError("differential evolution needs finite limits on every free parameter")
        x = differential_evolution(chi2, list(zip(lo, hi, strict=True)), seed=seed, tol=1e-10, polish=True).x
    elif optimiser == "basin":
        rng = np.random.default_rng(seed)
        best = least_squares(res, x0, bounds=(lo, hi))
        span = np.where(finite, 0.1 * (hi - lo), 0.1 * np.maximum(np.abs(x0), 1e-3))
        for _ in range(kicks):
            trial = np.clip(best.x + span * rng.normal(size=len(x0)), lo, hi)
            got = least_squares(res, trial, bounds=(lo, hi))
            if got.cost < best.cost:
                best = got
        x = best.x
    elif optimiser == "careful":
        geo = [k for k in free if k in geometric]
        if geo:
            row = fit(system, model, "de", geo, weights, None, seed=seed)
            x0 = np.array([row.values[k] for k in free])
        x = least_squares(res, x0, bounds=(lo, hi)).x
    else:
        raise ValueError(f"unknown optimiser: {optimiser}")
    for k, v in zip(free, x, strict=True):
        system.params[k].value = float(v)
    system.apply()
    jac = least_squares(res, x, bounds=(lo, hi), max_nfev=1).jac
    try:
        err = np.sqrt(np.diag(np.linalg.inv(jac.T @ jac)))
    except np.linalg.LinAlgError:
        err = np.full(len(free), np.nan)
    values = {k: p.value for k, p in system.params.items()}
    errors = dict(zip(free, map(float, err), strict=True))
    row = Row(optimiser, free, before, chi2(x), time.monotonic() - began, values, errors)
    if history is not None:
        history.rows.append(row)
    return row
