"""Calibrate stage: what the run writes and the free space, shown before Run (CAL-14)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel

from ..calibration.output import check_space, count_files, estimate, free_bytes
from .messages import translate as message

translate = QCoreApplication.translate


def add_estimate_label(page, layout):
    page.estimate = QLabel(page)
    page.estimate.setWordWrap(True)
    layout.addWidget(page.estimate)
    page.output.textChanged.connect(lambda: refresh(page))
    page.split_colour.toggled.connect(lambda: refresh(page))


def _need(page):
    split = page.split_colour.isChecked()
    return estimate(page.frames, split, page._camera_params()["write_planes"]), split


def refresh(page):
    """The line under the output folder; empty until there are lights and a folder."""
    folder = page.output.text().strip()
    if not folder or not any(f["kind"] in ("light", "arc") for f in page.frames):
        page.estimate.setText("")
        return
    need, split = _need(page)
    page.estimate.setText(
        translate(
            "CalibrateEstimate", "This run writes about {n} files, {size} GB, to {folder}; free space {free} GB"
        ).format(
            n=count_files(page.frames, split),
            size=f"{need / 1e9:.1f}",
            folder=folder,
            free=f"{free_bytes(folder) / 1e9:.1f}",
        )  # fmt: skip
    )


def refused(page):
    """True (with the reason on the result line) when the disk cannot hold the run; nothing is written then."""
    try:
        check_space(page.output.text(), _need(page)[0])
    except ValueError as e:
        page.result.setText(message(e))
        return True
    return False
