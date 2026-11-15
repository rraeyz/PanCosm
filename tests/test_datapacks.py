"""ARC-20 item 1: the data manager lists, measures and removes what was downloaded; no network."""

import pytest

from astrowb.core import datapacks


def test_packs_are_measured_and_removed_alone(tmp_path):
    (tmp_path / "templates" / "mk_libnor36").mkdir(parents=True)
    (tmp_path / "templates" / "pickles_uk_1.fits").write_bytes(b"x" * 100)
    (tmp_path / "templates" / "mk_libnor36" / "t100l00p00.rbn").write_bytes(b"y" * 50)
    (tmp_path / "templates" / "mine.fits").write_bytes(b"z")  # the user's own file in the same folder
    got = {p["id"]: p for p in datapacks.packs(tmp_path)}
    assert got["pickles"]["size"] == 100 and got["mk"]["size"] == 50 and got["phoenix"]["files"] == 0
    assert got["mk"]["source"][0].startswith("https://") and got["answers"]["source"] == []
    assert datapacks.remove(tmp_path, "mk") == 1
    assert not (tmp_path / "templates" / "mk_libnor36").exists() and (tmp_path / "templates" / "mine.fits").exists()
    assert datapacks.remove(tmp_path, "pickles") == 1 and (tmp_path / "templates" / "mine.fits").exists()
    assert datapacks.remove(tmp_path, "phoenix") == 0
    with pytest.raises(ValueError):
        datapacks.remove(tmp_path, "nope")


def test_the_data_page_shows_sizes_and_removes(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow
    from astrowb.ui.settings_window import SettingsWindow

    settings = Settings(tmp_path)
    (tmp_path / "phoenix").mkdir()
    (tmp_path / "phoenix" / "a.fits").write_bytes(b"x" * 2000)
    main = MainWindow(settings)
    qtbot.addWidget(main)
    win = SettingsWindow(main)
    qtbot.addWidget(win)
    button = win.data_buttons["phoenix"]
    assert button.text().startswith("2.0 kB") and button.isEnabled()
    button.click()
    assert not (tmp_path / "phoenix").exists() and not button.isEnabled()
    main.engine.shutdown()
