"""The Calibrate page: bias, dark and flat frames, masters and calibrated lights."""

import re
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..calibration.frames import Frame
from ..calibration.matching import make_plan
from ..photometry.multifilter import by_filter  # noqa: F401  (imported from here by other pages)
from . import automatic
from .kit.help import help_line
from .kit.widgets import Collapsible, StepGuide, _title
from .master_choice import add_button as add_masters_button
from .messages import translate
from .star_picker import add_align_row
from .star_picker import parse as parse_stars
from .undo import Undoable


class CalibratePage(Undoable, QWidget):
    """Raw folder -> frame list and plan -> masters + calibrated lights."""

    scan_requested = Signal(str, str)  # calibration (or mixed) folders, light folder
    run_requested = Signal(list, str, dict)  # frames, output folder, params
    stack_requested = Signal(list, str, dict)  # calibrated images, output file, params
    photometry_requested = Signal(list)  # calibrated lights to measure

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.frames, self._problems, self._raw_converted, self.calibrated = [], [], 0, []
        left, right = QWidget(self), QWidget(self)  # 1. the frames | 2.–4. what is done with them
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Calibration"), self))
        self.guide = StepGuide(
            [
                (
                    self.tr("Choose the folders of the lights and of the bias, dark and flat frames, then Scan"),
                    self.tr(
                        "Choose the light frames' folder and the calibration frames' folder (Browse…), then press Scan."
                    ),
                ),
                (
                    self.tr("Check the frame types found (IRAF ccdlist)"),
                    self.tr(
                        "Check the table: each frame's type, exposure, filter and temperature. Double-click a wrong "
                        "type to change it, and read the problems listed under the table."
                    ),
                ),
                (
                    self.tr(
                        "Combine the masters and calibrate the lights (zerocombine, darkcombine, flatcombine, ccdproc)"
                    ),
                    self.tr(
                        "Choose where to write the results and press 3. Calibrate. For spectra tick Spectra: do not "
                        "divide by the flat."
                    ),
                ),
                (
                    self.tr("Measure them, or stack them (phot, imcombine)"),
                    self.tr("Press 4. Measure them in the Photometry window →, or stack them into one deep picture."),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)
        lay.addWidget(QLabel(self.tr("1. Choose your frames: the lights and the calibration frames (BDF)."), self))
        lay.addWidget(help_line(self.tr("Lights in one folder, bias / dark / flat (BDF) in another — or everything "
                                        "as BDF."), "calibration-1-scan-raw-frames", self))  # fmt: skip
        row = QHBoxLayout()
        self.lights = QLineEdit(self)
        self.lights.setPlaceholderText(self.tr("light frames (data) folder"))
        self.lights.setToolTip(
            self.tr("Every frame here is a light, unless its header says bias, dark or flat. Sub-folders are read too.")
        )
        browse_l = self.lights_browse = QPushButton(self.tr("Browse…"), self)
        browse_l.clicked.connect(lambda: self._pick(self.lights))
        browse_l.setToolTip(self.tr("Choose the folder in a dialog"))
        row.addWidget(QLabel(self.tr("Lights"), self))
        row.addWidget(self.lights, 1)
        row.addWidget(browse_l)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.folder = QLineEdit(self)
        self.folder.setPlaceholderText(self.tr("bias / dark / flat folder; another folder; …"))
        self.folder.setToolTip(
            self.tr(
                "Calibration frames, sorted into bias, dark and flat. Several folders separated by ';' (e.g. a "
                "calibration library). Everything in one folder: give it here only."
            )
        )
        browse = self.frames_browse = QPushButton(self.tr("Browse…"), self)
        browse.clicked.connect(lambda: self._pick(self.folder))
        browse.setToolTip(self.tr("Choose the folder in a dialog"))
        add_folder = self.add_folder_button = QPushButton(self.tr("Add folder…"), self)
        add_folder.setToolTip(
            self.tr("Read frames from one more folder, e.g. master or calibration frames kept elsewhere")
        )
        add_folder.clicked.connect(self._add_folder)
        row.addWidget(QLabel(self.tr("BDF"), self))
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        row.addWidget(add_folder)
        lay.addLayout(row)
        self.scan_button = QPushButton(self.tr("Scan"), self)
        self.scan_button.clicked.connect(lambda: self.scan_requested.emit(self.folder.text(), self.lights.text()))
        self.scan_button.setToolTip(
            self.tr(
                "Reads every frame and sorts it by its header into bias, dark, flat, arc and light; nothing"
                " is changed yet, check the table"
            )
        )
        self.clock_offset = QDoubleSpinBox(self)
        self.clock_offset.setRange(-14, 14)
        self.clock_offset.setDecimals(2)
        self.clock_offset.setPrefix(self.tr("DSLR clock − UTC: "))
        self.clock_offset.setSuffix(self.tr(" h"))
        self.clock_offset.setToolTip(
            self.tr(
                "Camera raw files (CR2, NEF, ARW, DNG…) are converted to FITS in the folder fits_from_raw. Their "
                "time is the camera clock: give how many hours it is ahead of UTC (0 if the camera is set to UTC), "
                "and check the clock against a time signal — timing errors go straight into minima and O−C."
            )
        )
        row = QHBoxLayout()  # a second row: the first stays narrow enough for two columns on a small screen
        for w in (self.clock_offset, self.scan_button):
            row.addWidget(w)
        row.addStretch(1)
        lay.addLayout(row)
        self.summary = QLabel(self)
        self.summary.setWordWrap(True)
        remove = self.remove_button = QPushButton(self.tr("Remove from the list"), self)
        remove.setToolTip(
            self.tr(
                "Leaves the selected frames out of the calibration (Delete key; Ctrl+Z brings them back). "
                "The files are not deleted."
            )
        )
        remove.clicked.connect(self._remove_selected)
        clear = self.clear_button = QPushButton(self.tr("Clear"), self)
        clear.setToolTip(self.tr("Empties the folders and the frame list, to choose the folders again (Ctrl+Z undoes)"))
        clear.clicked.connect(self._clear)
        row = QHBoxLayout()
        row.addWidget(self.summary, 1)
        row.addWidget(remove)
        row.addWidget(clear)
        lay.addLayout(row)
        self.table = QTableWidget(0, 6, self)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.installEventFilter(self)  # the Delete key removes the selected frames
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("File"),
                self.tr("Type"),
                self.tr("Exposure (s)"),
                self.tr("Filter"),
                self.tr("Temp. (°C)"),
                self.tr("Binning"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._edit_kind)
        self.table.setToolTip(self.tr("Double-click a frame's type to change it"))
        lay.addWidget(self.table, 1)
        lay.addWidget(help_line(self.tr("The type comes from the header, else from the file name; double-click a "
                                        "type to change it."), "calibration-1-scan-raw-frames", self))  # fmt: skip
        self.warnings = QPlainTextEdit(self)
        self.warnings.setReadOnly(True)
        self.warnings.setMaximumHeight(90)
        self.warnings.setPlaceholderText(self.tr("Problems and missing calibration frames are listed here."))
        lay.addWidget(self.warnings)
        lay = QVBoxLayout(right)
        lay.addWidget(QLabel(self.tr("2. Choose where to write master frames and calibrated images."), self))
        row = QHBoxLayout()
        self.output = QLineEdit(self)
        browse_out = QPushButton(self.tr("Browse…"), self)
        browse_out.clicked.connect(lambda: self._pick(self.output))
        self.output.setToolTip(
            self.tr(
                "Folder for the master frames and the calibrated images; created if it does not exist. The "
                "raw frames are never changed."
            )
        )
        browse_out.setToolTip(self.tr("Choose the folder in a dialog"))
        row.addWidget(self.output)
        row.addWidget(browse_out)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Rejection (sigma):"), self))
        self.sigma = QDoubleSpinBox(self)
        self.sigma.setRange(1.5, 10.0)
        self.sigma.setSingleStep(0.5)
        self.sigma.setValue(3.0)
        self.sigma.setToolTip(
            self.tr(
                "A pixel further than this many standard deviations from the other frames' values is left "
                "out when the masters are combined and when images are stacked; 3 is the usual value"
            )
        )
        row.addWidget(self.sigma)
        self.cosmics = QCheckBox(self.tr("Remove cosmic rays from lights"), self)
        self.cosmics.setToolTip(
            self.tr(
                "Finds cosmic-ray hits in each light by their sharp edges (L.A.Cosmic, astroscrappy) and "
                "replaces them. Useful for long exposures and spectra; when many frames are stacked with "
                "rejection it is not needed."
            )
        )
        self.optimize_dark = QCheckBox(self.tr("Scale the dark to each light (dark optimisation)"), self)
        self.optimize_dark.setToolTip(
            self.tr("Finds the dark scale that leaves the least noise; useful when the camera temperature drifted")
        )
        self.fix_defects = QCheckBox(self.tr("Repair hot and dead pixels (defect map from the masters)"), self)
        self.fix_defects.setToolTip(
            self.tr(
                "Hot pixels (from the master dark) and dead pixels (from the master flat) are replaced by "
                "the median of their neighbours in every light; the map is saved with the masters"
            )
        )
        self.spectra = QCheckBox(self.tr("Spectra: do not divide by the flat"), self)
        self.spectra.setToolTip(
            self.tr(
                "For echelle and long-slit frames: the flat between the orders is near zero, so dividing by it "
                "would blow up the noise. The master flat is still made; give it to the Spectroscopy window."
            )
        )
        self.split_colour = QCheckBox(self.tr("Colour camera: each colour as its own image"), self)
        self.split_colour.setChecked(True)
        self.split_colour.setToolTip(
            self.tr(
                "Frames with a Bayer pattern (BAYERPAT) are calibrated as a mosaic, then written as three half-size "
                "images R, G, B (filters TR, TG, TB) without interpolation; G is closest to V. "
                "Monochrome frames are not affected."
            )
        )
        row.addStretch(1)
        self.run_button = QPushButton(self.tr("3. Calibrate"), self)
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self._run)
        self.run_button.setToolTip(
            self.tr(
                "Makes the master bias, dark and flat and writes every light as (light − bias − dark) / "
                "flat into the output folder"
            )
        )
        add_masters_button(self, row, lay)  # "Choose the masters by hand…" on its line, then Calibrate
        lay.addLayout(row)
        lay.addWidget(self.cosmics)  # its own line: beside the button it kept the column wider than a small window
        self.linearity = QLineEdit(self)
        self.linearity.setPlaceholderText(self.tr("linearity correction c0 c1 c2 … (empty: none)"))
        self.linearity.setToolTip(
            self.tr(
                "The camera's non-linearity: every raw value v becomes c0 + c1·v + c2·v² + … before calibration "
                "(from the maker's sheet or a series of flats of rising exposure)"
            )
        )
        self.more_options = Collapsible(self.tr("More calibration options"), self)
        for w in (self.optimize_dark, self.fix_defects, self.split_colour, self.spectra, self.linearity):
            self.more_options.body.addWidget(w)
        lay.addWidget(self.more_options)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        lay.addWidget(self.result)
        self.photometry_button = QPushButton(self.tr("4. Measure them in the Photometry window →"), self)
        self.photometry_button.setEnabled(False)
        self.photometry_button.setToolTip(
            self.tr(
                "Sends the calibrated lights to the Photometry window and opens it (a light curve, a variable star)"
            )
        )
        self.photometry_button.clicked.connect(lambda: self.photometry_requested.emit(list(self.calibrated)))
        self.photometry_button.clicked.connect(lambda: self.guide.set_state(3, "done"))
        lay.addWidget(self.photometry_button)
        self.stack_button = QPushButton(self.tr("Or: stack them into one deep picture (not for a light curve)"), self)
        self.stack_button.setEnabled(False)
        self.stack_button.clicked.connect(self._stack)
        self.stack_button.setToolTip(
            self.tr(
                "Aligns the calibrated images on their stars and adds them into one image per filter: fainter stars "
                "and nebulae show, for a picture, astrometry or a colour image. Not needed for photometry: a light "
                "curve measures every single image (a stack has one time only)."
            )
        )
        lay.addWidget(self.stack_button)
        opts = QGridLayout()
        self.stack_opts = {}
        choices = {
            "method": (
                self.tr("Combine"),
                {"mean": self.tr("mean"), "median": self.tr("median"), "sum": self.tr("sum")},
            ),
            "rejection": (
                self.tr("Reject"),
                {
                    "sigma": self.tr("sigma clipping"),
                    "mad": self.tr("sigma clipping, median / MAD spread"),
                    "winsorized": self.tr("winsorized sigma clipping"),
                    "minmax": self.tr("min / max (drop lowest and highest)"),
                    "percentile": self.tr("percentile clipping"),
                    "none": self.tr("none"),
                },
            ),
            "normalize": (
                self.tr("Normalise"),
                {
                    "none": self.tr("none"),
                    "multiplicative": self.tr("multiplicative (scale to the first frame)"),
                    "additive": self.tr("additive (shift to the first frame)"),
                },
            ),
            "weighting": (self.tr("Weights"), {"none": self.tr("equal"), "noise": self.tr("by noise (1 / σ²)")}),
            "align": (
                self.tr("Align"),
                {
                    "translation": self.tr("shift only"),
                    "stars": self.tr("star patterns (rotation and scale too)"),
                },
            ),
        }
        tips = {
            "method": self.tr("mean: the least noise; median: robust without rejection; sum: keeps the counts"),
            "rejection": self.tr(
                "Pixels unlike the others (satellites, cosmic rays, hot pixels) are left out before combining; "
                "sigma clipping is IRAF imcombine's (median ± σ × rms) where ten or more frames cover a pixel and "
                "the median / MAD spread where fewer do; min / max and percentile also work with few frames"
            ),
            "normalize": self.tr(
                "Brings the frames to the same level before rejection: multiplicative when the transparency "
                "changed, additive when the sky background changed"
            ),
            "weighting": self.tr("By noise: noisier frames (thin cloud, twilight) count less"),
            "align": self.tr(
                "Shift only: an equatorial mount without field rotation; star patterns: the field rotates or the "
                "scale differs (alt-az mount, meridian flip, another telescope)"
            ),
        }
        for i, (key, (label, items)) in enumerate(choices.items()):
            box = QComboBox(self)
            for value, text in items.items():
                box.addItem(text, value)
            # its width from 10 characters, not the longest choice: opened, the options pushed the right column
            # past a window's edge (user-feedback UF-9); the list still shows each choice whole
            box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(10)
            self.stack_opts[key] = box
            box.setToolTip(tips[key])
            opts.addWidget(QLabel(label, self), i // 2, 2 * (i % 2))
            opts.addWidget(box, i // 2, 2 * (i % 2) + 1)
        self.clip_low, self.clip_high = QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w, v in ((self.clip_low, 1), (self.clip_high, 1)):
            w.setRange(0, 50)
            w.setDecimals(2)
            w.setValue(v)
            w.setToolTip(self.tr("min / max: how many values to drop; percentile: the fraction of the median"))
        opts.addWidget(QLabel(self.tr("Low / high"), self), 2, 2)
        lh = QHBoxLayout()
        lh.addWidget(self.clip_low)
        lh.addWidget(self.clip_high)
        opts.addLayout(lh, 2, 3)
        self.stack_options = Collapsible(self.tr("Stacking options"), self)
        add_align_row(self, self.stack_options.body, opts)  # the options' grid, then the stars to align on
        self.drizzle = QCheckBox(self.tr("Drizzle onto a 2× finer grid (undersampled, dithered frames)"), self)
        self.drizzle.setToolTip(
            self.tr(
                "For stars only one or two pixels wide (FWHM under about 2 px) in frames shifted a little "
                "between exposures: recovers detail on a grid twice as fine (Fruchter & Hook 2002). Needs "
                "many frames; otherwise leave it off."
            )
        )
        self.stack_options.body.addWidget(self.drizzle)
        lay.addWidget(self.stack_options)
        lay.addStretch(1)
        split = QSplitter(Qt.Horizontal, self)  # two columns: on a short window nothing is below the fold
        split.addWidget(left)
        split.addWidget(right)
        split.setChildrenCollapsible(False)
        split.setSizes([3000, 2000])
        QVBoxLayout(self).addWidget(split)
        self.calibrated = []

    def stack_params(self):
        params = {k: box.currentData() for k, box in self.stack_opts.items()} | {"sigma": self.sigma.value()}
        low, high = self.clip_low.value(), self.clip_high.value()
        if params["rejection"] == "minmax":
            low, high = int(low), int(high)
        elif params["rejection"] == "percentile" and (low >= 1 or high >= 1):  # given in percent
            low, high = low / 100, high / 100
        params |= {"low": low, "high": high}
        if params["align"] == "picked":  # unreadable text: no stars, and the step says to pick some
            try:
                params["align_stars"] = parse_stars(self.align_stars.text())
            except ValueError:
                params["align_stars"] = []
        return params

    def _stack(self):
        """One stack per filter (a colour camera's R, G, B channels are filters TR, TG, TB): frames taken through
        different filters must never be combined."""
        self.guide.set_state(3, "done")
        name = "drizzle" if self.drizzle.isChecked() else "stack"
        groups = by_filter(self.calibrated)
        single = [filt or "—" for filt, paths in groups.items() if len(paths) < 2]
        self.result.setText(
            self.tr("Stacking…")
            + (
                " " + self.tr("Only one frame through {f}: nothing to stack.").format(f=", ".join(single))
                if single
                else ""
            )
        )
        for filt, paths in groups.items():
            if len(paths) < 2:
                continue
            suffix = f"_{re.sub(r'[^A-Za-z0-9.+-]+', '_', filt).strip('_')}" if len(groups) > 1 else ""
            params = {"drizzle": True} if self.drizzle.isChecked() else self.stack_params()
            self.stack_requested.emit(paths, str(Path(self.output.text()) / f"{name}{suffix}.fits"), params)

    def _pick(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose folder"), self._first(line_edit.text()))
        if folder:
            line_edit.setText(folder)
            if line_edit is self.folder and not self.output.text():
                self.output.setText(str(Path(folder) / "calibrated"))
            if line_edit is not self.output and automatic.on("calibration.scan_on_folder"):  # no Scan press needed
                self.scan_button.click()

    @staticmethod
    def _first(text):
        return next((f.strip() for f in text.split(";") if f.strip()), "")

    def _add_folder(self, folder=None):
        """One more folder to read frames from (several folders are separated by ";")."""
        folder = folder or QFileDialog.getExistingDirectory(
            self, self.tr("Add folder"), self._first(self.folder.text())
        )
        if folder:
            current = [f.strip() for f in self.folder.text().split(";") if f.strip()]
            self.folder.setText("; ".join(current + [folder]))
            if not self.output.text():
                self.output.setText(str(Path(self._first(self.folder.text())) / "calibrated"))
            if automatic.on("calibration.scan_on_folder"):
                self.scan_button.click()

    def _edit_kind(self, row, col):
        """Double-click on a type: a list of the types; the choice is used for the calibration (the files are not
        changed)."""
        if col != 1 or row >= len(self.frames):
            return
        names = self._kind_names()
        box = QComboBox(self.table)
        for key, text in names.items():
            box.addItem(text, key)
        box.setCurrentIndex(max(0, box.findData(self.frames[row]["kind"])))

        def chosen(i):
            frames = list(self.frames)
            frames[row] = dict(frames[row]) | {"kind": box.itemData(i)}
            self.edit(self.tr("change a frame's type"), self.show_frames, frames, self._problems, self._raw_converted)

        box.activated.connect(chosen)
        self.table.setCellWidget(row, 1, box)
        box.showPopup()

    def _kind_names(self):
        return {
            "bias": self.tr("bias"),
            "dark": self.tr("dark"),
            "flat": self.tr("flat"),
            "light": self.tr("light"),
            "arc": self.tr("arc lamp"),
            "unknown": self.tr("unknown"),
        }

    def undo_state(self):
        return ([dict(f) for f in self.frames], list(self._problems), self.lights.text(), self.folder.text())

    def set_undo_state(self, state):
        frames, problems, lights, folder = state
        self.lights.setText(lights)
        self.folder.setText(folder)
        self.show_frames([dict(f) for f in frames], list(problems), self._raw_converted)

    def eventFilter(self, obj, event):
        if obj is self.table and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete:
            self._remove_selected()
            return True
        return super().eventFilter(obj, event)

    def _remove_selected(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        if rows:
            frames = [f for r, f in enumerate(self.frames) if r not in rows]
            self.edit(
                self.tr("remove frames from the list"), self.show_frames, frames, self._problems, self._raw_converted
            )

    def _clear(self):
        def clear():
            self.lights.clear()
            self.folder.clear()
            self.show_frames([], [], 0)

        self.edit(self.tr("clear the frame list"), clear)

    def show_frames(self, frames: list[dict], problems: list, raw_converted: int = 0):
        if not (self._editing or self._restoring):  # a new scan: the edits of the old list are not undone into it
            self.undo_stack.clear()
        self.frames, self._problems, self._raw_converted = frames, problems, raw_converted
        self.guide.set_state(0, "done" if frames else None)
        self.table.clearContents()
        base = self.lights.text().strip() or self._first(self.folder.text())
        if not self.output.text() and base:
            self.output.setText(str(Path(base) / "calibrated"))
        kinds = self._kind_names()
        self.table.setRowCount(len(frames))
        for r, f in enumerate(frames):
            values = (
                Path(f["path"]).name,
                kinds[f["kind"]],
                f["exptime"],
                f["filter"],
                None if f["temperature"] is None else f"{f['temperature']:.1f}",
                "×".join(map(str, f["binning"])),
            )
            for c, v in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))
        counts = {k: sum(f["kind"] == k for f in frames) for k in kinds}
        text = "  ".join(f"{kinds[k]}: {n}" for k, n in counts.items() if n)
        if raw_converted:
            text += "  " + self.tr("({n} camera raw files read; times: camera clock − {h} h)").format(
                n=raw_converted, h=f"{self.clock_offset.value():g}"
            )
        self.summary.setText(text)
        plan = make_plan([Frame(**f | {"binning": tuple(f["binning"]), "shape": tuple(f["shape"])}) for f in frames])
        cannot = self.tr("Cannot read {file}: {error}")
        lines = [cannot.format(file=Path(p).name, error=translate(e)) for p, e in problems]
        lines += [self.tr("Type unknown, ignored: {file}").format(file=Path(p).name) for p in plan.unknown]
        lines += [f"{Path(p).name}: {self._missing_text(k, why)}" for p, k, why in plan.missing]
        if frames and not counts["light"]:
            lines.insert(
                0,
                self.tr(
                    "No light frames found, so there is nothing to calibrate yet. If the lights are in another "
                    "folder, choose the folder that holds both (sub-folders are read) or add it with “Add folder…”."
                ),
            )
        self.warnings.setPlainText("\n".join(lines))
        self.run_button.setEnabled(counts["light"] + counts["arc"] > 0)
        self.run_button.setToolTip("" if counts["light"] else self.tr("Needs at least one light frame"))

    def _missing_text(self, kind, w):
        size = f"{w['shape'][1]}×{w['shape'][0]}, bin {w['binning'][0]}×{w['binning'][1]}"
        if kind == "flat":
            return self.tr("no flat for filter '{filter}' ({size}); will be calibrated without flat").format(
                filter=w["filter"] or "—", size=size
            )
        if kind == "dark":
            return self.tr(
                "no dark for {t} s within {tol} °C of {temp} °C (darks of another exposure need bias "
                "frames to be scaled); will be calibrated without dark"
            ).format(
                t=w["exptime"], tol=w["temp_tol"], temp="—" if w["temperature"] is None else f"{w['temperature']:.1f}"
            )
        return self.tr("no bias ({size}); will be calibrated without bias").format(size=size)

    def _run(self):
        self.result.setText(self.tr("Calibrating…"))
        params = {"sigma": self.sigma.value(), "cosmic_rays": self.cosmics.isChecked()}
        params |= {"optimize_dark": self.optimize_dark.isChecked(), "fix_defects": self.fix_defects.isChecked()}
        params["divide_flat"] = not self.spectra.isChecked()
        params["split_colour"] = self.split_colour.isChecked()
        params["use"] = self.master_choices  # the masters chosen by hand, over the program's matches
        try:
            params["linearity"] = [float(v) for v in self.linearity.text().replace(",", " ").split()]
        except ValueError:
            self.result.setText(self.tr("Linearity correction: write numbers c0 c1 c2 …, e.g. 0 1 4e-6"))
            return
        self.run_requested.emit(self.frames, self.output.text(), params)

    def show_result(self, out: dict):
        self.calibrated = out["calibrated"]
        for i in (1, 2):
            self.guide.set_state(i, "done")
        self.stack_button.setEnabled(len(self.calibrated) > 1)
        self.photometry_button.setEnabled(bool(self.calibrated))
        self.result.setText(
            self.tr("Done: {n} images calibrated, {m} master frames written to {folder}.").format(
                n=len(out["calibrated"]), m=len(out["masters"]), folder=self.output.text()
            )
            + (
                " " + self.tr("{n} arc lamp frames calibrated (bias and dark only).").format(n=len(out["arcs"]))
                if out.get("arcs")
                else ""
            )
            + (
                " "
                + self.tr("Dark scaled by {lo:.3f}–{hi:.3f} (DARKSCAL in each file's header).").format(
                    lo=min(out["dark_scales"]), hi=max(out["dark_scales"])
                )
                if out.get("dark_scales")
                else ""
            )
        )
        from .messages import translate

        unused = out.get("unused_groups") or []
        if unused:  # not combined: no light needs them (another size, binning, filter or setting)
            self.result.setText(
                self.result.text()
                + " "
                + self.tr("{n} groups of calibration frames fit no light and were not combined (e.g. {file}).").format(
                    n=len(unused), file=unused[0]["file"]
                )
            )
        failed = out.get("failed_masters") or []
        if failed:  # said where the user looks for problems, the frames list's note box
            kinds = {"bias": self.tr("bias"), "dark": self.tr("dark"), "flat": self.tr("flat")}
            lines = [
                self.tr("Master {kind} not made from {n} frames (e.g. {file}), calibrated without it: {why}").format(
                    kind=kinds.get(f["kind"], f["kind"]), n=f["frames"], file=f["file"], why=translate(f["reason"])
                )
                for f in failed
            ]
            self.warnings.setPlainText("\n".join(lines + [self.warnings.toPlainText()]).strip())
