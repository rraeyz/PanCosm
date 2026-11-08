"""Main window: workspace sidebar, the pages behind it, and running tasks."""

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence, QUndoGroup
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
from ..display import INTERVALS, STRETCHES
from ..engine.core import Engine
from ..engine.project import EXTENSION, Project
from ..io import fits as fitsio
from ..settings import Settings
from .area_window import _raise as _raise_window
from .files import images_filter
from .i18n import LANGUAGES
from .messages import task_error, translate
from .workspaces import (
    CalibratePage,
    ImagePage,
    LightCurvePage,
    OCPage,
    PhotometryPage,
    PlotCanvas,
    ProjectPage,
    StartPage,
)

FITS_FILTER = "FITS (*.fits *.fit *.fts *.fits.gz *.fit.gz)"


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
        page = getattr(win, "_make_" + self.name)()
        vars(win)[self.name] = page  # later reads find the page directly
        win._place(self.name, page)
        return page


class MainWindow(QMainWindow):
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
        self._fill_image_toolbar()
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
        titles = {
            "start": self.tr("Start"),
            "plan": self.tr("Plan"),
            "observe": self.tr("Observe"),
            "calibrate": self.tr("Calibrate"),
            "image": self.tr("Images"),
            "photometry": self.tr("Photometry"),
            "timeseries": self.tr("Light curves & O-C"),
            "oc": self.tr("O−C"),
            "spectroscopy": self.tr("Spectroscopy"),
            "orbits": self.tr("Orbits & models"),
            "remotesensing": self.tr("Remote sensing"),
            "automation": self.tr("Automation"),
            "project": self.tr("Project"),
            "guide": self.tr("Guide"),
        }
        self._titles = titles  # the main window's own pages and the areas' old names (tests, tools)
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

        from .table_view import DataTable

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
            bar.insertMenu(win.window_menu.menuAction(), menu)
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

    def _place_in_window(self, key, page):
        """The page, as it is, in an area window of its own (scrolling inside it when the window is smaller)."""
        from PySide6.QtWidgets import QFrame, QScrollArea

        from .area_window import AreaWindow
        from .start_page import areas

        if key == "photometry":
            self._photometry_window(page)
            return
        if key == "spectroscopy":
            self._spectroscopy_window(page)
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
        builder = getattr(self, f"_{key}_menus", None)
        if builder is not None:  # the area's own menus and toolbar (interface I6c)
            builder(page, win)
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

    def _photometry_window(self, page):
        """Photometry in its full window (plans/interface.md I5): the image in the middle, the numbered steps in a
        panel on the left, the results (light curve, stars, detrending, minimum, export) in a panel below; a
        toolbar for the frequent actions; every panel can be pulled out and is remembered."""
        from PySide6.QtGui import QAction

        from .area_window import AreaWindow
        from .start_page import areas

        parts = page.window_parts()
        kinds = {}

        def mirror(widget, short=None, kind=None):
            act = _mirror(widget, page, short)
            if kind:
                kinds[act] = kind
            return act

        images = mirror(page.load_button, self.tr("Images…"), "open")
        blink = mirror(page.blink, self.tr("Blink"), "blink")
        prev, nxt = (mirror(page.prev_frame, self.tr("Previous frame"), "previous"),
                     mirror(page.next_frame, self.tr("Next frame"), "next"))  # fmt: skip
        for act, text in ((prev, self.tr("Previous frame")), (nxt, self.tr("Next frame"))):
            act.setText(text)  # the tool buttons show only an arrow
        bad = mirror(page.quality_button, self.tr("Bad frames"), "bad_frames")
        comps = mirror(page.suggest_button, self.tr("Comparisons"), "comparisons")
        radii = mirror(page.apertures_button, self.tr("Radii"), "radii")
        measure = mirror(page.measure_button, self.tr("Measure"), "measure")
        minimum = mirror(page.minimum_button, self.tr("Minimum"), "minimum")
        export = mirror(page.export_button, self.tr("Export"), "export")
        target = mirror(page.make_target)
        target.setText(self.tr("Make the chosen variable star the target"))  # the button sits beside its list
        check = QAction(self.tr("Mark check stars"), page)
        check.setToolTip(self.tr("The next clicks on the image mark check stars (K1, K2…)"))
        check.triggered.connect(lambda: page.click_role.setCurrentIndex(page.click_role.findData("check")))
        menus = [  # the approved table (plans/interface.md I6c), in the order of the work
            (self.tr("F&rames"), [images, mirror(page.live_button), blink, prev, nxt, None, bad,
                                  mirror(page.drop_bad), mirror(page.restore_button)]),
            (self.tr("&Stars"), [comps, target, check, None, mirror(page.clear_button)]),
            (self.tr("&Measure"), [radii, mirror(page.follow_seeing), mirror(page.psf), None, measure,
                                   mirror(page.catalog_button), mirror(page.pol_button)]),
            (self.tr("&Analyse"), [mirror(page.detrend_button), mirror(page.undo_detrend), None, minimum, None,
                                   mirror(page.go_model), mirror(page.go_period)]),
        ]  # fmt: skip
        actions = [images, blink, prev, nxt, None, bad, comps, radii, measure, None, minimum, export]
        name = next(n for k, _, n, _ in areas() if k == "photometry")
        win = AreaWindow(
            "photometry", name, self.settings, parts["view"], steps=parts["steps"],
            panels=[("results", self.tr("Results: light curve, stars, minimum, export"), parts["results"],
                     Qt.BottomDockWidgetArea)],
            menus=menus, toolbar=actions,
            undo_stack=_undo_source(page), open_files=page.set_images, file_filter=images_filter(), parent=self,
        )  # fmt: skip
        from PySide6.QtWidgets import QMenu

        exports = QMenu(self.tr("&Export"), win)  # File → Export, just before Close window
        win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
        exports.addActions([export, mirror(page.aavso_button)])
        win.set_icons(kinds)  # icons, the names in the tooltips (View → Toolbar text shows them too)
        page.setParent(win)  # the page keeps the state and the logic, unseen
        page.hide()
        page.results_dock = win.docks["results"]
        page.results_dock.setVisible(page.target is not None or page.lc_raw is not None)
        self._frames[page] = parts["steps"]
        win.setWindowIcon(self.windowIcon())
        win.help_requested.connect(self._help_for)
        self.area_windows["photometry"] = win
        self._complete_menus(win)

    def _calibrate_menus(self, page, win):
        """Calibration: Frames, Masters, Process, Send (interface I6c.4), from the page's own controls."""

        def named(widget, text, short=None):
            act = _mirror(widget, page, short)
            act.setText(text)  # the button's text carries its place in the steps ("3.", "Browse…")
            return act

        lights = named(page.lights_browse, self.tr("Lights folder…"), self.tr("Lights"))
        frames = named(page.frames_browse, self.tr("Calibration frames folder…"))
        scan = _mirror(page.scan_button)
        run = named(page.run_button, self.tr("Calibrate"))
        stack = named(page.stack_button, self.tr("Stack into one deep picture"), self.tr("Stack"))
        send = named(page.photometry_button, self.tr("Send to Photometry →"), self.tr("Photometry"))
        win.add_menus(
            [
                (self.tr("F&rames"), [lights, frames, _mirror(page.add_folder_button), None, scan, None,
                                      _mirror(page.remove_button), _mirror(page.clear_button)]),
                (self.tr("&Masters"), [_mirror(page.cosmics), _mirror(page.optimize_dark), _mirror(page.fix_defects),
                                       _mirror(page.split_colour), _mirror(page.spectra)]),
                (self.tr("&Process"), [run, None, stack, _mirror(page.drizzle)]),
                (self.tr("Se&nd"), [send]),
            ],
            toolbar=[lights, scan, None, run, stack, None, send],
        )  # fmt: skip
        win.set_icons({lights: "open_folder", scan: "scan", run: "calibrate", stack: "stack", send: "send"})

    def _timeseries_menus(self, page, win):
        """Light curves and period: Data, Search, Send and File → Load / Download / Save (interface I6c.6); each item
        shows its tab first."""
        from PySide6.QtWidgets import QMenu

        pp, fp, vf = page.period_page, page.frequency_page, page.varfind_page

        def tab(widget, owner, text=None, short=None):
            act = _mirror(widget, page, short)
            if text:
                act.setText(text)
            act.triggered.connect(lambda _=False: page.setCurrentWidget(owner))
            return act

        load = tab(pp.load_button, pp, short=self.tr("Load"))
        fetch = tab(pp.fetch_button, pp, self.tr("Download a light curve (TESS, Kepler, ZTF, AAVSO)"),
                    self.tr("Download"))  # fmt: skip
        save = tab(pp.save_button, pp, short=self.tr("Save"))
        search = tab(pp.search_button, pp, self.tr("Period search"))
        freq = tab(fp.button, fp)
        var = tab(vf.button, vf)
        win.add_menus(
            [
                (self.tr("&Data"), [tab(pp.delete_mode, pp), tab(pp.clip_button, pp), tab(pp.bin_button, pp),
                                    tab(pp.units_button, pp), None, tab(pp.undo_button, pp)]),
                (self.tr("Se&arch"), [search, freq, None, tab(vf.choose_button, vf), var]),
                (self.tr("Se&nd"), [tab(fp.to_oc, fp), tab(vf.send, vf)]),
            ],
            toolbar=[load, fetch, save, None, search, freq, var],
        )  # fmt: skip
        files = QMenu(self.tr("&Light curve"), win)  # File → Light curve, before Close window
        win.file_menu.insertMenu(win.file_menu.actions()[-1], files)
        files.addActions([fetch, save])  # loading is File → Open… (Ctrl+O, or drop a file)
        win.set_icons({load: "open", fetch: "download", save: "save", search: "period_search", freq: "frequency",
                       var: "variable_search"})  # fmt: skip

    def _oc_menus(self, page, win):
        """O−C: Ephemeris, Models, File → Load minima / Export (interface I6c.6)."""
        from PySide6.QtGui import QActionGroup
        from PySide6.QtWidgets import QMenu

        def named(widget, text=None, short=None):
            act = _mirror(widget, page, short)
            if text:
                act.setText(text)
            return act

        load = named(page.load_button, self.tr("Load minimum times…"), self.tr("Load"))
        look = named(page.look_up, self.tr("Look up the ephemeris (VSX)"), self.tr("Look up"))
        fit = named(page.fit_button, short=self.tr("Fit"))
        export = named(page.results_button, short=self.tr("Export"))
        models = [named(r) for r in (page.linear, page.quadratic, page.ltte, page.apsidal)]
        group = QActionGroup(win)  # one model at a time, as the radio buttons
        for act in models:
            group.addAction(act)
        win.add_menus(
            [
                (self.tr("&Ephemeris"), [look, None, models[0], models[1], None, fit]),
                (self.tr("&Models"), [models[2], models[3], None, named(page.use_mcmc)]),
            ],
            toolbar=[load, look, fit, export],
        )
        files = QMenu(self.tr("&Export"), win)
        win.file_menu.insertMenu(win.file_menu.actions()[-1], files)  # loading minima is File → Open… (Ctrl+O)
        files.addAction(export)
        win.set_icons({load: "open", look: "lookup", fit: "fit_model", export: "export"})

    def _orbits_menus(self, page, win):
        """Models: Fit, Visual orbit, File → Compare / Export (interface I6c.7); each item shows its tab first."""
        from PySide6.QtWidgets import QMenu

        binary, visual = page.tabs.widget(0), page.visual_tab

        def tab(widget, owner, text=None, short=None):
            act = _mirror(widget, page, short)
            if text:
                act.setText(text)
            act.triggered.connect(lambda _=False: page.tabs.setCurrentWidget(owner))
            return act

        fit = tab(page.fit_button, binary, self.tr("Fit the eclipse or transit model"), self.tr("Fit"))
        posterior = tab(page.posterior_button, binary, short=self.tr("Posterior"))
        orbit = tab(visual.fit_button, visual, short=self.tr("Visual orbit"))
        export = tab(page.results_button, binary, short=self.tr("Export"))
        win.add_menus(
            [
                (self.tr("F&it"), [fit, posterior, None, tab(page.use_mcmc, binary), tab(page.use_orbit, binary)]),
                (self.tr("&Visual orbit"), [tab(visual.load_button, visual), orbit]),
            ],
            toolbar=[win.file_menu.actions()[0], fit, posterior, orbit, None, export],
        )
        win.file_menu.insertAction(win.file_menu.actions()[-1], tab(page.overlay_button, binary))
        exports = QMenu(self.tr("&Export"), win)
        win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
        exports.addActions([export, tab(page.phoebe_button, binary), tab(page.wd_button, binary),
                            tab(page.transit_button, binary)])  # fmt: skip
        win.set_icons({win.file_menu.actions()[0]: "open", fit: "fit_model", posterior: "posterior",
                       orbit: "visual_orbit", export: "export"})  # fmt: skip

    def _spectroscopy_menus(self, page, win):
        """Reduce, Lines, Spectrum, Measure, Velocity and File → Export (interface I6c.5, the table agreed from
        IRAF's tasks and iSpec's Operations / Parameters menus): every item does what its job's button does, and
        shows that job first."""
        from PySide6.QtWidgets import QMenu

        red, ech, tel, vel, cube, tools = (page.reduce_tab, page.echelle_tab, page.telluric_tab, page.velocity_tab,
                                            page.cube_tab, page.tools_tab)  # fmt: skip

        def job(tab, widget, text=None):
            act = _mirror(widget, page)
            if text:
                act.setText(text)
            act.triggered.connect(lambda _=False: page.tabs.setCurrentWidget(tab))
            return act

        def either(text, which):
            """One item for the long-slit and the échelle job: the one shown, else long slit."""
            act = QAction(text, page)

            def run():
                tab = ech if page.tabs.currentWidget() is ech else red
                page.tabs.setCurrentWidget(tab)
                getattr(tab, which).click()

            act.triggered.connect(run)
            act.setToolTip(getattr(red, which).toolTip())
            return act

        menus = [
            (self.tr("&Reduce"), [
                job(red, red.extract_button, self.tr("Extract the long-slit spectrum")), None,
                job(ech, ech.find_button, self.tr("Find the échelle orders on the flat")),
                job(ech, ech.extract_button, self.tr("Extract the échelle orders")), None,
                job(cube, cube.load_button), job(cube, cube.show_button),
                job(cube, cube.save_button, self.tr("Save the cube region's spectrum…"))]),
            (self.tr("&Lines"), [
                job(red, red.reference_button), job(ech, ech.database_button), None,
                job(red, red.solve_button, self.tr("Fit the wavelengths (long slit)")),
                job(ech, ech.solve_button, self.tr("Fit the wavelengths, merge the orders (échelle)")), None,
                either(red.refit_button.text(), "refit_button"), either(red.forget_button.text(), "forget_button")]),
            (self.tr("S&pectrum"), [
                job(tools, tools.open_button), None, job(tools, tools.normalise_button), job(tools, tools.pick),
                job(tools, tools.through_button), job(tools, tools.smooth_button),
                job(tools, tools.resample_button), None, job(tools, tools.combine_button),
                job(tools, tools.response_button), job(tools, tools.apply_resp), None,
                job(tel, tel.button, self.tr("Telluric correction")),
                job(tools, tools.open_b_button),
                job(tools, tools.arith_button, self.tr("Arithmetic with spectrum B"))]),
            (self.tr("Mea&sure"), [
                job(tools, tools.measure_button, self.tr("Measure a line")), job(tools, tools.vr_button),
                job(tools, tools.series_button), None, job(tools, tools.atm_button),
                job(vel, vel.type_button)]),
            (self.tr("&Velocity"), [
                job(vel, vel.rv_button), job(vel, vel.separate_button), job(vel, vel.orbit_button)]),
        ]  # fmt: skip
        win.add_menus(menus)
        exports = QMenu(self.tr("&Export"), win)  # File → Export, just before Close window
        win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
        exports.addActions([job(tools, tools.save_button, self.tr("Save the spectrum as…")),
                            job(tools, tools.bess_button)])  # fmt: skip

    def _spectroscopy_window(self, page):
        """Spectroscopy in its own window (plans/spectroscopy.md step 1.1): the job chosen in the toolbar (and the
        Job menu), its view in the middle, its steps in the left panel."""
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtGui import QAction, QActionGroup

        from .area_window import AreaWindow
        from .start_page import areas

        parts = page.window_parts()
        group, actions = QActionGroup(page), []
        for i, (job, tip) in enumerate(zip(parts["jobs"], page.JOB_TIPS, strict=True)):
            act = QAction(job, page)
            act.setCheckable(True)
            act.setToolTip(QCoreApplication.translate("SpectroscopyPage", tip))
            act.setStatusTip(act.toolTip())
            act.triggered.connect(lambda _=False, k=i: page.tabs.setCurrentIndex(k))
            group.addAction(act)
            actions.append(act)
        page.tabs.currentChanged.connect(lambda i: actions[i].setChecked(True))
        actions[page.tabs.currentIndex()].setChecked(True)
        handler, file_filter = self._opener("spectroscopy", page)
        name = next(n for k, _, n, _ in areas() if k == "spectroscopy")
        win = AreaWindow(
            "spectroscopy", name, self.settings, parts["view"], steps=parts["steps"],
            menus=[(self.tr("&Job"), actions)], toolbar=actions, undo_stack=_undo_source(page),
            open_files=handler, file_filter=file_filter, parent=self,
        )  # fmt: skip
        jobs = ("long_slit", "echelle", "telluric", "velocity", "cube", "spectrum_tools")
        win.set_icons(dict(zip(actions, jobs, strict=True)))
        self._spectroscopy_menus(page, win)
        page.setParent(win)  # the page keeps the state and the logic, unseen
        page.hide()
        self._frames[page] = parts["steps"]
        win.setWindowIcon(self.windowIcon())
        win.help_requested.connect(self._help_for)
        self.area_windows["spectroscopy"] = win
        self._complete_menus(win)

    def _complete_menus(self, win):
        """The common menus of every area window (interface I6c.2): Edit → Copy and the settings, Help → the tour,
        updates and About — the main window's own actions and Settings menu, so they act the same everywhere."""
        if not hasattr(self, "settings_menu"):  # built before the main window's menus: done right after them
            self.__dict__.setdefault("_pending_menus", []).append(win)
            return
        from PySide6.QtWidgets import QApplication, QTableWidget

        from .export import selected_text

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

        from .export import export_table, selected_text, table_rows

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
        act = getattr(self, "expert_action", None)
        if act is not None and act.isChecked() != (mode == "expert"):
            act.setChecked(mode == "expert")
        start = self.__dict__.get("start_page")
        if start is not None:
            (start.expert if mode == "expert" else start.basic).setChecked(True)

    def _make_image_page(self):
        page = ImagePage(self)
        page.header_save_requested.connect(self.save_header_changes)
        page.image_chosen.connect(lambda p: self.open_fits(Path(p)))
        page.viewer.context_requested.connect(lambda x, y, pos: self.image_menu(x, y).exec(pos))
        return page

    def image_menu(self, x, y):
        """Right click on the image: what can be done with the star or place under the mouse."""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        page = self.image_page
        self._action(
            menu,
            self.tr("Send the open images to Photometry"),
            lambda: self.send_to_photometry(page.open_paths() or [str(self.current_path)]),
        )
        menu.addSeparator()
        self._action(menu, self.tr("Measure this star"), lambda: page.measure_star(x, y))
        self._action(menu, self.tr("Photometry: this star as the target"), lambda: self.photometry_from_image(x, y))
        comp = self._action(
            menu, self.tr("Photometry: add as a comparison star"), lambda: self.photometry_from_image(x, y, True)
        )
        phot = self.__dict__.get("photometry_page")
        comp.setEnabled(bool(phot and phot.images and phot.target and str(phot.images[0]) == str(self.current_path)))
        menu.addSeparator()
        self._action(menu, self.tr("Copy the position"), lambda: self._copy_position(x, y))
        simbad = self._action(menu, self.tr("Look up in SIMBAD"), lambda: self._simbad(x, y))
        simbad.setEnabled(self.wcs is not None)
        menu.addSeparator()
        self._action(
            menu,
            self.tr("Centre the view here"),
            lambda: self.viewer.centerOn(x + 0.5, page.viewer.data.shape[0] - 0.5 - y),
        )
        menu.addAction(self.fit_action)
        self._action(menu, self.tr("Statistics of the whole image"), page.measure_whole)
        return menu

    def _sky(self, x, y):
        return self.wcs.pixel_to_world(x, y) if self.wcs is not None else None

    def _copy_position(self, x, y):
        from PySide6.QtWidgets import QApplication

        text = f"x={x + 1:.1f} y={y + 1:.1f}"  # FITS convention, as in the status bar
        sky = self._sky(x, y)
        if sky is not None:
            text += f"  {sky.to_string('hmsdms', sep=':', precision=2)}  ({sky.ra.deg:.6f} {sky.dec.deg:+.6f})"
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(text, 8000)
        return text

    def _simbad(self, x, y):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        sky = self._sky(x, y)
        url = QUrl(
            "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord="
            f"{sky.ra.deg:.6f}%20{sky.dec.deg:+.6f}&Radius=10&Radius.unit=arcsec"
        )
        QDesktopServices.openUrl(url)
        return url

    def send_to_photometry(self, paths, ask=True):
        """Images to the Photometry window, which is then shown. Several filters: one light curve per filter, so the
        user picks the filter (the largest group first)."""
        from PySide6.QtWidgets import QInputDialog

        from .workspaces import by_filter

        paths = [str(p) for p in paths if p]
        if not paths:
            return None
        groups = by_filter(paths)
        if len(groups) > 1 and ask:
            names = sorted(groups, key=lambda k: -len(groups[k]))
            labels = [self.tr("{f} ({n} images)").format(f=k or "—", n=len(groups[k])) for k in names]
            question = self.tr("A light curve is measured in one filter. Which one?")
            label, ok = QInputDialog.getItem(self, self.tr("Filter"), question, labels, 0, False)
            if not ok:
                return None
            paths = groups[names[labels.index(label)]]
        elif len(groups) > 1:
            paths = max(groups.values(), key=len)
        self.photometry_page.set_images(paths)
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

    def save_header_changes(self, set_cards, delete, destination=None):
        """A copy of the current file with the edited header, opened when written."""
        if self.current_path is None:
            return None
        if destination is None:
            suggestion = str(self.current_path.with_name(self.current_path.stem + "_hdr.fits"))
            destination, _ = QFileDialog.getSaveFileName(self, self.tr("Save FITS as"), suggestion, FITS_FILTER)
        if not destination:
            return None
        return self.run_step(
            "fits.save_as",
            {"source": str(self.current_path), "destination": str(destination)},
            {"overwrite": True, "set_cards": set_cards, "delete": delete},
            on_done=lambda out: self.open_fits(Path(out["destination"])),
        )

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

    def _make_spectro_page(self):
        from .spectro_page import SpectroscopyPage  # imported with its page: start-up stays fast

        page = SpectroscopyPage(self, self.settings)
        rt, vt, et, tt = page.reduce_tab, page.velocity_tab, page.echelle_tab, page.telluric_tab
        rt.reduce_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.reduce",
                inputs,
                params,
                on_done=lambda out: self._spectrum_done(out["spectrum"]),
                on_fail=rt.status.setText,  # not "Working…" behind an error box
            )
        )
        et.reduce_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.echelle",
                inputs,
                params,
                on_done=lambda out: self._echelle_done(out["echelle"]),
                on_fail=et.status.setText,
            )
        )
        et.orders_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.orders",
                inputs,
                params,
                on_done=lambda out: et.show_orders(out["orders"]),
                on_fail=et.status.setText,
            )
        )
        tt.correct_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.telluric",
                inputs,
                params,
                on_done=lambda out: self._telluric_done(out["telluric"]),
                on_fail=tt.status.setText,
            )
        )
        vt.rv_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.rv",
                inputs | ({"site": self.settings.get("site")} if self.settings.get("site") else {}),
                params,
                on_done=lambda out: vt.show_rvs(out["rvs"], out.get("skipped")),
                on_fail=vt.status.setText,
            )
        )
        vt.disentangle_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.disentangle",
                inputs,
                params,
                on_done=lambda out: vt.show_components(out["components"]),
                on_fail=vt.status.setText,
            )
        )
        page.tools_tab.combine_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.combine",
                inputs,
                params,
                on_done=lambda out: page.tools_tab.show_combined(out["combined"]),
                on_fail=page.tools_tab.source.setText,
            )
        )
        page.tools_tab.atmosphere_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.atmosphere",
                inputs | {"cache": str(self.settings.path.parent / "phoenix")},
                params,
                on_done=lambda out: page.tools_tab.show_atmosphere(out["atmosphere"]),
            )
        )
        vt.classify_requested.connect(
            lambda spectrum: self.run_step_for(
                "spectroscopy",
                "spectroscopy.classify",
                {"spectrum": spectrum, "library": str(self.settings.path.parent / "templates")},
                {},
                on_done=lambda out: vt.show_classes(
                    out["classes"], out.get("mk"), out.get("mk_note"), out.get("mk_model"), out.get("classes_note")
                ),
            )
        )
        vt.orbit_requested.connect(
            lambda inputs, params: self.run_step_for(
                "spectroscopy",
                "spectroscopy.orbit",
                inputs,
                params,
                on_done=lambda out: (vt.show_orbit(out["orbit"]), self.models_page.set_orbit(out["orbit"])),
                on_fail=vt.status.setText,
            )
        )
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

    def _make_models_page(self):
        from .models_page import ModelsPage  # imported with its page: start-up stays fast

        page = ModelsPage(self)
        page.fit_requested.connect(
            lambda inputs, params: self.run_step_for(
                "orbits",
                "models.eb_fit",
                inputs,
                params,
                on_done=lambda out: page.show_fit(out["model"]),
                on_fail=page.status.setText,
            )
        )
        page.visual_tab.fit_requested.connect(
            lambda inputs, params: self.run_step_for(
                "orbits",
                "models.visual_orbit",
                inputs,
                params,
                on_done=lambda out: page.visual_tab.show_orbit(out["orbit"]),
                on_fail=page.visual_tab.status.setText,
            )
        )
        return page

    def _make_photometry_page(self):
        page = PhotometryPage(self)
        page.measure_requested.connect(self.measure_light_curve)
        page.catalog_requested.connect(
            lambda inputs, params: self.run_step(
                "photometry.catalog",
                inputs,
                params,
                on_done=lambda out: page.show_catalog(out["catalog"]),
                area="photometry",
            )
        )
        page.quality_requested.connect(
            lambda images: self.run_step(
                "photometry.quality",
                {"images": images},
                {},
                on_done=lambda out: page.show_quality(out["quality"]),
                area="photometry",
            )
        )
        page.minimum_requested.connect(self.time_minimum)
        page.next_requested.connect(self._photometry_next)
        page.apertures_requested.connect(
            lambda images, target, comps: self.run_step(
                "photometry.apertures",
                {"images": images, "target_xy": target, "comps_xy": comps},
                {},
                on_done=lambda out: page.show_apertures(out["apertures"]),
                area="photometry",
            )
        )
        page.polarimetry_requested.connect(
            lambda images, o, e, params: self.run_step(
                "photometry.polarimetry",
                {"images": images, "o_xy": o, "e_xy": e},
                params,
                on_done=lambda out: page.show_polarimetry(out["polarimetry"]),
                area="photometry",
            )
        )
        page.suggest_requested.connect(
            lambda images, target, params: self.run_step(
                "photometry.suggest_comparisons",
                # the Gaia stars of the field when it was solved on the frame the stars are marked on
                {"images": images, "target_xy": target}
                | ({"field": page.field} if page.field and page.ref == 0 else {}),
                params,
                on_done=lambda out: page.set_comparisons(out["comps_xy"], out.get("catalogue")),
                area="photometry",
            )
        )
        page.field_requested.connect(
            lambda image: self.run_step(
                "photometry.identify_field",
                {"image": image},
                on_done=lambda out: page.show_field(out["field"]),
                on_fail=page.field_failed,
                area="photometry",
            )
        )
        return page

    def _make_oc_page(self):
        """O-C in a window of its own (the owner, 2026-11-08); minima timed in Photometry and maxima from the
        frequency analysis arrive here."""
        oc = OCPage(self)
        oc.ephemeris_requested.connect(
            lambda name: self.run_step_for(
                "oc",
                "planning.ephemeris",
                {"name": name},
                {"catalogue": "vsx"},
                on_done=lambda out: oc.set_ephemeris(out["target"]),
                on_fail=lambda msg: oc.result.setText(translate(msg)),
            )
        )

        def oc_background(model, text, t0, period, steps, minima):
            from .messages import translate

            params = {"model": model, "t0": t0, "period": period, "mcmc_steps": steps}
            fail = oc.tr("Cannot fit: {error}")
            self.run_step_for(
                "oc",
                "timeseries.oc_fit",
                {"minima": text},
                params,
                on_done=lambda out: oc.show_fit(out["fit"], minima),
                on_fail=lambda msg: oc.result.setText(fail.format(error=translate(msg))),
            )

        oc.background = oc_background
        return oc

    def _make_lightcurve_page(self):
        page = LightCurvePage(self)
        page.period_page.search_requested.connect(self.search_period)
        vf = page.varfind_page
        vf.search_requested.connect(
            lambda images, params: self.run_step_for(
                "timeseries", "photometry.varfind", {"images": images}, params, on_done=vf.show_result
            )
        )
        vf.light_curve_chosen.connect(
            lambda t, f, label: (
                page.period_page.set_light_curve(t, f, label),
                page.setCurrentWidget(page.period_page),
            )
        )
        fp = page.frequency_page
        fp.analyse_requested.connect(
            lambda t, y, params: self.run_step_for(
                "timeseries", "timeseries.frequencies", {"time": t, "flux": y}, params, on_done=fp.show_result
            )
        )
        fp.to_oc.clicked.connect(  # to the O-C window, opened so the user sees them arrive
            lambda: (
                [self.oc_page.add_minimum(tm, err, "maximum") for tm, err in (fp.result or {}).get("maxima", [])],
                self.open_area("oc"),
            )
        )
        pp = page.period_page

        def fetch(target, mission):
            from ..settings import config_dir

            def done(out):
                lc = out["light_curve"]
                pp.set_light_curve(lc["time"], lc["rel_flux"], f"{target} ({lc['source']})", err=lc.get("rel_flux_err"))

            if mission in ("ZTF", "AAVSO"):
                inputs = {"target": target, "cache_file": str(config_dir() / "targets.json")}
                return self.run_step_for(
                    "timeseries",
                    "timeseries.survey_lc",
                    inputs,
                    {"source": mission},
                    on_done=done,
                    on_fail=pp.source.setText,
                )
            inputs = {"target": target, "folder": str(self.settings.path.parent / "archive")}
            return self.run_step_for(
                "timeseries",
                "timeseries.mission_lc",
                inputs,
                {"mission": mission},
                on_done=done,
                on_fail=pp.source.setText,
            )

        pp.archive_requested.connect(fetch)
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
        from .area_window import AreaWindow, _raise
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

    def _fill_image_toolbar(self):
        """The most used image commands as small icons above the image: the same actions as in the menus."""
        from PySide6.QtWidgets import QToolButton

        bar, self._glyphs = self.image_page.toolbar, []
        first = bar.actions()[0]  # the measuring tools stay at the end
        icons = (  # kinds of ui/icons.py: the same icon as in the other windows
            (self.open_action, "open"),
            (self.save_action, "save"),
            None,
            (self.previous_action, "previous"),
            (self.next_action, "next"),
            None,
            (self.fit_action, "fit"),
            (self.zoom_in_action, "zoom_in"),
            (self.zoom_out_action, "zoom_out"),
            None,
            (self.levels_action, "levels"),
            (self.blink_action, "blink"),
            (self.overlay_menu.menuAction(), "overlays"),
            None,
            (self.process_menu.menuAction(), "process"),
            (self.solve_action, "solve"),
            None,
        )
        for item in icons:
            if item is None:
                bar.insertSeparator(first)
                continue
            act, kind = item
            self._glyphs.append((act, kind))
            act.setToolTip(act.text().replace("&", ""))
            bar.insertAction(first, act)
            if act.menu():
                bar.widgetForAction(act).setPopupMode(QToolButton.InstantPopup)
        self._paint_glyphs()

    def _paint_glyphs(self):
        from .icons import icon

        for act, kind in self._glyphs:
            act.setIcon(icon(kind, self))

    def _build_menus(self):
        m = self.menuBar().addMenu(self.tr("&File"))
        self._action(m, self.tr("&New project…"), self.new_project_dialog, QKeySequence.New)
        self._action(m, self.tr("Open &project…"), self.open_project_dialog)
        m.addSeparator()
        self.open_action = self._action(m, self.tr("&Open FITS…"), self.open_fits_dialog, QKeySequence.Open)
        self.save_action = self._action(m, self.tr("&Save FITS as…"), self.save_as_dialog, QKeySequence.SaveAs)
        self.save_action.setEnabled(False)
        self.picture_action = self._action(m, self.tr("Save &picture (PNG / JPEG / TIFF)…"), self.save_picture_dialog)
        self.picture_action.setEnabled(False)
        self._action(m, self.tr("&Convert many images (PNG / JPEG / TIFF)…"), self.convert_dialog)
        m.addSeparator()
        self._action(m, self.tr("&Close image"), self.close_image, QKeySequence.Close)
        self._action(m, self.tr("Close &all images"), lambda: self.close_image(everything=True))
        m.addSeparator()
        self._action(m, self.tr("&Quit"), self.close, QKeySequence.Quit)

        e = self.menuBar().addMenu(self.tr("&Edit"))
        self.undo_group = QUndoGroup(self)
        self.undo_action = self.undo_group.createUndoAction(self, self.tr("&Undo"))
        self.undo_action.setShortcuts([QKeySequence(QKeySequence.Undo)])
        self.redo_action = self.undo_group.createRedoAction(self, self.tr("&Redo"))
        redo = [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")] + QKeySequence.keyBindings(QKeySequence.Redo)
        unique = {k.toString(): k for k in redo}  # one key twice on one action is "ambiguous": it would do nothing
        self.redo_action.setShortcuts(list(unique.values()))
        for act, tip in (
            (self.undo_action, self.tr("Take back the last change in this window (stars marked, points deleted, …)")),
            (self.redo_action, self.tr("Do again what Undo took back")),
        ):
            act.setToolTip(tip)
            e.addAction(act)

        v = self.view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.fit_action = self._action(v, self.tr("Zoom to &fit"), self.viewer.fit, "F")
        self.zoom_in_action = self._action(v, self.tr("Zoom &in"), lambda: self.viewer.zoom(1.25), QKeySequence.ZoomIn)
        zoom_out = QKeySequence.ZoomOut
        self.zoom_out_action = self._action(v, self.tr("Zoom &out"), lambda: self.viewer.zoom(0.8), zoom_out)
        names = {
            "zscale": self.tr("ZScale"),
            "minmax": self.tr("Min–max"),
            "99.5%": self.tr("99.5 %"),
            "linear": self.tr("Linear"),
            "sqrt": self.tr("Square root"),
            "log": self.tr("Logarithmic"),
            "asinh": self.tr("Asinh"),
        }
        self.previous_action = self._action(v, self.tr("&Previous image"), lambda: self.image_page.step_image(-1))
        self.next_action = self._action(v, self.tr("&Next image"), lambda: self.image_page.step_image(1))
        for act, key in ((self.previous_action, Qt.Key_PageUp), (self.next_action, Qt.Key_PageDown)):
            act.setShortcut(key)
            act.setShortcutContext(Qt.WidgetWithChildrenShortcut)  # only over the image: tables keep their keys
            self.image_page.addAction(act)
        v.addSeparator()
        self.levels_action = self._action(v, self.tr("Display &levels and colours…"), self.levels_dialog, "Ctrl+L")
        self.blink_action = self._action(v, self.tr("&Blink images…"), self.blink_dialog)
        from .overlay_actions import add_menu as add_overlay_menu

        self.overlay_menu = add_overlay_menu(self, v)
        for title, keys, kw in (
            (self.tr("Interval"), INTERVALS, "interval"),
            (self.tr("Stretch"), STRETCHES, "stretch"),
        ):
            sub, group = v.addMenu(title), QActionGroup(self)
            for key in keys:
                act = self._action(sub, names[key], lambda _=False, k=key, kw=kw: self.viewer.set_stretch(**{kw: k}))
                act.setCheckable(True)
                act.setChecked(key == getattr(self.viewer, kw))
                group.addAction(act)

        im = self.image_bar_menu = self.menuBar().addMenu(self.tr("&Image"))
        self.solve_action = self._action(im, self.tr("&Plate solve (ASTAP / astrometry.net)"), self.plate_solve)
        self.solve_action.setEnabled(False)
        self._action(im, self.tr("&Colour image from three filters…"), self.colour_dialog)
        self._action(im, self.tr("&Asteroid and comet astrometry…"), self.moving_dialog)
        self._action(im, self.tr("Photometric &coefficients (extinction, transformation)…"), self.coefficients_dialog)
        self.process_menu = im.addMenu(self.tr("P&rocess"))
        self.process_menu.setEnabled(False)
        self.apply_all_action = self.process_menu.addAction(self.tr("Apply to all open images"))
        self.apply_all_action.setCheckable(True)
        self.apply_all_action.setToolTip(
            self.tr("The next operations run on every image in the list; the processed copies take their places")
        )
        self.process_menu.setToolTipsVisible(True)
        self.process_menu.addSeparator()
        ops = (
            (self.tr("Pixel math…"), "pixel_math"),
            (self.tr("Flip left–right"), ("flip", {"axis": "x"})),
            (self.tr("Flip top–bottom"), ("flip", {"axis": "y"})),
            (self.tr("Rotate 90°"), ("rotate90", {"k": 1})),
            (self.tr("Rotate by any angle…"), "rotate"),
            (self.tr("Resample (change the pixel size)…"), "resample"),
            (self.tr("Bin 2×2"), ("bin", {"factor": 2})),
            (self.tr("Crop…"), "crop"),
            (self.tr("Gaussian smoothing…"), "gaussian"),
            (self.tr("Median filter…"), "median"),
            (self.tr("Unsharp mask…"), "unsharp"),
            (self.tr("Remove background gradient…"), "background"),
            (self.tr("Kernel filter…"), "kernel"),
            (self.tr("Deconvolution (Richardson–Lucy)…"), "deconvolve"),
            (self.tr("Digital development (DDP)"), ("ddp", {})),
            (self.tr("Match the histogram of another image…"), "histogram_match"),
        )
        for text, op in ops:
            self._action(self.process_menu, text, lambda _=False, o=op: self.process_dialog(o))

        self.plugins_menu = self.menuBar().addMenu(self.tr("&Plugins"))
        self.plugins_menu.aboutToShow.connect(self._fill_plugins_menu)

        s = self.settings_menu = self.menuBar().addMenu(self.tr("&Settings"))
        self.expert_action = QAction(self.tr("&Expert mode (every option open)"), self)
        self.expert_action.setCheckable(True)
        self.expert_action.setChecked(self.ui_mode() == "expert")
        self.expert_action.toggled.connect(lambda on: self.set_ui_mode("expert" if on else "basic"))
        s.addAction(self.expert_action)
        s.addSeparator()
        lang_menu, group = s.addMenu(self.tr("&Language")), QActionGroup(self)
        current = self.settings.get("ui.language")
        for code, native in LANGUAGES.items():
            act = self._action(lang_menu, native, lambda _=False, c=code: self.set_language(c))
            act.setCheckable(True)
            act.setChecked(code == current)
            group.addAction(act)

        theme_menu, group = s.addMenu(self.tr("&Look")), QActionGroup(self)
        looks = {"dark": self.tr("Dark"), "light": self.tr("Light")}
        for code, label in looks.items():
            act = self._action(theme_menu, label, lambda _=False, c=code: self.set_theme(c))
            act.setCheckable(True)
            act.setChecked(code == self.settings.get("ui.theme", "dark"))
            group.addAction(act)

        dev_menu, group = s.addMenu(self.tr("&Processing device")), QActionGroup(self)
        names = {"auto": self.tr("Automatic (GPU when useful)"), "cpu": self.tr("CPU only"), "gpu": self.tr("GPU")}
        for code, label in names.items():
            act = self._action(dev_menu, label, lambda _=False, c=code: self.set_compute(c))
            act.setCheckable(True)
            act.setChecked(code == compute.mode())
            group.addAction(act)

        text_menu = s.addMenu(self.tr("Text size"))  # View → Text size in the area windows
        sizes = (
            (self.tr("&Larger text"), 1, "Ctrl+Shift++"),
            (self.tr("&Smaller text"), -1, "Ctrl+Shift+-"),
            (self.tr("&Normal text size"), 0, "Ctrl+Shift+0"),
        )
        for text, step, key in sizes:
            self._action(text_menu, text, lambda s=step: self._change_font(s), key)
        self.window_menu = self.menuBar().addMenu(self.tr("&Window"))
        self.window_menu.aboutToShow.connect(self._fill_window_menu)
        h = self.menuBar().addMenu(self.tr("&Help"))
        self._action(h, self.tr("Report a problem…"), self.report_problem)
        self._action(h, self.tr("Training &guide"), lambda: self.show_workspace("guide"), QKeySequence.HelpContents)
        self.tour_action = self._action(h, self.tr("Quick &tour"), self.start_tour)
        self._action(h, self.tr("&Practice data for a first night…"), self.practice_data)
        self._action(h, self.tr("Check the &installation and internet services"), self.check_installation)
        self.update_action = self._action(h, self.tr("Check for &updates…"), self.check_updates)
        self.about_action = self._action(h, self.tr("&About {app}").format(app=BRAND.display_name), self.about)

    # --- image processing ---------------------------------------------------
    def process_dialog(self, op):
        """Ask for the operation's settings (if any) and run it on the current image."""
        from PySide6.QtWidgets import QInputDialog

        if isinstance(op, tuple):
            return self.process_image(*op)
        if op == "pixel_math":
            others, _ = QFileDialog.getOpenFileNames(
                self, self.tr("Other images, named B, C, … (optional)"), "", images_filter()
            )
            expr, ok = QInputDialog.getText(
                self, self.tr("Pixel math"), self.tr("Expression (A is this image), e.g. A - 0.95 * B:")
            )
            from ..io.bayer import fits_paths

            return self.process_image("pixel_math", {"expression": expr}, fits_paths(others)) if ok and expr else None
        if op == "crop":
            text, ok = QInputDialog.getText(
                self, self.tr("Crop"), self.tr("x0 x1 y0 y1 (pixels, 0-based, end excluded):")
            )
            try:
                x0, x1, y0, y1 = (int(v) for v in text.replace(",", " ").split())
            except ValueError:
                return None
            return self.process_image("crop", {"x0": x0, "x1": x1, "y0": y0, "y1": y1}) if ok else None
        if op == "rotate":
            angle, ok = QInputDialog.getDouble(
                self, self.tr("Rotate"), self.tr("Angle (degrees, counter-clockwise):"), 0.0, -360.0, 360.0, 3
            )
            return self.process_image("rotate", {"angle": angle}) if ok else None
        if op == "histogram_match":
            ref, _ = QFileDialog.getOpenFileName(self, self.tr("Reference image"), "", images_filter())
            from ..io.bayer import fits_copy

            return self.process_image("histogram_match", {"reference": str(fits_copy(ref))}) if ref else None
        if op == "kernel":
            kinds = {
                self.tr("Low pass (smooth)"): "lowpass",
                self.tr("High pass (sharpen)"): "highpass",
                self.tr("Laplacian"): "laplacian",
                self.tr("Edges (Sobel)"): "sobel",
                self.tr("Vertical edges"): "edge_x",
                self.tr("Horizontal edges"): "edge_y",
            }
            name, ok = QInputDialog.getItem(self, self.tr("Kernel filter"), self.tr("Filter:"), list(kinds), 0, False)
            return self.process_image("kernel", {"kind": kinds[name]}) if ok else None
        if op == "deconvolve":
            fwhm, ok = QInputDialog.getDouble(
                self,
                self.tr("Deconvolution"),
                self.tr("Star FWHM (pixels; measure it with the Star tool):"),
                3.0,
                0.5,
                50,
                2,
            )
            if not ok:
                return None
            n, ok = QInputDialog.getInt(self, self.tr("Deconvolution"), self.tr("Iterations:"), 20, 1, 500)
            return self.process_image("deconvolve", {"fwhm": fwhm, "iterations": n}) if ok else None
        prompts = {
            "resample": (self.tr("Factor (2: twice as many pixels across, 0.5: half):"), "factor", 2.0),
            "gaussian": (self.tr("Sigma (pixels):"), "sigma", 1.5),
            "median": (self.tr("Box size (pixels, odd):"), "size", 3),
            "unsharp": (self.tr("Sigma (pixels):"), "sigma", 2.0),
            "background": (self.tr("Box size (pixels):"), "box", 64),
        }
        label, key, default = prompts[op]
        value, ok = QInputDialog.getDouble(self, self.tr("Process"), label, default, 0.01, 10000, 2)
        if not ok:
            return None
        return self.process_image(op, {key: int(value) if key in ("size", "box") else value})

    def process_image(self, op, args=None, others=None):
        """Run an image operation on the current file, or on every open image (Process -> Apply to all open
        images: each processed copy takes the place of its original in the list); the result opens when written."""
        if getattr(self, "current_path", None) is None:
            return None
        every = self.apply_all_action.isChecked()
        tasks = []
        for path in self.image_page.open_paths() if every else [str(self.current_path)]:
            inputs = {"image": path, "operation": op}
            if others:
                inputs["others"] = list(others)
            tasks.append(
                self.run_step(
                    "image.process", inputs, {"args": args or {}}, on_done=lambda out, p=path: self._processed(p, out)
                )
            )
        return tasks if every else tasks[0]

    def _processed(self, source, out):
        if self.apply_all_action.isChecked():
            self.image_page.replace_open(source, out["image"])
        if source == str(self.current_path) or not self.apply_all_action.isChecked():
            # Ctrl+Z shows the image before the operation again (the processed copy stays on disk)
            self.image_page.edit(self.tr("image operation"), self.open_fits, Path(out["image"]))

    def colour_dialog(self, paths=None, output=None):
        """Red, green and blue frames -> a colour PNG (aligned, Lupton asinh stretch), shown when ready."""
        if paths is None:
            paths = []
            for label in (self.tr("Red frame"), self.tr("Green frame"), self.tr("Blue frame")):
                path, _ = QFileDialog.getOpenFileName(self, label, "", images_filter())
                if not path:
                    return None
                paths.append(path)
            output, _ = QFileDialog.getSaveFileName(self, self.tr("Colour image"), "colour.png", "PNG (*.png)")
            if not output:
                return None
        from ..io.bayer import fits_paths

        inputs = dict(zip(("red", "green", "blue"), fits_paths(paths), strict=True)) | {"output": output}
        return self.run_step("image.rgb", inputs, {}, on_done=lambda out: self.show_picture(out["rgb"]))

    def coefficients_dialog(self):
        from .coefficients_dialog import CoefficientsDialog

        lc = getattr(self.photometry_page, "lc_raw", None) if "photometry_page" in self.__dict__ else None
        dlg = CoefficientsDialog(lc, self)
        dlg.transform_requested.connect(
            lambda a, b, params: self.run_step(
                "photometry.transformation", {"image_a": a, "image_b": b}, params, on_done=dlg.show_transformation
            )
        )
        dlg.open()
        self.coefficients = dlg
        return dlg

    def moving_dialog(self):
        from .moving_dialog import MovingObjectDialog

        dlg = MovingObjectDialog(self.settings, self)
        dlg.measure_requested.connect(
            lambda images, first, last: self.run_step(
                "astrometry.moving",
                {"images": images, "first_xy": first, "last_xy": last},
                {},
                on_done=lambda out: dlg.show_positions(out["positions"], out.get("unsolved", ())),
            )
        )
        dlg.open()
        self.astrometry_dialog = dlg
        return dlg

    def show_picture(self, path):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QScrollArea, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle(Path(path).name)
        label = QLabel(dlg)
        label.setPixmap(QPixmap(str(path)))
        area = QScrollArea(dlg)
        area.setWidget(label)
        QVBoxLayout(dlg).addWidget(area)
        dlg.resize(900, 700)
        dlg.open()
        self.picture_dialog = dlg
        return dlg

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
        self.viewer.set_image(data)
        self.image_page.set_header(header, self.wcs)
        self._show_header(header)
        self.save_action.setEnabled(True)
        self.picture_action.setEnabled(True)
        if getattr(self, "_levels", None) is not None and self._levels.isVisible():
            self._levels.refresh()
        self.solve_action.setEnabled(True)
        self.process_menu.setEnabled(True)
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

    def levels_dialog(self):
        from .levels_dialog import LevelsDialog

        if getattr(self, "_levels", None) is None:
            self._levels = LevelsDialog(self.viewer, self)
        self._levels.refresh()
        self._levels.show()
        self._levels.raise_()
        return self._levels

    def blink_dialog(self):
        from .blink_dialog import BlinkDialog

        dlg = BlinkDialog(self)
        dlg.show()
        return dlg

    def save_picture_dialog(self, path=None):
        """The image as shown on screen (PNG / JPEG), or its data as a 32-bit TIFF."""
        from ..display import save_picture

        if self.viewer.data is None:
            return None
        if path is None:
            stem = self.current_path.stem if self.current_path else "image"
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save picture"), f"{stem}.png", "PNG (*.png);;JPEG (*.jpg);;TIFF, 32-bit data (*.tif)"
            )
        if not path:
            return None
        v = self.viewer
        return save_picture(path, v.data, v.interval, v.stretch, v.limits, v.cmap, v.invert)

    def convert_dialog(self, paths=None, folder=None, fmt=None):
        """Batch conversion: FITS files to pictures with the current display interval and stretch."""
        from PySide6.QtWidgets import QInputDialog

        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Images to convert"), "", images_filter())
            if not paths:
                return None
        from ..io.bayer import fits_paths

        paths = fits_paths(paths)
        if fmt is None:
            choices = {"PNG": "png", "JPEG": "jpg", self.tr("TIFF, 32-bit data"): "tif"}
            name, ok = QInputDialog.getItem(
                self, self.tr("Convert images"), self.tr("Format:"), list(choices), 0, False
            )
            if not ok:
                return None
            fmt = choices[name]
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, self.tr("Folder for the pictures"))
            if not folder:
                return None
        params = {"fmt": fmt, "interval": self.viewer.interval, "stretch": self.viewer.stretch}
        return self.run_step(
            "image.convert",
            {"images": list(paths), "output_dir": folder},
            params,
            on_done=lambda out: self.statusBar().showMessage(
                self.tr("{n} pictures written to {folder}.").format(n=len(out["written"]), folder=folder), 10000
            ),
        )

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
        from .area_window import AreaWindow

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
                f"{step_name(task.name)}\n\n{task_error(task.error)}",
                parent=self,
            )
            box.setDetailedText(str(task.error))  # the full traceback, for reports
            box.open()

    def plate_solve(self):
        from .. import astrometry

        if astrometry.find_solver() is None:
            QMessageBox.information(
                self,
                self.tr("No plate solver"),
                self.tr(
                    "Install ASTAP and one of its star databases (hnsky.org/astap.htm), or astrometry.net, "
                    "then try again. Nothing is sent over the internet."
                ),
            )
            return None
        return self.run_step(
            "astrometry.solve",
            {"image": str(self.current_path)},
            on_done=lambda out: self.open_fits(Path(out["solved"])),
        )

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

    def stack_images(self, images, output, params):
        def done(out):
            if self.engine.project:
                self.engine.project.add_file(Path(out["stack"]), "stack")
            self.calibrate_page.result.setText(self.tr("Stack written: {path}").format(path=out["stack"]))
            self.open_fits(Path(out["stack"]))

        step_id = "stacking.drizzle" if params.pop("drizzle", False) else "stacking.stack"
        return self.run_step(step_id, {"images": images, "output": output}, params, on_done=done, area="calibrate")

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
    def _show_pixel(self, x, y, value):
        label = self.tr("value")
        text = f"x={x:.0f}  y={y:.0f}  {label}={value:.6g}"
        if self.wcs is not None:
            sky = self.wcs.pixel_to_world(x - 1, y - 1)
            text += "  " + sky.to_string("hmsdms", precision=1)
        self.pixel_label.setText(text)
        if getattr(self, "image_pixel_label", None) is not None:  # the cursor read-out of the Images window
            self.image_pixel_label.setText(text)

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
        """Short guided tour of the pages and the main controls."""
        from PySide6.QtWidgets import QToolButton

        from .tour import TourOverlay, rect_of

        def item(key):  # the area's block on the start page
            return lambda: rect_of(self.start_page.findChild(QToolButton, f"start_{key}"), self)

        def blocks():
            shown = [rect_of(b, self) for b in self.start_page.blocks]
            shown = [r for r in shown if r is not None]
            return shown[0].united(shown[-1]) if shown else None

        self.show_workspace("start")
        dock = self.findChild(QDockWidget, "tasks")
        steps = [
            (None, self.tr("Welcome! This one-minute tour shows where things are. Press Next, or Skip at any time.")),
            (blocks, self.tr("The areas, in the order of an observing night. Click one to open it in its window.")),
            (
                lambda: rect_of(self.start_page, self),
                self.tr(
                    "Start here: pick what you have — raw frames, images, spectra, a list of minima — and you are taken to the right page."  # noqa: E501
                ),
            ),
            (
                item("plan"),
                self.tr("Plan: when your targets are visible, airmass, the Moon, predicted eclipses and transits."),
            ),
            (
                item("observe"),
                self.tr(
                    "Observe: connect the telescope and camera, run sequences and whole nights. The safety supervisor parks the telescope when something is wrong."  # noqa: E501
                ),
            ),
            (
                item("calibrate"),
                self.tr(
                    "Calibrate: bias, dark and flat frames are matched and applied automatically; frames can be aligned and stacked."  # noqa: E501
                ),
            ),
            (
                item("photometry"),
                self.tr(
                    "Photometry and Light curves & O-C: measure stars, get light curves, minima, O-C diagrams and periods."  # noqa: E501
                ),
            ),
            (
                item("spectroscopy"),
                self.tr(
                    "Spectroscopy: long-slit and echelle reduction, telluric correction, radial velocities, IFU cubes."
                ),
            ),
            (
                item("orbits"),
                self.tr("Orbits & models: radial-velocity orbits and eclipsing-binary or transit models."),
            ),
            (
                item("remotesensing"),
                self.tr(
                    "Remote sensing: satellite and aerial images — band math, vegetation and water indices, classes."
                ),
            ),
            (
                item("automation"),
                self.tr(
                    "Automation: chain steps into your own pipeline or start from a ready template (eclipsing binary night, transit, calibration, spectra to RV) and run it in one go."  # noqa: E501
                ),
            ),
            (
                lambda: rect_of(self.menuBar(), self),  # the guide has no block: Help → Training guide opens it
                self.tr(
                    "Guide: every page explained step by step, by category, with search. Help → Training guide opens it too."  # noqa: E501
                ),
            ),
            (
                lambda: rect_of(dock, self),
                self.tr("Tasks: long jobs run here in the background with their progress; you can keep working."),
            ),
            (
                lambda: rect_of(self.menuBar(), self),
                self.tr(
                    "Menus: Image → Process for image operations, Plugins for your own tools, Settings for language, look and CPU/GPU, Help for this tour and the training pages."  # noqa: E501
                ),
            ),
        ]
        self.tour = TourOverlay(self, steps)
        self.tour.start()
        self.settings.set("ui.tour_done", True)
        return self.tour

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

    def check_installation(self):
        """Every part of the installation and every web service (SIMBAD, VizieR, MAST, ...) in one report: what to
        send when something does not work."""

        def done(out):
            box = QMessageBox(QMessageBox.Information, self.tr("Installation and internet services"), "", parent=self)
            box.setText(
                self.tr("Everything works.")
                if out["ok"]
                else self.tr(
                    "Some checks failed (see below). A failing web service is often the network or the service."
                )
            )
            box.setDetailedText(out["report"])
            box.exec()

        self.statusBar().showMessage(self.tr("Checking the installation and the internet services…"), 60000)
        return self.run_step("app.check", {}, {}, on_done=done)

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


def _mirror(widget, parent=None, short=None):
    """A menu / toolbar action that does what a page's button or check box does (interface I6c): the button's text
    in the menus, the short name on the toolbar (its icon text), enabled and checked as the widget is; the button
    stays the one place where the page decides."""
    act = QAction(widget.text() or short, parent or widget)
    if short:
        act.setIconText(short)
    act.setToolTip(widget.toolTip() or widget.text())
    act.setStatusTip(act.toolTip())
    if widget.isCheckable():
        act.setCheckable(True)
        act.setChecked(widget.isChecked())
        act.toggled.connect(widget.setChecked)
        widget.toggled.connect(act.setChecked)
    else:
        act.triggered.connect(lambda _=False, b=widget: b.click())
    _follow_enabled(widget, act)
    return act


def _follow_enabled(button, action):
    """A toolbar or menu action that is enabled exactly when the page's button is, and not while the page has hidden
    the button (Posterior… before an MCMC run); the button stays the one place where the page decides. A button in
    a tab that is not shown is not hidden: its action stays usable."""
    from PySide6.QtCore import QEvent

    def follow():
        action.setEnabled(button.isEnabled() and not button.isHidden())

    class _Watch(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.EnabledChange, QEvent.ShowToParent, QEvent.HideToParent):
                follow()
            return False

    watch = _Watch(button)
    button.installEventFilter(watch)
    follow()
    action._watch = watch


def _undo_source(page):
    """What an area window's Undo / Redo act on: the page's undo stack, or for a page of tabs (Light curves: period,
    frequency, variables, O−C) a group that follows the tab shown."""
    tabs = page if hasattr(page, "currentWidget") else getattr(page, "tabs", None)
    if tabs is None or getattr(page, "undo_stack", None) is not None:  # a page with one stack of its own (Models)
        return getattr(page, "undo_stack", None)
    group = QUndoGroup(page)
    stacks = {}
    for i in range(tabs.count()):
        stack = getattr(tabs.widget(i), "undo_stack", None)
        if stack is not None:
            group.addStack(stack)
            stacks[i] = stack

    def follow(i):
        group.setActiveStack(stacks.get(i))

    tabs.currentChanged.connect(follow)
    follow(tabs.currentIndex())
    return group


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
