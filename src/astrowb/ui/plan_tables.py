"""The night in numbers, beside the Plan window's charts (as airmass.org lists them): the Sun's events, the Moon,
and every target's rise, set, highest point, best airmass and closest approach to the Moon — UTC and local time."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from .plan_chart import airmass_of, clock, crossing_hours


def tr(text):
    return QCoreApplication.translate("PlanTables", text)


def _when(h, offset):
    return (clock(h), clock(h + offset)) if h is not None else ("—", "—")


def sun_rows(n, hours, offset):
    """(event, UTC, local) for sunset, the three dusks, the three dawns and sunrise."""
    sun = np.asarray(n["sun_alt"], float)
    rows = []
    for name_down, name_up, level in (
        (tr("Sunset"), tr("Sunrise"), 0.0),
        (tr("Civil dusk (−6°)"), tr("Civil dawn (−6°)"), -6.0),
        (tr("Nautical dusk (−12°)"), tr("Nautical dawn (−12°)"), -12.0),
        (tr("Astronomical dusk (−18°)"), tr("Astronomical dawn (−18°)"), -18.0),
    ):
        down, up = crossing_hours(hours, sun, level)
        rows.append((name_down, level, down[0] if down else None, True))
        rows.append((name_up, level, up[0] if up else None, False))
    rows.sort(key=lambda r: (r[2] is None, r[2] if r[2] is not None else 0))
    return [(name, *_when(h, offset)) for name, _level, h, _down in rows]


def moon_rows(n, hours, offset):
    alt = np.asarray(n["moon_alt"], float)
    down, up = crossing_hours(hours, alt, 0.0)
    k = int(np.argmax(alt))
    return [
        (tr("Moonrise"), *_when(up[0] if up else None, offset)),
        (tr("Moonset"), *_when(down[0] if down else None, offset)),
        (tr("Highest ({alt:.0f}°)").format(alt=alt[k]), *_when(hours[k] if alt[k] > 0 else None, offset)),
        (tr("Illuminated"), f"{100 * n['moon_illumination']:.0f} %", ""),
    ]


def target_rows(n, hours, offset, min_alt):
    """(name, rises, sets, highest at, highest alt, best airmass, closest to the Moon) per target; times local."""
    dark = np.asarray(n["sun_alt"], float) < -0.8
    rows = []
    for t in n["targets"]:
        alt = np.asarray(t["alt"], float)
        down, up = crossing_hours(hours, alt, min_alt)
        k = int(np.argmax(np.where(dark, alt, -90)))  # the highest point in the dark
        sep = np.asarray(t.get("moon_sep") or [np.nan] * len(alt), float)
        close = np.nanmin(np.where(dark & (alt > 0), sep, np.nan)) if np.any(dark & (alt > 0)) else np.nan
        name = t["body"].capitalize() if t.get("body") else t["name"]
        rows.append((
            name,
            clock(up[0] + offset) if up else ("up" if alt[0] >= min_alt else "—"),
            clock(down[-1] + offset) if down else ("up" if alt[-1] >= min_alt else "—"),
            clock(hours[k] + offset) if alt[k] > 0 else "—",
            f"{alt[k]:.0f}°" if alt[k] > 0 else "—",
            f"{float(airmass_of(alt[k])):.2f}" if alt[k] > 0 else "—",
            f"{close:.0f}°" if np.isfinite(close) else "—",
        ))  # fmt: skip
    return rows


def _table(parent, headers, rows):
    table = QTableWidget(len(rows), len(headers), parent)
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().hide()
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            table.setItem(r, c, QTableWidgetItem(str(v)))
    table.setMinimumHeight(table.horizontalHeader().height() + sum(table.rowHeight(r) for r in range(len(rows))) + 4)
    return table


def tables_page(n, hours, offset, min_alt, parent=None):
    page = QWidget(parent)
    lay = QVBoxLayout(page)
    local = tr("Local (UTC{off})").format(off=f"{offset:+g}")
    heads = (tr("Sun"), tr("Moon"), tr("Targets"), tr("local time; above {alt:g}°").format(alt=min_alt))
    lay.addWidget(QLabel(f"<b>{heads[0]}</b>", page))
    page.sun = _table(page, [tr("Event"), "UTC", local], sun_rows(n, hours, offset))
    lay.addWidget(page.sun)
    lay.addWidget(QLabel(f"<b>{heads[1]}</b>", page))
    page.moon = _table(page, [tr("Event"), "UTC", local], moon_rows(n, hours, offset))
    lay.addWidget(page.moon)
    lay.addWidget(QLabel(f"<b>{heads[2]}</b>  ({heads[3]})", page))
    page.targets = _table(
        page,
        [tr("Target"), tr("Rises"), tr("Sets"), tr("Highest at"), tr("Altitude"), tr("Airmass"), tr("Moon closest")],
        target_rows(n, hours, offset, min_alt),
    )
    lay.addWidget(page.targets)
    lay.addStretch(1)
    return page
