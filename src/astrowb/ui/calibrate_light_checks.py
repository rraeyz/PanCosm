"""The Calibrate stage's searches on the lights: cosmic rays (moved here from the page unchanged) and satellite trails
(plans/calibration.md CAL-12)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox

translate = QCoreApplication.translate


def add_light_checks(page):
    page.cosmics = QCheckBox(translate("CalibratePage", "Remove cosmic rays from lights"), page)
    page.cosmics.setToolTip(
        translate(
            "CalibratePage",
            "Finds cosmic-ray hits in each light by their sharp edges (L.A.Cosmic, astroscrappy) and replaces them."
            " Useful for long exposures and spectra; not needed when many frames are stacked with rejection. "
            "The slowest part of calibrating the lights: switch it off for a quick pass.",
        )
    )
    page.find_trails = QCheckBox(translate("CalibratePage", "Find satellite trails in lights"), page)
    page.find_trails.setToolTip(
        translate(
            "CalibratePage",
            "Searches each calibrated light for a satellite or aircraft trail; costs about 2-3 s per 2k frame. "
            "Trails are listed under Problems and flagged in the image's DQ plane, not repaired.",
        )
    )


def trail_lines(out):
    return [
        translate("CalibratePage", "{file}: satellite trail across the frame (angle {angle:.1f}°)").format(**t)
        for t in out.get("trails") or []
    ]
