"""Main window: workspace sidebar, the pages behind it, and running tasks."""

import json
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
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
from .files import images_filter
from .i18n import LANGUAGES
from .messages import task_error, translate
from .workspaces import (
    CalibratePage,
    ImagePage,
    LightCurvePage,
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


def _glyph(text, color, size=40):
    """A toolbar icon drawn from a symbol of the user interface font, in the text colour of the theme."""
    from PySide6.QtGui import QPainter, QPixmap

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    font = p.font()
    font.setPixelSize(int(size * 0.8))
    p.setFont(font)
    p.setPen(color)
    p.drawText(pix.rect(), Qt.AlignCenter, text)
    p.end()
    return QIcon(pix)


class _Panel(QDockWidget):
    """A page shown beside the image; closing it puts the page back in the sidebar's list."""

    closed = Signal()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()


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
    spectro_page = _Lazy()
    models_page = _Lazy()
    rs_page = _Lazy()
    automation_page = _Lazy()
    project_page = _Lazy()
    guide_page = _Lazy()

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings()
        self.engine = Engine()
        self.current_path: Path | None = None
        self.wcs = None
        self.setWindowIcon(QIcon(str(BRAND.icon_path)))
        self.resize(1200, 800)
        self._panels, self._key = {}, "start"  # pages shown as panels beside the image; the page in the stack

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
        self.setAcceptDrops(True)  # files dropped on the window open (images, a project)
        self._fill_image_toolbar()
        self._update_title()
        for key in self.settings.get("ui.panels", []):  # the panels of the last session
            if key in self.PAGES:
                self.dock_page(key)

    # --- construction -------------------------------------------------------
    PAGES = {  # key (stable, never translated) -> attribute of the page
        "start": "start_page",
        "plan": "plan_page",
        "observe": "observe_page",
        "calibrate": "calibrate_page",
        "image": "image_page",
        "photometry": "photometry_page",
        "timeseries": "lightcurve_page",
        "spectroscopy": "spectro_page",
        "orbits": "models_page",
        "remotesensing": "rs_page",
        "automation": "automation_page",
        "project": "project_page",
        "guide": "guide_page",
    }

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
            "spectroscopy": self.tr("Spectroscopy"),
            "orbits": self.tr("Orbits & models"),
            "remotesensing": self.tr("Remote sensing"),
            "automation": self.tr("Automation"),
            "project": self.tr("Project"),
            "guide": self.tr("Guide"),
        }
        groups = {  # a heading before the first page of each group; the order of the work through a night
            "plan": self.tr("Observation"),
            "calibrate": self.tr("Reduction"),
            "photometry": self.tr("Analysis"),
            "automation": self.tr("Tools"),
        }
        self.nav = QListWidget(self)
        self.nav.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav.customContextMenuRequested.connect(self._nav_menu)
        self.nav.setObjectName("sidebar")
        self.pages = QStackedWidget(self)
        self._placeholders = {}
        for key, attr in self.PAGES.items():
            if key in groups:  # a heading: not selectable, carries no page
                self.nav.addItem(groups[key].upper())
                heading = self.nav.item(self.nav.count() - 1)
                heading.setFlags(Qt.NoItemFlags)
                font = heading.font()
                font.setPointSizeF(font.pointSizeF() * 0.8)
                font.setBold(True)
                heading.setFont(font)
            self.nav.addItem(titles[key])
            self.nav.item(self.nav.count() - 1).setData(Qt.UserRole, key)
            self._placeholders[attr] = QWidget(self.pages)
            self.pages.addWidget(self._placeholders[attr])
        # at least as wide as the longest title in the chosen language; wider or folded away by dragging its edge
        nav_width = self.nav.sizeHintForColumn(0) + 2 * self.nav.frameWidth() + 28
        self.nav.setMinimumWidth(nav_width)
        for attr in ("start_page", "image_page", "project_page", "calibrate_page"):  # cheap and needed at once
            getattr(self, attr)
        self.viewer, self.header_table = self.image_page.viewer, self.image_page.header_table
        self.files_list = self.project_page.files_list
        self.viewer.hovered.connect(self._show_pixel)
        self.files_list.itemActivated.connect(lambda item: self.open_fits(Path(item.data(Qt.UserRole)), ask=True))
        self.nav.currentItemChanged.connect(lambda item, _: item and self._show_key(item.data(Qt.UserRole)))
        from PySide6.QtWidgets import QSplitter

        self.central_split = central = QSplitter(Qt.Horizontal, self)  # every border can be dragged
        central.addWidget(self.nav)
        central.addWidget(self.pages)
        central.setStretchFactor(1, 1)
        central.setSizes([nav_width, 10000])
        self.setCentralWidget(central)
        self.show_workspace("start")

    def _place(self, attr, page):
        """Put a freshly built page where its placeholder was in the stack; its tables get an export menu."""
        from PySide6.QtWidgets import QTableWidget

        for table in page.findChildren(QTableWidget):
            table.setContextMenuPolicy(Qt.CustomContextMenu)
            table.customContextMenuRequested.connect(lambda pos, t=table: self._table_menu(t, pos))
        from PySide6.QtWidgets import QFrame, QScrollArea

        holder = self._placeholders.pop(attr)
        i = self.pages.indexOf(holder)
        current = self.pages.currentIndex() == i
        frame = QScrollArea(self.pages)  # a window smaller than the page scrolls instead of overflowing the screen
        frame.setWidget(page)
        frame.setWidgetResizable(True)
        frame.setFrameShape(QFrame.NoFrame)
        self._frames[page] = frame
        self.pages.insertWidget(i, frame)
        self.pages.removeWidget(holder)
        holder.deleteLater()
        if current:
            self.pages.setCurrentIndex(i)

    def _table_menu(self, table, pos):
        from PySide6.QtWidgets import QApplication, QMenu

        from .export import export_table, table_rows

        menu = QMenu(table)
        export = menu.addAction(self.tr("Export table (CSV or LaTeX)…"))
        copy = menu.addAction(self.tr("Copy table"))
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen is export:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Export table"), "table.csv", "CSV (*.csv);;LaTeX (*.tex)"
            )
            if path:
                export_table(table, path)
        elif chosen is copy:
            header, rows = table_rows(table)
            QApplication.clipboard().setText("\n".join("\t".join(r) for r in [header, *rows]))

    def _show_key(self, key):
        if key in self._panels:  # a panel: bring it forward and keep the page that is shown
            self._panels[key].show()
            self._panels[key].raise_()
            self.nav.blockSignals(True)
            self.nav.setCurrentItem(self._nav_items()[self._key])
            self.nav.blockSignals(False)
        elif key:
            page = getattr(self, self.PAGES[key])
            self.pages.setCurrentWidget(self._frames.get(page, page))
            self._key = key

    def dock_page(self, key, on=True):
        """Show a page as a panel beside the image, as MaxIm DL's tool windows (it can be dragged out as a window
        of its own or tabbed with other panels), or put it back in the sidebar's list. Remembered for next time."""
        if key in ("start", "image") or on == (key in self._panels):
            return None
        page = getattr(self, self.PAGES[key])
        frame = self._frames.get(page, page)
        if on:
            self.pages.removeWidget(frame)
            dock = _Panel(self._nav_items()[key].text(), self)
            dock.setObjectName(f"panel_{key}")  # stable id; never translated
            dock.setWidget(frame)
            others = list(self._panels.values())
            self.addDockWidget(Qt.RightDockWidgetArea, dock)
            if others:
                self.tabifyDockWidget(others[-1], dock)
            self.resizeDocks([dock], [page.minimumSizeHint().width() + 24], Qt.Horizontal)  # whole page
            self.image_page.split.setSizes([1, 0])  # the image keeps the room; the header tabs fold (drag back)
            dock.closed.connect(lambda k=key: self.dock_page(k, False))
            self._panels[key] = dock
            dock.show()
            dock.raise_()
            if self._key == key:
                self.show_workspace("image")
        else:
            dock = self._panels.pop(key)
            self.pages.addWidget(frame)  # takes the page out of the panel
            self.removeDockWidget(dock)
            dock.deleteLater()
        self.settings.set("ui.panels", list(self._panels))
        return self._panels.get(key)

    def _fill_panels_menu(self):
        self.panels_menu.clear()
        for key, item in self._nav_items().items():
            if key not in ("start", "image"):
                act = self._action(
                    self.panels_menu, item.text(), lambda _=False, k=key: self.dock_page(k, k not in self._panels)
                )  # toggles
                act.setCheckable(True)
                act.setChecked(key in self._panels)

    def _nav_menu(self, pos):
        """Right click in the sidebar: show the page beside the image, or put it back."""
        from PySide6.QtWidgets import QMenu

        item = self.nav.itemAt(pos)
        key = item.data(Qt.UserRole) if item else None
        if key in (None, "start", "image"):
            return None
        menu = QMenu(self)
        on = key not in self._panels
        text = self.tr("Show beside the image") if on else self.tr("Put back in the list")
        self._action(menu, text, lambda: self.dock_page(key, on))
        menu.exec(self.nav.viewport().mapToGlobal(pos))
        return menu

    def _nav_items(self):
        """key -> sidebar item (group headings excluded)."""
        items = (self.nav.item(i) for i in range(self.nav.count()))
        return {it.data(Qt.UserRole): it for it in items if it.data(Qt.UserRole)}

    @property
    def workspaces(self):
        """key -> (sidebar title, page); building every page (tests and tools, not start-up)."""
        return {key: (it.text(), getattr(self, self.PAGES[key])) for key, it in self._nav_items().items()}

    oc_page = property(lambda self: self.lightcurve_page.oc_page)
    period_page = property(lambda self: self.lightcurve_page.period_page)

    # --- pages, built on first use -------------------------------------------
    def _make_start_page(self):
        page = StartPage(self)
        page.action.connect(self._start_action)
        return page

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

    def photometry_from_image(self, x, y, comparison=False):
        """Start photometry from the Images page: the open images (or the shown one) go to the Photometry page with
        this star as the target, or add it as a comparison star."""
        phot = self.photometry_page
        if not comparison:
            paths = self.image_page.open_paths() or [str(self.current_path)]
            phot.set_images(paths if str(self.current_path) in paths else [str(self.current_path)])
            if str(phot.images[0]) != str(self.current_path):  # stars are marked on the first frame in time
                self.statusBar().showMessage(
                    self.tr("Click the target on the first image in time, shown on the Photometry page."), 10000
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
            lambda site, date, targets, params: self.run_step(
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
            lambda inputs, params: self.run_step(
                "spectroscopy.reduce", inputs, params, on_done=lambda out: self._spectrum_done(out["spectrum"])
            )
        )
        et.reduce_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.echelle", inputs, params, on_done=lambda out: self._echelle_done(out["echelle"])
            )
        )
        et.orders_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.orders", inputs, params, on_done=lambda out: et.show_orders(out["orders"])
            )
        )
        tt.correct_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.telluric", inputs, params, on_done=lambda out: self._telluric_done(out["telluric"])
            )
        )
        vt.rv_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.rv",
                inputs | ({"site": self.settings.get("site")} if self.settings.get("site") else {}),
                params,
                on_done=lambda out: vt.show_rvs(out["rvs"]),
            )
        )
        vt.disentangle_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.disentangle", inputs, params, on_done=lambda out: vt.show_components(out["components"])
            )
        )
        page.tools_tab.atmosphere_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.atmosphere",
                inputs | {"cache": str(self.settings.path.parent / "phoenix")},
                params,
                on_done=lambda out: page.tools_tab.show_atmosphere(out["atmosphere"]),
            )
        )
        vt.classify_requested.connect(
            lambda spectrum: self.run_step(
                "spectroscopy.classify",
                {"spectrum": spectrum, "library": str(self.settings.path.parent / "templates")},
                {},
                on_done=lambda out: vt.show_classes(out["classes"]),
            )
        )
        vt.orbit_requested.connect(
            lambda inputs, params: self.run_step(
                "spectroscopy.orbit",
                inputs,
                params,
                on_done=lambda out: (vt.show_orbit(out["orbit"]), self.models_page.set_orbit(out["orbit"])),
            )
        )
        return page

    def _make_rs_page(self):
        from .rs_page import RemoteSensingPage  # imported with its page: start-up stays fast

        page = RemoteSensingPage(self)
        page.step_requested.connect(
            lambda sid, inputs, params: self.run_step(
                sid, inputs, params, on_done=lambda out: page.show_product(out["product"])
            )
        )
        return page

    def _make_models_page(self):
        from .models_page import ModelsPage  # imported with its page: start-up stays fast

        page = ModelsPage(self)
        page.fit_requested.connect(
            lambda inputs, params: self.run_step(
                "models.eb_fit", inputs, params, on_done=lambda out: page.show_fit(out["model"])
            )
        )
        page.visual_tab.fit_requested.connect(
            lambda inputs, params: self.run_step(
                "models.visual_orbit", inputs, params, on_done=lambda out: page.visual_tab.show_orbit(out["orbit"])
            )
        )
        return page

    def _make_photometry_page(self):
        page = PhotometryPage(self)
        page.measure_requested.connect(self.measure_light_curve)
        page.catalog_requested.connect(
            lambda inputs, params: self.run_step(
                "photometry.catalog", inputs, params, on_done=lambda out: page.show_catalog(out["catalog"])
            )
        )
        page.quality_requested.connect(
            lambda images: self.run_step(
                "photometry.quality", {"images": images}, {}, on_done=lambda out: page.show_quality(out["quality"])
            )
        )
        page.minimum_requested.connect(self.time_minimum)
        page.apertures_requested.connect(
            lambda images, target, comps: self.run_step(
                "photometry.apertures",
                {"images": images, "target_xy": target, "comps_xy": comps},
                {},
                on_done=lambda out: page.show_apertures(out["apertures"]),
            )
        )
        page.polarimetry_requested.connect(
            lambda images, o, e, params: self.run_step(
                "photometry.polarimetry",
                {"images": images, "o_xy": o, "e_xy": e},
                params,
                on_done=lambda out: page.show_polarimetry(out["polarimetry"]),
            )
        )
        page.suggest_requested.connect(
            lambda images, target, params: self.run_step(
                "photometry.suggest_comparisons",
                {"images": images, "target_xy": target},
                params,
                on_done=lambda out: page.set_comparisons(out["comps_xy"]),
            )
        )
        return page

    def _make_lightcurve_page(self):
        page = LightCurvePage(self)
        page.period_page.search_requested.connect(self.search_period)
        vf = page.varfind_page
        vf.search_requested.connect(
            lambda images, params: self.run_step(
                "photometry.varfind", {"images": images}, params, on_done=vf.show_result
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
            lambda t, y, params: self.run_step(
                "timeseries.frequencies", {"time": t, "flux": y}, params, on_done=fp.show_result
            )
        )
        fp.to_oc.clicked.connect(
            lambda: [page.oc_page.add_minimum(tm, err, "maximum") for tm, err in (fp.result or {}).get("maxima", [])]
        )
        pp = page.period_page

        def fetch(target, mission):
            from ..settings import config_dir

            def done(out):
                lc = out["light_curve"]
                pp.set_light_curve(lc["time"], lc["rel_flux"], f"{target} ({lc['source']})")

            if mission in ("ZTF", "AAVSO"):
                inputs = {"target": target, "cache_file": str(config_dir() / "targets.json")}
                return self.run_step("timeseries.survey_lc", inputs, {"source": mission}, on_done=done)
            inputs = {"target": target, "folder": str(self.settings.path.parent / "archive")}
            return self.run_step("timeseries.mission_lc", inputs, {"mission": mission}, on_done=done)

        pp.archive_requested.connect(fetch)
        return page

    def _make_calibrate_page(self):
        page = CalibratePage(self)
        page.scan_requested.connect(self.scan_raw)
        page.run_requested.connect(self.calibrate)
        page.stack_requested.connect(self.stack_images)
        return page

    def show_workspace(self, key):
        self.nav.setCurrentItem(self._nav_items()[key])

    def current_workspace(self) -> str:
        return self.nav.currentItem().data(Qt.UserRole)

    def _start_action(self, key):
        actions = {
            "new_project": self.new_project_dialog,
            "open_project": self.open_project_dialog,
            "open_fits": self.open_fits_dialog,
        }
        actions[key]() if key in actions else self.show_workspace(key)

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
        from PySide6.QtWidgets import QStyle, QToolButton

        bar, style, self._glyphs = self.image_page.toolbar, self.style(), []
        first = bar.actions()[0]  # the measuring tools stay at the end
        icons = (
            (self.open_action, style.standardIcon(QStyle.SP_DialogOpenButton)),
            (self.save_action, style.standardIcon(QStyle.SP_DialogSaveButton)),
            None,
            (self.previous_action, "◀"),
            (self.next_action, "▶"),
            None,
            (self.fit_action, "⤢"),
            (self.zoom_in_action, "+"),
            (self.zoom_out_action, "−"),
            None,
            (self.levels_action, "◐"),
            (self.blink_action, "⇆"),
            (self.overlay_menu.menuAction(), "▦"),
            None,
            (self.process_menu.menuAction(), "ƒ"),
            (self.solve_action, "⊕"),
            None,
        )
        for item in icons:
            if item is None:
                bar.insertSeparator(first)
                continue
            act, icon = item
            if isinstance(icon, str):
                self._glyphs.append((act, icon))
            else:
                act.setIcon(icon)
            act.setToolTip(act.text().replace("&", ""))
            bar.insertAction(first, act)
            if act.menu():
                bar.widgetForAction(act).setPopupMode(QToolButton.InstantPopup)
        self._paint_glyphs()

    def _paint_glyphs(self):
        color = self.palette().windowText().color()
        for act, text in self._glyphs:
            act.setIcon(_glyph(text, color))

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

        v = self.menuBar().addMenu(self.tr("&View"))
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
        self.panels_menu = v.addMenu(self.tr("Panels beside the image"))
        self.panels_menu.aboutToShow.connect(self._fill_panels_menu)
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

        im = self.menuBar().addMenu(self.tr("&Image"))
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

        s = self.menuBar().addMenu(self.tr("&Settings"))
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

        h = self.menuBar().addMenu(self.tr("&Help"))
        self._action(h, self.tr("Training &guide"), lambda: self.show_workspace("guide"), QKeySequence.HelpContents)
        self._action(h, self.tr("Quick &tour"), self.start_tour)
        self._action(h, self.tr("&Practice data for a first night…"), self.practice_data)
        self._action(h, self.tr("Check the &installation and internet services"), self.check_installation)
        self._action(h, self.tr("Check for &updates…"), self.check_updates)
        self._action(h, self.tr("&About {app}").format(app=BRAND.display_name), self.about)

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
            self.open_fits(Path(out["image"]))

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
            QMessageBox.warning(self, self.tr("Cannot open project"), f"{path}\n\n{e}")
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
            QMessageBox.warning(self, self.tr("Cannot open file"), f"{path}\n\n{e}")
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
        self.header_table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            for col, val in enumerate((card.keyword, str(card.value), card.comment)):
                self.header_table.setItem(row, col, QTableWidgetItem(val))

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
    def run_step(self, step_id, inputs, params=None, on_done=None, on_fail=None):
        """Run a step as a task; on_done(outputs) is called on the GUI thread when it succeeds, on_fail(message)
        (instead of the error box) when it fails. Never touch widgets from task.add_callback: that runs on a
        background thread."""
        task = self.engine.run_step(step_id, inputs, params)
        if on_done:
            self._on_done[task.id] = on_done
        if on_fail:
            self._on_fail[task.id] = on_fail
        task.add_callback(self.taskUpdated.emit)
        self.taskUpdated.emit(task)
        return task

    def run_automation(self, auto, inputs):
        """Run an automation task by task: each step starts when the previous one has finished."""
        from ..engine import automation

        gen, page, n = automation.calls(auto, inputs), self.automation_page, [0]

        def advance(out=None):
            try:
                call = next(gen) if out is None else gen.send(out)
                n[0] += 1
                page.step_started(n[0], call[0])
                self.run_step(*call, on_done=advance)  # a failed task shows its error; the chain stops there
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
        text = f"{task.name} — {states[task.state]} {int(task.progress * 100)}% {translate(task.message)}"
        if task.id not in self._task_items:
            self.tasks_list.addItem(text)
            self._task_items[task.id] = (task, self.tasks_list.count() - 1)
        self.tasks_list.item(self._task_items[task.id][1]).setText(text)
        self.progress.setVisible(any(not t.finished for t, _ in self._task_items.values()))
        self.progress.setValue(int(task.progress * 100))
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
                QMessageBox.Warning, self.tr("Task failed"), f"{task.name}\n\n{task_error(task.error)}", parent=self
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
    def scan_raw(self, folder):
        if folder:
            return self.run_step(
                "calibration.scan",
                {"folder": folder},
                {"clock_utc_offset": self.calibrate_page.clock_offset.value()},
                on_done=lambda out: self.calibrate_page.show_frames(
                    out["frames"], out["problems"], out.get("raw_converted", 0)
                ),
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

        return self.run_step("calibration.run", {"frames": frames, "output_dir": output_dir}, params, on_done=done)

    def stack_images(self, images, output, params):
        def done(out):
            if self.engine.project:
                self.engine.project.add_file(Path(out["stack"]), "stack")
            self.calibrate_page.result.setText(self.tr("Stack written: {path}").format(path=out["stack"]))
            self.open_fits(Path(out["stack"]))

        step_id = "stacking.drizzle" if params.pop("drizzle", False) else "stacking.stack"
        return self.run_step(step_id, {"images": images, "output": output}, params, on_done=done)

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
    def measure_light_curve(self, images, target, comps, coord, params):
        inputs = {"images": images, "target_xy": target, "comps_xy": comps}
        if coord:
            inputs["coord"] = coord
        params = dict(params)
        if params.get("extra_xy"):  # check stars and further targets are inputs of the step
            inputs["extra_xy"] = params.pop("extra_xy")
        params.pop("extra_xy", None)

        def done(out):
            lc = out["light_curve"]
            self.photometry_page.show_light_curve(lc)
            self.period_page.set_light_curve(lc["time"], lc["rel_flux"], self.tr("the Photometry page"))

        return self.run_step("photometry.light_curve", inputs, params, on_done=done)

    def search_period(self, time, flux, params):
        return self.run_step(
            "timeseries.period", {"time": time, "flux": flux}, params, on_done=self.period_page.show_result
        )

    def time_minimum(self, light_curve, params):
        def done(out):
            m = out["minimum"]
            self.photometry_page.show_minimum(m)
            self.oc_page.add_minimum(m["time"], m["error"], "this work")  # ready for the O-C diagram
            if params.get("t0") and not self.oc_page.t0.text():
                self.oc_page.t0.setText(repr(params["t0"]))
                self.oc_page.period.setText(repr(params["period"]))

        return self.run_step("timeseries.minimum", {"light_curve": light_curve}, params, on_done=done)

    # --- misc ---------------------------------------------------------------
    def _show_pixel(self, x, y, value):
        label = self.tr("value")
        text = f"x={x:.0f}  y={y:.0f}  {label}={value:.6g}"
        if self.wcs is not None:
            sky = self.wcs.pixel_to_world(x - 1, y - 1)
            text += "  " + sky.to_string("hmsdms", precision=1)
        self.pixel_label.setText(text)

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
        from .tour import TourOverlay, rect_of

        def item(key):
            def rect():
                it = self._nav_items().get(key)
                if it is None:
                    return None
                r = self.nav.visualItemRect(it)
                return QRect(self.nav.viewport().mapTo(self, r.topLeft()), r.size())

            return rect

        self.show_workspace("start")
        dock = self.findChild(QDockWidget, "tasks")
        steps = [
            (None, self.tr("Welcome! This one-minute tour shows where things are. Press Next, or Skip at any time.")),
            (
                lambda: rect_of(self.nav, self),
                self.tr("The pages, in the order of an observing night. Click one to open it."),
            ),
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
                item("guide"),
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
        theme.apply(QApplication.instance(), code)
        self._paint_glyphs()  # the symbols take the text colour of the new theme
        for canvas in self.findChildren(PlotCanvas):  # plots already drawn pick up the new colours
            canvas.figure.set_facecolor(theme.colors(code)["window"])
            canvas.draw()

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
            text = self.tr("Could not check for updates: {e}").format(e=error)
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
        self.engine.shutdown()
        if self.engine.project:
            self.engine.project.close()
        super().closeEvent(event)
