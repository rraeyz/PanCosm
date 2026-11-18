"""Difference imaging in the Photometry window's Measure stage (plans/photometry.md PHO-29): a separate action next to
the measure method, the step photometry.dia_curve on the chosen images, and the flux changes in a result tab."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from .messages import translate as message
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
from .plot.view import PlotView

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryDia", "…") calls
DEFAULT_FRAMES = 5  # a UI choice for the reference, not a physical constant


def attach(win, page):
    """The button, the reference size and a line for what went wrong in the Measure stage; the result tab appears
    with the first result. The FWHM is the one the Apertures stage found (remembered when it sets the radii)."""
    panel = win.stage_panels["measure"]
    box = QWidget(panel)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    page.dia_button = QPushButton(translate("PhotometryDia", "Difference imaging (crowded field)…"), box)
    page.dia_button.setToolTip(
        translate(
            "PhotometryDia",
            "For fields too crowded for apertures and PSF fitting: the target's flux change on every frame against "
            "a reference made of the sharpest frames (needs the radii chosen first, for the FWHM)",
        )
    )
    page.dia_frames = QSpinBox(box)
    page.dia_frames.setRange(1, 999)
    page.dia_frames.setValue(DEFAULT_FRAMES)
    page.dia_frames.setToolTip(translate("PhotometryDia", "How many of the sharpest frames make the reference"))
    page.dia_note = QLabel(box)
    page.dia_note.setWordWrap(True)
    page.dia_note.setProperty("muted", True)
    for w in (page.dia_button, QLabel(translate("PhotometryDia", "Frames in the reference"), box), page.dia_frames,
              page.dia_note):  # fmt: skip
        lay.addWidget(w)
    panel.add(box)
    page.dia_button.clicked.connect(lambda: run(win, page))
    show_radii = page.show_apertures

    def remember(a):
        show_radii(a)
        page._dia_fwhm = float(a["fwhm"])

    page.show_apertures = remember


def run(win, page):
    say = page.dia_note.setText
    frames = page._series() if page.images else []
    if not (frames and page.target is not None):
        return say(translate("PhotometryDia", "Choose the images and mark the target first."))
    if len(frames) < 2:
        return say(translate("PhotometryDia", "Difference imaging needs at least two frames."))
    fwhm = getattr(page, "_dia_fwhm", None)
    if not fwhm:
        return say(translate("PhotometryDia", "Choose the radii from the star profiles first: they give the FWHM."))
    n_best = min(page.dia_frames.value(), len(frames))
    page.dia_frames.setValue(n_best)
    say(translate("PhotometryDia", "Making the reference and measuring {n} frames…").format(n=len(frames)))
    win.parent().run_step_for("photometry", "photometry.dia_curve",
                              {"images": frames, "target_xy": list(page.target)}, {"n_best": n_best, "fwhm": fwhm},
                              on_done=lambda out: show(win, page, out["dia"]),
                              on_fail=lambda msg: say(message(msg)))  # fmt: skip


def show(win, page, dia):
    """The result tab (made on first use): the flux change against time, with errors."""
    try:
        t = (np.asarray(dia["jd_utc"], float) - dia["jd_utc"][0]) * 24
        figure = FigureSpec([PanelSpec(
            AxisSpec(translate("PhotometryDia", "Time since the first frame"), "h"),
            AxisSpec(translate("PhotometryDia", "Flux change"), translate("PhotometryDia", "reference units")),
            [SeriesSpec(translate("PhotometryDia", "target"), t, dia["flux"], yerr=dia["error"])],
        )])  # fmt: skip
        tab = getattr(page, "dia_tab", None)
        if tab is None:
            tab = page.dia_tab = QWidget(win)
            tab.note = QLabel(translate("PhotometryDia", "The values are flux changes relative to the reference "
                                        "(reference units), not total fluxes."), tab)  # fmt: skip
            tab.note.setWordWrap(True)
            tab.plot = PlotView(parent=tab)
            lay = QVBoxLayout(tab)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(tab.note)
            lay.addWidget(tab.plot, 1)
            win.add_result_tab("dia", translate("PhotometryDia", "Difference imaging"), tab)
        tab.plot.set_figure(figure)
        win.docks["result_dia"].raise_()
        page.dia_note.setText(translate("PhotometryDia", "Done: {n} frames.").format(n=len(t)))
    except (ValueError, KeyError, IndexError) as e:  # a malformed result is said, never raised
        page.dia_note.setText(message(e))
