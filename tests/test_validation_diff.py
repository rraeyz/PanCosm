"""VAL-5: the science changelog lists the numbers that moved by more than a third of their tolerance."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validation_report", ROOT / "tools" / "validation_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def row(quantity, measured, tolerance="0.003 mag"):
    return {"area": "Photometry", "quantity": quantity, "measured": measured, "tolerance": tolerance}


def test_moves_beyond_a_third_of_the_tolerance():
    old = [row("sky", "0.0010 mag"), row("aperture", "0.0020 mag"), row("gone", "1")]
    new = [row("sky", "0.0025 mag"), row("aperture", "0.0028 mag"), row("added", "2")]
    moved = report.diff(old, new)
    names = [m[1] for m in moved]
    assert names == ["added", "gone", "sky"]  # sky moved 0.0015 > 0.001; aperture 0.0008 stayed inside
