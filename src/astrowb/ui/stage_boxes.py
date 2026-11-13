"""A page's left column as stages of its area window (plans/interface.md UI-16.x): the page builds its parts as boxes
(`page.stage_boxes`, in order), the window shows each as a stage beside the page's main view, and the page's step
guide moves the rail (a step done gets ✓). Used by Planning (UI-16.8), O−C (UI-16.5) and Calibration (UI-16.2)."""

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


def _index(layout, widget):
    """The place in layout of the item holding widget (the widget itself or a row layout with it)."""
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is widget or (item.layout() is not None and item.layout().indexOf(widget) >= 0):
            return i
    raise ValueError(widget)


def boxes_from_column(layout, starts):
    """starts: [(key, first widget)] in the column's order; each box holds the items from its first widget up to
    the next box's (the last one: to the column's end)."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    boxes, stop = {}, layout.count()
    for key, widget in reversed(starts):
        box = QWidget()
        QVBoxLayout(box).setContentsMargins(0, 0, 0, 0)
        start = _index(layout, widget)
        _take(layout, start, stop, box.layout())
        box.layout().addStretch(1)
        boxes[key], stop = box, start
    return dict(reversed(boxes.items()))


def one_per_row(grid):
    """A grid of buttons laid out again one per row: two per row are wider than a stage beside the main view."""
    items = []
    while grid.count():
        r, c, *_ = grid.getItemPosition(0)
        items.append(((r, c), grid.takeAt(0)))
    for i, (_, item) in enumerate(sorted(items, key=lambda e: e[0])):
        if item.widget() is not None:
            grid.addWidget(item.widget(), i, 0)


def _take(layout, start, stop, into):
    """Move the items start..stop-1 of layout (widgets and row layouts; stretches dropped) into the layout into."""
    for _ in range(start, stop):
        item = layout.takeAt(start)
        if item.widget() is not None:
            into.addWidget(item.widget())
        elif item.layout() is not None:
            sub = item.layout()
            sub.setParent(None)  # a layout has one parent: free it before the stage's box takes it
            into.addLayout(sub)


def calibration_stages(win, page):
    """The Calibration window (UI-16.2): Frames (folders, Scan, the list), Calibrate (where to write, rejection,
    options, the result), Continue (Photometry, stacking); the frame table and its problems stay the main view."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    left = page.guide.parentWidget()
    split = left.parentWidget()
    while not isinstance(split, QSplitter):
        split = split.parentWidget()
    right = next(
        w for w in split.findChildren(QWidget) if w.layout() is not None and w.layout().indexOf(page.result) >= 0
    )
    lay_l, lay_r = left.layout(), right.layout()
    boxes = {}
    for key in ("frames", "calibrate", "continue"):
        boxes[key] = QWidget()
        QVBoxLayout(boxes[key]).setContentsMargins(0, 0, 0, 0)

    index = _index
    start = index(lay_l, page.guide) + 1
    _take(lay_l, start, index(lay_l, page.table), boxes["frames"].layout())
    boxes["frames"].layout().addStretch(1)
    _take(lay_r, 0, index(lay_r, page.photometry_button), boxes["calibrate"].layout())
    boxes["calibrate"].layout().addStretch(1)
    _take(lay_r, 0, lay_r.count(), boxes["continue"].layout())
    boxes["continue"].layout().addStretch(1)
    _take(lay_l, index(lay_l, page.table), lay_l.count(), lay_r)  # the list of frames and its problems: the view
    page.stage_boxes = boxes
    titles = {"frames": translate("CalibrationWindow", "Frames"),
              "calibrate": translate("CalibrationWindow", "Calibrate"),
              "continue": translate("CalibrationWindow", "Continue")}  # fmt: skip
    anchors = {"frames": "calibration-1-scan-raw-frames", "calibrate": "calibration-3-calibrate",
               "continue": "calibration-4-align-stack"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "frames", 1: "frames", 2: "calibrate", 3: "continue"})


def models_stages(win, page):
    """The Models window (UI-16.6): Data, Parameters, Fit beside the light curve and its model; on the Visual binary
    tab the stages do not apply and their dock is hidden."""
    lay = page.guide.parentWidget().layout()
    page.stage_boxes = boxes_from_column(lay, [("data", page.file), ("parameters", page.table),
                                               ("fit", page.use_mcmc)])  # fmt: skip
    from PySide6.QtWidgets import QGridLayout

    for grid in page.stage_boxes["fit"].findChildren(QGridLayout):
        one_per_row(grid)
    titles = {"data": translate("ModelsWindow", "Data"), "parameters": translate("ModelsWindow", "Parameters"),
              "fit": translate("ModelsWindow", "Fit")}  # fmt: skip
    anchors = {"data": "orbits-models-fitting-light-curve", "parameters": "orbits-models-model",
               "fit": "orbits-models-mcmc-uncertainties"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "data", 1: "parameters", 2: "fit", 3: "fit"})
    page.tabs.currentChanged.connect(lambda i: win.docks["stages"].setVisible(i == 0))


def period_stages(win, light_curves):
    """The Light curves window (UI-16.4), Period search tab: Data (the curve: Photometry, a file, an archive), Clean
    (outliers, binning, points, units), Search (method, range, Search, the result) beside the three plots; the stage
    dock hides on the other tabs."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    page = light_curves.period_page
    lay = page.guide.parentWidget().layout()
    parts = boxes_from_column(lay, [("data", page.source), ("settings", page.method), ("clean", page.clip_button),
                                    ("run", page.search_button)])  # fmt: skip
    search = QWidget()
    both = QVBoxLayout(search)
    both.setContentsMargins(0, 0, 0, 0)
    both.addWidget(parts["settings"])
    both.addWidget(parts["run"], 1)
    page.stage_boxes = {"data": parts["data"], "clean": parts["clean"], "search": search}
    titles = {"data": translate("PeriodWindow", "Data"), "clean": translate("PeriodWindow", "Clean"),
              "search": translate("PeriodWindow", "Search")}  # fmt: skip
    anchors = {"data": "lightcurves-period-search", "clean": "lightcurves-period-search",
               "search": "methods-period-search"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "data", 1: "clean", 2: "search", 3: "search"})
    light_curves.currentChanged.connect(lambda i: win.docks["stages"].setVisible(i == 0))
