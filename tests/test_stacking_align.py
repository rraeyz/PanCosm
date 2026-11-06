"""Stacking: alignment off (frames aligned already) and on stars the user picked (the owner, 2026-11-13: the
automatic ways are not always right; the user decides)."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration.stacking import align_transforms


def frames(tmp_path, shifts):
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[:120, :120]
    paths = []
    for i, (dx, dy) in enumerate(shifts):
        img = rng.normal(100, 5, (120, 120))
        for x, y, f in ((40.3, 50.2, 3e4), (80.1, 70.6, 2e4), (60.0, 95.0, 1e4)):
            img += f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / 8.0)
        fits.PrimaryHDU(img.astype(np.float32)).writeto(tmp_path / f"f{i}.fits")
        paths.append(str(tmp_path / f"f{i}.fits"))
    return paths


def test_none_and_picked(tmp_path):
    shifts = [(0, 0), (3.4, -2.1), (7.9, -4.0), (12.2, -6.5)]  # a drift of 14 px over the night
    paths = frames(tmp_path, shifts)
    assert all(np.array_equal(t, [0, 0]) for _, t in align_transforms(paths, "none"))
    got = [t for _, t in align_transforms(paths, "picked", stars=[(41, 49), (79, 71)])]  # clicks a pixel off
    assert np.allclose(got, shifts, atol=0.1)
    with pytest.raises(ValueError, match="pick at least one star"):
        align_transforms(paths, "picked")


def test_stars_picked_on_the_first_frame(tmp_path, qapp):
    """The picker snaps a click onto its star and takes it off on a second click; the stacking options carry them."""
    from astrowb.ui.star_picker import StarPicker, as_text, parse

    paths = frames(tmp_path, [(0, 0)])
    dlg = StarPicker(paths[0])
    dlg.click(42.0, 51.0)
    dlg.click(80.0, 70.0)
    assert np.allclose(dlg.stars, [(40.3, 50.2), (80.1, 70.6)], atol=0.1)
    dlg.click(80.5, 70.5)
    assert len(dlg.stars) == 1 and parse(as_text(dlg.stars)) == [(40.3, 50.2)]
    dlg.close()
    with pytest.raises(ValueError):
        parse("1 2 3")


def test_images_window_asks_how_to_align(tmp_path, qapp, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    from astrowb.ui import star_picker

    paths = frames(tmp_path, [(0, 0)])
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: (a[3][2], True))  # "none"
    assert star_picker.choose_alignment(None, paths[0]) == {"align": "none"}
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: (a[3][0], False))  # cancelled
    assert star_picker.choose_alignment(None, paths[0]) is None


def test_picked_stars_follow_a_rotated_and_shifted_field(tmp_path):
    """Three stars picked: a field turned by 3° and shifted 6 px between frames (a meridian flip's cousin, an alt-az
    mount) is followed with its rotation."""
    rng = np.random.default_rng(1)
    yy, xx = np.mgrid[:160, :160]
    stars = np.array([(50.3, 60.2), (110.1, 70.6), (80.0, 120.0), (40.0, 130.0)])
    paths = []
    for i, ang in enumerate((0.0, 1.5, 3.0)):
        c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        m = np.array([[c, -s], [s, c]])
        t = np.array([2.0 * i, -1.0 * i])
        img = rng.normal(100, 5, (160, 160))
        for x, y in stars @ m.T + t:
            img += 2e4 / (2 * np.pi * 4) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 8.0)
        fits.PrimaryHDU(img.astype(np.float32)).writeto(tmp_path / f"r{i}.fits")
        paths.append(str(tmp_path / f"r{i}.fits"))
    got = align_transforms(paths, "picked", stars=stars[:3] + 0.8)
    m, t = got[2]
    assert np.degrees(np.arctan2(m[1, 0], m[0, 0])) == pytest.approx(3.0, abs=0.05)
    assert np.allclose(stars[3] @ m.T + t, stars[3] @ np.array([[np.cos(np.radians(3)), -np.sin(np.radians(3))],
                       [np.sin(np.radians(3)), np.cos(np.radians(3))]]).T + [4.0, -2.0], atol=0.1)  # fmt: skip


def test_photometry_follows_a_turning_field_on_picked_stars(tmp_path):
    """Frames turned by 4° each (an alt-az mount): the automatic shift cannot place them; the light curve placed by
    three picked stars measures every frame, and the target's flux stays where it is."""
    from astrowb.photometry.lightcurve import light_curve

    rng = np.random.default_rng(2)
    yy, xx = np.mgrid[:200, :200]
    stars = np.array([(100.3, 100.2), (60.1, 70.6), (140.0, 130.0), (70.0, 150.0), (150.0, 60.0)])
    paths = []
    for i in range(6):
        a = np.radians(4.0 * i)
        m = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        img = rng.normal(100, 5, (200, 200))
        for x, y in (stars - 100) @ m.T + 100 + [1.5 * i, 0.5 * i]:
            img += 3e4 / (2 * np.pi * 4) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 8.0)
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"t{i}.fits")
        paths.append(str(tmp_path / f"t{i}.fits"))
    lc = light_curve(paths, stars[0], stars[1:3], 5, 10, 14, track_stars=stars[2:5])
    assert len(lc["time"]) == 6 and not lc["lost"]
    assert np.allclose(lc["rel_flux"], 0.5, rtol=0.02)
