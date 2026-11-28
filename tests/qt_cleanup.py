"""Deleting the windows a test opened (kept, they piled up and slowed every later style change)."""


def delete_window(win):
    """The main window and the area windows it opened are deleted after each test: kept, they piled up (408 windows
    after the every-button test) and every later style change re-polished them all (CI: one font test took 15 min)."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    for area in list(getattr(win, "area_windows", {}).values()):
        area.close()
        area.deleteLater()
    win.close()
    win.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
