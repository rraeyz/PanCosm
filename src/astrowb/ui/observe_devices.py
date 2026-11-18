"""Observe page: the single device commands (cooler, preview, focuser, filter) and the devices line."""

import re
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)


def _wrapped(text, parent):
    """A form label that wraps instead of widening the page (long in some languages)."""
    label = QLabel(text, parent)
    label.setWordWrap(True)
    return label


translate = QCoreApplication.translate


class DeviceControls:
    """Mixed into ObservePage; its texts are translated in the ObservePage context."""

    def _device_fields(self):
        self.preview_exp = QDoubleSpinBox(self)
        self.preview_exp.setRange(0.001, 3600)
        self.preview_exp.setDecimals(3)
        self.preview_exp.setValue(2)
        self.preview_exp.setSuffix(" s")
        self.preview_exp.setToolTip(
            translate("ObservePage", "Exposure time of a single test frame (not saved with the sequence)")
        )
        self.cooler_temp = QDoubleSpinBox(self)
        self.cooler_temp.setRange(-60, 30)
        self.cooler_temp.setValue(-10)
        self.cooler_temp.setSuffix(" °C")
        self.cooler_temp.setToolTip(
            translate(
                "ObservePage",
                "Target temperature of the camera sensor; darks must be taken at the same temperature as the lights",
            )
        )
        self.focus_pos = QSpinBox(self)
        self.focus_pos.setRange(0, 1_000_000)
        self.focus_pos.setToolTip(translate("ObservePage", "Focuser position in steps"))
        self.filter_name = QComboBox(self)
        self.filter_name.setEditable(True)
        self.filter_name.setToolTip(translate("ObservePage", "Filter of the filter wheel by its name"))

    def _device_controls(self):
        """Single commands in three grids: cooler (and devices line), preview, focuser and filter."""
        self._device_fields()

        def button(text, slot, tip, key):
            b = self.buttons[key] = QPushButton(text, self)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        rows = (
            (
                translate("ObservePage", "Preview"),
                self.preview_exp,
                button(
                    translate("ObservePage", "Take preview"),
                    self.take_preview,
                    translate(
                        "ObservePage",
                        "One frame with this exposure, shown in the Images window (to check pointing and focus)",
                    ),
                    "preview",
                ),
                None,
            ),
            (
                translate("ObservePage", "Cooler"),
                self.cooler_temp,
                button(
                    translate("ObservePage", "Cool to"),
                    self._cool,
                    translate("ObservePage", "Switches the cooler on and sets this temperature"),
                    "cool",
                ),
                button(
                    translate("ObservePage", "Off"),
                    lambda: self._post("/cooler", {"on": False}),
                    translate("ObservePage", "Switches the cooler off (do it slowly at the end of the night)"),
                    "cooler_off",
                ),
            ),
            (
                translate("ObservePage", "Focuser"),
                self.focus_pos,
                button(
                    translate("ObservePage", "Move"),
                    lambda: self._post("/focuser", {"position": self.focus_pos.value()}),
                    translate("ObservePage", "Moves the focuser to this position"),
                    "focuser",
                ),
                None,
            ),
            (
                translate("ObservePage", "Filter"),
                self.filter_name,
                button(
                    translate("ObservePage", "Change"),
                    lambda: self._post("/filter", {"name": self.filter_name.currentText()}),
                    translate("ObservePage", "Turns the filter wheel to this filter"),
                    "filter",
                ),
                None,
            ),
        )
        return self._device_grids(rows)

    def _device_grids(self, rows):
        grids = cooler, preview, focus = QGridLayout(), QGridLayout(), QGridLayout()  # one per stage
        for (label, field, first, second), grid in zip(rows, (preview, cooler, focus, focus), strict=True):
            r = grid.rowCount() if grid.count() else 0  # an empty grid reports one row
            grid.addWidget(_wrapped(label, self), r, 0)
            grid.addWidget(field, r, 1)
            if second:  # both buttons in one cell: no fourth column to widen the page
                pair = QHBoxLayout()
                pair.setContentsMargins(0, 0, 0, 0)
                pair.addWidget(first)
                pair.addWidget(second)
                grid.addLayout(pair, r, 2)
            else:
                grid.addWidget(first, r, 2)
        self.devices = QLabel(self)
        self.devices.setProperty("muted", True)
        cooler.addWidget(self.devices, 1, 0, 1, 3)
        return grids

    def _cool(self):
        return self._post("/cooler", {"temperature": self.cooler_temp.value(), "on": True})

    def take_preview(self):
        spec = {"exptime": self.preview_exp.value(), "out_dir": self.out_dir.text().strip()}
        if self.filter_name.currentText().strip():
            spec["filter"] = self.filter_name.currentText().strip()
        return self._post("/preview", spec)

    def _show_devices(self, st):
        parts = []
        cam, foc, fw = st.get("camera", {}), st.get("focuser", {}), st.get("filterwheel", {})
        if "CCDTemperature" in cam:
            on = translate("ObservePage", "on") if cam.get("CoolerOn") else translate("ObservePage", "off")
            parts.append(
                translate("ObservePage", "Camera {t:.1f} °C, cooler {on}").format(t=cam["CCDTemperature"], on=on)
            )
        if "Position" in foc:
            parts.append(translate("ObservePage", "focuser at {p}").format(p=foc["Position"]))
        names = fw.get("Names") or []
        if names and [self.filter_name.itemText(i) for i in range(self.filter_name.count())] != names:
            self.filter_name.clear()
            self.filter_name.addItems(names)
        if names and 0 <= fw.get("Position", -1) < len(names):
            parts.append(translate("ObservePage", "filter {f}").format(f=names[fw["Position"]]))
        self.devices.setText(", ".join(parts))
        job = st["job"]
        if job["name"] == "sequence" and getattr(self, "_sequence_dir", None) and not job["running"]:
            if job["written"]:  # also after a weather stop: the frames taken so far are worth processing
                self._fetch(job["written"], self._sequence_dir, self.sequence_finished.emit)
            self._sequence_dir = None
        if job["name"] == "preview" and not job["running"] and job["written"]:
            path = job["written"][0]
            if path != self._shown_preview:
                self._shown_preview = path
                name = re.split(r"[\\/]", path)[-1]  # the observatory may run on Windows
                folder = path[: -len(name)].rstrip("\\/")
                self._fetch([path], folder, lambda local: self.preview_ready.emit(str(Path(local) / name)))
