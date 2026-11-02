"""Ephemeris models beyond ephemeris.fit (plans/oc.md OC-5): any polynomial order, segmented linear ephemerides
with period jumps, weights by method, robust fitting, the comparison of models (χ², BIC, AIC, an F-test), the
secondary's offset from phase 0.5, mass transfer, and the ephemeris in the form observers write it.

Times T(E) of minima at epochs E (half-integers for secondaries); every fit is made around the middle epoch and
returned in the caller's numbering with its covariance. Errors are scaled by √χ²ᵣ when χ²ᵣ > 1.
"""

import itertools

import numpy as np
from scipy import stats

from .ephemeris import SECONDS_PER_YEAR

METHOD_WEIGHTS = {"visual": 1.0, "photographic": 3.0, "electronic": 10.0}  # relative weights, editable


def weights_by_method(methods, table=None):
    """Relative weights from each minimum's method (σ ∝ 1 / √weight); unknown methods weigh 1."""
    table = METHOD_WEIGHTS if table is None else table
    return np.array([table.get(str(m).lower(), 1.0) for m in methods], float)


def _design(e, order, breaks=(), secondary=None, cycles=(), e_abs=None):
    cols = [np.ones_like(e)] + [e**k for k in range(1, order + 1)]
    cols += [np.maximum(e - b, 0.0) for b in breaks]  # a change of period after each break, continuous O−C
    if secondary is not None:
        cols.append(secondary.astype(float))
    for c in cycles:  # sinusoids of c cycles' period, phased on the caller's epochs (not moved with the middle)
        cols += [np.sin(2 * np.pi * e_abs / c), np.cos(2 * np.pi * e_abs / c)]
    return np.column_stack(cols)


def fit(times, epochs, errors, order=1, breaks=(), secondary_offset=False, robust=None, n_sigma=3.0, cycles=()):
    """Weighted least squares of T(E) = Σ c_k E^k (+ Σ ΔP_j max(E − b_j, 0)) (+ δ for secondaries) (+ sinusoids
    of the given periods in cycles: the quick cyclic model, OC-11).
    robust: None, "huber" (iteratively reweighted, c = 1.345 σ) or "clip" (iterative n_sigma rejection).
    Returns a dict: coef (caller's numbering: T0, P, Q, …, then ΔP_j, then δ), cov, residuals, used (mask),
    chi2, chi2r, n, k, bic, aic, and the names of the coefficients."""
    t, e = np.asarray(times, float), np.asarray(epochs, float)
    err = np.asarray(errors, float)
    mid = float(np.round(np.median(e)))
    t_mid = float(np.median(t))
    sec = (np.abs(e % 1 - 0.5) < 1e-6) if secondary_offset else None
    a = _design(e - mid, order, [b - mid for b in breaks], sec, cycles, e)
    used = np.ones(len(t), bool)
    w = 1 / err
    for _ in range(50):
        coef, *_ = np.linalg.lstsq(a[used] * w[used, None], (t[used] - t_mid) * w[used], rcond=None)
        r = t - t_mid - a @ coef
        if robust == "clip":
            scale = np.sqrt(np.sum((r[used] / err[used]) ** 2) / max(used.sum() - a.shape[1], 1))
            keep = np.abs(r / err) <= n_sigma * max(scale, 1.0)
            if np.array_equal(keep, used):
                break
            used = keep
        elif robust == "huber":
            z = np.abs(r / err)
            new = np.where(z <= 1.345, 1.0, 1.345 / np.maximum(z, 1e-12)) ** 0.5 / err
            if np.allclose(new, w, rtol=1e-8):
                break
            w = new
        else:
            break
    n, k = int(used.sum()), a.shape[1]
    chi2 = float(np.sum((r[used] / err[used]) ** 2))
    chi2r = chi2 / max(n - k, 1)
    aw = a[used] * w[used, None]
    cov = np.linalg.inv(aw.T @ aw) * max(chi2r, 1.0)
    # back to the caller's numbering: the polynomial part E' = E − mid by the binomial expansion
    m = np.eye(k)
    for i in range(order + 1):
        for j in range(i, order + 1):
            m[i, j] = _binom(j, i) * (-mid) ** (j - i)
    coef = m @ coef
    coef[0] += t_mid
    cov = m @ cov @ m.T
    names = ["T0", "P"] + [f"c{j}" for j in range(2, order + 1)] + [f"dP{j + 1}" for j in range(len(breaks))]
    names += ["delta"] if secondary_offset else []
    names += [f"{kind}{j + 1}" for j in range(len(cycles)) for kind in ("sin", "cos")]
    return {"coef": coef, "cov": cov, "err": np.sqrt(np.diag(cov)), "names": names[:k], "residuals": r,
            "used": used, "epochs": e, "chi2": chi2, "chi2r": chi2r, "n": n, "k": k, "order": order,
            "breaks": tuple(breaks), "cycles": tuple(cycles), "bic": chi2 + k * np.log(n),
            "aic": chi2 + 2 * k}  # fmt: skip


def _binom(n, k):
    from math import comb

    return comb(n, k)


def segmented(times, epochs, errors, n_breaks=1, grid=60, robust=None):
    """The segmented linear ephemeris with n_breaks period changes, the break epochs found on a grid of epochs
    between the data (all combinations for one or two breaks; for more, one break moved at a time until no move
    lowers χ²). Each segment's period follows from P and the ΔP_j."""
    e = np.sort(np.asarray(epochs, float))
    inner = np.unique(np.linspace(e[2], e[-3], grid).round())
    best = None
    if n_breaks <= 2:
        candidates = itertools.combinations(inner, n_breaks)
    else:
        candidates = [tuple(np.quantile(inner, (np.arange(n_breaks) + 1) / (n_breaks + 1)).round())]
    for bs in candidates:
        got = fit(times, epochs, errors, 1, bs, robust=robust)
        if best is None or got["chi2"] < best["chi2"]:
            best = got
    if n_breaks > 2:
        improved = True
        while improved:
            improved = False
            for j in range(n_breaks):
                for b in inner:
                    bs = tuple(sorted({*best["breaks"][:j], b, *best["breaks"][j + 1 :]}))
                    if len(bs) != n_breaks:
                        continue
                    got = fit(times, epochs, errors, 1, bs, robust=robust)
                    if got["chi2"] < best["chi2"] - 1e-9:
                        best, improved = got, True
    p = best["coef"][1] + np.concatenate([[0.0], np.cumsum(best["coef"][2 : 2 + n_breaks])])
    best["periods"] = p
    best["jumps"] = np.diff(p) / p[:-1]  # ΔP / P at each break
    return best


def f_test(simple, richer):
    """The F statistic of the richer nested model and its probability under the simpler one."""
    d1 = richer["k"] - simple["k"]
    d2 = richer["n"] - richer["k"]
    f = ((simple["chi2"] - richer["chi2"]) / d1) / (richer["chi2"] / d2)
    return float(f), float(stats.f.sf(f, d1, d2))


def compare(fits):
    """[(name, χ², χ²ᵣ, BIC, AIC, ΔBIC)] and a one-line verdict on the model with the lowest BIC."""
    best = min(fits, key=lambda name: fits[name]["bic"])
    rows = [(name, f["chi2"], f["chi2r"], f["bic"], f["aic"], f["bic"] - fits[best]["bic"]) for name, f in fits.items()]
    others = [r for r in rows if r[0] != best]
    if not others:
        return rows, f"{best}"
    second = min(others, key=lambda r: r[3])
    return rows, f"{best} is preferred: ΔBIC = {fits[best]['bic'] - second[3]:.0f} against {second[0]}"


def dp_dt(f):
    """dP/dt of a quadratic fit: (seconds per year, its error) and P/Ṗ in years."""
    p, q = f["coef"][1], f["coef"][2]
    rate = 2 * q / p  # days per day
    err = 2 * f["err"][2] / p
    return rate * SECONDS_PER_YEAR, err * SECONDS_PER_YEAR, p / rate / 365.25 if rate else np.inf


def ecosw(f):
    """e cos ω ≈ (π / 2)(φ₂ − 0.5) from the fitted offset δ of the secondaries (days), and its error."""
    i = f["names"].index("delta")
    p = f["coef"][1]
    return float(np.pi / 2 * f["coef"][i] / p), float(np.pi / 2 * f["err"][i] / p)


def mass_transfer(dpdt_s_per_yr, period_days, m1, m2):
    """Conservative mass transfer (Kwee 1958): Ṁ₁ = Ṗ M₁ M₂ / (3 P (M₁ − M₂)) in M☉ per year; positive when star 1
    gains. Undefined for equal masses."""
    if m1 == m2:
        raise ValueError("conservative transfer between equal masses changes no period")
    rate = dpdt_s_per_yr / (period_days * 86400.0)  # per year
    return rate * m1 * m2 / (3 * (m1 - m2))


def ambiguous(times, epochs, t0, period):
    """Minima whose O−C against the reference exceeds a quarter period: their cycle count can be wrong."""
    oc = np.asarray(times, float) - (t0 + period * np.asarray(epochs, float))
    return np.flatnonzero(np.abs(oc) > 0.25 * period)


def _digits(value, err, decimals):
    """value with its error in parentheses on the last digits, as observers write it."""
    s = f"{value:.{decimals}f}"
    e = int(round(err * 10**decimals))
    return f"{s}({e})"


def observer_form(t0, t0_err, period, period_err, kind="I", standard="BJD_TDB"):
    """'Min I = BJD_TDB 2459000.12345(12) + 0.36512345(3) E' with each error's two significant digits."""

    def decimals(err):
        return max(int(-np.floor(np.log10(err))) + 1, 0) if err > 0 else 6

    return f"Min {kind} = {standard} {_digits(t0, t0_err, decimals(t0_err))} + " \
           f"{_digits(period, period_err, decimals(period_err))} E"  # fmt: skip


def updated(f, at="middle"):
    """The ephemeris at the middle epoch of the data or at the latest one: (T0, its error, P, its error, the
    epoch moved to), T and dT/dE of the polynomial there — T0 and P least correlated near the middle."""
    e = np.asarray(f["epochs"], float)
    s = float(np.round(np.median(e)) if at == "middle" else np.floor(e.max()))
    k = f["order"] + 1
    jac = np.array([[s**j for j in range(k)], [j * s ** (j - 1) if j else 0.0 for j in range(k)]])
    c = f["coef"][:k]
    cov = jac @ f["cov"][:k, :k] @ jac.T
    t0, p = jac @ c
    return float(t0), float(np.sqrt(cov[0, 0])), float(p), float(np.sqrt(cov[1, 1])), s


def dp_dt_days_per_myr(f):
    """dP/dt of a quadratic fit in days per million years (pulsating stars' unit), with its error."""
    rate, err, _ = dp_dt(f)
    k = 1e6 / 86400.0  # s/yr → d/Myr
    return rate * k, err * k


def cyclic_terms(f):
    """Each sinusoid's semi-amplitude (days) with its error and its phase (cycles of the term, 0 at E = 0)."""
    out = []
    for j, c in enumerate(f["cycles"]):
        i = f["names"].index(f"sin{j + 1}")
        s, co = f["coef"][i], f["coef"][i + 1]
        v = f["cov"][i : i + 2, i : i + 2]
        amp = float(np.hypot(s, co))
        err = float(np.sqrt(max((s * s * v[0, 0] + co * co * v[1, 1] + 2 * s * co * v[0, 1]) / amp**2, 0.0)))
        out.append({"cycles": c, "amplitude": amp, "amplitude_err": err,
                    "phase": float(np.arctan2(co, s) / (2 * np.pi) % 1.0)})  # fmt: skip
    return out


def find_cycle(times, epochs, errors, order=1, n_grid=4000):
    """The quick cyclic model with the best modulation period: the residuals' periodogram over 2 … 3 × span
    cycles, then χ² minimised near its peak. Returns fit(..., cycles=(best,))."""
    from scipy.optimize import minimize_scalar

    e = np.asarray(epochs, float)
    span = np.ptp(e)
    grid = np.geomspace(max(2 * np.median(np.diff(np.sort(e))), span / 100), 3 * span, n_grid)
    chi = [fit(times, epochs, errors, order, cycles=(c,))["chi2"] for c in grid]
    k = int(np.argmin(chi))
    lo, hi = grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)]
    best = minimize_scalar(lambda c: fit(times, epochs, errors, order, cycles=(c,))["chi2"], bounds=(lo, hi),
                           method="bounded", options={"xatol": 1e-6 * grid[k]})  # fmt: skip
    return fit(times, epochs, errors, order, cycles=(best.x,))
