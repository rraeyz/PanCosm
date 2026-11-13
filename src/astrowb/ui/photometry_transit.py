"""The exact transit model in the Photometry window's Timing stage (plans/photometry.md PHO-26): one button runs
photometry.transit_fit on the measured light curve, with the period typed beside the ephemeris and the detrending
against airmass when the light curve has it; the result names the mid-time, depth, durations, a/R★, b and the
fit's quality."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryTransit", "…") calls


def starts(lc):
    """Start values from the curve: the mid-time and the depth of its smoothed dip."""
    t, f = np.asarray(lc["time"], float), np.asarray(lc["rel_flux"], float)
    k = max(len(f) // 25, 3)
    smooth = np.convolve(f / np.median(f), np.ones(k) / k, mode="same")
    inner = slice(k, len(f) - k) if len(f) > 3 * k else slice(None)
    i = int(np.argmin(smooth[inner])) + (inner.start or 0)
    depth = max(1 - smooth[i], 1e-4)
    return float(t[i]), float(np.sqrt(depth))


def result_text(out):
    v, e, d = out["values"], out["errors"], out["derived"]
    from ..timeseries.oc_report import paren

    return translate(
        "PhotometryTransit",
        "Mid-transit {tc} BJD; depth {depth:.2f} ppt ({mmag:.1f} mmag); T14 {t14:.2f} h, T23 {t23:.2f} h; "
        "a/R★ {a}; b {b}; i {inc:.1f}°; ρ★ {rho:.2f} g/cm³. Reduced χ² {chi2r:.2f}, RMS {rms:.2f} ppt, β {beta:.2f}.",
    ).format(tc=paren(v["tc"], e.get("tc", 0)), depth=d["depth_ppt"], mmag=d["depth_mmag"], t14=d["t14_h"],
             t23=d["t23_h"], a=paren(v["a_rs"], e.get("a_rs", 0)), b=paren(v["b"], e.get("b", 0)), inc=d["inc"],
             rho=d["rho_star"], chi2r=out["chi2r"], rms=out["rms_ppt"], beta=out["beta"])  # fmt: skip


def attach(main, page):
    """The group under the Time of minimum button; the fit runs as a task of the Photometry window."""
    box = QGroupBox(translate("PhotometryTransit", "Exact transit model"), page)
    lay = QVBoxLayout(box)
    page.transit_button = QPushButton(translate("PhotometryTransit", "Fit the transit"), box)
    page.transit_button.setToolTip(
        translate(
            "PhotometryTransit",
            "Limb-darkened transit with a trend in airmass, fitted to the measured curve; needs the period",
        )  # fmt: skip
    )
    page.transit_result = QLabel(box)
    page.transit_result.setWordWrap(True)
    page.transit_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(page.transit_button)
    lay.addWidget(page.transit_result)

    def run():
        lc = page.light_curve
        if lc is None:
            page.transit_result.setText(translate("PhotometryTransit", "Measure the light curve first."))
            return
        try:
            period = float(page.period.text().replace(",", "."))
        except ValueError:
            page.transit_result.setText(translate("PhotometryTransit", "Type the period (d) above first."))
            return
        tc, k = starts(lc)
        params = {"period": period, "tc": tc, "k": k, "detrend": "airmass" if lc.get("airmass") else ""}
        page.transit_result.setText(translate("PhotometryTransit", "Fitting the transit…"))
        main.run_step_for("photometry", "photometry.transit_fit", {"light_curve": lc}, params,
                          on_done=lambda out: page.transit_result.setText(result_text(out["transit"])),
                          on_fail=lambda msg: page.transit_result.setText(message(msg)))  # fmt: skip

    from .messages import translate as message

    page.transit_button.clicked.connect(run)
    page.minimum_button.parentWidget().layout().insertWidget(
        page.minimum_button.parentWidget().layout().indexOf(page.minimum_button) + 1, box
    )
    return box
