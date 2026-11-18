"""The Light curves window on stages (plans/interface.md UI-16.4): the Period search tab's Data, Clean, Search, then one
stage each for the Frequency analysis and Variable star search tabs. One rail; a stage of another tab brings that tab
forward, and choosing a tab shows its first stage."""

from PySide6.QtCore import QCoreApplication

from .lightcurve_fold import fold_stage, peak_inspector, report_stage
from .stage_boxes import period_stages

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PeriodWindow", "…") calls


def _follow_guide(tab, win, key):
    """The rail replaces the tab's step guide: the second step done (the analysis, the search) ticks the stage."""
    tab.guide.hide()
    set_state = tab.guide.set_state

    def follow(i, state="done"):
        set_state(i, state)
        if i == 1:
            win.set_stage_state(key, "done" if state == "done" else "empty")

    tab.guide.set_state = follow


def light_curve_stages(win, lc):
    fp, vf = lc.frequency_page, lc.varfind_page
    freq, var = translate("PeriodWindow", "Frequencies"), translate("PeriodWindow", "Variables")
    table = peak_inspector(win, lc.period_page)
    extra = {  # key: title, the tab's whole controls column, guide anchor
        "fold": (translate("PeriodWindow", "Fold"), fold_stage(lc.period_page), "lightcurves-period-search"),
        "frequencies": (freq, fp.guide.parentWidget(), "lightcurves-frequency-analysis"),
        "variables": (var, vf.guide.parentWidget(), "photometry-psf-photometry-searching-variables"),
        "report": (
            translate("PeriodWindow", "Report"),
            report_stage(lc.period_page, table),
            "lightcurves-period-search",
        ),
    }
    period_stages(win, lc, extra)
    _follow_guide(fp, win, "frequencies")
    _follow_guide(vf, win, "variables")
    tab_of = {"data": 0, "clean": 0, "search": 0, "fold": 0, "report": 0, "frequencies": 1, "variables": 2}
    first = {0: "data", 1: "frequencies", 2: "variables"}
    show = win.show_stage

    def show_stage(key):
        if lc.currentIndex() != tab_of[key]:
            lc.setCurrentIndex(tab_of[key])
        show(key)

    def follow(i):
        if i in first and tab_of.get(win.rail.current) != i:  # the Occultation tab has no stage
            show(first[i])

    win.show_stage = show_stage
    win.rail.stage_chosen.disconnect(show)
    win.rail.stage_chosen.connect(show_stage)
    lc.currentChanged.connect(follow)
