"""VAL-2: every reference table of the validation tests can be made again: it has a manifest beside it (program,
version, date, command, a digest of its inputs) whose command is a script in the repository; and no reference
program is imported by the package or its tests (they run outside, their tables are compared)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tests" / "validation" / "data"
REFERENCE_PROGRAMS = ("pyraf", "iraf", "lightkurve", "batman", "ellc", "phoebe", "transitleastsquares", "wotan")


def test_every_reference_table_has_a_manifest_and_its_script():
    tables = sorted(p for p in TABLES.iterdir() if p.suffix in (".csv", ".txt", ".dat"))
    assert tables
    for table in tables:
        manifest = table.with_suffix(".manifest.json")
        assert manifest.exists(), f"{table.name}: no manifest (write it with the table's script)"
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        assert {"program", "version", "date", "command", "inputs_sha256"} <= set(doc), manifest.name
        script = ROOT / doc["command"].split()[-1]
        assert script.is_file() and script.is_relative_to(ROOT / "tests" / "validation" / "scripts"), doc["command"]


def test_no_reference_program_is_imported():
    pattern = re.compile(rf"^\s*(?:import|from)\s+({'|'.join(REFERENCE_PROGRAMS)})\b", re.M)
    scripts = ROOT / "tests" / "validation" / "scripts"
    found = [
        str(p.relative_to(ROOT))
        for folder in (ROOT / "src", ROOT / "tests")
        for p in folder.rglob("*.py")
        if not p.is_relative_to(scripts) and pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not found, found
