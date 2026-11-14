"""A library of masters across nights (plans/calibration.md CAL-7): masters filed with what makes them fit a light
(kind, size, binning, read-out, temperature, exposure, filter, date), so that a night without its own calibration
frames still calibrates — with the reason and the age said.

    lib = Library(folder)
    lib.add(path)                         copies the master in and indexes it from its header
    m = lib.best(kind, light_header, now) {"path", "age_days", "valid", "why"} or None
    lib.retire(path)                      kept on disk, no longer offered
    cmp = compare(a, b)                   ratio statistics of two masters (and where a dust shadow moved)

Validity per kind (editable): bias 90 days, dark 90 days, flat 7 days — an older master is offered marked, never
used silently.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

VALID_DAYS = {"bias": 90.0, "dark": 90.0, "flat": 7.0}


def _describe(header):
    from ..hdr import get

    def text(*keys):
        for k in keys:
            if header.get(k) not in (None, ""):
                return str(header[k]).strip()
        return ""

    kind = text("IMAGETYP", "FRAMETYP").lower()
    kind = next((k for k in ("bias", "dark", "flat") if k in kind), kind)
    return {"kind": kind, "shape": [int(header.get("NAXIS2", 0)), int(header.get("NAXIS1", 0))],
            "binning": [int(get(header, "XBINNING", default=1) or 1), int(get(header, "YBINNING", default=1) or 1)],
            "readout": text("READOUTM", "GAIN", "OFFSET"), "temperature": get(header, "CCD-TEMP", "SET-TEMP"),
            "exptime": get(header, "EXPTIME", "EXPOSURE"), "filter": text("FILTER"),
            "date": text("DATE-OBS", "DATE")[:19]}  # fmt: skip


def _days(a, b):
    try:
        return abs((datetime.fromisoformat(a[:19]) - datetime.fromisoformat(b[:19])).total_seconds()) / 86400
    except ValueError:
        return float("inf")


class Library:
    def __init__(self, folder, valid_days=None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.valid = dict(VALID_DAYS) | (valid_days or {})
        self.index_path = self.folder / "index.json"
        self.entries = json.loads(self.index_path.read_text("utf-8")) if self.index_path.exists() else []

    def _save(self):
        self.index_path.write_text(json.dumps(self.entries, indent=1), "utf-8")

    def add(self, path, kind=None):
        from astropy.io import fits

        info = _describe(fits.getheader(path))
        info["kind"] = kind or info["kind"]
        dest = self.folder / info["kind"] / Path(path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():  # two nights' master_flat_00.fits: kept apart by their date
            dest = dest.with_name(f"{dest.stem}_{info['date'].replace(':', '').replace('-', '')}{dest.suffix}")
        shutil.copy2(path, dest)
        self.entries.append(info | {"path": str(dest), "retired": False})
        self._save()
        return str(dest)

    def retire(self, path):
        for e in self.entries:
            if e["path"] == str(path):
                e["retired"] = True
        self._save()

    def best(self, kind, light_header, now=None, temp_tol=2.0):
        """The fitting master of this kind for a light (same size, binning and read-out; a dark of the same
        exposure and temperature; a flat of the same filter), the newest first; None when none fits at all."""
        want = _describe(light_header)
        now = now or want["date"]
        fits_ = []
        for e in self.entries:
            if e["retired"] or e["kind"] != kind or e["shape"] != want["shape"] or e["binning"] != want["binning"]:
                continue
            if e["readout"] != want["readout"]:
                continue
            if (
                kind == "dark"
                and want["exptime"]
                and e["exptime"]
                and abs(e["exptime"] - want["exptime"]) > 0.1 * want["exptime"]
            ):
                continue
            if kind == "dark" and None not in (e["temperature"], want["temperature"]):
                if abs(e["temperature"] - want["temperature"]) > temp_tol:
                    continue
            if kind == "flat" and e["filter"] != want["filter"]:
                continue
            fits_.append(e)
        if not fits_:
            return None
        e = min(fits_, key=lambda x: _days(x["date"], now))
        age = _days(e["date"], now)
        valid = age <= self.valid.get(kind, np.inf)
        why = f"from the library, {age:.0f} days old" + (
            "" if valid else f" — older than its {self.valid[kind]:g} days"
        )
        return {"path": e["path"], "age_days": age, "valid": bool(valid), "why": why}


def compare(a, b, min_depth=0.01):
    """{"ratio_median", "ratio_rms", "moved_dust"}: two masters of the same kind divided; the dust shadows of each
    (calibration/quality.dust) and those of one not at the other's places (a mote that moved)."""
    from .quality import dust

    a, b = np.asarray(a, float), np.asarray(b, float)
    r = (a / np.nanmedian(a)) / (b / np.nanmedian(b))
    da, db = dust(a, min_depth=min_depth), dust(b, min_depth=min_depth)

    def unmatched(xs, ys):
        return [d for d in xs if all(np.hypot(d["x"] - e["x"], d["y"] - e["y"]) > 2 * max(d["radius"], 3) for e in ys)]

    return {"ratio_median": float(np.nanmedian(r)), "ratio_rms": float(np.nanstd(r)),
            "moved_dust": unmatched(da, db) + unmatched(db, da)}  # fmt: skip
