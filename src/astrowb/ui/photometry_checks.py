"""The Photometry window's Checks results tab (plans/photometry.md PHO-33, interface UI-16.1): the night's flags —
cloud, bad seeing, a jump of the field, near saturation — with the one-line verdict and the flagged frames."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryChecks", "…") calls


def kinds():
    return {
        "cloud": translate("PhotometryChecks", "behind cloud"),
        "seeing": translate("PhotometryChecks", "bad seeing"),
        "jump": translate("PhotometryChecks", "the field jumped"),
        "near_saturation": translate("PhotometryChecks", "near saturation"),
    }


class ChecksTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self.verdict = QLabel(translate("PhotometryChecks", "Measure the light curve to check the night."), self)
        self.verdict.setWordWrap(True)
        self.table = DataTable(self)
        lay.addWidget(self.verdict)
        lay.addWidget(self.table, 1)

    def show_checks(self, lc):
        from ..photometry.quality import lc_checks

        flags, _line = lc_checks(lc)
        names = kinds()
        counts = [f"{len(v)} × {names[k]}" for k, v in flags.items() if v]
        self.verdict.setText(
            translate("PhotometryChecks", "Flagged frames: {list}").format(list=", ".join(counts))
            if counts
            else translate("PhotometryChecks", "No frame flagged: no cloud, seeing jump, field jump or saturation.")
        )
        files = lc.get("file") or [""] * len(lc.get("rel_flux", []))
        rows = sorted({i for v in flags.values() for i in v})
        self.table.set_data(
            [translate("PhotometryChecks", "Frame"), translate("PhotometryChecks", "File"),
             translate("PhotometryChecks", "Flags")],
            [[i + 1, Path(str(files[i])).name if i < len(files) else "",
              ", ".join(names[k] for k, v in flags.items() if i in v)] for i in rows],
            keys=rows,
        )  # fmt: skip
        return flags
