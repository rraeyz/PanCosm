"""A system notification when long work ends while the program is not in front (plans/interface.md UI-9): the
desktop's own message (Windows' action centre, macOS' notification centre, a Linux notification), through a tray
icon made the first time and kept. Settings → General can turn it off (ui.notify)."""

import time

LONG_S = 60  # shorter work: the window's Toast and the task-bar flash are enough
_tray = []


def worth_it(task, settings):
    """Whether the task's end deserves a notification: it ran longer than LONG_S and they are not turned off."""
    started = getattr(task, "_started", None)
    return bool(settings.get("ui.notify", True)) and started is not None and time.monotonic() - started > LONG_S


def notify(window, title, text):
    """Show the message; False where the desktop has no place for it (no tray: some Linux desktops)."""
    from PySide6.QtWidgets import QSystemTrayIcon

    if not QSystemTrayIcon.isSystemTrayAvailable():
        return False
    if not _tray:
        tray = QSystemTrayIcon(window.windowIcon(), window.window())
        tray.activated.connect(lambda *_: window.activateWindow())
        _tray.append(tray)
    _tray[0].show()
    _tray[0].showMessage(title, text, QSystemTrayIcon.Information, 8000)
    return True
