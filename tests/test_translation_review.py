"""Spreadsheet review of the translations: export, corrections back, placeholders protected."""

import csv
import importlib.util
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool():
    spec = importlib.util.spec_from_file_location("translation_review", ROOT / "tools" / "translation_review.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_export_and_import_corrections(tmp_path):
    tool = _tool()
    for lang in ("de", "tr"):
        shutil.copy(tool.I18N / f"app_{lang}.ts", tmp_path)
    tool.I18N = tmp_path
    out = tmp_path / "review.csv"
    tool.export("de", out)
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
    assert len(rows) > 1000 and set(tool.FIELDS) == set(rows[0])
    plain = next(r for r in rows if r["english"] == "Visual binary orbit")
    assert plain["current"] == "Bahn eines visuellen Doppelsterns" and plain["turkish"]
    braces = next(r for r in rows if r["english"] == "{n} orders traced.")
    plain["corrected"], braces["corrected"] = "Visuelle Doppelsternbahn", "Ordnungen verfolgt."  # {n} lost
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, tool.FIELDS)
        w.writeheader()
        w.writerows(rows)
    changed, refused = tool.apply("de", out)
    assert changed == 1 and len(refused) == 1 and "placeholders" in refused[0][1]
    got = {m.findtext("source"): m.findtext("translation") for m in ET.parse(tmp_path / "app_de.ts").iter("message")}
    assert got["Visual binary orbit"] == "Visuelle Doppelsternbahn"
    assert got["{n} orders traced."] == "{n} Ordnungen verfolgt."  # refused: left as it was
