"""The Calibration window's Report and Log result tabs (plans/interface.md UI-16.2): the Report is the run's result
(`calibration.run` outputs) and what the Check stage left out, as text; the Log is the run's progress messages as
the task sent them (the phases, with the time and the share done)."""

import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QPlainTextEdit, QPushButton

translate = QCoreApplication.translate


def _view():
    view = QPlainTextEdit()
    view.setReadOnly(True)
    view.setFocusPolicy(Qt.NoFocus)  # like the Problems tab: a tab behind the front one keeps out of the Tab chain
    return view


def make(page):
    page.report_view, page.log_view = _view(), _view()
    page.save_report_button = QPushButton(translate("CalibrationWindow", "Save report…"))
    page.save_report_button.setToolTip(
        translate(
            "CalibrationWindow",
            "Writes the report as a text file. After each run the report is also written to "
            "calibration_report.txt in the output folder, over the previous run's file.",
        )
    )
    page.save_report_button.clicked.connect(lambda: save_dialog(page))
    page.result_shown.connect(lambda out: show_report(page, out))
    show_report(page, None)


def report_text(out, left_out=()):
    """The report's lines: what the run wrote and which frames were left out, from the result alone."""
    if out is None:
        return translate("CalibrationWindow", "Calibrate to get the report.")
    lines = [
        translate("CalibrationWindow", "{n} images calibrated, {m} master frames written.").format(
            n=len(out.get("calibrated") or []), m=len(out.get("masters") or [])
        )
    ]
    if out.get("arcs"):
        lines.append(
            translate("CalibrationWindow", "{n} arc lamp frames calibrated (bias and dark only).").format(
                n=len(out["arcs"])
            )
        )
    if out.get("dark_scales"):
        lines.append(
            translate("CalibrationWindow", "Dark scaled by {lo:.3f}–{hi:.3f} (DARKSCAL in each file's header).").format(
                lo=min(out["dark_scales"]), hi=max(out["dark_scales"])
            )
        )
    lines += [f"{p}: {why}" for p, why in left_out]
    return "\n".join(lines)


def show_report(page, out):
    page.report_view.setPlainText(report_text(out, page.left_out))


def start_log(page, task):
    """Begin the Log for a new run; `log_update` adds a line whenever the task's message or progress moves."""
    page.log_view.clear()
    page._log_last = None
    log_update(page, task)


def log_update(page, task):
    from .messages import translate as message_text

    line = f"{int(task.progress * 100):3d} %  {message_text(task.message)}".rstrip()
    if line != getattr(page, "_log_last", None):
        page._log_last = line
        page.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {line}")


FILE = "calibration_report.txt"


def save_file(path, page):
    """Write the report as shown to `path`; False when the place cannot be written."""
    try:
        Path(path).write_text(page.report_view.toPlainText() + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def save_dialog(page):
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getSaveFileName(page, translate("CalibrationWindow", "Save report"), FILE, "Text (*.txt)")
    if path and not save_file(path, page):
        page.review_status.setText(
            translate("CalibrationWindow", "The report could not be written to {path}.").format(path=path)
        )


def save_beside_frames(page, output_dir):
    """After a run: the report goes into the output folder, over the previous run's file; the Review line says so."""
    path = Path(output_dir) / FILE
    if output_dir and save_file(path, page):
        page.review_status.setText(translate("CalibrationWindow", "Report written to {path}.").format(path=path))
        return path
    return None
