"""Main window: workspace sidebar, the pages behind it, and running tasks."""

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QTableWidgetItem,
    QWidget,
)

from .. import __version__, compute
from ..brand import BRAND
from ..engine.core import Engine
from ..engine.project import EXTENSION, Project
from ..io import fits as fitsio
from ..settings import Settings
from . import advice, area_menus, area_pages, area_windows, main_menus, tour
from .area_menus import _undo_source
from .files import FITS_FILTER, images_filter
from .image_actions import ImageActions
from .kit.window import _raise as _raise_window
from .messages import task_error, translate
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


class MainWindow(ImageActions, QMainWindow):
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

    def _help_for(self, key):
        """F1 in an area window: the guide, filtered to that area."""
        from .start_page import areas

        self.show_workspace("guide")
        _raise_window(self)
        name = next((n for k, _, n, _ in areas() if k == key), "")
        self.guide_page.search.setText(name)

    def _table_menu(self, table, pos):
        from PySide6.QtWidgets import QApplication, QMenu

        from .plot.export import export_table, selected_text, table_rows

        menu = QMenu(table)
        selected = menu.addAction(self.tr("Copy") + "\tCtrl+C")
        selected.setEnabled(bool(table.selectedIndexes()))
        copy = menu.addAction(self.tr("Copy table"))
        export = menu.addAction(self.tr("Export table (CSV or LaTeX)…"))
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen is selected:
            QApplication.clipboard().setText(selected_text(table))
        elif chosen is export:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Export table"), "table.csv", "CSV (*.csv);;LaTeX (*.tex)"
            )
            if path:
                export_table(table, path)
        elif chosen is copy:
            header, rows = table_rows(table)
            QApplication.clipboard().setText("\n".join("\t".join(r) for r in [header, *rows]))

    def _show_key(self, key):
        if key in self.WINDOWED:  # opens its window; the main window keeps showing what it showed
            self.open_area(key)
        elif key:
            page = getattr(self, self.PAGES[key])
            self.pages.setCurrentWidget(self._frames.get(page, page))
            self._key = key
            self._follow_undo(page)

    def _follow_undo(self, page=None):
        """Edit -> Undo / Redo act on the page shown (on its open tab when it has tabs)."""
        if not hasattr(self, "undo_group"):  # pages shown while the window is built, before its menus
            return
        page = page or getattr(self, self.PAGES.get(self._key, ""), None)
        tabs = page if hasattr(page, "currentWidget") else getattr(page, "tabs", None)
        if tabs is not None and not getattr(tabs, "_follows_undo", False):
            tabs.currentChanged.connect(lambda _=0: self._follow_undo())
            tabs._follows_undo = True
        inner = tabs.currentWidget() if tabs is not None else None
        stack = getattr(inner, "undo_stack", None) or getattr(page, "undo_stack", None)
        if stack is not None and stack not in self.undo_group.stacks():
            self.undo_group.addStack(stack)
        self.undo_group.setActiveStack(stack)

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

    def send_to_photometry(self, paths, ask=True):
        """Images to the Photometry window, which is then shown. Several filters: one light curve per filter, so the
        user picks the filter (the largest group first)."""
        from PySide6.QtWidgets import QInputDialog

        from .workspaces import by_filter

        paths = [str(p) for p in paths if p]
        if not paths:
            return None
        groups = by_filter(paths)
        all_paths = None
        if len(groups) > 1 and ask:
            names = sorted(groups, key=lambda k: -len(groups[k]))
            labels = [self.tr("{f} ({n} images)").format(f=k or "—", n=len(groups[k])) for k in names]
            both = self.tr("All of them: a curve per filter and the colour index (stars marked in {f})").format(
                f=names[0] or "—"
            )  # item 11
            question = self.tr("A light curve is measured in one filter. Which one?")
            label, ok = QInputDialog.getItem(self, self.tr("Filter"), question, [*labels, both], 0, False)
            if not ok:
                return None
            if label == both:
                all_paths, paths = paths, groups[names[0]]
            else:
                paths = groups[names[labels.index(label)]]
        elif len(groups) > 1:
            paths = max(groups.values(), key=len)
        self.photometry_page.set_images(paths)
        self.photometry_page.all_filter_images = all_paths
        self.show_workspace("photometry")
        return paths

    def photometry_from_image(self, x, y, comparison=False):
        """Start photometry from the Images page: the open images (or the shown one) go to the Photometry window with
        this star as the target, or add it as a comparison star."""
        phot = self.photometry_page
        if not comparison:
            paths = self.image_page.open_paths() or [str(self.current_path)]
            phot.set_images(paths if str(self.current_path) in paths else [str(self.current_path)])
            if str(phot.images[0]) != str(self.current_path):  # stars are marked on the first frame in time
                self.statusBar().showMessage(
                    self.tr("Click the target on the first image in time, shown in the Photometry window."), 10000
                )
                self.show_workspace("photometry")
                return False
            phot.target = (x, y)
        else:
            phot.comps.append((x, y))
        phot._draw_markers()
        if not comparison:
            self.show_workspace("photometry")
        return True

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

    def _set_clock_offset(self, hours):
        """Camera clock - UTC, for every camera raw file and picture opened from now on (all pages)."""
        from ..io import bayer

        bayer.CLOCK_UTC_OFFSET_H = float(hours)
        self.settings.set("camera.clock_utc_offset", float(hours))

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

    def _fill_window_menu(self):
        from .kit.window import AreaWindow, _raise
        from .start_page import areas

        self.window_menu.clear()
        self._action(self.window_menu, self.tr("Main window"), lambda: _raise(self))
        for key in ("start", "project", "guide"):  # the main window's own pages (the sidebar is gone)
            self._action(self.window_menu, self._titles[key], lambda k=key: (_raise(self), self.show_workspace(k)))
        self.window_menu.addSeparator()
        open_now = AreaWindow.shown()
        for win in open_now:
            self._action(self.window_menu, win.windowTitle(), lambda w=win: _raise(w))
        if open_now:
            self.window_menu.addSeparator()
        sub = self.window_menu.addMenu(self.tr("Open an area"))
        for key, _, name, _ in areas():
            self._action(sub, name, lambda k=key: self.open_area(k))

    def report_problem(self, path=None):
        from .report import report_dialog

        return report_dialog(self, self.settings, self.engine, path)

    def _start_action(self, key):
        actions = {
            "new_project": self.new_project_dialog,
            "open_project": self.open_project_dialog,
            "open_fits": self.open_fits_dialog,
        }
        actions[key]() if key in actions else self.open_area(key)

    def _dock(self, name, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(name)  # stable id for saved layouts; never translated
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

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
    def _fill_plugins_menu(self):
        from ..engine import plugins, steps

        menu = self.plugins_menu
        menu.clear()
        ids = plugins.load_plugins()
        for sid in ids:
            doc = (steps.REGISTRY[sid].func.__doc__ or "").strip().splitlines()
            act = self._action(
                menu, doc[0].rstrip(".") if doc else sid, lambda _=False, i=sid: self.run_plugin(steps.REGISTRY[i])
            )
            act.setToolTip(sid)
        if not ids:
            menu.addAction(self.tr("No plugins installed")).setEnabled(False)
        for name, err in plugins.ERRORS.items():
            act = menu.addAction(self.tr("Failed to load: {f}").format(f=name))
            act.setToolTip(err)
            act.triggered.connect(lambda _=False, e=err: QMessageBox.warning(self, self.tr("Plugin error"), e))
        menu.addSeparator()
        self._action(menu, self.tr("Install the example plugins"), self.install_example_plugins)
        self._action(menu, self.tr("Open plugins folder"), self.open_plugins_folder)
        self._action(menu, self.tr("What are plugins?"), lambda: self.show_workspace("guide"))

    def install_example_plugins(self):
        """Copy the three example plugins into the plugins folder; they appear in this menu at once."""
        from ..engine import plugins

        copied = plugins.install_examples()
        plugins.load_plugins()
        text = (
            self.tr("Installed: {names}. They are now in the Plugins menu.").format(names=", ".join(copied))
            if copied
            else self.tr("The example plugins are already installed.")
        )
        self.statusBar().showMessage(text, 10000)
        return copied

    def open_plugins_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from ..engine.plugins import plugin_dir

        plugin_dir().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(plugin_dir())))

    def run_plugin(self, step, values=None):
        """Ask for the step's inputs and parameters (or use values) and run it as a task."""
        import json

        from .plugin_dialog import PluginDialog

        if values is None:
            dlg = PluginDialog(step, self)
            if not dlg.exec():
                return None
            values = dlg.values()
        inputs, params = values

        def done(out):
            text = json.dumps(out, indent=1, default=str)
            self.plugin_result = out
            QMessageBox.information(self, step.id, text[:4000] + ("…" if len(text) > 4000 else ""))

        return self.run_step(step.id, inputs, params, on_done=done)

    # --- project ------------------------------------------------------------
    def new_project_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("New project"), "", f"*{EXTENSION}")
        if path:
            self.open_project(Path(path).with_suffix(EXTENSION))

    def open_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Open project"), "", f"*{EXTENSION}")
        if path:
            self.open_project(Path(path))

    def open_project(self, path: Path):
        try:
            project = Project(path)  # first the new one: a file that is not a project must not close the open one
        except Exception as e:  # not a project file, damaged, no permission
            QMessageBox.warning(self, self.tr("Cannot open project"), f"{path}\n\n{translate(str(e))}")
            return False
        if self.engine.project:
            self.engine.project.close()
        self.engine.project = project
        self.project_page.name_label.setText(f"<b>{path}</b>")
        recent = [str(path)] + [p for p in self.settings.get("recent_projects", []) if p != str(path)]
        self.settings.set("recent_projects", recent[:10])
        self._refresh_files()
        self._update_title()
        return True

    def _refresh_files(self):
        self.files_list.clear()
        if not self.engine.project:
            return
        runs = self.engine.project.runs(full=False)  # results stay in the file until a run is selected
        table = self.project_page.runs_table
        table.blockSignals(True)
        table.setRowCount(len(runs))
        for row, r in enumerate(runs):
            for col, val in enumerate((r["step"], r["status"], r["started"], json.dumps(r["params"]))):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, r["id"])
                table.setItem(row, col, item)
        table.blockSignals(False)
        for f in self.engine.project.files():
            self.files_list.addItem(f"{Path(f['path']).name}  [{f['kind']}]")
            self.files_list.item(self.files_list.count() - 1).setData(Qt.UserRole, f["path"])

    # --- FITS ---------------------------------------------------------------
    def open_fits_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Open FITS"), "", images_filter())
        return self.open_many(paths)

    def open_many(self, paths):
        """Open several files at once (as MaxIm DL opens a window for each): all go into the list of open images,
        the first is shown; the others are read only when chosen."""
        if not paths:
            return False
        self.image_page.add_open(paths)
        return self.open_fits(Path(paths[0]), ask=True)

    def close_image(self, everything=False):
        """Take the shown image (or all) out of the list of open images; the files are not touched."""
        page = self.image_page
        if everything:
            for p in page.open_paths():
                page.remove_open(p)
            following = None
        else:
            following = page.remove_open(self.current_path) if self.current_path else None
        if following:
            return self.open_fits(Path(following))
        self.current_path, self.wcs = None, None
        self.viewer.clear()
        page.set_header(None)
        self.header_table.setRowCount(0)
        for act in (self.save_action, self.picture_action, self.solve_action, self.process_menu):
            act.setEnabled(False)
        if hasattr(self, "split_action"):
            self.split_action.setEnabled(False)
        self._update_title()
        return True

    def open_fits(self, path: Path, extension=None, ask=False):
        """Open an image. ask (the user opens a file): a file with several image extensions asks which one, and the
        chosen one is opened as a file of its own, so every tool works on what is shown. Results the application
        writes (stacks with a coverage map, drizzle with a weight map) open on their first image without asking."""
        try:
            from ..io.bayer import fits_copy

            path = fits_copy(path)  # a camera raw file or a picture (phone, JPEG, TIFF): its FITS copy
            choices = fitsio.image_hdus(path)
            if extension is None and ask and len(choices) > 1:
                from PySide6.QtWidgets import QInputDialog

                labels = [c[1] for c in choices]
                label, ok = QInputDialog.getItem(
                    self, self.tr("Image extension"), self.tr("This file holds several images:"), labels, 0, False
                )
                if not ok:
                    return False
                extension = choices[labels.index(label)][0]
            if extension is not None and choices and extension != choices[0][0]:
                path = fitsio.extract_extension(path, extension)
            data, header, _ = fitsio.read_image(path)
        except Exception as e:  # unreadable or non-image file: tell the user, keep the current image
            QMessageBox.warning(self, self.tr("Cannot open file"), f"{path}\n\n{translate(str(e))}")
            return False
        self.current_path = path
        try:
            from astropy.wcs import WCS

            wcs = WCS(header)
            self.wcs = wcs if wcs.has_celestial else None
        except Exception:
            self.wcs = None
        self.viewer.set_image(data, wcs=self.wcs)
        self.image_page.set_header(header, self.wcs)
        self._show_header(header)
        self.save_action.setEnabled(True)
        self.picture_action.setEnabled(True)
        if getattr(self, "_levels", None) is not None and self._levels.isVisible():
            self._levels.refresh()
        self.solve_action.setEnabled(True)
        self.process_menu.setEnabled(True)
        if hasattr(self, "split_action"):  # a colour camera's raw image (its Bayer pattern in the header)
            from ..io.bayer import pattern_of

            self.split_action.setEnabled(bool(pattern_of(header)))
        self.image_page.add_open([path], current=path)
        if self.engine.project:
            self.engine.project.add_file(path, "image")
            self._refresh_files()
        self._update_title()
        self.show_workspace("image")
        return True

    def _show_header(self, header):
        cards = list(header.cards)
        table = self.header_table
        table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            for col, val in enumerate((card.keyword, str(card.value), card.comment)):
                item = QTableWidgetItem(val)
                item.setToolTip(val if col else "")  # the whole value or comment, however narrow the column
                table.setItem(row, col, item)
        table.resizeColumnsToContents()  # values readable at once; every column can still be dragged wider
        for col, most in ((0, 120), (1, 260)):
            table.setColumnWidth(col, min(table.columnWidth(col), most))

    def save_as_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save FITS as"), "", FITS_FILTER)
        if path:
            self.save_as(Path(path))

    def save_as(self, destination: Path):
        """Save a copy of the current file through the task queue. Returns the Task."""
        return self.run_step(
            "fits.save_as", {"source": str(self.current_path), "destination": str(destination)}, {"overwrite": True}
        )

    # --- tasks --------------------------------------------------------------
    def run_step(self, step_id, inputs, params=None, on_done=None, on_fail=None, area=None):
        """Run a step as a task; on_done(outputs) is called on the GUI thread when it succeeds, on_fail(message)
        (instead of the error box) when it fails. Never touch widgets from task.add_callback: that runs on a
        background thread. area: the area that asked for it; its window (if it has one) shows the progress."""
        task = self.engine.run_step(step_id, inputs, params)
        if area in self.area_windows:
            self.area_windows[area].track(task)
        if on_done:
            self._on_done[task.id] = on_done
        if on_fail:
            self._on_fail[task.id] = on_fail
        task.add_callback(self.taskUpdated.emit)
        self.taskUpdated.emit(task)
        return task

    def run_step_for(self, area, step_id, inputs, params=None, on_done=None, on_fail=None):
        """run_step for an area: its window shows the progress."""
        return self.run_step(step_id, inputs, params, on_done=on_done, on_fail=on_fail, area=area)

    def run_automation(self, auto, inputs):
        """Run an automation task by task: each step starts when the previous one has finished."""
        from ..engine import automation

        gen, page, n = automation.calls(auto, inputs), self.automation_page, [0]

        def advance(out=None):
            try:
                call = next(gen) if out is None else gen.send(out)
                n[0] += 1
                page.step_started(n[0], call[0])
                self.run_step(*call, on_done=advance, on_fail=page.failed)  # a failed step stops the chain
            except StopIteration as stop:
                page.finished(stop.value, out)
            except Exception as e:  # a link to a missing field, a refused input: say where it stopped
                page.failed(str(e))

        advance()

    def _load_sequence(self, target):
        self.observe_page.load_sequence(target)
        self.show_workspace("observe")

    def _on_task(self, task):
        states = {
            "queued": self.tr("queued"),
            "running": self.tr("running"),
            "done": self.tr("done"),
            "failed": self.tr("failed"),
            "cancelled": self.tr("cancelled"),
        }
        from .step_names import step_name

        text = f"{step_name(task.name)} — {states[task.state]} {int(task.progress * 100)}% {translate(task.message)}"
        if task.id not in self._task_items:
            self.tasks_list.addItem(text)
            self._task_items[task.id] = (task, self.tasks_list.count() - 1)
        self.tasks_list.item(self._task_items[task.id][1]).setText(text)
        self.progress.setVisible(any(not t.finished for t, _ in self._task_items.values()))
        self.progress.setValue(int(task.progress * 100))
        from .kit.window import AreaWindow

        for win in AreaWindow.alive():  # the area window that started it shows it in its status bar
            win.task_update(task)
        if task.finished:
            done = self._on_done.pop(task.id, None)
            fail = self._on_fail.pop(task.id, None)
            if done and task.state == "done":
                done(task.result())
            self._refresh_files()
            if fail and task.state == "failed":
                fail(task_error(task.error))
                return
        if task.state == "failed":
            box = QMessageBox(
                QMessageBox.Warning,
                self.tr("Task failed"),
                f"{step_name(task.name)}\n\n{task_error(task.error)}{advice.for_trace(task.error)}",
                parent=self,
            )
            box.setDetailedText(str(task.error))  # the full traceback, for reports
            box.open()

    # --- calibration --------------------------------------------------------
    def scan_raw(self, folder, lights=""):
        if folder or lights:
            inputs = {"folder": folder or ""}
            if lights:
                inputs["lights"] = lights
            return self.run_step(
                "calibration.scan",
                inputs,
                {"clock_utc_offset": self.calibrate_page.clock_offset.value()},
                on_done=lambda out: self.calibrate_page.show_frames(
                    out["frames"], out["problems"], out.get("raw_converted", 0)
                ),
                area="calibrate",
            )

    def calibrate(self, frames, output_dir, params):
        def done(out):
            if self.engine.project:
                for p in out["masters"]:
                    self.engine.project.add_file(Path(p), "master")
                for p in out["calibrated"]:
                    self.engine.project.add_file(Path(p), "calibrated")
            self.calibrate_page.show_result(out)
            if out["calibrated"] and not self.photometry_page.images:  # next step of the workflow is ready
                from .workspaces import by_filter

                groups = by_filter(out["calibrated"])  # one filter only; a colour camera's green (TG) first
                self.photometry_page.set_images(groups.get("TG") or max(groups.values(), key=len))

        return self.run_step(
            "calibration.run", {"frames": frames, "output_dir": output_dir}, params, on_done=done, area="calibrate"
        )

    def _spectrum_done(self, spectrum):
        self.spectro_page.reduce_tab.show_spectrum(spectrum)
        if spectrum.get("path"):
            if self.engine.project:
                self.engine.project.add_file(Path(spectrum["path"]), "spectrum")
            self.spectro_page.velocity_tab.add_files([spectrum["path"]])  # ready for radial velocities

    def _echelle_done(self, result):
        self.spectro_page.echelle_tab.show_result(result)
        if result.get("path"):
            if self.engine.project:
                self.engine.project.add_file(Path(result["path"]), "spectrum")
            self.spectro_page.velocity_tab.add_files([result["path"]])

    def _telluric_done(self, result):
        self.spectro_page.telluric_tab.show_result(result)
        if result.get("path") and self.engine.project:
            self.engine.project.add_file(Path(result["path"]), "spectrum")

    # --- planning -----------------------------------------------------------
    def resolve_target(self, name):
        from ..settings import config_dir

        return self.run_step(
            "planning.resolve",
            {"name": name, "cache_file": str(config_dir() / "targets.json")},
            on_done=lambda out: self.plan_page.add_target(out["target"]),
            on_fail=self.plan_page.status.setText,
        )

    def lookup_ephemeris(self, name):
        return self.run_step(
            "planning.ephemeris",
            {"name": name},
            on_done=lambda out: self.plan_page.add_target(out["target"]),
            on_fail=self.plan_page.status.setText,
        )

    # --- photometry ---------------------------------------------------------
    def _photometry_next(self, where, path):
        """From a measured light curve to the page that fits it (the period page already has the curve)."""
        if where == "orbits" and path:
            self.models_page.file.edit.setText(path)
        self.show_workspace(where)

    def measure_light_curve(self, images, target, comps, coord, params):
        inputs = {"images": images, "target_xy": target, "comps_xy": comps}
        if coord:
            inputs["coord"] = coord
        params = dict(params)
        if params.get("extra_xy"):  # check stars and further targets are inputs of the step
            inputs["extra_xy"] = params.pop("extra_xy")
        params.pop("extra_xy", None)
        if params.get("ref_image"):  # the frame the stars were marked on
            inputs["ref_image"] = params.pop("ref_image")
        params.pop("ref_image", None)

        def done(out):
            lc = out["light_curve"]
            self.photometry_page.show_light_curve(lc)
            self.period_page.set_light_curve(
                lc["time"], lc["rel_flux"], self.tr("the Photometry window"), err=lc.get("rel_flux_err")
            )

        every = getattr(self.photometry_page, "all_filter_images", None)
        if every:  # item 11: every filter of the night, and the colour index

            def done_all(out):
                from .workspaces import by_filter

                main = next(iter(by_filter(images)), "")  # the filter the stars were marked in
                curves = out["curves"]
                done({"light_curve": curves.get(main) or next(iter(curves.values()))})
                self.photometry_page.show_colour(out["colour"], curves)

            inputs["images"] = list(every)
            return self.run_step("photometry.multifilter", inputs, params, on_done=done_all, area="photometry")
        return self.run_step("photometry.light_curve", inputs, params, on_done=done, area="photometry")

    def search_period(self, time, flux, params):
        params = dict(params)
        inputs = {"time": time, "flux": flux}
        if params.get("err") is not None:
            inputs["err"] = params.pop("err")
        params.pop("err", None)
        return self.run_step(
            "timeseries.period", inputs, params, on_done=self.period_page.show_result, area="timeseries"
        )

    def time_minimum(self, light_curve, params):
        pp, page = self.period_page, self.photometry_page
        if "period" not in params and pp.best and pp.time and len(pp.time) == len(light_curve["time"]):
            params = params | {"period": float(pp.best), "t0": float(pp._t0())}  # from the period search just made
            page.period.setText(f"{params['period']:.8f}")
            page.t0.setText(f"{params['t0']:.6f}")

        def done(out):
            m = out["minimum"]
            page.show_minimum(m)
            for x in m.get("minima", [m]):  # ready for the O-C diagram
                self.oc_page.add_minimum(x["time"], x["error"], "this work", x.get("kind", "I"))
            obj = (page.field or {}).get("object") or {}
            if obj.get("in_field") and not self.oc_page.star.text():  # the star the files name, for Look up
                self.oc_page.star.setText(obj["name"])
            if params.get("t0") and not self.oc_page.t0.text():
                self.oc_page.t0.setText(repr(params["t0"]))
                self.oc_page.period.setText(repr(params["period"]))

        return self.run_step(
            "timeseries.minimum", {"light_curve": light_curve}, params, on_done=done, area="photometry"
        )

    # --- misc ---------------------------------------------------------------

    def _update_title(self):
        parts = [BRAND.display_name]
        if self.engine.project:
            parts.insert(0, self.engine.project.path.stem)
        if self.current_path:
            parts.insert(0, self.current_path.name)
        self.setWindowTitle(" — ".join(parts))

    def set_language(self, code):
        self.settings.set("ui.language", code)
        QMessageBox.information(
            self,
            self.tr("Language"),
            self.tr("The new language will be used after restarting {app}.").format(app=BRAND.display_name),
        )

    def start_tour(self):
        return tour.start(self)

    def set_theme(self, code):
        from PySide6.QtWidgets import QApplication

        from . import theme

        self.settings.set("ui.theme", code)
        theme.apply(QApplication.instance(), code, theme.font_size(self.settings))
        self._paint_glyphs()  # the symbols take the text colour of the new theme
        for canvas in self.findChildren(PlotCanvas):  # plots already drawn pick up the new colours
            canvas.figure.set_facecolor(theme.colors(code)["window"])
            canvas.draw()

    def _change_font(self, step):
        from PySide6.QtWidgets import QApplication

        from . import theme

        size = theme.change_font(QApplication.instance(), self.settings, step)
        self._paint_glyphs()
        self.statusBar().showMessage(self.tr("Text size: {pt:g} pt").format(pt=size), 3000)
        return size

    def set_compute(self, code):
        self.settings.set("compute.device", code)
        compute.set_mode(code)  # new worker processes inherit it
        self.statusBar().showMessage(compute.describe(), 8000)

    def update_time_tables(self, quiet=False):
        """Download newer Earth-orientation and leap-second tables (plans/architecture.md ARC-1). quiet: the weekly
        update at start-up, which only reports in the status bar and stays silent when offline."""
        from ..core import earth_orientation

        def done(out):
            earth_orientation.use_stored()
            self.statusBar().showMessage(self.tr("Earth-rotation tables updated: {0}").format(out["status"]), 15000)

        def failed(error):
            if quiet:
                self.statusBar().showMessage(self.tr("Earth-rotation tables not updated (offline?)"), 8000)
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Earth-rotation tables"),
                    self.tr(
                        "The tables could not be downloaded: {0}\n\nThe tables in use stay; nothing stops working. "
                        "Try again when online."
                    ).format(str(error).strip().splitlines()[-1]),
                )

        return self.run_step("app.update_time_tables", {}, {}, on_done=done, on_fail=failed)

    def practice_data(self, folder=None):
        """Simulated raw frames of an eclipsing binary night, for the Guide's first-night exercise."""
        folder = folder or QFileDialog.getExistingDirectory(self, self.tr("Folder for the practice data"))
        if not folder:
            return None

        def done(out):
            self.show_workspace("guide")
            self.guide_page.search.setText(self.tr("practice"))
            self.statusBar().showMessage(
                self.tr("Practice data in {f}: follow 'Your first night' in the Guide.").format(f=folder), 15000
            )

        return self.run_step("sample.night", {"folder": folder}, {}, on_done=done)

    def check_updates(self, fetch=None):
        """Ask GitHub for the newest release in the background; the answer comes in a message box."""
        import threading

        from .. import updates

        if not getattr(self, "_updates_connected", False):
            self.updateChecked.connect(self._show_update)
            self._updates_connected = True
        args = {"fetch": fetch} if fetch else {}
        threading.Thread(target=lambda: self.updateChecked.emit(*updates.check(**args)), daemon=True).start()

    def _show_update(self, release, error):
        if error:
            text = self.tr("Could not check for updates: {e}").format(e=translate(error))
        elif release:
            text = self.tr("Version {v} is available (you have {c}).").format(v=release["version"], c=__version__)
            link = self.tr("Open the download page")
            text += f"<br><a href='{release['url']}'>{link}</a>"
        else:
            text = self.tr("You have the latest version ({c}).").format(c=__version__)
        self.update_box = QMessageBox(QMessageBox.Information, self.tr("Updates"), text, parent=self)
        self.update_box.setTextFormat(Qt.RichText)
        self.update_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.update_box.open()

    def about(self):
        QMessageBox.about(
            self,
            self.tr("About {app}").format(app=BRAND.display_name),
            f"<b>{BRAND.display_name}</b> {__version__}<br>{BRAND.organization}<br>"
            f"<a href='{BRAND.homepage}'>{BRAND.homepage}</a><br><br>{compute.describe()}",
        )

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

    from .workspaces import PlotCanvas

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
