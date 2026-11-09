"""Trends shared by many stars of the field, removed from each (plans/photometry.md PHO-31).

    sysrem(mag, err, n_terms)            Tamuz, Mazeh & Zucker 2005 (MNRAS 356, 1466): rank-one effects c_i a_j
                                         found in turn with the errors as weights
    tfa(target, templates, err, fixed)   Kovács, Bakos & Noyes 2005 (MNRAS 356, 557): the target fitted by a few
                                         field stars' curves; with a known signal (fixed) the fit is made on the
                                         target minus the signal ("reconstruction")
    pca_basis(mag, max_terms)            the field's main shared trends, and bic_terms() to choose how many
    suppression(...)                     how much of an injected box signal survives the correction

mag: (stars, frames) magnitudes (or relative fluxes in magnitudes); each star's own mean is removed first.
"""

import numpy as np


def _centred(mag):
    mag = np.asarray(mag, float)
    return mag - np.nanmedian(mag, axis=1, keepdims=True)


def sysrem(mag, err=None, n_terms=2, iterations=20):
    """(corrected mag, [(c, a)] per term): each term is the outer product c_i a_j that best fits the residuals
    with weights 1/err², removed in turn. Missing points (NaN) keep their NaN and take no part."""
    r = _centred(mag)
    w = np.ones_like(r) if err is None else 1.0 / np.square(np.asarray(err, float))
    w = np.where(np.isfinite(r) & np.isfinite(w), w, 0.0)
    r0 = np.where(w > 0, r, 0.0)
    terms = []
    for _ in range(n_terms):
        a = np.ones(r.shape[1])
        for _ in range(iterations):
            c = (r0 * w * a).sum(1) / np.maximum((w * a * a).sum(1), 1e-300)
            a_new = (r0 * w * c[:, None]).sum(0) / np.maximum((w * c[:, None] ** 2).sum(0), 1e-300)
            done = np.allclose(a_new, a, rtol=1e-6, atol=1e-12)
            a = a_new
            if done:
                break
        r0 = r0 - np.outer(c, a) * (w > 0)
        terms.append((c, a))
    out = np.where(w > 0, r0, np.nan) + (np.asarray(mag, float) - r)  # each star's level back
    return out, terms


def pca_basis(mag, max_terms=10):
    """The field's shared trends, strongest first: (max_terms, frames), each of unit length, from the stars'
    centred curves (stars with a missing point are left out of the basis)."""
    r = _centred(mag)
    r = r[np.all(np.isfinite(r), axis=1)]
    r = r / np.maximum(r.std(axis=1, keepdims=True), 1e-12)  # every star counts alike, bright or faint
    _, _, vt = np.linalg.svd(r, full_matrices=False)
    return vt[:max_terms]


def _fit(y, basis, w, fixed=None):
    """Least-squares coefficients of basis (k, n) for y with weights w, beside a constant (not returned): the
    curve's level is no trend; fixed: a known signal left in."""
    target = y - (0.0 if fixed is None else fixed)
    ok = np.isfinite(target) & (w > 0)
    sw = np.sqrt(w[ok])
    design = np.vstack([np.ones(len(y)), basis])
    coef, *_ = np.linalg.lstsq((design[:, ok] * sw).T, target[ok] * sw, rcond=None)
    return coef[1:]


def bic_terms(y, basis, err=None, max_terms=None):
    """How many of the basis' leading vectors the curve y needs: the number with the lowest BIC."""
    y = np.asarray(y, float) - np.nanmedian(y)
    w = np.ones_like(y) if err is None else 1.0 / np.square(np.asarray(err, float))
    ok = np.isfinite(y)
    n = ok.sum()
    best, best_k = None, 0
    for k in range(0, (max_terms or len(basis)) + 1):
        model = 0.0 if k == 0 else _fit(y, basis[:k], w) @ basis[:k]
        chi2 = np.sum((w * (y - model) ** 2)[ok])
        bic = chi2 + k * np.log(n) if err is not None else n * np.log(chi2 / n) + k * np.log(n)
        if best is None or bic < best:
            best, best_k = bic, k
    return best_k


def tfa(target, templates, err=None, fixed=None):
    """The target with the shared trends of the template stars removed (Kovács et al. 2005). templates: (k, n)
    curves of field stars; fixed: the target's known signal (a fitted transit or a folded light curve) in the same
    units, so that the trends are fitted on the rest and the signal keeps its depth."""
    y = np.asarray(target, float)
    level = np.nanmedian(y)
    t = _centred(templates)
    t = np.where(np.isfinite(t), t, 0.0)
    w = np.ones_like(y) if err is None else 1.0 / np.square(np.asarray(err, float))
    coef = _fit(y - level, t, w, None if fixed is None else np.asarray(fixed, float) - np.nanmedian(fixed))
    return y - coef @ t


def correct(target, field_mag, err=None, max_terms=6, fixed=None):
    """The target's curve corrected by the field's trends: the PCA basis of the field stars, as many terms as the
    BIC asks for. Returns (corrected, number of terms)."""
    basis = pca_basis(field_mag, max_terms)
    y = np.asarray(target, float)
    k = bic_terms(y if fixed is None else y - fixed, basis, err)
    if k == 0:
        return y.copy(), 0
    w = np.ones_like(y) if err is None else 1.0 / np.square(np.asarray(err, float))
    level = np.nanmedian(y)
    coef = _fit(y - level, basis[:k], w, None if fixed is None else np.asarray(fixed, float) - np.nanmedian(fixed))
    return y - coef @ basis[:k], k


def box(time, t0, duration, depth):
    """A box-shaped dip of depth (magnitudes, positive) centred at t0."""
    return np.where(np.abs(np.asarray(time, float) - t0) < duration / 2, depth, 0.0)


def suppression(time, target, field_mag, err=None, depth=0.01, duration=None, max_terms=6, t0=None):
    """The share of an injected dip's depth that survives a blind `correct` (1.0: none lost), as "a 1 % transit
    would be reduced to 0.93 %" says it. The dip at t0 (the middle of the series), a tenth of it long by default.
    A dip that looks like one of the field's trends loses most; with the target's model given (`fixed`) nothing."""
    time = np.asarray(time, float)
    duration = duration or 0.1 * (time.max() - time.min())
    dip = box(time, np.median(time) if t0 is None else t0, duration, depth)
    before, _ = correct(target, field_mag, err, max_terms)
    after, _ = correct(np.asarray(target, float) + dip, field_mag, err, max_terms)
    inside, change = dip > 0, after - before
    return float((np.nanmean(change[inside]) - np.nanmean(change[~inside])) / depth)  # the depth as it is read
