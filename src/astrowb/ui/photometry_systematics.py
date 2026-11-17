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
DEFAULT_TERMS = inspect.signature(sy.sysrem).parameters["n_terms"].default


def field_mags(raw):
    """(stars, frames) magnitudes of the measured field stars (comparison and check stars), or None."""
    cols = [np.asarray(raw[k], float).reshape(len(raw["time"]), -1) for k in ("comp_flux", "extra_flux") if raw.get(k)]
    if not cols:
        return None
    flux = np.hstack(cols).T
    with np.errstate(all="ignore"):
        flux = flux / np.nanmedian(flux, axis=0, keepdims=True)
        return -2.5 * np.log10(np.where(flux > 0, flux, np.nan))


def remove_trends(rel, field, method, n_terms):
    """The target's relative flux with the field's shared trends removed."""
    with np.errstate(all="ignore"):
        y = -2.5 * np.log10(np.where(np.asarray(rel, float) > 0, rel, np.nan))
    if method == "pca":
        out, _ = sy.correct(y, field, max_terms=n_terms)
    else:  # the target is not in the fit of the terms: it cannot lend them its own signal
        _, terms = sy.sysrem(field, n_terms=n_terms)
        out = sy.tfa(y, np.array([a for _, a in terms]))
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
    field = field_mags(raw)
    n = 0 if field is None else len(field)
    box = page.field_box
    cfg = page.field_cfg
    for w, state in ((box, cfg is not None), (page.field_method, None), (page.field_terms, None)):
        w.blockSignals(True)
        if state is not None:
            w.setChecked(state)
    if cfg:
        page.field_method.setCurrentIndex(0 if cfg[0] == "sysrem" else 1)
        page.field_terms.setValue(cfg[1])
    for w in (box, page.field_method, page.field_terms):
        w.blockSignals(False)
        w.setEnabled(n >= MIN_STARS)
    lc.pop("field_trends", None)
    text = translate("PhotometryPage", "Needs at least {n} measured field stars ({have} now).").format(
        n=MIN_STARS, have=n
    )
    if n >= MIN_STARS:
        text = ""
    if cfg and n >= MIN_STARS:
        share = kept_share(lc["time"], lc["rel_flux"], field, *cfg)
        lc["rel_flux"] = remove_trends(lc["rel_flux"], field, *cfg).tolist()
        lc["field_trends"] = {"method": cfg[0], "terms": cfg[1], "stars": n, "kept": share}
        text = translate("PhotometryPage", "{n} field stars; a 1 % dip would be reduced to {d:.2f} %.").format(
            n=n, d=100 * 0.01 * share
        )
    page.field_note.setText(text)


def _changed(page):
    method = "sysrem" if page.field_method.currentIndex() == 0 else "pca"
    cfg = (method, page.field_terms.value()) if page.field_box.isChecked() else None
    page.edit(translate("PhotometryPage", "trends of the field stars"), _set, page, cfg)


def _set(page, cfg):
    page.field_cfg = cfg
    if page.lc_raw is not None:
        page._recompute()


def add_controls(page, layout):
    """The tick box, method and number of terms, and the note, below the detrending buttons."""
    page.field_cfg = None
    page.field_box = QCheckBox(translate("PhotometryPage", "Remove trends shared with the field stars"), page)
    page.field_box.setToolTip(
        translate(
            "PhotometryPage",
            "The trends that the measured comparison and check stars share (airmass, clouds, focus) are fitted "
            "and taken out of the target; untick to get the light curve back",
        )
    )
    page.field_method = QComboBox(page)
    page.field_method.addItems(["SysRem", translate("PhotometryPage", "PCA (terms by BIC)")])
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
