"""Settings → the internet: the Earth-rotation tables (ARC-1), working offline and the cache of catalogue answers
(ARC-14). Texts keep the main window's translation context ("MainWindow")."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from ..services import cache


def add(win, menu):

    settings = win.settings
    win.time_tables_action = QAction(
        QCoreApplication.translate("MainWindow", "Keep the Earth-rotation tables up to date (weekly)"), win
    )
    win.time_tables_action.setCheckable(True)
    win.time_tables_action.setChecked(bool(settings.get("time.auto_refresh", True)))
    win.time_tables_action.setToolTip(
        QCoreApplication.translate(
            "MainWindow",
            "Once a week, when online, about 3 MB from the IERS. Altitudes and airmass need them; BJD does not",
        )
    )
    win.time_tables_action.toggled.connect(lambda on: settings.set("time.auto_refresh", on))
    menu.addAction(win.time_tables_action)
    win._action(
        menu, QCoreApplication.translate("MainWindow", "Update the Earth-rotation tables now"), win.update_time_tables
    )
    cache.set_offline(bool(settings.get("services.offline", False)))  # worker processes started later inherit it
    win.offline_action = QAction(QCoreApplication.translate("MainWindow", "Work offline"), win)
    win.offline_action.setCheckable(True)
    win.offline_action.setChecked(cache.offline())
    win.offline_action.setToolTip(
        QCoreApplication.translate(
            "MainWindow", "Catalogues, archives and name look-ups answer only from what was fetched before"
        )
    )
    win.offline_action.toggled.connect(lambda on: (settings.set("services.offline", on), cache.set_offline(on)))
    win.offline_action.toggled.connect(lambda on: win.start_page.show_offline(on))
    win.start_page.show_offline(cache.offline())
    status_strip(win)
    menu.addAction(win.offline_action)
    win._action(
        menu, QCoreApplication.translate("MainWindow", "Clear the saved catalogue answers…"), lambda: clear(win)
    )


def status_strip(win):
    """The start window's status strip (UI-5 item 5): the processing device and Online / Offline; a click on the
    second switches working offline."""
    from PySide6.QtWidgets import QLabel, QToolButton

    translate = QCoreApplication.translate
    win.compute_chip = QLabel(win)
    win.compute_chip.setProperty("muted", True)
    show_compute(win)
    online = win.online_chip = QToolButton(win)
    online.setAutoRaise(True)

    def show(_on=None):
        off = win.offline_action.isChecked()
        online.setText(translate("MainWindow", "● Offline") if off else translate("MainWindow", "● Online"))
        back = translate("MainWindow", "Click to work online again")
        away = translate("MainWindow", "Click to work offline (catalogues answer from what was fetched)")
        online.setToolTip(back if off else away)

    online.clicked.connect(win.offline_action.toggle)
    win.offline_action.toggled.connect(show)
    show()
    win.statusBar().addPermanentWidget(win.compute_chip)
    win.statusBar().addPermanentWidget(online)


def show_compute(win):
    """The processing setting in words (never probing the GPU here: that would load its driver at start-up)."""
    from .. import compute

    translate = QCoreApplication.translate
    words = {
        "auto": translate("MainWindow", "Processing: automatic"),
        "cpu": translate("MainWindow", "Processing: CPU"),
        "gpu": translate("MainWindow", "Processing: GPU"),
    }
    win.compute_chip.setText(words.get(compute.mode(), compute.mode()))


def clear(win, ask=True):
    n, size = cache.size()
    text = QCoreApplication.translate(
        "MainWindow",
        "Delete {n} saved answers of catalogues and archives ({mb:.0f} MB)? They are fetched again when needed.",
    ).format(n=n, mb=size / 1e6)
    title = QCoreApplication.translate("MainWindow", "Saved catalogue answers")
    if ask and QMessageBox.question(win, title, text) != QMessageBox.Yes:
        return False
    cache.clear()
    return True
