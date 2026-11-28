"""The coefficients dialog's "Transformed magnitudes on every frame" (plans/photometry.md PHO-35): the target's
standard magnitude per frame by `photometry.transform.transformed`, from the comparison stars' catalogue magnitudes
and B − V colours (the Photometry page's Standard magnitudes look-up), the filter's colour term (this dialog's fit,
else the newest one in the profile) and the variable's colour (typed; the catalogue's when it has one)."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("CoefficientsTransform", "…") calls


def _bv(star):
    """The star's B − V, or None. shortcut: a Gaia-only entry may carry BP − RP as its colour (catalog.star_magnitude),
    so its colour is not taken; upgrade when the catalogue entry names its colour's bands."""
    source = (star or {}).get("source", "")
    if not star or star.get("colour") is None or (source.startswith("Gaia DR3") and "GSPC" not in source):
        return None
    return float(star["colour"])


def comparisons(lc, catalog):
    """(magnitudes, B − V colours) of the light curve's comparison stars, or the reason there are none (a text)."""
    if not lc or not lc.get("rel_flux"):
        return translate("CoefficientsTransform", "Measure a light curve first.")
    comps = (catalog or {}).get("comps") or []
    if len(comps) != np.asarray(lc["comp_flux"]).shape[1] or any(_bv(c) is None for c in comps):
        return translate(
            "CoefficientsTransform",
            "The light curve has no B − V colours of its comparison stars: look them up with Standard magnitudes "
            "(Report stage; the catalogue or the AAVSO chart must have their B and V magnitudes).",
        )
    return [float(c["mag"]) for c in comps], [_bv(c) for c in comps]


def coefficient(dlg, band):
    """{value, error} of the band's colour term: this dialog's fresh fit, else the profile's newest; or None."""
    from ..core import profile_coefficients

    key = f"t{band}".lower()
    fit = (dlg.result or {}).get("transformation") or {}
    if key in fit:
        return fit[key]
    found = profile_coefficients.latest(dlg.settings, band.lower()) if dlg.settings is not None else None
    return found[1] if found else None


def add(dlg, layout, catalog):
    """The tick box (disabled, with the reason as its tooltip, without the comparison colours), the colour field
    and the result line."""
    box = QGroupBox(translate("CoefficientsTransform", "Transformed magnitudes"), dlg)
    lay = QVBoxLayout(box)
    dlg.transform_box = QCheckBox(translate("CoefficientsTransform", "Transformed magnitudes on every frame"), box)
    dlg.target_colour = QLineEdit(box)
    dlg.target_colour.setPlaceholderText(translate("CoefficientsTransform", "B − V of the variable, e.g. 0.65"))
    dlg.target_colour.setToolTip(translate("CoefficientsTransform", "The variable's colour (B − V) on this night"))
    target = _bv((catalog or {}).get("target"))
    if target is not None:
        dlg.target_colour.setText(f"{target:.3f}")
    dlg.transform_note = QLabel(box)
    dlg.transform_note.setWordWrap(True)
    dlg.transformed, dlg.catalog = None, catalog
    row = QHBoxLayout()
    row.addWidget(dlg.transform_box)
    row.addWidget(dlg.target_colour)
    lay.addLayout(row)
    lay.addWidget(dlg.transform_note)
    found = comparisons(dlg.lc, catalog)
    if isinstance(found, str):
        dlg.transform_box.setEnabled(False)
        dlg.transform_box.setToolTip(found)
    else:
        dlg.transform_box.setToolTip(
            translate(
                "CoefficientsTransform", "The target's standard magnitude on each frame, with the filter's colour term"
            )
        )
    dlg.transform_box.toggled.connect(lambda on: show(dlg) if on else _clear(dlg))
    layout.addWidget(box)


def _clear(dlg):
    dlg.transformed = None
    dlg.transform_note.clear()


def show(dlg):
    """Computes and plots the transformed magnitudes; says what is missing instead (and unticks)."""
    from ..photometry.transform import transformed

    mags, colours = comparisons(dlg.lc, dlg.catalog)
    band = dlg.catalog.get("filter") or ""
    c = coefficient(dlg, band)
    text = dlg.target_colour.text().strip().replace(",", ".")
    try:
        colour = float(text)
    except ValueError:
        colour = None
    if c is None or colour is None:
        no_term = translate("CoefficientsTransform", "No colour term for {band}: fit one from a standard field "
                            "above or save one in the profile.").format(band=band)  # fmt: skip
        other = translate("CoefficientsTransform", "Type the variable's colour (B − V) first.")
        dlg.transform_note.setText(no_term if c is None else other)
        dlg.transform_box.blockSignals(True)
        dlg.transform_box.setChecked(False)
        dlg.transform_box.blockSignals(False)
        return None
    mag, err = transformed(dlg.lc, mags, colours, colour, c["value"], c.get("error", 0.0))
    dlg.transformed = {"mag": mag.tolist(), "err": err.tolist()}
    note = translate("CoefficientsTransform", "{band} on {n} frames: mean {m:.3f} (colour term {t:.4f} ± {e:.4f}, "
                                              "B − V {c:.3f}).")  # fmt: skip
    dlg.transform_note.setText(
        note.format(
            band=band,
            n=int(np.isfinite(mag).sum()),
            m=float(np.nanmean(mag)),
            t=c["value"],
            e=c.get("error", 0.0),
            c=colour,
        )  # fmt: skip
    )
    t = np.asarray(dlg.lc["time"], float)
    axes = (
        AxisSpec(translate("CoefficientsTransform", "Days from {t0:.5f}").format(t0=t[0])),
        AxisSpec(band, invert=True),
    )
    dlg.plot.set_figure(FigureSpec([PanelSpec(*axes, [SeriesSpec(band, t - t[0], mag, size=3)])]))
    return dlg.transformed
