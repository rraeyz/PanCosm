"""The Photometry page: stars, apertures, light curve, minimum and export."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .messages import translate
from .undo import Undoable
from .viewer import ImageViewer
from .widgets import Collapsible, PlotCanvas, StepGuide, _title


class PhotometryPage(Undoable, QWidget):
    """Pick target and comparison stars on the first image, measure, plot, time the minimum."""

    measure_requested = Signal(list, list, list, str, dict)  # images, target_xy, comps_xy, coord, params
    suggest_requested = Signal(list, list, dict)  # images, target_xy, params
    minimum_requested = Signal(dict, dict)  # light curve, params
    live_updated = Signal()
    polarimetry_requested = Signal(list, list, list, dict)  # images, o_xy, e_xy, params
    quality_requested = Signal(list)  # images
    catalog_requested = Signal(dict, dict)  # inputs, params
    apertures_requested = Signal(list, list, list)  # images, target_xy, comps_xy
    field_requested = Signal(str)  # the first frame: solved against Gaia, its variable stars named
    next_requested = Signal(str, str)  # the page to go on to ("timeseries" / "orbits"), the light curve file or ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.images, self.target, self.comps, self.light_curve = [], None, [], None
        self.ref, self.shown, self.skipped = None, 0, set()  # the frame the stars are marked on, the one shown, unused
        self.extras, self.lc_raw, self.detrend_cfg = [], None, None  # extras: [((x, y), "target" | "check")]
        self.excluded, self._frame_ids, self._plotted = set(), [], None  # frames deleted by hand
        self.comp_off, self._comp_scatter = (
            set(),
            {},
        )  # comparison stars left out of the ensemble (0-based), C_k scatter
        self._radii_set = False  # the radii chosen from the profiles (or by hand) for the step titles
        self.field = None  # what is in the first frame (photometry.identify_field): solution, VSX variables, OBJECT
        self.live, self.live_folder, self.live_seen, self._live_busy = None, None, set(), False
        # the image above the light curve on the left, the controls the whole height on the right: a light-curve
        # band across the page squeezed the controls into a strip whose buttons were only found by scrolling
        split = QSplitter(Qt.Vertical, self)
        self._split = split
        self.viewer = ImageViewer(self)
        self.viewer.empty_hint = self.tr("No images yet: press Choose images… in step 1, or drop the frames here")
        self.viewer.clicked.connect(self._clicked)
        self.viewer.rings_wheel.connect(self._rings_wheel)
        split.addWidget(self.viewer)
        from PySide6.QtWidgets import QScrollArea

        side_box = QWidget(self)
        side = QVBoxLayout(side_box)
        side.addWidget(_title(self.tr("Photometry"), self))
        self.guide = StepGuide(
            [
                (
                    self.tr("Choose the calibrated images (Calibration window)"),
                    self.tr("Choose images… — the calibrated frames of the night (bias, dark and flat taken off)."),
                ),
                (
                    self.tr("Find the bad frames: clouds, focus, trails (optional)"),
                    self.tr("Find the bad frames, look at the red ones in the list and leave them out."),
                ),
                (
                    self.tr("Mark the target, then the comparison stars (IRAF phot coordinates)"),
                    self.tr(
                        "The star the files name is marked as the target when it is in the field (else click it); "
                        "the comparison stars and the radii then follow on their own. A click on a marked star "
                        "takes it off, a click elsewhere adds one."
                    ),
                ),
                (
                    self.tr("Choose the aperture and the sky annulus (phot apertures, annulus)"),
                    self.tr("Press Choose the radii from the star profiles, or type the radii yourself."),
                ),
                (
                    self.tr("Measure the light curve (phot, differential photometry)"),
                    self.tr("Press Measure light curve."),
                ),
                (
                    self.tr("Check the curve, then time of minimum, export or AAVSO report"),
                    self.tr(
                        "Click points that are clearly bad (clouds, a cosmic ray) to delete them, detrend against "
                        "airmass if needed; then Time of minimum, Export CSV or the AAVSO report; Period search "
                        "and O−C → or Fit an eclipse or transit model → for the next page."
                    ),
                ),
            ],
            self,
        )
        side.addWidget(self.guide)
        # the controls in four numbered steps: the step being worked on is open, the ones done fold with a tick;
        # every one opens with a click (a guide, never a lock); the owner found one long column of 19 buttons
        # "amateurish"
        self.sections = [Collapsible("", self, expanded=k == 0, mode=None) for k in range(4)]
        self._step_now = 0
        self.load_button = QPushButton(self.tr("Choose images…"), self)
        self.load_button.clicked.connect(self._choose_images)
        self.load_button.setToolTip(
            self.tr(
                "The calibrated frames of one field (FITS, also TESS / Kepler target pixel files); they are"
                " sorted by time"
            )
        )
        self.sections[0].body.addWidget(self.load_button)
        self.images_label = QLabel(self.tr("No images"), self)
        self.images_label.setWordWrap(True)
        self.sections[0].body.addWidget(self.images_label)
        # what is in the field: the owner's files named a star 48 deg away, and nothing said so
        self.field_label = QLabel(self)
        self.field_label.setWordWrap(True)
        self.field_label.setToolTip(
            self.tr(
                "The first frame is solved against the Gaia catalogue (no plate solver to install; it needs the "
                "pointing and the pixel scale in the header and an internet connection), and the known variable "
                "stars in it are named (AAVSO VSX)"
            )
        )
        self.sections[0].body.addWidget(self.field_label)
        row = QHBoxLayout()
        self.variables = QComboBox(self)
        self.variables.setToolTip(
            self.tr(
                "Known variable stars in this field (AAVSO VSX), brightest first. The one chosen here is named on the "
                "image; point at any cyan ring for its name"
            )
        )
        self.variables.currentIndexChanged.connect(lambda *_: self._draw_markers() if self.field else None)
        self.make_target = QPushButton(self.tr("Make it the target"), self)
        self.make_target.setToolTip(
            self.tr(
                "Marks this star as the target T1 on the first frame and takes its catalogue position for the "
                "barycentric times (BJD)"
            )
        )
        self.make_target.clicked.connect(self._variable_as_target)
        row.addWidget(self.variables, 1)
        row.addWidget(self.make_target)
        self.sections[0].body.addLayout(row)
        for w in (self.field_label, self.variables, self.make_target):
            w.hide()
        # every frame can be looked at, marked on, or left out (the owner: "I only see one picture")
        browse = QHBoxLayout()
        self.prev_frame, self.next_frame = QToolButton(self), QToolButton(self)
        self.prev_frame.setArrowType(Qt.LeftArrow)
        self.next_frame.setArrowType(Qt.RightArrow)
        self.prev_frame.setToolTip(self.tr("Previous frame (in time)"))
        self.next_frame.setToolTip(self.tr("Next frame (in time)"))
        self.frame_slider = QSlider(Qt.Horizontal, self)
        self.frame_slider.setToolTip(self.tr("Go through the frames of the series"))
        self.prev_frame.clicked.connect(lambda: self.frame_slider.setValue(self.frame_slider.value() - 1))
        self.next_frame.clicked.connect(lambda: self.frame_slider.setValue(self.frame_slider.value() + 1))
        self.frame_slider.valueChanged.connect(self.show_frame)
        for w in (self.prev_frame, self.frame_slider, self.next_frame):
            browse.addWidget(w, 1 if w is self.frame_slider else 0)
        self.sections[0].body.addLayout(browse)
        self.frame_label = QLabel(self)
        self.frame_label.setWordWrap(True)
        self.sections[0].body.addWidget(self.frame_label)
        self.use_frame = QCheckBox(self.tr("Use this frame"), self)
        self.use_frame.setToolTip(
            self.tr("Untick to leave this frame out of the light curve (clouds, a satellite trail, a bad focus)")
        )
        self.use_frame.toggled.connect(self._use_frame)
        self.sections[0].body.addWidget(self.use_frame)
        # every frame in a list, as MaxIm DL shows them: click one to see it, untick to leave it out
        self.frame_table = QTableWidget(0, 4, self)
        self.frame_table.setHorizontalHeaderLabels([self.tr("Frame"), self.tr("Time (UTC)"), "FWHM", self.tr("Sky")])
        self.frame_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.frame_table.horizontalHeader().setStretchLastSection(True)
        self.frame_table.verticalHeader().setDefaultSectionSize(20)
        self.frame_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.frame_table.setSelectionMode(QTableWidget.SingleSelection)
        self.frame_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.frame_table.setMinimumHeight(110)
        self.frame_table.setMaximumHeight(200)
        self.frame_table.setToolTip(
            self.tr(
                "Every frame of the series: click one to show it, untick it to leave it out. FWHM and sky are filled "
                "by “Find the bad frames”; bad frames are red."
            )
        )
        self.frame_table.currentCellChanged.connect(
            lambda row, *_: self.frame_slider.setValue(row) if row >= 0 else None
        )
        self.frame_table.itemChanged.connect(self._frame_checked)
        self.sections[0].body.addWidget(self.frame_table)
        self.blink = QPushButton(self.tr("Blink"), self)
        self.blink.setCheckable(True)
        self.blink.setToolTip(
            self.tr(
                "Shows the frames used one after the other (about 2 a second): a passing cloud, a satellite trail, a "
                "jump in the pointing or a missing star catches the eye at once. Click again to stop."
            )
        )
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(450)
        self._blink_timer.timeout.connect(self._blink_step)
        self.blink.toggled.connect(lambda on: self._blink_timer.start() if on else self._blink_timer.stop())
        self.sections[0].body.addWidget(self.blink)
        for w in (self.prev_frame, self.frame_slider, self.next_frame, self.use_frame, self.blink):
            w.setEnabled(False)
        self.quality_button = QPushButton(self.tr("Find the bad frames (clouds, focus, trails)"), self)
        self.quality_button.setToolTip(
            self.tr(
                "Optional, before measuring: measures every frame's star size (FWHM), sky brightness and number of "
                "stars, and names the frames far from the night's usual values (passing clouds, lost focus or "
                "tracking, twilight). You then choose to leave them out; nothing is removed by itself."
            )
        )
        self.quality_button.setEnabled(False)
        self.quality_button.clicked.connect(lambda: self.quality_requested.emit(self._series()))
        self.sections[0].body.addWidget(self.quality_button)
        self.drop_bad = QPushButton(self.tr("Leave out the bad frames"), self)
        self.drop_bad.hide()
        self.drop_bad.clicked.connect(self._drop_bad)
        self.drop_bad.setToolTip(
            self.tr("Takes the frames the quality check marked as bad out of the list; the files stay on disk")
        )
        self.sections[0].body.addWidget(self.drop_bad)
        side.addWidget(self.sections[0])
        hint = QLabel(
            self.tr("Click the target star, then one or more comparison stars. A click on a marked star takes it off."),
            self,
        )
        hint.setWordWrap(True)
        self.sections[1].body.addWidget(hint)
        role_row = QHBoxLayout()
        role_row.addWidget(QLabel(self.tr("Clicks add:"), self))
        self.click_role = QComboBox(self)
        self.click_role.addItem(self.tr("target, then comparison stars"), "auto")
        self.click_role.addItem(self.tr("check stars"), "check")
        self.click_role.addItem(self.tr("more targets"), "target")
        self.click_role.currentIndexChanged.connect(lambda *_: self._draw_markers())
        self.click_role.setToolTip(
            self.tr("Check stars and further targets are measured against the same comparison stars, not used in them")
        )
        role_row.addWidget(self.click_role, 1)
        self.sections[1].body.addLayout(role_row)
        clear = QPushButton(self.tr("Clear stars"), self)
        clear.clicked.connect(lambda: self.edit(self.tr("clear the stars"), self._clear))
        clear.setToolTip(self.tr("Takes off every marked star (Ctrl+Z brings them back)"))
        self.sections[1].body.addWidget(clear)
        self.suggest_button = QPushButton(self.tr("Suggest comparison stars"), self)
        self.suggest_button.setEnabled(False)
        self.suggest_button.setToolTip(
            self.tr("Similar brightness, not saturated, no bright neighbour, inside the frame in every image")
        )
        self.suggest_button.clicked.connect(lambda: self._suggest(auto=False))
        self.sections[1].body.addWidget(self.suggest_button)
        side.addWidget(self.sections[1])
        grid = QGridLayout()
        self.r_ap, self.r_in, self.r_out = (self._spin(v) for v in (4.0, 10.0, 16.0))
        self.r_out.setToolTip(
            self.tr("Outer edge of the sky ring; the ring should hold several times as many pixels as the aperture")
        )
        self.r_in.setToolTip(
            self.tr(
                "The sky is measured in a ring around the star starting at this radius, where the star's "
                "light has ended (at least 3 FWHM)"
            )
        )
        self.r_ap.setToolTip(
            self.tr(
                "Radius of the circle in which the star's light is added up; about 1 to 2 times the FWHM "
                "gives the best signal-to-noise"
            )
        )
        for row, (label, w) in enumerate(
            (
                (self.tr("Ring 1 — the star's light inside (px)"), self.r_ap),
                (self.tr("Ring 2 — the sky starts (px)"), self.r_in),
                (self.tr("Ring 3 — the sky ends (px)"), self.r_out),
            )
        ):
            grid.addWidget(QLabel(label, self), row, 0)
            grid.addWidget(w, row, 1)
        self.sections[2].body.addLayout(grid)
        rings_note = QLabel(
            self.tr(
                "Radii in image pixels: the rings grow with the zoom. Between rings 1 and 2 nothing is measured "
                "(the star's faint wings); between 2 and 3 the sky. Shift + mouse wheel on the image makes them "
                "larger or smaller."
            ),
            self,
        )
        rings_note.setWordWrap(True)
        self.sections[2].body.addWidget(rings_note)
        self.apertures_button = QPushButton(self.tr("Choose the radii from the star profiles"), self)
        self.apertures_button.setToolTip(
            self.tr(
                "Measures the stars' FWHM; aperture = best signal-to-noise (1–3 FWHM), sky from where the star's "
                "light has ended (at least 3 FWHM) with four times as many pixels as the aperture"
            )
        )
        self.apertures_button.setEnabled(False)
        self.apertures_button.clicked.connect(self._choose_radii)
        self.sections[2].body.addWidget(self.apertures_button)
        side.addWidget(self.sections[2])
        self.follow_seeing = QCheckBox(self.tr("Radii follow the seeing (scaled by each frame's FWHM)"), self)
        self.follow_seeing.setToolTip(
            self.tr(
                "Each frame's radii are scaled by its FWHM over the first frame's, so the aperture holds "
                "the same part of the light when the seeing changes during the night. In a crowded field a changing "
                "aperture can add trends of its own: measure once with fixed radii too and compare"
            )
        )
        self.measure_options = Collapsible(self.tr("More measuring options: seeing, PSF, scintillation"), self)
        self.measure_options.body.addWidget(self.follow_seeing)
        self.psf = QCheckBox(self.tr("PSF photometry (crowded fields: blended stars fitted together)"), self)
        self.psf.setToolTip(
            self.tr(
                "For crowded fields: stars that overlap are fitted together with the image's star profile "
                "instead of being added up in a circle. Slower; for isolated stars the aperture is as good."
            )
        )
        self.measure_options.body.addWidget(self.psf)
        self.sections[3].body.addWidget(QLabel(self.tr("Target RA Dec (for BJD), e.g. 02:04:10.3 +46:41:16"), self))
        self.coord = QLineEdit(self)
        self.coord.setToolTip(
            self.tr(
                "Needed to turn the times into BJD (barycentric). Empty: taken from the header (OBJCTRA / "
                "OBJCTDEC or RA / DEC)."
            )
        )
        self.sections[3].body.addWidget(self.coord)
        tel = QHBoxLayout()
        tel.addWidget(QLabel(self.tr("Telescope aperture (m)"), self))
        self.telescope_d = QDoubleSpinBox(self)
        self.telescope_d.setRange(0.0, 50.0)
        self.telescope_d.setDecimals(3)
        self.telescope_d.setSingleStep(0.05)
        self.telescope_d.setSpecialValueText(self.tr("from the header"))
        self.telescope_d.setToolTip(
            self.tr(
                "For the scintillation noise in the error bars (Osborn et al. 2015). 0: APTDIA from the header; "
                "without it, scintillation is not included"
            )
        )
        tel.addWidget(self.telescope_d)
        self.measure_options.body.addLayout(tel)
        self.sections[3].body.addWidget(self.measure_options)
        self.measure_button = QPushButton(self.tr("Measure light curve"), self)
        self.measure_button.setEnabled(False)
        self.measure_button.clicked.connect(self._measure)
        self.measure_button.setToolTip(
            self.tr(
                "Measures the marked stars in every image and draws the differential light curve (target "
                "against the comparison stars)"
            )
        )
        self.sections[3].body.addWidget(self.measure_button)
        side.addWidget(self.sections[3])
        self.live_button = QPushButton(self.tr("Live: follow a folder during the night…"), self)
        self.live_button.setCheckable(True)
        self.live_button.setToolTip(
            self.tr(
                "Each new frame in the folder is calibrated (optional masters) and measured as it arrives; "
                "the light curve grows on its own."
            )
        )
        self.live_button.toggled.connect(self._toggle_live)
        # rarely used tools: out of the main steps, one click away (PLAN 4.8 item 16)
        self.other_tools = Collapsible(self.tr("Other tools: live light curve, polarimetry"), self)
        self.other_tools.body.addWidget(self.live_button)
        self.pol_button = QPushButton(self.tr("Polarimetry (dual beam)"), self)
        self.pol_button.setToolTip(
            self.tr(
                "Click the ordinary image of the star as target and its extraordinary image as the first "
                "comparison; the half-wave-plate angle is read from the header."
            )
        )
        self.pol_button.clicked.connect(self._polarimetry)
        self.other_tools.body.addWidget(self.pol_button)
        side.addWidget(self.other_tools)
        self._step_titles()
        side.addStretch(1)
        scroll = QScrollArea(self)  # small screens: the panel scrolls instead of pushing the window taller
        scroll.setWidget(side_box)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(side_box.sizeHint().width() + 20)
        self._steps_scroll = scroll

        bottom = QWidget(self)
        b_lay = QHBoxLayout(bottom)
        self.plot = PlotCanvas(bottom)
        left = QVBoxLayout()  # the plot and, under it, what was measured (scatter, warnings)
        left.addWidget(self.plot, 1)
        b_lay.addLayout(left, 1)
        res = QVBoxLayout()
        self.res_tabs = QTabWidget(self)
        # stars: roles, typed-in comparison magnitudes, weights
        stars_tab = QWidget(self)
        sl = QVBoxLayout(stars_tab)
        self.star_table = QTableWidget(0, 6, self)
        self.star_table.setHorizontalHeaderLabels(
            [self.tr("Star"), self.tr("Role"), "x", "y", self.tr("Known magnitude"), self.tr("Scatter (mmag)")]
        )
        self.star_table.horizontalHeader().setStretchLastSection(True)
        for col in (0, 1, 2, 3, 4, 5):  # every header readable; the table scrolls sideways if narrow
            self.star_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.star_table.verticalHeader().hide()
        self.star_table.setToolTip(
            self.tr(
                "Untick a comparison star to leave it out of the ensemble: the light curve and the scatters change at "
                "once (Ctrl+Z brings it back). Scatter: each comparison star against the others, in mmag; the "
                "largest is the one to look at. Type the comparison stars' magnitudes (from a chart or catalogue) to "
                "get the target's magnitude."
            )
        )
        self.star_table.itemChanged.connect(self._star_item_changed)
        sl.addWidget(self.star_table, 1)
        self.weighted = QCheckBox(self.tr("Weight comparison stars by their scatter"), self)
        self.weighted.setToolTip(
            self.tr("Each comparison star is measured against the others; noisy or variable ones count less")
        )
        self.weighted.toggled.connect(lambda *_: self._recompute())
        sl.addWidget(self.weighted)
        self.res_tabs.addTab(stars_tab, self.tr("Stars"))
        # plot and detrending
        plot_tab = QWidget(self)
        pl = QVBoxLayout(plot_tab)
        self.show_what = QComboBox(self)
        self.show_what.setPlaceholderText(self.tr("Measure a light curve to choose what to plot"))
        self.show_what.setEnabled(False)
        self.show_what.currentIndexChanged.connect(lambda *_: self._plot_current())
        self.show_what.setToolTip(
            self.tr(
                "Which curve to draw: the target against the comparison stars, the checks, the comparison "
                "stars against each other, sky, FWHM, airmass…"
            )
        )
        pl.addWidget(self.show_what)
        edit_row = QHBoxLayout()
        self.delete_mode = QCheckBox(self.tr("Click a point to delete it"), self)
        self.delete_mode.setToolTip(
            self.tr("For a bad frame (cloud, satellite, wrong star): it is left out of every result, export included")
        )
        edit_row.addWidget(self.delete_mode)
        restore = QPushButton(self.tr("Restore deleted points"), self)
        restore.clicked.connect(self.restore_points)
        restore.setToolTip(self.tr("Brings back every point deleted by clicking"))
        edit_row.addWidget(restore)
        pl.addLayout(edit_row)
        space_row = QHBoxLayout()
        space_row.addWidget(QLabel(self.tr("Spacing between curves"), self))
        self.spacing = QDoubleSpinBox(self)
        self.spacing.setRange(0.0, 2.0)
        self.spacing.setSingleStep(0.01)
        self.spacing.setDecimals(3)
        self.spacing.setValue(0.05)
        self.spacing.setToolTip(self.tr("For the views with several curves; 0 puts them on top of each other"))
        self.spacing.valueChanged.connect(lambda *_: self._plot_current())
        space_row.addWidget(self.spacing)
        pl.addLayout(space_row)
        pl.addWidget(QLabel(self.tr("Detrend against:"), self))
        trend_row = QGridLayout()
        self.trend_boxes = {}
        names = {
            "airmass": self.tr("airmass"),
            "fwhm": self.tr("FWHM"),
            "sky": self.tr("sky"),
            "x": "x",
            "y": "y",
            "time": self.tr("time"),
        }
        trend_tips = {
            "airmass": self.tr("Extinction: the stars change with their height above the horizon"),
            "fwhm": self.tr("Seeing: larger star images lose more light outside the aperture"),
            "sky": self.tr("Sky brightness: twilight, moonlight, thin cloud"),
            "x": self.tr("Position on the chip: the stars drift over pixels of different sensitivity"),
            "y": self.tr("Position on the chip: the stars drift over pixels of different sensitivity"),
            "time": self.tr("A slow change with time"),
        }
        for i, (key, text) in enumerate(names.items()):
            box = QCheckBox(text, self)
            box.setToolTip(trend_tips[key])
            self.trend_boxes[key] = box
            trend_row.addWidget(box, i // 3, i % 3)
        pl.addLayout(trend_row)
        from PySide6.QtWidgets import QSpinBox

        deg_row = QHBoxLayout()
        self.trend_degree = QSpinBox(self)
        self.trend_degree.setRange(1, 3)
        self.trend_degree.setToolTip(self.tr("1: linear; 2 or 3: curved trends (a polynomial in each quantity)"))
        deg_row.addWidget(QLabel(self.tr("Trend degree"), self))
        deg_row.addWidget(self.trend_degree)
        deg_row.addStretch(1)
        pl.addLayout(deg_row)
        ex_row = QHBoxLayout()
        ex_row.addWidget(QLabel(self.tr("Leave out from"), self))
        self.exclude_from = QLineEdit(self)
        self.exclude_to = QLineEdit(self)
        for w in (self.exclude_from, self.exclude_to):
            w.setPlaceholderText(self.tr("time"))
            w.setToolTip(
                self.tr(
                    "Points in this time range (the eclipse or transit itself) are left out of the trend fit, "
                    "then corrected with it"
                )
            )
        ex_row.addWidget(self.exclude_from)
        ex_row.addWidget(QLabel(self.tr("to"), self))
        ex_row.addWidget(self.exclude_to)
        pl.addLayout(ex_row)
        d_row = QHBoxLayout()
        self.detrend_button = QPushButton(self.tr("Detrend"), self)
        self.detrend_button.setToolTip(
            self.tr("Fits ln(flux) linearly in the ticked quantities on the points outside the left-out range")
        )
        self.detrend_button.clicked.connect(self._detrend)
        self.undo_detrend = QPushButton(self.tr("Undo detrending"), self)
        self.undo_detrend.clicked.connect(lambda: self._set_detrend(None))
        self.undo_detrend.setToolTip(self.tr("Back to the light curve before detrending"))
        d_row.addWidget(self.detrend_button)
        d_row.addWidget(self.undo_detrend)
        pl.addLayout(d_row)
        pl.addStretch(1)
        self.res_tabs.addTab(plot_tab, self.tr("Plot"))
        # minimum
        min_tab = QWidget(self)
        ml = QVBoxLayout(min_tab)
        grid = QGridLayout()
        self.t0 = QLineEdit(self)
        self.t0.setPlaceholderText(self.tr("optional"))
        self.period = QLineEdit(self)
        self.period.setPlaceholderText(self.tr("optional"))
        grid.addWidget(QLabel(self.tr("Ephemeris T0 (BJD)"), self), 0, 0)
        grid.addWidget(self.t0, 0, 1)
        grid.addWidget(QLabel(self.tr("Period (d)"), self), 1, 0)
        grid.addWidget(self.period, 1, 1)
        ml.addLayout(grid)
        self.period.setToolTip(self.tr("Optional: with T0 and the period the minimum gets its cycle number and O−C"))
        self.t0.setToolTip(self.tr("Optional: with T0 and the period the minimum gets its cycle number and O−C"))
        from PySide6.QtWidgets import QButtonGroup, QGroupBox

        method_box = QGroupBox(self.tr("What kind of minimum is it?"), self)
        mb = QVBoxLayout(method_box)
        self.kvw = QRadioButton(self.tr("Eclipsing binary: Kwee–van Woerden method"), self)
        self.kvw.setToolTip(
            self.tr(
                "Kwee & van Woerden (1956), the standard method for minima of eclipsing binaries and the times "
                "collected in O−C databases: the time about which the descending and ascending branches are most "
                "symmetric, with its error"
            )
        )
        self.trapezoid = QRadioButton(self.tr("Exoplanet transit: trapezoid fit"), self)
        self.trapezoid.setToolTip(
            self.tr(
                "A trapezoid (ingress, flat bottom, egress) fitted to the dip: mid-transit time with its error, "
                "depth and duration, as the ExoClock and ETD projects use"
            )
        )
        self.kvw.setChecked(True)
        group = QButtonGroup(method_box)
        for b in (self.kvw, self.trapezoid):
            group.addButton(b)
            mb.addWidget(b)
        note = QLabel(
            self.tr(
                "Choose by what you observe: a V-shaped or rounded minimum of a binary star, or the flat-bottomed "
                "dip of a planet passing in front of its star."
            ),
            self,
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        mb.addWidget(note)
        ml.addWidget(method_box)
        self.minimum_button = QPushButton(self.tr("Time of minimum"), self)
        self.minimum_button.setEnabled(False)
        self.minimum_button.clicked.connect(self._minimum)
        self.minimum_button.setToolTip(
            self.tr(
                "Time of minimum of the curve shown, with its error (every minimum if the night holds more than one)"
            )
        )
        ml.addWidget(self.minimum_button)
        ml.addStretch(1)
        self.res_tabs.addTab(min_tab, self.tr("Minimum"))
        # export and standard magnitudes
        out_tab = QWidget(self)
        ol = QVBoxLayout(out_tab)
        self.export_button = QPushButton(self.tr("Export CSV…"), self)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        self.export_button.setToolTip(
            self.tr("Time, flux, magnitude and error of every star as a table for a spreadsheet or another program")
        )
        ol.addWidget(self.export_button)
        row = QHBoxLayout()
        self.band = QComboBox(self)
        self.band.addItems(("V", "B", "R", "I", "G", "SG", "SR", "SI", "CV"))
        self.band.setToolTip(self.tr("Filter of the images (CV: unfiltered, reduced to V)"))
        self.catalog_button = QPushButton(self.tr("Standard magnitudes (APASS / Gaia)"), self)
        self.catalog_button.setToolTip(
            self.tr(
                "Looks up the comparison stars in APASS and Gaia (needs the internet and a plate-solved first "
                "image) and turns the light curve into magnitudes in the standard system"
            )
        )
        self.catalog_button.setEnabled(False)
        self.catalog_button.clicked.connect(self._catalog)
        row.addWidget(self.band)
        row.addWidget(self.catalog_button, 1)
        ol.addLayout(row)
        self.catalog = None
        self.aavso_button = QPushButton(self.tr("Export AAVSO report…"), self)
        self.aavso_button.setEnabled(False)
        self.aavso_button.clicked.connect(self._export_aavso)
        self.aavso_button.setToolTip(
            self.tr(
                "A report in AAVSO's Extended File Format to submit through WebObs; the comparison stars' "
                "magnitudes are asked for"
            )
        )
        ol.addWidget(self.aavso_button)
        ol.addStretch(1)
        self.res_tabs.addTab(out_tab, self.tr("Export"))
        res.addWidget(self.res_tabs, 1)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # under the plot (the star table keeps the column's height, I6b (2)); a long text scrolls past four lines
        result_box = QScrollArea(self)
        result_box.setWidget(self.result)
        result_box.setWidgetResizable(True)
        result_box.setFrameShape(QScrollArea.NoFrame)
        result_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        result_box.setMaximumHeight(4 * self.result.fontMetrics().lineSpacing() + 6)
        left.addWidget(result_box)
        # photometry only measures; the fits are in the next windows — say so where the result appears
        self.next_box = QWidget(self)
        nb = QVBoxLayout(self.next_box)
        nb.setContentsMargins(0, 0, 0, 0)
        # what comes next is in the buttons' tooltips: a paragraph here left the star table one row (I6b (2))
        go_period = QPushButton(self.tr("Period search →"), self)
        go_period.setToolTip(
            self.tr(
                "Opens Light curves and period, which already has this light curve; times of minimum timed here go "
                "to the O−C window by themselves. Photometry only measures"
            )
        )
        go_period.clicked.connect(lambda: self.next_requested.emit("timeseries", ""))
        go_model = QPushButton(self.tr("Fit an eclipse or transit model →"), self)
        go_model.setToolTip(
            self.tr(
                "Saves the light curve as a CSV file and opens it in the Models window: a physical model of an "
                "eclipsing binary or a transit (formulas: Guide, Mathematics of the methods)"
            )
        )
        go_model.clicked.connect(self._to_models)
        nb.addWidget(go_period)
        nb.addWidget(go_model)
        self.next_box.setVisible(False)
        res.addWidget(self.next_box)
        widest = max(self.res_tabs.widget(i).minimumSizeHint().width() for i in range(self.res_tabs.count()))
        self.res_tabs.setMinimumWidth(widest + 30)  # scrolling only up and down: never cut a control's text
        self._next_buttons = (go_period, go_model)
        self.next_box.installEventFilter(self)  # side by side when they fit: a row more for the star table
        for i in range(self.res_tabs.count()):  # a tab's controls scroll rather than take the image's height
            text, inner = self.res_tabs.tabText(i), self.res_tabs.widget(i)
            box = QScrollArea(self)
            box.setWidgetResizable(True)
            box.setFrameShape(QScrollArea.NoFrame)
            box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.res_tabs.removeTab(i)
            box.setWidget(inner)
            self.res_tabs.insertTab(i, box, text)
        self.res_tabs.setCurrentIndex(0)
        b_lay.addLayout(res, 1)
        split.addWidget(bottom)
        self._lower = bottom  # the light curve and the star table: shown once a star is marked
        bottom.setVisible(False)
        page = QSplitter(Qt.Horizontal, self)
        page.addWidget(split)
        page.addWidget(scroll)
        page.setStretchFactor(0, 1)
        page.setStretchFactor(1, 0)
        page.setChildrenCollapsible(False)
        QVBoxLayout(self).addWidget(page)

    def _polarimetry(self):
        if not (self.images and self.target and self.comps):
            self.result.setText(self.tr("Click the ordinary and the extraordinary image of the star first."))
            return
        params = {"r_ap": self.r_ap.value(), "r_in": self.r_in.value(), "r_out": self.r_out.value()}
        self.result.setText(self.tr("Measuring…"))
        self.polarimetry_requested.emit(self._series(), list(self.target), list(self.comps[0]), params)

    def show_polarimetry(self, r):
        self.result.setText(
            self.tr(
                "q = {q:.5f} ± {qe:.5f}, u = {u:.5f} ± {ue:.5f}, P = {p:.3f} ± {pe:.3f} % "
                "(debiased {p0:.3f} %), θ = {t:.1f} ± {te:.1f}°; {n} frames, angles: {src}"
            ).format(
                q=r["q"],
                qe=r["q_err"],
                u=r["u"],
                ue=r["u_err"],
                p=100 * r["p"],
                pe=100 * r["p_err"],
                p0=100 * r["p_debiased"],
                t=r["theta"],
                te=r["theta_err"],
                n=r["n"],
                src=r["angle_source"],
            )
        )

    # --- live -------------------------------------------------------------
    def _toggle_live(self, on):
        if not on:
            self.stop_live()
            return
        folder = QFileDialog.getExistingDirectory(self, self.tr("Folder the camera writes to"))
        if not folder:
            self.live_button.setChecked(False)
            return
        masters, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Master bias / dark / flat (optional; Cancel for none)"), folder, "FITS (*.fits *.fit *.fts)"
        )
        self.start_live(folder, masters)

    def start_live(self, folder, masters=()):
        """Follow folder. Without stars yet, the first frame is shown to click them; press Live again."""
        from ..photometry import live

        if not (self.target and self.comps):
            first = live.ready_files(folder, set(), min_age_s=0)
            if first:
                self.set_images(first[:1])
            self.result.setText(self.tr("Click the target and comparison stars on the first frame, then start Live."))
            self.live_button.setChecked(False)
            return False
        self.live = live.LiveLightCurve(
            self.target,
            self.comps,
            self.r_ap.value(),
            self.r_in.value(),
            self.r_out.value(),
            self.coord.text().strip() or None,
            masters=live.load_masters(masters),
        )
        self.live_folder, self.live_seen = folder, set()
        self.live_updated.connect(self._live_show)
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self.poll_live)
        self._live_timer.start(3000)
        self.result.setText(self.tr("Live: waiting for frames in {f}").format(f=folder))
        self.poll_live()
        return True

    def stop_live(self):
        if getattr(self, "_live_timer", None):
            self._live_timer.stop()
            self._live_timer = None
            try:
                self.live_updated.disconnect(self._live_show)
            except RuntimeError:
                pass

    def poll_live(self):
        """Measure the frames that arrived since the last poll, in a background thread."""
        import threading

        from ..photometry import live

        if self.live is None or self._live_busy:
            return
        new = live.ready_files(self.live_folder, self.live_seen)
        if not new:
            return
        self._live_busy = True

        def work(session=self.live):
            try:
                for p in new:
                    self.live_seen.add(p)
                    session.add(p)
            finally:
                self._live_busy = False
                try:
                    self.live_updated.emit()
                except RuntimeError:  # page closed meanwhile
                    pass

        threading.Thread(target=work, daemon=True).start()

    def _live_show(self):
        if self.live and self.live.points:
            self.show_light_curve(self.live.light_curve())
            if self.live.failed:
                self.result.setText(
                    self.result.text() + " " + self.tr("{n} frames skipped.").format(n=len(self.live.failed))
                )

    def _spin(self, value):
        w = QDoubleSpinBox(self)
        w.setRange(0.5, 200)
        w.setSingleStep(0.5)
        w.setValue(value)
        w.valueChanged.connect(self._draw_markers)
        return w

    def _choose_images(self):
        from .files import images_filter

        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Choose images"), "", images_filter())
        if paths:
            self.set_images(paths)

    def set_images(self, paths):
        self.guide.set_state(0, "done" if paths else None)
        from .. import timing
        from ..io.bayer import fits_paths
        from ..io.fits import read_image

        paths = fits_paths(paths)  # camera raw files and pictures get a FITS copy every tool can read

        self.quality_button.setEnabled(True)
        self._frame_jd = {}  # mid-exposure UTC of every frame, read once here for the frame list
        self.images = timing.chronological(paths, self._frame_jd)
        self.ref, self.shown, self.skipped = None, 0, set()
        data, header, _ = read_image(self.images[0])
        self.viewer.set_image(data)
        self.frame_slider.blockSignals(True)
        self.frame_slider.setRange(0, len(self.images) - 1)
        self.frame_slider.setValue(0)
        self.frame_slider.blockSignals(False)
        for w in (self.prev_frame, self.frame_slider, self.next_frame, self.use_frame, self.blink):
            w.setEnabled(True)
        self.quality = []
        self._fill_frames()
        self._frame_text(header)
        sky = None
        try:
            from ..photometry.lightcurve import target_coord

            sky = target_coord(header)
        except Exception:  # header position unreadable: the user types it
            pass
        if sky is not None and not self.coord.text():
            self.coord.setText(sky.to_string("hmsdms", sep=":", precision=1))
        self.field = None
        for w in (self.variables, self.make_target):
            w.hide()
        if "TPFSKIP" in header or sky is None:  # a pixel file, or no pointing to solve from: nothing to identify
            self.field_label.hide()
        else:
            self.field_label.setText(self.tr("Identifying the field (Gaia, VSX)…"))
            self.field_label.show()
            self.field_requested.emit(self.images[0])
        self._step_now = 0
        self._advance(1)
        text = self.tr("{n} images, first: {name}").format(n=len(self.images), name=Path(self.images[0]).name)
        if "TPFSKIP" in header:  # a TESS / Kepler file: say what was left out, the user may want them back
            text += "\n" + self.tr(
                "Target pixel file: {n} cadences left out (no time, or flagged as useless by the mission)."
            ).format(n=header["TPFSKIP"])
        if "DATE-CAM" in header:  # a phone or camera picture: its time is the camera clock, often local time
            text += "\n" + self.tr(
                "Times: camera clock − {h} h. A camera on local time needs DSLR clock − UTC in the Calibration window."
            ).format(h=f"{header.get('CLKOFFS', 0):g}")
        self.images_label.setText(text)
        self._clear()
        self.undo_stack.clear()  # stars marked on other frames: their history goes with them

    def undo_state(self):
        return {
            "target": self.target,
            "ref": self.ref,
            "comps": list(self.comps),
            "extras": list(self.extras),
            "excluded": sorted(self.excluded),
            "detrend": self.detrend_cfg,
            "comp_off": sorted(self.comp_off),
        }

    def set_undo_state(self, st):
        self.target, self.comps, self.extras = st["target"], list(st["comps"]), list(st["extras"])
        self.ref = st.get("ref")
        self._draw_markers()
        off = set(st.get("comp_off", ()))
        if (set(st["excluded"]), st["detrend"], off) != (self.excluded, self.detrend_cfg, self.comp_off):
            self.excluded, self.detrend_cfg, self.comp_off = set(st["excluded"]), st["detrend"], off
            self._fill_star_table()
            if self.lc_raw is not None:
                self._recompute()

    def _clicked(self, x, y):
        self.edit(self.tr("mark or unmark a star"), self._mark, x, y)

    def _mark(self, x, y):
        if self._star_names() and self.ref not in (None, self.shown):
            self.result.setText(
                self.tr(
                    "The stars are marked on frame {k}: go back to it to change them, or Clear stars to mark them on "
                    "this frame."
                ).format(k=self.ref + 1)
            )
            return
        if not self._star_names():
            self.ref = self.shown  # positions are taken on this frame; the measurement carries them to the others
        near = [xy for _, _, xy in self._star_names() if (xy[0] - x) ** 2 + (xy[1] - y) ** 2 <= self.r_ap.value() ** 2]
        if near:  # a click on a marked star takes it off again, instead of marking it twice
            xy = near[0]
            self.target = None if self.target == xy else self.target
            self.comps = [c for c in self.comps if c != xy]
            self.extras = [e for e in self.extras if e[0] != xy]
            if self.target is None and self.comps:  # the first comparison is not promoted: say it
                self.result.setText(self.tr("The target was removed: click the new target."))
            self._draw_markers()
            return
        role = self.click_role.currentData()
        if role in ("check", "target") and self.target is not None:
            self.extras.append(((x, y), role))
        elif self.target is None:
            self.target = (x, y)
            if self.field and self.ref == 0:  # the solved first frame gives the target's sky position for BJD
                ra, dec = self._field_wcs().pixel_to_world_values(x, y)
                from astropy.coordinates import SkyCoord

                self.coord.setText(
                    SkyCoord(float(ra), float(dec), unit="deg").to_string("hmsdms", sep=":", precision=1)
                )
            self._draw_markers()
            self._suggest()
            return
        else:
            self.comps.append((x, y))
        self._draw_markers()

    def _clear(self):
        self.target, self.comps, self.extras = None, [], []
        self.ref = None
        self._draw_markers()

    def _frame_text(self, header=None):
        from .. import timing

        path = self.images[self.shown]
        when = ""
        try:
            when = timing.mid_time(header).utc.isot[:19].replace("T", " ") + " UTC" if header is not None else ""
        except Exception:  # no time in the file: the name says enough
            pass
        text = self.tr("Frame {k} of {n}: {name}").format(k=self.shown + 1, n=len(self.images), name=Path(path).name)
        if when:
            text += f", {when}"
        if self.ref is not None:
            text += "\n" + (
                self.tr("The stars are marked on this frame.")
                if self.ref == self.shown
                else self.tr("The stars are marked on frame {k}.").format(k=self.ref + 1)
            )
        self.frame_label.setText(text)
        self.use_frame.blockSignals(True)
        self.use_frame.setChecked(path not in self.skipped)
        self.use_frame.blockSignals(False)

    def show_frame(self, i):
        """Show frame i of the series; the marked stars are drawn on the frame they were marked on."""
        from ..io.fits import read_image

        if not self.images:
            return
        self.shown = max(0, min(int(i), len(self.images) - 1))
        data, header, _ = read_image(self.images[self.shown])
        self.viewer.set_image(data, keep_view=True)  # browsing and blinking keep the zoom
        self._draw_markers()
        self._frame_text(header)
        self.frame_table.blockSignals(True)
        self.frame_table.selectRow(self.shown)
        self.frame_table.blockSignals(False)

    def _use_frame(self, on):
        item = self.frame_table.item(self.shown, 0)
        if item is not None:
            item.setCheckState(Qt.Checked if on else Qt.Unchecked)  # the list does the rest (_frame_checked)
            return
        path = self.images[self.shown]
        if on:
            self.skipped.discard(path)
        elif len(self.skipped) + 1 < len(self.images):
            self.skipped.add(path)
        self._frame_text()
        used = len(self.images) - len(self.skipped)
        self.images_label.setText(self.tr("{n} images, {k} of them used").format(n=len(self.images), k=used))

    def _fill_frames(self):
        """The frame list: name, mid-exposure time, the quality numbers when measured, the use box."""
        from astropy.time import Time

        quality = {r["file"]: r for r in getattr(self, "quality", None) or []}
        lost = (getattr(self, "lc_raw", None) or {}).get("lost") or {}  # frames the measurement left out, with why
        jds = getattr(self, "_frame_jd", {})
        known = [p for p in self.images if p in jds]  # a file without a time: the name is enough
        stamps = (
            dict(zip(known, Time([jds[p] for p in known], format="jd", scale="utc").isot, strict=True)) if known else {}
        )
        self.frame_table.blockSignals(True)
        self.frame_table.setRowCount(len(self.images))
        for i, path in enumerate(self.images):
            when = stamps.get(path, "")[11:19]
            q = quality.get(path, {})
            fwhm, sky = q.get("fwhm"), q.get("background")
            cells = (Path(path).name, when, "" if fwhm is None else f"{fwhm:.2f}", "" if sky is None else f"{sky:.0f}")
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked if path in self.skipped else Qt.Checked)
                why = [translate(w) for w in q.get("why", [])] if q and not q.get("good", True) else []
                if Path(path).name in lost:
                    why.insert(0, self._lost_text(lost[Path(path).name]))
                if why:
                    from PySide6.QtGui import QColor

                    item.setForeground(QColor("#e5484d"))
                    item.setToolTip(", ".join(why))
                self.frame_table.setItem(i, col, item)
        self.frame_table.selectRow(self.shown)
        self.frame_table.blockSignals(False)

    def _frame_checked(self, item):
        if item.column() != 0:
            return
        path = self.images[item.row()]
        on = item.checkState() == Qt.Checked
        if not on and len(self.skipped) + 1 >= len(self.images):  # one frame at least stays in
            self.frame_table.blockSignals(True)
            item.setCheckState(Qt.Checked)
            self.frame_table.blockSignals(False)
            return
        (self.skipped.discard if on else self.skipped.add)(path)
        self._frame_text()
        self.images_label.setText(
            self.tr("{n} images, {k} of them used").format(n=len(self.images), k=len(self.images) - len(self.skipped))
        )

    def _blink_step(self):
        """The next frame in use (round the series)."""
        used = [i for i, p in enumerate(self.images) if p not in self.skipped]
        if len(used) < 2:
            self.blink.setChecked(False)
            return
        later = [i for i in used if i > self.shown]
        self.frame_slider.setValue(later[0] if later else used[0])

    def _series(self):
        """The frames to measure, the frame with the marked stars first (where the positions belong)."""
        used = [p for p in self.images if p not in self.skipped]
        ref = self.images[self.ref or 0]
        return [ref] + [p for p in used if p != ref] if ref in used else used

    def _star_names(self):
        """[(name, role, (x, y))]: T1 target, C1… comparison, T2… further targets, K1… check stars."""
        out = [("T1", "target", self.target)] if self.target else []
        out += [(f"C{i + 1}", "comparison", c) for i, c in enumerate(self.comps)]
        n_t = n_k = 0
        for xy, role in self.extras:
            if role == "target":
                n_t += 1
                out.append((f"T{n_t + 1}", "target", xy))
            else:
                n_k += 1
                out.append((f"K{n_k}", "check", xy))
        return out

    def _fill_star_table(self):
        known = self._known_mags_by_name()
        roles = {"target": self.tr("target"), "comparison": self.tr("comparison"), "check": self.tr("check")}
        stars = self._star_names()
        worst = max(self._comp_scatter, key=self._comp_scatter.get) if len(self._comp_scatter) > 1 else None
        self.star_table.blockSignals(True)
        self.star_table.setRowCount(len(stars))
        for i, (name, role, (x, y)) in enumerate(stars):
            k = int(name[1:]) - 1 if role == "comparison" else None
            sc = self._comp_scatter.get(k) if k is not None else None
            cells = (
                name,
                roles[role],
                f"{x + 1:.1f}",
                f"{y + 1:.1f}",
                known.get(name, ""),
                "" if sc is None else f"{sc:.1f}",
            )
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col != 4:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == 0 and k is not None:  # a comparison star: in the ensemble or left out
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked if k in self.comp_off else Qt.Checked)
                if col == 5 and k is not None and k == worst:
                    from PySide6.QtGui import QColor

                    item.setForeground(QColor("#e5484d"))
                self.star_table.setItem(i, col, item)
        self.star_table.blockSignals(False)

    def _star_item_changed(self, item):
        """A comparison star ticked or unticked: the ensemble changes (undoable); a typed magnitude: recomputed."""
        name = self.star_table.item(item.row(), 0)
        if item.column() == 0 and name and name.text().startswith("C") and name.flags() & Qt.ItemIsUserCheckable:
            k = int(name.text()[1:]) - 1
            off = (self.comp_off - {k}) if item.checkState() == Qt.Checked else (self.comp_off | {k})
            if len(off) >= len(self.comps):  # one comparison star at least stays in
                self._fill_star_table()
                return
            self.edit(self.tr("use or leave out a comparison star"), self._set_comp_off, off)
        else:
            self._recompute()

    def _set_comp_off(self, off):
        self.comp_off = set(off)
        self._fill_star_table()
        if self.lc_raw is not None:
            self._recompute()

    def _known_mags_by_name(self):
        out = {}
        for i in range(self.star_table.rowCount()):
            name, mag = self.star_table.item(i, 0), self.star_table.item(i, 4)
            if name and mag and mag.text().strip():
                out[name.text()] = mag.text().strip()
        return out

    def known_comp_mags(self):
        """Magnitudes of the comparison stars in their order: typed in the star table, else from the catalogue
        look-up (None where neither has one)."""
        known = self._known_mags_by_name()
        cat = (self.catalog or {}).get("comps") or []
        n = len(self.lc_raw["comp_flux"][0]) if self.lc_raw else len(self.comps)
        out = []
        for i in range(n):
            try:
                out.append(float(known[f"C{i + 1}"].replace(",", ".")))
            except (KeyError, ValueError):
                out.append(cat[i]["mag"] if i < len(cat) and cat[i] else None)
        return out

    def window_parts(self):
        """The image, the steps and the results (light curve, stars, minimum, export) as separate widgets for the
        Photometry window (plans/interface.md I5): the image in the middle, the steps and the results in panels
        that can be pulled out. The page keeps its state and logic; only where the widgets live changes."""
        parts = {"view": self.viewer, "steps": self._steps_scroll, "results": self._lower}
        for w in parts.values():
            w.setParent(None)
        self._lower.setVisible(True)  # its panel is shown and hidden instead (results_dock)
        return parts

    def eventFilter(self, obj, event):
        if obj is getattr(self, "next_box", None) and event.type() == QEvent.Resize:
            need = sum(b.sizeHint().width() for b in self._next_buttons) + obj.layout().spacing()
            obj.layout().setDirection(QVBoxLayout.LeftToRight if obj.width() >= need else QVBoxLayout.TopToBottom)
        return super().eventFilter(obj, event)

    def _show_lower(self, on):
        """The lower panel (light curve, star table) only when there is something in it: until then the image has
        the whole height (the owner found the empty band in the way)."""
        dock = getattr(self, "results_dock", None)
        if dock is not None:  # in the Photometry window: the results panel appears with something in it
            if on and dock.isHidden():
                dock.show()
                win = dock.parentWidget()  # two fifths of the height, as the page's own split: room for 5 stars
                win.resizeDocks([dock], [max(dock.height(), win.height() * 2 // 5)], Qt.Vertical)
            elif not on:
                dock.hide()
            return
        if on and self._lower.isHidden():
            self._lower.setVisible(True)
            total = max(sum(self._split.sizes()), 500)
            self._split.setSizes([total * 3 // 5, total * 2 // 5])
        elif not on:
            self._lower.setVisible(False)

    def _rings_wheel(self, step):
        """Shift + wheel on the image: all three rings 0.5 px larger / smaller, the gap and the sky ring keep their
        widths; ring 1 never below 1 px."""
        d = 0.5 * step
        if self.r_ap.value() + d < 1:
            return
        for w in (self.r_out, self.r_in, self.r_ap) if d > 0 else (self.r_ap, self.r_in, self.r_out):
            w.setValue(w.value() + d)

    def _draw_markers(self):
        """Three rings per star: the aperture (solid), the inner and outer edge of the sky annulus (dashed); the
        gap between the aperture and the annulus is measured by neither."""
        self.guide.set_state(2, "done" if self.target is not None and self.comps else None)
        if self.target is not None and self.guide.states[1] is None:
            self.guide.set_state(1, "skipped")  # the bad-frame check is optional
        r, r_in, r_out = self.r_ap.value(), self.r_in.value(), self.r_out.value()
        colours = {"target": "lime", "comparison": "red", "check": "#ffb224"}
        stars = [(xy, colours[role], name) for name, role, xy in self._star_names()]
        self._show_lower(bool(stars) or self.lc_raw is not None)
        self._fill_star_table()
        marks = []
        here = self.ref is None or self.ref == self.shown
        for xy, colour, label in stars if here else ():
            marks += [(*xy, r, colour, label), (*xy, r_in, colour, "", "dash"), (*xy, r_out, colour, "", "dash")]
        if self.field and self.shown == 0:  # the known variable stars, where the solution of the first frame puts them
            # named only when chosen in the list (40 names hid the field, I6b (1)); the others on hover
            chosen = (self.variables.currentData() or {}).get("name")
            for v in self.field["variables"][:30]:
                marks.append(
                    (v["x"], v["y"], 2 * r_out, "cyan", v["name"], "dash", *([] if v["name"] == chosen else ["quiet"]))
                )
        self.viewer.set_markers(marks)
        role = self.click_role.currentData()
        nxt = "target" if self.target is None or role == "target" else "check" if role == "check" else "comparison"
        # the rings of the next click follow the mouse, in the colour of the star it will mark
        self.viewer.set_pick(True, [(r, False), (r_in, True), (r_out, True)], colours[nxt])
        self.apertures_button.setEnabled(bool(self.images and self.target))
        if hasattr(self, "sections"):
            if self.target is not None and self.comps:
                self._advance(2)
            else:
                self._step_titles()
        self.measure_button.setEnabled(bool(self.images and self.target))  # no comparison: the target's own flux
        self.catalog_button.setEnabled(bool(self.images and self.target and self.comps))
        self.suggest_button.setEnabled(bool(self.images and self.target))

    def _step_titles(self):
        """Numbered step titles; a step that is done gets a tick."""
        names = (self.tr("1. Images"), self.tr("2. Target and comparison stars"), self.tr("3. Aperture and sky ring"),
                 self.tr("4. Measure"))  # fmt: skip
        done = (
            bool(self.images),
            self.target is not None and bool(self.comps),
            self._radii_set,
            self.lc_raw is not None,
        )
        for sec, name, ok in zip(self.sections, names, done, strict=True):
            sec.button.setText(("✓ " if ok else "") + name)

    def _advance(self, k):
        """Open step k and fold steps 2 and 3 before it (they reopen with a click); the images step stays as it is:
        its frame list shows the frames left out in red."""
        if k <= self._step_now:
            self._step_titles()
            return
        self._step_now = k
        for i, sec in enumerate(self.sections):
            if 0 < i < k:
                sec.set_expanded(False)
        self.sections[k].set_expanded(True)
        self._step_titles()

    def show_field(self, field):
        """What is in the first frame (photometry.identify_field): solution, OBJECT check, variable stars."""
        self.field = field
        lines = [
            self.tr("Field solved against Gaia: {n} stars, {scale:.2f}″ per pixel.").format(
                n=field["matched"], scale=field["scale"]
            )
        ]
        obj = field.get("object")
        if obj and obj.get("known") and not obj.get("in_field"):
            lines.append(
                self.tr(
                    "⚠ The files say OBJECT = {name}, but that star is {deg:.1f}° from this field: the name in the "
                    "files is wrong. Choose the target from the variable stars below, or by its position."
                ).format(name=obj["name"], deg=obj["distance_deg"])
            )
        elif obj and obj.get("in_field"):
            lines.append(
                self.tr("OBJECT {name} is in the field, at x {x:.0f}, y {y:.0f}.").format(
                    name=obj["name"], x=obj["x"], y=obj["y"]
                )
            )
        variables = field.get("variables") or []
        self.variables.clear()
        for v in variables:
            mag = f" ({v['mag']:.1f} mag)" if v.get("mag") is not None else ""
            self.variables.addItem(f"{v['name']}{mag}", v)
        if variables:
            lines.append(self.tr("{n} known variable star(s) in the field (marked in cyan on the first frame).").format(
                n=len(variables)
            ))  # fmt: skip
        else:
            lines.append(self.tr("No known variable star (AAVSO VSX) in the field."))
        self.field_label.setText("\n".join(lines))
        self.field_label.show()
        for w in (self.variables, self.make_target):
            w.setVisible(bool(variables))
        self._draw_markers()
        if obj and obj.get("in_field") and self.target is None and not self.comps:
            # the star the files name is the target: nothing to click (a click elsewhere changes it)
            self.edit(self.tr("the target from the files"), self._set_target_from_field, (obj["x"], obj["y"]), obj)

    def field_failed(self, message):
        self.field = None
        self.field_label.setText(
            self.tr("The field was not identified ({why}): mark the stars by hand.").format(why=translate(message))
        )
        self.field_label.show()

    def _field_wcs(self):
        from astropy.io import fits
        from astropy.wcs import WCS

        return WCS(fits.Header.fromstring(self.field["header"])) if self.field else None

    def _variable_as_target(self):
        v = self.variables.currentData()
        if not v:
            return
        if self.shown != 0:
            self.show_frame(0)  # the solution belongs to the first frame
        self.edit(self.tr("make a variable star the target"), self._set_target_from_field, (v["x"], v["y"]), v)

    def _set_target_from_field(self, xy, v):
        if self.ref not in (None, 0):  # stars marked on another frame cannot be mixed with these positions
            self.comps, self.extras = [], []
        self.ref, self.target = 0, (float(xy[0]), float(xy[1]))
        from astropy.coordinates import SkyCoord

        self.coord.setText(SkyCoord(v["ra"], v["dec"], unit="deg").to_string("hmsdms", sep=":", precision=1))
        self._draw_markers()
        self.result.setText(
            self.tr("T1 = {name}; its catalogue position is used for the barycentric times (BJD).").format(
                name=v["name"]
            )
        )
        self._suggest()

    def _suggest(self, auto=True):
        """Ask for comparison stars; on its own (auto) only while none is marked: the chain target -> comparison
        stars -> radii runs without a press, so that choosing the images and Measure is the whole of it."""
        if not (self.images and self.target) or (auto and self.comps):
            return
        self._auto_for = self.target if auto else None
        if auto:
            self.result.setText(self.tr("Choosing the comparison stars…"))
        self.suggest_requested.emit(self._series(), list(self.target), {"r_out": self.r_out.value()})

    def _choose_radii(self):
        self.apertures_requested.emit(self._series(), list(self.target), [list(c) for c in self.comps])

    def set_comparisons(self, comps, catalogue=None):
        auto, self._auto_for = getattr(self, "_auto_for", None), None
        if auto is not None and (auto != self.target or self.comps):
            return  # the target changed, or stars were clicked, while the suggestion was on its way
        self.edit(self.tr("suggested comparison stars"), self._set_comps, [tuple(c) for c in comps])
        if comps and catalogue:
            text = self.tr("{n} comparison stars chosen from Gaia: about as bright as the target, not variable, "
                           "alone, unsaturated, inside every frame.").format(n=len(comps))  # fmt: skip
            if not catalogue.get("same_colour"):
                text += " " + self.tr(
                    "No star of the target's colour (BP−RP {c:.2f}) is in the field: with stars of another colour "
                    "the light curve can drift slowly with airmass; detrend it against airmass."
                ).format(c=catalogue["colour"])
            self.result.setText(text)
        if comps and not self._radii_set:
            self._choose_radii()

    def _set_comps(self, comps):
        self.comps = comps
        self._draw_markers()
        if not comps:
            self.result.setText(self.tr("No suitable comparison star found; click them by hand."))
        else:
            self.result.setText(
                self.tr(
                    "{n} comparison stars suggested: similar brightness, near the target, unsaturated, no neighbour "
                    "in the sky ring, inside every frame. Click one to take it off, or click others to add them."
                ).format(n=len(comps))
            )

    def _measure(self):
        params = {"r_ap": self.r_ap.value(), "r_in": self.r_in.value(), "r_out": self.r_out.value()}
        params["follow_seeing"] = self.follow_seeing.isChecked()
        if self.telescope_d.value() > 0:
            params["aperture_m"] = self.telescope_d.value()
        params["psf"] = self.psf.isChecked()
        if self.extras:
            params["extra_xy"] = [list(xy) for xy, _ in self.extras]
        self.result.setText(self.tr("Measuring…"))
        series = self._series()
        params["ref_image"] = series[0]  # the positions belong to this frame; the step carries them to the others
        self.measure_requested.emit(
            series, list(self.target), [list(c) for c in self.comps], self.coord.text().strip(), params
        )

    def show_apertures(self, a):
        """Set the three radii and draw the star's radial profile with them (like a seeing profile)."""
        self.guide.set_state(3, "done")
        for w, key in ((self.r_ap, "r_ap"), (self.r_in, "r_in"), (self.r_out, "r_out")):
            w.setValue(a[key])
        self._radii_set = True
        self._advance(3)
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        ax.axvspan(0, a["r_ap"], color="#46a758", alpha=0.18, lw=0, label=self.tr("aperture"))
        ax.axvspan(a["r_in"], a["r_out"], color="#3e63dd", alpha=0.18, lw=0, label=self.tr("sky annulus"))
        ax.plot(a["profile_r"], a["profile"], ".-", lw=0.8, ms=4, label=self.tr("star profile (peak = 1)"))
        ax.axhline(0, color="grey", lw=0.5)
        ax.axhline(0.5, color="grey", lw=0.5, ls=":")
        for r in (a["r_ap"], a["r_in"], a["r_out"]):
            ax.axvline(r, color="grey", lw=0.8, ls="--")
        ax.set_xlim(0, a["r_out"] * 1.15)
        ax.set_xlabel(self.tr("Radius (px)"))
        ax.set_ylabel(self.tr("Relative brightness"))
        ax.legend(fontsize=8)
        self.plot.draw()
        self.result.setText(
            self.tr(
                "FWHM {f:.2f} px. Aperture {a:.2f} px ({af:.1f} FWHM; best S/N at {b:.2f} px; holds {ee:.1f} % of the "
                "light). Gap {a:.2f}–{i:.2f} px is left out. Sky annulus {i:.2f}–{o:.2f} px."
            ).format(
                f=a["fwhm"],
                a=a["r_ap"],
                af=a["r_ap"] / a["fwhm"],
                b=a["best_snr_radius"],
                ee=100 * a["encircled_at_aperture"],
                i=a["r_in"],
                o=a["r_out"],
            )
            + (
                "\n"
                + self.tr(
                    "The target's light grows {x:.1f} % more than the comparison stars' between 1 and 1.5 apertures: "
                    "something faint is next to it. Keep the radii fixed (not following the seeing); its light then "
                    "only dilutes the depth a little."
                ).format(x=100 * a["target_excess"])
                if a.get("target_excess", 0) > 0.01
                else ""
            )
            + (
                "\n"
                + self.tr(
                    "Chosen on {k} frames of the series: the light curve changed least from one frame to the next "
                    "({best:.2f} %) with this aperture; {small:.2f} % with {r1:.1f} px, the best for one star's noise "
                    "alone, which loses a share of the light that moves with the seeing."
                ).format(
                    k=a["scan"]["frames"],
                    best=100 * min(a["scan"]["scatter"]),
                    small=100 * a["scan"]["scatter"][0],
                    r1=a["scan"]["radii"][0],
                )
                if a.get("scan")
                else ""
            )
        )

    def show_quality(self, rows):
        """Plot FWHM, number of stars and sky of every frame; bad ones in red, with the reasons."""
        self.guide.set_state(1, "done")
        from .messages import translate

        self.quality = rows
        self._show_lower(True)  # the plot is in the lower panel
        self._fill_frames()
        n = np.arange(len(rows))
        bad = np.array([not r["good"] for r in rows])
        self.plot.figure.clear()
        axes = self.plot.figure.subplots(3, 1, sharex=True)
        for ax, key, label in zip(
            axes,
            ("fwhm", "stars", "background"),
            (self.tr("FWHM (px)"), self.tr("Stars"), self.tr("Sky (ADU)")),
            strict=True,
        ):
            y = np.array([np.nan if r[key] is None else r[key] for r in rows], float)
            ax.plot(n, y, ".-", lw=0.6, ms=4)
            ax.plot(n[bad], y[bad], "o", color="#e5484d", ms=6)
            ax.set_ylabel(label)
        axes[-1].set_xlabel(self.tr("Frame"))
        self.plot.draw()
        reasons = [
            f"{r['file'].replace(chr(92), '/').split('/')[-1]}: {', '.join(translate(w) for w in r['why'])}"
            for r in rows
            if not r["good"]
        ]
        self.result.setText(
            self.tr("{g} of {n} frames are good.").format(g=len(rows) - len(reasons), n=len(rows))
            + "".join("\n" + t for t in reasons[:12])
        )
        self.drop_bad.setVisible(bool(reasons))

    def _drop_bad(self):
        """The bad frames are unticked in the list (not deleted: a tick brings one back)."""
        bad = {r["file"] for r in self.quality if not r["good"]}
        self.skipped |= bad & set(self.images)
        if len(self.skipped) >= len(self.images):
            self.skipped -= bad
        self._fill_frames()
        self._frame_text()
        self.images_label.setText(
            self.tr("{n} images, {k} of them used").format(n=len(self.images), k=len(self.images) - len(self.skipped))
        )
        self.drop_bad.hide()

    def _catalog(self):
        inputs = {"image": self._series()[0], "target_xy": list(self.target), "comps_xy": [list(c) for c in self.comps]}
        self.result.setText(self.tr("Looking up the comparison stars…"))
        self.catalog_requested.emit(inputs, {"filter": self.band.currentText()})

    def show_catalog(self, cat):
        """Comparison magnitudes found: written into the star table's known-magnitude column, so the target's
        standard magnitudes (with the colour term) come from the same calculation as typed-in magnitudes."""
        self.catalog = cat
        lines = [
            self.tr("Comparison {i}: {m:.3f} ± {e:.3f} ({src})").format(
                i=i + 1, m=c["mag"], e=c["err"], src=c["source"]
            )
            if c
            else self.tr("Comparison {i}: not in the catalogues").format(i=i + 1)
            for i, c in enumerate(cat["comps"])
        ]
        self.star_table.blockSignals(True)
        for i, c in enumerate(cat["comps"]):
            row = 1 + i  # T1 is the first row, then C1, C2…
            if c and row < self.star_table.rowCount():
                self.star_table.setItem(row, 4, QTableWidgetItem(f"{c['mag']:.6f}"))
        self.star_table.blockSignals(False)
        if self.lc_raw is None and self.light_curve is not None:
            self.lc_raw = self.light_curve
        if self.lc_raw is not None:
            if not self.show_what.count():
                self._fill_show_choices()
            self._recompute()
            lc = self.light_curve
            if "mag" in lc:
                m = np.asarray(lc["mag"])
                lines.append(
                    self.tr("Target {band}: {lo:.3f} – {hi:.3f} mag").format(
                        band=lc["mag_band"], lo=np.nanmin(m), hi=np.nanmax(m)
                    )
                )
                self.show_what.setCurrentIndex(self.show_what.findData("mag"))
        self.result.setText("\n".join(lines))

    def show_light_curve(self, lc):
        """A new measurement: kept as measured; weights, detrending and magnitudes are applied on top of it."""
        self.guide.set_state(4, "done")
        self.lc_raw, self.detrend_cfg, self.excluded, self.comp_off = lc, None, set(), set()
        self._step_titles()
        self._fill_frames()  # frames left out by the measurement in red, with why
        self._show_lower(True)
        self.next_box.setVisible(True)
        self.minimum_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.aavso_button.setEnabled(True)
        self._fill_show_choices()
        self._recompute()

    def _fill_show_choices(self):
        current = self.show_what.currentData()
        self.show_what.blockSignals(True)
        self.show_what.setEnabled(True)
        self.show_what.clear()
        self.show_what.addItem(self.tr("Differential: target − comparison, the check star above it"), "diff")
        self.show_what.addItem(self.tr("T1: relative flux"), "rel")
        self.show_what.addItem(self.tr("T1: differential magnitude (Δm)"), "dmag")
        self.show_what.addItem(self.tr("T1: magnitude (needs known magnitudes)"), "mag")
        for i, (name, _role, _) in enumerate(n for n in self._star_names() if n[1] != "comparison" and n[0] != "T1"):
            self.show_what.addItem(self.tr("{name}: relative flux").format(name=name), f"extra{i}")
        self.show_what.addItem(self.tr("Comparison stars against the others"), "comps")
        self.show_what.addItem(self.tr("All stars, normalised and offset"), "all")
        self.show_what.addItem(self.tr("Airmass, sky, FWHM and position"), "trends")
        i = self.show_what.findData(current)
        self.show_what.setCurrentIndex(max(i, 0))
        self.show_what.blockSignals(False)

    def _recompute(self):
        """Current light curve = measured one, with the chosen ensemble weights, detrending and magnitudes."""
        from ..photometry import differential as d
        from ..photometry.catalog import calibrate

        raw = self.lc_raw
        if raw is None:
            return
        raw, self._frame_ids = _without_frames(raw, self.excluded)
        n_comp = len(raw["comp_flux"][0]) if raw.get("comp_flux") and len(raw["comp_flux"][0]) else 0
        self._comp_scatter = {}
        if n_comp > 1:  # each comparison star against the others (all of them), in mmag, for the star table
            _, sc = d.comps_against_others(raw["comp_flux"])
            self._comp_scatter = {k: 1085.7 * float(v) for k, v in enumerate(sc)}
        keep = [k for k in range(n_comp) if k not in self.comp_off] or list(range(n_comp))
        if len(keep) < n_comp:  # comparison stars left out by the user: the ensemble without them
            cut = {
                key: [[row[k] for k in keep] for row in raw[key]]
                for key in ("comp_flux", "comp_flux_err")
                if key in raw
            }
            raw = dict(raw) | cut
        lc = dict(raw)
        w = None
        if "comp_flux_err" in raw:  # light curves of older projects and the live one keep their own ensemble
            if self.weighted.isChecked() and len(raw["comp_flux"][0]) > 1:
                w = d.scatter_weights(raw["comp_flux"])
            rel, err = d.ensemble(raw["target_flux"], raw["target_flux_err"], raw["comp_flux"], raw["comp_flux_err"], w)
            lc |= {"rel_flux": rel.tolist(), "rel_flux_err": err.tolist()}
        lc["weights"] = None if w is None else w.tolist()
        if self.detrend_cfg:
            names, exclude, *rest = self.detrend_cfg
            cov = d.covariates(lc)
            degree = rest[0] if rest else 1
            out = d.detrend(lc["rel_flux"], {k: cov[k] for k in names}, exclude=exclude, time=lc["time"], degree=degree)
            lc |= {"rel_flux": out["rel_flux"], "detrend": out}
        lc["extra"] = []
        extras = [n for n in self._star_names() if n[1] != "comparison" and n[0] != "T1"]
        for i, (name, role, _) in enumerate(extras):
            if "extra_flux" not in raw or i >= len(raw["extra_flux"][0]):
                break
            f = [row[i] for row in raw["extra_flux"]]
            fe = [row[i] for row in raw["extra_flux_err"]]
            r, re_ = d.ensemble(f, fe, raw["comp_flux"], raw["comp_flux_err"], w)
            lc["extra"].append({"name": name, "role": role, "rel_flux": r.tolist(), "rel_flux_err": re_.tolist()})
        all_mags = self.known_comp_mags()
        mags = [all_mags[k] for k in keep if k < len(all_mags)] if n_comp else all_mags
        if any(m is not None for m in mags):
            cat_all = (self.catalog or {}).get("comps") or []
            cat = [cat_all[k] if k < len(cat_all) else None for k in keep] if n_comp else cat_all
            comps = []
            for i, m in enumerate(mags):  # catalogue colours are kept when the magnitude is the catalogue's
                c = cat[i] if i < len(cat) and cat[i] and m is not None and abs(cat[i]["mag"] - m) < 1e-6 else None
                comps.append(c if c else (None if m is None else {"mag": m}))
            colour = ((self.catalog or {}).get("target") or {}).get("colour")
            try:
                out = calibrate(lc, comps, colour)
            except ValueError:
                out = None
            if out:
                band = self.catalog["filter"] if self.catalog else self.band.currentText()
                lc |= {"mag": out["mag"], "mag_err": out["mag_err"], "mag_band": band, "mag_suspect": out["suspect"]}
                for x in lc["extra"]:
                    rel_x = np.asarray(x["rel_flux"])
                    xs = dict(lc) | {
                        "target_flux": (
                            rel_x * (np.asarray(raw["comp_flux"]) * (1 if w is None else w)).sum(axis=1)
                        ).tolist(),
                        "rel_flux": x["rel_flux"],
                        "rel_flux_err": x["rel_flux_err"],
                    }
                    xo = calibrate(xs, comps, None)
                    x |= {"mag": xo["mag"], "mag_err": xo["mag_err"]}
        lc["comps_used"] = [k + 1 for k in keep]
        self.light_curve = lc
        self._fill_star_table()
        self._plot_current()
        self._summarise()

    def _saturated_frames(self, lc):
        sat = lc.get("saturation")
        if not sat or not lc.get("peak"):
            return np.zeros(len(lc["time"]), bool)
        return np.array([any(p is not None and p >= sat for p in row) for row in lc["peak"]])

    def _lost_text(self, why):
        """Why the measurement left a frame out (lightcurve._measure_frame), in the interface language."""
        if why[0] == "target":
            return self.tr("the target was not found there (clouds, or off the frame?)")
        if why[0] == "comparison":
            return self.tr("comparison star C{k} was not found there (clouds, off the frame, or saturated?)").format(
                k=why[1]
            )
        return self.tr("the stars were not found (clouds, a jolt, or another field)")

    def _summarise(self):
        lc = self.light_curve
        f = np.asarray(lc["rel_flux"], float)
        lines = [self.tr("{n} points, scatter {rms:.2f} %").format(n=len(f), rms=100 * np.nanstd(f / np.nanmedian(f)))]
        a = lc.get("apertures") or {}
        if a.get("replaced"):
            lines.append(
                self.tr(
                    "The rings do not fit these small frames: aperture {r:.1f} px, sky {a:.1f}–{b:.1f} px, chosen "
                    "from the stars."
                ).format(r=a["r_ap"], a=a["r_in"], b=a["r_out"])
            )
        used = lc.get("comps_used") or []
        n_all = len((self.lc_raw or {}).get("comp_flux", [[]])[0]) if self.lc_raw else 0
        if used and len(used) < n_all:
            out = [f"C{k}" for k in range(1, n_all + 1) if k not in used]
            lines.append(
                self.tr("Comparison stars in use: {used} (left out: {out}).").format(
                    used=", ".join(f"C{k}" for k in used), out=", ".join(out)
                )
            )
        lost = (self.lc_raw or {}).get("lost") or {}
        if lost:
            lines.append(
                self.tr("⚠ {n} frame(s) left out by the measurement (in red in the frame list):").format(n=len(lost))
            )
            lines += [f"  {name}: {self._lost_text(why)}" for name, why in list(lost.items())[:6]]
            if len(lost) > 6:
                lines.append("  …")
        if self.excluded:
            lines.append(
                self.tr("{n} points deleted by hand (Restore deleted points brings them back).").format(
                    n=len(self.excluded)
                )
            )
        if lc.get("scintillation"):
            sc = 1085.7 * np.asarray(lc["scintillation"], float)
            lines.append(
                self.tr("Scintillation {lo:.1f}–{hi:.1f} mmag per frame is included in the errors.").format(
                    lo=np.nanmin(sc), hi=np.nanmax(sc)
                )
            )
        elif not np.size(lc.get("comp_flux", [])):  # space data (TESS, Kepler): no atmosphere to divide out
            lines.append(
                self.tr(
                    "No comparison star: the target's own flux over its median. Right for space data (TESS, Kepler); "
                    "from the ground, clouds and airmass stay in the light curve."
                )
            )
        elif "scintillation" in lc:
            lines.append(self.tr("Scintillation is not in the errors: give the telescope aperture (and the site)."))
        for x in lc["extra"]:
            r = np.asarray(x["rel_flux"], float)
            lines.append(
                self.tr("{name}: scatter {mmag:.1f} mmag").format(
                    name=x["name"], mmag=1000 * 1.0857 * np.nanstd(r / np.nanmedian(r))
                )
            )
        if lc.get("weights"):
            lines.append(
                self.tr("Weights: {w}").format(w=", ".join(f"C{i + 1} {v:.2f}" for i, v in enumerate(lc["weights"])))
            )
        if lc.get("detrend"):
            dt = lc["detrend"]
            lines.append(
                self.tr("Detrended ({k}): scatter of the {n} points fitted {a:.2f} % → {b:.2f} %").format(
                    k=", ".join(dt["coefficients"]),
                    n=dt["points_fitted"],
                    a=100 * dt["scatter_before"],
                    b=100 * dt["scatter_after"],
                )
            )
        for i in lc.get("mag_suspect") or []:
            lines.append(
                self.tr("C{i} disagrees with its known magnitude by more than 0.1 mag and was left out.").format(
                    i=i + 1
                )
            )
        sat = self._saturated_frames(lc)
        if sat.any():
            lines.append(
                self.tr("⚠ {n} frames have a star at or above the saturation level (marked red).").format(
                    n=int(sat.sum())
                )
            )
        self.result.setText("\n".join(lines))

    def _plot_current(self):
        from ..photometry import differential as d

        lc = self.light_curve
        if lc is None:
            return
        what = self.show_what.currentData() or "rel"
        t = np.asarray(lc["time"], float)
        t_ref = np.floor(t.min())
        x = t - t_ref
        sat = self._saturated_frames(lc)
        self.plot.figure.clear()
        self._plotted = None
        if not getattr(self, "_click_hooked", False):
            self.plot.canvas.mpl_connect("button_press_event", self._plot_clicked)
            self._click_hooked = True
        ax = self.plot.figure.add_subplot()
        if what == "diff":
            label = self._plot_differential(ax, lc, x, sat)
        elif what in ("rel", "dmag", "mag") or what.startswith("extra"):
            src = lc if not what.startswith("extra") else lc["extra"][int(what[5:])]
            f, e = np.asarray(src["rel_flux"], float), np.asarray(src["rel_flux_err"], float)
            if what == "mag" and "mag" in lc:
                y, ye, label = (
                    np.asarray(lc["mag"], float),
                    np.asarray(lc["mag_err"], float),
                    self.tr("Magnitude ({band})").format(band=lc["mag_band"]),
                )
                ax.invert_yaxis()
            elif what in ("dmag", "mag"):
                y, ye = d.delta_mag(f, e)
                label = self.tr("Δm (target − comparison)")
                ax.invert_yaxis()
            else:
                med = np.nanmedian(f)
                y, ye, label = f / med, e / med, self.tr("Relative flux")
            ax.errorbar(x, y, ye, fmt=".", ms=3, lw=0.5, alpha=0.8)
            self._plotted = (ax, x, y)
            if sat.any():
                ax.plot(x[sat], y[sat], "o", mfc="none", color="#e5484d", ms=7)
        elif what == "comps":
            curves, scatter = d.comps_against_others(lc["comp_flux"], lc.get("weights"))
            for i, (c, s_) in enumerate(zip(curves, scatter, strict=True)):
                ax.plot(
                    x,
                    np.asarray(c) - self.spacing.value() * i,
                    ".",
                    ms=3,
                    label=f"C{i + 1} ({1000 * 1.0857 * s_:.1f} mmag)",
                )
            label = self.tr("Relative flux (offset)")
            ax.legend(fontsize=7)
        elif what == "all":
            curves = [("T1", lc["rel_flux"])] + [(xx["name"], xx["rel_flux"]) for xx in lc["extra"]]
            for i, (name, c) in enumerate(curves):
                c = np.asarray(c, float)
                ax.plot(x, c / np.nanmedian(c) - self.spacing.value() * i, ".", ms=3, label=name)
            label = self.tr("Relative flux (offset)")
            ax.legend(fontsize=7)
        else:
            cov = d.covariates(lc)
            for key in ("airmass", "sky", "fwhm", "x", "y"):
                if key in cov:
                    v = np.asarray(cov[key], float)
                    ax.plot(x, (v - np.nanmean(v)) / (np.nanstd(v) or 1), ".", ms=2, label=key)
            label = self.tr("Normalised value")
            ax.legend(fontsize=7)
        ax.set_xlabel(f"{lc['time_scale']} − {t_ref:.0f}")
        ax.set_ylabel(label)
        self.plot.draw()

    def _plot_differential(self, ax, lc, x, sat):
        """The classic differential plot: Δm of the target against the comparison (ensemble) and, offset from it,
        the check star against the same comparison — or C1 − C2 when there is no check star. A flat check curve
        says the comparison is constant; its scatter (mmag) is the precision the target can be trusted to."""
        from ..photometry import differential as d

        rel = np.asarray(lc["rel_flux"], float)
        y, ye = d.delta_mag(rel, np.asarray(lc["rel_flux_err"], float))
        y = y - np.nanmedian(y)
        ax.errorbar(x, y, ye, fmt=".", ms=3, lw=0.5, alpha=0.8, label=self.tr("T1 − comparison"))
        bad = np.flatnonzero(np.isfinite(rel) & (rel <= 0))
        if len(bad):
            files = [Path(f).name for f in lc.get("file") or []]
            names = ", ".join(files[i] for i in bad[:4] if i < len(files)) + (", …" if len(bad) > 4 else "")
            note = self.tr(
                "{n} frame(s) without a positive flux for T1 ({frames}), no magnitude: is the star on those "
                "frames, or a brighter star in its sky ring? Leave them out with “Use this frame”."
            ).format(n=len(bad), frames=names)
            ax.text(0.01, 0.01, note, transform=ax.transAxes, fontsize=7, color="#e5484d", va="bottom")
        self._plotted = (ax, x, y)
        if sat.any():
            ax.plot(x[sat], y[sat], "o", mfc="none", color="#e5484d", ms=7)
        check = next((e for e in lc.get("extra", []) if e.get("role") == "check"), None)
        comp = np.asarray(lc.get("comp_flux") or [[]], float)
        if check is not None:
            k, _ = d.delta_mag(np.asarray(check["rel_flux"], float), np.asarray(check["rel_flux_err"], float))
            name = self.tr("{k} (check) − comparison").format(k=check["name"])
        elif comp.ndim == 2 and comp.shape[1] >= 2:
            with np.errstate(divide="ignore", invalid="ignore"):
                k = -2.5 * np.log10(comp[:, 0] / comp[:, 1])
            name = "C1 − C2"
        else:
            k = None
        if k is not None:
            k = k - np.nanmedian(k)
            rms = 1000 * np.nanstd(k)
            gap = max(self.spacing.value(), 4 * np.nanstd(y), 4 * np.nanstd(k), 0.02)
            ax.plot(x, k - gap, ".", ms=3, color="#8e8e93", label=f"{name}: {rms:.1f} mmag")  # above: axis inverted
        ax.invert_yaxis()
        ax.legend(fontsize=7, loc="best")
        return self.tr("Δm (mag)")

    def _plot_clicked(self, event):
        """With "Click a point to delete it": the point nearest the click (within 10 screen pixels) is left out."""
        if not (self.delete_mode.isChecked() and self._plotted and event.inaxes is self._plotted[0]):
            return
        ax, x, y = self._plotted
        pix = ax.transData.transform(np.column_stack([x, y]))
        dist = np.hypot(pix[:, 0] - event.x, pix[:, 1] - event.y)
        i = int(np.nanargmin(dist)) if np.isfinite(dist).any() else -1
        if i >= 0 and dist[i] < 10:
            self.delete_point(i)

    def delete_point(self, i):
        """Leave out the i-th point of the light curve now shown (and its frame from every result)."""
        self.edit(self.tr("delete a point"), self._exclude, self.excluded | {self._frame_ids[i]})

    def restore_points(self):
        self.edit(self.tr("restore deleted points"), self._exclude, set())

    def _exclude(self, frames):
        self.excluded = frames
        self._recompute()

    def _detrend(self):
        names = [k for k, b in self.trend_boxes.items() if b.isChecked()]
        if not names or self.lc_raw is None:
            self.result.setText(self.tr("Tick at least one quantity to detrend against."))
            return
        from ..photometry.differential import covariates

        missing = [k for k in names if k not in covariates(self.lc_raw)]
        if missing:
            self.result.setText(
                self.tr(
                    "Not in this light curve: {names} (FWHM needs ‘Radii follow the seeing’; "
                    "airmass needs the site and RA/Dec)."
                ).format(names=", ".join(missing))
            )
            return
        exclude = None
        try:
            if self.exclude_from.text().strip() and self.exclude_to.text().strip():
                exclude = (float(self.exclude_from.text()), float(self.exclude_to.text()))
        except ValueError:
            self.result.setText(self.tr("The left-out range must be two times (numbers)."))
            return
        self._set_detrend((names, exclude, self.trend_degree.value()))

    def _set_detrend(self, cfg):
        self.edit(self.tr("detrending") if cfg else self.tr("undo detrending"), self._apply_detrend, cfg)

    def _apply_detrend(self, cfg):
        from .messages import translate

        old, self.detrend_cfg = self.detrend_cfg, cfg
        try:
            self._recompute()
        except ValueError as e:
            self.detrend_cfg = old
            self._recompute()
            self.result.setText(translate(str(e)))

    def _minimum(self):
        params = {"method": "kvw" if self.kvw.isChecked() else "trapezoid"}
        try:
            if self.t0.text().strip() and self.period.text().strip():
                params |= {"t0": float(self.t0.text()), "period": float(self.period.text())}
        except ValueError:
            self.result.setText(self.tr("T0 and period must be numbers."))
            return
        self.minimum_requested.emit(self.light_curve, params)

    def show_minimum(self, m):
        self.guide.set_state(5, "done")
        methods = {"kvw": self.tr("Kwee–van Woerden"), "trapezoid": self.tr("trapezoid fit")}
        if "minima" in m:  # every eclipse of a long series (TESS, several nights)
            ms = m["minima"]
            oc = np.array([x["o_minus_c"] for x in ms]) * 1440
            text = self.tr(
                "{n} minima timed ({p} primary, {s} secondary), {method}; O−C {mean:+.2f} min, scatter {sd:.2f} min"
            ).format(
                n=len(ms),
                p=sum(x["kind"] == "I" for x in ms),
                s=sum(x["kind"] == "II" for x in ms),
                method=methods[m["method"]],
                mean=float(np.mean(oc)),
                sd=float(np.std(oc)),
            )
            if m.get("skipped"):
                text += "\n" + self.tr("{n} predicted minima left out: not covered on both sides, or no dip.").format(
                    n=m["skipped"]
                )
            self.result.setText(text + "\n" + self.tr("All of them are in the O-C tab."))
            if not self.plot.figure.axes or not self.light_curve:  # the plot was cleared meanwhile: nothing to mark
                return
            ax = self.plot.figure.axes[0]
            t_ref = np.floor(min(self.light_curve["time"]))
            for x in ms:
                ax.axvline(x["time"] - t_ref, color="red" if x["kind"] == "I" else "orange", lw=0.8)
            self.plot.draw()
            return
        text = self.tr("Minimum: {t:.6f} ± {e:.6f} {scale} ({e_min:.1f} min), {method}").format(
            t=m["time"], e=m["error"], scale=m["time_scale"], e_min=m["error"] * 1440, method=methods[m["method"]]
        )
        if "depth" in m:
            text += "\n" + self.tr("Depth {d:.2f} %, duration {h:.2f} h").format(
                d=100 * m["depth"], h=24 * m["duration"]
            )
        if "o_minus_c" in m:
            text += "\n" + self.tr("Epoch {n}, O−C = {oc:+.2f} min").format(n=m["epoch"], oc=m["o_minus_c"] * 1440)
        self.result.setText(text)
        if not self.plot.figure.axes or not self.light_curve:  # (an intermittent CI failure)
            return
        ax = self.plot.figure.axes[0]
        t_ref = np.floor(min(self.light_curve["time"]))
        ax.axvline(m["time"] - t_ref, color="red", lw=1)
        self.plot.draw()

    def _export_aavso(self):
        self.guide.set_state(5, "done")
        from ..brand import BRAND
        from ..photometry.export import aavso_extended

        dialog = AavsoDialog(len(self.comps), self)
        mags = self.known_comp_mags()
        if mags and all(m is not None for m in mags):
            dialog.mags.setText(", ".join(f"{m:.3f}" for m in mags))
        if self.catalog:
            dialog.filter.setCurrentText(self.catalog["filter"])
        checks = [x for x in self.light_curve.get("extra", []) if x["role"] == "check"]
        if checks:
            dialog.check.setText(checks[0]["name"])
        if dialog.exec() != QDialog.Accepted:
            return
        extra = {}
        if checks:  # the first check star goes into KNAME / KMAG
            extra = {"check": checks[0]["rel_flux"], "check_name": dialog.check.text().strip() or checks[0]["name"]}
        try:
            text = aavso_extended(self.light_curve, software_name=BRAND.display_name, **dialog.values(), **extra)
        except ValueError as e:
            QMessageBox.warning(self, self.tr("AAVSO report"), translate(e))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("AAVSO report"), "aavso.txt", "Text (*.txt)")
        if path:
            Path(path).write_text(text, encoding="utf-8")

    def _export(self):
        self.guide.set_state(5, "done")
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export light curve"), "lightcurve.csv", "CSV (*.csv)")
        if path:
            export_csv(self.light_curve, path)

    def _to_models(self, path=None):
        """The light curve as a CSV file (the user chooses where; next to the frames by default), opened on the
        Orbits & models page."""
        default = str(Path(self.images[0]).with_name("lightcurve.csv")) if self.images else "lightcurve.csv"
        path = path or QFileDialog.getSaveFileName(self, self.tr("Save the light curve for the model"), default,
                                                   "CSV (*.csv)")[0]  # fmt: skip
        if path:
            export_csv(self.light_curve, path)
            self.next_requested.emit("orbits", str(path))


class AavsoDialog(QDialog):
    """The fields an AAVSO Extended report needs that the light curve does not know."""

    FILTERS = ("V", "B", "R", "I", "CV", "CR", "TG", "TB", "TR", "SG", "SR", "SI", "U")

    def __init__(self, n_comps, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("AAVSO report"))
        form = QFormLayout(self)
        self.star, self.obscode, self.mags = QLineEdit(self), QLineEdit(self), QLineEdit(self)
        self.chart, self.notes = QLineEdit(self), QLineEdit(self)
        self.filter = QComboBox(self)
        self.filter.addItems(self.FILTERS)
        self.mags.setPlaceholderText(self.tr("{n} values, e.g. 11.20, 11.85").format(n=n_comps))
        self.notes.setToolTip(self.tr("Anything a reader of the data should know (clouds, Moon, instrument)"))
        self.chart.setToolTip(self.tr("The identifier of the AAVSO chart (VSP) the comparison magnitudes come from"))
        self.filter.setToolTip(self.tr("Filter of the images, as AAVSO names it (CV: unfiltered, reduced to V)"))
        self.obscode.setToolTip(self.tr("Your AAVSO observer code"))
        self.star.setToolTip(self.tr("The variable's name as in AAVSO's VSX, e.g. AI DRA"))
        self.mags.setToolTip(
            self.tr("The comparison stars' magnitudes from the AAVSO chart (VSP), in the order the stars were marked")
        )
        form.addRow(self.tr("Star name (AAVSO VSX)"), self.star)
        form.addRow(self.tr("Observer code"), self.obscode)
        form.addRow(self.tr("Filter"), self.filter)
        form.addRow(self.tr("Catalogue magnitudes of the comparison stars"), self.mags)
        self.check = QLineEdit(self)
        self.check.setPlaceholderText(self.tr("label on the chart, e.g. 123"))
        self.check.setToolTip(
            self.tr(
                "The first check star's label on the chart; its magnitude goes into the report as a test of"
                " the comparison stars"
            )
        )
        form.addRow(self.tr("Check star (KNAME)"), self.check)
        form.addRow(self.tr("Chart ID"), self.chart)
        form.addRow(self.tr("Notes"), self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        mags = [float(v) for v in self.mags.text().replace(";", ",").split(",") if v.strip()]
        return {
            "star_name": self.star.text().strip(),
            "obscode": self.obscode.text().strip().upper(),
            "filt": self.filter.currentText(),
            "comp_mags": mags,
            "chart": self.chart.text().strip() or "na",
            "notes": self.notes.text().strip().replace(",", ";") or "na",
        }


def _without_frames(lc, excluded):
    """The light curve without the frames whose indices are in excluded: every per-frame list is filtered.
    Returns it and the original index of each kept frame."""
    n = len(lc["time"])
    keep = [i for i in range(n) if i not in excluded]
    if len(keep) == n:
        return lc, keep
    out = {k: [v[i] for i in keep] if isinstance(v, list) and len(v) == n else v for k, v in lc.items()}
    return out, keep


def export_csv(lc, path):
    """Light curve table as CSV (time, relative flux, error, raw fluxes)."""
    from astropy.table import Table

    t = Table(
        {
            lc["time_scale"]: lc["time"],
            "rel_flux": lc["rel_flux"],
            "rel_flux_err": lc["rel_flux_err"],
            "target_flux": lc["target_flux"],
            "file": lc["file"],
        }
    )
    for i, col in enumerate(np.asarray(lc["comp_flux"]).T):
        t[f"comp{i + 1}_flux"] = col
    if "airmass" in lc:
        t["airmass"] = lc["airmass"]
    from ..photometry.differential import delta_mag

    t["delta_mag"], t["delta_mag_err"] = delta_mag(lc["rel_flux"], lc["rel_flux_err"])
    if "mag" in lc:  # magnitudes from known (typed-in or catalogue) comparison magnitudes
        t[f"{lc['mag_band']}_mag"], t[f"{lc['mag_band']}_mag_err"] = lc["mag"], lc["mag_err"]
    for x in lc.get("extra") or []:  # check stars and further targets against the same ensemble
        t[f"{x['name']}_rel_flux"], t[f"{x['name']}_rel_flux_err"] = x["rel_flux"], x["rel_flux_err"]
        if "mag" in x:
            t[f"{x['name']}_mag"], t[f"{x['name']}_mag_err"] = x["mag"], x["mag_err"]
    if lc.get("fwhm"):
        t["fwhm"] = lc["fwhm"]
    t.write(path, format="csv", overwrite=True)
    return path
