"""CAL-7: the plan takes the library's masters for what the night lacks (marked, within validity), the night's own
win, a run's masters are filed in the library, and the follow mode uses it for a light of an empty run."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration.frames import Frame
from astrowb.calibration.library import Library
from astrowb.calibration.library_use import add_masters, fill
from astrowb.calibration.live import LiveCalibrator
from astrowb.calibration.matching import make_plan
from astrowb.core.errors import AppError
from astrowb.engine.steps import execute
from astrowb.settings import ENV_CONFIG_DIR

SHAPE = (40, 50)
LIGHT_DATE = "2026-11-14T20:00:00"


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def _fits(path, level, **cards):
    path.parent.mkdir(parents=True, exist_ok=True)
    fits.PrimaryHDU(np.full(SHAPE, level, np.float32), fits.Header(cards)).writeto(path, overwrite=True)
    return path


def _library(tmp_path, flat_date="2026-11-04T18:00:00"):
    lib = Library(tmp_path / "lib")
    src = tmp_path / "libsrc"
    lib.add(_fits(src / "master_bias_00.fits", 300, IMAGETYP="Bias", **{"DATE-OBS": "2026-11-04T18:00:00"}))
    lib.add(
        _fits(src / "master_dark_01.fits", 310, IMAGETYP="Dark", EXPTIME=30.0, **{"DATE-OBS": "2026-11-04T18:00:00"})
    )
    lib.add(_fits(src / "master_flat_02.fits", 1.0, IMAGETYP="Flat", **{"DATE-OBS": flat_date}))
    return str(tmp_path / "lib")


def _night(tmp_path, kinds):
    """Lights and the calibration frames of `kinds` (bias / dark / flat) of the night; the scanned frames."""
    raw, lights = tmp_path / "raw", tmp_path / "lights"
    levels = {"bias": (300, {}), "dark": (310, {"EXPTIME": 30.0}), "flat": (20000, {"EXPTIME": 1.0})}
    for i in range(3):
        for k in kinds:
            _fits(raw / f"{k}{i}.fits", levels[k][0] + i, IMAGETYP=k.upper(), **levels[k][1])
        _fits(lights / f"l{i}.fits", 900, IMAGETYP="LIGHT", EXPTIME=30.0, **{"DATE-OBS": LIGHT_DATE})
    raw.mkdir(exist_ok=True)
    return execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())["frames"]


def _frames(dicts):
    return [Frame(**f | {"binning": tuple(f["binning"]), "shape": tuple(f["shape"])}) for f in dicts]


def test_a_night_without_darks_and_bias_takes_the_library_marked(tmp_path):
    frames = _night(tmp_path, ["flat"])
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "out")},
                  {"library_folder": _library(tmp_path)}, Ctx())  # fmt: skip
    assert sorted(out["library_used"]) == [["master_bias_00.fits", "bias"], ["master_dark_01.fits", "dark"]]
    assert not [m for m in out["missing"] if m[1] in ("bias", "dark")]
    h = fits.getheader(out["calibrated"][0])
    assert h["CALB"] == "master_bias_00.fits" and h["CALD"] == "master_dark_01.fits"
    plan = make_plan(_frames(frames))
    fill(plan, _frames(frames), _library(tmp_path), load=False)
    assert {(k, round(n["age"])) for _, k, n in plan.library if n["used"]} == {("bias", 10), ("dark", 10)}


def test_an_old_flat_is_listed_not_used(tmp_path):
    frames = _frames(_night(tmp_path, []))
    plan = make_plan(frames)
    assert fill(plan, frames, _library(tmp_path, flat_date="2026-10-05T18:00:00")).keys() == {
        k for e in plan.lights for k in [e["bias"], e["dark"]]
    }
    flat = [(p, k, n) for p, k, n in plan.library if k == "flat"]
    assert flat and not flat[0][2]["used"] and flat[0][2]["valid_days"] == 7.0 and round(flat[0][2]["age"]) == 40
    assert {k for _, k, _ in plan.missing} == {"flat"}  # still missing: calibrated without, as today


def test_the_nights_own_dark_wins(tmp_path):
    frames = _night(tmp_path, ["bias", "dark", "flat"])
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "out")},
                  {"library_folder": _library(tmp_path)}, Ctx())  # fmt: skip
    assert out["library_used"] == []
    assert fits.getheader(out["calibrated"][0])["CALD"] == "master_dark_01.fits"  # the night's, built in out/masters
    assert str(tmp_path / "out") in [p for p in out["masters"] if "master_dark" in p][0]


def test_a_kind_chosen_none_is_not_filled_from_the_library(tmp_path):
    frames = _night(tmp_path, ["flat"])
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "out")},
                  {"library_folder": _library(tmp_path), "use": {"*": {"dark": "none"}}}, Ctx())  # fmt: skip
    assert out["library_used"] == [["master_bias_00.fits", "bias"]]
    assert fits.getheader(out["calibrated"][0])["CALD"] == "none"


@pytest.mark.parametrize("on", [True, False])
def test_masters_of_a_run_are_added_when_the_setting_is_on(qtbot, tmp_path, monkeypatch, on):
    monkeypatch.setenv(ENV_CONFIG_DIR, str(tmp_path / "cfg"))
    from astrowb.settings import Settings
    from astrowb.ui.calibrate_page import CalibratePage

    s = Settings()
    s.set("calibration.add_to_library", on)
    s.set("calibration.library_folder", str(tmp_path / "lib"))
    frames = _night(tmp_path, ["bias", "dark", "flat"])
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "out")}, {}, Ctx())
    page = CalibratePage()
    qtbot.addWidget(page)
    page.output.setText(str(tmp_path / "out"))
    page.show_result(out)
    if on:
        assert "3 masters added to the library" in page.result.text()
        assert len(Library(tmp_path / "lib").entries) == 3
        assert add_masters(str(tmp_path / "lib"), out["masters"]) == 0  # not twice
    else:
        assert "added to the library" not in page.result.text() and not (tmp_path / "lib").exists()


def test_follow_with_an_empty_run_uses_the_library_and_skips_a_light_with_no_match(tmp_path):
    live = LiveCalibrator([], tmp_path / "live", library=_library(tmp_path))
    ok = _fits(tmp_path / "in" / "a.fits", 900, IMAGETYP="LIGHT", EXPTIME=30.0, **{"DATE-OBS": LIGHT_DATE})
    h = fits.getheader(live.process(ok))
    assert h["CALB"] == "master_bias_00.fits" and h["CALD"] == "master_dark_01.fits" and h["CALF"] == "none"
    odd = _fits(tmp_path / "in" / "b.fits", 900, IMAGETYP="LIGHT", EXPTIME=30.0, XBINNING=3, YBINNING=3,
                **{"DATE-OBS": LIGHT_DATE})  # fmt: skip
    with pytest.raises(AppError, match="no master in the library"):
        live.process(odd)
    assert live.process(ok)  # following goes on
