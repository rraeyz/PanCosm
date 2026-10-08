"""No module or function grows beyond its limit (plans/architecture.md ARC-4.1); oversized ones only shrink."""

import importlib.util
from pathlib import Path


def test_modules_and_functions_within_their_limits():
    path = Path(__file__).resolve().parents[1] / "tools" / "module_sizes.py"
    spec = importlib.util.spec_from_file_location("module_sizes", path)
    sizes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sizes)
    assert sizes.problems() == []
