"""A minimum is a record (plans/oc.md OC-1): where its time came from, in which time standard, how it was timed,
by whom, and whether it is used — every row of an O−C table carries all of it.

    rows = parse_text(pasted)                       # a paper's table, a list, another program's export
    add_bjd(rows, SkyCoord("02h04m10s +46d41m16s")) # every time also in BJD_TDB
    mark_duplicates(rows); mark_epoch_conflicts(rows, t0, period)
    write_ecsv(rows, "minima.ecsv"); to_latex(rows, t0, period)

Rows are plain dicts with the keys of COLUMNS; a stable "id" per row survives editing, sorting and saving.
"""

import itertools
import re

import numpy as np

COLUMNS = ("id", "time_original", "standard_original", "bjd_tdb", "error", "error_assumed", "kind", "method",
           "filter", "timing", "observer", "source", "weight", "use", "note")  # fmt: skip
STANDARDS = ("HJD_UTC", "HJD_TT", "HJD unknown", "BJD_TDB", "BJD_UTC", "JD_UTC", "JD geocentric")
METHODS = ("ccd", "pe", "pg", "vis", "dslr", "space", "unknown")
TIMINGS = ("kvw", "poly", "model", "template", "other")
DEFAULT_ERRORS = {"vis": 0.004, "pg": 0.003, "pe": 0.0010, "ccd": 0.0005, "dslr": 0.0005, "space": 0.0001,
                  "unknown": 0.0010}  # days, when a row gives none (editable)  # fmt: skip
_ids = itertools.count(1)


def record(time, error=None, kind="I", standard="HJD unknown", method="unknown", **more):
    """One row with every column; the error taken from the method's default when none is given."""
    if standard not in STANDARDS:
        raise ValueError(f"unknown time standard {standard}")
    row = dict.fromkeys(COLUMNS, "") | {"id": f"m{next(_ids):05d}", "time_original": float(time),
           "standard_original": standard, "bjd_tdb": np.nan, "kind": kind, "method": method, "weight": 1.0,
           "use": True, "error_assumed": error is None}  # fmt: skip
    row["error"] = float(DEFAULT_ERRORS.get(method, DEFAULT_ERRORS["unknown"]) if error is None else error)
    row.update(more)
    return row


# --- reading text: lists, papers' tables, other programs' exports -----------------------------------------------
_KIND = {"i": "I", "p": "I", "pri": "I", "prim": "I", "1": "I", "ii": "II", "s": "II", "sec": "II", "2": "II"}
_METHOD = {"ccd": "ccd", "pe": "pe", "pg": "pg", "vis": "vis", "v": None, "dslr": "dslr", "tess": "space",
           "kepler": "space", "space": "space", "photo": "pg", "visual": "vis"}  # fmt: skip
_FILTER = re.compile(r"^(U|B|V|R|I|Rc|Ic|C|CV|CR|Clear|TG|TR|TB|g'?|r'?|i'?|z'?|Cl)$", re.I)
_GROUPED = re.compile(r"\b(\d)\s(\d{3})\s(\d{3}\.\d+)")  # "2 451 234.5678"
_PAREN = re.compile(r"(\d+\.(\d+))\((\d+)\)")  # "51234.5678(3)": the error in units of the last digits
_PM = re.compile(r"\s*(?:±|\+/-|\+-)\s*")


def _time(value):
    """A time as written: an implied 2 400 000 or 2 450 000 added to a short one."""
    if value < 1e4:
        return value + 2450000.0  # "1234.5678" in lists that drop 2 450 000
    if value < 1e5:
        return value + 2400000.0  # "51234.5678"
    return value


def _line(line):
    """(time, error, kind, method, filter, rest words) of one line, or None when it holds no time."""
    line = _GROUPED.sub(r"\1\2\3", line.split("#", 1)[0])
    line = _PAREN.sub(lambda m: f"{m.group(1)} {int(m.group(3)) * 10 ** -len(m.group(2)):.10f}", line)
    line = _PM.sub(" ", line).replace(",", " ").replace(";", " ").replace("\t", " ")
    words = [w.rstrip("*†‡abcd") if re.match(r"^\d", w) else w.rstrip("*†‡") for w in line.split()]
    numbers, rest = [], []
    for w in words:
        try:
            numbers.append(float(w))
        except ValueError:
            rest.append(w)
    times = [x for x in numbers if x > 1e3]
    if not times:
        return None
    t = times[0]
    small = [x for x in numbers if 0 < x < 0.1]
    kind, method, filt, words_left = "I", "unknown", "", []
    for w in rest:
        low = w.lower().strip("().")
        if low in _KIND:
            kind = _KIND[low]
        elif low in _METHOD and _METHOD[low]:
            method = _METHOD[low]
        elif _FILTER.match(w) and not filt:
            filt = w
        else:
            words_left.append(w)
    for x in numbers:  # a kind written as 1 / 2 after the time
        if x in (1.0, 2.0) and str(int(x)) in words:
            kind = "I" if x == 1 else "II"
    return _time(t), (small[0] if small else None), kind, method, filt, " ".join(words_left)


def parse_text(text, standard="HJD unknown", source=""):
    """Rows from text: one minimum per line with its time first or anywhere, an error after it (also ± e and
    (3) in units of the last digits), the kind (I/II, p/s, pri/sec), the method (CCD, pe, pg, vis, DSLR) and a
    filter where written; header lines and comments (#) are skipped. The standard is the reader's choice for the
    whole text ("HJD unknown" when the source does not say)."""
    rows = []
    for line in text.splitlines():
        got = _line(line)
        if got is None:
            continue
        t, err, kind, method, filt, rest = got
        rows.append(record(t, err, kind, standard, method, filter=filt, observer=rest, source=source))
    return rows


# --- time standards ---------------------------------------------------------------------------------------------
def _tt_minus_utc(jd):
    from astropy.time import Time

    t = Time(np.asarray(jd, float), format="jd", scale="utc")
    return (t.tt.jd - t.jd) * 86400.0


def add_bjd(rows, target, site=None):
    """Fill bjd_tdb for every row from its time and standard (core.units, ARC-15). "HJD unknown" is read as
    HJD_UTC and TT − UTC at that date is added in quadrature to its error (a note says so); "JD geocentric" is
    JD_UTC. Returns the number of rows whose error grew."""
    from ..core.units import convert_times

    grown = 0
    by_std = {}
    for r in rows:
        by_std.setdefault(r["standard_original"], []).append(r)
    for std, group in by_std.items():
        given = {"HJD unknown": "HJD_UTC", "JD geocentric": "JD_UTC"}.get(std, std)
        times = [r["time_original"] for r in group]
        bjd = convert_times(times, given, target, site)["BJD_TDB"]
        for r, b in zip(group, np.atleast_1d(bjd), strict=True):
            r["bjd_tdb"] = float(b)
        if std == "HJD unknown":
            for r, dt in zip(group, np.atleast_1d(_tt_minus_utc(times)), strict=True):
                r["error"] = float(np.hypot(r["error"], dt / 86400.0))
                r["note"] = (r["note"] + "; " if r["note"] else "") + f"HJD scale unknown: ±{dt:.0f} s added"
                grown += 1
    return grown


# --- checks -----------------------------------------------------------------------------------------------------
def mark_duplicates(rows, tolerance=0.002):
    """The same eclipse reported twice (within `tolerance` days and of the same kind): every repeat after the first
    is unticked with the reason. Returns the ids unticked."""
    times = np.array([r["bjd_tdb"] if np.isfinite(r["bjd_tdb"]) else r["time_original"] for r in rows])
    order = np.argsort(times)
    out = []
    for a, b in itertools.pairwise(order):
        if times[b] - times[a] <= tolerance and rows[a]["kind"] == rows[b]["kind"] and rows[a]["use"]:
            rows[b]["use"] = False
            rows[b]["note"] = (rows[b]["note"] + "; " if rows[b]["note"] else "") + f"same eclipse as {rows[a]['id']}"
            out.append(rows[b]["id"])
    return out


def mark_epoch_conflicts(rows, t0, period, slack=0.15):
    """A primary that falls at phase 0.5 of the ephemeris (or a secondary at 0) is noted; returns their ids."""
    out = []
    for r in rows:
        t = r["bjd_tdb"] if np.isfinite(r["bjd_tdb"]) else r["time_original"]
        phase = ((t - t0) / period) % 1.0
        near_half = abs(phase - 0.5) < slack
        if (r["kind"] == "I" and near_half) or (r["kind"] == "II" and not near_half and min(phase, 1 - phase) < slack):
            r["note"] = (r["note"] + "; " if r["note"] else "") + f"kind {r['kind']} at phase {phase:.2f}"
            out.append(r["id"])
    return out


# --- writing ----------------------------------------------------------------------------------------------------
_FLOATS = ("time_original", "bjd_tdb", "error", "weight")
_BOOLS = ("error_assumed", "use")


def to_table(rows):
    """An astropy Table with each column's type stated (an empty text column stays text when read back)."""
    from astropy.table import Table

    types = [float if c in _FLOATS else bool if c in _BOOLS else str for c in COLUMNS]
    return Table(rows=[[r[c] for c in COLUMNS] for r in rows] or None, names=COLUMNS, dtype=types)


def write_ecsv(rows, path):
    to_table(rows).write(path, format="ascii.ecsv", overwrite=True)


def read_ecsv(path):
    from astropy.table import Table

    table = Table.read(path, format="ascii.ecsv")
    rows = []
    for line in table:
        row = {}
        for c in COLUMNS:
            v = line[c]
            row[c] = float(v) if c in _FLOATS else bool(v) if c in _BOOLS else ("" if np.ma.is_masked(v) else str(v))
        rows.append(row)
    return rows


def write_csv(rows, path):
    to_table(rows).write(path, format="ascii.csv", overwrite=True)


def to_latex(rows, t0, period):
    """A table for a paper: BJD_TDB, error, epoch, O−C (d), kind, method, reference — the used rows only."""
    head = r"BJD$_\mathrm{TDB}$ & Error (d) & Epoch & O$-$C (d) & Type & Method & Reference \\"
    lines = [r"\begin{tabular}{rrrrlll}", r"\hline", head, r"\hline"]
    for r in rows:
        if not r["use"]:
            continue
        t = r["bjd_tdb"] if np.isfinite(r["bjd_tdb"]) else r["time_original"]
        half = 0.5 if r["kind"] == "II" else 0.0
        epoch = round((t - t0) / period - half) + half
        oc = t - (t0 + epoch * period)
        ep = f"{epoch:.1f}" if half else f"{int(epoch)}"
        lines.append(
            f"{t:.5f} & {r['error']:.5f} & {ep} & {oc:+.5f} & {r['kind']} & {r['method']} & {r['source']} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    return "\n".join(lines) + "\n"
