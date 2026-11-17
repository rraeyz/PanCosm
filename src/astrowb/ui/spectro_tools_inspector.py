"""The Spectrum tools' lines table in the Spectroscopy inspector (plans/interface.md UI-16.3): the chosen measured
line with what its result holds, and a small plot of the fitted profile (the result keeps the fitted curve and the
continuum over the window, not the fitted parameters of a profile object) with the data around the line when the
measuring page kept them. Nothing is computed here but a lookup."""

import numpy as np
from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from . import spectro_figures
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("SpectroscopyWindow", "…") calls

# (name, result key, its error key, unit)
_FIELDS = (
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "Centre"), "centre", "centre_err", "Å"),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "FWHM"), "fwhm", "fwhm_err", "Å"),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "EW"), "ew", "ew_err", "Å"),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "EW of fit"), "ew_fit", None, "Å"),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "Depth"), "depth", "depth_err", ""),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "Line flux"), "line_flux", None, ""),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "S/N"), "snr", None, ""),
    (QT_TRANSLATE_NOOP("SpectroscopyWindow", "V/R"), "v_over_r", None, ""),
)


def window_data(wave, flux, m):
    """(wave, flux) of the spectrum inside the measured window, kept with the row so the plot needs no recompute."""
    w, f = np.asarray(wave, float), np.asarray(flux, float)
    keep = (w >= m["lo"]) & (w <= m["hi"])
    return w[keep].tolist(), f[keep].tolist()


def tool_rows(label, m):
    """[(name, value, unit)]: the file, then every value the measurement result holds for it."""
    rows = [(translate("SpectroscopyWindow", "File / date"), label, "")]
    for name, key, err, unit in _FIELDS:
        if m.get(key) is not None:
            value = m[key]
            shown = translate("SpectroscopyWindow", name)
            rows.append((shown, value, unit))
            if err and m.get(err) is not None:
                rows.append((translate("SpectroscopyWindow", "σ {name}").format(name=shown), m[err], unit))
    rows.append((translate("SpectroscopyWindow", "Profile"), m.get("profile"), ""))
    rows.append((translate("SpectroscopyWindow", "Window"), f"{m['lo']:.2f}–{m['hi']:.2f}", "Å"))
    return rows


def tool_plot(panel, m, data):
    """Fill the small plot of `panel` (made on first use): data around the line, the continuum and the fitted curve."""
    if getattr(panel, "tool_plot", None) is None:
        box, panel.tool_plot = plot_box(panel)
        box.setMinimumHeight(150)
        panel.layout().insertWidget(panel.layout().count() - 1, box)
        panel.tool_plot_box = box
    panel.tool_plot_box.show()
    wave, flux = data or (m["wave"], [np.nan] * len(m["wave"]))  # no data kept: the fitted curve alone
    panel.tool_plot.set_figure(spectro_figures.spectrum_figure(wave, flux, m, [], {}))
