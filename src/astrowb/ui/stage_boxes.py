"""A page's left column as stages of its area window (plans/interface.md UI-16.x): the page builds its parts as boxes
(`page.stage_boxes`, in order), the window shows each as a stage beside the page's main view, and the page's step
guide moves the rail (a step done gets ✓). Used by Planning (UI-16.8) and O−C (UI-16.5)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PlanWindow", "…") calls


def stages_from_boxes(win, page, titles, anchors, step_stage):
    """titles, anchors: {box key: stage title, guide anchor}; step_stage: {guide step: box key}."""
    from .kit.anatomy import Stage

    stages = []
    for key, box in page.stage_boxes.items():
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(box, 1)
        stages.append(Stage(key, titles[key], holder, anchors[key]))
    win.set_stages(stages)
    column = page.guide.parentWidget()  # the left column keeps only the title and the guide: the rail says it now
    while column.parentWidget() is not None and not isinstance(column.parentWidget(), QSplitter):
        column = column.parentWidget()  # up to the splitter's left side (a scroll area on the Plan page)
    column.hide()
    page.guide.hide()
    set_state = page.guide.set_state

    def follow(i, state="done"):
        set_state(i, state)
        key = step_stage.get(i)
        if key:
            win.set_stage_state(key, "done" if state == "done" else "empty")

    page.guide.set_state = follow
    win.restoreDockWidget(win.docks["stages"])


def plan_stages(win, page):
    titles = {"site": translate("PlanWindow", "Site and night"), "targets": translate("PlanWindow", "Targets"),
              "night": translate("PlanWindow", "Night"), "schedule": translate("PlanWindow", "Schedule")}  # fmt: skip
    anchors = {"site": "planning-your-site", "targets": "planning-adding-targets", "night": "planning-reading-plot",
               "schedule": "planning-plan-observing"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "site", 1: "targets", 2: "night", 4: "schedule"})


def oc_stages(win, page):
    titles = {"minima": translate("OcWindow", "Minima"), "ephemeris": translate("OcWindow", "Ephemeris"),
              "model": translate("OcWindow", "Model"), "report": translate("OcWindow", "Fit and report")}  # fmt: skip
    anchors = {"minima": "lightcurves-o-c-diagram-o", "ephemeris": "methods-ephemeris-o-c",
               "model": "lightcurves-third-body-apsidal-motion",
               "report": "lightcurves-reading-o-c-diagram"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "minima", 1: "ephemeris", 3: "model", 4: "report"})
