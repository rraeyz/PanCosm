"""Speed changes of PLAN 4.8 item 12 must not change any result: each fast path against the method it replaced."""

import numpy as np
from astropy.stats import sigma_clipped_stats

from astrowb.photometry import aperture


def _old_frame_shift(ref, img, dtype=np.float64):
    """The complex-FFT version that rfft2 replaced. Under NumPy 2 it ran in single precision (float32 in,
    complex64 out); dtype=float64 is the exact reference for the new double-precision code."""

    def prep(a):
        a = aperture.despike(a)
        _, med, std = sigma_clipped_stats(a[::2, ::2])
        return np.fft.fft2(np.clip(a - med - 3 * std, 0, 50 * std).astype(dtype))

    corr = np.fft.ifft2(prep(img) * np.conj(prep(ref))).real
    py, px = np.unravel_index(np.argmax(corr), corr.shape)

    def refine(c_m, c_0, c_p):
        d = c_m - 2 * c_0 + c_p
        return 0.0 if d == 0 else 0.5 * (c_m - c_p) / d

    ny, nx = corr.shape
    dy = py + refine(corr[(py - 1) % ny, px], corr[py, px], corr[(py + 1) % ny, px])
    dx = px + refine(corr[py, (px - 1) % nx], corr[py, px], corr[py, (px + 1) % nx])
    return (dx - nx if dx > nx / 2 else dx), (dy - ny if dy > ny / 2 else dy)


def test_frame_shift_with_real_fft_equals_the_complex_fft():
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[:301, :257]  # odd and uneven sizes: irfft2 must get the shape back exactly
    stars = rng.uniform([10, 10, 500], [247, 291, 5e4], (60, 3))

    def frame(dx, dy):
        img = rng.normal(400, 8, xx.shape)
        for x, y, f in stars:
            img += f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / (2 * 2.0**2))
        return img.astype(np.float32)

    ref = frame(0, 0)
    for dx, dy in ((3.3, -1.7), (-12.6, 8.2), (0.4, 0.0)):
        img = frame(dx, dy)
        aperture._last_fft.clear()
        new = aperture.frame_shift(ref, img)
        old = _old_frame_shift(ref, img)
        assert np.allclose(new, old, rtol=0, atol=1e-9), (new, old)
        single = _old_frame_shift(ref, img, np.float32)  # what the old code computed: within 1e-5 px
        assert np.allclose(new, single, rtol=0, atol=1e-5)
        assert np.allclose(new, (dx, dy), atol=0.15)  # and it finds the true shift


def test_despike_in_threads_equals_the_median_filter():
    from scipy.ndimage import median_filter

    rng = np.random.default_rng(8)
    a = rng.normal(100, 10, (1100, 333)).astype(np.float32)  # three blocks of rows, the last one short
    a[rng.integers(0, 1100, 500), rng.integers(0, 333, 500)] = 6e4
    assert np.array_equal(aperture.despike(a), median_filter(a, size=3, mode="reflect"))
    assert np.array_equal(aperture.despike(a, rows=2000), aperture.despike(a))  # one block = many blocks
