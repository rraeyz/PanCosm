"""Each area window's own menus and toolbar, built from the page's controls (interface I6c), moved out of
main_window.py (plans/architecture.md ARC-4.4). Texts keep the main window's translation context ("MainWindow")."""

from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QAction


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


def calibrate(main, page, win):
    """Calibration: Frames, Masters, Process, Send (interface I6c.4), from the page's own controls."""

    def named(widget, text, short=None):
        act = _mirror(widget, page, short)
        act.setText(text)  # the button's text carries its place in the steps ("3.", "Browse…")
        return act

    lights = named(
        page.lights_browse,
        QCoreApplication.translate("MainWindow", "Lights folder…"),
        QCoreApplication.translate("MainWindow", "Lights"),
    )
    frames = named(page.frames_browse, QCoreApplication.translate("MainWindow", "Calibration frames folder…"))
    scan = _mirror(page.scan_button)
    run = named(page.run_button, QCoreApplication.translate("MainWindow", "Calibrate"))
    stack = named(
        page.stack_button,
        QCoreApplication.translate("MainWindow", "Stack into one deep picture"),
        QCoreApplication.translate("MainWindow", "Stack"),
    )
    send = named(
        page.photometry_button,
        QCoreApplication.translate("MainWindow", "Send to Photometry →"),
        QCoreApplication.translate("MainWindow", "Photometry"),
    )
    win.add_menus(
        [
            (
                QCoreApplication.translate("MainWindow", "F&rames"),
                [
                    lights,
                    frames,
                    _mirror(page.add_folder_button),
                    None,
                    scan,
                    None,
                    _mirror(page.remove_button),
                    _mirror(page.clear_button),
                ],
            ),
            (
                QCoreApplication.translate("MainWindow", "&Masters"),
                [
                    _mirror(page.cosmics),
                    _mirror(page.optimize_dark),
                    _mirror(page.fix_defects),
                    _mirror(page.split_colour),
                    _mirror(page.spectra),
                ],
            ),
            (QCoreApplication.translate("MainWindow", "&Process"), [run, None, stack, _mirror(page.drizzle)]),
            (QCoreApplication.translate("MainWindow", "Se&nd"), [send]),
        ],
        toolbar=[lights, scan, None, run, stack, None, send],
    )
    win.set_icons({lights: "open_folder", scan: "scan", run: "calibrate", stack: "stack", send: "send"})


def timeseries(main, page, win):
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

    load = tab(pp.load_button, pp, short=QCoreApplication.translate("MainWindow", "Load"))
    fetch = tab(
        pp.fetch_button,
        pp,
        QCoreApplication.translate("MainWindow", "Download a light curve (TESS, Kepler, ZTF, AAVSO)"),
        QCoreApplication.translate("MainWindow", "Download"),
    )
    save = tab(pp.save_button, pp, short=QCoreApplication.translate("MainWindow", "Save"))
    search = tab(pp.search_button, pp, QCoreApplication.translate("MainWindow", "Period search"))
    freq = tab(fp.button, fp)
    var = tab(vf.button, vf)
    win.add_menus(
        [
            (
                QCoreApplication.translate("MainWindow", "&Data"),
                [
                    tab(pp.delete_mode, pp),
                    tab(pp.clip_button, pp),
                    tab(pp.bin_button, pp),
                    tab(pp.units_button, pp),
                    None,
                    tab(pp.undo_button, pp),
                ],
            ),
            (QCoreApplication.translate("MainWindow", "Se&arch"), [search, freq, None, tab(vf.choose_button, vf), var]),
            (QCoreApplication.translate("MainWindow", "Se&nd"), [tab(fp.to_oc, fp), tab(vf.send, vf)]),
        ],
        toolbar=[load, fetch, save, None, search, freq, var],
    )
    files = QMenu(
        QCoreApplication.translate("MainWindow", "&Light curve"), win
    )  # File → Light curve, before Close window
    win.file_menu.insertMenu(win.file_menu.actions()[-1], files)
    files.addActions([fetch, save])  # loading is File → Open… (Ctrl+O, or drop a file)
    win.set_icons(
        {
            load: "open",
            fetch: "download",
            save: "save",
            search: "period_search",
            freq: "frequency",
            var: "variable_search",
        }
    )


def oc(main, page, win):
    """O−C: Ephemeris, Models, File → Load minima / Export (interface I6c.6)."""
    from PySide6.QtGui import QActionGroup
    from PySide6.QtWidgets import QMenu

    def named(widget, text=None, short=None):
        act = _mirror(widget, page, short)
        if text:
            act.setText(text)
        return act

    load = named(
        page.load_button,
        QCoreApplication.translate("MainWindow", "Load minimum times…"),
        QCoreApplication.translate("MainWindow", "Load"),
    )
    look = named(
        page.look_up,
        QCoreApplication.translate("MainWindow", "Look up the ephemeris (VSX)"),
        QCoreApplication.translate("MainWindow", "Look up"),
    )
    fit = named(page.fit_button, short=QCoreApplication.translate("MainWindow", "Fit"))
    export = named(page.results_button, short=QCoreApplication.translate("MainWindow", "Export"))
    models = [named(r) for r in (page.linear, page.quadratic, page.ltte, page.apsidal)]
    group = QActionGroup(win)  # one model at a time, as the radio buttons
    for act in models:
        group.addAction(act)
    win.add_menus(
        [
            (QCoreApplication.translate("MainWindow", "E&phemeris"), [look, None, models[0], models[1], None, fit]),
            (QCoreApplication.translate("MainWindow", "&Models"), [models[2], models[3], None, named(page.use_mcmc)]),
        ],
        toolbar=[load, look, fit, export],
    )
    files = QMenu(QCoreApplication.translate("MainWindow", "&Export"), win)
    win.file_menu.insertMenu(win.file_menu.actions()[-1], files)  # loading minima is File → Open… (Ctrl+O)
    files.addAction(export)
    win.set_icons({load: "open", look: "lookup", fit: "fit_model", export: "export"})


def plan(main, page, win):
    """Planning: Targets and Night (interface I6c.9)."""

    def named(widget, text=None, short=None):
        act = _mirror(widget, page, short)
        if text:
            act.setText(text)
        return act

    add = named(page.add_button, QCoreApplication.translate("MainWindow", "Add target"))
    ephemeris = named(
        page.ephemeris_button,
        QCoreApplication.translate("MainWindow", "Add target with ephemeris"),
        QCoreApplication.translate("MainWindow", "With ephemeris"),
    )
    plan = named(page.plan_button)
    schedule = named(page.schedule_button)
    send = named(page.send_button, short=QCoreApplication.translate("MainWindow", "Send"))
    exposure = named(page.exposure_button)
    win.add_menus(
        [
            (QCoreApplication.translate("MainWindow", "&Targets"), [add, ephemeris, None, named(page.remove_button)]),
            (QCoreApplication.translate("MainWindow", "&Night"), [plan, exposure, None, schedule, send]),
        ],
        toolbar=[add, ephemeris, None, plan, exposure, None, schedule, send],
    )
    win.set_icons(
        {
            add: "add_target",
            ephemeris: "ephemeris",
            plan: "plan_night",
            exposure: "exposure",
            schedule: "schedule",
            send: "send",
        }
    )


def observe(main, page, win):
    """Observing: Devices, Telescope, Camera, Focus, Flats, Sequence (interface I6c.9), as N.I.N.A. and
    MaxIm DL group their observatory controls."""
    b = page.buttons

    def named(key, text=None):
        act = _mirror(b[key], page)
        if text:
            act.setText(text)
        return act

    acts = {key: named(key) for key in b}
    for key, text in (
        ("cooler_off", QCoreApplication.translate("MainWindow", "Cooler off")),
        ("focuser", QCoreApplication.translate("MainWindow", "Move the focuser")),
        ("filter", QCoreApplication.translate("MainWindow", "Change the filter")),
        ("cool", QCoreApplication.translate("MainWindow", "Cool the camera")),
    ):
        acts[key].setText(text)
    a = acts
    win.add_menus(
        [
            (QCoreApplication.translate("MainWindow", "&Devices"), [a["set_up"], a["connect"], None, a["start_local"]]),
            (
                QCoreApplication.translate("MainWindow", "&Telescope"),
                [a["slew"], a["centre"], a["polar"], None, a["park"]],
            ),
            (
                QCoreApplication.translate("MainWindow", "&Camera"),
                [a["preview"], None, a["cool"], a["cooler_off"], None, a["filter"]],
            ),
            (QCoreApplication.translate("MainWindow", "F&ocus"), [a["autofocus"], a["focuser"]]),
            (QCoreApplication.translate("MainWindow", "F&lats"), [a["sky_flats"], a["panel_flats"]]),
            (
                QCoreApplication.translate("MainWindow", "&Sequence"),
                [a["add_row"], a["remove_row"], None, a["start"], a["abort"], a["resume"], None, a["clear_plan"]],
            ),
        ],
        toolbar=[
            a["connect"],
            None,
            a["slew"],
            a["centre"],
            a["park"],
            None,
            a["preview"],
            a["autofocus"],
            None,
            a["start"],
            a["abort"],
        ],
    )
    win.set_icons(
        {
            a["connect"]: "connect",
            a["slew"]: "slew",
            a["centre"]: "centre",
            a["park"]: "park",
            a["preview"]: "preview",
            a["autofocus"]: "autofocus",
            a["start"]: "start",
            a["abort"]: "abort",
        }
    )


def automation(main, page, win):
    """Automation: File → New / Save as, Steps, Run (interface I6c.10)."""

    def named(widget, text=None, short=None):
        act = _mirror(widget, page, short)
        if text:
            act.setText(text)
        return act

    new = named(
        page.new_button,
        QCoreApplication.translate("MainWindow", "New automation"),
        QCoreApplication.translate("MainWindow", "New"),
    )
    save = named(
        page.save_button,
        QCoreApplication.translate("MainWindow", "Save the automation as…"),
        QCoreApplication.translate("MainWindow", "Save as"),
    )
    add = named(page.add_button)
    remove, up, down = (
        named(b, t)
        for b, t in zip(
            page.step_buttons,
            (
                QCoreApplication.translate("MainWindow", "Remove the step"),
                QCoreApplication.translate("MainWindow", "Move the step up"),
                QCoreApplication.translate("MainWindow", "Move the step down"),
            ),
            strict=True,
        )
    )
    run = named(
        page.run_button,
        QCoreApplication.translate("MainWindow", "Run the automation"),
        QCoreApplication.translate("MainWindow", "Run"),
    )
    send = named(
        page.sequence_button, page.sequence_button.toolTip(), QCoreApplication.translate("MainWindow", "To Observing")
    )
    win.add_menus(
        [
            (QCoreApplication.translate("MainWindow", "&Steps"), [add, remove, None, up, down]),
            (QCoreApplication.translate("MainWindow", "&Run"), [run, None, send, named(page.after_night)]),
        ],
        toolbar=[new, save, None, add, None, run, send],
    )
    win.file_menu.insertActions(win.file_menu.actions()[-1], [new, save])
    win.file_menu.insertSeparator(win.file_menu.actions()[-1])
    win.set_icons({new: "new", save: "save", add: "add_step", run: "start", send: "send"})


def remotesensing(main, page, win):
    """Remote sensing: Analyse (band formula, classification, principal components) (interface I6c.10);
    opening is File → Open… (Ctrl+O, or a drop)."""
    compute = _mirror(page.compute_button, page, QCoreApplication.translate("MainWindow", "Compute"))
    compute.setText(QCoreApplication.translate("MainWindow", "Compute the band formula"))
    classify = _mirror(page.classify_button, page, QCoreApplication.translate("MainWindow", "Classify"))
    pca = _mirror(page.pca_button, page, QCoreApplication.translate("MainWindow", "Components"))
    win.add_menus(
        [(QCoreApplication.translate("MainWindow", "&Analyse"), [compute, None, classify, pca])],
        toolbar=[win.file_menu.actions()[0], None, compute, classify, pca],
    )
    win.set_icons({win.file_menu.actions()[0]: "open", compute: "compute", classify: "classify", pca: "pca"})


def orbits(main, page, win):
    """Models: Fit, Visual orbit, File → Compare / Export (interface I6c.7); each item shows its tab first."""
    from PySide6.QtWidgets import QMenu

    binary, visual = page.tabs.widget(0), page.visual_tab

    def tab(widget, owner, text=None, short=None):
        act = _mirror(widget, page, short)
        if text:
            act.setText(text)
        act.triggered.connect(lambda _=False: page.tabs.setCurrentWidget(owner))
        return act

    fit = tab(
        page.fit_button,
        binary,
        QCoreApplication.translate("MainWindow", "Fit the eclipse or transit model"),
        QCoreApplication.translate("MainWindow", "Fit"),
    )
    posterior = tab(page.posterior_button, binary, short=QCoreApplication.translate("MainWindow", "Posterior"))
    orbit = tab(visual.fit_button, visual, short=QCoreApplication.translate("MainWindow", "Visual orbit"))
    export = tab(page.results_button, binary, short=QCoreApplication.translate("MainWindow", "Export"))
    win.add_menus(
        [
            (
                QCoreApplication.translate("MainWindow", "F&it"),
                [fit, posterior, None, tab(page.use_mcmc, binary), tab(page.use_orbit, binary)],
            ),
            (QCoreApplication.translate("MainWindow", "Visual &orbit"), [tab(visual.load_button, visual), orbit]),
        ],
        toolbar=[win.file_menu.actions()[0], fit, posterior, orbit, None, export],
    )
    win.file_menu.insertAction(win.file_menu.actions()[-1], tab(page.overlay_button, binary))
    exports = QMenu(QCoreApplication.translate("MainWindow", "&Export"), win)
    win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
    exports.addActions(
        [export, tab(page.phoebe_button, binary), tab(page.wd_button, binary), tab(page.transit_button, binary)]
    )
    win.set_icons(
        {
            win.file_menu.actions()[0]: "open",
            fit: "fit_model",
            posterior: "posterior",
            orbit: "visual_orbit",
            export: "export",
        }
    )


def spectroscopy(main, page, win):
    """Reduce, Lines, Spectrum, Measure, Velocity and File → Export (interface I6c.5, the table agreed from
    IRAF's tasks and iSpec's Operations / Parameters menus): every item does what its job's button does, and
    shows that job first."""
    from PySide6.QtWidgets import QMenu

    red, ech, tel, vel, cube, tools = (
        page.reduce_tab,
        page.echelle_tab,
        page.telluric_tab,
        page.velocity_tab,
        page.cube_tab,
        page.tools_tab,
    )

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

    t = (red, ech, tel, vel, cube, tools)
    menus = _reduce_and_lines(job, either, *t) + _spectrum_measure_velocity(job, *t)
    win.add_menus(menus)
    exports = QMenu(QCoreApplication.translate("MainWindow", "&Export"), win)  # File → Export, just before Close window
    win.file_menu.insertMenu(win.file_menu.actions()[-1], exports)
    exports.addActions(
        [
            job(tools, tools.save_button, QCoreApplication.translate("MainWindow", "Save the spectrum as…")),
            job(tools, tools.bess_button),
        ]
    )


def _reduce_and_lines(job, either, red, ech, tel, vel, cube, tools):
    """The Reduce and Lines menus of the Spectroscopy window."""
    return [
        (
            QCoreApplication.translate("MainWindow", "&Reduce"),
            [
                job(
                    red, red.extract_button, QCoreApplication.translate("MainWindow", "Extract the long-slit spectrum")
                ),
                None,
                job(
                    ech,
                    ech.find_button,
                    QCoreApplication.translate("MainWindow", "Find the échelle orders on the flat"),
                ),
                job(ech, ech.extract_button, QCoreApplication.translate("MainWindow", "Extract the échelle orders")),
                None,
                job(cube, cube.load_button),
                job(cube, cube.show_button),
                job(
                    cube, cube.save_button, QCoreApplication.translate("MainWindow", "Save the cube region's spectrum…")
                ),
            ],
        ),
        (
            QCoreApplication.translate("MainWindow", "&Lines"),
            [
                job(red, red.reference_button),
                job(ech, ech.database_button),
                None,
                job(red, red.solve_button, QCoreApplication.translate("MainWindow", "Fit the wavelengths (long slit)")),
                job(
                    ech,
                    ech.solve_button,
                    QCoreApplication.translate("MainWindow", "Fit the wavelengths, merge the orders (échelle)"),
                ),
                None,
                either(red.refit_button.text(), "refit_button"),
                either(red.forget_button.text(), "forget_button"),
            ],
        ),
    ]


def _spectrum_measure_velocity(job, red, ech, tel, vel, cube, tools):
    """The Spectrum, Measure and Velocity menus of the Spectroscopy window."""
    return [
        (
            QCoreApplication.translate("MainWindow", "S&pectrum"),
            [
                job(tools, tools.open_button),
                None,
                job(tools, tools.normalise_button),
                job(tools, tools.pick),
                job(tools, tools.through_button),
                job(tools, tools.smooth_button),
                job(tools, tools.resample_button),
                None,
                job(tools, tools.combine_button),
                job(tools, tools.response_button),
                job(tools, tools.apply_resp),
                None,
                job(tel, tel.button, QCoreApplication.translate("MainWindow", "Telluric correction")),
                job(tools, tools.open_b_button),
                job(tools, tools.arith_button, QCoreApplication.translate("MainWindow", "Arithmetic with spectrum B")),
            ],
        ),
        (
            QCoreApplication.translate("MainWindow", "Mea&sure"),
            [
                job(tools, tools.measure_button, QCoreApplication.translate("MainWindow", "Measure a line")),
                job(tools, tools.vr_button),
                job(tools, tools.series_button),
                None,
                job(tools, tools.atm_button),
                job(vel, vel.type_button),
            ],
        ),
        (
            QCoreApplication.translate("MainWindow", "Velo&city"),
            [job(vel, vel.rv_button), job(vel, vel.separate_button), job(vel, vel.orbit_button)],
        ),
    ]
