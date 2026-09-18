"""Observe: connect to the observatory process, watch safety, slew/park/abort, run sequences.

The observatory process owns the devices and the safety supervisor; this page only sends
commands, so closing the window never leaves the telescope unattended."""

import json
import re
import secrets
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..devices.client import Client
from .messages import translate
from .undo import Undoable, track_typing
from .workspaces import _title

KINDS = ("light", "dark", "bias", "flat")


def _wrapped(text, parent):
    """A form label that wraps instead of widening the page (long in some languages)."""
    label = QLabel(text, parent)
    label.setWordWrap(True)
    return label


def launch_observatory(config_path: Path):
    """Start the observatory process detached from this window (it survives the UI closing)."""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    changed = not cfg.get("token")
    cfg["token"] = cfg.get("token") or secrets.token_urlsafe(24)
    if cfg.get("tls"):  # the certificate is made here, so its fingerprint is known before the process starts
        from ..devices.tls import ensure_certificate

        fp = ensure_certificate(config_path.parent)[2]
        changed |= cfg.get("tls_fingerprint") != fp
        cfg["tls_fingerprint"] = fp
    if changed:
        config_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    cmd = [sys.executable] + ([] if getattr(sys, "frozen", False) else ["-m", "astrowb"])
    cmd += ["--observatory", str(config_path)]
    kwargs = (
        {"start_new_session": True}
        if sys.platform != "win32"
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS}
    )
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    scheme = "https://" if cfg.get("tls") else "http://"
    return scheme + cfg.get("listen", "127.0.0.1:11112").replace("0.0.0.0", "127.0.0.1"), cfg["token"], proc


class ObservePage(Undoable, QWidget):
    status_arrived = Signal(object)  # from the polling thread
    preview_ready = Signal(str)  # a preview frame that this computer can open (local observatory)
    sequence_finished = Signal(str)  # out_dir of a sequence that ended with frames written
    frames_copied = Signal(str, object)  # from the copy thread: local folder, callback
    copy_failed = Signal(str)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.settings = settings
        self.client = None
        self.status = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Observe"), self))
        conn = self.settings.get("observatory", {"url": "http://127.0.0.1:11112", "token": ""})
        grid = QGridLayout()
        self.url, self.token = QLineEdit(conn["url"], self), QLineEdit(conn["token"], self)
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setToolTip(
            self.tr(
                "The password shown when the observatory program starts; without it nobody else can move the telescope"
            )
        )
        self.url.setToolTip(
            self.tr(
                "Address of the observatory program: on this computer http://127.0.0.1:11112, otherwise the"
                " observatory computer's address"
            )
        )
        grid.addWidget(QLabel(self.tr("Observatory address"), self), 0, 0)
        grid.addWidget(self.url, 0, 1)
        grid.addWidget(QLabel(self.tr("Token"), self), 1, 0)
        grid.addWidget(self.token, 1, 1)
        self.fingerprint = QLineEdit(conn.get("fingerprint", ""), self)
        self.fingerprint.setPlaceholderText(self.tr("only for https: shown when the observatory starts"))
        grid.addWidget(QLabel(self.tr("Certificate fingerprint"), self), 2, 0)
        grid.addWidget(self.fingerprint, 2, 1)
        self.fingerprint.setToolTip(
            self.tr(
                "Checks that the https connection really goes to your observatory; copy it from the "
                "observatory computer"
            )
        )
        lay.addLayout(grid)
        row = QGridLayout()  # two rows: fits narrow windows in every language
        self.buttons = {}  # the page's commands by name, for the window's menus and toolbar (interface I6c.9)
        self.buttons["connect"] = connect = QPushButton(self.tr("Connect"), self)
        connect.clicked.connect(self.connect_to)
        connect.setToolTip(
            self.tr("Connects to the observatory program at this address and shows its status every two seconds")
        )
        self.buttons["start_local"] = start = QPushButton(self.tr("Start observatory on this computer…"), self)
        start.clicked.connect(self._start_local)
        start.setToolTip(
            self.tr(
                "Starts the observatory program here with a saved configuration file (devices connected to "
                "this computer)"
            )
        )
        self.buttons["set_up"] = wizard = QPushButton(self.tr("Set up observatory…"), self)
        wizard.clicked.connect(self.set_up)
        wizard.setToolTip(self.tr("Site, devices (ASCOM Alpaca or INDI) and safety limits, step by step"))
        row.addWidget(connect, 0, 0)
        row.addWidget(wizard, 0, 1)
        row.addWidget(start, 1, 0, 1, 2)
        lay.addLayout(row)
        self.safety = QLabel(self.tr("Not connected"), self)
        self.safety.setWordWrap(True)
        self.safety.setStyleSheet("font-weight: bold; padding: 6px;")
        lay.addWidget(self.safety)
        self.mount = QLabel(self)
        lay.addWidget(self.mount)
        row = QHBoxLayout()
        self.target = QLineEdit(self)
        self.target.setPlaceholderText(self.tr("RA Dec, e.g. 02:04:10 +46:41:16"))
        self.target.setToolTip(self.tr("Where to point the telescope (J2000)"))
        self.buttons["slew"] = slew = QPushButton(self.tr("Slew"), self)
        slew.clicked.connect(self._slew)
        slew.setToolTip(
            self.tr("Moves the telescope to these coordinates; refused below the altitude limit or while unsafe")
        )
        self.buttons["centre"] = centre = QPushButton(self.tr("Centre"), self)
        centre.setToolTip(
            self.tr("Slew, take a frame, plate-solve it, correct the mount and repeat until the target is centred")
        )
        centre.clicked.connect(self.centre)
        self.buttons["polar"] = polar = QPushButton(self.tr("Polar alignment"), self)
        polar.setToolTip(
            self.tr(
                "Point near the pole (declination 60-80°), then press: three solved frames while the RA axis turns "
                "give the error of the polar axis"
            )
        )
        polar.clicked.connect(lambda: self._post("/polar", {"exptime": 5.0, "out_dir": self.out_dir.text().strip()}))
        lay.addWidget(self.target)  # the coordinates on a line of their own, the buttons below: fits narrow windows
        row.addWidget(slew)
        row.addWidget(centre)
        row.addWidget(polar)
        lay.addLayout(row)
        row = QGridLayout()
        for i, (text, path, tip) in enumerate(
            (
                (self.tr("Park"), "/park", self.tr("Stops any slew and sends the mount to its park position")),
                (
                    self.tr("Abort"),
                    "/abort",
                    self.tr("Stops the running sequence, exposure or slew at once; the mount is not parked"),
                ),
                (
                    self.tr("Resume"),
                    "/resume",
                    self.tr("After a safety stop: allows sequences again, refused while anything is still unsafe"),
                ),
                (
                    self.tr("Autofocus"),
                    "/autofocus",
                    self.tr(
                        "Frames at nine focuser positions around the present one; the star size (HFR) against "
                        "position is fitted and the focuser moved to the best"
                    ),
                ),
            )
        ):
            b = QPushButton(text, self)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, p=path: self._post(p))
            row.addWidget(b, i // 2, i % 2)
            self.buttons[path.strip("/")] = b
        lay.addLayout(row)
        lay.addLayout(self._device_controls())
        lay.addWidget(QLabel(self.tr("Log"), self))
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        split.addWidget(left)

        right = QWidget(self)
        rl = QVBoxLayout(right)
        rl.addWidget(_title(self.tr("Sequence"), self))
        grid = QGridLayout()
        self.seq_name, self.seq_coord = QLineEdit(self), QLineEdit(self)
        self.seq_coord.setPlaceholderText(self.tr("empty for darks/bias (no slew)"))
        self.dither = QSpinBox(self)
        self.dither.setRange(0, 1000)
        self.dither.setToolTip(
            self.tr(
                "Moves the telescope a few pixels through the guider (PHD2) every N frames, so hot pixels "
                "and noise patterns do not stay on the stars; 0: never"
            )
        )
        self.out_dir = QLineEdit(str(Path.home() / "observations"), self)
        self.seq_start, self.seq_end = QLineEdit(self), QLineEdit(self)
        self.seq_start.setPlaceholderText(self.tr("now; or dusk, or a UTC time 2026-11-15T21:30"))
        self.seq_end.setPlaceholderText(self.tr("after the counts; or dawn, or a UTC time (repeats until then)"))
        self.rotation = QLineEdit(self)
        self.rotation.setPlaceholderText(self.tr("empty: leave the rotator where it is"))
        self.rotation.setToolTip(self.tr("Sky position angle for the camera rotator in degrees, if there is one"))
        self.seq_end.setToolTip(
            self.tr(
                "When the sequence ends: after the counts of the rows, or it repeats the rows until dawn or a UTC time"
            )
        )
        self.seq_start.setToolTip(
            self.tr("When the sequence begins: now, at dusk (the Sun below the observatory's limit) or at a UTC time")
        )
        self.seq_coord.setToolTip(
            self.tr("Coordinates of the target (J2000); the telescope slews there before the first frame")
        )
        self.seq_name.setToolTip(self.tr("Written into the frames' OBJECT keyword and their file names"))
        self.out_dir.setToolTip(
            self.tr("Folder on the observatory computer where the frames are written; they are copied here afterwards")
        )
        for r, (label, w) in enumerate(
            (
                (self.tr("Target name"), self.seq_name),
                (self.tr("RA Dec"), self.seq_coord),
                (self.tr("Dither every N frames (PHD2)"), self.dither),
                (self.tr("Start"), self.seq_start),
                (self.tr("End"), self.seq_end),
                (self.tr("Rotator angle (°)"), self.rotation),
                (self.tr("Save to (folder on the observatory computer)"), self.out_dir),
            )
        ):
            grid.addWidget(_wrapped(label, self), r, 0)
            grid.addWidget(w, r, 1)
        rl.addLayout(grid)
        self.plan_box = QWidget(self)
        pl = QVBoxLayout(self.plan_box)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(
            _wrapped(self.tr("Night plan (from the Planning window): every target gets the exposure rows below"), self)
        )
        self.plan_list = QListWidget(self)
        self.plan_list.setMaximumHeight(110)
        pl.addWidget(self.plan_list)
        self.buttons["clear_plan"] = clear = QPushButton(self.tr("Clear the night plan"), self)
        clear.clicked.connect(lambda: self.load_schedule([]))
        clear.setToolTip(self.tr("Forgets the night plan sent from the Planning window; the exposure rows stay"))
        pl.addWidget(clear)
        self.plan_box.hide()
        self.plan = []
        rl.addWidget(self.plan_box)
        self.exposures = QTableWidget(0, 9, self)
        self.exposures.setHorizontalHeaderLabels(
            [
                self.tr("Type"),
                self.tr("Filter"),
                self.tr("Exposure (s)"),
                self.tr("Count"),
                self.tr("Binning"),
                self.tr("Gain"),
                self.tr("Offset"),
                self.tr("Read-out mode"),
                self.tr("Sub-frame x, y, w, h"),
            ]
        )
        self.exposures.setToolTip(
            self.tr(
                "Gain, offset, read-out mode (number in the camera's list) and sub-frame (binned pixels): "
                "empty keeps the camera's setting and the full frame"
            )
        )
        # each column at least as wide as its header (Stretch cut them, I6b (4)); the table scrolls sideways if narrow
        self.exposures.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        rl.addWidget(self.exposures, 1)
        row = QHBoxLayout()
        self.buttons["add_row"] = add = QPushButton(self.tr("Add exposure row"), self)
        add.clicked.connect(lambda: self.edit(self.tr("add an exposure row"), self.add_exposure_row))
        add.setToolTip(
            self.tr("A new row: type, filter, exposure time, count, binning (gain, offset and the rest may stay empty)")
        )
        self.buttons["remove_row"] = remove = QPushButton(self.tr("Remove row"), self)
        remove.clicked.connect(
            lambda: self.edit(self.tr("remove an exposure row"), self.exposures.removeRow, self.exposures.currentRow())
        )
        remove.setToolTip(self.tr("Removes the selected exposure row"))
        self.buttons["start"] = self.start_button = QPushButton(self.tr("Start sequence"), self)
        self.start_button.clicked.connect(self._start_sequence)
        self.start_button.setToolTip(
            self.tr("Sends the sequence to the observatory, which runs it on its own; Abort stops it")
        )
        self.buttons["sky_flats"] = flats = QPushButton(self.tr("Sky flats"), self)
        flats.setToolTip(
            self.tr(
                "Twilight flats with the filter and count of the selected row; exposure times follow the "
                "sky brightness. Point the telescope at the flat spot first, tracking off."
            )
        )
        flats.clicked.connect(self._sky_flats)
        self.buttons["panel_flats"] = panel = QPushButton(self.tr("Panel flats"), self)
        panel.setToolTip(
            self.tr(
                "Flats on the flat panel (cover closed, panel lit, exposure adjusted to the target level), "
                "with the filter and count of the selected row; the panel is switched off afterwards"
            )
        )
        panel.clicked.connect(self.panel_flats)
        row = QGridLayout()  # two rows: fits narrow windows in every language
        for i, b in enumerate((add, remove, self.start_button, flats, panel)):
            row.addWidget(b, i // 2, i % 2)
        rl.addLayout(row)
        self.job = QLabel(self)
        self.job.setWordWrap(True)
        rl.addWidget(self.job)
        split.addWidget(right)
        split.setSizes([500, 700])
        QVBoxLayout(self).addWidget(split)
        self.add_exposure_row()
        track_typing(self, self.exposures, self.tr("type a value"))

        self.status_arrived.connect(self._show_status)
        self.frames_copied.connect(lambda folder, done: done(folder))
        self.copy_failed.connect(
            lambda e: self.job.setText(self.tr("Copying the frames failed: {e}").format(e=translate(e)))
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(2000)

    def _device_controls(self):
        """Preview frame, cooler, focuser and filter: the observatory API's single commands."""
        grid = QGridLayout()
        self.preview_exp = QDoubleSpinBox(self)
        self.preview_exp.setRange(0.001, 3600)
        self.preview_exp.setDecimals(3)
        self.preview_exp.setValue(2)
        self.preview_exp.setSuffix(" s")
        self.preview_exp.setToolTip(self.tr("Exposure time of a single test frame (not saved with the sequence)"))
        self.cooler_temp = QDoubleSpinBox(self)
        self.cooler_temp.setRange(-60, 30)
        self.cooler_temp.setValue(-10)
        self.cooler_temp.setSuffix(" °C")
        self.cooler_temp.setToolTip(
            self.tr(
                "Target temperature of the camera sensor; darks must be taken at the same temperature as the lights"
            )
        )
        self.focus_pos = QSpinBox(self)
        self.focus_pos.setRange(0, 1_000_000)
        self.focus_pos.setToolTip(self.tr("Focuser position in steps"))
        self.filter_name = QComboBox(self)
        self.filter_name.setEditable(True)
        self.filter_name.setToolTip(self.tr("Filter of the filter wheel by its name"))
        self._shown_preview = None

        def button(text, slot, tip, key):
            b = self.buttons[key] = QPushButton(text, self)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        rows = (
            (
                self.tr("Preview"),
                self.preview_exp,
                button(
                    self.tr("Take preview"),
                    self.take_preview,
                    self.tr("One frame with this exposure, shown in the Images window (to check pointing and focus)"),
                    "preview",
                ),
                None,
            ),
            (
                self.tr("Cooler"),
                self.cooler_temp,
                button(
                    self.tr("Cool to"), self._cool, self.tr("Switches the cooler on and sets this temperature"), "cool"
                ),
                button(
                    self.tr("Off"),
                    lambda: self._post("/cooler", {"on": False}),
                    self.tr("Switches the cooler off (do it slowly at the end of the night)"),
                    "cooler_off",
                ),
            ),
            (
                self.tr("Focuser"),
                self.focus_pos,
                button(
                    self.tr("Move"),
                    lambda: self._post("/focuser", {"position": self.focus_pos.value()}),
                    self.tr("Moves the focuser to this position"),
                    "focuser",
                ),
                None,
            ),
            (
                self.tr("Filter"),
                self.filter_name,
                button(
                    self.tr("Change"),
                    lambda: self._post("/filter", {"name": self.filter_name.currentText()}),
                    self.tr("Turns the filter wheel to this filter"),
                    "filter",
                ),
                None,
            ),
        )
        for r, (label, field, first, second) in enumerate(rows):
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
        grid.addWidget(self.devices, len(rows), 0, 1, 3)
        return grid

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
            on = self.tr("on") if cam.get("CoolerOn") else self.tr("off")
            parts.append(self.tr("Camera {t:.1f} °C, cooler {on}").format(t=cam["CCDTemperature"], on=on))
        if "Position" in foc:
            parts.append(self.tr("focuser at {p}").format(p=foc["Position"]))
        names = fw.get("Names") or []
        if names and [self.filter_name.itemText(i) for i in range(self.filter_name.count())] != names:
            self.filter_name.clear()
            self.filter_name.addItems(names)
        if names and 0 <= fw.get("Position", -1) < len(names):
            parts.append(self.tr("filter {f}").format(f=names[fw["Position"]]))
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

    def download_dir(self, remote_folder):
        """Where frames of a remote observatory are copied: <download folder>/<last part of its folder>."""
        root = Path(self.settings.get("observatory.download_dir", str(Path.home() / "observations")))
        return root / (re.split(r"[\\/]", remote_folder.rstrip("\\/"))[-1] or "frames")

    @staticmethod
    def is_local(paths):
        return all(Path(p).is_file() for p in paths)  # observatory on this computer (or a shared disk)

    def _fetch(self, paths, folder, done):
        """done(local folder) once the frames are on this computer; copied first from a remote observatory."""
        if self.is_local(paths):
            return done(folder)
        local, client = self.download_dir(folder), self.client
        self.job.setText(self.tr("Copying {n} frames to {f}…").format(n=len(paths), f=local))

        def work():
            try:
                for p in paths:
                    client.download(p, local)
            except Exception as e:  # network down: the frames stay on the observatory computer
                self.copy_failed.emit(str(e))
                return
            self.frames_copied.emit(str(local), done)

        threading.Thread(target=work, daemon=True).start()

    # --- connection ---------------------------------------------------------
    def connect_to(self):
        url, token, fp = (w.text().strip() for w in (self.url, self.token, self.fingerprint))
        self.client = Client(url, token, timeout=5, fingerprint=fp)
        self.settings.set("observatory", {"url": url, "token": token, "fingerprint": fp})
        self._poll()

    def set_up(self, dialog_class=None):
        """The set-up dialog (site, devices, limits); 'Save and start' starts the observatory here."""
        from .observatory_dialog import ObservatoryDialog

        dlg = (dialog_class or ObservatoryDialog)(self.settings, self.settings.get("observatory.config"), self)
        if dlg.exec() and dlg.start_now:
            self.start_with(dlg.path)
        return dlg

    def _start_local(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Observatory configuration"), "", "JSON (*.json)")
        if path:
            self.start_with(path)

    def start_with(self, path):
        if path:
            try:
                url, token, _ = launch_observatory(Path(path))
            except (OSError, ValueError) as e:  # not a configuration file (wrong file, damaged JSON)
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, self.tr("Observatory configuration"), f"{path}\n\n{translate(e)}")
                return None
            self.url.setText(url)
            self.token.setText(token)
            self.fingerprint.setText(json.loads(Path(path).read_text(encoding="utf-8")).get("tls_fingerprint", ""))
            QTimer.singleShot(3000, self.connect_to)

    def _poll(self):
        if self.client is None:
            return

        def work(client=self.client):
            try:
                st = client.status()
            except Exception as e:  # network or server down
                st = {"error": str(e)}
            try:
                self.status_arrived.emit(st)
            except RuntimeError:  # the page was closed while the request was running
                pass

        threading.Thread(target=work, daemon=True).start()

    def _show_status(self, st):
        self.status = st
        if "error" in st:
            self.safety.setText(self.tr("No connection to the observatory: {e}").format(e=translate(st["error"])))
            self.safety.setStyleSheet("font-weight: bold; padding: 6px; background: #c62828; color: white;")
            return
        if st["safe"] and not st["aborted"]:
            self.safety.setText(self.tr("Safe"))
            self.safety.setStyleSheet("font-weight: bold; padding: 6px; background: #2e7d32; color: white;")
        else:
            reasons = "; ".join(translate(r) for r in st["reasons"]) or self.tr("aborted — press Resume when ready")
            self.safety.setText(self.tr("NOT SAFE: {r}").format(r=reasons))
            self.safety.setStyleSheet("font-weight: bold; padding: 6px; background: #c62828; color: white;")
        m = st.get("mount")
        if m and "error" not in m:
            self.mount.setText(
                self.tr("Mount: alt {alt:.1f}°, az {az:.1f}°, {state}").format(
                    alt=m["alt"],
                    az=m["az"],
                    state=self.tr("parked")
                    if m["parked"]
                    else (self.tr("tracking") if m["tracking"] else self.tr("not tracking")),
                )
            )
        job = st["job"]
        if job["name"]:
            done = not job["running"] and not job["error"]  # a slew or park reports no progress of its own
            text = f"{job['name']}: {100 if done else int(100 * job['progress'])}% {job['message']}"
            if job["error"]:
                text += "\n" + self.tr("Stopped: {e}").format(e=translate(job["error"]))
            elif not job["running"] and job.get("result"):
                text += "\n" + self.result_text(job["result"])
            elif not job["running"]:
                n = len(job["written"])
                text += "\n" + (self.tr("Finished, {n} frames.").format(n=n) if n else self.tr("Finished."))
            self.job.setText(text)
        self.log.setPlainText("\n".join(st["log"]))
        self._show_devices(st)

    def _post(self, path, body=None):
        if self.client is None:
            self.safety.setText(self.tr("Connect first."))
            return False
        try:
            self.client.post(path, body)
            self._poll()
            return True
        except Exception as e:
            self.job.setText(self.tr("Refused: {e}").format(e=translate(e)))
            return False

    def _coord(self, text):
        from ..planning.targets import parse_coordinates

        c = parse_coordinates(text)
        if c is None:
            raise ValueError(self.tr("Coordinates not understood: {t}").format(t=text))
        return c

    def centre(self):
        try:
            c = self._coord(self.target.text())
        except ValueError as e:
            self.job.setText(translate(e))
            return False
        return self._post(
            "/center", {"ra": c.ra.deg, "dec": c.dec.deg, "exptime": 5.0, "out_dir": self.out_dir.text().strip()}
        )

    def result_text(self, result):
        """Plain words for what a centring or polar-alignment job found."""
        if not result:
            return ""
        if "errors" in result:
            e = result["errors"]
            return self.tr("Centred to {e:.0f} arcsec after {n} frames.").format(e=e[-1], n=len(e))
        p = result["polar"]
        alt = self.tr("lower the axis by {v:.1f}′") if p["alt"] > 0 else self.tr("raise the axis by {v:.1f}′")
        az = self.tr("turn it west by {v:.1f}′") if p["az"] > 0 else self.tr("turn it east by {v:.1f}′")
        return self.tr("Polar axis off by {t:.1f}′: {alt}, {az}.").format(
            t=p["total"], alt=alt.format(v=abs(p["alt"])), az=az.format(v=abs(p["az"]))
        )

    def _slew(self):
        try:
            c = self._coord(self.target.text())
        except ValueError as e:
            self.job.setText(translate(e))
            return
        self._post("/slew", {"ra": c.ra.deg, "dec": c.dec.deg})

    # --- sequence -------------------------------------------------------------
    def add_exposure_row(self):
        r = self.exposures.rowCount()
        self.exposures.insertRow(r)
        kind = QComboBox(self.exposures)
        kind.addItems(KINDS)
        kind.setToolTip(
            self.tr(
                "light: the sky; dark: shutter closed, as long as the lights; bias: the shortest exposure, "
                "shutter closed; flat: an evenly lit field"
            )
        )
        kind.currentIndexChanged.connect(self._widget_changed)
        self.exposures.setCellWidget(r, 0, kind)
        self.exposures.setItem(r, 1, QTableWidgetItem(""))
        exp = QDoubleSpinBox(self.exposures)
        exp.setRange(0, 36000)
        exp.setDecimals(3)
        exp.setValue(60)
        exp.setToolTip(self.tr("Exposure time of each frame in seconds"))
        exp.valueChanged.connect(self._widget_changed)
        self.exposures.setCellWidget(r, 2, exp)
        for c, (lo, hi, v) in ((3, (1, 10000, 10)), (4, (1, 8, 1))):
            s = QSpinBox(self.exposures)
            s.setRange(lo, hi)
            s.setValue(v)
            s.setToolTip(
                self.tr("How many frames") if c == 3 else self.tr("Binning: 1 is full resolution, 2 adds 2×2 pixels")
            )
            s.valueChanged.connect(self._widget_changed)
            self.exposures.setCellWidget(r, c, s)
        for c in range(5, 9):
            self.exposures.setItem(r, c, QTableWidgetItem(""))

    # --- undo / redo of the exposure rows (Edit menu, Ctrl+Z / Ctrl+Y) ---------
    def undo_state(self):
        rows = []
        for r in range(self.exposures.rowCount()):
            cells = [self.exposures.item(r, c).text() if self.exposures.item(r, c) else "" for c in range(9)]
            w = [self.exposures.cellWidget(r, c) for c in range(5)]
            rows.append((w[0].currentIndex(), cells[1], w[2].value(), w[3].value(), w[4].value(), *cells[5:]))
        return tuple(rows)

    def set_undo_state(self, rows):
        self.exposures.blockSignals(True)
        self.exposures.setRowCount(0)
        for row in rows:
            self.add_exposure_row()
            r = self.exposures.rowCount() - 1
            widgets = [self.exposures.cellWidget(r, c) for c in (0, 2, 3, 4)]
            for w in widgets:
                w.blockSignals(True)
            widgets[0].setCurrentIndex(row[0])
            for w, v in zip(widgets[1:], row[2:5], strict=True):
                w.setValue(v)
            for w in widgets:
                w.blockSignals(False)
            for c, text in zip((1, 5, 6, 7, 8), (row[1], *row[5:]), strict=True):
                self.exposures.item(r, c).setText(text)
        self.exposures.blockSignals(False)

    def _widget_changed(self, *_):
        if hasattr(self, "_typed_from"):  # not while the first row is built
            self.record(self.tr("change an exposure row"), self._typed_from)

    def _camera_cells(self, r):
        """Gain, offset, read-out mode and sub-frame of a row; empty cells are left out."""
        out = {}
        for c, key in ((5, "gain"), (6, "offset"), (7, "readout")):
            text = self.exposures.item(r, c).text().strip() if self.exposures.item(r, c) else ""
            if text:
                if not text.lstrip("-").isdigit():
                    raise ValueError(
                        self.tr("Row {row}: gain, offset and read-out mode are whole numbers").format(row=r + 1)
                    )
                out[key] = int(text)
        text = self.exposures.item(r, 8).text().strip() if self.exposures.item(r, 8) else ""
        if text:
            parts = text.replace(",", " ").split()
            if len(parts) != 4 or not all(p.isdigit() for p in parts) or min(int(p) for p in parts[2:]) < 1:
                raise ValueError(self.tr("Row {row}: sub-frame is x, y, width, height in pixels").format(row=r + 1))
            out["roi"] = [int(p) for p in parts]
        return out

    def sequence_spec(self):
        exposures = []
        for r in range(self.exposures.rowCount()):
            filt = self.exposures.item(r, 1).text().strip() if self.exposures.item(r, 1) else ""
            exposures.append(
                {
                    "kind": self.exposures.cellWidget(r, 0).currentText(),
                    "filter": filt or None,
                    "exptime": self.exposures.cellWidget(r, 2).value(),
                    "count": self.exposures.cellWidget(r, 3).value(),
                    "binning": self.exposures.cellWidget(r, 4).value(),
                }
                | self._camera_cells(r)
            )
        target = {
            "name": self.seq_name.text().strip() or "target",
            "exposures": exposures,
            "dither_every": self.dither.value(),
        }
        if self.seq_coord.text().strip():
            c = self._coord(self.seq_coord.text())
            target |= {"ra": c.ra.deg, "dec": c.dec.deg}
        for key, edit in (("start", self.seq_start), ("end", self.seq_end)):
            if edit.text().strip():
                target[key] = edit.text().strip()
        if self.rotation.text().strip():
            try:
                target["rotation"] = float(self.rotation.text().replace(",", "."))
            except ValueError:
                raise ValueError(self.tr("The rotator angle must be a number of degrees.")) from None
        if self.plan:  # the night plan replaces the single target (its exposure rows and dithering are used)
            common = {"exposures": exposures, "dither_every": self.dither.value()}
            return {"out_dir": self.out_dir.text().strip(), "targets": [t | common for t in self.plan]}
        return {"out_dir": self.out_dir.text().strip(), "targets": [target]}

    def load_schedule(self, blocks):
        """A night plan: one sequence target per block, observed between its start and end."""
        from astropy.time import Time

        self.plan = [
            {
                "name": b["name"],
                "ra": b["ra"],
                "dec": b["dec"],
                "start": Time(b["start"], format="jd").isot[:19],
                "end": Time(b["end"], format="jd").isot[:19],
            }
            for b in blocks
        ]
        self.plan_list.clear()
        self.plan_list.addItems(f"{t['start'][11:16]}–{t['end'][11:16]} UTC  {t['name']}" for t in self.plan)
        self.plan_box.setVisible(bool(self.plan))

    def load_sequence(self, target):
        """Fill the sequence form from a target spec (as sequence_spec writes it, e.g. from an automation)."""
        from astropy.coordinates import SkyCoord

        self.seq_name.setText(target.get("name", ""))
        coord = ""
        if "ra" in target:
            coord = SkyCoord(target["ra"], target["dec"], unit="deg").to_string("hmsdms", sep=":", precision=1)
        self.seq_coord.setText(coord)
        self.dither.setValue(int(target.get("dither_every", 0)))
        self.seq_start.setText(target.get("start") or "")
        self.seq_end.setText(target.get("end") or "")
        self.edit(self.tr("load a sequence"), self._load_rows, target.get("exposures", []))
        self.rotation.setText("" if target.get("rotation") is None else str(target["rotation"]))

    def _load_rows(self, exposures):
        self.exposures.setRowCount(0)
        for e in exposures:
            self.add_exposure_row()
            r = self.exposures.rowCount() - 1
            self.exposures.cellWidget(r, 0).setCurrentText(e.get("kind", "light"))
            self.exposures.item(r, 1).setText(e.get("filter") or "")
            self.exposures.cellWidget(r, 2).setValue(float(e.get("exptime", 60)))
            self.exposures.cellWidget(r, 3).setValue(int(e.get("count", 1)))
            self.exposures.cellWidget(r, 4).setValue(int(e.get("binning", 1)))
            for c, key in ((5, "gain"), (6, "offset"), (7, "readout")):
                self.exposures.item(r, c).setText("" if e.get(key) is None else str(e[key]))
            self.exposures.item(r, 8).setText(", ".join(str(v) for v in e.get("roi") or []))

    def _start_sequence(self):
        try:
            spec = self.sequence_spec()
        except ValueError as e:
            self.job.setText(translate(e))
            return
        if self._post("/sequence", spec):
            self._sequence_dir = spec["out_dir"]

    def panel_flats(self):
        r = max(self.exposures.currentRow(), 0)
        item = self.exposures.item(r, 1)
        return self._post(
            "/panelflats",
            {
                "filter": (item.text().strip() if item else "") or None,
                "count": self.exposures.cellWidget(r, 3).value(),
                "out_dir": self.out_dir.text().strip(),
            },
        )

    def _sky_flats(self):
        r = max(self.exposures.currentRow(), 0)
        item = self.exposures.item(r, 1)
        self._post(
            "/skyflats",
            {
                "filter": (item.text().strip() if item else "") or None,
                "count": self.exposures.cellWidget(r, 3).value(),
                "out_dir": self.out_dir.text().strip(),
            },
        )
