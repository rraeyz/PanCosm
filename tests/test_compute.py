import numpy as np
import pytest
from astropy.stats import sigma_clip

from astrowb import compute
from astrowb.compute.combine import clipped_mean


@pytest.fixture
def stack():
    rng = np.random.default_rng(42)
    s = rng.normal(100, 5, (15, 40, 30)).astype(np.float32)
    s[3, 10, 10] = 5000  # cosmic ray
    s[7, 5, 5] = -800
    s[:, 0, 0] = np.nan  # dead pixel in every frame
    s[2, 1, 1] = np.inf
    return s


def reference(stack, sigma=3.0, maxiters=5):
    clipped = sigma_clip(stack, sigma=sigma, maxiters=maxiters, cenfunc="median", stdfunc="mad_std", axis=0)
    return clipped.mean(axis=0).filled(np.nan), (~clipped.mask).sum(0)


@pytest.fixture
def cpu_mode():
    compute.set_mode("cpu")
    yield
    compute.set_mode("auto")


@pytest.fixture
def gpu_mode():
    compute.set_mode("gpu")  # accepts software adapters (CI has no GPU)
    if compute.device() is None:
        compute.set_mode("auto")
        pytest.skip(f"no wgpu adapter: {compute.describe()}")
    yield
    compute.set_mode("auto")


def test_cpu_matches_astropy(stack, cpu_mode):
    img, cnt, used = clipped_mean(stack)
    ref, ref_cnt = reference(stack)
    assert used == "cpu"
    np.testing.assert_allclose(img, ref, rtol=1e-6, equal_nan=True)
    np.testing.assert_array_equal(cnt, ref_cnt)
    assert cnt[10, 10] == 14 and abs(img[10, 10] - 100) < 5  # cosmic ray rejected
    assert np.isnan(img[0, 0]) and cnt[0, 0] == 0


def test_gpu_matches_cpu(stack, gpu_mode):
    img, cnt, used = clipped_mean(stack, use_gpu=True)
    assert used == "gpu"
    ref, ref_cnt = reference(stack)
    np.testing.assert_allclose(img, ref, rtol=1e-5, equal_nan=True)
    np.testing.assert_array_equal(cnt, ref_cnt)


def test_gpu_chunks_and_2d_dispatch(gpu_mode, monkeypatch):
    rng = np.random.default_rng(1)
    s = rng.normal(0, 1, (4, 300, 300)).astype(np.float32)
    monkeypatch.setattr("astrowb.compute.combine.max_binding_bytes", lambda: 4 * 4 * 10_000)  # force 9+ chunks
    img, _, used = clipped_mean(s, use_gpu=True)
    assert used == "gpu"
    np.testing.assert_allclose(img, reference(s)[0], rtol=1e-4, atol=1e-6)
    assert compute.dispatch_size(64 * 70_000) == (65535, 2, 1)


def test_gpu_failure_falls_back_to_cpu(stack, gpu_mode, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("device lost")

    monkeypatch.setattr("astrowb.compute.combine.run", broken)
    img, _, used = clipped_mean(stack, use_gpu=True)
    assert used == "cpu" and not np.isnan(img[5, 5])
    assert "device lost" in compute.describe()


def test_cpu_mode_never_touches_gpu(cpu_mode):
    assert compute.device() is None and compute.describe() == "CPU"


@pytest.mark.parametrize("method", ["mean", "median", "sum"])
@pytest.mark.parametrize("rejection", ["none", "sigma", "winsorized", "minmax", "percentile"])
def test_gpu_stack_combine_matches_numpy(stack, gpu_mode, method, rejection):
    """Every method and rejection of the stacking page on the GPU gives the NumPy result (calibration.stacking.combine,
    the reference and the fallback), weights included."""
    from astrowb.calibration.stacking import combine
    from astrowb.compute.stack import gpu_combine

    s = np.where(np.isfinite(stack), stack, np.nan)  # the stacker marks uncovered pixels NaN
    low, high = (2, 3) if rejection == "minmax" else (0.05, 0.05) if rejection == "percentile" else (1, 1)
    w = None if method == "median" else np.linspace(0.5, 1.5, len(s))
    cpu = combine(s, method, rejection, 3.0, low, high, w)
    gpu = gpu_combine(s, method, rejection, 3.0, low, high, w, force=True)
    np.testing.assert_allclose(gpu, cpu, rtol=1e-6, equal_nan=True)


def test_gpu_stack_matches_cpu_stack(tmp_path, gpu_mode, monkeypatch):
    """A whole stack (resampled frames, normalisation, a GPU failure half-way) comes out as on the CPU."""
    from astropy.io import fits

    from astrowb.calibration import stacking
    from astrowb.compute import stack as gstack

    rng = np.random.default_rng(3)
    paths = []
    for i in range(9):
        img = rng.normal(500 + 10 * i, 8, (60, 50)).astype(np.float32)
        img[rng.integers(0, 60, 30), rng.integers(0, 50, 30)] = 9000
        paths.append(tmp_path / f"f{i}.fits")
        fits.PrimaryHDU(img).writeto(paths[-1])
    offsets = [(0.3 * i, -0.2 * i) for i in range(9)]
    args = {"method": "median", "rejection": "winsorized", "normalize": "additive"}
    compute.set_mode("cpu")
    cpu, cnt_cpu, _ = stacking.stack(paths, offsets, **args)
    compute.set_mode("gpu")
    monkeypatch.setattr(gstack, "GPU_MIN_VALUES", 0)
    monkeypatch.setattr(stacking, "STACK_BUDGET", 9 * 50 * 4 * 7)  # 7 rows per block: several blocks
    gpu, cnt_gpu, _ = stacking.stack(paths, offsets, **args)
    np.testing.assert_allclose(gpu, cpu, rtol=1e-6, equal_nan=True)
    np.testing.assert_array_equal(cnt_gpu, cnt_cpu)
    calls = []

    def broken(*a, **k):  # the driver fails on the second block: the rest is done on the CPU
        calls.append(1)
        if len(calls) == 2:
            compute.disable("test")
            return None
        return real(*a, **k)

    real = stacking.gpu_combine
    monkeypatch.setattr(stacking, "gpu_combine", broken)
    again, _, _ = stacking.stack(paths, offsets, **args)
    np.testing.assert_allclose(again, cpu, rtol=1e-6, equal_nan=True)


def test_gpu_nearest_centre_matches_numpy(gpu_mode):
    """k-means classes on the GPU: the nearest centre of every pixel, as the NumPy version gives it."""
    from astrowb.compute.classify import gpu_nearest
    from astrowb.remotesensing.analysis import _nearest

    rng = np.random.default_rng(5)
    centres = rng.normal(0, 3, (6, 8)).astype(np.float32)
    x = (centres[rng.integers(0, 6, 5000)] + rng.normal(0, 1, (5000, 8))).T.astype(np.float32)
    gpu = gpu_nearest(x, centres, force=True)
    compute.set_mode("cpu")
    np.testing.assert_array_equal(gpu, _nearest(x, centres))
