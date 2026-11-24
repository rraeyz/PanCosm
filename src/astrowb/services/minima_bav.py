"""Minima of one star from the BAV's Lichtenknecker-Database (LkDB, plans/oc.md OC-4), read as minima records
(timeseries/minima_table).

    rows = minima("AI Dra")      times in HJD (scale not stated), cached (services.cache)

A form POST makes the site write the star's list to one file shared by every user of the site and redirect to it,
so the file's `#` header must name the star asked for. Then tab-separated, Latin-1: Minimum [HJD], Minimum [UT],
Epoch, (O−C) [d], Photom., Filt., Observer, Source; no error and no I/II column (an epoch ending in .5 is a
secondary). The LkDB's terms forbid passing the data on: it is fetched on the user's request only, never stored
with the program.
"""

import re

from . import http

URL = "https://bav-astro.eu/LkDB/index_joomla.php"
SOURCE = "BAV LkDB"
CITATION = "Lichtenknecker-Database of the BAV"
# C CCD, E photoelectric, P photoplate, V visual; F (series of exposures), K (wedge photometer), ? have no
# counterpart in minima_table.METHODS: unknown
_METHOD = {"C": "ccd", "E": "pe", "P": "pg", "V": "vis"}
_FORM = {"kenn": "liste_min_text", "lang": "en", "sprache_dial": "de", "quelle": "GCVS", "e0_user": "", "p_user": "",
         "ccd": "NEIN", "quali": "NEIN", "date_first": "", "date_last": "", "user_data": ""}  # fmt: skip


def _name(star):
    return " ".join(str(star).split())


def parse(text, star):
    """The LkDB list -> minima records ("HJD unknown", the method's default error); ValueError when the shared
    file's header names another star."""
    from ..timeseries.minima_table import _time, record

    head = " ".join(" ".join(line.lstrip("#").split()) for line in text.splitlines() if line.startswith("#"))
    if not re.search(rf"(?<!\w){re.escape(_name(star))}(?!\w)", head, re.I):
        raise ValueError("the BAV answer was for another star; try again")
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("\t")] + [""] * 8
        try:
            hjd, epoch = float(cells[0]), float(cells[2])
        except ValueError:
            continue  # the header, the column names, the filters' legend
        kind = "II" if abs(epoch % 1.0 - 0.5) < 0.01 else "I"
        source = f"{cells[7]}; {SOURCE}" if cells[7] else SOURCE
        method = _METHOD.get(cells[4].upper(), "unknown")
        rows.append(record(_time(hjd), None, kind, "HJD unknown", method, filter=cells[5], observer=cells[6],
                           source=source))  # fmt: skip
    return rows


def fetch(star):
    """The star's LkDB list as text, cached; ValueError when the shared file was overwritten for another star."""
    from .cache import cached

    name = _name(star)

    def now():
        text = http.post(URL, _FORM | {"stern": name}).decode("latin-1")
        parse(text, name)  # another star's list raises here, so it is never kept in the cache
        return text

    return cached("bav", name.lower(), now)


def minima(star):
    return parse(fetch(star), star)
