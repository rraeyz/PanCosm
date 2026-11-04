"""Observatory set-up: site, devices (found on the network or typed), safety limits, guiding; saved as the
JSON file the observatory process reads."""

import json
import threading
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..devices import setup
from .messages import translate


def _spin(value, lo, hi, suffix="", decimals=1):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setValue(value)
    s.setSuffix(suffix)
    return s


class ObservatoryDialog(QDialog):
    found = Signal(object)  # discovery results, from a thread

    def __init__(self, settings, path=None, parent=None):
        super().__init__(parent)
        self.settings, self.path, self.start_now = settings, path, False
        self.setWindowTitle(self.tr("Observatory set-up"))
        self.resize(760, 600)  # a starting size; small screens may make it narrower
        lay = QVBoxLayout(self)
        site = settings.get("site", {"lat": 39.9, "lon": 32.8, "height": 900.0})
        form = QFormLayout()
        self.lat = _spin(site["lat"], -90, 90, " °", 5)
        self.lon = _spin(site["lon"], -180, 360, " °", 5)
        self.height = _spin(site.get("height", 0), -500, 9000, " m", 0)
        form.addRow(self.tr("Latitude (°, N+)"), self.lat)
        form.addRow(self.tr("Longitude (°, E+)"), self.lon)
        form.addRow(self.tr("Height (m)"), self.height)
        self.height.setToolTip(self.tr("Height above sea level in metres"))
        self.lon.setToolTip(
            self.tr("Longitude of the telescope in degrees, east positive (west of Greenwich is negative)")
        )
        self.lat.setToolTip(self.tr("Latitude of the telescope in degrees, north positive"))
        lay.addLayout(form)

        lay.addWidget(QLabel(self.tr("Devices"), self))
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            [self.tr("Device"), self.tr("Protocol"), self.tr("Address (host:port)"), self.tr("Number or INDI name")]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table)
        row = QHBoxLayout()
        self.find_button = QPushButton(self.tr("Find Alpaca devices on the network"), self)
        self.find_button.clicked.connect(self.find)
        self.find_button.setToolTip(
            self.tr("Asks the local network which ASCOM Alpaca devices are there and adds them to the list")
        )
        add = QPushButton(self.tr("Add device"), self)
        add.clicked.connect(lambda: self.add_device())
        add.setToolTip(
            self.tr("A row for a device by hand: kind, protocol (Alpaca or INDI), address and number or name")
        )
        remove = QPushButton(self.tr("Remove device"), self)
        remove.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        remove.setToolTip(self.tr("Removes the selected device"))
        for b in (self.find_button, add, remove):
            row.addWidget(b)
        lay.addLayout(row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        form = QFormLayout()
        self.min_alt = _spin(setup.RULE_DEFAULTS["min_alt"], 0, 60, " °")
        self.sun_max_alt = _spin(setup.RULE_DEFAULTS["sun_max_alt"], -18, 0, " °")
        self.max_humidity = _spin(setup.RULE_DEFAULTS["max_humidity"], 10, 100, " %")
        self.max_wind = _spin(setup.RULE_DEFAULTS["max_wind"], 1, 50, " m/s")
        form.addRow(self.tr("Lowest altitude"), self.min_alt)
        form.addRow(self.tr("The night ends when the Sun is above"), self.sun_max_alt)
        form.addRow(self.tr("Highest humidity"), self.max_humidity)
        form.addRow(self.tr("Highest wind speed"), self.max_wind)
        self.max_wind.setToolTip(self.tr("Above this wind speed (from the weather station) the observatory closes"))
        self.max_humidity.setToolTip(
            self.tr(
                "Above this humidity (from the weather station) the observatory closes, before dew forms on the optics"
            )
        )
        self.sun_max_alt.setToolTip(
            self.tr(
                "Observing stops and the telescope parks when the Sun rises above this altitude (−6°: civil"
                " twilight, −12°: nautical)"
            )
        )
        self.min_alt.setToolTip(self.tr("The mount never points lower than this"))
        self.phd2 = QLineEdit(self)
        self.phd2.setPlaceholderText(self.tr("empty: no guiding; or host:port, e.g. 127.0.0.1:4400"))
        form.addRow(self.tr("PHD2 guiding"), self.phd2)
        self.phd2.setToolTip(self.tr("Address of a running PHD2 for guiding and dithering during sequences"))
        self.focus_offsets = QLineEdit(self)
        self.focus_offsets.setPlaceholderText(self.tr("e.g. L=0, B=-30, V=15 (focuser steps)"))
        self.focus_offsets.setToolTip(self.tr("The focuser moves by the difference when the filter changes"))
        form.addRow(self.tr("Filter focus offsets"), self.focus_offsets)
        self.temp_coeff = _spin(0.0, -1000, 1000, self.tr(" steps/°C"))
        self.temp_coeff.setToolTip(
            self.tr("Focuser steps per degree; during a sequence the focus follows the focuser's temperature (0: off)")
        )
        form.addRow(self.tr("Temperature compensation"), self.temp_coeff)
        self.remote = QCheckBox(self.tr("Other computers may connect (protected by the token)"), self)
        form.addRow("", self.remote)
        self.remote.setToolTip(
            self.tr("Off: only this computer can control the telescope. On: others on the network can, with the token.")
        )
        self.tls = QCheckBox(self.tr("Encrypt the connection (HTTPS; recommended when others may connect)"), self)
        self.remote.toggled.connect(lambda on: self.tls.setChecked(on or self.tls.isChecked()))
        form.addRow("", self.tls)
        self.tls.setToolTip(
            self.tr("The connection is encrypted, so the token and commands cannot be read on the network")
        )
        lay.addLayout(form)

        row = QHBoxLayout()
        self.open_button = QPushButton(self.tr("Open…"), self)
        self.open_button.clicked.connect(self._open_dialog)
        self.open_button.setToolTip(self.tr("Loads a saved observatory configuration"))
        save = QPushButton(self.tr("Save…"), self)
        save.clicked.connect(lambda: self._save_dialog(start=False))
        save.setToolTip(self.tr("Saves this configuration to a file"))
        start = QPushButton(self.tr("Save and start"), self)
        start.setProperty("primary", True)
        start.clicked.connect(lambda: self._save_dialog(start=True))
        start.setToolTip(self.tr("Saves the configuration and starts the observatory program on this computer"))
        row.addWidget(self.open_button)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(start)
        lay.addLayout(row)
        self.found.connect(self._show_found)
        if path and Path(path).exists():
            self.load(path)

    # --- devices --------------------------------------------------------------
    def add_device(self, kind="mount", protocol="alpaca", address="127.0.0.1:11111", target="0"):
        r = self.table.rowCount()
        self.table.insertRow(r)
        k, p = QComboBox(self.table), QComboBox(self.table)
        k.addItems(setup.KINDS)
        k.setCurrentText(kind)
        p.addItem("ASCOM Alpaca", "alpaca")
        p.addItem("INDI", "indi")
        p.setCurrentIndex(0 if protocol == "alpaca" else 1)
        k.setToolTip(
            self.tr(
                "What the device is: mount, camera, focuser, filter wheel, dome, safety monitor, weather station, "
                "rotator, flat panel"
            )
        )
        p.setToolTip(self.tr("ASCOM Alpaca (Windows drivers, network devices) or INDI (Linux, Raspberry Pi)"))
        self.table.setCellWidget(r, 0, k)
        self.table.setCellWidget(r, 1, p)
        self.table.setItem(r, 2, QTableWidgetItem(address))
        self.table.setItem(r, 3, QTableWidgetItem(str(target)))

    def devices(self):
        out = []
        for r in range(self.table.rowCount()):
            protocol, target = self.table.cellWidget(r, 1).currentData(), self.table.item(r, 3).text().strip()
            d = {"kind": self.table.cellWidget(r, 0).currentText(), "protocol": protocol}
            d["address"] = self.table.item(r, 2).text().strip()
            d |= {"number": int(target or 0)} if protocol == "alpaca" else {"name": target}
            out.append(d)
        return out

    def find(self, discover=setup.discover):
        self.find_button.setEnabled(False)
        self.status.setText(self.tr("Searching the network…"))
        threading.Thread(target=lambda: self.found.emit(self._safe(discover)), daemon=True).start()

    @staticmethod
    def _safe(discover):
        try:
            return discover()
        except Exception as e:  # no network, firewall: say so, keep the dialog usable
            return str(e)

    def _show_found(self, found):
        self.find_button.setEnabled(True)
        if isinstance(found, str):
            self.status.setText(self.tr("Search failed: {e}").format(e=found))
            return
        have = {(d["address"], d.get("number")) for d in self.devices() if d["protocol"] == "alpaca"}
        new = [d for d in found if (d["address"], d["number"]) not in have]
        for d in new:
            self.add_device(d["kind"], "alpaca", d["address"], d["number"])
        self.status.setText(
            self.tr("{n} devices found, {m} added. Check the list: one device of each kind.").format(
                n=len(found), m=len(new)
            )
        )

    # --- file -----------------------------------------------------------------
    def config(self):
        site = {"lat": self.lat.value(), "lon": self.lon.value(), "height": self.height.value()}
        rules = {
            "min_alt": self.min_alt.value(),
            "sun_max_alt": self.sun_max_alt.value(),
            "max_humidity": self.max_humidity.value(),
            "max_wind": self.max_wind.value(),
        }
        focus = {"offsets": self.offsets(), "temp_coeff": self.temp_coeff.value(), "temp_step": 0.5}
        cfg = setup.make_config(
            site, self.devices(), rules, self.phd2.text().strip() or None, self.remote.isChecked(), focus=focus
        )
        return cfg | ({"tls": True} if self.tls.isChecked() else {})

    def offsets(self):
        """{filter: steps} from "L=0, B=-30"."""
        out = {}
        for part in self.focus_offsets.text().replace(";", ",").split(","):
            name, sep, value = part.partition("=")
            if not part.strip():
                continue
            if not sep or not name.strip() or not value.strip().lstrip("+-").isdigit():
                raise ValueError(self.tr("Filter focus offsets: write name=steps, e.g. B=-30"))
            out[name.strip()] = int(value)
        return out

    def load(self, path):
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
        site = cfg.get("site", {})
        self.lat.setValue(site.get("lat", 0))
        self.lon.setValue(site.get("lon", 0))
        self.height.setValue(site.get("height", 0))
        self.table.setRowCount(0)
        for kind, spec in cfg.get("devices", {}).items():
            if "alpaca" in spec:
                self.add_device(kind, "alpaca", spec["alpaca"], spec.get("number", 0))
            else:
                self.add_device(kind, "indi", spec.get("indi", ""), spec.get("device", ""))
        for key, spin in (
            ("min_alt", self.min_alt),
            ("sun_max_alt", self.sun_max_alt),
            ("max_humidity", self.max_humidity),
            ("max_wind", self.max_wind),
        ):
            if cfg.get("rules", {}).get(key) is not None:
                spin.setValue(cfg["rules"][key])
        phd2 = cfg.get("phd2")
        self.phd2.setText(f"{phd2.get('host', '127.0.0.1')}:{phd2.get('port', 4400)}" if phd2 else "")
        focus = cfg.get("focus", {})
        self.focus_offsets.setText(", ".join(f"{k}={v}" for k, v in focus.get("offsets", {}).items()))
        self.temp_coeff.setValue(float(focus.get("temp_coeff", 0.0)))
        self.remote.setChecked(cfg.get("listen", "").startswith("0.0.0.0"))
        self.tls.setChecked(bool(cfg.get("tls")))
        self.path = str(path)

    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Observatory configuration"), "", "JSON (*.json)")
        if path:
            self.load(path)

    def save(self, path, start=False):
        """Write the file; problems are shown but do not block (the owner decides). Returns the path."""
        try:
            cfg = self.config()
        except ValueError as e:
            self.status.setText(translate(str(e)))
            return None
        issues = setup.problems(cfg)
        self.path = str(setup.save(cfg, path))
        self.settings.set("observatory.config", self.path)
        self.start_now = start
        text = self.tr("Saved: {p}").format(p=self.path)
        self.status.setText(text + "".join("\n" + translate(i) for i in issues))
        return self.path

    def _save_dialog(self, start):
        path = (
            self.path
            or QFileDialog.getSaveFileName(
                self, self.tr("Observatory configuration"), "observatory.json", "JSON (*.json)"
            )[0]
        )
        if path and self.save(path, start):
            self.accept()
