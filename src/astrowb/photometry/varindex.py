"""Variable stars found among all the stars of a field (plans/photometry.md PHO-30).

    ens = ensemble(mag, err)          Honeycutt (1992, PASP 104, 435): frame zero points and star means solved
                                      together with weights, variables left out of the zero points
    idx = indices(ens["resid"], err)  per star: weighted σ, MAD, IQR, 1/η (von Neumann), Stetson J and K, χ²_ν
    cand = candidates(ens["mean"], idx)   beyond n robust σ of the stars of its brightness in at least two indices

The indices are those Sokolovsky et al. (2017, MNRAS 464, 274) rank best for finding variables in a time series of
many stars (IQR, 1/η, MAD, weighted σ) besides Stetson's (Welch & Stetson 1993; Stetson 1996). mag, err: (frames,
stars), NaN where a star was not measured.
"""

import numpy as np

SELECT = ("wsigma", "mad", "iqr", "inv_eta", "stetson_j", "chi2")  # larger = more variable; K is a shape index


def ensemble(mag, err, iterations=12, cut=3.0):
    """{"zp": per frame, "mean": per star, "resid": magnitudes minus both, "used": stars in the zero points}."""
    m = np.asarray(mag, float)
    w = 1.0 / np.square(np.asarray(err, float))
    w = np.where(np.isfinite(m) & np.isfinite(w), w, 0.0)
    m0 = np.where(w > 0, m, 0.0)
    zp = np.zeros(m.shape[0])
    used = (w > 0).mean(0) > 0.8  # stars seen on most frames
    mean = np.zeros(m.shape[1])
    for _ in range(iterations):
        wu = w * used
        mean = ((m0 - zp[:, None]) * w).sum(0) / np.maximum(w.sum(0), 1e-300)
        zp = ((m0 - mean) * wu).sum(1) / np.maximum(wu.sum(1), 1e-300)
        zp -= np.average(zp)
        resid = np.where(w > 0, m - mean - zp[:, None], np.nan)
        chi2 = np.nansum(resid**2 * w, 0) / np.maximum((w > 0).sum(0) - 1, 1)
        keep = chi2 < cut * np.nanmedian(chi2[used]) if used.any() else used
        if np.array_equal(keep & used, used):
            break
        used = used & keep
    return {"zp": zp, "mean": mean, "resid": np.where(w > 0, m - mean - zp[:, None], np.nan), "used": used}


def indices(resid, err):
    """{index name: per-star array} for the residual series (frames, stars)."""
    r = np.asarray(resid, float)
    e = np.asarray(err, float)
    ok = np.isfinite(r) & np.isfinite(e) & (e > 0)
    n = ok.sum(0)
    w = np.where(ok, 1 / e**2, 0.0)
    r0 = np.where(ok, r, 0.0)
    wmean = (w * r0).sum(0) / np.maximum(w.sum(0), 1e-300)
    d = np.where(ok, r - wmean, np.nan)
    wsigma = np.sqrt(np.nansum(w * d**2, 0) / np.maximum(w.sum(0), 1e-300) * n / np.maximum(n - 1, 1))
    med = np.nanmedian(r, 0)
    mad = 1.4826 * np.nanmedian(np.abs(r - med), 0)
    q75, q25 = np.nanpercentile(r, [75, 25], axis=0)
    var = np.nanvar(r, 0, ddof=1)
    step = np.nanmean(np.diff(r, axis=0) ** 2, 0)  # NaN pairs left out; frames in time order
    inv_eta = var / np.maximum(step, 1e-300)  # 1/η: large for smooth variations
    delta = np.sqrt(n / np.maximum(n - 1, 1)) * d / e  # Stetson's normalised residuals
    pk = delta[:-1] * delta[1:]  # consecutive pairs
    stetson_j = np.nanmean(np.sign(pk) * np.sqrt(np.abs(pk)), 0)
    stetson_k = np.nanmean(np.abs(delta), 0) / np.sqrt(np.nanmean(delta**2, 0))
    chi2 = np.nansum((d / e) ** 2, 0) / np.maximum(n - 1, 1)
    return {"wsigma": wsigma, "mad": mad, "iqr": q75 - q25, "inv_eta": inv_eta, "stetson_j": stetson_j,
            "stetson_k": stetson_k, "chi2": chi2, "n": n}  # fmt: skip


def _robust_z(mean, value, window=101):
    """How many robust σ each star's value lies above the running median of the stars nearest in brightness."""
    order = np.argsort(mean)
    v = np.asarray(value, float)[order]
    z = np.full(len(v), np.nan)
    half = window // 2
    for k in range(len(v)):
        near = v[max(0, k - half) : k + half + 1]
        near = near[np.isfinite(near)]
        if len(near) < 5:
            continue
        centre = np.median(near)
        spread = 1.4826 * np.median(np.abs(near - centre))
        z[k] = (v[k] - centre) / max(spread, 1e-12)
    out = np.empty_like(z)
    out[order] = z
    return out


def candidates(mean, idx, nsigma=5.0, needed=2):
    """{"candidate": bool per star, "z": {index: robust σ above its brightness's typical value}, "count"}."""
    z = {k: _robust_z(mean, idx[k]) for k in SELECT}
    count = np.sum([np.nan_to_num(z[k]) > nsigma for k in SELECT], axis=0)
    return {"candidate": count >= needed, "z": z, "count": count}


def search(mag, err, nsigma=5.0):
    """ensemble → indices → candidates in one call; the stars ordered by how many indices flag them."""
    ens = ensemble(mag, err)
    idx = indices(ens["resid"], err)
    cand = candidates(ens["mean"], idx, nsigma)
    return ens | {"indices": idx} | cand
