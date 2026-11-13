"""The Planning window on the stage anatomy (plans/interface.md UI-16.8, plans/planning.md PLN-W): the left column's
parts become stages — Site and night, Targets, Night, Schedule (and send) — beside the chart and the tables, and the
page's step guide moves the rail (a step done gets ✓)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PlanWindow", "…") calls

STEP_STAGE = {0: "site", 1: "targets", 2: "night", 4: "schedule"}  # the guide's steps; 3 (exposure) is optional


def plan_stages(win, page):
    from .kit.anatomy import Stage

    titles = {"site": translate("PlanWindow", "Site and night"), "targets": translate("PlanWindow", "Targets"),
              "night": translate("PlanWindow", "Night"),
              "schedule": translate("PlanWindow", "Schedule")}  # fmt: skip
    anchors = {"site": "planning-your-site", "targets": "planning-adding-targets", "night": "planning-reading-plot",
               "schedule": "planning-plan-observing"}  # fmt: skip
    stages = []
    for key, box in page.stage_boxes.items():
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(box, 1)
        stages.append(Stage(key, titles[key], holder, anchors[key]))
    win.set_stages(stages)
    column = page.guide.parentWidget()  # the left column keeps only the title and the guide: the rail says it now
    while column is not None and not isinstance(column, QScrollArea):
        column = column.parentWidget()
    if column is not None:
        column.hide()
    page.guide.hide()
    set_state = page.guide.set_state

    def follow(i, state="done"):
        set_state(i, state)
        key = STEP_STAGE.get(i)
        if key:
            win.set_stage_state(key, "done" if state == "done" else "empty")

    page.guide.set_state = follow
    win.restoreDockWidget(win.docks["stages"])
