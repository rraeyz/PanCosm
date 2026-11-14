"""PLN-2: target lists kept between sessions, CSV import by column names, duplicates merged by position."""

import pytest

from astrowb.planning import target_lists as tl

CSV = """Name;RA;Dec;Period;Epoch;Notes
NY Vir;13:38:48.1;-02:01:49;0.10101596;2453174.442699;sdB+dM
AI Dra;250.4321;52.6941;1.1988;2445862.5643;
broken;;;;;
HAT-P-32 b;02h04m10.3s;+46d41m16s;2.15;2455867.4027;planet
"""


def test_csv_import_with_its_columns_found():
    rows, skipped = tl.from_csv(CSV)
    assert [r["name"] for r in rows] == ["NY Vir", "AI Dra", "HAT-P-32 b"] and skipped == [4]
    ny = rows[0]
    assert ny["ra"] == pytest.approx(15 * (13 + 38 / 60 + 48.1 / 3600)) and ny["dec"] == pytest.approx(-2.030278, 1e-5)
    assert ny["period"] == 0.10101596 and ny["t0"] == 2453174.442699 and ny["notes"] == "sdB+dM"
    assert rows[1]["ra"] == 250.4321 and "notes" in rows[1]
    assert rows[2]["ra"] == pytest.approx(31.04292, abs=1e-5) and rows[2]["dec"] == pytest.approx(46.68778, abs=1e-5)
    with pytest.raises(ValueError):
        tl.from_csv("a,b\n1,2\n")


def test_lists_survive_and_duplicates_merge():
    rows, _ = tl.from_csv(CSV)
    tl.save("my EBs", rows[:2])
    assert tl.names() == ["my EBs"] and tl.load("my EBs")[0]["name"] == "NY Vir"
    again = {"name": "NY Virginis", "ra": rows[0]["ra"] + 1 / 3600, "dec": rows[0]["dec"], "period": 0.101015965}
    merged = tl.merge(tl.load("my EBs"), [again, rows[2]])
    assert len(merged) == 3 and merged[0]["period"] == 0.101015965 and merged[0]["notes"] == "sdB+dM"
    tl.delete("my EBs")
    assert tl.names() == []


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_the_planning_window_imports_saves_and_opens_lists(window, tmp_path):
    text = CSV
    page = window.plan_page
    window.show_workspace("plan")
    (tmp_path / "t.csv").write_text(text, encoding="utf-8")
    assert len(page.import_targets(str(tmp_path / "t.csv"))) == 3 and page.table.rowCount() == 3
    assert "4" in page.status.text()  # the row without a position is named
    assert page.import_targets(str(tmp_path / "t.csv")) == []  # the same stars are not added twice
    page.save_list("tonight")
    page.table.setRowCount(0)
    assert len(page.open_list("tonight")) == 3 and page.targets()[0]["period"] == 0.10101596
    win = window.area_windows["plan"]
    texts = [a.text() for m in win.menuBar().actions() if m.menu() for a in m.menu().actions()]
    assert "Open a saved list…" in texts and "Import targets from CSV…" in texts
