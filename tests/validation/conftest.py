"""VAL-3: each validation test writes what it measured against what it was compared with to
validation-results/<test>.json (or $ASTROWB_VALIDATION_RESULTS); tools/validation_report.py makes the report."""

import json
import os
import platform
from pathlib import Path

import pytest


@pytest.fixture
def measured(request):
    """measured(area, quantity, compared_with, tolerance, value, ok, data=..., step=...): one row of the report."""
    rows = []

    def add(area, quantity, compared_with, tolerance, value, ok, data="", step=""):
        rows.append({"area": area, "quantity": quantity, "compared_with": compared_with, "tolerance": tolerance,
                     "measured": value, "verdict": "pass" if ok else "fail", "data": data, "step": step,
                     "test": request.node.nodeid})  # fmt: skip

    yield add
    if rows:
        from astrowb import __version__

        folder = Path(os.environ.get("ASTROWB_VALIDATION_RESULTS", "validation-results"))
        folder.mkdir(parents=True, exist_ok=True)
        doc = {"rows": rows, "versions": {"application": __version__, "python": platform.python_version()}}
        (folder / f"{request.node.name}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
