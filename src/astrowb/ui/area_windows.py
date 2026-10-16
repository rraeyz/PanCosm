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
    actions = [images, blink, prev, nxt, None, bad, comps, radii, measure, None, minimum, export]
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
    from PySide6.QtWidgets import QMenu

    exports = QMenu(translate("MainWindow", "&Export"), win)  # File → Export, just before Close window
    win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
    exports.addActions([export, mirror(page.aavso_button), mirror(page.etd_button)])
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
        if now > last[0]:  # the page went on to a next step: it opens by itself, as the sections did
            win.show_stage(keys[now])
        last[0] = now  # a stage the user went back to stays shown

    page.steps_shown = follow
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
    ]


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
