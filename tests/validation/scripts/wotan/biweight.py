"""The reference for clean.trend("biweight") (plans/period.md PER-2): a light curve with two segments, a slow
trend, transits and outliers (numbers fixed by the seed), detrended by wotan's time-windowed biweight (window 0.5 d,
segments broken at gaps over 0.5 d). Run in an environment of its own with wotan (MIT) installed, never ours:

    python -m venv /tmp/wotan && /tmp/wotan/bin/pip install wotan
    /tmp/wotan/bin/python tests/validation/scripts/wotan/biweight.py

It writes tests/validation/data/wotan_biweight.txt (time, flux, trend) and its manifest."""

import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
OUT = HERE.parents[2] / "data" / "wotan_biweight.txt"


def curve():
    rng = np.random.default_rng(7)
    t = np.sort(np.concatenate([rng.uniform(0, 6, 2500), rng.uniform(8, 13, 2000)]))
    y = 1 + 0.01 * np.sin(t / 2) + 0.003 * t + rng.normal(0, 0.001, t.size)
    y[np.abs(((t - 1.3) / 2.7 + 0.5) % 1 - 0.5) * 2.7 < 0.06] -= 0.01
    y[rng.choice(t.size, 20)] += 0.02
    return np.round(t, 8), np.round(y, 8)


def main():
    from wotan import flatten

    t, y = curve()
    _flat, trend = flatten(t, y, method="biweight", window_length=0.5, return_trend=True, edge_cutoff=0,
                           break_tolerance=0.5)  # fmt: skip
    np.savetxt(OUT, np.column_stack([t, y, trend]), fmt="%.8f %.8f %.10f")
    manifest = {
        "program": "wotan.flatten (biweight)",
        "version": version("wotan"),
        "date": time.strftime("%Y-%m-%d"),
        "command": f"python {HERE.relative_to(HERE.parents[4]).as_posix()}",
        "inputs": "the synthetic curve of curve() (seed 7)",
        "inputs_sha256": hashlib.sha256(np.column_stack([t, y]).tobytes()).hexdigest(),
    }
    OUT.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


if __name__ == "__main__":
    main()
