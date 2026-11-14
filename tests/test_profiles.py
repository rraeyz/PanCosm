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


def test_header_filter_names_become_aavso_bands(tmp_path):
    """ARC-16: "Johnson V" is V, "Luminance" CV, Sloan names S-bands; the profile's own table wins; an unknown
    name is left to the user."""
    settings = Settings(tmp_path)
    got = [profiles.aavso_band(settings, n) for n in ("V", "Johnson V", "Luminance", "r'", "Green", "Ha", None)]
    assert got == ["V", "V", "CV", "SR", "TG", None, None]
    profiles.update(settings, "filters", names={"Ha": "CR"})
    assert profiles.aavso_band(settings, "Ha") == "CR"


def test_aavso_dialog_takes_the_band_from_the_images(qtbot, tmp_path):
    import numpy as np
    from astropy.io import fits

    from astrowb.ui.aavso_dialog import AavsoDialog

    image = tmp_path / "a.fits"
    fits.PrimaryHDU(np.zeros((4, 4)), fits.Header({"FILTER": "Johnson V"})).writeto(image)
    dialog = AavsoDialog(2, settings=Settings(tmp_path))
    qtbot.addWidget(dialog)
    assert dialog.band_of([str(image)]) == "V" and dialog.band_of([]) is None


def test_a_plate_solution_that_disagrees_with_the_profile_is_found(tmp_path):
    from astropy.io import fits

    settings = Settings(tmp_path)
    solved = fits.Header({"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 10.0, "CRVAL2": 20.0,
                          "CDELT1": -0.62 / 3600, "CDELT2": 0.62 / 3600, "CRPIX1": 50, "CRPIX2": 50})  # fmt: skip
    assert profiles.scale_differs(settings, solved) is None  # no scale in the profile yet
    profiles.update(settings, "camera", pixel_size=3.76)
    profiles.update(settings, "optics", focal_length=1250.0)  # 0.620 ″/px
    assert profiles.scale_differs(settings, solved) is None
    profiles.update(settings, "optics", focal_length=2000.0)  # 0.388 ″/px: a reducer forgotten
    mine, got = profiles.scale_differs(settings, solved)
    assert abs(mine - 0.388) < 0.001 and abs(got - 0.62) < 1e-6
    assert profiles.scale_differs(settings, fits.Header()) is None


def test_aavso_dialog_transforms_with_a_colour_term(qapp, tmp_path):
    from astrowb.ui.aavso_dialog import AavsoDialog

    d = AavsoDialog(2, settings=Settings(tmp_path))
    d.star.setText("NY Vir")
    d.obscode.setText("abc")
    d.mags.setText("11.20, 11.85")
    assert "transform" not in d.values()  # empty: untransformed
    d.coefficient.setText("0,085")
    d.comp_colours.setText("0.62, 0.71")
    with pytest.raises(ValueError, match="colour"):
        d.values()  # the variable's colour missing
    d.target_colour.setText("-0.4")
    t = d.values()["transform"]
    assert t["coefficient"] == 0.085 and t["colour_c"] == [0.62, 0.71] and t["colour_t"] == -0.4


def test_several_profiles(tmp_path):
    """ARC-16: a second site and camera beside the first; switching brings each back whole, readers of "site" follow."""
    from astrowb.core import profiles
    from astrowb.settings import Settings

    s = Settings(tmp_path)
    profiles.update(s, "site", name="Ankara", lat=39.8, lon=32.8)
    profiles.update(s, "camera", gain=1.2)
    profiles.save_as(s, "La Palma")
    assert profiles.active(s) == "La Palma" and profiles.section(s, "camera")["gain"] == 1.2  # a copy
    profiles.update(s, "site", name="ORM", lat=28.76, lon=-17.88)
    assert profiles.names(s) == ["La Palma", "Default"] and s.get("site")["name"] == "ORM"
    profiles.switch(s, "Default")
    assert profiles.section(s, "site")["name"] == "Ankara" and Settings(tmp_path).get("site")["lat"] == 39.8
    profiles.switch(s, "La Palma")
    assert profiles.section(s, "site")["lat"] == 28.76
    profiles.switch(s, "Empty")
    assert not profiles.has(s, "site") and profiles.section(s, "camera")["gain"] == 0.0
    with pytest.raises(ValueError):
        profiles.remove(s, "Empty")
    with pytest.raises(ValueError):
        profiles.save_as(s, "Default")
    profiles.remove(s, "Default")
    assert profiles.names(s) == ["Empty", "La Palma"]


def test_a_profile_is_exported_and_imported(tmp_path):
    """ARC-16 item 2: a profile file moves a profile to another computer; unknown fields are dropped."""
    import json

    from astrowb.core import profiles
    from astrowb.settings import Settings

    a = Settings(tmp_path / "a")
    profiles.update(a, "site", name="Ankara", lat=39.8)
    profiles.update(a, "spectrograph", kind="long-slit", grating=600.0)
    profiles.update(a, "filters", zero_points={"V": 21.3}, focus_offsets={"V": -12})
    profiles.export_profile(a, tmp_path / "p.json")
    b = Settings(tmp_path / "b")
    with pytest.raises(ValueError, match="exists already"):  # the file's own name is taken on b
        profiles.import_profile(b, tmp_path / "p.json")
    doc = json.loads((tmp_path / "p.json").read_text())
    doc["name"], doc["site"]["bogus"], doc["alien"] = "Copy", 1, {"x": 1}
    (tmp_path / "q.json").write_text(json.dumps(doc))
    assert profiles.import_profile(b, tmp_path / "q.json") == "Copy" and profiles.active(b) == "Default"
    profiles.switch(b, "Copy")
    assert profiles.section(b, "site")["name"] == "Ankara" and "bogus" not in profiles.section(b, "site")
    assert profiles.section(b, "spectrograph")["grating"] == 600.0
    assert profiles.section(b, "filters")["zero_points"] == {"V": 21.3}
    with pytest.raises(ValueError, match="exists already"):
        profiles.import_profile(b, tmp_path / "q.json")
    (tmp_path / "bad.json").write_text("[1]")
    with pytest.raises(ValueError, match="not a profile file"):
        profiles.import_profile(b, tmp_path / "bad.json")


def test_the_chooser_exports_and_imports(qtbot, tmp_path):
    from PySide6.QtWidgets import QWidget

    from astrowb.core import profiles
    from astrowb.settings import Settings
    from astrowb.ui.profile_chooser import ProfileChooser

    host = QWidget()
    qtbot.addWidget(host)
    host.settings, host.profile_controls, host._show_scale = Settings(tmp_path), {}, lambda: None
    chooser = ProfileChooser(host)
    profiles.update(host.settings, "site", name="Ankara")
    chooser.export(str(tmp_path / "p.json"))
    (tmp_path / "p.json").write_text((tmp_path / "p.json").read_text().replace('"Default"', '"Copy"'))
    assert chooser.import_file(str(tmp_path / "p.json")) == "Copy"
    assert profiles.names(host.settings) == ["Default", "Copy"]
