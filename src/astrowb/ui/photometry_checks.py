"""The Photometry window's Checks results tab (plans/photometry.md PHO-33, interface UI-16.1): the night's flags —
cloud, bad seeing, a jump of the field, near saturation — with the one-line verdict and the flagged frames."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from .kit.table_view import DataTable
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryChecks", "…") calls


def kinds():
    return {
        "cloud": translate("PhotometryChecks", "behind cloud"),
        "seeing": translate("PhotometryChecks", "bad seeing"),
        "jump": translate("PhotometryChecks", "the field jumped"),
        "near_saturation": translate("PhotometryChecks", "near saturation"),
        "spike": translate("PhotometryChecks", "cosmic ray or hot pixel in an aperture"),
        "trail": translate("PhotometryChecks", "satellite or aircraft trail across an aperture"),
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
        self.leave_out.clicked.connect(lambda: self.leave_out_flagged())
        self.leave_kind = QPushButton(translate("PhotometryChecks", "Leave out only…"), self)
        self.leave_kind.setToolTip(translate("PhotometryChecks", "The frames of one kind of flag, the others kept"))
        self.leave_kind.setMenu(QMenu(self.leave_kind))
        self.leave_kind.setEnabled(False)
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
        row = QHBoxLayout()
        row.addWidget(self.leave_out)
        row.addWidget(self.leave_kind)
        row.addStretch(1)
        lay.addLayout(row)
        self.panels_box, self.panels = plot_box(self)
        self.panels.setMinimumHeight(260)
        self.panels_box.hide()
        lay.addWidget(self.panels_box, 2)
        self.rms_box, self.rms = plot_box(self)  # PHO-34: RMS against bin size, the red noise's β
        self.rms.setMinimumHeight(180)
        self.rms_box.hide()
        lay.addWidget(self.rms_box, 1)
        lay.addWidget(self.table, 1)
        self.line = QLabel(self)  # the same verdict in the Light curve stage (stage_line)
        self.line.setWordWrap(True)
        self.line.hide()
        refill = page._fill_frames  # the Frames table is rebuilt now and then: its marks come back with it
        page._fill_frames = lambda: (refill(), self.mark_frames())

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
                 "ellipticity": translate("PhotometryChecks", "Ellipticity"),
                 "airmass": translate("PhotometryChecks", "Airmass")}  # fmt: skip
        for key, label in names.items():
            values = _series(lc, key)
            series[label] = np.asarray([np.nan if v is None else v for v in values], float) if values else None
        peak, sat = lc.get("peak") or [], lc.get("saturation")
        if sat and len(peak) == n:  # the target's brightest pixel as a share of the linearity limit
            series[translate("PhotometryChecks", "Target peak / limit")] = np.array(
                [np.nan if p[0] is None else p[0] / sat for p in peak], float)  # fmt: skip
        check = next((e for e in lc.get("extra") or [] if e.get("role") == "check"), None)
        if check and len(check.get("rel_flux") or []) == n:  # comparison ensemble against the check star (mag)
            c = np.asarray(check["rel_flux"], float)
            series[translate("PhotometryChecks", "Comparison − check (mag)")] = -2.5 * np.log10(c / np.nanmedian(c))
        shown = {k: v for k, v in series.items() if v is not None and len(v) == n and np.isfinite(v).any()}
        self.panels_box.setVisible(bool(shown))
        if not shown:
            return
        flagged = np.array(sorted({i for v in flags.values() for i in v if i < n}), int)
        frames, panels = np.arange(n), []
        for label, y in shown.items():
            series = [SeriesSpec(label, frames, y, size=3)]
            if len(flagged):  # the warning colour
                series.append(SeriesSpec(translate("PhotometryChecks", "Flagged"), flagged, y[flagged], size=6,
                                         colour=role("saturated"), z=1))  # fmt: skip
            panels.append(PanelSpec(AxisSpec(translate("PhotometryChecks", "Frame")), AxisSpec(label), series))
        self.panels.set_figure(FigureSpec(panels, shared_x=True))

    def _draw_rms(self, lc):
        """The binned RMS of a constant star's curve against the bin size, with the white-noise line, and β (Winn et
        al. 2008): the first check star, else T1 (an eclipse in it then raises the RMS too, as the title says)."""
        import numpy as np

        from ..exoplanets.noise import beta_factor
        from ..photometry.errors import rms_vs_bin

        check = next((e for e in lc.get("extra") or [] if e.get("role") == "check"), None)
        y = np.asarray((check or lc).get("rel_flux") or [], float)
        y = y[np.isfinite(y)]
        sizes = [n for n in (1, 2, 3, 5, 8, 12, 20, 30, 50, 80) if len(y) // n >= 3]
        show = len(sizes) >= 3 and bool(np.std(y) > 0)
        self.rms_box.setVisible(show)
        if not show:
            return None
        r = y / np.median(y) - 1
        rows = rms_vs_bin(r, sizes)
        beta = beta_factor(r, sizes[1:])
        n, got, white = (np.array(c, float) for c in zip(*rows, strict=True))
        who = (
            translate("PhotometryChecks", "check star")
            if check
            else translate("PhotometryChecks", "T1 (no check star)")
        )
        measured = translate("PhotometryChecks", "measured")
        series = [SeriesSpec(measured, n, 1000 * got, kind="line"), SeriesSpec(measured, n, 1000 * got, size=5),
                  SeriesSpec(translate("PhotometryChecks", "white noise"), n, 1000 * white, kind="line")]  # fmt: skip
        title = translate("PhotometryChecks", "RMS against bin size, {who}: β = {beta:.2f}").format(who=who, beta=beta)
        panel = PanelSpec(AxisSpec(translate("PhotometryChecks", "Points per bin"), scale="log"),
                          AxisSpec("RMS", "ppt", scale="log"), series)  # fmt: skip
        self.rms.set_figure(FigureSpec([panel], title=title))
        return beta

    def stage_line(self, panel):
        """Put the verdict in the Light curve stage's panel."""
        panel.add(self.line)

    def mark_frames(self):
        """The flagged frames in the Frames table: the reasons as tooltip, amber where the row is not already red or
        orange for a frame the measurement left out."""
        from PySide6.QtGui import QColor

        from .kit.tokens import role

        lc, names, table = getattr(self, "judged", None), kinds(), self.page.frame_table
        if lc is None:
            return
        files = list(lc.get("file") or [])
        why = {}
        for k, v in self.flags.items():
            for i in v:
                if i < len(files):
                    why.setdefault(Path(str(files[i])).name, []).append(names[k])
        for r, path in enumerate(self.page.images[: table.rowCount()]):
            reasons = why.get(Path(path).name)
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if reasons and item is not None:
                    if not item.toolTip():
                        item.setForeground(QColor(role("non_linear")))
                    item.setToolTip(", ".join(filter(None, [item.toolTip(), *reasons])))

    def mark(self, x, y, lc):
        """The flagged frames (cloud, spikes …) crossed on the light curve, once this tab has judged this very
        curve: [SeriesSpec] to draw with it."""
        import numpy as np

        from .kit.tokens import role

        if getattr(self, "judged", None) is not lc:
            return []
        idx = np.array(sorted({i for v in self.flags.values() for i in v if i < len(x)}), int)
        if not len(idx):
            return []
        name = translate("PhotometryChecks", "Flagged")
        return [
            SeriesSpec(
                name, np.asarray(x)[idx], np.asarray(y)[idx], symbol="x", colour=role("saturated"), size=8, ids=idx, z=1
            )
        ]

    def leave_out_flagged(self, kind=None):
        """Through the page's undoable exclusion, as its saturated-points command: every flagged frame, or only those
        of one kind ("cloud", "spike" …)."""
        page = self.page
        frames = sorted({i for k, v in self.flags.items() if kind in (None, k) for i in v})
        ids = {page._frame_ids[i] for i in frames if i < len(page._frame_ids)}
        if ids:
            page.edit(translate("PhotometryChecks", "leave out the flagged points"), page._exclude, page.excluded | ids)

    def show_checks(self, lc):
        from ..photometry.quality import lc_checks

        flags, _line = lc_checks(lc)
        self.flags, replot = flags, getattr(self, "judged", None) is not lc and any(flags.values())
        self.judged = lc
        self.leave_out.setEnabled(any(flags.values()))
        names = kinds()
        menu = self.leave_kind.menu()
        menu.clear()
        for k, v in flags.items():
            if v:
                label = translate("PhotometryChecks", "{kind} ({n})").format(kind=names[k], n=len(v))
                menu.addAction(label).triggered.connect(lambda _=False, k=k: self.leave_out_flagged(k))
        self.leave_kind.setEnabled(sum(bool(v) for v in flags.values()) > 1)  # one kind: the first button does it
        counts = [f"{len(v)} × {names[k]}" for k, v in flags.items() if v]
        self.verdict.setText(
            translate("PhotometryChecks", "Flagged frames: {list}").format(list=", ".join(counts))
            if counts
            else translate("PhotometryChecks", "No frame flagged: no cloud, seeing jump, field jump or saturation.")
        )
        self.line.setText(self.verdict.text())
        self.line.show()
        self.advice.setText(self._advice(lc))
        self._show_noise(lc)
        self._draw_panels(lc, flags)
        self.beta = self._draw_rms(lc)
        files = self.files = list(lc.get("file") or [""] * len(lc.get("rel_flux", [])))
        rows = sorted({i for v in flags.values() for i in v})
        self.table.set_data(
            [translate("PhotometryChecks", "Frame"), translate("PhotometryChecks", "File"),
             translate("PhotometryChecks", "Flags")],
            [[i + 1, Path(str(files[i])).name if i < len(files) else "",
              ", ".join(names[k] for k, v in flags.items() if i in v)] for i in rows],
            keys=rows,
        )  # fmt: skip
        self.page._fill_frames()  # rebuilt with the marks (mark_frames), so none pile up
        if replot and self.page.light_curve is lc and hasattr(self.page, "_plot_current"):
            self.page._plot_current()  # the light curve drawn before the checks: now with its flagged points
        return flags
