"""Calibrate stage: "Follow a folder…" (CAL-22). Each new FITS file that appears in the folder is calibrated with the
masters of the last run (or none: refused) by `LiveCalibrator`, written to the output folder like the batch run."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QFileDialog, QPushButton

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
    page.live_sink = None  # the main window sets it
    page.follower, page.follow_state = FolderFollower(page, lambda paths: _calibrate(page, paths)), None
    page.follow_button.toggled.connect(lambda on: _toggled(page, on))
    column.addWidget(page.follow_button)
    page.follow_send = QCheckBox(translate("CalibrateFollow", "Send each calibrated frame to Photometry"), page)
    page.follow_send.setToolTip(
        translate(
            "CalibrateFollow",
            "The Photometry window measures each frame as soon as it is calibrated, "
            "with the stars and apertures set there",
        )
    )
    column.addWidget(page.follow_send)


def _toggled(page, on):
    if not on:
        page.follower.stop()
        return
    from ..calibration.library_use import library_folder, open_library
    from ..settings import Settings

    masters, library = list(getattr(page, "masters", [])), library_folder(Settings())
    if (not masters and open_library(library) is None) or not page.output.text():
        page.result.setText(translate("CalibrateFollow", "Make or choose the masters first"))
        page.follow_button.setChecked(False)
        return
    folder = QFileDialog.getExistingDirectory(page, translate("CalibrateFollow", "Follow a folder…"))
    if not folder:
        page.follow_button.setChecked(False)
        return
    from ..calibration.live import LiveCalibrator

    try:
        live = LiveCalibrator(
            masters,
            page.output.text(),
            cosmic_rays=page.cosmics.isChecked(),
            params=page._camera_params() | {"find_trails": page.find_trails.isChecked()},
            library=library,
        )
    except (OSError, ValueError) as e:
        page.result.setText(message(e))
        page.follow_button.setChecked(False)
        return
    page.follow_state = {"live": live, "folder": folder, "n": 0, "last": "", "error": "", "waiting": False}
    page.follower.start(folder)
    _show(page)


def _calibrate(page, paths):
    state = page.follow_state
    done = []
    for path in paths:
        try:
            out = state["live"].process(path)
            state["last"] = _name(out)
            done.append(out)
            state["n"] += 1
            state["error"] = ""
        except (OSError, ValueError) as e:  # an unreadable or wrong-sized file: said here, following goes on
            state["error"] = f"{_name(path)}: {message(e)}"
    state["waiting"] = bool(done) and page.follow_send.isChecked() and not _send(page, done)
    _show(page)


def _send(page, done):
    """Hand the calibrated files to Photometry's live mode; False when it is not measuring (they wait there)."""
    if page.live_sink is None:
        return True
    try:
        return page.live_sink(done)
    except (OSError, ValueError) as e:  # a Photometry error: said, goes on
        page.follow_state["error"] = message(e)
        return True


def _name(path):
    from pathlib import Path

    return Path(path).name


def _show(page):
    s = page.follow_state
    line = translate("CalibrateFollow", "Following {folder}: {n} frames calibrated, last {name}").format(
        folder=s["folder"], n=s["n"], name=s["last"] or "-"
    )
    wait = translate(
        "CalibrateFollow", "Photometry is not measuring yet: set the stars and start live photometry there"
    )
    from .calibrate_light_checks import trail_lines

    trails = trail_lines({"trails": s["live"].trails})
    page.result.setText("\n".join(x for x in (line, *trails, s["error"], wait if s.get("waiting") else "") if x))
