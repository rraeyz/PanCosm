import pytest

from astrowb.settings import Settings
from astrowb.ui.observe_results import filtered, graphs_figure


@pytest.fixture
def setup(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    window = MainWindow(Settings(tmp_path))
    qtbot.addWidget(window)
    win = window.open_area("observe")
    yield win, window.observe_page
    win.close()
    window.engine.shutdown()


def status(temp, pos, log):
    return {"camera": {"CCDTemperature": temp}, "focuser": {"Position": pos}, "log": log}


def test_filter_keeps_matching_lines():
    assert filtered(["Slew done", "Cooler on", "slew started"], " SLEW ") == ["Slew done", "slew started"]
    assert filtered(["a", "b"], "") == ["a", "b"]


def test_dock_starts_hidden_then_shows_log_and_graphs(setup):
    win, page = setup
    res = win.observe_results
    assert "result_log" not in win.docks and "result_graphs" not in win.docks  # docked at the first content
    assert res.view.focusPolicy().name == "NoFocus"
    res.update({"error": "down"})  # no status: nothing shown
    assert not res.lines and not any(res.samples.values())
    res.update(status(-10.0, 12000, ["slew done", "cooler on"]))
    res.update(status(-10.5, 12034, ["slew done", "cooler on", "focus ok"]))
    assert not win.docks["result_log"].isHidden() and not win.docks["result_graphs"].isHidden()
    assert res.view.toPlainText().count("\n") == 2
    res.filter.setText("focus")
    assert res.view.toPlainText() == "focus ok"
    assert [len(p) for p in res.samples.values()] == [2, 2]
    assert len(graphs_figure(res.samples).panels) == 2
    assert len(graphs_figure({"x": []}).panels) == 0
