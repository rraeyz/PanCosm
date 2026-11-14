"""Target lists that remember (plans/planning.md PLN-2): named lists ("my EBs", "ExoClock") kept in the user's
folder, CSV import with the columns found by their names, duplicates merged by position.

    save("my EBs", targets); load("my EBs"); names(); delete("my EBs")
    rows = from_csv(text)          name / ra / dec (degrees or sexagesimal) / t0 / period / duration / priority …
    merged = merge(old, new)       a star given twice (within 5″) is kept once, the newer values winning

A target is a dict: name, ra, dec (degrees, ICRS) and any of t0, period, duration, secondary, priority, notes.
"""

import csv
import io
import json
import re

import numpy as np

ALIASES = {
    "name": ("name", "object", "target", "star", "id", "designation"),
    "ra": ("ra", "ra_deg", "raj2000", "ra2000", "right ascension", "alpha"),
    "dec": ("dec", "de", "dec_deg", "dej2000", "dec2000", "declination", "delta"),
    "t0": ("t0", "epoch", "hjd0", "bjd0", "min i", "tmin", "tc"),
    "period": ("period", "p", "per", "period_d", "period (d)"),
    "duration": ("duration", "d", "dur", "t14", "duration_d"),
    "priority": ("priority", "prio"),
    "notes": ("notes", "note", "comment", "remarks"),
}


def _folder():
    from ..settings import config_dir

    path = config_dir() / "target_lists"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _file(name):
    safe = re.sub(r"[^\w\- ]", "_", name).strip() or "list"
    return _folder() / f"{safe}.json"


def save(name, targets):
    path = _file(name)
    path.write_text(json.dumps({"name": name, "targets": list(targets)}, indent=1, ensure_ascii=False), "utf-8")
    return path


def load(name):
    return json.loads(_file(name).read_text(encoding="utf-8"))["targets"]


def names():
    return sorted(json.loads(p.read_text(encoding="utf-8"))["name"] for p in _folder().glob("*.json"))


def delete(name):
    _file(name).unlink(missing_ok=True)


def _angle(text, hours):
    text = str(text).strip()
    if not text:
        return None
    if re.fullmatch(r"[+-]?\d+(\.\d*)?", text):
        return float(text)  # degrees already
    parts = re.split(r"[:hmsd°'\" ]+", text.strip('s"'))
    parts = [p for p in parts if p]
    sign = -1.0 if text.startswith("-") else 1.0
    d, m, s = (abs(float(v)) for v in (parts + ["0", "0"])[:3])
    return sign * (d + m / 60 + s / 3600) * (15.0 if hours else 1.0)


def from_csv(text):
    """Targets from a CSV (comma, semicolon or tab), its columns found by their header names; rows without a name
    or position are skipped and returned as such: (targets, skipped row numbers)."""
    sample = text[:2000]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample.strip() else csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return [], []
    head = [h.strip().lower() for h in rows[0]]
    where = {key: next((i for i, h in enumerate(head) if h in names_), None) for key, names_ in ALIASES.items()}
    if where["name"] is None or where["ra"] is None or where["dec"] is None:
        raise ValueError("the file needs columns for the name, the right ascension and the declination")
    out, skipped = [], []
    for k, row in enumerate(rows[1:], start=2):
        try:
            t = {"name": row[where["name"]].strip(), "ra": _angle(row[where["ra"]], hours=":" in row[where["ra"]]
                 or "h" in row[where["ra"]]), "dec": _angle(row[where["dec"]], hours=False)}  # fmt: skip
        except (IndexError, ValueError):
            skipped.append(k)
            continue
        if not t["name"] or t["ra"] is None or t["dec"] is None:
            skipped.append(k)
            continue
        for key in ("t0", "period", "duration", "priority"):
            i = where[key]
            if i is not None and i < len(row) and row[i].strip():
                try:
                    t[key] = float(row[i])
                except ValueError:
                    pass
        if where["notes"] is not None and where["notes"] < len(row):
            t["notes"] = row[where["notes"]].strip()
        out.append(t)
    return out, skipped


def merge(old, new, within_arcsec=5.0):
    """old + new with a star given twice kept once (the new values over the old ones), in old's order then new's."""
    out = [dict(t) for t in old]
    for t in new:
        match = None
        for o in out:
            d = 3600 * np.hypot((o["ra"] - t["ra"]) * np.cos(np.radians(t["dec"])), o["dec"] - t["dec"])
            if d <= within_arcsec:
                match = o
                break
        if match is None:
            out.append(dict(t))
        else:
            match.update({k: v for k, v in t.items() if v is not None})
    return out
