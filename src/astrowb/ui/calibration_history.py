"""The Calibration window's History result tab (plans/interface.md UI-16.2): the calibration lines of app.log written
since the window opened, and the calibration runs of the open project's history. Read-only, with a filter line; the
dock stays hidden until there is a line to show."""

import time

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

translate = QCoreApplication.translate


def history_lines(project, log_text, since):
    """Calibration lines: the project's runs of `calibration.*` steps, then app.log lines (text starting with a
    timestamp not before `since`) that mention calibration (the task timeline lines carry the step name)."""
    lines = []
    for run in project.runs(full=False) if project else []:
        if run["step"].startswith("calibration."):
            lines.append(
                f"{run['started']}  {run['step']} {run['status']}" + (f": {run['error']}" if run["error"] else "")
            )
    lines += [ln for ln in log_text.splitlines() if ln[:19] >= since and "calibration" in ln.lower()]
    return lines


def make(win, page):
    box = QWidget(win)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    page.history_filter = QLineEdit(box)
    page.history_filter.setPlaceholderText(translate("CalibrationWindow", "Filter the history"))
    page.history_filter.setClearButtonEnabled(True)
    page.history_view = QPlainTextEdit(box)
    page.history_view.setReadOnly(True)
    page.history_view.setFocusPolicy(Qt.NoFocus)
    lay.addWidget(page.history_filter)
    lay.addWidget(page.history_view, 1)
    page._history_since = time.strftime("%Y-%m-%d %H:%M:%S")
    page._history_lines = []
    page.history_dock = (win, ("history", translate("CalibrationWindow", "History"), box))
    box.hide()  # docked at the first line: hidden docks left a stray tab bar in the Tab order
    page.history_filter.textChanged.connect(lambda: _show(page))


def refresh(main, page):
    """Read app.log and the project again (`main`: the main window); called when a calibration run has finished."""
    from ..core import log

    page._history_lines = history_lines(
        main.engine.project, log.tail(main.settings.path.parent, 2000), page._history_since
    )
    _show(page)


def _show(page):
    needle = page.history_filter.text().strip().lower()
    page.history_view.setPlainText("\n".join(ln for ln in page._history_lines if needle in ln.lower()))
    if page._history_lines and isinstance(page.history_dock, tuple):  # not docked yet
        win, (key, title, box) = page.history_dock
        page.history_dock = win.add_result_tab(key, title, box)
        box.show()  # hidden by hand above, so docking alone would not show it
        page.history_dock.show()
