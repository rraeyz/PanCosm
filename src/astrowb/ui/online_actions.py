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
    menu.addAction(win.offline_action)
    win._action(
        menu, QCoreApplication.translate("MainWindow", "Clear the saved catalogue answers…"), lambda: clear(win)
    )


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
