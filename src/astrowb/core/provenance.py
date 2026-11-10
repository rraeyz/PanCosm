"""Provenance: every product says how it was made (plans/architecture.md ARC-11).

    rec = record("calibration.run", params, {"lights": [path, ...], "bias": master})
    to_fits(header, rec)              # SWCREATE, SWVERS, PROCSTEP, PROCHASH and HISTORY lines
    table.meta = to_ecsv(table.meta, rec)
    read(path) == rec                 # back from a FITS or ECSV product

Inputs are named by file name, size and a BLAKE2 checksum (of the first and last MiB and the size for large files:
fast on 100 MB frames, still telling a changed file). No Qt here.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

CHUNK = 1 << 20
_PREFIX = "PROV "  # HISTORY lines that hold the machine-readable record
_LINE = 64  # characters of JSON per HISTORY card (cards hold 72)


def checksum(path):
    """BLAKE2b-128 of a file: all of it below 4 MiB, else its size, first and last MiB."""
    path = Path(path)
    size = path.stat().st_size
    h = hashlib.blake2b(digest_size=16)
    h.update(str(size).encode())
    with open(path, "rb") as f:
        if size <= 4 * CHUNK:
            h.update(f.read())
        else:
            h.update(f.read(CHUNK))
            f.seek(-CHUNK, 2)
            h.update(f.read(CHUNK))
    return h.hexdigest()


def _versions():
    from importlib.metadata import PackageNotFoundError, version

    from .. import __version__

    out = {"application": __version__}
    for name in ("numpy", "astropy", "scipy", "photutils"):
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            pass
    return out


def record(step_id, params, inputs):
    """The record of one step: inputs is {role: path or [paths]}; params must be JSON values."""

    def describe(p):
        p = Path(p)
        return {"name": p.name, "size": p.stat().st_size, "blake2": checksum(p)} if p.exists() else {"name": p.name}

    files = {role: [describe(p) for p in (v if isinstance(v, list | tuple) else [v])] for role, v in inputs.items()}
    return {
        "step": step_id,
        "params": json.loads(json.dumps(params, default=str)),
        "inputs": files,
        "versions": _versions(),
        "made": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def digest(rec):
    """A short hash of the record (PROCHASH): equal for equal steps on equal inputs, whenever they ran."""
    stable = {k: v for k, v in rec.items() if k != "made"}
    return hashlib.blake2b(json.dumps(stable, sort_keys=True).encode(), digest_size=8).hexdigest()


def to_fits(header, rec):
    """Keywords, readable HISTORY lines and the record itself in HISTORY lines starting with 'PROV '."""
    from ..brand import BRAND

    header["SWCREATE"] = (BRAND.display_name, "software that made this file")
    header["SWVERS"] = (rec["versions"]["application"], "its version")
    header["PROCSTEP"] = (rec["step"], "processing step")
    header["PROCHASH"] = (digest(rec), "hash of step, parameters and inputs")
    header.add_history(f"{rec['step']} at {rec['made']}")
    for key, value in rec["params"].items():
        header.add_history(f"  {key} = {value}"[:72])
    for role, files in rec["inputs"].items():
        for f in files:
            header.add_history(f"  {role}: {f['name']} {f.get('blake2', '')}"[:72])
    # spaces escaped: FITS drops the trailing spaces of a card, which would cut a space at the end of a chunk
    text = json.dumps(rec, separators=(",", ":"), ensure_ascii=True).replace(" ", "\\u0020")
    for i in range(0, len(text), _LINE):
        header.add_history(_PREFIX + text[i : i + _LINE])
    return header


def to_ecsv(meta, rec):
    meta = dict(meta or {})
    meta["provenance"] = rec
    return meta


def from_header(header):
    """The record written by to_fits, or None (the last one when a file went through several steps)."""
    parts, records = [], []
    for value in header.get("HISTORY", []):
        value = str(value)
        if value.startswith(_PREFIX):
            parts.append(value[len(_PREFIX) :])
            try:
                records.append(json.loads("".join(parts)))
                parts = []
            except json.JSONDecodeError:
                continue  # the record goes on in the next card
    return records[-1] if records else None


def read(path):
    """The record of a FITS or ECSV product, or None."""
    path = Path(path)
    if path.suffix.lower() == ".ecsv":
        from astropy.table import Table

        return Table.read(path, format="ascii.ecsv").meta.get("provenance")
    from astropy.io import fits

    return from_header(fits.getheader(path))
