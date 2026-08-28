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


def _iraf_msigclip(values, lsigma=3.0, hsigma=3.0):
    """IRAF imcombine ic_msigclip (icsclip.gx) for one pixel, line by line: what is kept."""
    d = np.sort(values[np.isfinite(values)])
    n1, nl, nh = len(d), 0, len(d) - 1
    while True:
        n2, n3 = n1, nl + n1 // 2
        med = (d[n3 - 1] + d[n3]) / 2 if n1 % 2 == 0 else d[n3]
        if n1 >= 3:
            s = np.sqrt(np.sum((d[nl : nh + 1] - med) ** 2) / (n1 - 1))
            if s > 0:
                while nl <= nh and (med - d[nl]) / s > lsigma:
                    nl, n1 = nl + 1, n1 - 1
                while nh >= nl and (d[nh] - med) / s > hsigma:
                    nh, n1 = nh - 1, n1 - 1
        if n1 == n2 or n1 < 3:
            return d[nl : nh + 1]


def test_sigma_clipping_is_iraf_imcombines_where_ten_frames_cover_the_pixel():
    """rejection="sigma" keeps, pixel by pixel, what IRAF's sigclip keeps (40 LCO frames with a satellite trail and
    cosmic rays: the same sky noise as IRAF, 2.022 / 2.023 ADU; the median / MAD clipping 2.055); where fewer than
    ten frames cover a pixel it falls back to the median / MAD spread, which still rejects a single cosmic ray."""
    rng = np.random.default_rng(0)
    b = rng.normal(1000, 10, (25, 30, 40)).astype(np.float32)
    b[rng.integers(0, 25, 300), rng.integers(0, 30, 300), rng.integers(0, 40, 300)] += rng.uniform(50, 5000, 300)
    b[3:6, 2, 2] = np.nan
    b[:, 4, 4] = 7.0  # equal values
    keep = stacking.reject(b, "sigma", 3.0)
    for y in range(30):
        for x in range(40):
            if np.isfinite(b[:, y, x]).sum() >= stacking.IRAF_MIN_FRAMES:
                np.testing.assert_array_equal(np.sort(b[:, y, x][keep[:, y, x]]), _iraf_msigclip(b[:, y, x]))
    few = rng.normal(1000, 10, (7, 5, 5)).astype(np.float32)
    few[3, 2, 2] = 6000.0  # IRAF's rms about the median puts it only 2.45 sigma off
    assert _iraf_msigclip(few[:, 2, 2]).max() == 6000.0
    assert not stacking.reject(few, "sigma", 3.0)[3, 2, 2]
    np.testing.assert_array_equal(stacking.reject(few, "sigma", 3.0), stacking.reject(few, "mad", 3.0))


def test_a_shift_is_resampled_as_map_coordinates_does(tmp_path):
    """Pure shifts are resampled from four slices with the same two weights for every pixel; the result is
    map_coordinates(order=1, cval=NaN), edges and the last row / column included."""
    from scipy.ndimage import map_coordinates

    img = np.random.default_rng(1).normal(1000, 10, (50, 60)).astype(np.float32)
    fits.PrimaryHDU(img).writeto(tmp_path / "a.fits")
    with fits.open(tmp_path / "a.fits") as h:
        for t in [(0, 0), (1.5, -2.25), (-3.7, 4.1), (0.0, 0.5), (-0.3, -0.8), (59.5, 0), (0, -49.9), (100, 3)]:
            for b0, b1 in [(0, 50), (10, 20), (45, 50)]:
                yy, xx = np.meshgrid(np.arange(b0, b1, dtype=float), np.arange(60, dtype=float), indexing="ij")
                ref = map_coordinates(img, [yy + t[1], xx + t[0]], order=1, cval=np.nan, prefilter=False)
                got = stacking._shifted_rows(h[0], b0, b1, t, 50, 60)
                np.testing.assert_allclose(got, ref, rtol=1e-6, equal_nan=True)


def test_the_quality_check_keeps_the_shifts_for_the_light_curve(frames, monkeypatch):
    """The quality check measures the shift between consecutive frames while each is open; align_offsets (the
    comparison suggestion, the light curve) then reads them instead of opening every frame again, and computes only
    the pairs that are new (frames left out after the check)."""
    from astrowb.engine.steps import execute

    paths, _ = frames
    fresh = stacking.align_offsets(paths)

    class Ctx:
        def progress(self, *a, **k):
            pass

        def check(self):
            pass

    from astrowb.settings import config_dir

    (config_dir() / "shifts.json").unlink()  # forget the shifts measured above
    execute("photometry.quality", {"images": [str(p) for p in paths]}, {}, Ctx())
    real, calls = stacking._run_shifts, []
    monkeypatch.setattr(stacking, "_run_shifts", lambda run: pytest.fail("frames read again"))
    assert stacking.align_offsets(paths) == fresh
    monkeypatch.setattr(stacking, "_run_shifts", lambda run: calls.append(len(run[0])) or real(run))
    stacking.align_offsets([paths[0], paths[1], paths[3], paths[4]])  # frame 2 left out: one new pair, 2 frames
    assert calls == [2]
