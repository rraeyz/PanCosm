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


def test_help_menu_check_shows_the_report(qtbot, tmp_path, monkeypatch):
    """Help -> Check the installation: the report in a window (no terminal needed, e.g. on Windows)."""
    from PySide6.QtWidgets import QMessageBox

    from astrowb.engine.steps import execute
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    monkeypatch.setattr(selfcheck, "online", lambda: [("SIMBAD (target names)", False, "ConnectionError: no network")])

    class Ctx:
        def progress(self, *a):
            pass

    out = execute("app.check", {}, {}, Ctx())
    assert out["ok"] is False and "FAIL  SIMBAD" in out["report"] and "OK    application modules" in out["report"]
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: shown.append(box.detailedText()))
    monkeypatch.setattr(win, "run_step", lambda step, inputs, params, on_done: on_done(out))
    from astrowb.ui import help_checks

    help_checks.installation(win)
    assert shown and "SIMBAD" in shown[0]
    win.engine.shutdown()


def test_gpu_check_step_writes_its_report(tmp_path, monkeypatch):
    import json

    from astrowb.compute import check
    from astrowb.engine import builtin

    def fake_report(found):
        found["adapter"] = {"device": "Test GPU"}
        found["jobs"] = [{"job": "stack", "cpu_s": 1.0, "gpu_s": 0.1, "same": True}]
        yield "GPU found: Test GPU"
        yield "1 of 1 GPU jobs work."

    monkeypatch.setattr(check, "report", fake_report)
    monkeypatch.setenv("ASTROWB_CONFIG_DIR", str(tmp_path))
    ctx = type("Ctx", (), {"progress": lambda self, *a: None})()
    out = builtin.app_check_gpu({}, {}, ctx)
    saved = json.loads((tmp_path / "gpu-report.json").read_text(encoding="utf-8"))
    assert out["path"] == str(tmp_path / "gpu-report.json") and "1 of 1" in out["report"]
    assert saved["adapter"]["device"] == "Test GPU" and saved["jobs"][0]["same"] and saved["version"]


def test_the_iers_check_imports(monkeypatch):
    """It named the module one package too far up: the check failed on every computer."""
    from astrowb import selfcheck

    monkeypatch.setattr(selfcheck, "_checks", lambda vega, mast, iers: {"IERS": iers})
    assert selfcheck.online()[0][1] is True


def test_offline_checks_pass_in_a_fresh_process():
    """The installed copy runs the check before anything else is imported: a module imported first in that order
    (a step description before its steps) failed there only, not in this test process."""
    import subprocess
    import sys

    code = "from astrowb import selfcheck; print([r for r in selfcheck.offline() if not r[1]])"
    env = {**__import__("os").environ, "QT_QPA_PLATFORM": "offscreen"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=300)
    assert out.stdout.strip().endswith("[]"), out.stdout[-2000:] + out.stderr[-2000:]


def test_a_refusing_or_dead_service_is_said_in_words():
    """User feedback UF-21: "HTTPError: HTTP Error 404" told the owner nothing; CDS was down that night."""
    import urllib.error

    from astrowb import selfcheck

    def down():
        raise urllib.error.HTTPError("https://x", 404, "Not Found", {}, None)

    def refused():
        raise urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)

    got = dict((n, d) for n, _ok, d in selfcheck._run({"cds": down, "aavso": refused}))
    assert "down or moved" in got["cds"] and "refused" in got["aavso"]
