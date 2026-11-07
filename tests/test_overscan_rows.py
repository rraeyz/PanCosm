"""Row-by-row overscan (PLAN 4.8 item 17): bias structure along the readout is followed, a flat bias stays flat."""

import numpy as np
from astropy.io import fits

from astrowb.calibration.masters import load, master_bias


def frame(path, bias_rows, strip="right", signal=200.0, seed=0):
    rng = np.random.default_rng(seed)
    ny, nx = 120, 90
    img = np.zeros((ny, nx), np.float32)
    if strip == "right":
        img += bias_rows[:, None]
        img[:, :80] += signal
        h = {"BIASSEC": "[83:90,1:120]", "TRIMSEC": "[1:80,1:120]"}
    else:  # overscan rows along the top, bias varying along the columns
        img += bias_rows[None, :nx]
        img[:110, :] += signal
        h = {"BIASSEC": "[1:90,113:120]", "TRIMSEC": "[1:90,1:110]"}
    img += rng.normal(0, 3, img.shape)
    fits.PrimaryHDU(img, fits.Header(h)).writeto(path)
    return str(path)


def test_bias_ramp_along_the_rows_is_removed(tmp_path):
    rows = np.arange(120, dtype=float)
    bias = 500 + 0.4 * rows + 15 * np.sin(rows / 40)  # a drifting, curved bias along the readout
    data, h = load(frame(tmp_path / "a.fits", bias))
    assert data.shape == (120, 80)
    prof = data.mean(axis=1)
    assert np.std(prof - 200) < 1.0  # a single level would leave ~16 ADU of structure
    assert abs(h["OVERSCAN"] - bias.mean()) < 1


def test_strip_of_rows_and_flat_bias(tmp_path):
    cols = np.arange(90, dtype=float)
    data, _ = load(frame(tmp_path / "b.fits", 480 + 0.3 * cols, strip="top"))
    assert data.shape == (110, 90) and np.std(data.mean(axis=0) - 200) < 1.0
    flat = [frame(tmp_path / f"f{i}.fits", np.full(120, 500.0), signal=0.0, seed=i) for i in range(5)]
    master, _ = master_bias(flat)  # read in row blocks: the per-row levels must line up with the blocks
    assert abs(float(np.mean(master))) < 0.3 and np.std(master.mean(axis=1)) < 0.5


def test_a_crop_is_the_same_part_of_the_whole_frame(tmp_path):
    """load(path, crop) (the light curve reads only the part around its stars) gives that part of load(path),
    overscan levels per row or per column included, also as a tile-compressed (fpack) frame."""
    rows = 500 + 0.4 * np.arange(120, dtype=float)
    paths = [frame(tmp_path / "r.fits", rows), frame(tmp_path / "t.fits", 480 + 0.3 * np.arange(120.0), strip="top")]
    data, h = load(paths[0])
    fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(data, h)]).writeto(tmp_path / "c.fits.fz")
    for p in [*paths, str(tmp_path / "c.fits.fz")]:
        whole, h = load(p)
        for y0, y1, x0, x1 in [(10, 50, 5, 30), (100, 500, 60, 500), (0, 120, 0, 90)]:
            part, h2 = load(p, (y0, y1, x0, x1))
            assert np.array_equal(part, whole[y0:y1, x0:x1]) and dict(h2) == dict(h)
