"""Plan: observing site, date, targets (SIMBAD or coordinates, optional ephemeris), altitude chart, events."""

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

from .workspaces import PlotCanvas, _title

TARGET_COLUMNS = ("name", "ra", "dec", "t0", "period", "duration", "secondary")


class PlanPage(QWidget):
    resolve_requested = Signal(str)
    ephemeris_requested = Signal(str)  # name: VSX or NASA Exoplanet Archive
    plan_requested = Signal(dict, str, list, dict)  # site, date (YYYY-MM-DD), targets, params
    schedule_requested = Signal(list)  # blocks for the Observe page

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Plan"), self))

        site = self.settings.get("site", {"name": "", "lat": 39.9, "lon": 32.8, "height": 900.0})
        grid = QGridLayout()
        self.site_name = QLineEdit(site["name"], self)
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
        grid.addWidget(self.min_alt, 5, 1)
        lay.addLayout(grid)

        lay.addWidget(QLabel(self.tr("Targets: name (looked up in SIMBAD) or coordinates"), self))
        row = QHBoxLayout()
        self.target_input = QLineEdit(self)
        self.target_input.setPlaceholderText("HAT-P-32  |  02:04:10 +46:41:16")
        self.target_input.returnPressed.connect(self._add)
        add = QPushButton(self.tr("Add"), self)
        add.clicked.connect(self._add)
        ephem = QPushButton(self.tr("Add with ephemeris"), self)
        ephem.setToolTip(
            self.tr("Coordinates, period, epoch and duration from VSX (variable stars) or the NASA Exoplanet Archive")
        )
        ephem.clicked.connect(self._add_ephemeris)
        row.addWidget(self.target_input)
        row.addWidget(add)
        row.addWidget(ephem)
        lay.addLayout(row)
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
        remove = QPushButton(self.tr("Remove selected"), self)
        remove.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        lay.addWidget(remove)
        self.plan_button = QPushButton(self.tr("Plan the night"), self)
        self.plan_button.clicked.connect(self._plan)
        lay.addWidget(self.plan_button)
        row = QHBoxLayout()
        self.schedule_button = QPushButton(self.tr("Make a schedule"), self)
        self.schedule_button.setToolTip(
            self.tr("Eclipses and transits first, then the highest target in each hour of the night")
        )
        self.schedule_button.clicked.connect(self.make_schedule)
        self.send_button = QPushButton(self.tr("Send to the Observe page"), self)
        self.send_button.clicked.connect(lambda: self.schedule_requested.emit(self.blocks))
        for b in (self.schedule_button, self.send_button):
            b.setEnabled(False)
            row.addWidget(b)
        lay.addLayout(row)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        split.addWidget(left)

        right = QSplitter(Qt.Vertical, self)
        self.plot = PlotCanvas(self)
        right.addWidget(self.plot)
        self.events = QTableWidget(0, 6, self)
        self.events.setHorizontalHeaderLabels(
            [
                self.tr("Target"),
                self.tr("Event"),
                self.tr("Start (UTC)"),
                self.tr("Middle (UTC)"),
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

    def add_target(self, target: dict):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, key in enumerate(TARGET_COLUMNS[:3]):
            value = target[key]
            self.table.setItem(r, c, QTableWidgetItem(f"{value:.5f}" if isinstance(value, float) else str(value)))
        for c, key in zip(range(3, 6), ("t0", "period", "duration"), strict=True):
            value = target.get(key)
            self.table.setItem(r, c, QTableWidgetItem("" if value is None else repr(float(value))))
        check = QCheckBox(self.table)
        check.setChecked(bool(target.get("secondary")))
        self.table.setCellWidget(r, 6, check)
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
            self.status.setText(str(e))
            return
        self.settings.set("site", self.site())
        self.status.setText(self.tr("Computing…"))
        self._planned = targets
        self.plan_requested.emit(
            self.site(), self.date.date().toString("yyyy-MM-dd"), targets, {"min_alt": self.min_alt.value()}
        )

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

    def show_night(self, n):
        from astropy.time import Time

        self.result = n
        self.schedule_button.setEnabled(True)
        jd = np.asarray(n["jd"])
        midnight = np.floor(jd[0] + 0.5) - 0.5  # 00:00 UTC of the first date (JD days start at noon)
        hours = (jd - midnight) * 24
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        sun = np.asarray(n["sun_alt"])
        for level, shade in ((-0.8, 0.08), (-6, 0.15), (-12, 0.22), (-18, 0.3)):
            ax.fill_between(hours, 0, 90, where=sun < level, color="navy", alpha=shade, lw=0)
        for t in n["targets"]:
            ax.plot(hours, t["alt"], label=t["name"])
            for e in t["events"]:
                h = (e["mid"] - midnight) * 24
                ax.plot([h], [e["alt_mid"]], "v", color="red", ms=8)
        ax.plot(
            hours,
            n["moon_alt"],
            "--",
            color="gray",
            lw=1,
            label=self.tr("Moon ({p:.0f} %)").format(p=100 * n["moon_illumination"]),
        )
        ax.axhline(self.min_alt.value(), color="red", lw=0.6, ls=":")
        ax.set_ylim(0, 90)
        ax.set_xlim(hours[0], hours[-1])
        ax.set_xlabel(self.tr("UTC (hours)"))
        ax.set_ylabel(self.tr("Altitude (°)"))
        secax = ax.secondary_yaxis("right", functions=(_alt_to_airmass, _airmass_to_alt))
        secax.set_ticks([1.0, 1.2, 1.5, 2.0, 3.0])
        secax.set_ylabel(self.tr("Airmass"))
        ax.legend(fontsize="small", loc="upper right")
        self.plot.draw()

        rows = [(t["name"], e) for t in n["targets"] for e in t["events"]]
        self.events.setRowCount(len(rows))
        kinds = {"primary": self.tr("minimum I / transit"), "secondary": self.tr("minimum II")}

        def fmt(jd_value):
            return Time(jd_value, format="jd").iso[:16] if jd_value else "—"

        for r, (name, e) in enumerate(rows):
            for c, v in enumerate(
                (
                    name,
                    kinds[e["kind"]],
                    fmt(e["start"]),
                    fmt(e["mid"]),
                    fmt(e["end"]),
                    self.tr("yes") if e["full"] else self.tr("partly"),
                )
            ):
                self.events.setItem(r, c, QTableWidgetItem(v))
        dusk = fmt(n["dusk"]) if n["dusk"] else self.tr("no astronomical night")
        self.status.setText(
            self.tr("Astronomical night: {dusk} – {dawn} UTC; {n} events.").format(
                dusk=dusk, dawn=fmt(n["dawn"]) if n["dawn"] else "—", n=len(rows)
            )
        )


def _alt_to_airmass(alt):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 1 / np.sin(np.radians(np.clip(alt, 1, 90)))


def _airmass_to_alt(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.degrees(np.arcsin(1 / np.clip(x, 1, 60)))
