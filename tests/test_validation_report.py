"""VAL-3: the report puts each measured row beside the plan's tolerance table; a planned quantity without a test is
listed as not yet tested."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_report_from_a_run(tmp_path):
    spec = importlib.util.spec_from_file_location("validation_report", ROOT / "tools" / "validation_report.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    rows = [{"area": "Photometry", "quantity": "aperture flux", "compared_with": "IRAF phot", "tolerance": "0.1 %",
             "measured": "0.04 %", "verdict": "pass", "data": "HAT-P-32", "step": "photometry item 1",
             "test": "tests/validation/test_iraf_phot.py::test_x"}]  # fmt: skip
    (tmp_path / "x.json").write_text(json.dumps({"rows": rows, "versions": {}}))
    report = tool.build(tmp_path)
    assert "| aperture flux | IRAF phot | 0.1 % | 0.04 % | pass |" in report
    assert "## Calibration" in report and "not yet tested | CAL-21" in report
    assert report.count("not yet tested") == len(tool.planned()) - 1  # the photometry item-1 row is tested
