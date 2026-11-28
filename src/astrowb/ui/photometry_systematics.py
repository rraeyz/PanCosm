"""Light curve stage: "Remove trends shared with the field stars" (plans/photometry.md PHO-31).

The measured comparison and check stars are the field; their flux (each frame divided by the frame's median over
the stars) gives the shared trends, found by SysRem or by the PCA basis with BIC terms, and removed from the
target's light curve. The cost is shown: how much of an injected 1 % dip the same correction would keep.
"""

import inspect

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox

from ..photometry import systematics as sy

translate = QCoreApplication.translate
MIN_STARS = 30  # fewer stars give trends that are mostly the target's own noise
METHODS = ("sysrem", "pca", "tfa")
DEFAULT_TERMS = inspect.signature(sy.sysrem).parameters["n_terms"].default


def _whole_field(whole, time, target):
    """(stars, frames) magnitudes of the whole-field measurement (PHO-30) on the light curve's frames, without the
    target, the candidate variables and the stars seen on fewer than 80 % of the frames; None when the frames differ."""
    f, v = whole["field"], whole["variability"]
    t = np.asarray(f["time"], float)
    idx = np.searchsorted(t, np.asarray(time, float))
    idx = np.minimum(idx, len(t) - 1)
    if len(t) == 0 or not np.allclose(t[idx], time, rtol=0, atol=1e-5):  # a second
        return None
    mag = np.asarray(f["mag"], float)[idx]
    keep = np.isfinite(mag).mean(0) > 0.8
    keep &= ~np.asarray(v.get("candidate", np.zeros(mag.shape[1])), bool)
    if target is not None:
        keep &= np.hypot(*(np.asarray(f["xy"], float) - target).T) > 5.0  # pixels
    return (mag - np.nanmedian(mag[:, keep], axis=1, keepdims=True)).T[keep]


def field_mags(raw, whole=None, target=None):
    """((stars, frames) magnitudes of the field, its name) or (None, ""): the whole-field measurement when there is
    one that fits the light curve's frames, else the measured comparison and check stars."""
    if whole:
        mags = _whole_field(whole, raw["time"], target)
        if mags is not None:
            return mags, translate("PhotometryPage", "whole-field")
    cols = [np.asarray(raw[k], float).reshape(len(raw["time"]), -1) for k in ("comp_flux", "extra_flux") if raw.get(k)]
    if not cols:
        return None, ""
    flux = np.hstack(cols).T
    with np.errstate(all="ignore"):
        flux = flux / np.nanmedian(flux, axis=0, keepdims=True)
        return -2.5 * np.log10(np.where(flux > 0, flux, np.nan)), translate("PhotometryPage", "comparison and check")


def fitted_signal(page, lc):
    """The Timing and fit stage's transit model alone (no baseline, no airmass trend) as magnitudes on lc's frames,
    or None when there is no fit of these frames: the trends are then fitted on the rest and keep the dip's depth."""
    from ..photometry.transitfit import NAMES

    fit_lc, out = getattr(page, "transit_fit", None) or (None, None)
    t = np.asarray(lc["time"], float)
    if out is None or len(out["model"]) != len(t) or not np.allclose(fit_lc["time"], t, rtol=0, atol=1e-6):
        return None
    v = out["values"]
    shape = np.asarray(out["model"], float) / v["baseline"]
    for k in set(v) - set(NAMES):  # the trend fitted with it, normalised as transitfit.fit does
        z = np.asarray(fit_lc[k], float)
        shape = shape / np.exp(v[k] * (z - z.mean()) / (z.std() or 1.0))
    return -2.5 * np.log10(shape)


def remove_trends(rel, field, method, n_terms, fixed=None):
    """The target's relative flux with the field's shared trends removed; fixed: its known signal (magnitudes)."""
    with np.errstate(all="ignore"):
        y = -2.5 * np.log10(np.where(np.asarray(rel, float) > 0, rel, np.nan))
    if method == "pca":
        out, _ = sy.correct(y, field, max_terms=n_terms, fixed=fixed)
    elif method == "tfa":  # the engine's defaults: the field stars themselves are the templates
        out = sy.tfa(y, field, fixed=fixed)
    else:  # the target is not in the fit of the terms: it cannot lend them its own signal
        _, terms = sy.sysrem(field, n_terms=n_terms)
        out = sy.tfa(y, np.array([a for _, a in terms]), fixed=fixed)
    return 10 ** (-0.4 * out)


def kept_share(time, rel, field, method, n_terms, depth=0.01):
    """The share of an injected dip of `depth` (a tenth of the night long) that the correction leaves."""
    time = np.asarray(time, float)
    dip = sy.box(time, np.median(time), 0.1 * (time.max() - time.min()), depth)
    base = remove_trends(rel, field, method, n_terms)
    hit = remove_trends(np.asarray(rel, float) * 10 ** (-0.4 * dip), field, method, n_terms)
    change = -2.5 * np.log10(hit / base)
    inside = dip > 0
    return float((np.nanmean(change[inside]) - np.nanmean(change[~inside])) / depth)


def apply(page, lc, raw):
    """Called by the page's _recompute: syncs the controls and, when ticked, replaces lc's relative flux."""
    field, which = field_mags(raw, page.field_source(), page.target)
    n = 0 if field is None else len(field)
    box = page.field_box
    cfg = page.field_cfg
    for w, state in ((box, cfg is not None), (page.field_method, None), (page.field_terms, None)):
        w.blockSignals(True)
        if state is not None:
            w.setChecked(state)
    if cfg:
        page.field_method.setCurrentIndex(METHODS.index(cfg[0]))
        page.field_terms.setValue(cfg[1])
    for w in (box, page.field_method, page.field_terms):
        w.blockSignals(False)
        w.setEnabled(n >= MIN_STARS)
    lc.pop("field_trends", None)
    text = translate("PhotometryPage", "Needs at least {n} measured field stars ({have} now).").format(
        n=MIN_STARS, have=n
    )
    page.field_terms.setEnabled(n >= MIN_STARS and (cfg or ("",))[0] != "tfa")
    if n >= MIN_STARS:
        text = ""
    if cfg and n >= MIN_STARS:
        fixed = fitted_signal(page, lc)
        share = None if fixed is not None else kept_share(lc["time"], lc["rel_flux"], field, *cfg)
        lc["rel_flux"] = remove_trends(lc["rel_flux"], field, *cfg, fixed=fixed).tolist()
        lc["field_trends"] = {"method": cfg[0], "terms": cfg[1], "stars": n, "kept": share}
        if fixed is not None:
            text = translate(
                "PhotometryPage", "{n} field stars ({which}); the fitted transit is kept out of the trends' fit."
            ).format(n=n, which=which)
        else:
            text = translate(
                "PhotometryPage", "{n} field stars ({which}); a 1 % dip would be reduced to {d:.2f} %."
            ).format(n=n, which=which, d=100 * 0.01 * share)
    page.field_note.setText(text)


def _changed(page):
    method = METHODS[page.field_method.currentIndex()]
    cfg = (method, page.field_terms.value()) if page.field_box.isChecked() else None
    page.edit(translate("PhotometryPage", "trends of the field stars"), _set, page, cfg)


def _set(page, cfg):
    page.field_cfg = cfg
    if page.lc_raw is not None:
        page._recompute()


def add_controls(page, layout):
    """The tick box, method and number of terms, and the note, below the detrending buttons."""
    page.field_cfg = None
    page.field_source = lambda: None  # the window sets it: the whole-field search result (PHO-30), if there is one
    page.field_box = QCheckBox(translate("PhotometryPage", "Remove trends shared with the field stars"), page)
    page.field_box.setToolTip(
        translate(
            "PhotometryPage",
            "The trends that the measured comparison and check stars share (airmass, clouds, focus) are fitted "
            "and taken out of the target; untick to get the light curve back",
        )
    )
    page.field_method = QComboBox(page)
    page.field_method.addItems(["SysRem", translate("PhotometryPage", "PCA (terms by BIC)"), "TFA"])
    page.field_terms = QSpinBox(page)
    page.field_terms.setRange(1, 10)
    page.field_terms.setValue(DEFAULT_TERMS)
    page.field_terms.setToolTip(translate("PhotometryPage", "Number of trends removed (at most, for PCA)"))
    page.field_note = QLabel(page)
    page.field_note.setWordWrap(True)
    row = QHBoxLayout()
    for w in (page.field_box, page.field_method, page.field_terms):
        row.addWidget(w)
    layout.addLayout(row)
    layout.addWidget(page.field_note)
    page.field_box.toggled.connect(lambda _: _changed(page))
    page.field_method.currentIndexChanged.connect(lambda _: page.field_box.isChecked() and _changed(page))
    page.field_terms.valueChanged.connect(lambda _: page.field_box.isChecked() and _changed(page))
    for w in (page.field_box, page.field_method, page.field_terms):
        w.setEnabled(False)
