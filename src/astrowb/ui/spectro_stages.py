"""The Spectroscopy window on stages (plans/interface.md UI-16.3): one rail for all jobs, each job showing only its own
stages (Frames, Extract, Wavelengths for the long slit and the échelle; the other jobs one stage each) beside the
chosen job's view. The job is still chosen in the toolbar; choosing a stage of another job switches the job."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from .kit.fields import Segmented
from .kit.focus import read_in_order
from .stage_boxes import _index, boxes_from_column, stages_from_boxes

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("SpectroscopyWindow", "…") calls

SLIT, ECHELLE, TELLURIC, VELOCITY, CUBE, TOOLS = range(6)  # the job tabs' order


def _label_after(lay, button):
    """The first label after button in the column: the heading of the lines table."""
    for i in range(_index(lay, button) + 1, lay.count()):
        w = lay.itemAt(i).widget()
        if isinstance(w, QLabel):
            return w
    raise ValueError(button)


def _wavelength_boxes(tab, first, last_step):
    """A reduction tab's column as boxes: Frames (the files), Extract (up to the extraction), Wavelengths."""
    lay = tab.guide.parentWidget().layout()
    return boxes_from_column(lay, [("frames", tab.science), ("extract", first),
                                   ("lines", _label_after(lay, last_step))])  # fmt: skip


def _whole(panel):
    """A job's whole column as a stage: out of the scroll area the page put it in (the stage scrolls itself)."""
    whole = panel.takeWidget() if isinstance(panel, QScrollArea) else panel
    whole.layout().setContentsMargins(0, 0, 0, 0)  # the stage has its own
    return whole


def _two_lines(button, limit=400):
    """A button whose text is wider than a stage breaks it into two lines at the best space (a button never wraps)."""
    if button.sizeHint().width() <= limit or " " not in button.text():
        return
    words, width = button.text().split(" "), button.fontMetrics().horizontalAdvance
    cut = min(range(1, len(words)), key=lambda k: max(width(" ".join(words[:k])), width(" ".join(words[k:]))))
    button.setText(" ".join(words[:cut]) + "\n" + " ".join(words[cut:]))


def two_columns(grid):
    """A grid of three columns laid out in two: in a row of three the third item goes under the pair, and an item that
    spanned columns has its own line (three columns of fields and buttons are wider than a stage beside the view)."""
    rows = {}
    while grid.count():
        r, c, _, span = grid.getItemPosition(0)
        rows.setdefault(r, []).append((c, span, grid.takeAt(0)))
    lines = []
    for _, items in sorted(rows.items()):
        one = [item for _, c, item in sorted(items, key=lambda e: e[0]) if c == 1]
        lines += [one[:2], one[2:]] + [[item] for _, c, item in sorted(items, key=lambda e: e[0]) if c > 1]
    for r, line in enumerate(x for x in lines if x):
        for k, item in enumerate(line):
            grid.addItem(item, r, k, 1, 2 if len(line) == 1 else 1)


def _overview(page):
    """The instrument profile and the folded order of work, which belong to no single job."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(page.profile_bar)
    lay.addWidget(page.steps)
    lay.addStretch(1)
    return box


def _follow_guide(tab, win, prefix, steps):
    """The tab's step guide is replaced by the rail: a step done ticks its stage."""
    tab.guide.hide()
    set_state = tab.guide.set_state

    def follow(i, state="done"):
        set_state(i, state)
        if i in steps:
            win.set_stage_state(f"{prefix}_{steps[i]}", "done" if state == "done" else "empty")

    tab.guide.set_state = follow


def job_switch(win, page):
    """The toolbar's job switch: a Segmented over the same jobs as the tabs (they stay the owner of the current job)."""
    tabs = page.tabs
    names = [tabs.tabText(i) for i in range(tabs.count())]
    switch = Segmented(list(zip(map(str, range(len(names))), names, strict=True)), str(tabs.currentIndex()))
    for button, tip in zip(switch.buttons.values(), page.JOB_TIPS, strict=True):
        button.setToolTip(translate("SpectroscopyPage", tip))
    switch.changed.connect(lambda key: tabs.setCurrentIndex(int(key)))
    tabs.currentChanged.connect(lambda i: switch.setValue(str(i)))
    win.job_switch = switch
    win.toolbar.insertWidget(win._end, switch)
    win.toolbar.setVisible(True)


def spectroscopy_stages(win, page):
    from .spectro_inspector import line_inspector

    line_inspector(win, page)
    red, ech = page.reduce_tab, page.echelle_tab
    for grid in page.tools_tab.findChildren(QGridLayout):
        if grid.columnCount() > 2:
            two_columns(grid)
    slit = _wavelength_boxes(red, red.row, red.extract_button)
    orders = _wavelength_boxes(ech, ech.extracted, ech.extract_button)
    frames, extract = translate("SpectroscopyWindow", "Frames"), translate("SpectroscopyWindow", "Extract")
    lines = translate("SpectroscopyWindow", "Wavelengths")
    rows = [  # key, title, job (None: every job), the widget, the guide's anchor
        ("overview", translate("SpectroscopyWindow", "Overview"), None, _overview(page),
         "spectroscopy-instrument-profiles"),
        *((f"slit_{k}", title, SLIT, slit[k], "spectroscopy-long-slit-reduction-reduce")
          for k, title in zip(slit, (frames, extract, lines), strict=True)),
        *((f"echelle_{k}", title, ECHELLE, orders[k], "spectroscopy-echelle")
          for k, title in zip(orders, (frames, extract, lines), strict=True)),
        ("telluric", translate("SpectroscopyWindow", "Telluric"), TELLURIC, _whole(page.job_panels[TELLURIC]),
         "spectroscopy-telluric-correction"),
        ("velocity", translate("SpectroscopyWindow", "Velocities"), VELOCITY, _whole(page.job_panels[VELOCITY]),
         "spectroscopy-radial-velocity-orbit"),
        ("cube", translate("SpectroscopyWindow", "IFU cube"), CUBE, _whole(page.job_panels[CUBE]),
         "spectroscopy-ifu-data-cubes"),
        ("tools", translate("SpectroscopyWindow", "Spectrum tools"), TOOLS, _whole(page.job_panels[TOOLS]),
         "spectroscopy-spectrum-tools"),
    ]  # fmt: skip
    page.left = page  # stages_from_boxes wants the column the controls came from; the page has none to hide
    page.stage_boxes = {key: widget for key, _, _, widget, _ in rows}
    for widget in page.stage_boxes.values():
        for button in widget.findChildren(QPushButton):
            _two_lines(button)
    jobs = {key: job for key, _, job, _, _ in rows}
    stages_from_boxes(win, page, {k: title for k, title, *_ in rows}, {k: a for k, _, _, _, a in rows}, {}, True)
    _follow_guide(red, win, "slit", {1: "frames", 2: "extract", 3: "lines", 4: "lines"})
    _follow_guide(ech, win, "echelle", {1: "frames", 2: "extract", 3: "extract", 4: "lines", 5: "lines"})
    first = {job: next(k for k, j in jobs.items() if j == job) for job in range(6) if job in jobs.values()}
    show = win.show_stage

    def show_stage(key):  # a stage of another job brings that job (its view, its rail) forward first
        job = jobs[key]
        if job is not None and page.tabs.currentIndex() != job:
            page.tabs.setCurrentIndex(job)
        show(key)

    def follow(i):
        for key, button in win.rail.buttons.items():
            button.setVisible(jobs[key] in (None, i))
        if jobs.get(win.rail.current) not in (None, i):
            show(first[i])

    win.show_stage = show_stage
    win.rail.stage_chosen.disconnect(show)
    win.rail.stage_chosen.connect(show_stage)
    page.tabs.currentChanged.connect(follow)
    follow(page.tabs.currentIndex())
    show(first[page.tabs.currentIndex()])
    views = win.centralWidget()  # the stages are read before the view; the frame before its plots (as _frame_and_plot)
    parts = [(t.frame_view, t.plot_box) if hasattr(t, "frame_view") else (views.widget(i),)
             for i, t in enumerate(page.tabs.widget(i) for i in range(page.tabs.count()))]  # fmt: skip
    read_in_order(win.rail, win.stage_stack, *(w for part in parts for w in part))
