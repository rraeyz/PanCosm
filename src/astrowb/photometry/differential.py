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
    """Differential magnitudes (target minus ensemble) and their errors."""
    rel, rel_err = np.asarray(rel, float), np.asarray(rel_err, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return -2.5 * np.log10(rel), 2.5 / LN10 * rel_err / rel


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


def detrend(rel, covariates, exclude=None, time=None, degree=1):
    """Divide out a trend of ln(rel) in the covariates (dict name -> per-frame values): a polynomial of the
    given degree (1 linear; 2 or 3 for curved trends, e.g. a non-linear airmass or a slow drift in time) in each
    covariate. exclude=(t1, t2) leaves that time range (the eclipse or transit) out of the fit. Returns the
    detrended curve, the coefficients (per unit of each covariate; "name^2", "name^3" for the higher terms, per
    unit of the centred covariate), and the scatter of the fitted points before and after."""
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
        },
        "degree": degree,
        "scatter_before": before,
        "scatter_after": after,
        "points_fitted": int(use.sum()),
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
