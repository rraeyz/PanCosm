"""A page's left column as stages of its area window (plans/interface.md UI-16.x): the page builds its parts as boxes
(`page.stage_boxes`, in order), the window shows each as a stage beside the page's main view, and the page's step
guide moves the rail (a step done gets ✓). Used by Planning (UI-16.8), O−C (UI-16.5) and Calibration (UI-16.2)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PlanWindow", "…") calls


def stages_from_boxes(win, page, titles, anchors, step_stage, keep_column=False):
    """titles, anchors: {box key: stage title, guide anchor}; step_stage: {guide step: box key}; keep_column: only
    the guide is hidden, the rest of its column (a plot under the controls) stays."""
    from .kit.anatomy import Stage

    stages = []
    for key, box in page.stage_boxes.items():
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(box, 1)
        stages.append(Stage(key, titles[key], holder, anchors[key]))
    win.set_stages(stages)
    guide = getattr(page, "guide", None)  # Observing has no step guide: its left column goes whole
    column = page.left if guide is None else guide.parentWidget()  # the column keeps only the title and the guide
    while column.parentWidget() is not None and not isinstance(column.parentWidget(), QSplitter):
        column = column.parentWidget()  # up to the splitter's left side (a scroll area on the Plan page)
    if not keep_column:
        column.hide()
    if guide is None:
        win.restoreDockWidget(win.docks["stages"])
        _refit_columns(page)
        return
    guide.hide()
    set_state = guide.set_state

    def follow(i, state="done"):
        set_state(i, state)
        key = step_stage.get(i)
        if key:
            win.set_stage_state(key, "done" if state == "done" else "empty")

    page.guide.set_state = follow
    win.restoreDockWidget(win.docks["stages"])
    _refit_columns(page)


def _refit_columns(page):
    """A page's columns scroll in areas as wide as the columns were when built (main_window._fields_scroll); with
    their controls moved into the stages they are narrower, and the page must fit beside the stages."""
    from PySide6.QtWidgets import QScrollArea

    for area in page.findChildren(QScrollArea):
        if isinstance(area.parentWidget(), QSplitter) and area.widget() is not None and area.minimumWidth() > 0:
            area.setMinimumWidth(area.widget().minimumSizeHint().width() + 20)


def _current_tab_only(tabs):
    """Only the shown tab counts for the page's width: the other tabs hide the stages and have the whole window."""
    from PySide6.QtWidgets import QSizePolicy

    def follow(i):
        for k in range(tabs.count()):
            w = tabs.widget(k)
            w.setSizePolicy(QSizePolicy.Preferred if k == i else QSizePolicy.Ignored, w.sizePolicy().verticalPolicy())

    tabs.currentChanged.connect(follow)
    follow(tabs.currentIndex())


def plan_stages(win, page):
    titles = {"site": translate("PlanWindow", "Site and night"), "targets": translate("PlanWindow", "Targets"),
              "night": translate("PlanWindow", "Night"), "schedule": translate("PlanWindow", "Schedule")}  # fmt: skip
    anchors = {"site": "planning-your-site", "targets": "planning-adding-targets", "night": "planning-reading-plot",
               "schedule": "planning-plan-observing"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "site", 1: "targets", 2: "night", 4: "schedule"})


def exoplanets_stages(win, page):
    """The Exoplanets window (UI-16.7): Data, Star, Planets, Model, Fit, Uncertainty, Results beside the transit."""
    from .exoplanets_page import STAGES

    titles = {"data": translate("ExoplanetsWindow", "Data"), "star": translate("ExoplanetsWindow", "Star"),
              "planets": translate("ExoplanetsWindow", "Planets"), "model": translate("ExoplanetsWindow", "Model"),
              "fit": translate("ExoplanetsWindow", "Fit"),
              "uncertainty": translate("ExoplanetsWindow", "Uncertainty"),
              "results": translate("ExoplanetsWindow", "Results")}  # fmt: skip
    anchors = {key: f"exoplanets-{key}" for key in STAGES}
    stages_from_boxes(win, page, titles, anchors, {}, keep_column=True)
    page.stage_done.connect(lambda key: win.set_stage_state(key, "done"))


def _index(layout, widget):
    """The place in layout of the item holding widget (the widget itself or a row layout with it)."""
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is widget or (item.layout() is not None and item.layout().indexOf(widget) >= 0):
            return i
    raise ValueError(widget)


def boxes_from_column(layout, starts, end=None):
    """starts: [(key, first widget)] in the column's order; each box holds the items from its first widget up to
    the next box's (the last one: to the column's end, or to the widget end, which stays)."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    boxes, stop = {}, layout.count() if end is None else _index(layout, end)
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
    from .calibration_checks import make, refresh_frames

    extra = make(page)  # Check, Masters, Review: new boxes, refreshed by the page's signals
    for key in ("frames", "calibrate", "continue"):
        boxes[key] = QWidget()
        QVBoxLayout(boxes[key]).setContentsMargins(0, 0, 0, 0)

    index = _index
    start = index(lay_l, page.guide) + 1
    _take(lay_l, start, index(lay_l, page.table.parent()), boxes["frames"].layout())
    boxes["frames"].layout().addStretch(1)
    _take(lay_r, 0, index(lay_r, page.photometry_button), boxes["calibrate"].layout())
    boxes["calibrate"].layout().addStretch(1)
    _take(lay_r, 0, lay_r.count(), boxes["continue"].layout())
    boxes["continue"].layout().addStretch(1)
    # the list of frames and its problems: the view
    _take(lay_l, index(lay_l, page.table.parent()), lay_l.count(), lay_r)
    extra["masters"].layout().addWidget(page.masters_button)  # the hand choice, with the masters to make
    extra["masters"].layout().addStretch(1)
    for box in (extra["check"], extra["review"]):
        box.layout().addStretch(0)
    order = ("frames", "check", "masters", "calibrate", "review", "continue")
    page.stage_boxes = {k: (boxes | extra)[k] for k in order}
    titles = {"frames": translate("CalibrationWindow", "Frames"), "check": translate("CalibrationWindow", "Check"),
              "masters": translate("CalibrationWindow", "Masters"),
              "calibrate": translate("CalibrationWindow", "Calibrate"),
              "review": translate("CalibrationWindow", "Review"),
              "continue": translate("CalibrationWindow", "Continue")}  # fmt: skip
    anchors = {"frames": "calibration-1-scan-raw-frames", "check": "calibration-1-scan-raw-frames",
               "masters": "calibration-3-calibrate", "calibrate": "calibration-3-calibrate",
               "review": "calibration-3-calibrate", "continue": "calibration-4-align-stack"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "frames", 1: "check", 2: "calibrate", 3: "continue"})
    win.add_result_tab("problems", translate("CalibrationWindow", "Problems"), page.problems_view)
    win.add_result_tab("plan", translate("CalibrationWindow", "Plan"), page.plan_table)
    win.add_result_tab("report", translate("CalibrationWindow", "Report"), page.report_view)
    win.add_result_tab("log", translate("CalibrationWindow", "Log"), page.log_view)
    refresh_frames(page)  # fill the new stages from what is already scanned


def period_stages(win, light_curves, extra=None):
    """The Light curves window (UI-16.4), Period search tab: Data (the curve: Photometry, a file, an archive), Clean
    (outliers, binning, points, units), Search (method, range, Search, the result) beside the three plots; the stage
    dock hides on the other tabs unless `extra` ({key: (title, widget, guide anchor)}) adds stages for them."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    extra = extra or {}
    page = light_curves.period_page
    lay = page.guide.parentWidget().layout()
    parts = boxes_from_column(lay, [("data", page.source), ("settings", page.method), ("clean", page.clip_button),
                                    ("run", page.search_button)])  # fmt: skip
    search = QWidget()
    both = QVBoxLayout(search)
    both.setContentsMargins(0, 0, 0, 0)
    both.addWidget(parts["settings"])
    both.addWidget(parts["run"], 1)
    page.stage_boxes = {"data": parts["data"], "clean": parts["clean"], "search": search,
                        **{k: w for k, (_, w, _) in extra.items()}}  # fmt: skip
    titles = {"data": translate("PeriodWindow", "Data"), "clean": translate("PeriodWindow", "Clean"),
              "search": translate("PeriodWindow", "Search")}  # fmt: skip
    anchors = {"data": "lightcurves-period-search", "clean": "lightcurves-period-search",
               "search": "methods-period-search"}  # fmt: skip
    titles |= {k: t for k, (t, _, _) in extra.items()}
    anchors |= {k: a for k, (_, _, a) in extra.items()}
    stages_from_boxes(win, page, titles, anchors, {0: "data", 1: "clean", 2: "search", 3: "search"})
    if not extra:
        light_curves.currentChanged.connect(lambda i: win.docks["stages"].setVisible(i == 0))
    _current_tab_only(light_curves)


def rs_stages(win, page):
    """The Remote sensing window (UI-16.13): Scene, Display, Indices, Classes beside the map; the pixel read-out,
    the status and the plot stay in the column under them."""
    lay = page.guide.parentWidget().layout()
    page.open_button = lay.itemAt(_index(lay, page.guide) + 1).widget()  # Open image…, the column's first control
    starts = [("scene", page.open_button), ("display", page.show_combo), ("indices", page.index), ("classes", page.k)]
    page.stage_boxes = boxes_from_column(lay, starts, end=page.readout)
    from .rs_views import export_stage

    page.stage_boxes["export"] = export_stage(page)
    titles = {"scene": translate("RemoteSensingWindow", "Scene"),
              "display": translate("RemoteSensingWindow", "Display"),
              "indices": translate("RemoteSensingWindow", "Indices"),
              "classes": translate("RemoteSensingWindow", "Classes"),
              "export": translate("MainWindow", "Export")}  # fmt: skip
    anchors = {
        "scene": "remote-sensing-opening-image",
        "display": "remote-sensing-band-roles-indices",
        "indices": "remote-sensing-band-math",
        "classes": "remote-sensing-classification-principal-components",
        "export": "remote-sensing-opening-image",
    }
    stages_from_boxes(win, page, titles, anchors, {0: "scene", 1: "display", 2: "indices", 3: "classes"}, True)
    from .rs_views import add_views

    add_views(win, page)


def observing_stages(win, page):
    """The Observing window (UI-16.9): Connect, Point, Focus, Sequence, Night; the exposure rows stay the main view."""
    left, right = page.left.layout(), page.right.layout()
    box = boxes_from_column(left, [("connect", page.url), ("point", page.mount), ("focus", page.focus_pos),
                                   ("night", page.buttons["abort"])])  # fmt: skip
    box["sequence"] = boxes_from_column(right, [("sequence", page.start_button)])["sequence"]
    page.stage_boxes = {k: box[k] for k in ("connect", "point", "focus", "sequence", "night")}
    titles = {"connect": translate("ObservePage", "Connect"), "point": translate("ObservePage", "Point"),
              "focus": translate("ObservePage", "Focus"), "sequence": translate("ObservePage", "Sequence"),
              "night": translate("ObservePage", "Night")}  # fmt: skip
    anchors = {"connect": "observing-starting-connecting", "point": "observing-moving-telescope",
               "focus": "observing-autofocus", "sequence": "observing-sequences",
               "night": "observing-safety-supervisor"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {})
    from .observe_chips import ObserveChips

    win.observe_chips = ObserveChips(win, page)  # the device chips and the inspector


def astrometry_stages(win, page):
    """The Astrometry window (UI-16.11): Images, Solve, Find, Measure, Report beside the frame and the positions."""
    titles = {"images": translate("AstrometryWindow", "Images"), "solve": translate("AstrometryWindow", "Solve"),
              "find": translate("AstrometryWindow", "Find"), "measure": translate("AstrometryWindow", "Measure"),
              "report": translate("AstrometryWindow", "Report")}  # fmt: skip
    anchors = {key: f"astrometry-{key}" for key in ("images", "solve", "find", "measure", "report")}
    stages_from_boxes(win, page, titles, anchors, {})
