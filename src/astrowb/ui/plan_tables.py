"""The night in numbers, beside the Plan window's charts (as airmass.org lists them): the Sun's events, the Moon,
and every target's rise, set, highest point, best airmass and closest approach to the Moon — UTC and local time."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from .plan_chart import airmass_of, clock, crossing_hours

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


def _when(h, offset):
    return (clock(h), clock(h + offset)) if h is not None else ("—", "—")


def sun_rows(n, hours, offset):
    """(event, UTC, local) for sunset, the three dusks, the three dawns and sunrise."""
    sun = np.asarray(n["sun_alt"], float)
    rows = []
    for name_down, name_up, level in (
        (translate("PlanTables", "Sunset"), translate("PlanTables", "Sunrise"), 0.0),
        (translate("PlanTables", "Civil dusk (−6°)"), translate("PlanTables", "Civil dawn (−6°)"), -6.0),
        (translate("PlanTables", "Nautical dusk (−12°)"), translate("PlanTables", "Nautical dawn (−12°)"), -12.0),
        (
            translate("PlanTables", "Astronomical dusk (−18°)"),
            translate("PlanTables", "Astronomical dawn (−18°)"),
            -18.0,
        ),
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
        (translate("PlanTables", "Moonrise"), *_when(up[0] if up else None, offset)),
        (translate("PlanTables", "Moonset"), *_when(down[0] if down else None, offset)),
        (
            translate("PlanTables", "Highest ({alt:.0f}°)").format(alt=alt[k]),
            *_when(hours[k] if alt[k] > 0 else None, offset),
        ),
        (translate("PlanTables", "Illuminated"), f"{100 * n['moon_illumination']:.0f} %", ""),
    ]


def target_rows(n, hours, offset, min_alt):
    """(name, rises, sets, highest at, highest alt, best airmass, closest to the Moon) per target; times local."""
    dark = np.asarray(n["sun_alt"], float) < -0.8
    rows = []
    for t in n["targets"]:
        alt = np.asarray(t["alt"], float)
        floor = np.asarray(t.get("limit") or np.full(len(alt), min_alt), float)  # the horizon profile, when given
        down, up = crossing_hours(hours, alt - floor, 0.0)
        k = int(np.argmax(np.where(dark, alt, -90)))  # the highest point in the dark
        sep = np.asarray(t.get("moon_sep") or [np.nan] * len(alt), float)
        close = np.nanmin(np.where(dark & (alt > 0), sep, np.nan)) if np.any(dark & (alt > 0)) else np.nan
        name = t["body"].capitalize() if t.get("body") else t["name"]
        rows.append((
            name,
            clock(up[0] + offset) if up else ("up" if alt[0] >= floor[0] else "—"),
            clock(down[-1] + offset) if down else ("up" if alt[-1] >= floor[-1] else "—"),
            clock(hours[k] + offset) if alt[k] > 0 else "—",
            f"{alt[k]:.0f}°" if alt[k] > 0 else "—",
            f"{float(airmass_of(alt[k])):.2f}" if alt[k] > 0 else "—",
            f"{close:.0f}°" if np.isfinite(close) else "—",
        ))  # fmt: skip
    return rows


def standard_rows(n, hours, offset, kind="telluric"):
    """(target, telluric standard, local time, its airmass, the target's, separation) at each fixed target's highest
    point in the dark: the nearest standard within 0.1 airmass (PLN-9)."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.time import Time

    from ..planning import standards
    from ..planning.visibility import Site

    site = Site(**{k: n["site"][k] for k in ("name", "lat", "lon", "height")})
    rows, out = standards.load(kind), []
    dark = np.asarray(n["sun_alt"], float) < -12
    for t in n["targets"]:
        if "ra" not in t or not dark.any():
            continue
        alt = np.where(dark, np.asarray(t["alt"], float), -90)
        k = int(np.argmax(alt))
        if alt[k] <= 20:
            continue
        found = standards.matching(SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg), Time(n["jd"][k], format="jd"),
                                   site, rows, limit=1)  # fmt: skip
        if found:
            s = found[0]
            out.append((t["name"], s["name"], clock(hours[k] + offset), f"{s['airmass']:.2f}",
                        f"{s['target_airmass']:.2f}", f"{s['separation']:.0f}°"))  # fmt: skip
        else:
            out.append((t["name"], "—", clock(hours[k] + offset), "—", f"{float(airmass_of(alt[k])):.2f}", "—"))
    return out


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
    local = translate("PlanTables", "Local (UTC{off})").format(off=f"{offset:+g}")
    heads = (
        translate("PlanTables", "Sun"),
        translate("PlanTables", "Moon"),
        translate("PlanTables", "Targets"),
        translate("PlanTables", "local time; above {alt:g}°").format(alt=min_alt),
    )
    lay.addWidget(QLabel(f"<b>{heads[0]}</b>", page))
    page.sun = _table(page, [translate("PlanTables", "Event"), "UTC", local], sun_rows(n, hours, offset))
    lay.addWidget(page.sun)
    lay.addWidget(QLabel(f"<b>{heads[1]}</b>", page))
    page.moon = _table(page, [translate("PlanTables", "Event"), "UTC", local], moon_rows(n, hours, offset))
    lay.addWidget(page.moon)
    lay.addWidget(QLabel(f"<b>{heads[2]}</b>  ({heads[3]})", page))
    page.targets = _table(
        page,
        [
            translate("PlanTables", "Target"),
            translate("PlanTables", "Rises"),
            translate("PlanTables", "Sets"),
            translate("PlanTables", "Highest at"),
            translate("PlanTables", "Altitude"),
            translate("PlanTables", "Airmass"),
            translate("PlanTables", "Moon closest"),
        ],
        target_rows(n, hours, offset, min_alt),
    )
    lay.addWidget(page.targets)
    note = translate("PlanTables", "nearest at the same airmass, at the target’s highest point")
    heads = [translate("PlanTables", "Target"), translate("PlanTables", "Standard"), translate("PlanTables", "At"),
             translate("PlanTables", "Its airmass"), translate("PlanTables", "Target airmass"),
             translate("PlanTables", "Distance")]  # fmt: skip
    for attr, kind, title, tip in (
        ("standards", "telluric", translate("PlanTables", "Telluric standards"),
         translate("PlanTables", "Hot bright stars from Hipparcos (van Leeuwen 2007) to remove the atmosphere's "
                   "lines from a spectrum")),
        ("photometric", "landolt1992", translate("PlanTables", "Photometric standards"),
         translate("PlanTables", "Landolt (1992) UBVRI standard stars: the night's zero points and extinction")),
    ):  # fmt: skip
        lay.addWidget(QLabel(f"<b>{title}</b>  ({note})", page))
        table = _table(page, heads, standard_rows(n, hours, offset, kind))
        table.setToolTip(tip)
        setattr(page, attr, table)
        lay.addWidget(table)
    lay.addStretch(1)
    return page
