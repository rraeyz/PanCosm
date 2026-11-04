"""The Photometry window's Checks results tab (plans/photometry.md PHO-33, interface UI-16.1): the night's flags —
cloud, bad seeing, a jump of the field, near saturation — with the one-line verdict and the flagged frames."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryChecks", "…") calls


def kinds():
    return {
        "cloud": translate("PhotometryChecks", "behind cloud"),
        "seeing": translate("PhotometryChecks", "bad seeing"),
        "jump": translate("PhotometryChecks", "the field jumped"),
        "near_saturation": translate("PhotometryChecks", "near saturation"),
    }


def advice_lines(items):
    """The next-night advice (photometry.advice) in words, each with its reason."""
    words = {
        "exposure": translate(
            "PhotometryChecks",
            "Expose {suggest:.0f} s instead of {now:.0f} s: the highest peak reached {peak:.0f} of the limit "
            "{limit:.0f}; this puts it at 60 %.",
        ),
        "defocus": translate(
            "PhotometryChecks",
            "Defocus a little: the brightest pixel holds {percent:.0f} % of the target's light, so flat-field errors "
            "weigh on every point.",
        ),
        "lost": translate(
            "PhotometryChecks",
            "Comparison {star} was missing on {percent:.0f} % of the frames: point so that it stays well inside the "
            "frame, or choose another.",
        ),
        "cadence": translate(
            "PhotometryChecks",
            "Only {points} points over the ingress at a {cadence_s:.0f} s cadence: shorter exposures resolve it.",
        ),
    }
    return [words[a["kind"]].format(**a, percent=100 * a.get("share", 0)) for a in items if a["kind"] in words]


class ChecksTab(QWidget):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.flags, self.files = page, {}, []
        lay = QVBoxLayout(self)
        self.verdict = QLabel(translate("PhotometryChecks", "Measure the light curve to check the night."), self)
        self.verdict.setWordWrap(True)
        self.leave_out = QPushButton(translate("PhotometryChecks", "Leave out the flagged points"), self)
        self.leave_out.setToolTip(
            translate("PhotometryChecks", "Their points leave the light curve; Undo brings them back")
        )
        self.leave_out.setEnabled(False)
        self.leave_out.clicked.connect(self.leave_out_flagged)
        self.table = DataTable(self)
        self.table.row_chosen.connect(self._show)
        self.advice = QLabel(self)
        self.advice.setWordWrap(True)
        lay.addWidget(self.verdict)
        lay.addWidget(self.advice)
        lay.addWidget(self.leave_out)
        lay.addWidget(self.table, 1)

    def _show(self, i):
        """The chosen point's frame on the image (the light curve may hold fewer frames than the list)."""
        name = self.files[i] if i is not None and i < len(self.files) else None
        index = next((k for k, p in enumerate(self.page.images) if Path(p).name == name), None)
        if index is not None:
            self.page.show_frame(index)

    def _advice(self, lc):
        from ..calibration.masters import load
        from ..hdr import get
        from ..photometry.advice import next_night

        exptime = None
        try:
            exptime = (
                get(load(self.page.images[0])[1], "EXPTIME", "EXPOSURE", default=None) if self.page.images else None
            )
        except (OSError, ValueError, IndexError):  # no frame to read: the advice that needs no exposure time
            pass
        fit = getattr(self.page, "transit_fit", None)  # the ingress from the fitted transit, when there is one
        d = fit[1]["derived"] if fit else {}
        ingress = (d["t14_h"] - d["t23_h"]) / 2 / 24 if d.get("t14_h", 0) > d.get("t23_h", 0) else None
        lines = advice_lines(next_night(lc, exptime=exptime, ingress_days=ingress))
        title = translate("PhotometryChecks", "For next time:")
        return "\n".join([title, *("• " + x for x in lines)]) if lines else ""

    def leave_out_flagged(self):
        """Through the page's undoable exclusion, as its saturated-points command."""
        page = self.page
        frames = sorted({i for v in self.flags.values() for i in v})
        ids = {page._frame_ids[i] for i in frames if i < len(page._frame_ids)}
        if ids:
            page.edit(translate("PhotometryChecks", "leave out the flagged points"), page._exclude, page.excluded | ids)

    def show_checks(self, lc):
        from ..photometry.quality import lc_checks

        flags, _line = lc_checks(lc)
        self.flags = flags
        self.leave_out.setEnabled(any(flags.values()))
        names = kinds()
        counts = [f"{len(v)} × {names[k]}" for k, v in flags.items() if v]
        self.verdict.setText(
            translate("PhotometryChecks", "Flagged frames: {list}").format(list=", ".join(counts))
            if counts
            else translate("PhotometryChecks", "No frame flagged: no cloud, seeing jump, field jump or saturation.")
        )
        self.advice.setText(self._advice(lc))
        files = self.files = list(lc.get("file") or [""] * len(lc.get("rel_flux", [])))
        rows = sorted({i for v in flags.values() for i in v})
        self.table.set_data(
            [translate("PhotometryChecks", "Frame"), translate("PhotometryChecks", "File"),
             translate("PhotometryChecks", "Flags")],
            [[i + 1, Path(str(files[i])).name if i < len(files) else "",
              ", ".join(names[k] for k, v in flags.items() if i in v)] for i in rows],
            keys=rows,
        )  # fmt: skip
        return flags
