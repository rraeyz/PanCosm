"""The exact transit model in the Photometry window's Timing stage (plans/photometry.md PHO-26): one button runs
photometry.transit_fit on the measured light curve, with the period typed beside the ephemeris and the detrending
against airmass when the light curve has it; the result names the mid-time, depth, durations, a/R★, b and the
fit's quality."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

from . import photometry_neb

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
             rho=d["rho_star"], chi2r=out["chi2r"], rms=out["rms_ppt"], beta=out["beta"]) + _mcmc_text(out)  # fmt: skip


def _mcmc_text(out):
    m = out.get("mcmc")
    if not m:
        return ""
    p = m["params"]
    digits = {"tc": 6}
    parts = [f"{n} {p[n][0]:.{digits.get(n, 4)}f} −{p[n][1]:.{digits.get(n, 4)}f} +{p[n][2]:.{digits.get(n, 4)}f}"
             for n in ("tc", "k", "a_rs", "b") if n in p]  # fmt: skip
    note = "" if m["converged"] else " " + translate("PhotometryTransit", "(not converged: more steps)")
    return "\n" + translate("PhotometryTransit", "MCMC: {values}.").format(values="; ".join(parts)) + note


def add_archive_button(main, page, layout):
    """PHO-26 archive fill: the planet's period, T0 and the fit's starting k, a/R★, b from the NASA Exoplanet
    Archive (step planning.ephemeris); the name asked, the files' OBJECT offered."""
    from PySide6.QtWidgets import QInputDialog

    page.archive_button = QPushButton(translate("PhotometryTransit", "From the NASA archive…"), page)
    page.archive_button.setToolTip(
        translate("PhotometryTransit", "Period and T0 into the Timing fields, Rp/R★, a/R★ and b as the fit's start")
    )

    def ask():
        obj = ((page.field or {}).get("object") or {}).get("name", "")
        title = translate("PhotometryTransit", "NASA Exoplanet Archive")
        name, ok = QInputDialog.getText(
            page, title, translate("PhotometryTransit", "Planet, e.g. Qatar-1 b:"), text=obj
        )
        if ok and name.strip():
            page.transit_result.setText(translate("PhotometryTransit", "Asking the NASA Exoplanet Archive…"))
            main.run_step_for("photometry", "planning.ephemeris", {"name": name.strip()}, {"catalogue": "exoplanet"},
                              on_done=lambda out: fill(page, out["target"]),
                              on_fail=lambda msg: page.transit_result.setText(message(msg)))  # fmt: skip

    from .messages import translate as message

    page.archive_button.clicked.connect(ask)
    layout.addWidget(page.archive_button)


def fill(page, target):
    page.archive = target
    if target.get("period"):
        page.period.setText(repr(float(target["period"])))
    if target.get("t0"):
        page.t0.setText(repr(float(target["t0"])))
    known = ", ".join(f"{n} {target[k]:g}" for k, n in (("k", "Rp/R★"), ("a_rs", "a/R★"), ("b", "b")) if k in target)
    page.transit_result.setText(
        translate("PhotometryTransit", "{name}: period and T0 filled; the fit starts from {known}.").format(
            name=target.get("name", ""), known=known or "—"
        )
    )


def add_oc_button(main, page, box, lay):
    """ "Add the times to the O−C list": the times of minimum and the transit mid-time, by hand (UI-20)."""
    page.to_oc_button = QPushButton(translate("PhotometryTransit", "Add the times to the O−C list"), box)
    page.to_oc_button.setToolTip(
        translate("PhotometryTransit", "The times of minimum and the transit mid-time measured here, into O−C")
    )

    def to_oc():
        oc = getattr(main, "oc_page", None)
        rows = [(x["time"], x["error"], "this work", x.get("kind", "I")) for x in getattr(page, "last_minima", [])]
        if getattr(page, "transit_fit", None):
            fit = page.transit_fit[1]
            rows.append((fit["values"]["tc"], fit["errors"].get("tc", 0.0), "this work (transit fit)", "I"))
        for row in rows if oc is not None else ():
            oc.add_minimum(*row)
        page.transit_result.setText(
            translate("PhotometryTransit", "{n} times added to the O−C list.").format(n=len(rows))
        )

    page.to_oc_button.clicked.connect(to_oc)
    lay.addWidget(page.to_oc_button)


def add_mcmc_box(page, layout):
    from PySide6.QtWidgets import QCheckBox

    page.transit_mcmc = QCheckBox(translate("PhotometryTransit", "MCMC uncertainties (slower)"), page)
    page.transit_mcmc.setToolTip(
        translate("PhotometryTransit", "After the fit, Markov chains give each parameter's 68 % interval; correlated "
                  "parameters (a/R★ and b) get honest, one-sided errors. Scale the errors first if they are too small.")
    )  # fmt: skip
    layout.addWidget(page.transit_mcmc)


def details_dialog(page, lc, out):
    """The fitted parameters with their errors, and the curve with the model and the residuals below it."""
    from .kit.dialogs import Dialog
    from .kit.table_view import DataTable
    from .kit.widgets import PlotCanvas

    d = Dialog(translate("PhotometryTransit", "Transit fit"), page, getattr(page, "settings", None), "transit_fit")
    table = DataTable(d)
    v, e = out["values"], out["errors"]
    rows = [[k, v[k], e[k] if k in e else translate("PhotometryTransit", "fixed")] for k in v]
    rows += [[k, val, ""] for k, val in out["derived"].items()]
    rows += [[k, out[k], ""] for k in ("chi2r", "bic", "rms_ppt", "beta")]
    table.set_data([translate("PhotometryTransit", "Parameter"), translate("PhotometryTransit", "Value"),
                    translate("PhotometryTransit", "Error")], rows)  # fmt: skip
    plot = PlotCanvas(d)
    t = np.asarray(lc["time"], float)
    f, m = np.asarray(lc["rel_flux"], float), np.asarray(out["model"], float)
    base = v["baseline"]
    top, bottom = plot.figure.subplots(2, 1, sharex=True, height_ratios=(3, 1))
    top.plot(t - t[0], f / base, ".", ms=3, alpha=0.6, label=translate("PhotometryTransit", "measured"))
    top.plot(t - t[0], m / base, "-", lw=1.5, label=translate("PhotometryTransit", "model"))
    top.set_ylabel(translate("PhotometryTransit", "Relative flux"))
    top.legend()
    bottom.plot(t - t[0], (f - m) / base * 1000, ".", ms=3)
    bottom.axhline(0, lw=0.8, color="0.5")
    bottom.set_ylabel(translate("PhotometryTransit", "O − C (ppt)"))
    bottom.set_xlabel(translate("PhotometryTransit", "Days from {t0:.5f}").format(t0=t[0]))
    plot.draw()
    d.body.addWidget(plot, 3)
    d.body.addWidget(table, 2)
    d.add_buttons(translate("PhotometryTransit", "Close")).setDefault(True)
    d.resize(max(d.width(), 760), max(d.height(), 640))
    return d


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
    page.transit_details = QPushButton(translate("PhotometryTransit", "Parameters and plot…"), box)
    page.transit_details.setEnabled(False)
    add_archive_button(main, page, lay)
    lay.addWidget(page.transit_button)
    add_mcmc_box(page, lay)
    lay.addWidget(page.transit_result)
    lay.addWidget(page.transit_details)

    def done(out):
        page.transit_fit = (page.light_curve, out["transit"])
        if getattr(page, "checks", None) is not None:  # the next-night advice can now judge the cadence
            page.checks.show_checks(page.light_curve)
        page.transit_result.setText(result_text(out["transit"]))
        page.transit_details.setEnabled(True)
        from . import automatic

        oc = getattr(main, "oc_page", None)
        if oc is not None and automatic.on("oc.take_minima"):  # ready for the O−C diagram, as the times of minimum
            fit = out["transit"]
            oc.add_minimum(fit["values"]["tc"], fit["errors"].get("tc", 0.0), "this work (transit fit)", "I")

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
        known = getattr(page, "archive", None) or {}
        params = {"period": period, "tc": tc, "k": known.get("k", k), "detrend": "airmass" if lc.get("airmass") else "",
                  "mcmc_steps": 5000 if page.transit_mcmc.isChecked() else 0}  # fmt: skip
        params |= {n: known[n] for n in ("a_rs", "b") if n in known}  # the archive's values as the start
        page.transit_result.setText(translate("PhotometryTransit", "Fitting the transit…"))
        main.run_step_for("photometry", "photometry.transit_fit", {"light_curve": lc}, params,
                          on_done=done,
                          on_fail=lambda msg: page.transit_result.setText(message(msg)))  # fmt: skip

    from .messages import translate as message

    page.transit_button.clicked.connect(run)
    add_oc_button(main, page, box, lay)
    photometry_neb.add(main, page, lay)
    page.transit_details.clicked.connect(lambda: details_dialog(page, *page.transit_fit).exec())
    page.minimum_button.parentWidget().layout().insertWidget(
        page.minimum_button.parentWidget().layout().indexOf(page.minimum_button) + 1, box
    )
    return box
