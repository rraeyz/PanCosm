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
