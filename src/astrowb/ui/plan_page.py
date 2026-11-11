"""Plan: observing site, date, targets (SIMBAD or coordinates, optional ephemeris), altitude chart, events."""

from datetime import UTC, datetime

import numpy as np
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import profiles
from .converter_dialog import converter_button
from .kit.help import help_line
from .kit.widgets import PlotCanvas, _title
from .messages import translate
from .undo import Undoable, track_typing

AUTO = -13.0  # the UTC offset box's lowest value, shown as "Auto": this computer's time zone
TARGET_COLUMNS = ("name", "ra", "dec", "t0", "period", "duration", "secondary")


class PlanPage(Undoable, QWidget):
    resolve_requested = Signal(str)
    ephemeris_requested = Signal(str)  # name: VSX or NASA Exoplanet Archive
    plan_requested = Signal(dict, str, list, dict)  # site, date (YYYY-MM-DD), targets, params
    schedule_requested = Signal(list)  # blocks for the Observe page

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.settings = settings
        self.result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Planning"), self))
        from .kit.widgets import StepGuide

        self.guide = StepGuide(
            [
                (
                    self.tr("Set the site and the night"),
                    self.tr("Choose the observatory or type its latitude, longitude and height, and set the date."),
                ),
                (
                    self.tr("Add the targets"),
                    self.tr("Type a name and press Add; for eclipses and transits press Add with ephemeris."),
                ),
                (
                    self.tr("Plan the night: altitude, airmass, the Moon, events"),
                    self.tr("Press Plan the night and look at the visibility chart."),
                ),
                (
                    self.tr("Optional: exposure time"),
                    self.tr("Exposure time… estimates the exposure for a signal-to-noise."),
                ),
                (
                    self.tr("Make a schedule and send it to the Observing window"),
                    self.tr("Press Make a schedule, check it, then Send to the Observing window."),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)

        site = profiles.section(self.settings, "site")
        grid = QGridLayout()
        self.site_name = QLineEdit(site["name"], self)
        self.site_name.setPlaceholderText(self.tr("observatory name, e.g. TUG, Roque de los Muchachos"))
        self.site_name.setToolTip(self.tr("Type the name of a known observatory to fill in its position"))
        from PySide6.QtWidgets import QCompleter

        from ..planning.sites import observatories

        completer = QCompleter(sorted(observatories(), key=str.lower), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.site_name.setCompleter(completer)
        completer.activated.connect(self._known_site)
        self.site_name.editingFinished.connect(lambda: self._known_site(self.site_name.text()))
        self.lat, self.lon, self.height = (
            self._spin(site[k], lo, hi, d)
            for k, lo, hi, d in (("lat", -90, 90, 4), ("lon", -180, 180, 4), ("height", -500, 6000, 0))
        )
        for row, (label, w) in enumerate(
            (
                (self.tr("Site"), self.site_name),
                (self.tr("Latitude (°, N+)"), self.lat),
                (self.tr("Longitude (°, E+)"), self.lon),
                (self.tr("Height (m)"), self.height),
            )
        ):
            grid.addWidget(QLabel(label, self), row, 0)
            grid.addWidget(w, row, 1)
        self.date = QDateEdit(QDate.currentDate(), self)
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(QLabel(self.tr("Night starting on"), self), 4, 0)
        grid.addWidget(self.date, 4, 1)
        self.min_alt = self._spin(20.0, 0, 80, 0)
        grid.addWidget(QLabel(self.tr("Lowest altitude (°)"), self), 5, 0)
        self.min_alt.setToolTip(
            self.tr(
                "Targets below this altitude count as not observable (trees, buildings, thick air near the horizon)"
            )
        )
        self.date.setToolTip(self.tr("The evening on which the night begins (local date)"))
        self.height.setToolTip(self.tr("Height above sea level in metres"))
        self.lon.setToolTip(self.tr("Longitude of the site in degrees, east positive (west of Greenwich is negative)"))
        self.lat.setToolTip(self.tr("Latitude of the site in degrees, north positive"))
        grid.addWidget(self.min_alt, 5, 1)
        self.utc_offset = self._spin(self.settings.get("plan.utc_offset", AUTO), AUTO, 14, 1)
        self.utc_offset.setSingleStep(0.5)
        self.utc_offset.setSpecialValueText(self.tr("Auto"))
        self.utc_offset.setToolTip(
            self.tr(
                "Hours to add to UTC for the local time shown above the chart and in the events (Turkey: 3). Auto: "
                "this computer's time zone on the night's date, summer time included; type the offset for an "
                "observatory in another time zone"
            )
        )
        grid.addWidget(QLabel(self.tr("Local time (hours from UTC)"), self), 6, 0)
        grid.addWidget(self.utc_offset, 6, 1)
        lay.addLayout(grid)

        lay.addWidget(QLabel(self.tr("Targets: name (looked up in SIMBAD), coordinates, or a planet / the Moon"), self))
        row = QHBoxLayout()
        self.target_input = QLineEdit(self)
        self.target_input.setPlaceholderText("HAT-P-32  |  02:04:10 +46:41:16  |  Saturn")
        self.target_input.returnPressed.connect(self._add)
        self.target_input.setToolTip(
            self.tr(
                "A star name (looked up in SIMBAD, needs the internet), coordinates RA Dec, or a planet / the Moon "
                "(followed through the night, works offline); Enter adds it"
            )
        )
        self.add_button = add = QPushButton(self.tr("Add"), self)
        add.clicked.connect(self._add)
        add.setToolTip(
            self.tr(
                "Adds the target with its coordinates only: enough to see when it is high in the sky. Several "
                "targets (stars, planets, the Moon) are drawn together in one chart"
            )
        )
        self.ephemeris_button = ephem = QPushButton(self.tr("Add with ephemeris"), self)
        ephem.setToolTip(
            self.tr(
                "An ephemeris is the timetable of a variable star or planet: the time of one minimum or transit (T0) "
                "and the period, from which every later one is computed. This button adds the target with its "
                "coordinates and its T0, period and duration from VSX (variable stars) or the NASA Exoplanet "
                "Archive; the night plan then lists the eclipses / transits you can observe"
            )
        )
        ephem.clicked.connect(self._add_ephemeris)
        row.addWidget(self.target_input)
        row.addWidget(add)
        row.addWidget(ephem)
        lay.addLayout(row)
        hint = help_line(self.tr("Add: position only. Add with ephemeris: also the times of its eclipses or "
                                 "transits."), "planning-adding-targets", self)  # fmt: skip
        lay.addWidget(hint)
        self.table = QTableWidget(0, len(TARGET_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                "RA (°)",
                "Dec (°)",
                self.tr("T0 (BJD)"),
                self.tr("Period (d)"),
                self.tr("Duration (d)"),
                self.tr("Secondary"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setToolTip(self.tr("Enter T0 and period to list minima / transits of the night."))
        lay.addWidget(self.table, 1)
        track_typing(self, self.table, self.tr("type a value"))
        self.remove_button = remove = QPushButton(self.tr("Remove selected"), self)
        remove.clicked.connect(
            lambda: self.edit(self.tr("remove a target"), self.table.removeRow, self.table.currentRow())
        )
        remove.setToolTip(self.tr("Removes the selected target from the list"))
        self.exposure_button = exposure = QPushButton(self.tr("Exposure time…"), self)
        exposure.setToolTip(self.tr("How long to expose for a wanted signal-to-noise, and when a star saturates"))
        exposure.clicked.connect(self.exposure_dialog)
        row = QHBoxLayout()
        for w in (remove, exposure, converter_button(self)):
            row.addWidget(w)
        lay.addLayout(row)
        self.plan_button = QPushButton(self.tr("Plan the night"), self)
        self.plan_button.clicked.connect(self._plan)
        self.plan_button.setToolTip(
            self.tr(
                "Altitude of every target through the night with twilight and the Moon, and the minima / "
                "transits that fall in the dark hours"
            )
        )
        lay.addWidget(self.plan_button)
        row = QHBoxLayout()
        self.schedule_button = QPushButton(self.tr("Make a schedule"), self)
        self.schedule_button.setToolTip(
            self.tr("Eclipses and transits first, then the highest target in each hour of the night")
        )
        self.schedule_button.clicked.connect(self.make_schedule)
        self.send_button = QPushButton(self.tr("Send to the Observing window"), self)
        self.send_button.clicked.connect(lambda: self.schedule_requested.emit(self.blocks))
        self.send_button.clicked.connect(lambda: self.guide.set_state(4, "done"))
        self.send_button.setToolTip(
            self.tr(
                "The schedule becomes the night plan of the Observing window; you still check it and start it there"
            )
        )
        for b in (self.schedule_button, self.send_button):
            b.setEnabled(False)
            row.addWidget(b)
        lay.addLayout(row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        from PySide6.QtWidgets import QScrollArea

        # the fields scroll on their own: on a short window the whole page scrolled and the chart's lower part
        # (below ~20°) was out of sight — the owner thought the chart started at 20°
        scroll = QScrollArea(self)
        scroll.setWidget(left)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(left.sizeHint().width() + 20)
        split.addWidget(scroll)

        right = QSplitter(Qt.Vertical, self)
        self.plot = PlotCanvas(self)
        right.addWidget(self.plot)
        self.events = QTableWidget(0, 7, self)
        self.events.setHorizontalHeaderLabels(
            [
                self.tr("Target"),
                self.tr("Event"),
                self.tr("Start (UTC)"),
                self.tr("Middle (UTC)"),
                self.tr("Middle (local)"),
                self.tr("End (UTC)"),
                self.tr("Observable"),
            ]
        )
        self.events.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.events.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.events)
        self.schedule_table = QTableWidget(0, 4, self)
        self.schedule_table.setHorizontalHeaderLabels(
            [self.tr("Target"), self.tr("Start (UTC)"), self.tr("End (UTC)"), self.tr("Why")]
        )
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right.addWidget(self.schedule_table)
        right.setSizes([480, 160, 160])
        right.setStretchFactor(0, 1)  # the chart takes what the window gives; the tables keep their share
        self.blocks = []
        split.addWidget(right)
        split.setSizes([430, 800])
        QVBoxLayout(self).addWidget(split)

    def _spin(self, value, lo, hi, decimals):
        w = QDoubleSpinBox(self)
        w.setRange(lo, hi)
        w.setDecimals(decimals)
        w.setValue(value)
        return w

    def site(self):
        return {
            "name": self.site_name.text(),
            "lat": self.lat.value(),
            "lon": self.lon.value(),
            "height": self.height.value(),
        }

    def _add(self):
        text = self.target_input.text().strip()
        if text:
            self.status.setText(self.tr("Looking up {name}…").format(name=text))
            self.resolve_requested.emit(text)

    # --- undo / redo (Edit menu, Ctrl+Z / Ctrl+Y) -----------------------------
    def undo_state(self):
        return tuple(
            (*(self._cell(r, c) for c in range(6)), bool(w and w.isChecked()))
            for r in range(self.table.rowCount())
            for w in [self.table.cellWidget(r, 6)]
        )

    def set_undo_state(self, rows):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, text in enumerate(row[:6]):
                self.table.setItem(r, c, QTableWidgetItem(text))
            self._secondary_box(r, row[6])
        self.table.blockSignals(False)

    def _secondary_box(self, r, on):
        check = QCheckBox(self.table)
        check.setChecked(on)
        check.setToolTip(self.tr("Also list the secondary minima (half a period after the primary)"))
        check.toggled.connect(lambda _on: self.record(self.tr("secondary minima"), self._typed_from))
        self.table.setCellWidget(r, 6, check)

    def add_target(self, target: dict):
        self.edit(self.tr("add a target"), self._add_target, target)

    def _add_target(self, target: dict):
        for i in (0, 1):
            self.guide.set_state(i, "done")
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, key in enumerate(TARGET_COLUMNS[:3]):
            value = target[key]
            self.table.setItem(r, c, QTableWidgetItem(f"{value:.5f}" if isinstance(value, float) else str(value)))
        for c, key in zip(range(3, 6), ("t0", "period", "duration"), strict=True):
            value = target.get(key)
            self.table.setItem(r, c, QTableWidgetItem("" if value is None else repr(float(value))))
        self._secondary_box(r, bool(target.get("secondary")))
        self.target_input.clear()
        self.status.setText(self.tr("{name} added ({source}).").format(name=target["name"], source=target["source"]))

    def _add_ephemeris(self):
        name = self.target_input.text().strip()
        if name:
            self.status.setText(self.tr("Looking up {name}…").format(name=name))
            self.ephemeris_requested.emit(name)

    def _cell(self, r, c):
        item = self.table.item(r, c)
        return item.text().strip() if item else ""

    def targets(self):
        out = []
        for r in range(self.table.rowCount()):
            t = {"name": self._cell(r, 0), "ra": float(self._cell(r, 1)), "dec": float(self._cell(r, 2))}
            try:
                if self._cell(r, 3) and self._cell(r, 4):
                    t |= {"t0": float(self._cell(r, 3)), "period": float(self._cell(r, 4))}
                    if self._cell(r, 5):
                        t["duration"] = float(self._cell(r, 5))
                    t["secondary"] = self.table.cellWidget(r, 6).isChecked()
            except ValueError:
                msg = self.tr("Row {row}: T0, period and duration must be numbers").format(row=r + 1)
                raise ValueError(msg) from None
            out.append(t)
        return out

    def _plan(self):
        try:
            targets = self.targets()
        except ValueError as e:
            self.status.setText(translate(e))
            return
        profiles.update(self.settings, "site", **self.site())
        self.settings.set("plan.utc_offset", self.utc_offset.value())
        self.status.setText(self.tr("Computing…"))
        self._planned = targets
        self.plan_requested.emit(
            self.site(), self.date.date().toString("yyyy-MM-dd"), targets, {"min_alt": self.min_alt.value()}
        )

    def _known_site(self, name):
        """A known observatory's name fills its latitude, longitude and height."""
        from ..planning.sites import find

        where = find(name)
        if where:
            for box, value in zip((self.lat, self.lon, self.height), where, strict=True):
                box.setValue(value)
        return where

    def converter_dialog(self):
        from .converter_dialog import ConverterDialog

        dlg = ConverterDialog(self.settings, self)
        dlg.show()
        return dlg

    def exposure_dialog(self):
        from .exposure_dialog import ExposureDialog

        dlg = ExposureDialog(self.settings, self)
        self.guide.set_state(3, "done")
        dlg.show()
        return dlg

    def make_schedule(self):
        from astropy.time import Time

        from ..planning.schedule import schedule

        self.blocks = schedule(self.result, self._planned, min_alt=max(self.min_alt.value(), 0.0))
        why = {"event": self.tr("eclipse / transit"), "best altitude": self.tr("highest target")}
        self.schedule_table.setRowCount(len(self.blocks))
        for r, b in enumerate(self.blocks):
            cells = (
                b["name"],
                Time(b["start"], format="jd").iso[:16],
                Time(b["end"], format="jd").iso[:16],
                why[b["why"]],
            )
            for c, text in enumerate(cells):
                self.schedule_table.setItem(r, c, QTableWidgetItem(text))
        self.send_button.setEnabled(bool(self.blocks))
        if not self.blocks:
            self.status.setText(self.tr("No target is high enough during the dark hours."))
        return self.blocks

    def local_offset(self, jd):
        """Hours from UTC to the local time: the typed offset, or this computer's on that date (Auto)."""
        if self.utc_offset.value() > AUTO:
            return self.utc_offset.value()
        when = datetime.fromtimestamp((jd - 2440587.5) * 86400, UTC).astimezone()
        return when.utcoffset().total_seconds() / 3600

    def show_night(self, n):
        from astropy.time import Time

        self.result = n
        self.schedule_button.setEnabled(True)
        self.guide.set_state(2, "done")
        jd = np.asarray(n["jd"])
        midnight = np.floor(jd[0] + 0.5) - 0.5  # 00:00 UTC of the first date (JD days start at noon)
        hours = (jd - midnight) * 24
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        sun = np.asarray(n["sun_alt"])
        for level, shade in ((-0.8, 0.08), (-6, 0.15), (-12, 0.22), (-18, 0.3)):
            ax.fill_between(hours, 0, 90, where=sun < level, color="navy", alpha=shade, lw=0)
        off = self.local_offset(jd[len(jd) // 2])
        # the chart is in English whatever the interface language: it goes into papers and reports
        for t in n["targets"]:
            ax.plot(hours, t["alt"], label=t["body"].capitalize() if t.get("body") else t["name"])
            for e in t["events"]:
                h = (e["mid"] - midnight) * 24
                ax.plot([h], [e["alt_mid"]], "v", color="red", ms=8)
        if not any(t.get("body") == "moon" for t in n["targets"]):  # typed: drawn above as a target
            ax.plot(
                hours,
                n["moon_alt"],
                "--",
                color="gray",
                lw=1,
                label=f"Moon ({100 * n['moon_illumination']:.0f} %)",
            )
        ax.axhline(self.min_alt.value(), color="red", lw=0.6, ls=":")
        ax.set_ylim(0, 90)
        ax.set_xlim(hours[0], hours[-1])
        ax.xaxis.set_major_formatter(lambda h, _pos: f"{h % 24:g}")  # 25 h is 1 h UTC the next day
        ax.set_xlabel("UTC (hours)")
        ax.set_ylabel("Altitude (°)")
        top = ax.secondary_xaxis("top", functions=(lambda h: h + off, lambda h: h - off))
        top.xaxis.set_major_formatter(lambda h, _pos: f"{h % 24:g}")
        top.set_xlabel(f"Local time (UTC{off:+g}, hours)")
        secax = ax.secondary_yaxis("right", functions=(_alt_to_airmass, _airmass_to_alt))
        secax.set_ticks([1.0, 1.2, 1.5, 2.0, 3.0])
        secax.set_ylabel("Airmass")
        ax.legend(fontsize="small", loc="upper right")
        self.plot.draw()

        rows = [(t["name"], e) for t in n["targets"] for e in t["events"]]
        self.events.setRowCount(len(rows))
        kinds = {"primary": self.tr("minimum I / transit"), "secondary": self.tr("minimum II")}

        def fmt(jd_value):
            return Time(jd_value, format="jd").iso[:16] if jd_value else "—"

        def local(jd_value):
            return Time(jd_value + off / 24, format="jd").iso[11:16] if jd_value else "—"

        for r, (name, e) in enumerate(rows):
            for c, v in enumerate(
                (
                    name,
                    kinds[e["kind"]],
                    fmt(e["start"]),
                    fmt(e["mid"]),
                    local(e["mid"]),
                    fmt(e["end"]),
                    self.tr("yes") if e["full"] else self.tr("partly"),
                )
            ):
                self.events.setItem(r, c, QTableWidgetItem(v))
        dusk = fmt(n["dusk"]) if n["dusk"] else self.tr("no astronomical night")
        self.status.setText(
            self.tr("Astronomical night: {dusk} – {dawn} UTC ({ldusk} – {ldawn} local, UTC{off}); {n} events.").format(
                dusk=dusk,
                dawn=fmt(n["dawn"]) if n["dawn"] else "—",
                ldusk=local(n["dusk"]),
                ldawn=local(n["dawn"]),
                off=f"{off:+g}",
                n=len(rows),
            )
        )


def _alt_to_airmass(alt):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 1 / np.sin(np.radians(np.clip(alt, 1, 90)))


def _airmass_to_alt(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.degrees(np.arcsin(1 / np.clip(x, 1, 60)))
