"""Differential photometry on a measured light curve: differential magnitudes, magnitudes from known comparison
magnitudes, check stars and further targets against the same ensemble, each comparison star against the
others, a weighted ensemble, and detrending.

Ensemble with weights w_c (all 1 by default):
    E = sum(w_c F_c),  rel = F_t / E,  (s_rel / rel)^2 = (s_t / F_t)^2 + sum(w_c^2 s_c^2) / E^2
Weights from the comparison stars' own scatter (each star against the sum of the others): w_c = 1 / var_c, the
inverse-variance weighting that gives the least noisy ensemble (as in AIJ / HOPS-style comparison weighting).
Differential magnitude: dm = -2.5 log10(rel); with known comparison magnitudes the ensemble's magnitude is
m_E = -2.5 log10(sum 10^(-0.4 m_c)) and m_t = dm + m_E (photometry.catalog.calibrate does it frame by frame).
Detrending (AIJ, EXOTIC): ln(rel) = b0 + sum_k b_k (z_k - <z_k>), fitted by least squares on the points outside
the eclipse / transit, divided out of all points.
"""

import numpy as np

LN10 = np.log(10.0)


def delta_mag(rel, rel_err):
    """Differential magnitudes (target minus ensemble) and their errors; NaN for both where the flux ratio is not
    positive (no magnitude: the target lost in the sky, its sky ring on a brighter star) — the error came out
    negative there and the light-curve plot refused it (the owner's NSVS 07826147 night)."""
    rel, rel_err = np.asarray(rel, float), np.asarray(rel_err, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ok = rel > 0
        return np.where(ok, -2.5 * np.log10(rel), np.nan), np.where(ok, 2.5 / LN10 * rel_err / rel, np.nan)


def comps_against_others(comp_flux, weights=None):
    """Each comparison star divided by the (weighted) sum of the other comparison stars, normalised to its median,
    and its scatter: a variable or disturbed comparison star stands out. Needs two comparison stars or more."""
    c = np.asarray(comp_flux, float)
    if c.ndim != 2 or c.shape[1] < 2:
        return [], []
    w = np.ones(c.shape[1]) if weights is None else np.asarray(weights, float)
    total = (c * w).sum(axis=1)
    curves, scatter = [], []
    for i in range(c.shape[1]):
        with np.errstate(divide="ignore", invalid="ignore"):
            r = c[:, i] / (total - w[i] * c[:, i])
        r = r / np.nanmedian(r)
        curves.append(r.tolist())
        scatter.append(float(np.nanstd(r)))
    return curves, scatter


def scatter_weights(comp_flux, iterations=10):
    """Inverse-variance weights from each comparison star's scatter against the others (mean weight 1). Iterated:
    a variable star in the "others" would make every star look noisy, so it is down-weighted first and the
    others are measured again against the improved sum."""
    n = np.asarray(comp_flux).shape[1]
    w = np.ones(n)
    for _ in range(iterations if n > 1 else 0):
        _, scatter = comps_against_others(comp_flux, w)
        w = 1 / np.maximum(np.asarray(scatter), 1e-6) ** 2
        w = w * n / w.sum()
    return w


def ensemble(flux_t, err_t, comp_flux, comp_err, weights=None):
    """Relative flux of a star against the (weighted) sum of the comparison stars, with its error."""
    f, s = np.asarray(flux_t, float), np.asarray(err_t, float)
    c, ce = np.asarray(comp_flux, float), np.asarray(comp_err, float)
    if c.ndim < 2 or c.shape[1] == 0:  # no comparison star (space photometry): the target's flux over its median
        norm = np.nanmedian(f)
        return f / norm, np.abs(s / norm)
    w = np.ones(c.shape[1]) if weights is None else np.asarray(weights, float)
    e = (c * w).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = f / e
        err = np.abs(rel) * np.sqrt((s / f) ** 2 + ((w * ce) ** 2).sum(axis=1) / e**2)
    return rel, err


def star_magnitudes(lc, comp_mags, flux=None, flux_err=None):
    """Magnitudes of a star (the target by default) from typed-in comparison magnitudes (None for a comparison
    star without one). Returns mag, mag_err and the comparison stars that disagree (see catalog.calibrate)."""
    from .catalog import calibrate

    comps = [None if m is None else {"mag": float(m)} for m in comp_mags]
    if flux is not None:
        rel, rel_err = ensemble(flux, flux_err, lc["comp_flux"], lc["comp_flux_err"])
        lc = dict(lc) | {"target_flux": list(flux), "rel_flux": rel.tolist(), "rel_flux_err": rel_err.tolist()}
    return calibrate(lc, comps, colour_term=False)


def detrend(rel, covariates, exclude=None, time=None, degree=1, flip_time=None):
    """Divide out a trend of ln(rel) in the covariates (dict name -> per-frame values): a polynomial of the
    given degree (1 linear; 2 or 3 for curved trends, e.g. a non-linear airmass or a slow drift in time) in each
    covariate. exclude=(t1, t2) leaves that time range (the eclipse or transit) out of the fit. Returns the
    detrended curve, the coefficients (per unit of each covariate; "name^2", "name^3" for the higher terms, per
    unit of the centred covariate), and the scatter of the fitted points before and after. flip_time: a step in
    ln(rel) from that time on (the meridian flip turns the camera: the stars land on other pixels), "flip"."""
    rel = np.asarray(rel, float)
    names = list(covariates)
    z = np.column_stack([np.asarray(covariates[k], float) for k in names]) if names else np.empty((len(rel), 0))
    use = np.isfinite(rel) & (rel > 0) & np.all(np.isfinite(z), axis=1)
    if exclude is not None and time is not None:
        t = np.asarray(time, float)
        use &= ~((t >= min(exclude)) & (t <= max(exclude)))
    degree = int(degree)
    if use.sum() < degree * len(names) + 3:
        raise ValueError("too few points outside the left-out range to detrend")
    left_out = ~use & np.isfinite(rel) & np.all(np.isfinite(z), axis=1)
    for i, k in enumerate(names):  # a trend carried far beyond the values it was fitted on is a guess
        lo, hi = z[use, i].min(), z[use, i].max()
        if left_out.any() and np.any(np.abs(z[left_out, i] - (lo + hi) / 2) > 1.5 * (hi - lo) + 1e-12):
            raise ValueError(
                f"{k} in the left-out range is far from its values at the fitted points: leave out only the eclipse"
            )
    centre = z[use].mean(axis=0)
    zc = z - centre
    terms = np.column_stack([zc**p for p in range(1, degree + 1)]) if names else zc  # columns: z, z^2, ...
    if flip_time is not None:
        terms = np.column_stack([terms, _flip_column(time, flip_time)])
    b, *_ = np.linalg.lstsq(np.column_stack([np.ones(use.sum()), terms[use]]), np.log(rel[use]), rcond=None)
    trend = np.exp(terms @ b[1:])
    out = rel / trend
    before = float(np.nanstd(rel[use] / np.nanmedian(rel[use])))
    after = float(np.nanstd(out[use] / np.nanmedian(out[use])))
    return {
        "rel_flux": out.tolist(),
        "coefficients": {
            (k if p == 1 else f"{k}^{p}"): float(b[1 + (p - 1) * len(names) + i])
            for p in range(1, degree + 1)
            for i, k in enumerate(names)
        }
        | ({"flip": float(b[-1])} if flip_time is not None else {}),
        "degree": degree,
        "scatter_before": before,
        "scatter_after": after,
        "points_fitted": int(use.sum()),
    }


def _flip_column(time, flip_time):
    if time is None:
        raise ValueError("the meridian flip needs the times")
    return (np.asarray(time, float) >= flip_time).astype(float)


def best_comparison_sets(comp_flux, check_flux=None, top=8, exhaustive_up_to=12):
    """The comparison-star sets with the quietest ensemble, as AstroImageJ's ensemble optimisation but without the
    target, so that no set is chosen for hiding the target's own variation: every comparison star (and the check star)
    is divided by the sum of the set's other stars, and a set's score is the median point-to-point scatter of those
    curves (mmag). A variable star in the set spoils every curve; outside it, it spoils only its own, which the median
    passes over. Every set of two or more stars is tried up to exhaustive_up_to stars, else one star is toggled at a
    time until the score stops improving (AstroImageJ's second search). Returns [(indices, mmag)], best first."""
    from itertools import combinations

    c = np.asarray(comp_flux, float)
    m = c.shape[1]
    stars = [c[:, j] for j in range(m)] + ([np.asarray(check_flux, float)] if check_flux is not None else [])

    def p2p(y):
        y = y[np.isfinite(y)]
        return np.std(np.diff(y)) / np.sqrt(2) if y.size > 2 else np.inf

    def score(subset):
        idx = list(subset)
        total = c[:, idx].sum(axis=1)
        curves = []
        for j, f in enumerate(stars):
            ref = total - c[:, j] if j < m and j in subset else total
            if j < m and j in subset and len(idx) < 2:
                continue
            with np.errstate(divide="ignore", invalid="ignore"):
                r = f / ref
            curves.append(p2p(r / np.nanmedian(r)))
        return float(1085.7 * np.median(curves))

    if m < 2:
        return [(tuple(range(m)), np.nan)]
    seen = {}
    if m <= exhaustive_up_to:
        for k in range(2, m + 1):
            for subset in combinations(range(m), k):
                seen[subset] = score(subset)
    else:
        current = tuple(range(m))
        seen[current] = score(current)
        while True:
            trials = [tuple(sorted(set(current) ^ {j})) for j in range(m)]
            for t in trials:
                if len(t) >= 2 and t not in seen:
                    seen[t] = score(t)
            best = min((t for t in trials if len(t) >= 2), key=seen.get)
            if seen[best] >= seen[current]:
                break
            current = best
    return sorted(seen.items(), key=lambda kv: kv[1])[:top]


def flip_from_headers(files, times):
    """The time of the meridian flip: the first frame whose PIERSIDE (East / West, as ASCOM and INDI write it)
    differs from the first frame's, half-way to the frame before it. None when the headers do not say."""
    from astropy.io import fits

    sides = []
    for f in files:
        try:
            sides.append(str(fits.getheader(f).get("PIERSIDE", "")).strip().upper()[:1])
        except (OSError, ValueError):
            return None
    known = [i for i, s in enumerate(sides) if s in ("E", "W")]
    if not known:
        return None
    first = sides[known[0]]
    change = next((i for i in known if sides[i] != first), None)
    if change is None:
        return None
    before = max(i for i in known if i < change)
    return (float(times[before]) + float(times[change])) / 2


def detrend_bic(rel, err, covariates, exclude=None, time=None, degree=1, flip_time=None):
    """Every set of the covariates (and the flip step when flip_time is given) fitted to ln(rel) on the same points,
    as AstroImageJ's exhaustive search: [{"names", "flip", "n_params", "chi2", "reduced_chi2", "bic", "delta_bic",
    "chosen"}], lowest BIC first. BIC = chi2 + k ln n with the errors (chi2 of ln(rel), sigma = err / rel), or
    n ln(RSS / n) + k ln n without them. "chosen": the set AstroImageJ's rule keeps, a parameter only when it lowers
    the BIC by more than 2: the fewest parameters within 2 of the lowest BIC. exclude, time: as in detrend."""
    from itertools import combinations

    rel = np.asarray(rel, float)
    names = [k for k in covariates if np.nanmax(covariates[k]) > np.nanmin(covariates[k])]  # constants explain nothing
    z = np.column_stack([np.asarray(covariates[k], float) for k in names]) if names else np.empty((len(rel), 0))
    use = np.isfinite(rel) & (rel > 0) & np.all(np.isfinite(z), axis=1)
    if exclude is not None and time is not None:
        t = np.asarray(time, float)
        use &= ~((t >= min(exclude)) & (t <= max(exclude)))
    sigma = None if err is None else np.asarray(err, float) / rel
    if sigma is not None:
        use &= np.isfinite(sigma) & (sigma > 0)
    n = int(use.sum())
    y = np.log(rel[use])
    zc = z[use] - z[use].mean(axis=0)
    flip = None if flip_time is None else _flip_column(time, flip_time)[use]
    rows = []
    for k in range(len(names) + 1):
        for subset in combinations(range(len(names)), k):
            for with_flip in (False, True) if flip is not None and 0 < flip.sum() < n else (False,):
                cols = [np.ones(n)] + [zc[:, i] ** p for p in range(1, int(degree) + 1) for i in subset]
                cols += [flip] if with_flip else []
                a = np.column_stack(cols)
                if n <= a.shape[1] + 1:
                    continue
                w = 1 / sigma[use] if sigma is not None else np.ones(n)
                b, *_ = np.linalg.lstsq(a * w[:, None], y * w, rcond=None)
                r = y - a @ b
                p = int(np.linalg.matrix_rank(a))
                if sigma is not None:
                    chi2 = float(np.sum((r * w) ** 2))
                    bic = chi2 + p * np.log(n)
                else:
                    chi2 = float(np.sum(r**2))
                    bic = n * np.log(max(chi2, 1e-300) / n) + p * np.log(n)
                rows.append({"names": [names[i] for i in subset], "flip": with_flip, "n_params": p, "chi2": chi2,
                             "reduced_chi2": chi2 / (n - p), "bic": float(bic)})  # fmt: skip
    if not rows:
        raise ValueError("too few points outside the left-out range to detrend")
    rows.sort(key=lambda r: r["bic"])
    best = rows[0]["bic"]
    chosen = min((r for r in rows if r["bic"] <= best + 2), key=lambda r: (r["n_params"], r["bic"]))
    for r in rows:
        r["delta_bic"] = r["bic"] - best
        r["chosen"] = r is chosen
    return rows


def spline_detrend(rel, time, exclude=None, spacings_h=(0.5, 0.75, 1, 1.5, 2, 3, 4, 6), clip=3.0):
    """A smooth trend divided out: a cubic spline in time fitted to ln(rel) with its knot spacing chosen by the BIC
    (as AstroImageJ's Kepler spline, after Vanderburg & Johnson 2014), points beyond clip sigma left out in three
    passes. exclude=(t1, t2): the event is left out and the spline bridges it — make the spacing longer than the
    event or the trend in it is a guess. Returns {"rel_flux", "spacing_h", "bic": {spacing: bic}, ...}."""
    from scipy.interpolate import LSQUnivariateSpline

    rel, t = np.asarray(rel, float), np.asarray(time, float)
    use = np.isfinite(rel) & (rel > 0) & np.isfinite(t)
    if exclude is not None:
        use &= ~((t >= min(exclude)) & (t <= max(exclude)))
    results = {}

    def fit(keep, s):
        tt = t[keep]
        order = np.argsort(tt)
        tt, yy = tt[order], np.log(rel[keep])[order]
        knots = np.arange(tt[0] + s / 24, tt[-1] - 1e-9, s / 24)
        if len(knots):  # a knot needs data between it and the previous one (Schoenberg-Whitney)
            counts = np.histogram(tt, np.r_[tt[0], knots, tt[-1] + 1e-9])[0]
            knots = knots[(counts[:-1] > 0) & (counts[1:] > 0)]
        if len(tt) < len(knots) + 8:
            return None
        try:
            return LSQUnivariateSpline(tt, yy, knots, k=3), len(knots)
        except ValueError:
            return None

    for s in spacings_h:
        keep, got = use.copy(), None
        for _ in range(3):
            trial = fit(keep, s)
            if trial is None:
                break
            got = trial
            r = np.log(np.where(use, rel, np.nan)) - got[0](t)
            sd = 1.4826 * np.nanmedian(np.abs(r[keep] - np.nanmedian(r[keep])))
            new = use & (np.abs(np.nan_to_num(r, nan=np.inf)) <= clip * sd) if sd > 0 else keep
            if np.array_equal(new, keep) or new.sum() < 8:
                break
            keep = new
        got = fit(keep, s) or got  # the spline of the points finally kept
        if got is None:
            continue
        spl, n_knots = got
        n, p = int(keep.sum()), n_knots + 4
        rss = float(np.sum((np.log(rel[keep]) - spl(t[keep])) ** 2))
        results[s] = (n * np.log(max(rss, 1e-300) / n) + p * np.log(n), spl, keep)
    if not results:
        raise ValueError("too few points outside the left-out range to detrend")
    best = min(results, key=lambda s: results[s][0])
    _, spl, keep = results[best]
    out = rel / np.exp(spl(t))
    return {
        "rel_flux": out.tolist(),
        "spacing_h": float(best),
        "bic": {float(s): float(v[0]) for s, v in results.items()},
        "scatter_before": float(np.nanstd(rel[keep] / np.nanmedian(rel[keep]))),
        "scatter_after": float(np.nanstd(out[keep] / np.nanmedian(out[keep]))),
        "points_fitted": int(keep.sum()),
    }


def covariates(lc):
    """The per-frame quantities a light curve offers for detrending."""
    out = {"time": lc["time"]}
    if lc.get("airmass"):
        out["airmass"] = lc["airmass"]
    if lc.get("sky"):
        out["sky"] = [row[0] for row in lc["sky"]]  # the target's sky level
    if lc.get("xy"):
        out["x"] = [row[0][0] for row in lc["xy"]]
        out["y"] = [row[0][1] for row in lc["xy"]]
    if lc.get("fwhm"):
        out["fwhm"] = lc["fwhm"]
    return out
