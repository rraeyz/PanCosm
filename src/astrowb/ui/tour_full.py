"""The full tour (Help → Full tour): the first quick tour's 16 stops, one per area and part of the start window.
The six-stop quick tour in tour.py is the default."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDockWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MainWindow", "…") calls


def start_full(main):
    from .tour import TourOverlay, rect_of

    main.tour = TourOverlay(main, _steps(main, rect_of))
    main.tour.start()
    return main.tour


def _steps(main, rect_of):
    """The tour's stops: (where, text)."""
    from PySide6.QtWidgets import QToolButton

    def item(key):  # the area's block on the start page
        return lambda: rect_of(main.start_page.findChild(QToolButton, f"start_{key}"), main)

    def blocks():
        shown = [rect_of(b, main) for b in main.start_page.blocks]
        shown = [r for r in shown if r is not None]
        return shown[0].united(shown[-1]) if shown else None

    main.show_workspace("start")
    dock = main.findChild(QDockWidget, "tasks")
    return [
        (
            None,
            translate(
                "MainWindow", "Welcome! This one-minute tour shows where things are. Press Next, or Skip at any time."
            ),
        ),
        (
            blocks,
            translate(
                "MainWindow", "The areas, in the order of an observing night. Click one to open it in its window."
            ),
        ),
        (
            lambda: rect_of(main.start_page, main),
            translate(
                "MainWindow",
                "Start here: pick what you have — raw frames, images, spectra, a list of minima — and its window opens.",  # noqa: E501
            ),
        ),
        (
            item("plan"),
            translate(
                "MainWindow",
                "Planning: when your targets are visible, airmass, the Moon, predicted eclipses and transits.",
            ),
        ),
        (
            item("observe"),
            translate(
                "MainWindow",
                "Observing: connect the telescope and camera, run sequences and whole nights. The safety supervisor parks the telescope when something is wrong.",  # noqa: E501
            ),
        ),
        (
            item("calibrate"),
            translate(
                "MainWindow",
                "Calibration: bias, dark and flat frames are matched and applied automatically; frames can be aligned and stacked.",  # noqa: E501
            ),
        ),
        (
            item("photometry"),
            translate(
                "MainWindow",
                "Photometry, then Light curves and period and O−C: measure stars, get light curves, periods, minima and O−C diagrams.",  # noqa: E501
            ),
        ),
    ] + _later_steps(main, rect_of, dock)


def _later_steps(main, rect_of, dock):
    """The second half of the tour's stops."""

    def item(key):  # the area's block on the start page
        from PySide6.QtWidgets import QToolButton

        return lambda: rect_of(main.start_page.findChild(QToolButton, f"start_{key}"), main)

    return [
        (
            item("astrometry"),
            translate(
                "MainWindow", "Astrometry: positions of an asteroid or comet on plate-solved frames, the MPC report."
            ),
        ),
        (
            item("spectroscopy"),
            translate(
                "MainWindow",
                "Spectroscopy: long-slit and echelle reduction, telluric correction, radial velocities, IFU cubes.",
            ),
        ),
        (
            item("orbits"),
            translate(
                "MainWindow",
                "Models: eclipsing-binary and transit light-curve models, absolute dimensions and visual orbits.",
            ),
        ),
        (
            item("remotesensing"),
            translate(
                "MainWindow",
                "Remote sensing: satellite and aerial images — band math, vegetation and water indices, classes.",
            ),
        ),
        (
            item("automation"),
            translate(
                "MainWindow",
                "Automation: chain steps into your own pipeline or start from a ready template (eclipsing binary night, transit, calibration, spectra to RV) and run it in one go.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),  # the guide has no block: Help → Training guide opens it
            translate(
                "MainWindow",
                "Guide: every window explained step by step, by category, with search. Help → Training guide opens it; F1 in a window opens its own page.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(dock, main),
            translate(
                "MainWindow", "Tasks: long jobs run here in the background with their progress; you can keep working."
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),
            translate(
                "MainWindow",
                "Menus: Plugins for your own tools, Settings for language, look and CPU/GPU, Help for this tour and the guide; each area's window has its own menus and toolbar.",  # noqa: E501
            ),
        ),
        (
            lambda: rect_of(main.menuBar(), main),  # Help → Practice data is there
            translate(
                "MainWindow",
                "In every area window: the stages on the left (Ctrl+1…9), F5 runs the stage's main action, F1 or Shift+F1 opens help, Ctrl+K finds any action, Ctrl+/ lists every key. To try it all, Help → Practice data for a first night gives data with known answers.",  # noqa: E501
            ),
        ),
    ]
