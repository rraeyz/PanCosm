"""ARC-16: one profile entered once; older settings move in; two windows do not undo each other's settings."""

import pytest

from astrowb.core import profiles
from astrowb.settings import Settings


def test_older_settings_move_into_the_profile(tmp_path):
    s = Settings(tmp_path)
    s.set("site", {"name": "TUG", "lat": 36.82, "lon": 30.34, "height": 2500.0})
    s.set("mpc", {"code": "A84", "observers": "A. B.", "catalog": "Gaia3"})
    assert profiles.section(s, "site")["lat"] == 36.82
    assert profiles.section(s, "observer")["mpc_code"] == "A84" and profiles.section(s, "camera")["gain"] == 0.0
    profiles.update(s, "observer", aavso_code="XYZ")
    assert Settings(tmp_path).get("profile")["observer"] == {"mpc_code": "A84", "observers": "A. B.",
                                                             "catalog": "Gaia3", "aavso_code": "XYZ"}  # fmt: skip
    with pytest.raises(KeyError):
        profiles.update(s, "camera", gian=2.0)


def test_two_settings_objects_do_not_undo_each_other(tmp_path):
    a, b = Settings(tmp_path), Settings(tmp_path)
    a.set("ui.theme", "dark")
    b.set("plan.utc_offset", 3.0)  # b was made before a's change
    assert Settings(tmp_path).values == {"ui.theme": "dark", "plan.utc_offset": 3.0}


def test_the_aavso_code_is_remembered(qapp, tmp_path):
    from astrowb.ui.aavso_dialog import AavsoDialog

    s = Settings(tmp_path)
    d = AavsoDialog(2, settings=s)
    d.obscode.setText("abc")
    d.accept()
    assert AavsoDialog(2, settings=Settings(tmp_path)).obscode.text() == "ABC"


def test_a_site_with_a_name_is_saved(tmp_path):
    s = Settings(tmp_path)
    profiles.update(s, "site", name="TUG", lat=36.8, lon=30.3, height=2500.0)
    assert profiles.section(s, "site")["name"] == "TUG" and s.get("site")["lat"] == 36.8


def test_profile_from_a_fits_header():
    """ARC-16 item 2: what a header gives about site, camera and observer; nothing it does not give."""
    from astropy.io import fits

    from astrowb.core.profiles import from_header

    h = fits.Header({"SITELAT": 36.8247, "SITELONG": 30.3353, "SITEELEV": 2500.0, "SITENAME": "TUG", "EGAIN": 1.4,
                     "RDNOISE": 7.2, "SATURATE": 65000, "OBSERVER": "A. Observer", "GAIN": 0})  # fmt: skip
    got = from_header(h)
    assert got["site"] == {"lat": 36.8247, "lon": 30.3353, "height": 2500.0, "name": "TUG"}
    assert got["camera"] == {"gain": 1.4, "read_noise": 7.2, "saturation": 65000.0}
    assert got["observer"] == {"name": "A. Observer"} and from_header(fits.Header()) == {}


def test_optics_and_pixel_scale(tmp_path):
    """ARC-16: aperture, focal length and pixel size from a header; the pixel scale follows (206.265 × µm / mm)."""
    from astropy.io import fits

    from astrowb.core import profiles
    from astrowb.settings import Settings

    settings = Settings(tmp_path)
    assert profiles.pixel_scale(settings) is None
    got = profiles.from_header(fits.Header({"FOCALLEN": 2000.0, "APTDIA": 280.0, "XPIXSZ": 3.76}))
    assert got["optics"] == {"aperture": 280.0, "focal_length": 2000.0} and got["camera"] == {"pixel_size": 3.76}
    for part, values in got.items():
        profiles.update(settings, part, **values)
    assert abs(profiles.pixel_scale(settings) - 0.38778) < 1e-4
