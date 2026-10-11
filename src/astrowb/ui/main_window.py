"""Main window: workspace sidebar, the pages behind it, and running tasks."""

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QStackedWidget,
    QWidget,
)

from ..brand import BRAND
from ..engine.core import Engine
from ..engine.project import EXTENSION
from ..settings import Settings
from . import area_menus, area_pages, area_windows, main_menus, tour
from .area_actions import AreaActions
from .area_menus import _undo_source
from .file_actions import FileActions
from .files import images_filter
from .image_actions import ImageActions
from .kit.window import _raise as _raise_window
from .main_settings import SettingsActions
from .task_actions import TaskActions
from .window_menu import WindowMenu
from .workspaces import (
    CalibratePage,
    PlotCanvas,
    ProjectPage,
    StartPage,
)


class _TaskList(QListWidget):
    def sizeHint(self):  # a few lines by default; the user can drag the dock larger
        return QSize(400, 70)


class _Lazy:
    """A page attribute that builds the page (MainWindow._make_<attr>) the first time it is read."""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, win, owner=None):
        if win is None:
            return self
        own = getattr(win, "_make_" + self.name, None)  # the pages not yet moved to area_pages.py (ARC-4.4)
        page = own() if own else getattr(area_pages, "make_" + self.name)(win)
        vars(win)[self.name] = page  # later reads find the page directly
        win._place(self.name, page)
        return page


class MainWindow(WindowMenu, TaskActions, FileActions, AreaActions, SettingsActions, ImageActions, QMainWindow):
    taskUpdated = Signal(object)  # emitted from the task monitor thread, delivered on the GUI thread
    updateChecked = Signal(object, object)  # newer release or None, error or None (from a thread)
    start_page = _Lazy()
    plan_page = _Lazy()
    observe_page = _Lazy()
    calibrate_page = _Lazy()
    image_page = _Lazy()
    photometry_page = _Lazy()
    lightcurve_page = _Lazy()
    oc_page = _Lazy()
    spectro_page = _Lazy()
    models_page = _Lazy()
    rs_page = _Lazy()
    automation_page = _Lazy()
    project_page = _Lazy()
    guide_page = _Lazy()

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings()
        from datetime import datetime

        from ..io import bayer

        # cameras and phones keep local time: by default the computer's offset from UTC (as Siril via libraw)
        local = datetime.now().astimezone().utcoffset().total_seconds() / 3600
        bayer.CLOCK_UTC_OFFSET_H = float(self.settings.get("camera.clock_utc_offset", local))  # every picture opened
        self.engine = Engine()
        self.current_path: Path | None = None
        self.wcs = None
        self.setWindowIcon(QIcon(str(BRAND.icon_path)))
        self.resize(1200, 800)
        self._key = "start"  # the page in the stack
        self.area_windows = {}  # area key -> its AreaWindow, once the area has moved into one (I4)

        self._build_workspaces()

        self.tasks_list = _TaskList(self)
        self._dock("tasks", self.tr("Tasks"), self.tasks_list, Qt.BottomDockWidgetArea)
        self.taskUpdated.connect(self._on_task)
        self._task_items = {}
        self._on_done, self._on_fail = {}, {}

        self.pixel_label = QLabel(self)
        self.progress = QProgressBar(self)
        self.progress.setMaximumWidth(200)
        self.progress.hide()
        self.statusBar().addWidget(self.pixel_label, 1)
        self.statusBar().addPermanentWidget(self.progress)

        self._build_menus()
        for win in self.__dict__.pop("_pending_menus", []):
            self._complete_menus(win)
        self._menus_to_image_window()
        self._follow_undo()
        self.setAcceptDrops(True)  # files dropped on the window open (images, a project)
        area_windows.fill_image_toolbar(self)
        self._update_title()

    # --- construction -------------------------------------------------------
    PAGES = {  # key (stable, never translated) -> attribute of the page
        "start": "start_page",
        "plan": "plan_page",
        "observe": "observe_page",
        "calibrate": "calibrate_page",
        "image": "image_page",
        "photometry": "photometry_page",
        "timeseries": "lightcurve_page",
        "oc": "oc_page",
        "spectroscopy": "spectro_page",
        "orbits": "models_page",
        "remotesensing": "rs_page",
        "automation": "automation_page",
        "project": "project_page",
        "guide": "guide_page",
    }

    # areas already moved into windows of their own (plans/interface.md I4); the others are still pages here
    WINDOWED = (
        "photometry",
        "calibrate",
        "timeseries",
        "oc",
        "spectroscopy",
        "orbits",
        "plan",
        "observe",
        "automation",
        "remotesensing",
        "image",
    )

    def _area_key(self, attr):
        return next((k for k, a in self.PAGES.items() if a == attr), None)

    def _build_workspaces(self):
        self._frames = {}  # page -> the scroll area that holds it in the stack
        """Sidebar (one entry per stage of the work) + one page per entry. Light pages are built now; the
        others (see _Lazy) when they are first shown or used, so the window opens quickly."""
        from .start_page import areas

        titles = {"start": self.tr("Start")}
        titles.update({key: name for key, _, name, _ in areas()})  # the areas' names, as on their blocks
        titles.update({"project": self.tr("Project"), "guide": self.tr("Guide")})
        self._titles = titles  # the main window's own pages and the areas' names (Window menu, tests, tools)
        self.pages = QStackedWidget(self)
        self._placeholders = {}
        for attr in self.PAGES.values():
            self._placeholders[attr] = QWidget(self.pages)
            self.pages.addWidget(self._placeholders[attr])
        for attr in ("start_page", "image_page", "project_page", "calibrate_page"):  # cheap and needed at once
            getattr(self, attr)
        self.viewer, self.header_table = self.image_page.viewer, self.image_page.header_table
        self.files_list = self.project_page.files_list
        self.viewer.hovered.connect(self._show_pixel)
        self.files_list.itemActivated.connect(lambda item: self.open_fits(Path(item.data(Qt.UserRole)), ask=True))
        # no sidebar (the owner, 2026-11-08): the area blocks and the Window menu are the ways in
        self.setCentralWidget(self.pages)
        self.show_workspace("start")

    def _place(self, attr, page):
        """Put a freshly built page where its placeholder was in the stack; its tables get an export menu."""
        from PySide6.QtWidgets import QTableWidget

        from .kit.table_view import DataTable

        for table in page.findChildren(QTableWidget):
            if isinstance(table.parent(), DataTable):  # it has its own menu (copy, export, columns)
                continue
            table.setContextMenuPolicy(Qt.CustomContextMenu)
            table.customContextMenuRequested.connect(lambda pos, t=table: self._table_menu(t, pos))
        from PySide6.QtWidgets import QFrame, QLabel, QScrollArea

        for label in page.findChildren(QLabel):  # a long one-line label kept a column wider than a small window
            if not label.wordWrap() and len(label.text()) > 40 and label.pixmap().isNull():
                label.setWordWrap(True)
        _fields_scroll(page)
        _apply_mode(page, self.ui_mode())
        key = self._area_key(attr)
        if key in self.WINDOWED:
            self._place_in_window(key, page)
            return
        holder = self._placeholders.pop(attr)
        i = self.pages.indexOf(holder)
        current = self.pages.currentIndex() == i
        frame = QScrollArea(self.pages)  # a window smaller than the page scrolls instead of overflowing the screen
        frame.setWidget(page)
        frame.setWidgetResizable(True)
        frame.setFrameShape(QFrame.NoFrame)
        self._frames[page] = frame
        _Columns(frame, page)
        self.pages.insertWidget(i, frame)
        self.pages.removeWidget(holder)
        holder.deleteLater()
        if current:
            self.pages.setCurrentIndex(i)

    def _menus_to_image_window(self):
        """The image's menus (View: zoom, levels, stretch, overlays; Image: solving, processing) move with the Images
        page into its window; Open / Save image are in both File menus (interface I4.6)."""
        win = self.area_windows.get("image")
        if win is None:
            return
        bar = win.menuBar()
        for menu in (self.view_menu, self.image_bar_menu):
            self.menuBar().removeAction(menu.menuAction())
        bar.insertMenu(win.window_menu.menuAction(), self.view_menu)
        win.view_menu.menuAction().setVisible(False)  # the frame's own View: its items join the moved one
        self.view_menu.addSeparator()
        for act in win.view_menu.actions():
            self.view_menu.addAction(act)
        # the window's own Open… (Ctrl+O, also on drop) opens images: the main window's Open FITS… is not added twice
        acts = win.file_menu.actions()
        after_recent = acts[acts.index(win.recent_menu.menuAction()) + 1]
        win.file_menu.insertAction(after_recent, self.save_action)
        from PySide6.QtWidgets import QLabel

        self.image_pixel_label = QLabel(win)
        win.statusBar().addWidget(self.image_pixel_label, 1)
        area_windows.fill_image_menus(self, win)

    def _place_in_window(self, key, page):
        """The page, as it is, in an area window of its own (scrolling inside it when the window is smaller)."""
        from PySide6.QtWidgets import QFrame, QScrollArea

        from .kit.window import AreaWindow
        from .start_page import areas

        if key == "photometry":
            area_windows.photometry_window(self, page)
            return
        if key == "spectroscopy":
            area_windows.spectroscopy_window(self, page)
            return

        frame = QScrollArea()
        frame.setWidget(page)
        frame.setWidgetResizable(True)
        frame.setFrameShape(QFrame.NoFrame)
        self._frames[page] = frame
        _Columns(frame, page)
        title = next(name for k, _, name, _ in areas() if k == key)
        handler, file_filter = self._opener(key, page)
        win = AreaWindow(
            key, title, self.settings, frame, undo_stack=_undo_source(page), open_files=handler,
            file_filter=file_filter, parent=self,
        )  # fmt: skip
        win.setWindowIcon(self.windowIcon())
        win.help_requested.connect(self._help_for)
        builder = getattr(area_menus, key, None)
        if builder is not None:  # the area's own menus and toolbar (interface I6c)
            builder(self, page, win)
        self.area_windows[key] = win
        self._complete_menus(win)

    def _opener(self, key, page):
        """What a window does with files opened from its File menu or dropped on it (interface I6b (8)):
        (handler([paths]), file filter), or (None, "") for an area that opens no file."""

        def folder(paths):
            first = Path(paths[0])
            return str(first if first.is_dir() else first.parent)

        def calibrate(paths):
            page.lights.setText(folder(paths))  # the night's frames: their folder is what Calibration reads

        def light_curve(paths):
            page.setCurrentWidget(page.period_page)
            page.period_page._load(paths[0])

        def spectrum(paths):
            page.tabs.setCurrentWidget(page.reduce_tab)
            page.reduce_tab.science.edit.setText(paths[0])

        return {
            "image": (self.open_many, images_filter()),
            "calibrate": (calibrate, images_filter()),
            "timeseries": (light_curve, "CSV (*.csv *.txt *.dat);;*"),
            "oc": (lambda paths: page._load(paths[0]), "Text (*.txt *.csv *.dat);;*"),
            "orbits": (lambda paths: page.file.edit.setText(paths[0]), "Tables (*.csv *.txt *.dat);;*"),
            "spectroscopy": (spectrum, images_filter()),
            "remotesensing": (lambda paths: page.open(";".join(paths)), ""),
        }.get(key, (None, ""))

    def _complete_menus(self, win):
        """The common menus of every area window (interface I6c.2): Edit → Copy and the settings, Help → the tour,
        updates and About — the main window's own actions and Settings menu, so they act the same everywhere."""
        if not hasattr(self, "settings_menu"):  # built before the main window's menus: done right after them
            self.__dict__.setdefault("_pending_menus", []).append(win)
            return
        from PySide6.QtWidgets import QApplication, QTableWidget

        from .plot.export import selected_text

        def copy():
            w = QApplication.focusWidget()
            if isinstance(w, QTableWidget):  # tables have no copy of their own
                QApplication.clipboard().setText(selected_text(w))
            elif hasattr(w, "copy"):  # text boxes and fields
                w.copy()

        win.edit_menu.addSeparator()
        act = win._action(win.edit_menu, self.tr("&Copy"), copy, QKeySequence.Copy,
                          self.tr("Copies the selected cells or text"))  # fmt: skip
        act.setShortcutContext(Qt.WidgetWithChildrenShortcut)  # a text box under the cursor keeps its own Ctrl+C
        win.addAction(act)
        win.edit_menu.addMenu(self.settings_menu)  # language, look, processing device, text size
        win.help_menu.addSeparator()
        win._action(win.help_menu, self.tour_action.text(), lambda: (_raise_window(self), self.start_tour()))
        win.help_menu.addAction(self.update_action)
        win.help_menu.addAction(self.about_action)

    @property
    def workspaces(self):
        """key -> (title, page); building every page (tests and tools, not start-up)."""
        return {key: (self._titles[key], getattr(self, attr)) for key, attr in self.PAGES.items()}

    period_page = property(lambda self: self.lightcurve_page.period_page)

    # --- pages, built on first use -------------------------------------------
    def _make_start_page(self):
        page = StartPage(self, self.ui_mode(), self.recent_work())
        page.action.connect(self._start_action)
        page.resume.connect(self._resume)
        page.mode_chosen.connect(self.set_ui_mode)
        return page

    def recent_work(self):
        """[(kind, path)] for "Continue where you left off": the last projects, then the last files of each area
        window."""
        from .start_page import areas

        out = [("project", p) for p in self.settings.get("recent_projects", [])[:4]]
        for key, *_ in areas():
            out += [(key, p) for p in self.settings.get(f"area.{key}.recent", [])[:2]]
        return out[:8]

    def _resume(self, kind, path):
        if kind == "project":
            self.open_project(Path(path))
            return
        win = self.open_area(kind)
        if win is not None and win.open_files_handler is not None:
            win.open_files([path])

    def open_area(self, key):
        """Open or raise the area's window; an area not yet moved to a window of its own (I4) shows its page."""
        if key in self.WINDOWED and key not in self.area_windows:
            getattr(self, self.PAGES[key])  # builds the page, which puts it in its window
        win = self.area_windows.get(key)
        if win is None:
            self.show_workspace(key)
            return None
        self._last_area = key
        _raise_window(win)
        return win

    def ui_mode(self):
        return "expert" if self.settings.get("ui.mode", "basic") == "expert" else "basic"

    def set_ui_mode(self, mode):
        """Basic / Expert: which folding sections start open (workspaces.Collapsible.mode). Nothing is hidden for
        good; the choice is kept and applied to every page built so far and later."""
        self.settings.set("ui.mode", mode)
        self.settings.save()
        for frame in self._frames.values():
            _apply_mode(frame.widget(), mode)
        for win in self.area_windows.values():  # windows with panels (Photometry, Spectroscopy) are not in frames
            _apply_mode(win, mode)
        act = getattr(self, "expert_action", None)
        if act is not None and act.isChecked() != (mode == "expert"):
            act.setChecked(mode == "expert")
        start = self.__dict__.get("start_page")
        if start is not None:
            (start.expert if mode == "expert" else start.basic).setChecked(True)

    def _make_project_page(self):
        page = ProjectPage(self)
        page.run_selected.connect(lambda run_id: page.show_run(self.engine.project.run(run_id)))
        page.rerun_requested.connect(self.rerun)
        return page

    def rerun(self, run_id):
        """The same step with the recorded inputs and settings, recorded as a new run."""
        run = self.engine.project.run(run_id)
        return self.run_step(
            run["step"],
            run["inputs"],
            run["params"],
            on_done=lambda out: self.project_page.details.setPlainText(json.dumps(out, indent=1, default=str)[:20000]),
        )

    def _make_guide_page(self):
        from .guide_page import GuidePage

        return GuidePage(self.settings, self)

    def _make_plan_page(self):
        from .plan_page import PlanPage  # imported with its page: start-up stays fast

        page = PlanPage(self.settings, self)
        page.resolve_requested.connect(self.resolve_target)
        page.ephemeris_requested.connect(self.lookup_ephemeris)
        page.schedule_requested.connect(
            lambda blocks: (self.observe_page.load_schedule(blocks), self.show_workspace("observe"))
        )
        page.plan_requested.connect(
            lambda site, date, targets, params: self.run_step_for(
                "plan",
                "planning.night",
                {"site": site, "date": date, "targets": targets},
                params,
                on_done=lambda out: page.show_night(out["night"]),
            )
        )
        return page

    def _make_observe_page(self):
        from .observe_page import ObservePage  # imported with its page: start-up stays fast

        page = ObservePage(self.settings, self)
        page.preview_ready.connect(lambda p: self.open_fits(Path(p)))
        page.sequence_finished.connect(
            lambda folder: self.automation_page.night_finished(folder) if "automation_page" in vars(self) else None
        )
        return page

    def _make_automation_page(self):
        from .automation_page import AutomationPage  # imported with its page: start-up stays fast

        page = AutomationPage(self.settings, self)
        page.run_requested.connect(self.run_automation)
        page.sequence_requested.connect(self._load_sequence)
        return page

    def _make_rs_page(self):
        from .rs_page import RemoteSensingPage  # imported with its page: start-up stays fast

        page = RemoteSensingPage(self)
        page.step_requested.connect(
            lambda sid, inputs, params: self.run_step_for(
                "remotesensing",
                sid,
                inputs,
                params,
                on_done=lambda out: page.show_product(out["product"]),
                on_fail=page.status.setText,
            )
        )
        return page

    def _make_calibrate_page(self):
        page = CalibratePage(self)
        from ..io import bayer

        page.clock_offset.setValue(bayer.CLOCK_UTC_OFFSET_H)
        page.clock_offset.valueChanged.connect(self._set_clock_offset)
        page.scan_requested.connect(self.scan_raw)
        page.run_requested.connect(self.calibrate)
        page.stack_requested.connect(self.stack_images)
        page.photometry_requested.connect(self.send_to_photometry)
        return page

    def show_workspace(self, key):
        if key in self.WINDOWED:
            self.open_area(key)
            self._last_area = key
            return
        self._last_area = None
        self._show_key(key)

    def current_workspace(self) -> str:
        """The area the user was last sent to: an area window opened last, else the page shown here."""
        last = getattr(self, "_last_area", None)
        if last and self.area_windows.get(last) is not None and self.area_windows[last].isVisible():
            return last
        return self._key

    def _action(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        act.triggered.connect(lambda _checked=False: slot())  # Qt's "checked" flag must not reach the slot
        if shortcut:
            act.setShortcut(shortcut)
        menu.addAction(act)
        return act

    def _paint_glyphs(self):
        from .kit.icons import icon

        for act, kind in self._glyphs:
            act.setIcon(icon(kind, self))

    def _build_menus(self):
        main_menus.build(self)

    # --- image processing ---------------------------------------------------

    # --- plugins ------------------------------------------------------------

    # --- project ------------------------------------------------------------

    # --- FITS ---------------------------------------------------------------

    # --- tasks --------------------------------------------------------------

    # --- calibration --------------------------------------------------------

    # --- planning -----------------------------------------------------------

    # --- photometry ---------------------------------------------------------

    # --- misc ---------------------------------------------------------------

    def _update_title(self):
        parts = [BRAND.display_name]
        if self.engine.project:
            parts.insert(0, self.engine.project.path.stem)
        if self.current_path:
            parts.insert(0, self.current_path.name)
        self.setWindowTitle(" — ".join(parts))

    def start_tour(self):
        return tour.start(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Files dropped on the window: a project opens as the project, everything else as images."""
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        projects = [p for p in paths if p.endswith(EXTENSION)]
        if projects:
            self.open_project(Path(projects[0]))
        images = [p for p in paths if not p.endswith(EXTENSION) and Path(p).is_file()]
        if images:
            self.open_many(images)
        event.acceptProposedAction()

    def closeEvent(self, event):
        for win in self.area_windows.values():  # the area windows end with the main window (layouts saved)
            win.close()
        self.engine.shutdown()
        if self.engine.project:
            self.engine.project.close()
        super().closeEvent(event)


class _Columns(QObject):
    """Columns side by side, or one above the other while the window is narrower than they need together: side by
    side they were cut off on the right of a small window (the owner's Calibrate page)."""

    def __init__(self, frame, page):
        from PySide6.QtWidgets import QSplitter

        super().__init__(frame)
        self.frame, self.page = frame, page
        self.splits = [s for s in page.findChildren(QSplitter) if s.orientation() == Qt.Horizontal and s.count() > 1]
        self.wide = {s: True for s in self.splits}
        for w in (frame.viewport(), *self.splits):  # a tab's splitter is sized when the tab is first shown
            w.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.fit()
        return False

    def fit(self):
        over = max(self.page.width() - self.frame.viewport().width(), 0)  # how far the page sticks out
        for s in self.splits:
            if not s.isVisible():  # a tab not shown yet has no width of its own: decided when it is shown
                continue
            widgets = [s.widget(i) for i in range(s.count())]
            need = sum(max(w.minimumWidth(), w.minimumSizeHint().width()) for w in widgets)
            need += s.handleWidth() * (len(widgets) - 1)
            wide = s.width() - over >= need
            if wide != self.wide[s]:
                self.wide[s] = wide
                s.setOrientation(Qt.Horizontal if wide else Qt.Vertical)
                s.setSizes([10000] * len(widgets))


def _fields_scroll(page, tall=200):
    """In every splitter of a page, a block of fields taller than `tall` px scrolls on its own: on a short window the
    whole page scrolled and the plots and buttons below went out of sight (the owner's Photometry and Plan pages).
    Plots, images, tables and lists scroll or shrink by themselves and are left alone."""
    from PySide6.QtWidgets import QAbstractScrollArea, QFrame, QScrollArea, QSplitter, QTabWidget

    targets = []
    for split in page.findChildren(QSplitter):
        for i in range(split.count()):
            w = split.widget(i)
            if isinstance(w, (QAbstractScrollArea, QSplitter, QTabWidget, PlotCanvas)):
                continue
            side = split.orientation() == Qt.Horizontal  # a side column: the other column stays in view anyway
            if (side or w.findChild(PlotCanvas) is None) and w.minimumSizeHint().height() > tall:
                targets.append((split, w))  # above a plot, a panel holding a plot keeps it; small blocks need nothing
    for split, w in targets:
        i = split.indexOf(w)
        if i < 0:
            continue
        state = split.saveState()  # the page's own proportions (setSizes before it is shown)
        area = QScrollArea()
        area.setFrameShape(QFrame.NoFrame)
        area.setWidgetResizable(True)
        if split.orientation() == Qt.Horizontal:  # as narrow as its fields allow; never cut a field sideways
            area.setMinimumWidth(w.minimumSizeHint().width() + 20)  # too wide beside the rest: _Columns stacks them
        else:
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        split.insertWidget(i, area)
        area.setWidget(w)
        split.restoreState(state)


def _apply_mode(page, mode):
    """Open or fold the page's sections for the interface mode (workspaces.Collapsible.mode)."""
    from .workspaces import Collapsible

    for c in page.findChildren(Collapsible):
        if c.mode in ("basic", "expert"):
            c.set_expanded(c.mode == mode)
