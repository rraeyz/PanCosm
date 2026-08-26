import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import masters, stacking

NY, NX = 80, 100
STARS = [(30.3, 40.7, 8000), (70.1, 20.4, 5000), (50.0, 60.0, 3000), (15.5, 65.2, 4000), (85.0, 50.0, 6000)]


def frame(dx, dy, rng, noise=10.0):
    y, x = np.mgrid[:NY, :NX]
    img = np.full((NY, NX), 500.0)
    for sx, sy, f in STARS:
        img += f / (2 * np.pi * 1.8**2) * np.exp(-((x - sx - dx) ** 2 + (y - sy - dy) ** 2) / (2 * 1.8**2))
    return img + rng.normal(0, noise, img.shape)


@pytest.fixture
def frames(tmp_path):
    rng = np.random.default_rng(0)
    shifts = [(0, 0), (1.3, -0.7), (2.9, -1.6), (4.2, -2.1), (5.6, -3.3), (7.1, -4.2), (8.4, -5.0)]
    paths = []
    for i, (dx, dy) in enumerate(shifts):
        img = frame(dx, dy, rng)
        if i == 3:
            img[40, 30] += 5000  # cosmic ray in one frame
        p = tmp_path / f"f{i}.fits"
        fits.PrimaryHDU(img.astype(np.float32), fits.Header({"EXPTIME": 30.0})).writeto(p)
        paths.append(p)
    return paths, shifts


def test_offsets_recovered(frames):
    paths, shifts = frames
    found = stacking.align_offsets(paths)
    np.testing.assert_allclose(found, shifts, atol=0.15)


def test_offsets_of_the_same_frames_are_kept(frames, monkeypatch):
    """The shifts are measured once for the same files (comparison stars, then the light curve, then other radii:
    22 s each for 265 LCO frames); a file written again is measured again."""
    paths, _ = frames
    first = stacking.align_offsets(paths)
    real = stacking._run_shifts
    monkeypatch.setattr(stacking, "_run_shifts", lambda run: pytest.fail("frames read again"))
    assert stacking.align_offsets(paths) == first
    data = fits.getdata(paths[2], memmap=False)  # Windows cannot overwrite a mapped file
    fits.PrimaryHDU(np.roll(data, 3, axis=1), fits.Header({"EXPTIME": 30.0})).writeto(paths[2], overwrite=True)
    monkeypatch.setattr(stacking, "_run_shifts", real)
    again = stacking.align_offsets(paths)
    assert abs(again[2][0] - first[2][0] - 3) < 0.15 and again[3] == pytest.approx(first[3], abs=0.15)


def test_stack_aligns_reduces_noise_rejects_cosmics(frames, monkeypatch):
    paths, shifts = frames
    monkeypatch.setattr(stacking, "STACK_BUDGET", 7 * NX * 4 * 9)  # 9 rows per block: exercise block edges
    img, cnt, header = stacking.stack(paths, shifts)
    truth = frame(0, 0, np.random.default_rng(1), noise=0.0)
    inner = (slice(8, NY - 8), slice(4, NX - 12))  # covered by every frame
    resid = (img - truth)[inner]
    assert abs(np.median(resid)) < 2  # stars in the reference frame's place, no blur bias
    assert resid.std() < 10 / np.sqrt(7) * 1.6  # noise down by ~sqrt(N) (bilinear resampling smooths a bit)
    assert img[40, 30] - truth[40, 30] < 30  # the cosmic ray is gone
    assert cnt[inner].min() == 7 and cnt[NY - 1, NX - 1] < 7  # edge pixels are covered by fewer frames
    assert header["NCOMBINE"] == 7


def test_saved_stack_has_coverage(frames, tmp_path):
    paths, shifts = frames
    img, cnt, header = stacking.stack(paths, shifts)
    out = stacking.save_stack(tmp_path / "stack.fits", img, cnt, header)
    with fits.open(out) as h:
        assert h["COVERAGE"].data.max() == 7 and h[0].header["NCOMBINE"] == 7
    assert masters.load(out)[0].shape == (NY, NX)
