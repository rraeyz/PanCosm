import importlib.util
from pathlib import Path

import platformdirs

from astrowb import settings
from astrowb.brand import BRAND

ROOT = Path(__file__).resolve().parents[1]


def test_brand_name_only_in_brand_file():
    spec = importlib.util.spec_from_file_location("check_brand", ROOT / "tools" / "check_brand.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert BRAND.display_name in mod.brand_terms()
    assert mod.find_violations() == []


def test_brand_loaded():
    assert BRAND.display_name and BRAND.app_id == BRAND.app_id.lower()
    assert BRAND.icon_path.is_file()


def test_settings_roundtrip(tmp_path):
    s = settings.Settings(tmp_path)
    s.set("ui.language", "tr")
    assert settings.Settings(tmp_path).get("ui.language") == "tr"


def test_migration_copies_old_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(platformdirs, "user_config_path", lambda app, appauthor=False: tmp_path / "cfg" / app)
    monkeypatch.setattr(platformdirs, "user_data_path", lambda app, appauthor=False: tmp_path / "data" / app)
    old = tmp_path / "cfg" / "oldname"
    old.mkdir(parents=True)
    (old / settings.FILENAME).write_text('{"recent": ["a.astroproj"]}')
    created = settings.migrate_previous("newname", ["oldname"])
    assert created == [tmp_path / "cfg" / "newname"]
    assert settings.Settings(tmp_path / "cfg" / "newname").get("recent") == ["a.astroproj"]
    assert (old / settings.FILENAME).exists()  # old copy kept
    (tmp_path / "cfg" / "newname" / settings.FILENAME).write_text("{}")
    assert settings.migrate_previous("newname", ["oldname"]) == []  # never overwrites the new folder
