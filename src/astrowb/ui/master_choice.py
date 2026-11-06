"""The calibration masters chosen by hand (the owner, 2026-11-13): for the lights of each filter, which bias, dark
and flat group is used — "automatic" (the program's match), one of the night's groups, or none. The choice goes to
calibration.run as its `use` parameter (calibration/matching.apply_choices)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QPushButton

from .kit.dialogs import Dialog

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("MasterChoice", "…") calls
KINDS = ("bias", "dark", "flat")


def groups(frames):
    """{kind: [(a file of the group, description)]} from the scanned frames (dicts, calibration.scan's)."""
    from ..calibration.frames import Frame
    from ..calibration.matching import group_key

    found = {}
    for d in frames:
        if d["kind"] not in KINDS:
            continue
        f = Frame(**d | {"binning": tuple(d["binning"]), "shape": tuple(d["shape"])})
        found.setdefault(f.kind, {}).setdefault(group_key(f), []).append(f)
    out = {}
    for kind, by_key in found.items():
        rows = []
        for members in by_key.values():
            f = members[0]
            bits = [f.filter or ""] if kind == "flat" else []
            bits += [f"{f.exptime:g} s"] if kind == "dark" and f.exptime is not None else []
            bits += [f"{f.temperature:.0f} °C"] if f.temperature is not None else []
            bits += [f"{f.binning[0]}×{f.binning[1]}", translate("MasterChoice", "{n} frames").format(n=len(members))]
            rows.append((f.path, " · ".join(b for b in bits if b)))
        out[kind] = rows
    return out


def light_filters(frames):
    return sorted({d.get("filter") or "" for d in frames if d["kind"] == "light"})


class MasterChoice(Dialog):
    def __init__(self, frames, chosen=None, parent=None):
        super().__init__(translate("MasterChoice", "Masters for the lights"), parent, None, "master_choice")
        chosen = chosen or {}
        found = groups(frames)
        grid = QGridLayout()
        names = {"bias": translate("MasterChoice", "Bias"), "dark": translate("MasterChoice", "Dark"),
                 "flat": translate("MasterChoice", "Flat")}  # fmt: skip
        for c, kind in enumerate(KINDS, 1):
            grid.addWidget(QLabel(names[kind], self), 0, c)
        self.boxes = {}
        for r, filt in enumerate(light_filters(frames), 1):
            grid.addWidget(QLabel(filt or translate("MasterChoice", "no filter"), self), r, 0)
            for c, kind in enumerate(KINDS, 1):
                box = QComboBox(self)
                box.addItem(translate("MasterChoice", "automatic"), "auto")
                for path, text in found.get(kind, []):
                    box.addItem(text, path)
                box.addItem(translate("MasterChoice", "none"), "none")
                box.setCurrentIndex(max(0, box.findData((chosen.get(filt) or {}).get(kind, "auto"))))
                self.boxes[(filt, kind)] = box
                grid.addWidget(box, r, c)
        self.body.addWidget(
            QLabel(
                translate(
                    "MasterChoice",
                    "Which bias, dark and flat each filter's lights get; automatic: the "
                    "program's match by size, binning, exposure, temperature and filter.",
                ),
                self,
            )  # fmt: skip
        )
        self.body.addLayout(grid)
        self.add_buttons(translate("MasterChoice", "Use these"), translate("MasterChoice", "Cancel"))

    def choice(self):
        """{filter: {kind: file or "none"}}, without the automatic ones."""
        out = {}
        for (filt, kind), box in self.boxes.items():
            if box.currentData() != "auto":
                out.setdefault(filt, {})[kind] = box.currentData()
        return out


def add_button(page, layout):
    """'Choose the masters by hand…' beside Calibrate; the choice is kept on the page (page.master_choices)."""
    page.master_choices = {}
    page.masters_button = QPushButton(translate("MasterChoice", "Choose the masters by hand…"), page)
    page.masters_button.setToolTip(
        translate("MasterChoice", "For each filter's lights: which bias, dark and flat, or none (after Scan)")
    )

    def choose():
        if not page.frames:
            page.result.setText(translate("MasterChoice", "Scan the folder first."))
            return
        dlg = MasterChoice(page.frames, page.master_choices, page)
        if dlg.exec():
            page.master_choices = dlg.choice()

    page.masters_button.clicked.connect(choose)
    layout.addWidget(page.masters_button)
    layout.addWidget(page.run_button)
