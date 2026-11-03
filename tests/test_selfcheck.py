"""The installation self-check: complete list of libraries, and everything passes in a source install."""

import ast
import sys
from pathlib import Path

from astrowb import selfcheck

SRC = Path(__file__).resolve().parents[1] / "src" / "astrowb"


def imported_libraries():
    """Top-level third-party packages imported anywhere in the application, also inside functions."""
    out = set()
    for f in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                out |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                out.add(node.module.split(".")[0])
    return {m for m in out if m not in sys.stdlib_module_names and m not in ("astrowb", "PySide6")}


def test_every_library_is_checked():
    checked = {name.split(".")[0] for name in selfcheck.LIBRARIES}
    assert imported_libraries() <= checked, imported_libraries() - checked


def test_offline_checks_pass_in_a_source_install():
    results = selfcheck.offline()
    assert all(ok for _, ok, _ in results), selfcheck.report(results)
    assert "OK" in selfcheck.report(results)
