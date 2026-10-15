"""The main window's own menus (File, Edit, View, Image, Settings, Window, Help), moved out of main_window.py
(plans/architecture.md ARC-4.4). Texts keep the main window's translation context."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QUndoGroup

from .. import compute
from ..display import INTERVALS, STRETCHES
from . import help_checks, online_actions
from .i18n import LANGUAGES
from .kit.widgets import bar_menu

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


def build(main):
    m = bar_menu(main.menuBar(), translate("MainWindow", "&File"))
    main._action(m, translate("MainWindow", "&New project…"), main.new_project_dialog, QKeySequence.New)
    main._action(m, translate("MainWindow", "Open &project…"), main.open_project_dialog)
    m.addSeparator()
    main.open_action = main._action(m, translate("MainWindow", "&Open FITS…"), main.open_fits_dialog, QKeySequence.Open)
    main.save_action = main._action(
        m, translate("MainWindow", "&Save FITS as…"), main.save_as_dialog, QKeySequence.SaveAs
    )
    main.save_action.setEnabled(False)
    main.picture_action = main._action(
        m, translate("MainWindow", "Save &picture (PNG / JPEG / TIFF)…"), main.save_picture_dialog
    )
    main.picture_action.setEnabled(False)
    main._action(m, translate("MainWindow", "&Convert many images (PNG / JPEG / TIFF)…"), main.convert_dialog)
    m.addSeparator()
    main._action(m, translate("MainWindow", "&Close image"), main.close_image, QKeySequence.Close)
    main._action(m, translate("MainWindow", "Close &all images"), lambda: main.close_image(everything=True))
    m.addSeparator()
    main._action(m, translate("MainWindow", "&Quit"), main.close, QKeySequence.Quit)

    e = bar_menu(main.menuBar(), translate("MainWindow", "&Edit"))
    main.undo_group = QUndoGroup(main)
    main.undo_action = main.undo_group.createUndoAction(main, translate("MainWindow", "&Undo"))
    main.undo_action.setShortcuts([QKeySequence(QKeySequence.Undo)])
    main.redo_action = main.undo_group.createRedoAction(main, translate("MainWindow", "&Redo"))
    redo = [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")] + QKeySequence.keyBindings(QKeySequence.Redo)
    unique = {k.toString(): k for k in redo}  # one key twice on one action is "ambiguous": it would do nothing
    main.redo_action.setShortcuts(list(unique.values()))
    for act, tip in (
        (
            main.undo_action,
            translate("MainWindow", "Take back the last change in this window (stars marked, points deleted, …)"),
        ),
        (main.redo_action, translate("MainWindow", "Do again what Undo took back")),
    ):
        act.setToolTip(tip)
        e.addAction(act)

    _view_and_image(main)
    _image(main)
    _plugins_settings_window_help(main)


def _view_and_image(main):
    """View and Image menus."""
    v = main.view_menu = bar_menu(main.menuBar(), translate("MainWindow", "&View"))
    main.fit_action = main._action(v, translate("MainWindow", "Zoom to &fit"), main.viewer.fit, "F")
    main.zoom_in_action = main._action(
        v, translate("MainWindow", "Zoom &in"), lambda: main.viewer.zoom(1.25), QKeySequence.ZoomIn
    )
    zoom_out = QKeySequence.ZoomOut
    main.zoom_out_action = main._action(
        v, translate("MainWindow", "Zoom &out"), lambda: main.viewer.zoom(0.8), zoom_out
    )
    names = {
        "zscale": translate("MainWindow", "ZScale"),
        "minmax": translate("MainWindow", "Min–max"),
        "99.5%": translate("MainWindow", "99.5 %"),
        "linear": translate("MainWindow", "Linear"),
        "sqrt": translate("MainWindow", "Square root"),
        "log": translate("MainWindow", "Logarithmic"),
        "asinh": translate("MainWindow", "Asinh"),
    }
    main.previous_action = main._action(
        v, translate("MainWindow", "&Previous image"), lambda: main.image_page.step_image(-1)
    )
    main.next_action = main._action(v, translate("MainWindow", "&Next image"), lambda: main.image_page.step_image(1))
    for act, key in ((main.previous_action, Qt.Key_PageUp), (main.next_action, Qt.Key_PageDown)):
        act.setShortcut(key)
        act.setShortcutContext(Qt.WidgetWithChildrenShortcut)  # only over the image: tables keep their keys
        main.image_page.addAction(act)
    v.addSeparator()
    main.levels_action = main._action(
        v, translate("MainWindow", "Display &levels and colours…"), main.levels_dialog, "Ctrl+L"
    )
    main.blink_action = main._action(v, translate("MainWindow", "&Blink images…"), main.blink_dialog)
    from .overlay_actions import add_menu as add_overlay_menu

    main.overlay_menu = add_overlay_menu(main, v)
    for title, keys, kw in (
        (translate("MainWindow", "Interval"), INTERVALS, "interval"),
        (translate("MainWindow", "Stretch"), STRETCHES, "stretch"),
    ):
        sub, group = v.addMenu(title), QActionGroup(main)
        for key in keys:
            act = main._action(sub, names[key], lambda _=False, k=key, kw=kw: main.viewer.set_stretch(**{kw: k}))
            act.setCheckable(True)
            act.setChecked(key == getattr(main.viewer, kw))
            group.addAction(act)


def _image(main):
    """The Image menu."""
    im = main.image_bar_menu = bar_menu(main.menuBar(), translate("MainWindow", "&Image"))
    main.solve_action = main._action(
        im, translate("MainWindow", "&Plate solve (ASTAP / astrometry.net)"), main.plate_solve
    )
    main.solve_action.setEnabled(False)
    main.colour_action = main._action(
        im, translate("MainWindow", "&Colour image from three filters…"), main.colour_dialog
    )
    main.moving_action = main._action(
        im, translate("MainWindow", "&Asteroid and comet astrometry…"), main.moving_dialog
    )
    main.coefficients_action = main._action(
        im, translate("MainWindow", "Photometric &coefficients (extinction, transformation)…"), main.coefficients_dialog
    )
    main.process_menu = im.addMenu(translate("MainWindow", "P&rocess"))
    main.process_menu.setEnabled(False)
    main.apply_all_action = main.process_menu.addAction(translate("MainWindow", "Apply to all open images"))
    main.apply_all_action.setCheckable(True)
    main.apply_all_action.setToolTip(
        translate(
            "MainWindow", "The next operations run on every image in the list; the processed copies take their places"
        )
    )
    main.process_menu.setToolTipsVisible(True)
    main.process_menu.addSeparator()
    ops = (
        (translate("MainWindow", "Pixel math…"), "pixel_math"),
        (translate("MainWindow", "Flip left–right"), ("flip", {"axis": "x"})),
        (translate("MainWindow", "Flip top–bottom"), ("flip", {"axis": "y"})),
        (translate("MainWindow", "Rotate 90°"), ("rotate90", {"k": 1})),
        (translate("MainWindow", "Rotate by any angle…"), "rotate"),
        (translate("MainWindow", "Resample (change the pixel size)…"), "resample"),
        (translate("MainWindow", "Bin 2×2"), ("bin", {"factor": 2})),
        (translate("MainWindow", "Crop…"), "crop"),
        (translate("MainWindow", "Gaussian smoothing…"), "gaussian"),
        (translate("MainWindow", "Median filter…"), "median"),
        (translate("MainWindow", "Unsharp mask…"), "unsharp"),
        (translate("MainWindow", "Remove background gradient…"), "background"),
        (translate("MainWindow", "Kernel filter…"), "kernel"),
        (translate("MainWindow", "Deconvolution (Richardson–Lucy)…"), "deconvolve"),
        (translate("MainWindow", "Digital development (DDP)"), ("ddp", {})),
        (translate("MainWindow", "Match the histogram of another image…"), "histogram_match"),
    )
    for text, op in ops:
        main._action(main.process_menu, text, lambda _=False, o=op: main.process_dialog(o))


def _plugins_settings_window_help(main):
    """Plugins, Settings, Window and Help menus."""
    main.plugins_menu = bar_menu(main.menuBar(), translate("MainWindow", "&Plugins"))
    main.plugins_menu.aboutToShow.connect(main._fill_plugins_menu)

    s = main.settings_menu = bar_menu(main.menuBar(), translate("MainWindow", "&Settings"))
    main.expert_action = QAction(translate("MainWindow", "&Expert mode (every option open)"), main)
    main.expert_action.setCheckable(True)
    main.expert_action.setChecked(main.ui_mode() == "expert")
    main.expert_action.toggled.connect(lambda on: main.set_ui_mode("expert" if on else "basic"))
    s.addAction(main.expert_action)
    s.addSeparator()
    lang_menu, group = s.addMenu(translate("MainWindow", "&Language")), QActionGroup(main)
    current = main.settings.get("ui.language")
    for code, native in LANGUAGES.items():
        act = main._action(lang_menu, native, lambda _=False, c=code: main.set_language(c))
        act.setCheckable(True)
        act.setChecked(code == current)
        group.addAction(act)

    theme_menu, group = s.addMenu(translate("MainWindow", "&Look")), QActionGroup(main)
    looks = {"dark": translate("MainWindow", "Dark"), "light": translate("MainWindow", "Light")}
    for code, label in looks.items():
        act = main._action(theme_menu, label, lambda _=False, c=code: main.set_theme(c))
        act.setCheckable(True)
        act.setChecked(code == main.settings.get("ui.theme", "dark"))
        group.addAction(act)

    dev_menu, group = s.addMenu(translate("MainWindow", "&Processing device")), QActionGroup(main)
    names = {
        "auto": translate("MainWindow", "Automatic (GPU when useful)"),
        "cpu": translate("MainWindow", "CPU only"),
        "gpu": translate("MainWindow", "GPU"),
    }
    for code, label in names.items():
        act = main._action(dev_menu, label, lambda _=False, c=code: main.set_compute(c))
        act.setCheckable(True)
        act.setChecked(code == compute.mode())
        group.addAction(act)

    s.addSeparator()
    online_actions.add(main, s)
    text_menu = s.addMenu(translate("MainWindow", "Text size"))  # View → Text size in the area windows
    sizes = (
        (translate("MainWindow", "&Larger text"), 1, "Ctrl+Shift++"),
        (translate("MainWindow", "&Smaller text"), -1, "Ctrl+Shift+-"),
        (translate("MainWindow", "&Normal text size"), 0, "Ctrl+Shift+0"),
    )
    for text, step, key in sizes:
        act = main._action(text_menu, text, lambda s=step: main._change_font(s), key)
        # the keys only in the main window: the area windows show this menu under Edit and have the same keys in
        # their View menu (one key on two actions of a window does nothing: Ctrl+Shift++ did not work there)
        act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        main.addAction(act)
    main.window_menu = bar_menu(main.menuBar(), translate("MainWindow", "&Window"))
    main.window_menu.aboutToShow.connect(main._fill_window_menu)
    help_checks.add_menu(main)
