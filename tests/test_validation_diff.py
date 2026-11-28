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


def test_the_release_notes_section_compares_with_the_newest_older_version(tmp_path):
    import json

    def save(version, rows):
        (tmp_path / f"{version}.json").write_text(json.dumps({"version": version, "rows": rows}))
        return tmp_path / f"{version}.json"

    save("0.3.9", [row("sky", "0.0001 mag")])
    save("0.3.10", [row("sky", "0.0010 mag")])  # newer than 0.3.9 as a version, older as text
    new = save("0.3.11", [row("sky", "0.0025 mag")])
    text = report.notes(new, tmp_path)
    assert "## Science changes" in text and "against 0.3.10" in text and "sky: 0.0010 mag → 0.0025 mag" in text
    assert "No stored" in report.notes(save("0.1.0", []), tmp_path)
