"""Reproduce a run (ARC-11.5): keep a copy of the old products, compare them with the new ones."""

import shutil
from pathlib import Path

import numpy as np


def _walk(value, path):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, value


def files_in(outputs):
    """[(key path, Path)] of every string in a run's outputs that names an existing file."""
    found = []
    for key, v in _walk(outputs or {}, ""):
        if isinstance(v, str) and len(v) < 4096 and "\0" not in v:
            try:
                if Path(v).is_file():
                    found.append((key, Path(v)))
            except OSError:
                pass
    return found


def snapshot(outputs, dest):
    """Copy the files of the outputs into dest/original/; returns {key path: the copy}. Nothing is moved or deleted."""
    folder = Path(dest) / "original"
    folder.mkdir(parents=True, exist_ok=True)
    copies = {}
    for i, (key, src) in enumerate(files_in(outputs)):
        target = folder / src.name
        if target.exists():
            target = folder / f"{i}-{src.name}"
        shutil.copy2(src, target)
        copies[key] = target
    return copies


def _arrays_diff(a, b):
    """'identical', 'different shape' or the largest absolute difference of two lists of arrays."""
    if len(a) != len(b):
        return "different shape"
    worst = 0.0
    for x, y in zip(a, b, strict=True):
        x, y = np.asarray(x), np.asarray(y)
        if x.shape != y.shape:
            return "different shape"
        if x.dtype.kind in "fiub" and y.dtype.kind in "fiub" and x.size:
            both = np.isnan(x.astype(float)) & np.isnan(y.astype(float))
            d = np.abs(x.astype(float) - y.astype(float))
            worst = max(worst, float(np.max(np.where(both, 0.0, d))))
        elif not np.array_equal(x, y):
            return "different"
    return "identical" if worst == 0 else worst


def _fits_data(path):
    from astropy.io import fits

    with fits.open(path) as hdus:
        return [h.data for h in hdus if h.data is not None]


def _table_data(path):
    from astropy.table import Table

    t = Table.read(path)
    return [np.asarray(t[c]) for c in t.colnames]


def compare(old, new):
    """'identical', the largest absolute difference (float), 'different shape' or 'differs' for two files."""
    old, new = Path(old), Path(new)
    ext = new.suffix.lower()
    try:
        if ext in (".fits", ".fit", ".fts"):
            return _arrays_diff(_fits_data(old), _fits_data(new))
        if ext in (".ecsv", ".csv"):
            return _arrays_diff(_table_data(old), _table_data(new))
    except (OSError, ValueError):
        pass  # unreadable as its format: fall back to the bytes
    return "identical" if old.read_bytes() == new.read_bytes() else "differs"


def _numbers(outputs):
    return {k: v for k, v in _walk(outputs or {}, "") if isinstance(v, (int, float)) and not isinstance(v, bool)}


def report(before, after_outputs, old_outputs=None):
    """Lines of text: each file (before = snapshot map) and each plain number of the new run against the old one."""
    after = dict(files_in(after_outputs))
    lines = []
    for key in sorted(set(before) | set(after)):
        if key not in before:
            lines.append(f"{key}: only in the new run")
        elif key not in after:
            lines.append(f"{key}: missing in the new run")
        else:
            lines.append(f"{key}: {compare(before[key], after[key])}")
    old, new = _numbers(old_outputs), _numbers(after_outputs)
    for k in sorted(old.keys() & new.keys()):
        lines.append(f"{k}: {'identical' if old[k] == new[k] else abs(float(old[k]) - float(new[k]))}")
    return lines
