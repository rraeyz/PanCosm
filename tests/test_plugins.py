"""User plugins: loaded from the config folder, run in worker processes, broken ones reported."""

import os
from pathlib import Path

import pytest

GOOD = '''
from astrowb.engine.steps import step


@step("plugin.double", inputs=("value",), outputs=("result",), factor=2)
def double(inputs, params, ctx):
    """Multiply a number."""
    return {"result": inputs["value"] * params["factor"]}
'''
SNEAKY = """
from astrowb.engine.steps import step


@step("fits.not_mine", outputs=("x",))
def f(inputs, params, ctx):
    return {"x": 1}
"""


@pytest.fixture
def plugin_folder():
    folder = Path(os.environ["ASTROWB_CONFIG_DIR"]) / "plugins"
    folder.mkdir(parents=True)
    (folder / "good.py").write_text(GOOD)
    (folder / "sneaky.py").write_text(SNEAKY)
    (folder / "broken.py").write_text("def oops(:\n")
    yield folder
    from astrowb.engine import plugins, steps

    for sid in plugins.plugin_steps():
        steps.REGISTRY.pop(sid)
    plugins.ERRORS.clear()


def test_plugins_load_and_run(plugin_folder, qtbot, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QMessageBox

    from astrowb.engine import plugins, steps
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow
    from astrowb.ui.plugin_dialog import PluginDialog, parse

    assert plugins.load_plugins() == ["plugin.double"]
    assert "fits.not_mine" not in steps.REGISTRY  # plugins cannot add or replace built-in ids
    assert set(plugins.ERRORS) == {"sneaky.py", "broken.py"}
    assert parse("3") == 3 and parse("[1, 2]") == [1, 2] and parse("C:/data/a.fits") == "C:/data/a.fits"

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        win._fill_plugins_menu()
        texts = [a.text() for a in win.plugins_menu.actions()]
        assert "Multiply a number" in texts and any("broken.py" in t for t in texts)  # the docstring, not the id
        assert "plugin.double" in [a.toolTip() for a in win.plugins_menu.actions()]
        dlg = PluginDialog(steps.REGISTRY["plugin.double"], win)
        dlg.fields[("in", "value")].setText("21")
        assert dlg.values() == ({"value": 21}, {"factor": 2})
        win.plugin_result = None
        win.run_plugin(steps.REGISTRY["plugin.double"], ({"value": 21}, {"factor": 2}))  # in a worker process
        qtbot.waitUntil(lambda: win.plugin_result is not None, timeout=60000)
        assert win.plugin_result == {"result": 42}
    finally:
        win.engine.shutdown()


def test_example_plugins_install_and_give_right_answers(tmp_path, qtbot):
    import numpy as np
    from astropy.io import fits

    from astrowb.engine import plugins, steps
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        assert win.install_example_plugins() == ["exposure_time.py", "light_curve_summary.py", "sky_level.py"]
        assert win.install_example_plugins() == []  # never overwritten
        ids = plugins.plugin_steps()
        assert {"plugin.sky_level", "plugin.exposure_time", "plugin.light_curve_summary"} <= set(ids)
        img = tmp_path / "f.fits"
        data = np.random.default_rng(0).normal(500, 10, (100, 100))
        data[50, 50] = 60000
        fits.PrimaryHDU(data).writeto(img)
        sky = steps.execute("plugin.sky_level", {"image": str(img)}, {}, Ctx())["sky"]
        assert abs(sky["median"] - 500) < 1 and abs(sky["noise"] - 10) < 0.5
        t = steps.execute("plugin.exposure_time", {}, {"magnitude": 12, "zero_point": 22}, Ctx())["seconds"]
        star, npix = 10**4, np.pi * 25  # e/s at magnitude 12 with zero point 22
        snr = star * t / np.sqrt(star * t + npix * 5 * t + npix * 100)
        assert abs(snr - 100) < 0.05
        csv = tmp_path / "lc.csv"
        tt = np.linspace(0, 0.25, 50)
        csv.write_text("time,rel_flux\n" + "\n".join(f"{a},{1 - 0.1 * (abs(a - 0.1) < 0.01)}" for a in tt))
        s = steps.execute("plugin.light_curve_summary", {"csv_file": str(csv)}, {}, Ctx())["summary"]
        assert s["points"] == 50 and abs(s["span_hours"] - 6) < 1e-9 and abs(s["deepest_time"] - 0.1) < 0.01
    finally:
        for sid in plugins.plugin_steps():
            steps.REGISTRY.pop(sid)
        plugins.ERRORS.clear()
        win.engine.shutdown()
