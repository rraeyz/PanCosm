"""Spectroscopy: reduce a 2-D long-slit/slitless frame to a calibrated 1-D spectrum; radial
velocities against a template and a Keplerian orbit."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
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
    QListWidget,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .messages import translate
from .undo import Undoable, track_typing
from .workspaces import PlotCanvas


def _rows(table):
    return [
        [table.item(r, c).text() if table.item(r, c) else "" for c in range(table.columnCount())]
        for r in range(table.rowCount())
    ]


def _set_rows(table, rows):
    table.blockSignals(True)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            table.setItem(r, c, QTableWidgetItem(text))
    table.blockSignals(False)


FITS = "FITS (*.fits *.fit *.fts *.FITS *.FIT)"


def _database_and_reference(path):
    """(IRAF database, reference arc or None) from either of the two files chosen by the user."""
    from ..spectroscopy import reidentify

    path = Path(path)
    if path.suffix.lower() in (".fits", ".fit", ".fts", ".fz"):
        stem = path.name.split(".fit")[0]
        for db in (path.parent / "database" / f"id{stem}", path.parent / f"id{stem}"):
            if db.exists():
                return db, path
        raise ValueError(f"no IRAF database id{stem} next to it: choose the database file itself")
    return path, reidentify.find_reference(path)


def _spin(parent, value, lo=0.5, hi=500.0, decimals=1):
    w = QDoubleSpinBox(parent)
    w.setRange(lo, hi)
    w.setDecimals(decimals)
    w.setValue(value)
    return w


def _line_lists():
    from ..spectroscopy import wavecal  # scipy.signal: loaded when a spectroscopy tab is built

    return wavecal.line_lists()


class _Orientation(QWidget):
    """Dispersion direction on the detector (coude spectrographs often disperse along the columns)."""

    def __init__(self, parent):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(self.tr("Dispersion along"), self))
        self.axis = QComboBox(self)
        self.axis.addItems([self.tr("rows (x)"), self.tr("columns (y)")])
        self.axis.setToolTip(
            self.tr(
                "Along which axis of the detector the wavelength changes; many coudé spectrographs disperse"
                " along the columns"
            )
        )
        self.reverse = QCheckBox(self.tr("blue on the right"), self)
        self.reverse.setToolTip(
            self.tr("Tick when the wavelength decreases along the axis (blue on the right, or at the top)")
        )
        lay.addWidget(self.axis)
        lay.addWidget(self.reverse)
        lay.addStretch(1)

    def params(self):
        return {"orientation": "y" if self.axis.currentIndex() == 1 else "x", "reverse": self.reverse.isChecked()}

    def state(self):
        return {"axis": self.axis.currentIndex(), "reverse": self.reverse.isChecked()}

    def restore(self, st):
        self.axis.setCurrentIndex(int(st.get("axis", 0)))
        self.reverse.setChecked(bool(st.get("reverse", False)))


class _FileRow(QWidget):
    def __init__(self, label, parent, pattern=FITS):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(label, self))
        self.edit = QLineEdit(self)
        lay.addWidget(self.edit, 1)
        self.edit.setToolTip(self.tr("Path of the file: type it or choose it with Browse…"))
        b = QPushButton(self.tr("Browse…"), self)
        b.clicked.connect(lambda: self._pick(pattern))
        b.setToolTip(self.tr("Choose the file in a dialog"))
        lay.addWidget(b)

    def _pick(self, pattern):
        path, _ = QFileDialog.getOpenFileName(self, "", "", pattern)
        if path:
            self.edit.setText(path)

    def text(self):
        return self.edit.text().strip()


class ReduceTab(Undoable, QWidget):
    reduce_requested = Signal(dict, dict)  # inputs, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        self.science = _FileRow(self.tr("Science frame"), self)
        self.arc = _FileRow(self.tr("Arc lamp (optional)"), self)
        lay.addWidget(self.science)
        lay.addWidget(self.arc)
        self.orientation = _Orientation(self)
        lay.addWidget(self.orientation)
        grid = QGridLayout()
        self.width, self.sky_offset, self.sky_width = _spin(self, 10), _spin(self, 15), _spin(self, 10)
        self.sky_width.setToolTip(
            self.tr(
                "Width of each sky strip; the sky under the spectrum is fitted from them, row by row along the slit"
            )
        )
        self.sky_offset.setToolTip(
            self.tr("Distance from the spectrum's centre to the sky strips on both sides; beyond the star's light")
        )
        self.width.setToolTip(
            self.tr(
                "Width of the strip across the spectrum that is added up; about two to three times the spectrum's FWHM"
            )
        )
        self.row = _spin(self, 0, 0, 100000, 0)
        self.row.setSpecialValueText(self.tr("the brightest"))
        self.row.setToolTip(
            self.tr(
                "A row the spectrum crosses, when the frame holds several (two orders, a second star): it is "
                "followed from there along the frame. Check the traced line drawn on the frame after extracting."
            )
        )
        self.optimal = QCheckBox(self.tr("Optimal extraction (Horne)"), self)
        self.optimal.setChecked(True)
        self.optimal.setToolTip(
            self.tr(
                "Horne (1986): each pixel counts by the spectrum's profile and its noise; more signal-to-noise for "
                "faint spectra. Turn off for saturated or very bright spectra."
            )
        )
        self.line_list = QComboBox(self)
        self.line_list.addItems(_line_lists())
        self.line_list.setCurrentText("henear")
        self.line_list.setToolTip(
            self.tr(
                "The gas of your arc lamp: after your identified lines, further lines of this list are "
                "found and added to the fit, as IRAF identify does"
            )
        )
        for r, (label, w) in enumerate(
            (
                (self.tr("Spectrum at row"), self.row),
                (self.tr("Aperture width (px)"), self.width),
                (self.tr("Sky offset (px)"), self.sky_offset),
                (self.tr("Sky width (px)"), self.sky_width),
                (self.tr("Arc line list"), self.line_list),
            )
        ):
            grid.addWidget(QLabel(label, self), r, 0)
            grid.addWidget(w, r, 1)
        lay.addLayout(grid)
        lay.addWidget(self.optimal)
        self.extract_button = QPushButton(self.tr("1. Extract"), self)
        self.extract_button.clicked.connect(lambda: self._run(with_guesses=False))
        self.extract_button.setToolTip(
            self.tr(
                "Follows the spectrum along the frame, subtracts the sky and adds it up across the slit; "
                "the arc is extracted along the same trace"
            )
        )
        lay.addWidget(self.extract_button)
        lay.addWidget(QLabel(self.tr("2. Click arc lines in the lower plot, type their wavelengths (Å):"), self))
        self.guesses = QTableWidget(0, 2, self)
        self.guesses.setHorizontalHeaderLabels([self.tr("Pixel"), self.tr("Wavelength (Å)")])
        self.guesses.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        track_typing(self, self.guesses, self.tr("type a wavelength"))
        lay.addWidget(self.guesses, 1)
        self.reference_button = QPushButton(self.tr("Lines from a reference arc / IRAF database…"), self)
        self.reference_button.setToolTip(
            self.tr(
                "For a spectrograph whose arc was identified before (an IRAF identify database, with its reference "
                "arc spectrum, e.g. from the observatory's pipeline): this arc is matched to the reference "
                "(stretch and shift, as PypeIt and IRAF reidentify) and the known lines are placed on its peaks. "
                "They fill the table for you to check before solving."
            )
        )
        self.reference_button.clicked.connect(lambda: self.lines_from_reference())
        lay.addWidget(self.reference_button)
        row = QHBoxLayout()
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(lambda: self.edit(self.tr("clear the lines"), self.guesses.setRowCount, 0))
        clear.setToolTip(self.tr("Removes every identified line (Ctrl+Z brings them back)"))
        self.solve_button = QPushButton(self.tr("3. Solve wavelengths and save"), self)
        self.solve_button.clicked.connect(lambda: self._run(with_guesses=True))
        self.solve_button.setToolTip(
            self.tr(
                "Fits pixel → wavelength through the identified lines (at least three), shows the residual "
                "of every line and saves the calibrated spectrum"
            )
        )
        row.addWidget(clear)
        row.addWidget(self.solve_button)
        lay.addLayout(row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._plot_clicked)
        split.addWidget(self.plot)
        split.setSizes([380, 820])
        QVBoxLayout(self).addWidget(split)

    def _guesses(self):
        out = []
        for r in range(self.guesses.rowCount()):
            try:
                out.append([float(self.guesses.item(r, 0).text()), float(self.guesses.item(r, 1).text())])
            except (AttributeError, ValueError):
                continue  # a row without a wavelength yet
        return out

    def _run(self, with_guesses):
        if not self.science.text():
            self.status.setText(self.tr("Choose a science frame."))
            return
        from ..spectroscopy.steps import spectrum_name

        inputs = {"science": self.science.text()}
        if self.arc.text():
            inputs["arc"] = self.arc.text()
        if with_guesses:
            g = self._guesses()
            if len(g) < 2 or "arc" not in inputs:
                self.status.setText(self.tr("An arc and at least two identified lines are needed."))
                return
            inputs |= {
                "guesses": g,
                "output": str(Path(self.science.text()).with_name(spectrum_name(inputs["science"]))),
            }
        params = {
            "width": self.width.value(),
            "sky_offset": self.sky_offset.value(),
            "sky_width": self.sky_width.value(),
            "optimal": self.optimal.isChecked(),
            "line_list": self.line_list.currentText(),
            "guess_row": self.row.value() or None,
        } | self.orientation.params()
        self.status.setText(self.tr("Working…"))
        self.reduce_requested.emit(inputs, params)

    def state(self):
        return {
            "row": self.row.value(),
            "width": self.width.value(),
            "sky_offset": self.sky_offset.value(),
            "sky_width": self.sky_width.value(),
            "optimal": self.optimal.isChecked(),
            "line_list": self.line_list.currentText(),
            "orientation": self.orientation.state(),
        }

    def restore(self, st):
        for key in ("row", "width", "sky_offset", "sky_width"):
            if key in st:
                getattr(self, key).setValue(float(st[key]))
        self.optimal.setChecked(bool(st.get("optimal", True)))
        self.line_list.setCurrentText(st.get("line_list", "henear"))
        self.orientation.restore(st.get("orientation", {}))

    def show_spectrum(self, s):
        self.result = s
        self.plot.figure.clear()
        has_arc = bool(s.get("arc"))
        axes = self.plot.figure.subplots(3 if has_arc else 2, 1, squeeze=False)[:, 0]
        self._draw_trace(axes[-1], s["trace"])  # the user sees what was extracted, as IRAF's aptrace shows it
        x = s["wave"] if s["wave"] is not None else s["pixel"]
        axes[0].plot(x, s["flux"], lw=0.7)
        axes[0].set_xlabel(self.tr("Wavelength (Å)") if s["wave"] is not None else self.tr("Pixel"))
        axes[0].set_ylabel(self.tr("Flux"))
        if has_arc:
            axes[1].plot(s["pixel"], s["arc"], lw=0.7, color="gray")
            for p in s["arc_peaks"]:
                axes[1].axvline(p, color="orange", lw=0.5)
            axes[1].set_xlabel(self.tr("Pixel (click a line to identify it)"))
            self._arc_ax = axes[1]
        self.plot.draw()
        if s["solution"]:
            self.status.setText(
                self.tr("Wavelength solution: {n} lines, rms {rms:.3f} Å. Saved: {path}").format(
                    n=s["solution"]["n_lines"], rms=s["solution"]["rms"], path=s.get("path", "—")
                )
            )
        else:
            self.status.setText(
                self.tr("Extracted {n} columns; {m} arc lines found.").format(n=len(s["flux"]), m=len(s["arc_peaks"]))
            )

    def _draw_trace(self, ax, coef):
        from ..spectroscopy.steps import _load

        try:
            d = _load(self.science.text(), self.orientation.params())[0]
        except (OSError, ValueError):
            return
        lo, hi = np.nanpercentile(d[:: max(1, d.shape[0] // 256), :: max(1, d.shape[1] // 512)], [5, 99.5])
        ax.imshow(d, origin="lower", cmap="gray", vmin=lo, vmax=hi, aspect="auto", interpolation="nearest")
        x = np.arange(d.shape[1])
        y = np.polyval(coef, x)
        half = self.width.value() / 2
        for off, style in ((0, "-"), (-half, ":"), (half, ":")):
            ax.plot(x, y + off, style, color="#3fb950", lw=0.8)
        ax.set_xlim(0, d.shape[1] - 1)
        ax.set_ylim(0, d.shape[0] - 1)
        ax.set_title(self.tr("Traced spectrum and aperture (choose another row if this is not your star)"), fontsize=8)

    def _plot_clicked(self, event):
        if not self.result or getattr(self, "_arc_ax", None) is not event.inaxes or event.xdata is None:
            return
        peaks = np.asarray(self.result["arc_peaks"])
        if peaks.size == 0:
            return
        p = float(peaks[np.argmin(np.abs(peaks - event.xdata))])
        self.edit(self.tr("identify a line"), self._add_line, [f"{p:.2f}", ""])
        self.guesses.editItem(self.guesses.item(self.guesses.rowCount() - 1, 1))

    def _add_line(self, row):
        _set_rows(self.guesses, _rows(self.guesses) + [row])

    def lines_from_reference(self, path=None, record=0):
        """Identifications from an IRAF database (and the reference arc it was made on) placed on this arc."""
        from ..spectroscopy import reidentify

        if not self.result or not self.result.get("arc"):
            self.status.setText(self.tr("Extract with an arc first (1. Extract): its lines are matched."))
            return None
        path = (
            path
            or QFileDialog.getOpenFileName(
                self, self.tr("IRAF database or reference arc"), "", self.tr("IRAF databases and spectra (*)")
            )[0]
        )
        if not path:
            return None
        try:
            database, reference = _database_and_reference(path)
            features = reidentify.read_database(database)[record]["features"]
            peaks = self.result["arc_peaks"]
            if reference is not None:
                wave, flux = reidentify.reference_arc(reference)
                lines = [(f["wave"], f["label"]) for f in features]
                r = reidentify.from_reference(self.result["arc"], peaks, wave, flux, lines)
                rows = [[f"{p:.2f}", f"{w:.4f}"] for p, w, _ in r["pairs"]]
                text = self.tr(
                    "{m} of {n} lines of {ref} found in this arc (correlation {c:.2f}; rms {rms:.2f} Å against the "
                    "reference's lines). Check them on the arc plot, delete wrong rows, then 3. Solve."
                ).format(m=r["matched"], n=r["of"], ref=Path(reference).name, c=r["correlation"], rms=r["rms"])
                doubtful = r["correlation"] < 0.3 or r["matched"] < 3
            else:
                shift, found = reidentify.shift_features(peaks, features)
                rows = [[f"{p:.2f}", f"{f['wave']:.4f}"] for p, f in found]
                text = self.tr(
                    "{m} of {n} lines of {db} found in this arc, shifted by {s:+.1f} px (the database's pixels are "
                    "taken as this spectrograph's). Check them on the arc plot, delete wrong rows, then 3. Solve."
                ).format(m=len(found), n=len(features), db=Path(database).name, s=shift)
                doubtful = len(found) < 3
        except (OSError, ValueError, IndexError, KeyError) as e:
            self.status.setText(
                self.tr("Cannot use {file}: {error}").format(file=Path(path).name, error=translate(str(e)))
            )
            return None
        if doubtful:
            text += " " + self.tr(
                "Few lines agree: is the reference from the same spectrograph, grating, slit and lamp? "
                "Identify the lines by hand instead."
            )
        self.edit(self.tr("lines from a reference"), _set_rows, self.guesses, rows)
        self.status.setText(text)
        return rows

    def undo_state(self):
        return {"guesses": _rows(self.guesses)}

    def set_undo_state(self, st):
        _set_rows(self.guesses, st["guesses"])


class EchelleTab(Undoable, QWidget):
    """Echelle / cross-dispersed spectra: orders traced on a flat, global 2-D wavelength solution
    from lines identified in a few orders, blaze-corrected merged spectrum."""

    reduce_requested = Signal(dict, dict)
    orders_requested = Signal(dict, dict)  # image, params (with rows when the user edited them)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.result, self.excluded_lines, self._resid_ax = None, [], None
        self.order_rows, self.order_traces, self._orders_source, self._flat_ax = None, [], None, None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        self.science = _FileRow(self.tr("Science frame"), self)
        self.flat = _FileRow(self.tr("Flat (orders and blaze)"), self)
        self.arc = _FileRow(self.tr("Arc lamp (ThAr)"), self)
        self.orientation = _Orientation(self)
        for w in (self.science, self.flat, self.arc, self.orientation):
            lay.addWidget(w)
        self.fibre = QCheckBox(self.tr("Fibre-fed: no sky between the orders"), self)
        self.fibre.setToolTip(
            self.tr(
                "Tick for a spectrograph fed by an optical fibre: there is no sky beside the orders, so "
                "none is subtracted"
            )
        )
        lay.addWidget(self.fibre)
        self.scatter = QCheckBox(self.tr("Subtract scattered light (fitted in the gaps between the orders)"), self)
        self.scatter.setToolTip(self.tr("As IRAF apscatter: for the science frame and the flat, before extraction"))
        lay.addWidget(self.scatter)
        grid = QGridLayout()
        self.first_order = QSpinBox(self)
        self.first_order.setRange(0, 1000)
        self.first_order.setSpecialValueText(self.tr("unknown"))
        self.first_order.setToolTip(
            self.tr(
                "Absolute order number of the lowest order in the image (from the spectrograph manual). "
                "If unknown: m = λ2 / (λ2 − λ1) with λ1, λ2 the wavelengths at the same pixel in two "
                "neighbouring orders (λ2 the longer)."
            )
        )
        self.direction = QComboBox(self)
        self.direction.addItems([self.tr("increase upwards"), self.tr("decrease upwards")])
        self.direction.setToolTip(
            self.tr(
                "Whether the absolute order number grows towards the top of the image or towards the bottom"
                " (red orders have lower numbers)"
            )
        )
        self.line_list = QComboBox(self)
        self.line_list.addItems(_line_lists())
        self.line_list.setCurrentText("thar")
        self.line_list.setToolTip(
            self.tr(
                "The gas of the arc lamp (ThAr for most echelles): after your identified lines, further "
                "lines of this list are found in every order"
            )
        )
        self.optimal = QCheckBox(self.tr("Optimal extraction (Horne)"), self)
        self.optimal.setChecked(True)
        self.optimal.setToolTip(
            self.tr(
                "Horne (1986): each pixel counts by the spectrum's profile and its noise; more signal-to-noise for "
                "faint spectra. Turn off for saturated or very bright spectra."
            )
        )
        self.order_view = QSpinBox(self)
        self.order_view.setRange(0, 0)
        self.order_view.valueChanged.connect(self._draw)
        self.order_view.setToolTip(
            self.tr(
                "Which extracted order to show in the plots (counted from the first one found, not the absolute number)"
            )
        )
        for r, (label, w) in enumerate(
            (
                (self.tr("Lowest order number"), self.first_order),
                (self.tr("Order numbers"), self.direction),
                (self.tr("Arc line list"), self.line_list),
                (self.tr("Show order (index)"), self.order_view),
            )
        ):
            grid.addWidget(QLabel(label, self), r, 0)
            grid.addWidget(w, r, 1)
        lay.addLayout(grid)
        lay.addWidget(self.optimal)
        self.find_button = QPushButton(self.tr("Show the orders on the flat (check, remove, add)"), self)
        self.find_button.setToolTip(
            self.tr(
                "Optional: the orders found automatically are drawn on the flat. Click a wrong trace to remove it, "
                "click on an order that was missed to add it. Without this step the orders are found automatically."
            )
        )
        self.find_button.clicked.connect(lambda: self._find_orders())
        lay.addWidget(self.find_button)
        self.extract_button = QPushButton(self.tr("1. Trace and extract orders"), self)
        self.extract_button.clicked.connect(lambda: self._run(False))
        self.extract_button.setToolTip(
            self.tr(
                "Traces the orders on the flat, extracts science and arc along them and divides by the "
                "flat's blaze; then identify arc lines"
            )
        )
        lay.addWidget(self.extract_button)
        lay.addWidget(
            QLabel(self.tr("2. Click arc lines (3+ per order, in 2+ orders) and type their wavelengths (Å):"), self)
        )
        self.guesses = QTableWidget(0, 3, self)
        self.guesses.setHorizontalHeaderLabels([self.tr("Order"), self.tr("Pixel"), self.tr("Wavelength (Å)")])
        self.guesses.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        track_typing(self, self.guesses, self.tr("type a wavelength"))
        lay.addWidget(self.guesses, 1)
        self.database_button = QPushButton(self.tr("Lines from an IRAF ecidentify database…"), self)
        self.database_button.setToolTip(
            self.tr(
                "Lines identified before on this spectrograph with IRAF ecidentify (database/ec…): placed on this "
                "arc's peaks after the common shift (as IRAF ecreidentify); they fill the table for you to check"
            )
        )
        self.database_button.clicked.connect(lambda: self.lines_from_database())
        lay.addWidget(self.database_button)
        row = QHBoxLayout()
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(lambda: self.edit(self.tr("clear the lines"), self.guesses.setRowCount, 0))
        clear.setToolTip(self.tr("Removes every identified line (Ctrl+Z brings them back)"))
        self.solve_button = QPushButton(self.tr("3. Solve, merge and save"), self)
        self.solve_button.clicked.connect(lambda: self._run(True))
        self.solve_button.setToolTip(
            self.tr(
                "One wavelength solution for all orders together (λ·m as a polynomial in pixel and order), "
                "then the orders are merged into one spectrum and saved"
            )
        )
        row.addWidget(clear)
        row.addWidget(self.solve_button)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.refit_button = QPushButton(self.tr("Refit without the left-out lines"), self)
        self.refit_button.setToolTip(
            self.tr("Click points in the residual plot (bottom) to leave those arc lines out, then refit")
        )
        self.refit_button.clicked.connect(lambda: self._run(True))
        forget = QPushButton(self.tr("Use all lines again"), self)
        forget.clicked.connect(lambda: self.edit(self.tr("use all lines again"), self.forget_excluded))
        forget.setToolTip(self.tr("Takes back every line left out in the residual plot"))
        row.addWidget(self.refit_button)
        row.addWidget(forget)
        lay.addLayout(row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._plot_clicked)
        split.addWidget(self.plot)
        split.setSizes([400, 800])
        QVBoxLayout(self).addWidget(split)

    def _orders(self):
        if self.first_order.value() == 0 or not self.result:
            return None
        step = 1 if self.direction.currentIndex() == 0 else -1
        return [self.first_order.value() + step * k for k in range(self.result["n_orders"])]

    def _guesses(self):
        out = []
        for r in range(self.guesses.rowCount()):
            try:
                out.append([float(self.guesses.item(r, c).text()) for c in range(3)])
            except (AttributeError, ValueError):
                continue
        return out

    def _run(self, solve):
        if not self.science.text():
            self.status.setText(self.tr("Choose a science frame."))
            return
        from ..spectroscopy.steps import spectrum_name

        inputs = {"science": self.science.text()}
        for key, row in (("flat", self.flat), ("arc", self.arc)):
            if row.text():
                inputs[key] = row.text()
        params = {
            "optimal": self.optimal.isChecked(),
            "line_list": self.line_list.currentText(),
            "order_step": 1 if self.direction.currentIndex() == 0 else -1,
            "sky": not self.fibre.isChecked(),
            "scatter": self.scatter.isChecked(),
            "exclude": [list(v) for v in self.excluded_lines],
        } | self.orientation.params()
        if self.first_order.value():
            params["first_order"] = self.first_order.value()
        if self.order_rows is not None and self._orders_source == self._order_image():
            params["rows"] = list(self.order_rows)  # the orders as checked on the flat
        if solve:
            g = self._guesses()
            if "arc" not in inputs or len(g) < 4 or len({x[0] for x in g}) < 2 or not self.first_order.value():
                self.status.setText(
                    self.tr("An arc, the lowest order number and at least four lines in two orders are needed.")
                )
                return
            inputs |= {"guesses": g, "output": str(Path(inputs["science"]).with_name(spectrum_name(inputs["science"])))}
        self.status.setText(self.tr("Working…"))
        self.reduce_requested.emit(inputs, params)

    def _order_image(self):
        return self.flat.text() or self.science.text()

    def _find_orders(self, rows=None):
        image = self._order_image()
        if not image:
            self.status.setText(self.tr("Choose a flat (or the science frame) first."))
            return
        params = self.orientation.params() | ({} if rows is None else {"rows": [float(r) for r in rows]})
        self.status.setText(self.tr("Tracing the orders…"))
        self.orders_requested.emit({"image": image}, params)

    def show_orders(self, o):
        """The traced orders drawn on the flat; clicks remove or add orders."""
        from ..spectroscopy.steps import _load

        self.order_rows, self.order_traces, self._orders_source = (
            list(o["rows"]),
            list(o["traces"]),
            self._order_image(),
        )
        self._order_nx = o["nx"]
        self._order_data = _load(self._orders_source, self.orientation.params())[0]
        self._draw_orders(o.get("failed") or [])

    def _draw_orders(self, failed=()):
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        d = self._order_data
        lo, hi = np.nanpercentile(d[:: max(1, d.shape[0] // 512), :: max(1, d.shape[1] // 512)], [1, 99.5])
        ax.imshow(d, origin="lower", cmap="gray", vmin=lo, vmax=hi, aspect="auto", interpolation="nearest")
        x = np.linspace(0, d.shape[1] - 1, 200)
        for c in self.order_traces:
            ax.plot(x, np.polyval(c, x), color="#3fb950", lw=0.8)
        for r in failed:
            ax.plot(self._order_nx / 2, r, "x", color="#e5484d", ms=10)
        ax.set_xlim(0, d.shape[1] - 1)
        ax.set_ylim(0, d.shape[0] - 1)
        ax.set_title(
            self.tr("{n} orders. Click a trace to remove it; click on a missed order to add it.").format(
                n=len(self.order_traces)
            ),
            fontsize=9,
        )
        self._flat_ax, self._arc_ax, self._resid_ax = ax, None, None
        self.plot.draw()
        text = self.tr("{n} orders traced.").format(n=len(self.order_traces))
        if failed:
            text += " " + self.tr("{k} could not be traced (red crosses) and are left out.").format(k=len(failed))
        self.status.setText(text)

    def _order_clicked(self, x, y):
        from ..spectroscopy.echelle import order_window, row_at_centre

        if self.order_traces:
            dist = [abs(np.polyval(c, x) - y) for c in self.order_traces]
            i = int(np.argmin(dist))
            if dist[i] < max(3.0, 0.5 * order_window(self.order_rows)):  # on a trace: remove that order
                self.edit(self.tr("remove an order"), self._remove_order, i)
                return
        new = row_at_centre(self.order_traces, x, y, self._order_nx)
        self._find_orders(sorted(self.order_rows + [new]))  # traced again in the worker, with the new order

    def state(self):
        return {
            "first_order": self.first_order.value(),
            "direction": self.direction.currentIndex(),
            "line_list": self.line_list.currentText(),
            "optimal": self.optimal.isChecked(),
            "fibre": self.fibre.isChecked(),
            "scatter": self.scatter.isChecked(),
            "orientation": self.orientation.state(),
        }

    def restore(self, st):
        self.first_order.setValue(int(st.get("first_order", 0)))
        self.direction.setCurrentIndex(int(st.get("direction", 0)))
        self.line_list.setCurrentText(st.get("line_list", "thar"))
        self.optimal.setChecked(bool(st.get("optimal", True)))
        self.fibre.setChecked(bool(st.get("fibre", False)))
        self.scatter.setChecked(bool(st.get("scatter", False)))
        self.orientation.restore(st.get("orientation", {}))

    def show_result(self, r):
        self.result = r
        self.order_view.setRange(0, max(0, r["n_orders"] - 1))
        self._draw()
        if r["solution"]:
            self.status.setText(
                self.tr("{k} orders merged; wavelength solution: {n} lines, rms {rms:.4f} Å. Saved: {path}").format(
                    k=r["n_orders"], n=r["solution"]["n_lines"], rms=r["solution"]["rms"], path=r.get("path", "—")
                )
            )
        else:
            self.status.setText(self.tr("{k} orders traced and extracted.").format(k=r["n_orders"]))

    def _draw(self):
        r = self.result
        if not r:
            return
        k = self.order_view.value()
        self.plot.figure.clear()
        self._flat_ax = None
        has_arc = r.get("arc") is not None
        lines = (r.get("solution") or {}).get("lines") or []
        axes = self.plot.figure.subplots(1 + has_arc + bool(lines), 1, squeeze=False)[:, 0]
        if r.get("merged"):
            axes[0].plot(r["merged"]["wave"], r["merged"]["flux"], lw=0.6)
            axes[0].set_xlabel(self.tr("Wavelength (Å)"))
        else:
            axes[0].plot(r["flux"][k], lw=0.6)
            axes[0].set_xlabel(self.tr("Pixel"))
        axes[0].set_ylabel(self.tr("Flux"))
        self._arc_ax = None
        if has_arc:
            axes[1].plot(r["arc"][k], lw=0.6, color="gray")
            for p in r["arc_peaks"][k]:
                axes[1].axvline(p, color="orange", lw=0.4)
            orders = self._orders()
            name = orders[k] if orders else k
            axes[1].set_xlabel(self.tr("Arc, order {m}: pixel (click a line to identify it)").format(m=name))
            self._arc_ax = axes[1]
        self._resid_ax = None
        if lines:  # the wavelength fit, line by line, as IRAF ecidentify shows it
            ax = axes[-1]
            a = np.asarray(lines, float)
            used = a[:, 4] > 0
            sc = ax.scatter(a[used, 1], a[used, 3] * 1000, c=a[used, 0], s=6, cmap="viridis")
            ax.plot(a[~used, 1], a[~used, 3] * 1000, "x", color="gray", ms=4, label=self.tr("rejected (3σ)"))
            ax.axhline(0, color="gray", lw=0.5)
            ax.set_xlabel(self.tr("Pixel (click a point to leave that arc line out)"))
            ax.set_ylabel(self.tr("Residual (mÅ)"))
            self.plot.figure.colorbar(sc, ax=ax, label=self.tr("Order"))
            self._resid_ax, self._resid_points = ax, a
        self.plot.draw()

    def lines_from_database(self, path=None):
        """Identifications from an IRAF ecidentify database, shifted onto this arc's peaks order by order."""
        from ..spectroscopy import reidentify

        orders = self._orders()
        if not self.result or not self.result.get("arc_peaks") or orders is None:
            self.status.setText(
                self.tr("Extract with an arc first and give the lowest order number: the database names orders.")
            )
            return None
        path = path or QFileDialog.getOpenFileName(self, self.tr("IRAF ecidentify database"), "", "*")[0]
        if not path:
            return None
        try:
            features = [f for rec in reidentify.read_database(path) for f in rec["features"] if "order" in f]
            if not features:
                raise ValueError(self.tr("no echelle orders in it (an identify database is for the Reduce tab)"))
            pooled = [p for k, peaks in enumerate(self.result["arc_peaks"]) for p in np.asarray(peaks) + 1e5 * k]
            index = {m: k for k, m in enumerate(orders)}
            mine = [f | {"pixel": f["pixel"] + 1e5 * index[f["order"]]} for f in features if f["order"] in index]
            shift, found = reidentify.shift_features(pooled, mine)
        except (OSError, ValueError, KeyError) as e:
            self.status.setText(
                self.tr("Cannot use {file}: {error}").format(file=Path(path).name, error=translate(str(e)))
            )
            return None
        rows = [[str(f["order"]), f"{p % 1e5:.2f}", f"{f['wave']:.4f}"] for p, f in found]
        self.edit(self.tr("lines from a database"), _set_rows, self.guesses, rows)
        self.status.setText(
            self.tr(
                "{m} of {n} lines found in this arc, shifted by {s:+.1f} px. Check them, delete wrong rows, then 3. "
                "Solve."
            ).format(m=len(rows), n=len(features), s=shift)
        )
        return rows

    def forget_excluded(self):
        self.excluded_lines = []
        self.status.setText(self.tr("All arc lines will be used again at the next fit."))

    def _plot_clicked(self, event):
        if self._flat_ax is not None and event.inaxes is self._flat_ax and event.xdata is not None:
            self._order_clicked(float(event.xdata), float(event.ydata))
            return
        if self._resid_ax is not None and event.inaxes is self._resid_ax:
            a = self._resid_points
            pix = self._resid_ax.transData.transform(np.column_stack([a[:, 1], a[:, 3] * 1000]))
            i = int(np.argmin(np.hypot(pix[:, 0] - event.x, pix[:, 1] - event.y)))
            line = [float(a[i, 0]), float(a[i, 1])]
            if line not in self.excluded_lines:
                self.edit(self.tr("leave out an arc line"), self.excluded_lines.append, line)
                self._resid_ax.plot(a[i, 1], a[i, 3] * 1000, "o", mfc="none", color="#e5484d", ms=9)
                self.plot.draw()
            self.status.setText(
                self.tr("{n} arc line(s) left out; press Refit without the left-out lines.").format(
                    n=len(self.excluded_lines)
                )
            )
            return
        if not self.result or self._arc_ax is None or event.inaxes is not self._arc_ax or event.xdata is None:
            return
        k = self.order_view.value()
        peaks = np.asarray(self.result["arc_peaks"][k])
        if peaks.size == 0:
            return
        p = float(peaks[np.argmin(np.abs(peaks - event.xdata))])
        orders = self._orders()
        self.edit(self.tr("identify a line"), self._add_line, [str(orders[k] if orders else ""), f"{p:.2f}", ""])
        self.guesses.editItem(self.guesses.item(self.guesses.rowCount() - 1, 2))

    def _add_line(self, row):
        _set_rows(self.guesses, _rows(self.guesses) + [row])

    def _remove_order(self, i):
        del self.order_rows[i], self.order_traces[i]
        self._draw_orders()

    def undo_state(self):
        return {
            "guesses": _rows(self.guesses),
            "excluded": [list(v) for v in self.excluded_lines],
            "rows": None if self.order_rows is None else [float(r) for r in self.order_rows],
            "traces": [[float(v) for v in c] for c in self.order_traces],
        }

    def set_undo_state(self, st):
        _set_rows(self.guesses, st["guesses"])
        self.excluded_lines = [list(v) for v in st["excluded"]]
        if st["rows"] != self.order_rows and st["rows"] is not None:
            self.order_rows, self.order_traces = list(st["rows"]), [np.array(c) for c in st["traces"]]
            if self._flat_ax is not None:
                self._draw_orders()


class TelluricTab(QWidget):
    """Divide out the atmosphere measured in a telluric standard star."""

    correct_requested = Signal(dict, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        spectra = FITS + ";;Text (*.txt *.dat *.csv)"
        self.spectrum = _FileRow(self.tr("Spectrum (1-D)"), self, spectra)
        self.standard = _FileRow(self.tr("Telluric standard (hot, fast-rotating star)"), self, spectra)
        lay.addWidget(self.spectrum)
        lay.addWidget(self.standard)
        lay.addWidget(
            QLabel(
                self.tr(
                    "The standard's spectrum gives the atmospheric transmission. Its strength (airmass, water "
                    "vapour) and a small wavelength shift are fitted inside the telluric bands."
                ),
                self,
                wordWrap=True,
            )
        )
        self.button = QPushButton(self.tr("Correct and save"), self)
        self.button.clicked.connect(self._run)
        self.button.setToolTip(
            self.tr(
                "Divides the spectrum by the standard's atmospheric lines, fitted in strength and shift, "
                "and saves the result next to the spectrum"
            )
        )
        lay.addWidget(self.button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        lay.addStretch(1)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([380, 820])
        QVBoxLayout(self).addWidget(split)

    def _run(self):
        if not (self.spectrum.text() and self.standard.text()):
            self.status.setText(self.tr("Choose the spectrum and the standard."))
            return
        src = Path(self.spectrum.text())
        out = src.with_name(src.stem + "_telluric.fits")
        self.status.setText(self.tr("Working…"))
        self.correct_requested.emit({"spectrum": str(src), "standard": self.standard.text(), "output": str(out)}, {})

    def show_result(self, r):
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1, sharex=True)
        ax.plot(r["wave"], r["flux"], lw=0.6, color="gray", label=self.tr("before"))
        ax.plot(r["wave"], r["corrected"], lw=0.6, label=self.tr("corrected"))
        ax.legend(loc="lower left")
        ax.set_ylabel(self.tr("Flux"))
        ax2.plot(r["wave"], r["transmission"], lw=0.6, color="tab:green")
        ax2.set_ylabel(self.tr("Transmission"))
        ax2.set_xlabel(self.tr("Wavelength (Å)"))
        self.plot.draw()
        self.status.setText(
            self.tr("Optical depth scale {s:.3f}, shift {v:.2f} km/s. Saved: {path}").format(
                s=r["power"], v=r["shift_kms"], path=r.get("path", "—")
            )
        )


class VelocityTab(QWidget):
    rv_requested = Signal(dict, dict)
    orbit_requested = Signal(dict, dict)
    classify_requested = Signal(str)  # spectrum
    disentangle_requested = Signal(dict, dict)  # inputs, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rvs = []
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(QLabel(self.tr("1-D spectra (FITS table, 1-D FITS with wavelength WCS, or text)"), self))
        self.files = QListWidget(self)
        lay.addWidget(self.files, 1)
        row = QHBoxLayout()
        add = QPushButton(self.tr("Add…"), self)
        add.clicked.connect(self._add)
        add.setToolTip(self.tr("Adds wavelength-calibrated 1-D spectra of the same star, one per night or exposure"))
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(self.files.clear)
        clear.setToolTip(self.tr("Empties the list of spectra"))
        row.addWidget(add)
        row.addWidget(clear)
        lay.addLayout(row)
        self.template = _FileRow(self.tr("Template"), self, FITS + ";;Text (*.txt *.dat *.csv)")
        lay.addWidget(self.template)
        self.template2 = _FileRow(
            self.tr("Second template (double-lined binary, optional)"), self, FITS + ";;Text (*.txt *.dat *.csv)"
        )
        lay.addWidget(self.template2)
        grid = QGridLayout()
        self.coord = QLineEdit(self)
        self.coord.setPlaceholderText(self.tr("from the header if empty"))
        self.coord.setToolTip(self.tr("Needed for the barycentric correction; empty: taken from the header"))
        self.v_min, self.v_max = _spin(self, -300, -3000, 3000), _spin(self, 300, -3000, 3000)
        self.v_max.setToolTip(
            self.tr(
                "Velocities searched (km/s): wide enough for the star's motion and orbit; narrower is "
                "faster and safer from false peaks"
            )
        )
        self.v_min.setToolTip(
            self.tr(
                "Velocities searched (km/s): wide enough for the star's motion and orbit; narrower is "
                "faster and safer from false peaks"
            )
        )
        self.w_min, self.w_max = _spin(self, 0, 0, 30000), _spin(self, 0, 0, 30000)
        self.w_max.setToolTip(
            self.tr(
                "Only this wavelength range is used: leave out telluric bands, broad Balmer lines and noisy"
                " ends; 0 and 0: everything"
            )
        )
        self.w_min.setToolTip(
            self.tr(
                "Only this wavelength range is used: leave out telluric bands, broad Balmer lines and noisy"
                " ends; 0 and 0: everything"
            )
        )
        self.period = _spin(self, 0, 0, 100000, 6)
        self.period.setToolTip(self.tr("Starting value for the orbit fit (days); 0: searched from the velocities"))
        self.method = QComboBox(self)
        for text, data in (
            (self.tr("Cross-correlation (TODCOR with a second template)"), ("ccf", 1)),
            (self.tr("Broadening function, one star (fast rotators)"), ("bf", 1)),
            (self.tr("Broadening function, two stars (contact binaries)"), ("bf", 2)),
        ):
            self.method.addItem(text, data)
        self.method.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.method.setMinimumContentsLength(24)  # long choices do not widen the page; the list shows them whole
        self.method.setToolTip(
            self.tr(
                "Cross-correlation for most stars (with a second template: both stars of a double-lined "
                "binary, TODCOR); broadening function for fast rotators and contact binaries"
            )
        )
        for r, (label, w) in enumerate(
            (
                (self.tr("Method"), self.method),
                (self.tr("Target RA Dec"), self.coord),
                (self.tr("Velocity range from (km/s)"), self.v_min),
                (self.tr("to (km/s)"), self.v_max),
                (self.tr("Wavelengths from (Å, 0 = all)"), self.w_min),
                (self.tr("to (Å, 0 = all)"), self.w_max),
                (self.tr("Period guess (d)"), self.period),
            )
        ):
            grid.addWidget(QLabel(label, self), r, 0)
            grid.addWidget(w, r, 1)
        lay.addLayout(grid)
        self.type_button = QPushButton(self.tr("Spectral type of the first spectrum (and a template)"), self)
        self.type_button.setToolTip(
            self.tr(
                "MK type against the MK standard stars of Gray & Corbally (as MKCLASS; 3800–5600 Å, both downloaded "
                "once), ranked with scores; and the closest of the Pickles library's 131 stars becomes the template"
            )
        )
        self.type_button.clicked.connect(self._classify)
        lay.addWidget(self.type_button)
        self.rv_button = QPushButton(self.tr("Measure radial velocities"), self)
        self.rv_button.clicked.connect(self._measure)
        self.rv_button.setToolTip(
            self.tr("Velocity of every spectrum against the template, corrected to the barycentre, with its error")
        )
        self.orbit_button = QPushButton(self.tr("Fit orbit"), self)
        self.orbit_button.setEnabled(False)
        self.orbit_button.clicked.connect(self._orbit)
        self.orbit_button.setToolTip(
            self.tr(
                "Fits a Keplerian orbit to the velocities: period, eccentricity, K, γ (both stars for a "
                "double-lined binary)"
            )
        )
        lay.addWidget(self.rv_button)
        lay.addWidget(self.orbit_button)
        from .export import results_button

        self.orbit_result = None
        lay.addWidget(results_button(self, self.orbit_table))
        self.separate_button = QPushButton(self.tr("Separate the two stars' spectra (disentangling)"), self)
        self.separate_button.setEnabled(False)
        self.separate_button.clicked.connect(lambda: self.separate())
        self.separate_button.setToolTip(
            self.tr(
                "With the two stars' velocities in every spectrum, finds each star's own spectrum "
                "(disentangling); needs spectra at many orbital phases"
            )
        )
        lay.addWidget(self.separate_button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status)
        split.addWidget(left)
        right = QSplitter(Qt.Vertical, self)
        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("File"),
                "BJD_TDB",
                self.tr("RV (km/s)"),
                self.tr("Error"),
                self.tr("RV 2 (km/s)"),
                self.tr("Error 2"),
                self.tr("Barycentric corr."),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.table)
        self.plot = PlotCanvas(self)
        right.addWidget(self.plot)
        right.setSizes([220, 500])
        split.addWidget(right)
        split.setSizes([400, 800])
        QVBoxLayout(self).addWidget(split)

    def _add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Add spectra"), "", FITS + ";;Text (*.txt *.dat *.csv)")
        self.add_files(paths)

    def add_files(self, paths):
        """Spectra for the velocities, each once (a reduced spectrum is added on its own, then often again)."""
        have = {self.files.item(i).text() for i in range(self.files.count())}
        self.files.addItems([p for p in paths if p not in have])

    def _measure(self):
        spectra = [self.files.item(i).text() for i in range(self.files.count())]
        if not spectra or not self.template.text():
            self.status.setText(self.tr("Add spectra and choose a template."))
            return
        inputs = {"spectra": spectra, "template": self.template.text()}
        if self.template2.text():
            inputs["template2"] = self.template2.text()
        if self.coord.text().strip():
            inputs["coord"] = self.coord.text().strip()
        params = {
            "v_min": self.v_min.value(),
            "v_max": self.v_max.value(),
            "wave_min": self.w_min.value() or None,
            "wave_max": self.w_max.value() or None,
        }
        params["method"], params["components"] = self.method.currentData()
        self.status.setText(self.tr("Measuring…"))
        self.rv_requested.emit(inputs, params)

    def _classify(self):
        if not self.files.count():
            self.status.setText(self.tr("Add spectra and choose a template."))
            return
        self.status.setText(self.tr("Comparing with the template library…"))
        self.classify_requested.emit(self.files.item(0).text())

    def show_classes(self, classes, mk=None, mk_note=None, mk_model=None, classes_note=None):
        """The MK type from the MK standards (a ranked suggestion with scores) and the template for the velocities
        (the closest library spectrum, which also covers the red). The star is drawn over the best standard, so the
        user judges the suggestion with their own eyes, as MK classification is done."""
        if not classes and not mk:
            self.status.setText(
                self.tr("No library spectrum covers these wavelengths.")
                + (" " + translate(classes_note) if classes_note else "")
            )
            return
        lines = []
        if mk:
            ranked = ", ".join(f"{c['type']} ({c['score']:.4f})" for c in mk[:4])
            lines.append(
                self.tr(
                    "MK type against the MK standard stars (Gray & Corbally's libnor36, 3800–5600 Å; smaller is "
                    "better): {t}. A suggestion: check the spectrum against the standards before using it."
                ).format(t=ranked)
            )
        elif mk_note:
            lines.append(self.tr("No MK type: {why}.").format(why=translate(mk_note)))
        if classes:
            best = ", ".join(f"{c['type']} ({c['rms']:.3f})" for c in classes[:3])
            lines.append(
                self.tr("Closest library spectra (Pickles): {t}. The best one is now the template.").format(t=best)
            )
            self.template.edit.setText(classes[0]["template"])
        elif classes_note:
            lines.append(
                self.tr("The template library could not be fetched ({why}): choose a template yourself.").format(
                    why=translate(classes_note)
                )
            )
        self.status.setText("\n".join(lines))
        if mk and mk_model:
            self.plot.figure.clear()
            ax = self.plot.figure.add_subplot()
            ax.plot(mk_model["wave"], mk_model["star"], lw=0.8, color="k", label=self.tr("this star"))
            star = np.asarray(mk_model["star"], float)
            model = np.asarray(mk_model["model"], float)
            model = np.where(np.isfinite(star) & (model > 0), model, np.nan)  # only where both have data
            ax.plot(mk_model["wave"], model, lw=0.8, color="C3", label=mk[0]["type"])
            ax.set_xlabel(self.tr("Wavelength (Å)"))
            ax.set_ylabel(self.tr("Relative flux"))
            ax.set_title(self.tr("The star over the best MK standard"), fontsize="medium")
            ax.legend(loc="lower right", fontsize="small")
            self.plot.draw()

    def separate(self, folder=None):
        """Disentangle with the velocities measured on these spectra (observed frame) and their light ratio."""
        folder = folder or QFileDialog.getExistingDirectory(self, self.tr("Folder for the two spectra"))
        if not folder:
            return
        spectra = [self.files.item(i).text() for i in range(self.files.count())]
        by_name = {Path(s).name: s for s in spectra}
        rows = [r for r in self.rvs if r["file"] in by_name]
        inputs = {
            "spectra": [by_name[r["file"]] for r in rows],
            "rv1": [r["rv_obs"] for r in rows],
            "rv2": [r["rv2_obs"] for r in rows],
            "output_dir": folder,
        }
        ratios = [r["flux_ratio"] for r in rows if r.get("flux_ratio")]
        if ratios:
            inputs["light_ratio"] = float(np.median(ratios))
        self.status.setText(self.tr("Separating the two spectra…"))
        self.disentangle_requested.emit(inputs, {})

    def show_components(self, c):
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.plot(c["wave"], c["star1"], lw=0.7, label=self.tr("Star 1"))
        ax.plot(c["wave"], np.asarray(c["star2"]) - 0.5, lw=0.7, label=self.tr("Star 2 (shifted down by 0.5)"))
        ax.set_xlabel(self.tr("Wavelength (Å)"))
        ax.set_ylabel(self.tr("Flux"))
        ax.legend(fontsize="small")
        self.plot.draw()
        self.status.setText(self.tr("Written: {a} and {b}").format(a=c["paths"][0], b=c["paths"][1]))

    def show_rvs(self, rows, skipped=None):
        self.rvs = rows
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            v = row["rv"] if row["rv"] is not None else row["rv_obs"]
            v2 = row.get("rv2") if row.get("rv2") is not None else row.get("rv2_obs")
            values = (
                row["file"],
                f"{row['bjd']:.5f}" if row["bjd"] else "—",
                f"{v:.3f}",
                f"{row['rv_err']:.3f}",
                "—" if v2 is None else f"{v2:.3f}",
                "—" if v2 is None else f"{row['rv2_err']:.3f}",
                f"{row['v_corr']:.3f}" if row["v_corr"] is not None else self.tr("not applied"),
            )
            for c, text in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(text))
        usable = [r for r in rows if r["bjd"]]
        self.orbit_button.setEnabled(len(usable) >= 6)
        self.separate_button.setEnabled(self._is_sb2() and len(rows) >= 4)
        widths = [
            self.tr("v sin i = {v:.1f} km/s").format(v=np.median([r[k] for r in rows]))
            for k in ("vsini", "vsini2")
            if rows and all(r.get(k) is not None for r in rows)
        ]
        sites = {
            (round(r["site"]["lat"], 3), round(r["site"]["lon"], 3), r["site"]["from"]) for r in rows if r.get("site")
        }
        where = [
            (self.tr("site from the Plan page") if src == "plan" else self.tr("site from the file header"))
            + f" ({lat:+.3f}°, {lon:+.3f}°)"
            for lat, lon, src in sorted(sites)
        ]
        self.status.setText(
            self.tr("{n} velocities.").format(n=len(rows))
            + "".join(" " + w for w in widths)
            + (" " + self.tr("Barycentric correction for: {w}.").format(w="; ".join(where)) if where else "")
            + (
                " "
                + self.tr(
                    "{n} spectra are already barycentric (SPECSYS or HELIO in the header): not corrected again."
                ).format(n=sum(bool(r.get("already_barycentric")) for r in rows))
                if any(r.get("already_barycentric") for r in rows)
                else ""
            )
            + (
                " " + self.tr("The template was smoothed to the spectra's resolution (it is much finer).")
                if any(r.get("template_matched") for r in rows)
                else ""
            )
            + (
                " " + self.tr("Vacuum wavelengths converted to air (VACUUM in the header).")
                if any(r.get("vacuum_to_air") for r in rows)
                else ""
            )
            + "".join(
                " "
                + self.tr("{file} left out: it covers {a:.0f}–{b:.0f} Å, outside the chosen wavelengths.").format(
                    file=k["file"], a=k["from"], b=k["to"]
                )
                for k in skipped or []
            )
            + (
                ""
                if all(r["v_corr"] is not None for r in rows)
                else " "
                + self.tr("Barycentric correction needs the time, the target position and the site (Plan page).")
            )
        )

    def _series(self, component=1):
        rows = [r for r in self.rvs if r["bjd"]]
        t = [r["bjd"] for r in rows]
        if component == 2:
            v = [r["rv2"] if r.get("rv2") is not None else r.get("rv2_obs") for r in rows]
            return t, v, [r.get("rv2_err") for r in rows]
        v = [r["rv"] if r["rv"] is not None else r["rv_obs"] for r in rows]
        return t, v, [r["rv_err"] for r in rows]

    def _is_sb2(self):
        return bool(self.rvs) and all(r.get("rv2_obs") is not None for r in self.rvs)

    def _orbit(self):
        if not self.period.value():
            self.status.setText(self.tr("Give a period guess (e.g. from the period search)."))
            return
        t, v, e = self._series()
        inputs = {"time": t, "rv": v, "error": e}
        if self._is_sb2():
            _, v2, e2 = self._series(2)
            inputs |= {"rv2": v2, "error2": e2}
        self.orbit_requested.emit(inputs, {"period": self.period.value()})

    def orbit_table(self):
        """(rows, caption) of the fitted orbit for the results export."""
        o = self.orbit_result
        if not o:
            self.status.setText(self.tr("Fit an orbit first."))
            return None
        rows = [
            ("P", o["period"], o["period_err"] or None, "d"),
            ("T_peri", o["t_peri"], o["t_peri_err"], "BJD_TDB"),
            ("e", o["e"], o["e_err"], ""),
            ("omega", o["omega"], o["omega_err"], "deg"),
            ("K1", o["k"], o["k_err"], "km/s"),
            ("gamma", o["gamma"], o["gamma_err"], "km/s"),
        ]
        if "k2" in o:
            rows += [
                ("K2", o["k2"], o["k2_err"], "km/s"),
                ("q = M2/M1", o["q"], o["q_err"], ""),
                ("M1 sin^3 i", o["m1_sin3i"], o["m1_sin3i_err"], "Msun"),
                ("M2 sin^3 i", o["m2_sin3i"], o["m2_sin3i_err"], "Msun"),
                ("a sin i", o["a_sini_rsun"], o["a_sini_err"], "Rsun"),
                ("rms (primary)", o["rms"], None, "km/s"),
                ("rms (secondary)", o["rms2"], None, "km/s"),
            ]
        else:
            rows += [
                ("f(m)", o["mass_function"], None, "Msun"),
                ("a1 sin i", o["a_sini_rsun"], None, "Rsun"),
                ("rms", o["rms"], None, "km/s"),
            ]
        caption = self.tr(
            "Spectroscopic orbit: Keplerian least-squares fit to {n} radial velocities; 1σ errors from the "
            "covariance matrix (e and ω from its draws)."
        ).format(n=len(self._series()[0]))
        return rows, caption

    def show_orbit(self, o):
        from ..spectroscopy.orbit import rv_model

        self.orbit_result = o

        t, v, e = (np.asarray(a, float) for a in self._series())
        text = self.tr(
            "P = {p:.6f} ± {pe:.6f} d, e = {e:.3f} ± {ee:.3f}, ω = {w:.1f} ± {we:.1f}°, "
            "K = {k:.3f} ± {ke:.3f} km/s, γ = {g:.3f} ± {ge:.3f} km/s, rms = {rms:.3f} km/s"
        ).format(
            p=o["period"],
            pe=o["period_err"],
            e=o["e"],
            ee=o["e_err"],
            w=o["omega"],
            we=o["omega_err"],
            k=o["k"],
            ke=o["k_err"],
            g=o["gamma"],
            ge=o["gamma_err"],
            rms=o["rms"],
        )
        if "k2" in o:
            text += "\n" + self.tr(
                "K2 = {k2:.3f} ± {k2e:.3f} km/s, q = M2/M1 = {q:.4f} ± {qe:.4f}, "
                "M1 sin³i = {m1:.4f} ± {m1e:.4f} M☉, M2 sin³i = {m2:.4f} ± {m2e:.4f} M☉, "
                "a sin i = {a:.3f} ± {ae:.3f} R☉, rms 2 = {rms2:.3f} km/s"
            ).format(
                k2=o["k2"],
                k2e=o["k2_err"],
                q=o["q"],
                qe=o["q_err"],
                m1=o["m1_sin3i"],
                m1e=o["m1_sin3i_err"],
                m2=o["m2_sin3i"],
                m2e=o["m2_sin3i_err"],
                a=o["a_sini_rsun"],
                ae=o["a_sini_err"],
                rms2=o["rms2"],
            )
        else:
            text += ", " + self.tr("f(m) = {fm:.4g} M☉, a sin i = {a:.3f} R☉").format(
                fm=o["mass_function"], a=o["a_sini_rsun"]
            )
        self.status.setText(text)
        phase = ((t - o["t_peri"]) / o["period"]) % 1
        ph = np.linspace(0, 1, 400)
        model = rv_model(
            o["t_peri"] + ph * o["period"], o["period"], o["t_peri"], o["e"], o["omega"], o["k"], o["gamma"]
        )
        self.plot.figure.clear()
        # velocities with the orbit above, residuals below (the usual figure of an orbit paper)
        ax, res = self.plot.figure.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": (3, 1), "hspace": 0})
        args = (o["period"], o["t_peri"], o["e"])
        ax.axhline(o["gamma"], color="0.5", lw=0.6, ls=":")
        ax.errorbar(phase, v, e, fmt="o", ms=4, label=self.tr("primary"))
        ax.plot(ph, model, "r-", lw=1)
        res.errorbar(phase, v - rv_model(t, *args, o["omega"], o["k"], o["gamma"]), e, fmt="o", ms=3)
        if "k2" in o:
            t2, v2, e2 = (np.asarray(a, float) for a in self._series(2))
            model2 = rv_model(o["t_peri"] + ph * o["period"], *args, o["omega"] + 180, o["k2"], o["gamma"])
            phase2 = ((t2 - o["t_peri"]) / o["period"]) % 1
            ax.errorbar(phase2, v2, e2, fmt="s", ms=4, color="tab:orange", label=self.tr("secondary"))
            ax.plot(ph, model2, "-", color="tab:orange", lw=1)
            resid2 = v2 - rv_model(t2, *args, o["omega"] + 180, o["k2"], o["gamma"])
            res.errorbar(phase2, resid2, e2, fmt="s", ms=3, color="tab:orange")
            ax.legend(fontsize="small")
        res.axhline(0, color="0.5", lw=0.6)
        res.set_ylabel(self.tr("O−C (km/s)"))
        res.set_xlabel(self.tr("Phase (from periastron)"))
        res.set_xlim(0, 1)
        ax.set_ylabel(self.tr("RV (km/s)"))
        self.plot.draw()


class CubeTab(QWidget):
    """IFU data cubes: images over a wavelength window or continuum-subtracted line maps; click a
    spaxel for its spectrum, save it for the radial-velocity tools."""

    spectrum_saved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        from .viewer import ImageViewer

        self.data = self.wave = self.header = None
        self.spectrum = None
        split = QSplitter(Qt.Horizontal, self)
        self.viewer = ImageViewer(self)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.set_pick(True)  # clicks pick a point: a cross, not the hand; dragging still pans
        split.addWidget(self.viewer)
        side = QWidget(self)
        lay = QVBoxLayout(side)
        self.file = _FileRow(self.tr("Data cube"), self)
        self.file.edit.editingFinished.connect(lambda: self.open(self.file.text()))
        lay.addWidget(self.file)
        load = QPushButton(self.tr("Load cube"), self)
        load.clicked.connect(lambda: self.open(self.file.text()))
        load.setToolTip(
            self.tr("Opens a 3-D cube (two sky axes and wavelength), e.g. from MUSE or another integral-field unit")
        )
        lay.addWidget(load)
        self.info = QLabel(self)
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        grid = QGridLayout()
        self.mode = QComboBox(self)
        self.mode.addItems([self.tr("Mean over a wavelength window"), self.tr("Line map (continuum subtracted)")])
        self.mode.setToolTip(
            self.tr(
                "Mean: the picture in a wavelength window; line map: the same with the continuum on both "
                "sides subtracted, to show where a line shines"
            )
        )
        self.centre, self.width = _spin(self, 6563, 1, 300000, 2), _spin(self, 10, 0.01, 100000, 2)
        self.radius = _spin(self, 1.5, 0.5, 50, 1)
        self.radius.setToolTip(self.tr("A click sums the spectra of the spaxels within this radius"))
        self.width.setToolTip(self.tr("Width of the wavelength window"))
        self.centre.setToolTip(self.tr("Centre of the wavelength window, e.g. 6563 for Hα"))
        for r, (label, w) in enumerate(
            (
                (self.tr("Image"), self.mode),
                (self.tr("Centre (Å)"), self.centre),
                (self.tr("Width (Å)"), self.width),
                (self.tr("Spaxel aperture radius (px)"), self.radius),
            )
        ):
            grid.addWidget(QLabel(label, self), r, 0)
            grid.addWidget(w, r, 1)
        lay.addLayout(grid)
        show = QPushButton(self.tr("Show image"), self)
        show.clicked.connect(self.show_image)
        show.setToolTip(self.tr("Draws the image of the chosen window; click on it to see a spectrum"))
        lay.addWidget(show)
        self.save_button = QPushButton(self.tr("Save spectrum…"), self)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        self.save_button.setToolTip(self.tr("Saves the spectrum of the clicked spaxels as a 1-D FITS file"))
        lay.addWidget(self.save_button)
        self.status = QLabel(self.tr("Click a spaxel to see its spectrum."), self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.plot = PlotCanvas(self)
        lay.addWidget(self.plot, 1)
        split.addWidget(side)
        split.setSizes([700, 500])
        QVBoxLayout(self).addWidget(split)

    def open(self, path):
        from ..spectroscopy import cube

        if not path:
            return
        try:  # shortcut: the cube is read into memory; very large cubes (> RAM) need memory-mapped slices
            self.data, self.wave, self.header = cube.read_cube(path)
        except Exception as e:  # not a cube: say so, keep the tab usable
            self.status.setText(self.tr("Cannot open: {e}").format(e=translate(e)))
            return
        self.cube_path = path
        nw, ny, nx = self.data.shape
        self.info.setText(
            self.tr("{nx} × {ny} spaxels, {nw} wavelengths {lo:.1f}–{hi:.1f} Å").format(
                nx=nx, ny=ny, nw=nw, lo=self.wave.min(), hi=self.wave.max()
            )
        )
        self.centre.setValue(float(np.median(self.wave)))
        self.width.setValue(float(np.ptp(self.wave) / 2))
        self.mode.setCurrentIndex(0)
        self.show_image()

    def show_image(self):
        from ..spectroscopy import cube

        if self.data is None:
            return
        c, w = self.centre.value(), self.width.value()
        if self.mode.currentIndex() == 0:
            img = cube.image(self.data, self.wave, c - w / 2, c + w / 2)
        else:
            img = cube.line_map(self.data, self.wave, c, w)
        self.viewer.set_image(np.nan_to_num(img, nan=float(np.nanmin(img)) if np.isfinite(img).any() else 0.0))

    def _clicked(self, x, y):
        from ..spectroscopy import cube

        if self.data is None:
            return
        self.spectrum = (x, y, cube.spaxel_spectrum(self.data, x, y, self.radius.value()))
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.plot(self.wave, self.spectrum[2], lw=0.7)
        ax.set_xlabel(self.tr("Wavelength (Å)"))
        ax.set_ylabel(self.tr("Flux"))
        ax.set_title(self.tr("Spaxel {x:.0f}, {y:.0f}").format(x=x, y=y), fontsize=9)
        self.plot.draw()
        self.save_button.setEnabled(True)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save spectrum"), "", "FITS (*.fits)")
        if path:
            self.save_spectrum(path)

    def save_spectrum(self, path):
        from ..spectroscopy import spectrum_io

        x, y, flux = self.spectrum
        h = self.header.copy()
        for k in [k for k in h if k.endswith("3") or k.startswith(("NAXIS", "CTYPE", "CRVAL", "CRPIX", "CDELT", "CD"))]:
            h.remove(k, ignore_missing=True, remove_all=True)
        h["SPAXELX"], h["SPAXELY"], h["APRADIUS"] = round(float(x), 2), round(float(y), 2), self.radius.value()
        out = spectrum_io.write(path, self.wave, flux, np.full(len(flux), np.nan), h)
        self.status.setText(self.tr("Saved: {p}").format(p=out))
        self.spectrum_saved.emit(str(out))
        return out


class SpectroscopyPage(QWidget):
    """Tabs for each job, and named instrument profiles (orientation, apertures, line list, orders)."""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("spectroscopy")
        self.tabs = QTabWidget(self)
        self.reduce_tab = ReduceTab(self)
        self.echelle_tab = EchelleTab(self)
        self.telluric_tab = TelluricTab(self)
        self.velocity_tab = VelocityTab(self)
        self.cube_tab = CubeTab(self)
        self.cube_tab.spectrum_saved.connect(self.velocity_tab.files.addItem)
        self.tabs.addTab(self.reduce_tab, self.tr("Reduce"))
        self.tabs.addTab(self.echelle_tab, self.tr("Echelle"))
        self.tabs.addTab(self.telluric_tab, self.tr("Telluric"))
        self.tabs.addTab(self.velocity_tab, self.tr("Radial velocity && orbit"))
        self.tabs.addTab(self.cube_tab, self.tr("IFU cube"))
        from .spectrum_tools import SpectrumToolsTab

        self.tools_tab = SpectrumToolsTab(self)
        self.tabs.addTab(self.tools_tab, self.tr("Spectrum tools"))
        self.tabs.setDocumentMode(True)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(self.tr("Instrument profile"), self))
        self.profile = QComboBox(self)
        self.profile.setMinimumWidth(200)
        self.profile.activated.connect(lambda _: self.apply_profile(self.profile.currentText()))
        self.profile.setToolTip(
            self.tr(
                "Saved settings of a spectrograph (orientation, widths, line list, order numbers…): choose "
                "one to fill the Reduce and Echelle tabs"
            )
        )
        save = QPushButton(self.tr("Save as…"), self)
        save.clicked.connect(self._save_profile)
        save.setToolTip(
            self.tr(
                "Saves the present settings of the Reduce and Echelle tabs under a name, for the next night"
                " with this spectrograph"
            )
        )
        delete = QPushButton(self.tr("Delete"), self)
        delete.clicked.connect(self._delete_profile)
        delete.setToolTip(self.tr("Deletes the chosen instrument profile"))
        for w in (self.profile, save, delete):
            bar.addWidget(w)
        bar.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.tabs, 1)
        self._fill_profiles()

    def _profiles(self):
        return dict(self.settings.get("spectroscopy.profiles", {})) if self.settings else {}

    def _fill_profiles(self):
        self.profile.clear()
        self.profile.addItems(sorted(self._profiles()))

    def save_profile(self, name):
        if not self.settings or not name:
            return
        profiles = self._profiles()
        profiles[name] = {"reduce": self.reduce_tab.state(), "echelle": self.echelle_tab.state()}
        self.settings.set("spectroscopy.profiles", profiles)
        self.settings.save()
        self._fill_profiles()
        self.profile.setCurrentText(name)

    def apply_profile(self, name):
        p = self._profiles().get(name)
        if p:
            self.reduce_tab.restore(p.get("reduce", {}))
            self.echelle_tab.restore(p.get("echelle", {}))

    def _save_profile(self):
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, self.tr("Instrument profile"), self.tr("Name (e.g. telescope + spectrograph):")
        )
        if ok:
            self.save_profile(name.strip())

    def _delete_profile(self):
        profiles = self._profiles()
        profiles.pop(self.profile.currentText(), None)
        if self.settings:
            self.settings.set("spectroscopy.profiles", profiles)
            self.settings.save()
        self._fill_profiles()
