"""The plots of the Spectroscopy tabs as FigureSpecs (ARC-6): plain data in, a figure description out, so that the
window (PlotView) and the publication output draw the same thing. Texts keep the context of the tab they belong to."""

import numpy as np
from PySide6.QtCore import QCoreApplication

from .kit import tokens
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate
RED, GREY, ORANGE = tokens.role("saturated"), tokens.role("rejected"), tokens.role("non_linear")


def _line(name, x, y, **kw):
    return SeriesSpec(name, x, y, kind="line", **{"width": 0.7, **kw})


def _one(x, y, series, title=""):
    return FigureSpec([PanelSpec(AxisSpec(x), AxisSpec(y), series)], title=title)


def _arc_labels(atlas, top):
    return SeriesSpec(
        translate("ReduceTab", "line list"), [p for p, _ in atlas], np.full(len(atlas), top), kind="text",
        labels=[f"{w:.2f}" for _, w in atlas], angle=90, colour=tokens.SERIES[0],
    )  # fmt: skip


def reduce_figure(s, atlas):
    """(figure, index of the arc panel or None, the residual points or None) of an extraction result `s`; atlas:
    [(pixel, wavelength)] of the arc peaks that the identified lines name."""
    lines = (s.get("solution") or {}).get("lines") or []
    x = s["wave"] if s["wave"] is not None else s["pixel"]
    panels = [
        PanelSpec(
            AxisSpec(
                translate("ReduceTab", "Wavelength (Å)") if s["wave"] is not None else translate("ReduceTab", "Pixel")
            ),
            AxisSpec(translate("ReduceTab", "Flux")),
            [_line(translate("ReduceTab", "Flux"), x, s["flux"])],
        )
    ]
    arc_panel = points = None
    if s.get("arc"):
        arc = [
            _line(translate("ReduceTab", "Arc"), s["pixel"], s["arc"], colour=GREY),
            SeriesSpec(translate("ReduceTab", "peaks"), s["arc_peaks"], kind="vline", width=0.5, colour=ORANGE),
        ]
        if atlas:
            arc.append(_arc_labels(atlas, float(np.nanmax(s["arc"]))))
        panels.append(
            PanelSpec(AxisSpec(translate("ReduceTab", "Pixel (click a line to identify it)")), AxisSpec(""), arc)
        )
        arc_panel = len(panels) - 1
    if lines:  # the fit line by line, as IRAF identify shows it after 'f'
        points = np.asarray(lines, float)
        res = SeriesSpec(
            translate("ReduceTab", "Residual (mÅ)"), points[:, 0], points[:, 2] * 1000, pickable=True, size=5
        )
        zero = SeriesSpec("0", [0.0], kind="hline", width=0.5, colour=GREY)
        panels.append(
            PanelSpec(
                AxisSpec(translate("ReduceTab", "Pixel (click a point to leave that arc line out)")),
                AxisSpec(translate("ReduceTab", "Residual (mÅ)")),
                [res, zero],
            )
        )
    return FigureSpec(panels, shared_x=False), arc_panel, points


def telluric_figure(r):
    before = _line(translate("TelluricTab", "before"), r["wave"], r["flux"], width=0.6, colour=GREY)
    top = PanelSpec(
        AxisSpec(""),
        AxisSpec(translate("TelluricTab", "Flux")),
        [before, _line(translate("TelluricTab", "corrected"), r["wave"], r["corrected"], width=0.6)],
    )
    trans = _line(translate("TelluricTab", "Transmission"), r["wave"], r["transmission"], width=0.6)
    return FigureSpec(
        [
            top,
            PanelSpec(
                AxisSpec(translate("TelluricTab", "Wavelength (Å)")),
                AxisSpec(translate("TelluricTab", "Transmission")),
                [trans],
            ),
        ]
    )


def profile_figure(row, p, t1, t2):
    """The correlation (or broadening function) of one spectrum, the velocity read from it marked."""
    v = np.asarray(p["v"], float)
    names = {
        "ccf": translate("VelocityTab", "Cross-correlation"),
        "bf": translate("VelocityTab", "Broadening function"),
        "todcor": "TODCOR",
    }
    series = [
        _line(
            names[p["kind"]] + (" — " + translate("VelocityTab", "star 1") if "y2" in p else ""),
            v + t1,
            p["y"],
            width=0.9,
        )
    ]
    if "y2" in p:
        series.append(_line("TODCOR — " + translate("VelocityTab", "star 2"), v + t2, p["y2"], width=0.9))
    if p.get("model") is not None:
        series.append(
            _line(translate("VelocityTab", "fitted rotational profiles"), v + t1, p["model"], dash="dash", width=0.8)
        )
    series.append(SeriesSpec("RV", [row["rv_obs"]], kind="vline", colour=RED, width=0.8))
    if row.get("rv2_obs") is not None:
        series.append(SeriesSpec("RV 2", [row["rv2_obs"]], kind="vline", colour=RED, width=0.8, dash="dot"))
    figure = _one(
        translate("VelocityTab", "Velocity, before the barycentric correction (km/s)"),
        translate("VelocityTab", "Correlation"),
        series,
        row["file"],
    )
    return figure


def mk_figure(model, mk_type):
    """The star over the best MK standard (where both have data)."""
    star = np.asarray(model["star"], float)
    standard = np.asarray(model["model"], float)
    standard = np.where(np.isfinite(star) & (standard > 0), standard, np.nan)
    series = [
        _line(translate("VelocityTab", "this star"), model["wave"], star, width=0.8),
        _line(mk_type, model["wave"], standard, width=0.8, colour=RED),
    ]
    return _one(
        translate("VelocityTab", "Wavelength (Å)"),
        translate("VelocityTab", "Relative flux"),
        series,
        translate("VelocityTab", "The star over the best MK standard"),
    )


def components_figure(c):
    series = [
        _line(translate("VelocityTab", "Star 1"), c["wave"], c["star1"]),
        _line(translate("VelocityTab", "Star 2 (shifted down by 0.5)"), c["wave"], np.asarray(c["star2"]) - 0.5),
    ]
    return _one(translate("VelocityTab", "Wavelength (Å)"), translate("VelocityTab", "Flux"), series)


def orbit_figure(o, obs, obs2=None):
    """Velocities with the orbit above, residuals below (the usual figure of an orbit paper); obs, obs2: (t, v, e)
    of the primary and, for an SB2, of the secondary."""
    from ..spectroscopy.orbit import rv_model

    args = (o["period"], o["t_peri"], o["e"])
    ph = np.linspace(0, 1, 400)

    def curves(k, omega, data, name, colour, symbol):
        time, v, e = data
        phase = ((time - o["t_peri"]) / o["period"]) % 1
        model = rv_model(o["t_peri"] + ph * o["period"], *args, omega, k, o["gamma"])
        resid = v - rv_model(time, *args, omega, k, o["gamma"])
        points = SeriesSpec(name, phase, v, yerr=e, symbol=symbol, colour=colour)
        curve = _line(name + " model", ph, model, width=1.0, colour=colour or RED)
        return [points, curve], SeriesSpec(name + " O−C", phase, resid, yerr=e, symbol=symbol, size=3, colour=colour)

    top = [SeriesSpec("γ", [o["gamma"]], kind="hline", colour=GREY, width=0.6, dash="dot")]
    first, resid = curves(o["k"], o["omega"], obs, translate("VelocityTab", "primary"), None, "o")
    top, bottom = top + first, [resid]
    if obs2 is not None:
        second, resid2 = curves(
            o["k2"], o["omega"] + 180, obs2, translate("VelocityTab", "secondary"), tokens.SERIES[1], "s"
        )
        top, bottom = top + second, bottom + [resid2]
    bottom.append(SeriesSpec("0", [0.0], kind="hline", colour=GREY, width=0.6))
    phase = AxisSpec(translate("VelocityTab", "Phase (from periastron)"), limits=(0, 1))
    return FigureSpec(
        [
            PanelSpec(phase, AxisSpec(translate("VelocityTab", "RV (km/s)")), top, height_ratio=3),
            PanelSpec(phase, AxisSpec(translate("VelocityTab", "O−C (km/s)")), bottom),
        ]
    )


def cube_figure(wave, flux, x, y):
    title = translate("CubeTab", "Spaxel {x:.0f}, {y:.0f}").format(x=x, y=y)
    return _one(
        translate("CubeTab", "Wavelength (Å)"),
        translate("CubeTab", "Flux"),
        [_line(translate("CubeTab", "Flux"), wave, flux)],
        title,
    )


def spectrum_figure(wave, flux, last, points, markers):
    """The Spectrum tools plot: the spectrum, the last measurement's continuum and fit, the continuum points picked
    (dotted lines) and, as `markers` {name: wavelength}, the line markers with rotated names."""
    series = []
    if wave is not None:
        series.append(_line(translate("SpectrumToolsTab", "Flux"), wave, flux))
        if last:
            series.append(
                _line(
                    translate("SpectrumToolsTab", "continuum"),
                    last["wave"],
                    last["continuum"],
                    dash="dash",
                    colour=tokens.SERIES[2],
                    width=0.8,
                )
            )
            series.append(
                _line(translate("SpectrumToolsTab", "fit"), last["wave"], last["model"], width=0.9, colour=RED)
            )
        if points:
            series.append(
                SeriesSpec(
                    translate("SpectrumToolsTab", "continuum points"),
                    points,
                    kind="vline",
                    dash="dot",
                    width=0.6,
                    colour=ORANGE,
                )
            )
        if markers:
            at = list(markers.values())
            series.append(
                SeriesSpec(translate("SpectrumToolsTab", "lines"), at, kind="vline", width=0.5, alpha=0.7, colour=GREY)
            )
            top = np.full(len(at), float(np.nanmax(flux)))
            series.append(
                SeriesSpec(
                    translate("SpectrumToolsTab", "line names"),
                    at,
                    top,
                    kind="text",
                    labels=list(markers),
                    angle=90,
                    colour=GREY,
                )
            )
    return _one(translate("SpectrumToolsTab", "Wavelength (Å)"), translate("SpectrumToolsTab", "Flux"), series)


def atmosphere_figure(p):
    series = [
        _line(translate("SpectrumToolsTab", "observed"), p["wave"], p["flux"], width=0.6),
        _line(translate("SpectrumToolsTab", "model"), p["wave"], p["model"], width=0.6, colour=RED),
    ]
    return _one(translate("SpectrumToolsTab", "Wavelength (Å)"), "", series)
