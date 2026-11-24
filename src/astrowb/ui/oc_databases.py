"""The Minima stage's "From databases…" dialog (plans/oc.md OC-4): every service of literature minima with its
citation line; Fetch for those queried by program (Villanova by KIC, BAV LkDB by name), Open the page for the
others. Fetched minima are merged into the minima text with their source; a minimum already there (same kind,
within 0.002 d, OC-1.5) is not added again."""

import re

import numpy as np
from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QPushButton

from ..services import minima_bav, minima_villanova
from ..timeseries.ephemeris import parse_minima
from .kit.dialogs import Dialog

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcDatabases", "…") calls
_METHOD = {"ccd": "CCD", "pe": "pe", "pg": "pg", "vis": "vis"}  # minima_table methods parse_minima reads back
# the services read but not queried by program (plans/oc.md OC-4): name, page, citation
PAGES = (
    ("VarAstro", "https://var.astro.cz",
     "Hykel J., Brát L., Dub M., Přibík V., VarAstro portal, Variable Star and Exoplanet Section of the Czech "
     "Astronomical Society, https://var.astro.cz; and each minimum's Publication"),
    ("AAVSO, B. Nelson's O−C files", "https://www.aavso.org/bob-nelsons-o-c-files", ""),
    ("Kreiner, Kraków (elements only)", "https://www.as.up.krakow.pl/ephem/",
     "Kreiner J. M., 2004, Acta Astron. 54, 207"),
    ("TIDAK, Timing Database at Kraków", "https://www.as.up.krakow.pl/tidak/",
     "Ogloza W., Stachowski G., Zakrzewski B., Żejmo M., 2022, PTA Proc. 12, 216"),
)  # fmt: skip


_STANDARDS = ("BJD_TDB", "BJD_UTC", "HJD_UTC", "HJD_TT", "JD_UTC")  # as the text names them (JD_UTC last)


def table_standard(text):
    """The minima text's time standard: one it names, "HJD unknown" for HJD without a scale (ARC-15), None for an
    empty text (any standard fits), "not stated" otherwise."""
    from ..timeseries.ephemeris import hjd_scale_unknown

    minima = parse_minima(text)
    words = text.upper().replace(" ", "_")
    named = [s for s in _STANDARDS if s in words]
    if named:
        return named[0]
    if hjd_scale_unknown(text, [m.time for m in minima]):
        return "HJD unknown"
    return "not stated" if minima else None


def _coordinates(page):
    """The star's SkyCoord from the last Look up of the name typed now, or None."""
    name, ra, dec = getattr(page, "star_coords", (None, None, None))
    if name != page.star.text().strip() or ra is None or dec is None:
        return None
    from astropy.coordinates import SkyCoord

    return SkyCoord(ra, dec, unit="deg")


def merged(page, rows, service):
    """Merge the records `rows` (minima_table) into the page's minima text in the text's time standard and say what
    was done. Rows of another standard are converted to BJD_TDB (minima_table.add_bjd) when the table is in BJD_TDB
    and the star's coordinates are known; otherwise they are refused and the reason said."""
    have = table_standard(page.text.toPlainText())
    given = {r["standard_original"] for r in rows}
    shown = {"HJD unknown": translate("OcDatabases", "HJD (time scale not stated)"),
             "not stated": translate("OcDatabases", "a time standard not stated")}  # fmt: skip
    if not rows:
        return translate("OcDatabases", "{service} has no minima for this star.").format(service=service)
    note = ""
    if have is not None and given != {have}:
        std = ", ".join(shown.get(g, g) for g in sorted(given))
        if have != "BJD_TDB":
            return translate("OcDatabases", "{service} gives its times in {std}, the table's are in {table}: nothing "
                             "was added.").format(service=service, std=std, table=shown.get(have, have))  # fmt: skip
        target = _coordinates(page)
        if target is None:
            return translate("OcDatabases", "{service} gives its times in {std}: converting them to the table's "
                             "BJD_TDB needs the star's coordinates. Press Look up in the Ephemeris stage, then fetch "
                             "again.").format(service=service, std=std)  # fmt: skip
        from ..timeseries.minima_table import add_bjd

        grown = add_bjd(rows, target)
        note = " " + translate("OcDatabases", "Converted from {std} to BJD_TDB with the star's coordinates.").format(
            std=std
        )
        if grown:
            note += " " + translate("OcDatabases", "HJD without a time scale: TT − UTC added to their errors.")
    header = None
    if have is None:  # an empty table takes the service's standard, written where the summary line reads it
        have = given.pop() if len(given) == 1 else "not stated"
        header = {"HJD unknown": "# times: HJD", "not stated": None}.get(have, f"# times: {have}")
    added, there = merge(page, rows, have == "BJD_TDB", header)
    text = translate("OcDatabases", "{n} minima added from {service}.").format(n=added, service=service)
    if there:
        text += " " + translate("OcDatabases", "{n} were already in the table.").format(n=there)
    return text + note


def merge(page, rows, bjd=False, header=None):
    """Append the records `rows` to the minima text (their BJD_TDB when `bjd`, else the time as given) with their
    source; a minimum already there (same kind, within 0.002 d, OC-1.5) is not added. Returns (added, there)."""
    have = parse_minima(page.text.toPlainText())
    times, kinds = [m.time for m in have], [m.kind for m in have]
    lines = []
    for r in rows:
        t = r["bjd_tdb"] if bjd else r["time_original"]
        if np.any((np.abs(np.asarray(times) - t) <= 0.002) & (np.asarray(kinds) == r["kind"])):
            continue
        times.append(t)
        kinds.append(r["kind"])
        source = r["source"].replace("#", " ")  # "#" starts a comment in the text
        lines.append(f"{t!r} {r['error']!r} {r['kind']} {_METHOD.get(r['method'], '')} {source}")
    if lines:
        page.text.appendPlainText("\n".join([header, *lines] if header else lines))
    return len(lines), len(rows) - len(lines)


def open_dialog(page, main):
    from .messages import translate as message

    d = Dialog(translate("OcDatabases", "Minima from databases"), page, getattr(main, "settings", None), "oc_db")
    grid = QGridLayout()
    d.body.addLayout(grid)
    d.status = QLabel(d)
    d.status.setWordWrap(True)
    d.status.setObjectName("databases_status")

    def label(text, row, col=0, span=1):
        w = QLabel(text, d)
        w.setWordWrap(True)
        grid.addWidget(w, row, col, 1, span)
        return w

    def fetch(name, step, inputs):
        d.status.setText(translate("OcDatabases", "Asking {service}…").format(service=name))

        def done(out):
            try:
                d.status.setText(merged(page, out["minima"], name))
            except ValueError as e:  # the minima text has a line that is not a time
                d.status.setText(message(str(e)))

        main.run_step_for("oc", step, inputs, {}, on_done=done, on_fail=lambda msg: d.status.setText(message(msg)))

    def fetch_kic():
        try:
            kic = int(d.kic.text().strip())
        except ValueError:
            d.status.setText(translate("OcDatabases", "Give the star's KIC number."))
            return
        fetch("Villanova", "timeseries.villanova_minima", {"kic": kic})

    def fetch_name():
        if not page.star.text().strip():
            d.status.setText(translate("OcDatabases", "Type the star's name in the Ephemeris stage first."))
            return
        fetch("BAV LkDB", "timeseries.bav_minima", {"name": page.star.text().strip()})

    label(translate("OcDatabases", "Villanova Kepler EB catalogue"), 0)
    d.kic = QLineEdit(d)
    d.kic.setPlaceholderText("KIC")
    kic = re.fullmatch(r"\s*KIC\s*(\d+)\s*", page.star.text(), re.I)
    d.kic.setText(kic.group(1) if kic else "")
    grid.addWidget(d.kic, 0, 1)
    d.villanova = QPushButton(translate("OcDatabases", "Fetch"), d)
    d.villanova.clicked.connect(fetch_kic)
    grid.addWidget(d.villanova, 0, 2)
    label(minima_villanova.CITATION, 1, 0, 3)
    label(translate("OcDatabases", "BAV Lichtenknecker-Database (by the star's name)"), 2, 0, 2)
    d.bav = QPushButton(translate("OcDatabases", "Fetch"), d)
    d.bav.clicked.connect(fetch_name)
    grid.addWidget(d.bav, 2, 2)
    d.bav_note = label(
        minima_bav.CITATION + ". " + translate(
            "OcDatabases", "For your own use only: the database's terms forbid passing its data on."
        ), 3, 0, 3,
    )  # fmt: skip
    for k, (name, url, cite) in enumerate(PAGES):
        label(name, 4 + 2 * k, 0, 2)
        b = QPushButton(translate("OcDatabases", "Open the page"), d)
        b.setToolTip(url)
        b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        grid.addWidget(b, 4 + 2 * k, 2)
        label(cite or translate("OcDatabases", "The page asks for no citation."), 5 + 2 * k, 0, 3)
    d.body.addWidget(d.status)
    d.add_buttons(translate("OcDatabases", "Close"))
    return d


def add_button(page, main):
    """The "From databases…" button beside Load file in the Minima stage."""
    page.databases_button = QPushButton(translate("OcDatabases", "From databases…"), page)
    page.databases_button.setToolTip(
        translate("OcDatabases", "Minima of the star from the literature databases, with their citations")
    )
    page.databases_button.clicked.connect(lambda: open_dialog(page, main).open())
    set_ephemeris = page.set_ephemeris

    def keep_coordinates(target):  # the look-up's coordinates convert fetched HJD to BJD_TDB (merged)
        page.star_coords = (page.star.text().strip(), target.get("ra"), target.get("dec"))
        return set_ephemeris(target)

    page.set_ephemeris = keep_coordinates
    box = page.stage_boxes["minima"].layout()
    for i in range(box.count()):
        row = box.itemAt(i).layout()
        if row is not None and row.indexOf(page.load_button) >= 0:
            row.insertWidget(row.indexOf(page.load_button) + 1, page.databases_button)
