"""The Photometry and Spectroscopy windows and the Images window's menus and toolbar, built by the main window;
moved out of main_window.py (plans/architecture.md ARC-4.4). Texts keep the main window's translation context."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QAction, QActionGroup

from . import area_menus
from .area_menus import _mirror, _undo_source
from .files import images_filter

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


def photometry_window(main, page):
    """Photometry in its full window (plans/interface.md I5): the image in the middle, the numbered steps in a
    panel on the left, the results (light curve, stars, detrending, minimum, export) in a panel below; a
    toolbar for the frequent actions; every panel can be pulled out and is remembered."""
    from PySide6.QtGui import QAction

    from .kit.window import AreaWindow
    from .start_page import areas

    parts = page.window_parts()
    kinds = {}

    def mirror(widget, short=None, kind=None):
        act = _mirror(widget, page, short)
        if kind:
            kinds[act] = kind
        return act

    images = mirror(page.load_button, translate("MainWindow", "Images…"), "open")
    blink = mirror(page.blink, translate("MainWindow", "Blink"), "blink")
    prev, nxt = (
        mirror(page.prev_frame, translate("MainWindow", "Previous frame"), "previous"),
        mirror(page.next_frame, translate("MainWindow", "Next frame"), "next"),
    )
    for act, text in ((prev, translate("MainWindow", "Previous frame")), (nxt, translate("MainWindow", "Next frame"))):
        act.setText(text)  # the tool buttons show only an arrow
    bad = mirror(page.quality_button, translate("MainWindow", "Bad frames"), "bad_frames")
    comps = mirror(page.suggest_button, translate("MainWindow", "Comparisons"), "comparisons")
    radii = mirror(page.apertures_button, translate("MainWindow", "Radii"), "radii")
    measure = mirror(page.measure_button, translate("MainWindow", "Measure"), "measure")
    minimum = mirror(page.minimum_button, translate("MainWindow", "Minimum"), "minimum")
    leave_out = mirror(page.outlier_button, translate("MainWindow", "Leave out"), "leave_out")
    export = mirror(page.export_button, translate("MainWindow", "Export"), "export")
    target = mirror(page.make_target)
    target.setText(
        translate("MainWindow", "Make the chosen variable star the target")
    )  # the button sits beside its list
    check = QAction(translate("MainWindow", "Mark check stars"), page)
    check.setToolTip(translate("MainWindow", "The next clicks on the image mark check stars (K1, K2…)"))
    check.triggered.connect(lambda: page.click_role.setCurrentIndex(page.click_role.findData("check")))
    menus = _photometry_menu_table(
        main, page, mirror, images, blink, prev, nxt, bad, comps, radii, measure, minimum, target, check
    )
    actions = [images, blink, prev, nxt, None, bad, comps, radii, measure, leave_out, None, minimum, export]
    name = next(n for k, _, n, _ in areas() if k == "photometry")
    win = AreaWindow(
        "photometry",
        name,
        main.settings,
        parts["view"],
        panels=[
            (
                "results",
                translate("MainWindow", "Results: light curve, stars, measurements"),
                parts["results"],
                Qt.BottomDockWidgetArea,
            )
        ],
        menus=menus,
        toolbar=actions,
        undo_stack=_undo_source(page),
        open_files=page.set_images,
        file_filter=images_filter(),
        parent=main,
    )
    _exports_menu(win, page, [export, mirror(page.aavso_button), mirror(page.etd_button)])
    win.set_icons(kinds)  # icons, the names in the tooltips (View → Toolbar text shows them too)
    _photometry_stages(win, page)
    page.setParent(win)  # the page keeps the state and the logic, unseen
    page.hide()
    page.results_dock = win.docks["results"]
    page.results_dock.setVisible(page.target is not None or page.lc_raw is not None)
    main._frames[page] = win.docks["stages"].widget()  # Basic / Expert folds the sections inside the stages
    win.setWindowIcon(main.windowIcon())
    win.help_requested.connect(main._help_for)
    main.area_windows["photometry"] = win
    main._complete_menus(win)


def _exports_menu(win, page, actions):
    """File → Export, just before Close window."""
    from PySide6.QtWidgets import QMenu

    exports = QMenu(translate("MainWindow", "&Export"), win)
    win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
    exports.addActions(actions)
    exports.addAction(translate("MainWindow", "Light-curve file, nothing left out (.lc.ecsv)…"),
                      lambda: _save_lc_file(win, page))  # fmt: skip
    exports.addAction(translate("MainWindow", "Save all into a folder…"), lambda: _save_all(win, page))
    exports.addAction(translate("MainWindow", "Recipe for the command line (.json)…"), lambda: _save_recipe(win, page))
    page.measure_requested.connect(lambda *run: setattr(page, "last_measure", run))  # the run a recipe repeats
    from PySide6.QtWidgets import QPushButton

    box = page.export_button.parentWidget().layout()  # the Report stage: everything at once, first
    page.save_all_button = QPushButton(translate("MainWindow", "Save all into a folder…"), page)
    page.save_all_button.setToolTip(
        translate(
            "MainWindow",
            "Light curve, measurements, star list, fit, plots, summary page, methods text and "
            "references, and the ExoClock files when the times are BJD_TDB",
        )  # fmt: skip
    )
    page.save_all_button.clicked.connect(lambda: _save_all(win, page))
    box.insertWidget(box.indexOf(page.export_button), page.save_all_button)


def _aavso_header(win, page):
    """What the AAVSO exoplanet file needs that the program knows: the observer code (profile), the star (the files'
    OBJECT in the field), the band (the catalogue's, else the FILTER keyword through the profile's table)."""
    from ..core import profiles
    from .aavso_dialog import band_of

    settings = win.settings
    band = page.catalog["filter"] if page.catalog else band_of(settings, getattr(page, "images", None))
    star = ((page.field or {}).get("object") or {}).get("name")
    code = profiles.section(settings, "observer")["aavso_code"]
    return {"OBSCODE": code, "STAR_NAME": star, "FILTER": band}


def _save_all(win, page, folder=None):
    """PHO-27 item 5: the light curve, the measurements table, the star list, the transit fit and the plot."""
    from PySide6.QtWidgets import QFileDialog

    from ..photometry.reports.save_all import save_all

    if page.light_curve is None:
        page.result.setText(translate("MainWindow", "Measure the light curve first."))
        return None
    folder = folder or QFileDialog.getExistingDirectory(win, translate("MainWindow", "Folder for everything"))
    if not folder:
        return None
    stars = None
    if page.target is not None:
        wcs = page._field_wcs() if page.ref in (None, 0) else None
        stars = {"target": page.target, "comps": page.comps, "extras": page.extras, "wcs": wcs,
                 "radii": (page.r_ap.value(), page.r_in.value(), page.r_out.value())}  # fmt: skip
    fit = (getattr(page, "transit_fit", None) or (None, None))[1]
    aavso = _aavso_header(win, page)
    neb = getattr(page, "neb_rows", None)
    files = save_all(folder, page.light_curve, stars, fit, page.plot.figure, _provenance(page), aavso, neb)
    text = translate("MainWindow", "Saved {n} files in {folder}").format(n=len(files), folder=folder)
    names = {"OBSCODE": translate("MainWindow", "your AAVSO observer code (Settings → Profiles → Observer)"),
             "STAR_NAME": translate("MainWindow", "the star's name (the files' OBJECT, or Look up in the Field)"),
             "FILTER": translate("MainWindow", "the band (the FILTER keyword or a catalogue)")}  # fmt: skip
    missing = [names[k] for k, v in aavso.items() if not v]
    if missing and page.light_curve.get("time_scale") == "BJD_TDB":  # say what would let the AAVSO file be written
        text += "\n" + translate("MainWindow", "No AAVSO exoplanet file: it needs {what}.").format(
            what="; ".join(missing)
        )
    page.result.setText(text)
    return files


def _save_recipe(win, page, path=None):
    """PHO-20: the last measurement as an automation file that astrowb-cli recipe runs without the window."""
    from PySide6.QtWidgets import QFileDialog

    from ..photometry.recipe import light_curve_recipe, save

    run = getattr(page, "last_measure", None)
    if run is None:
        page.result.setText(translate("MainWindow", "Measure the light curve first."))
        return None
    path = path or QFileDialog.getSaveFileName(win, translate("MainWindow", "Recipe"), "light_curve.json",
                                               "JSON (*.json)")[0]  # fmt: skip
    if not path:
        return None
    images, target, comps, coord, params = run
    params = dict(params)
    extra, ref = params.pop("extra_xy", ()), params.pop("ref_image", None)
    sky = _stars_sky(page, ref or images[0], target, comps, extra)
    save(light_curve_recipe(images, target, comps, params, coord, extra, ref, stars_sky=sky), path)
    page.result.setText(translate("MainWindow", "Saved {name}").format(name=path))
    return path


def _stars_sky(page, ref, target, comps, extra):
    """The stars' RA, Dec through the identified field's solution or the marked frame's own WCS (PHO-20: a recipe
    then finds them on another night's solved frames); None without either."""
    from astropy.wcs import WCS

    from ..calibration.masters import load

    try:
        wcs = page._field_wcs() if page.field and page.ref in (None, 0) else WCS(load(ref)[1]).celestial
    except (OSError, ValueError, KeyError):
        return None
    if wcs is None or not wcs.has_celestial:
        return None

    def sky(xy):
        return [float(v) for v in wcs.pixel_to_world_values(float(xy[0]), float(xy[1]))]

    return {"target": sky(target), "comps": [sky(c) for c in comps], "extra": [sky(c) for c in extra]}


def _save_lc_file(win, page):
    """PHO-48: the measured light curve whole, readable back by every window."""
    from PySide6.QtWidgets import QFileDialog

    from ..photometry import lcfile

    if page.light_curve is None:
        page.result.setText(translate("MainWindow", "Measure the light curve first."))
        return
    path, _ = QFileDialog.getSaveFileName(win, translate("MainWindow", "Light-curve file"), "light_curve.lc.ecsv",
                                          "ECSV (*.ecsv)")  # fmt: skip
    if path:
        lcfile.write(page.light_curve, path, _provenance(page))
        page.result.setText(translate("MainWindow", "Saved {name}").format(name=path))


def _provenance(page):
    """ARC-11: how the light curve was measured (step, settings, the frames with their sizes and checksums, the
    versions), from the window's last measurement; None before one."""
    from ..core import provenance

    run = getattr(page, "last_measure", None)
    if run is None:
        return None
    images, target, comps, coord, params = run
    settings = dict(params) | {"target_xy": list(target), "comps_xy": [list(c) for c in comps], "coord": coord}
    return provenance.record("photometry.light_curve", settings, {"images": list(images)})


def _stage_parts(page):
    """The steps' contents as stages: [(key, title, widget, guide anchor)]. Each step's controls leave their folding
    section (which then folds an empty box: the page's own step logic goes on unchanged); the workflow summary goes
    with the first stage."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    names = (translate("MainWindow", "Images"), translate("MainWindow", "Stars"),
             translate("MainWindow", "Apertures"), translate("MainWindow", "Measure"))  # fmt: skip
    keys = ("images", "stars", "apertures", "measure")
    anchors = ("photometry-choosing-images-stars", "photometry-differential-photometry-targets-comparison",
               "photometry-apertures", "photometry-measure-light-curve")  # fmt: skip
    out = []
    for k, sec in enumerate([*page.sections, page.other_tools]):
        content = sec.content
        sec.layout().removeWidget(content)
        sec.content = QWidget(sec)  # what the section folds from now on
        content.setVisible(True)
        if k == 0:
            holder = QWidget()
            lay = QVBoxLayout(holder)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(page.guide)
            lay.addWidget(content)
            content = holder
        if k < 4:
            out.append((keys[k], names[k], content, anchors[k]))
        else:
            tools = ("tools", translate("MainWindow", "Other tools"), content, "photometry-live-light-curve")
    # the results' working tabs become stages; the light curve, stars and measurements stay in the results panel
    later = (
        (
            "lightcurve",
            translate("MainWindow", "Light curve"),
            page.show_what,
            "photometry-deleting-bad-points-spacing",
        ),
        ("timing", translate("MainWindow", "Timing"), page.minimum_button, "photometry-time-minimum"),
        ("report", translate("MainWindow", "Report"), page.export_button, "photometry-exporting"),
    )
    for key, title, inside, anchor in later:
        tabs = page.res_tabs
        i = next(i for i in range(tabs.count()) if tabs.widget(i).isAncestorOf(inside))
        box = tabs.widget(i)
        tabs.removeTab(i)
        box.setVisible(True)  # a tab not shown was hidden by its tab widget
        out.append((key, title, box, anchor))
    return [*out, tools]


def _photometry_stages(win, page):
    from . import automatic

    """The steps as stages (plans/interface.md UI-16.1): the rail on the left names them with their state, the
    stage's controls beside it; the page's own step logic (which step is next, which are done) moves the rail."""
    from .kit.anatomy import Stage

    parts = _stage_parts(page)
    win.set_stages([Stage(key, title, widget, anchor) for key, title, widget, anchor in parts])
    keys = [key for key, *_ in parts]

    last = [page._step_now]

    def follow(now, done):
        for k, ok in enumerate(done):
            win.set_stage_state(keys[k], "done" if ok else "empty")
        if now > last[0] and automatic.on("photometry.next_stage"):  # the page went on: the next stage opens
            win.show_stage(keys[now])
        last[0] = now  # a stage the user went back to stays shown

    page.steps_shown = follow
    page.viewer.step_frame.connect(lambda d: page.frame_slider.setValue(page.frame_slider.value() + d))  # [ ]
    page.viewer.blink_key.connect(lambda: page.blink.isEnabled() and page.blink.click())  # b
    for main in (
        page.load_button,
        page.suggest_button,
        page.apertures_button,
        page.measure_button,
        page.minimum_button,
        page.export_button,
    ):  # one main button per stage: F5 presses it (UI-12)
        main.setProperty("primary", True)
        main.style().polish(main)  # fmt: skip
    # the frame list: a results tab beside the light curve, Stars and Measurements (UI-16.1), not in the Images stage
    page.res_tabs.addTab(page.frame_table, translate("MainWindow", "Frames"))
    from .photometry_checks import ChecksTab

    page.checks = ChecksTab(page)  # PHO-33: the night's flags, refreshed with every light curve
    page.res_tabs.addTab(page.checks, translate("MainWindow", "Checks"))
    from .photometry_transit import attach

    attach(win.parent(), page)  # PHO-26: the exact transit under Time of minimum (the window's parent: main)
    page._step_titles()
    win.restoreDockWidget(win.docks["stages"])
    _photometry_inspector(win, page)


def star_rows(page, x, y):
    """The inspector's rows for the star at a click (0-based array x, y), or None where there is no star."""
    from ..io.inspect import saturation_level, star_info

    data = page.viewer.data
    if data is None:
        return None
    try:
        s = star_info(data, x, y, r_ap=page.r_ap.value(), r_in=page.r_in.value(), r_out=page.r_out.value(),
                      saturation=saturation_level(None, data))  # fmt: skip
    except Exception:  # noqa: BLE001 — no star there, at the edge: nothing to show
        return None
    names = {"target": translate("MainWindow", "target"), "comparison": translate("MainWindow", "comparison"),
             "check": translate("MainWindow", "check star")}  # fmt: skip
    near = [(n, role) for n, role, xy in page._star_names() if (xy[0] - s["x"]) ** 2 + (xy[1] - s["y"]) ** 2 <= 9]
    role = f"{near[0][0]} · {names[near[0][1]]}" if near else translate("MainWindow", "not marked")
    peak = f"{s['peak']:.0f}" + (" ⚠ " + translate("MainWindow", "saturated") if s["saturated"] else "")
    return [
        (translate("MainWindow", "Role"), role),
        (translate("MainWindow", "x, y (FITS pixels)"), f"{s['x'] + 1:.2f}, {s['y'] + 1:.2f}"),
        (translate("MainWindow", "Peak"), peak, "ADU"),
        (translate("MainWindow", "Sky per pixel"), s["background"], "ADU"),
        (translate("MainWindow", "Net counts"), f"{s['net_counts']:.0f} ± {s['net_counts_err']:.0f}", "ADU"),
        (translate("MainWindow", "Signal-to-noise"), round(s["snr"], 1)),
        ("FWHM", round(s["fwhm"], 2), "px"),
        *_noise_rows(page, s),
    ]


def _noise_rows(page, s):
    """PHO-34: where the star's noise comes from (photon, sky, dark, read; errors.budget), with the camera of the
    profile (gain 1 and no read noise when it is not filled in), per exposure."""
    import numpy as np

    from ..core import profiles
    from ..photometry.errors import budget
    from . import automatic

    cam = profiles.section(automatic._settings(None), "camera")
    gain = cam.get("gain") or 1.0
    exptime = 0.0
    try:
        from ..calibration.masters import load
        from ..hdr import get

        exptime = float(get(load(page.images[page.shown])[1], "EXPTIME", "EXPOSURE", default=0.0) or 0.0)
    except (OSError, ValueError, IndexError, TypeError, AttributeError):
        pass
    pixels = np.pi * page.r_ap.value() ** 2
    if s["net_counts"] <= 0:
        return []
    dark = (cam.get("dark_current") or 0.0) * exptime
    sky = max(s["background"], 0.0) * gain
    parts, rel = budget(s["net_counts"] * gain, sky, dark, cam.get("read_noise") or 0.0, pixels, 0.0)
    total = sum(parts.values())
    names = {"photon": translate("MainWindow", "star"), "sky": translate("MainWindow", "sky"),
             "dark": translate("MainWindow", "dark"), "read": translate("MainWindow", "read")}  # fmt: skip
    shares = ", ".join(f"{names[k]} {100 * v / total:.0f} %" for k, v in parts.items() if k in names and v > 0)
    return [(translate("MainWindow", "Noise from"), shares), (translate("MainWindow", "Predicted error"),
             round(1000 * rel, 2), "ppt")]  # fmt: skip


def _photometry_inspector(win, page):
    """The inspector (UI-16.1): what a click on the image finds there — the star's role, peak, sky, counts, FWHM."""
    from .kit.inspector import Inspector

    panel = Inspector(translate("MainWindow", "Star"))
    dock = win.set_inspector(panel)
    dock.hide()  # until a star is clicked

    def show(x, y):
        rows = star_rows(page, x, y)
        if rows:
            panel.set_rows(rows)
            dock.show()

    page.viewer.clicked.connect(show)


def spectroscopy_window(main, page):
    """Spectroscopy in its own window (plans/spectroscopy.md step 1.1): the job chosen in the toolbar (and the
    Job menu), its view in the middle, its steps in the left panel."""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QAction, QActionGroup

    from .kit.window import AreaWindow
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
    handler, file_filter = main._opener("spectroscopy", page)
    name = next(n for k, _, n, _ in areas() if k == "spectroscopy")
    win = AreaWindow(
        "spectroscopy",
        name,
        main.settings,
        parts["view"],
        steps=parts["steps"],
        menus=[(translate("MainWindow", "&Job"), actions)],
        toolbar=actions,
        undo_stack=_undo_source(page),
        open_files=handler,
        file_filter=file_filter,
        parent=main,
    )
    jobs = ("long_slit", "echelle", "telluric", "velocity", "cube", "spectrum_tools")
    win.set_icons(dict(zip(actions, jobs, strict=True)))
    area_menus.spectroscopy(main, page, win)
    page.setParent(win)  # the page keeps the state and the logic, unseen
    page.hide()
    main._frames[page] = parts["steps"]
    win.setWindowIcon(main.windowIcon())
    win.help_requested.connect(main._help_for)
    main.area_windows["spectroscopy"] = win
    main._complete_menus(win)


def fill_image_menus(main, win):
    """The Images window's menus as MaxIm DL and AstroImageJ group them (interface I6c.8): Process, Analyse,
    Overlays, Astrometry, Colour, Stack; the page's tool and header buttons are mirrored, not copied."""
    from PySide6.QtWidgets import QApplication

    page = main.image_page
    view = main.view_menu
    view.removeAction(main.overlay_menu.menuAction())  # a menu of its own, as AstroImageJ's Annotate
    tools, group = [], QActionGroup(win)
    for key in page.TOOLS:
        button = page.tool_buttons[key]
        act = QAction(button.text(), win)
        act.setToolTip(button.toolTip())
        act.setStatusTip(button.toolTip())
        act.setCheckable(True)
        act.setChecked(button.isChecked())
        act.triggered.connect(lambda _=False, k=key: page.set_tool(k))
        button.toggled.connect(act.setChecked)
        group.addAction(act)
        tools.append(act)
    main.split_action = QAction(translate("MainWindow", "Split into colour channels (R, G, B)"), win)
    main.split_action.setToolTip(
        translate(
            "MainWindow", "A colour camera's raw image as three half-size images, one per colour (no interpolation)"
        )
    )
    main.split_action.triggered.connect(lambda _=False: main.split_channels())
    main.split_action.setEnabled(False)
    stack = QAction(translate("MainWindow", "Stack the open images…"), win)
    stack.setToolTip(
        translate("MainWindow", "The open images aligned on their stars and averaged with outliers rejected")
    )
    stack.triggered.connect(lambda _=False: main.stack_open_images())
    drizzle = QAction(translate("MainWindow", "Drizzle the open images…"), win)
    drizzle.setToolTip(
        translate("MainWindow", "Dithered images onto a grid twice as fine (sharper for undersampled stars)")
    )
    drizzle.triggered.connect(lambda _=False: main.stack_open_images(drizzle=True))
    win.add_menus(
        [
            (main.process_menu.title(), []),
            (
                translate("MainWindow", "&Analyse"),
                [*tools, None, _mirror(page.whole_button, win), main.coefficients_action],
            ),
            (main.overlay_menu.title(), []),
            (translate("MainWindow", "A&strometry"), [main.solve_action, main.moving_action]),
            (translate("MainWindow", "&Colour"), [main.colour_action, main.split_action]),
            (translate("MainWindow", "S&tack"), [stack, drizzle, None, main.blink_action]),
        ]
    )
    bar = win.menuBar()
    for menu in (main.process_menu, main.overlay_menu):  # the menus themselves: the toolbar opens them too
        empty = next(a for a in bar.actions() if a.menu() and a.text() == menu.title() and a.menu() is not menu)
        bar.insertMenu(empty, menu)
        bar.removeAction(empty)
    view.removeAction(main.blink_action)
    edit = win.edit_menu
    copy_header = QAction(translate("MainWindow", "Copy the header"), win)
    copy_header.triggered.connect(
        lambda _=False: QApplication.clipboard().setText(page.header.tostring(sep="\n") if page.header else "")
    )
    for act in (*[_mirror(b, win) for b in page.keyword_buttons], copy_header):
        edit.insertAction(win.find_action, act)
    edit.insertSeparator(win.find_action)
    file_menu = win.file_menu
    acts = file_menu.actions()
    after_save, close = acts[acts.index(main.save_action) + 1], acts[-1]
    close_image = QAction(translate("MainWindow", "&Close image"), win)
    close_image.triggered.connect(lambda _=False: main.close_image())
    close_all = QAction(translate("MainWindow", "Close &all images"), win)
    close_all.triggered.connect(lambda _=False: main.close_image(everything=True))
    convert = QAction(translate("MainWindow", "&Convert many images (PNG / JPEG / TIFF)…"), win)
    convert.triggered.connect(lambda _=False: main.convert_dialog())
    file_menu.insertActions(after_save, [_mirror(page.header_save, win), main.picture_action, convert])
    file_menu.insertSeparator(after_save)
    file_menu.insertAction(after_save, _mirror(page.export_button, win))
    file_menu.insertActions(close, [close_image, close_all])
    file_menu.insertSeparator(close)


def fill_image_toolbar(main):
    """The most used image commands as small icons above the image: the same actions as in the menus."""
    from PySide6.QtWidgets import QToolButton

    bar, main._glyphs = main.image_page.toolbar, []
    first = bar.actions()[0]  # the measuring tools stay at the end
    icons = (  # kinds of ui/icons.py: the same icon as in the other windows
        (main.open_action, "open"),
        (main.save_action, "save"),
        None,
        (main.previous_action, "previous"),
        (main.next_action, "next"),
        None,
        (main.fit_action, "fit"),
        (main.zoom_in_action, "zoom_in"),
        (main.zoom_out_action, "zoom_out"),
        None,
        (main.levels_action, "levels"),
        (main.blink_action, "blink"),
        (main.overlay_menu.menuAction(), "overlays"),
        None,
        (main.process_menu.menuAction(), "process"),
        (main.solve_action, "solve"),
        None,
    )
    for item in icons:
        if item is None:
            bar.insertSeparator(first)
            continue
        act, kind = item
        if act.menu():  # a button of its own: an icon on the menu's action would replace its name in the menu bar
            menu, button = act.menu(), QToolButton(bar)
            button.setMenu(menu)
            button.setPopupMode(QToolButton.InstantPopup)
            button.setToolTip(act.text().replace("&", ""))
            button.setEnabled(act.isEnabled())
            act.changed.connect(lambda b=button, a=act: b.setEnabled(a.isEnabled()))
            main._glyphs.append((button, kind))
            bar.insertWidget(first, button)
            continue
        main._glyphs.append((act, kind))
        act.setToolTip(act.text().replace("&", ""))
        bar.insertAction(first, act)
    main._paint_glyphs()


def _photometry_menu_table(
    main, page, mirror, images, blink, prev, nxt, bad, comps, radii, measure, minimum, target, check
):
    """The Photometry window's menus (plans/interface.md I6c)."""
    return [  # the approved table (plans/interface.md I6c), in the order of the work
        (
            translate("MainWindow", "F&rames"),
            [
                images,
                mirror(page.live_button),
                blink,
                prev,
                nxt,
                None,
                bad,
                mirror(page.drop_bad),
                mirror(page.restore_button),
            ],
        ),
        (
            translate("MainWindow", "&Stars"),
            [
                comps,
                mirror(page.best_set_button),
                target,
                check,
                None,
                mirror(page.save_stars_button),
                mirror(page.load_stars_button),
                None,
                mirror(page.clear_button),
            ],
        ),
        (
            translate("MainWindow", "&Measure"),
            [
                radii,
                mirror(page.follow_seeing),
                mirror(page.psf),
                mirror(page.remove_neighbours),
                None,
                measure,
                mirror(page.catalog_button),
                mirror(page.pol_button),
            ],
        ),
        (
            translate("MainWindow", "&Analyse"),
            [
                mirror(page.detrend_button),
                mirror(page.undo_detrend),
                mirror(page.bic_button),
                mirror(page.outlier_button),
                None,
                mirror(page.cycle_button),
                mirror(page.save_plot_button),
                mirror(page.open_plot_button),
                None,
                minimum,
                None,
                mirror(page.go_model),
                mirror(page.go_period),
            ],
        ),
    ]
