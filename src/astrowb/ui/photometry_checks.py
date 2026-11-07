"""The Photometry window's Checks results tab (plans/photometry.md PHO-33, interface UI-16.1): the night's flags —
cloud, bad seeing, a jump of the field, near saturation — with the one-line verdict and the flagged frames."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .kit.table_view import DataTable
from .kit.widgets import PlotCanvas

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryChecks", "…") calls


def kinds():
    return {
        "cloud": translate("PhotometryChecks", "behind cloud"),
        "seeing": translate("PhotometryChecks", "bad seeing"),
        "jump": translate("PhotometryChecks", "the field jumped"),
        "near_saturation": translate("PhotometryChecks", "near saturation"),
        "spike": translate("PhotometryChecks", "cosmic ray or hot pixel in an aperture"),
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
    words["noise"] = translate("PhotometryChecks", "{term} is {percent:.0f} % of the target's noise: {remedy}")
    words["pointing"] = translate(
        "PhotometryChecks",
        "Point {dx:+d} px in x and {dy:+d} px in y on the frame: every star's path over the night then stays inside "
        "it with its sky ring.",
    )
    words["drift"] = translate(
        "PhotometryChecks",
        "The target moved about {px:.0f} px over the night: flat-field errors then enter the light curve; guide "
        "better, or take flats the same night.",
    )
    words["pointing_wide"] = translate(
        "PhotometryChecks",
        "The stars spread wider than the frame over the night: choose comparison stars nearer the target.",
    )
    terms = {
        "sky": (translate("PhotometryChecks", "The sky"),
                translate("PhotometryChecks", "a smaller aperture, a narrower filter or a darker sky lowers it.")),
        "scintillation": (translate("PhotometryChecks", "Scintillation"),
                          translate("PhotometryChecks", "longer exposures or a larger telescope lower it.")),
        "read": (translate("PhotometryChecks", "Read noise"),
                 translate("PhotometryChecks", "longer exposures or binning lower it.")),
        "dark": (translate("PhotometryChecks", "Dark current"),
                 translate("PhotometryChecks", "a colder camera lowers it.")),
    }  # fmt: skip
    out = []
    for a in items:
        if a["kind"] == "noise":
            term, remedy = terms.get(a["term"], (a["term"], ""))
            out.append(words["noise"].format(term=term, percent=100 * a["share"], remedy=remedy))
        elif a["kind"] == "pointing":
            out.append(words["pointing"].format(**a) if a["fits"] else words["pointing_wide"])
        elif a["kind"] in words:
            out.append(words[a["kind"]].format(**a, percent=100 * a.get("share", 0)))
    return out


class ChecksTab(QWidget):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.flags, self.files, self.factor = page, {}, [], None
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
        self.noise = QLabel(self)
        self.noise.setWordWrap(True)
        self.scale_button = QPushButton(self)
        self.scale_button.setToolTip(
            translate(
                "PhotometryChecks",
                "Reports and files then carry the scaled errors too (rel_flux_err_scaled); the formal ones stay",
            )
        )
        self.scale_button.hide()
        self.scale_button.clicked.connect(self._toggle_scale)
        lay.addWidget(self.verdict)
        lay.addWidget(self.noise)
        lay.addWidget(self.scale_button)
        lay.addWidget(self.advice)
        lay.addWidget(self.leave_out)
        self.panels = PlotCanvas(self)
        self.panels.setMinimumHeight(260)
        self.panels.hide()
        lay.addWidget(self.panels, 2)
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

        exptime, gain, h = None, 1.0, None
        try:
            h = load(self.page.images[0])[1] if self.page.images else {}
            exptime = get(h, "EXPTIME", "EXPOSURE", default=None)
            gain = float(get(h, "EGAIN", "GAIN", default=1.0) or 1.0)
        except (OSError, ValueError, IndexError):  # no frame to read: the advice that needs no exposure time
            pass
        fit = getattr(self.page, "transit_fit", None)  # the ingress from the fitted transit, when there is one
        d = fit[1]["derived"] if fit else {}
        ingress = (d["t14_h"] - d["t23_h"]) / 2 / 24 if d.get("t14_h", 0) > d.get("t23_h", 0) else None
        shape = (h.get("NAXIS2"), h.get("NAXIS1")) if h and h.get("NAXIS1") else None
        lines = advice_lines(next_night(lc, exptime=exptime, ingress_days=ingress, gain=gain, shape=shape))
        title = translate("PhotometryChecks", "For next time:")
        return "\n".join([title, *("• " + x for x in lines)]) if lines else ""

    def _show_noise(self, lc):
        """PHO-34: the observed scatter against the predicted errors, and the offer to scale them above 1.2."""
        from ..photometry.errors import point_to_point_ratio

        ratio, factor = point_to_point_ratio(lc.get("rel_flux", []), lc.get("rel_flux_err", []))
        self.factor = factor
        self.noise.setText(
            ""
            if ratio is None
            else translate("PhotometryChecks", "Scatter from point to point: {r:.2f} × the predicted errors.").format(
                r=ratio
            )
            + (translate("PhotometryChecks", " The errors are too small: scale them.") if factor else "")
        )
        self._label_scale(lc)

    def _label_scale(self, lc):
        scaled = "error_scale" in lc
        self.scale_button.setVisible(bool(self.factor) or scaled)
        self.scale_button.setText(
            translate("PhotometryChecks", "Use the formal errors")
            if scaled
            else translate("PhotometryChecks", "Scale the errors by {f:.2f}").format(f=self.factor or 1.0)
        )

    def _toggle_scale(self):
        """The factor and the scaled errors kept beside the formal ones (never overwriting them)."""
        import numpy as np

        lc = self.page.light_curve
        if lc is None:
            return
        if "error_scale" in lc:
            lc.pop("error_scale")
            lc.pop("rel_flux_err_scaled", None)
        elif self.factor:
            lc["error_scale"] = self.factor
            lc["rel_flux_err_scaled"] = (np.asarray(lc["rel_flux_err"], float) * self.factor).tolist()
        self._label_scale(lc)

    def _draw_panels(self, lc, flags):
        """The night at a glance (PHO-33): comparison counts, sky, FWHM, the field's x and y, airmass on the light
        curve's points, the flagged frames marked on every panel."""
        import numpy as np

        from ..photometry.fit_steps import _series
        from .kit.tokens import role

        n = len(lc.get("rel_flux") or [])
        comp = np.asarray(lc.get("comp_flux") or [], float)
        series = {translate("PhotometryChecks", "Comparison counts"): comp.reshape(n, -1).sum(1) if comp.size else None}
        names = {"sky": translate("PhotometryChecks", "Sky"), "fwhm": "FWHM", "x": "x", "y": "y",
                 "airmass": translate("PhotometryChecks", "Airmass")}  # fmt: skip
        for key, label in names.items():
            values = _series(lc, key)
            series[label] = np.asarray([np.nan if v is None else v for v in values], float) if values else None
        shown = {k: v for k, v in series.items() if v is not None and len(v) == n and np.isfinite(v).any()}
        self.panels.setVisible(bool(shown))
        fig = self.panels.figure
        fig.clear()
        if not shown:
            return
        flagged = sorted({i for v in flags.values() for i in v if i < n})
        axes = fig.subplots(len(shown), 1, sharex=True)
        for ax, (label, y) in zip(np.atleast_1d(axes), shown.items(), strict=True):
            ax.plot(np.arange(n), y, ".", ms=2)
            if flagged:
                ax.plot(flagged, y[flagged], "o", ms=4, color=role("saturated"))  # the warning colour
            ax.set_ylabel(label, fontsize=7)
            ax.tick_params(labelsize=7)
        np.atleast_1d(axes)[-1].set_xlabel(translate("PhotometryChecks", "Frame"), fontsize=7)
        self.panels.draw()

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
        self._show_noise(lc)
        self._draw_panels(lc, flags)
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
