"""Calibrate stage: "Follow a folder…" (CAL-22). Each new FITS file that appears in the folder is calibrated with the
masters of the last run (or none: refused) by `LiveCalibrator`, written to the output folder like the batch run."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog, QPushButton

from .image_follow import FolderFollower
from .messages import translate as message

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("CalibrateFollow", "…") calls


def add_follow_button(page, column):
    page.follow_button = QPushButton(translate("CalibrateFollow", "Follow a folder…"), page)
    page.follow_button.setCheckable(True)
    page.follow_button.setToolTip(
        translate(
            "CalibrateFollow",
            "Each new light that appears in the folder is calibrated with this night's masters as it arrives; "
            "the calibrated file is written to the output folder",
        )
    )
    page.follower, page.follow_state = FolderFollower(page, lambda paths: _calibrate(page, paths)), None
    page.follow_button.toggled.connect(lambda on: _toggled(page, on))
    column.addWidget(page.follow_button)


def _toggled(page, on):
    if not on:
        page.follower.stop()
        return
    masters = list(getattr(page, "masters", []))
    if not masters or not page.output.text():
        page.result.setText(translate("CalibrateFollow", "Make or choose the masters first"))
        page.follow_button.setChecked(False)
        return
    folder = QFileDialog.getExistingDirectory(page, translate("CalibrateFollow", "Follow a folder…"))
    if not folder:
        page.follow_button.setChecked(False)
        return
    from ..calibration.live import LiveCalibrator

    try:
        live = LiveCalibrator(masters, page.output.text(), params=page._camera_params())
    except (OSError, ValueError) as e:
        page.result.setText(message(e))
        page.follow_button.setChecked(False)
        return
    page.follow_state = {"live": live, "folder": folder, "n": 0, "last": "", "error": ""}
    page.follower.start(folder)
    _show(page)


def _calibrate(page, paths):
    state = page.follow_state
    for path in paths:
        try:
            state["last"] = _name(state["live"].process(path))
            state["n"] += 1
            state["error"] = ""
        except (OSError, ValueError) as e:  # an unreadable or wrong-sized file: said here, following goes on
            state["error"] = f"{_name(path)}: {message(e)}"
    _show(page)


def _name(path):
    from pathlib import Path

    return Path(path).name


def _show(page):
    s = page.follow_state
    line = translate("CalibrateFollow", "Following {folder}: {n} frames calibrated, last {name}").format(
        folder=s["folder"], n=s["n"], name=s["last"] or "-"
    )
    page.result.setText(f"{line}\n{s['error']}" if s["error"] else line)
