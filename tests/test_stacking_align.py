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
