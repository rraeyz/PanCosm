"""One eclipse timed by any method, with honest errors and a verdict on symmetry (plans/oc.md OC-2).

    r = time_minimum(t, flux, method="kvw")           # TimingResult(t_min, error, errors, method, quality, notes)
    table = compare_methods(t, flux)                  # every method; "asymmetric" when they disagree

Methods:
- kvw: Kwee & van Woerden (1956), minima.kwee_van_woerden;
- polynomial: a polynomial of order 2–8 chosen by BIC around the deepest point;
- gaussian, lorentzian: the dip as a Gaussian or a Lorentzian on a linear baseline;
- mikulasek: the phenomenological eclipse of Mikulášek (2015, A&A 584, A8), ψ = 1 − {1 − exp[1 − cosh(x / d)]}^Γ,
  depth A, width d, shape Γ (small Γ: V-shaped, large: flat-bottomed), on a linear baseline (with one branch
  covered to 60 % it was biased by 0.5–0.8 σ on a Gaussian and a trapezoid eclipse: KvW stays the default);
- bisector: the mid-points of the two branches at 7 levels between 20 % and 80 % of the depth, averaged (on a flat
  bottom its error came out 4 × the true scatter: safe, not sharp);
- trapezoid: minima.trapezoid_fit (transits).

Errors: the analytic one (the fit covariance scaled by χ²ᵣ; KvW's own; for the bisector the scatter of its
mid-points), the bootstrap of the residuals and the "prayer-bead" (the residuals shifted cyclically, for correlated
noise); the reported error is the largest. Times are given in the units of t.
"""

from dataclasses import dataclass, field

import numpy as np

from .minima import _smooth, kwee_van_woerden, trapezoid_fit

METHODS = ("kvw", "mikulasek", "polynomial", "gaussian", "lorentzian", "bisector", "trapezoid")


@dataclass
class TimingResult:
    t_min: float
    error: float  # the largest of `errors`
    method: str
    errors: dict = field(default_factory=dict)  # analytic, bootstrap, prayer_bead
    quality: dict = field(default_factory=dict)  # left, right (branch coverage 0–1), depth_snr
    notes: list = field(default_factory=list)  # English sentences the interface translates


def _mikulasek(x, a, d, g):
    psi = 1 - (1 - np.exp(1 - np.cosh(x / d))) ** g
    return a * psi


SHAPES = {  # name: (dip(x, depth, width, shape...), starting shape parameters, bounds of them)
    "gaussian": (lambda x, a, w: a * np.exp(-0.5 * (x / w) ** 2), (), ()),
    "lorentzian": (lambda x, a, w: a / (1 + (x / w) ** 2), (), ()),
    "mikulasek": (_mikulasek, (1.0,), ((0.2, 20.0),)),
}


def _start(t, y):
    """(centre, depth, half-width at half depth, baseline) from the smoothed curve."""
    ys = _smooth(y)
    base = float(np.median(y))
    k = int(np.argmin(ys))
    depth = max(base - ys[k], 1e-6)
    below = np.flatnonzero(ys < base - depth / 2)
    width = (t[below[-1]] - t[below[0]]) / 2 if below.size > 1 else (t[-1] - t[0]) / 10
    dip = np.clip(base - ys, 0, None)
    centre = float(np.sum(dip * t) / dip.sum()) if dip.sum() > 0 else float(t[k])
    return centre, depth, max(width, (t[-1] - t[0]) / 200), base


def _fit_shape(t, y, w, name, start=None):
    """Least squares of baseline + slope·x − dip(x − t0); returns (params, covariance scaled by χ²ᵣ, model)."""
    from scipy.optimize import least_squares

    dip, extra0, extra_bounds = SHAPES[name]
    c, a, hw, base = start or _start(t, y)
    width0 = {"gaussian": hw / 1.1774, "lorentzian": hw, "mikulasek": hw / 1.3}[name]
    span = t[-1] - t[0]
    p0 = [c, a, width0, *extra0, base, 0.0]
    lo = [t[0], 0, span / 1000, *(b[0] for b in extra_bounds), -np.inf, -np.inf]
    hi = [t[-1], np.inf, span, *(b[1] for b in extra_bounds), np.inf, np.inf]

    def model(p):
        x = t - p[0]
        return p[-2] + p[-1] * x - dip(x, *p[1:-2])

    res = least_squares(lambda p: (model(p) - y) * w, p0, bounds=(lo, hi), x_scale="jac")
    dof = max(1, len(y) - len(p0))
    chi2r = float(np.sum(res.fun**2)) / dof
    cov = np.linalg.pinv(res.jac.T @ res.jac) * chi2r
    return res.x, cov, model(res.x)


def _polynomial(t, y, w):
    """(t_min, error, model): orders 2–8 on the points within the half-depth width × 1.5, chosen by BIC."""
    c, _a, hw, _b = _start(t, y)
    sel = np.abs(t - c) <= max(1.5 * hw, 3 * np.median(np.diff(t)))
    if sel.sum() < 6:
        raise ValueError("too few points around the minimum for a polynomial")
    x, yy, ww = t[sel] - c, y[sel], w[sel]
    scale = max(np.abs(x).max(), 1e-12)
    best = None
    for order in range(2, min(8, sel.sum() - 3) + 1):
        coef, res, *_ = np.polyfit(x / scale, yy, order, w=ww, full=True)
        chi2 = float(res[0]) if len(res) else float(np.sum(((np.polyval(coef, x / scale) - yy) * ww) ** 2))
        bic = len(yy) * np.log(max(chi2, 1e-300) / len(yy)) + (order + 1) * np.log(len(yy))
        if best is None or bic < best[0]:
            best = (bic, coef)
    coef = best[1]
    grid = np.linspace(x.min(), x.max(), 2001) / scale
    u = grid[np.argmin(np.polyval(coef, grid))]
    d1, d2 = np.polyder(coef), np.polyder(coef, 2)
    for _ in range(20):  # Newton on the derivative from the grid's lowest point
        step = np.polyval(d1, u) / np.polyval(d2, u) if np.polyval(d2, u) > 0 else 0.0
        u -= step
        if abs(step) < 1e-12:
            break
    resid = (np.polyval(coef, x / scale) - yy) * ww
    sigma2 = np.sum(resid**2) / max(1, len(yy) - len(coef))
    vander = np.vander(x / scale, len(coef)) * ww[:, None]
    cov = np.linalg.pinv(vander.T @ vander) * sigma2
    n = len(coef) - 1  # the root u of p'(u) moves by −(∂p'/∂coef · δcoef) / p''(u)
    grad = np.array([(n - i) * u ** max(n - i - 1, 0) for i in range(n + 1)])
    err = scale * np.sqrt(max(grad @ cov @ grad, 0.0)) / max(np.polyval(d2, u), 1e-300)
    model = np.full_like(t, np.nan)
    model[sel] = np.polyval(coef, x / scale)
    return c + u * scale, float(err), model


LEVELS = np.linspace(0.2, 0.8, 7)  # fractions of the depth where the bisector is taken


def _mids(t, y, levels=LEVELS):
    """(levels, mid-points of the two branches at those fractions of the depth); levels the branches miss are left
    out."""
    _c, a, _hw, base = _start(t, y)
    ys = _smooth(y)
    k = int(np.argmin(np.where(np.abs(t - _c) < (t[-1] - t[0]) / 4, ys, np.inf)))
    got, mids = [], []
    for f in levels:
        level = base - a * f
        left = np.flatnonzero(ys[:k] > level)
        right = np.flatnonzero(ys[k:] > level)
        if not left.size or not right.size:
            continue
        i, j = left[-1], k + right[0]
        tl = np.interp(level, [ys[i + 1], ys[i]], [t[i + 1], t[i]])
        tr = np.interp(level, [ys[j - 1], ys[j]], [t[j - 1], t[j]])
        got.append(f)
        mids.append((tl + tr) / 2)
    return np.array(got), np.array(mids)


def _bisector(t, y):
    """(t_min, error, model=None): the branches' mid-points at 7 levels between 20 % and 80 % of the depth."""
    _levels, mids = _mids(t, y)
    if len(mids) < 3:
        raise ValueError("the eclipse's branches are not covered between 20 % and 80 % of its depth")
    return float(mids.mean()), float(mids.std(ddof=1) / np.sqrt(len(mids))), None


def _once(t, y, w, method):
    """(t_min, analytic error, model curve or None) by one method."""
    if method == "kvw":
        tm, s, _ = kwee_van_woerden(t, y, bootstrap=0)
        return tm, s, None
    if method == "trapezoid":
        r = trapezoid_fit(t, y)
        return r["t0"], r["t0_err"], None
    if method == "polynomial":
        return _polynomial(t, y, w)
    if method == "bisector":
        return _bisector(t, y)
    p, cov, model = _fit_shape(t, y, w, method)
    return float(p[0]), float(np.sqrt(max(cov[0, 0], 0.0))), model


def _quality(t, y, tm):
    c, a, hw, base = _start(t, y)
    noise = float(np.std(np.diff(y)) / np.sqrt(2))
    left = float(np.clip((tm - t[0]) / (2 * hw), 0, 1))
    right = float(np.clip((t[-1] - tm) / (2 * hw), 0, 1))
    return {"left": left, "right": right, "depth_snr": float(a / max(noise, 1e-300))}


def time_minimum(t, y, err=None, method="kvw", bootstrap=200, prayer_bead=True, seed=0):
    """Time one minimum: TimingResult. t sorted or not, one whole eclipse in the window with points on both sides."""
    if method not in METHODS:
        raise ValueError(f"unknown timing method {method}")
    t, y = np.asarray(t, float), np.asarray(y, float)
    order = np.argsort(t)
    t, y = t[order], y[order]
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)[order]
    ref = float(np.round(t.mean(), 1))  # a JD of 2.4e6 leaves too few digits for the fit's steps
    tm, analytic, model = _once(t - ref, y, w, method)
    errors = {"analytic": analytic}
    smooth = model if model is not None and np.all(np.isfinite(model)) else _smooth_model(t - ref, y, w, tm)
    resid = y - smooth
    rng = np.random.default_rng(seed)
    if bootstrap:
        times = _repeat(t - ref, w, method, [smooth + rng.choice(resid, len(resid)) for _ in range(bootstrap)])
        errors["bootstrap"] = float(np.std(times)) if len(times) > 10 else np.nan
    if prayer_bead:
        shifts = np.unique(np.linspace(1, len(resid) - 1, min(len(resid) - 1, 50)).astype(int))
        times = _repeat(t - ref, w, method, [smooth + np.roll(resid, s) for s in shifts])
        errors["prayer_bead"] = float(np.std(times)) if len(times) > 5 else np.nan
    error = float(np.nanmax(list(errors.values())))
    quality = _quality(t - ref, y, tm)
    notes = []
    if min(quality["left"], quality["right"]) < 0.3:
        notes.append("one branch only: the time is unreliable")
    return TimingResult(tm + ref, error, method, errors, quality, notes)


def _smooth_model(t, y, w, tm):
    """A noise-free curve for the resampled errors of the methods without a model of their own (KvW, bisector,
    polynomial, trapezoid): the Gaussian or Mikulášek fit that leaves the smaller residuals; the mirror-symmetric
    curve when neither fits to the noise (it keeps half the noise, so the errors come out larger)."""
    fits = []
    for name in ("gaussian", "mikulasek"):
        try:
            fits.append(_fit_shape(t, y, w, name)[2])
        except (ValueError, RuntimeError, np.linalg.LinAlgError):
            continue
    best = min(fits, key=lambda m: float(np.sum(((m - y) * w) ** 2))) if fits else None
    noise2 = np.var(np.diff(y)) / 2  # point to point
    if best is None or np.mean((best - y) ** 2) > 1.5 * noise2:  # neither shape suits (a flat bottom)
        return _smooth(_symmetric(t, y, tm))
    return best


def _symmetric(t, y, tm):
    """The light curve made symmetric about tm (the model for KvW, the bisector, the trapezoid's residuals)."""
    return 0.5 * (y + np.interp(2 * tm - t, t, y))


def _repeat(t, w, method, samples):
    times = []
    for yy in samples:
        try:
            times.append(_once(t, yy, w, method)[0])
        except (ValueError, np.linalg.LinAlgError, RuntimeError):
            pass
    return times


def asymmetry(t, y, t_min, samples=200, seed=0):
    """The bisector's slope: how far the branches' mid-point moves from 20 % to 80 % of the depth, in units of t,
    with its error from the mirror-symmetric curve plus noise of the point-to-point scatter; (slope, error, True
    when the slope is beyond 3 errors). A symmetric eclipse has a vertical bisector whatever its time; a spot or a
    reflection that deepens one branch tilts it."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    order = np.argsort(t)
    t, y = t[order], y[order]
    ref = float(np.round(t.mean(), 1))
    t = t - ref

    def slope(yy):
        levels, mids = _mids(t, yy)
        return np.polyfit(levels, mids, 1)[0] * 0.6 if len(mids) >= 4 else np.nan  # over 20 % → 80 %

    s0 = slope(y)
    sym = _symmetric(t, y, t_min - ref)
    noise = np.std(np.diff(y)) / np.sqrt(2)  # point to point: the residuals about `sym` would hold the asymmetry
    rng = np.random.default_rng(seed)
    boot = np.array([slope(sym + rng.normal(0, noise, len(y))) for _ in range(samples)])
    err = float(np.nanstd(boot))
    return float(s0), err, bool(np.isfinite(s0) and err > 0 and abs(s0) > 3 * err)


def compare_methods(t, y, err=None, methods=METHODS, bootstrap=100):
    """Every method on the same eclipse: {"results": {method: TimingResult}, "spread": the standard deviation of
    their times, "chi2r": their scatter about the error-weighted mean in units of their errors, "disagree": chi2r > 9
    (the methods differ by more than 3 σ: the eclipse is badly covered or none of the shapes suits it),
    "bisector_slope" and its error (`asymmetry`), "asymmetric": True when the slope is significant}. A method whose
    shape does not suit the eclipse reports a large error and so weighs little."""
    results = {}
    for m in methods:
        try:
            results[m] = time_minimum(t, y, err, method=m, bootstrap=bootstrap)
        except (ValueError, RuntimeError):
            continue
    times = np.array([r.t_min for r in results.values()])
    errors = np.array([r.error for r in results.values()])
    if len(times) < 3 or not np.all(errors > 0):
        return {"results": results, "spread": float(np.std(times)) if len(times) else 0.0, "chi2r": 0.0,
                "disagree": False, "bisector_slope": 0.0, "bisector_slope_err": 0.0, "asymmetric": False}  # fmt: skip
    mean = np.sum(times / errors**2) / np.sum(1 / errors**2)
    chi2r = float(np.sum(((times - mean) / errors) ** 2) / (len(times) - 1))
    tilt, tilt_err, asym = asymmetry(t, y, float(mean))
    return {"results": results, "spread": float(np.std(times)), "chi2r": chi2r, "disagree": chi2r > 9,
            "bisector_slope": tilt, "bisector_slope_err": tilt_err, "asymmetric": asym}  # fmt: skip
