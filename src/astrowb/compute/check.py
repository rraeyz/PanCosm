"""GPU check (--benchmark, tools/gpu_check.py): is there a GPU, does every GPU job give the CPU's result, and how long
does each take on both. Synthetic data of a real size; nothing is read or written except the report."""

import time

import numpy as np

from . import _adapter, _state, describe, device, set_mode


def _timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t


def _jobs(rng):
    """(name, CPU function, GPU function, how to compare) for every GPU job."""
    from astropy.timeseries import BoxLeastSquares

    from ..calibration.stacking import combine
    from ..remotesensing.analysis import _nearest
    from ..timeseries.period import _pdm_power
    from .bls import gpu_bls_power
    from .classify import gpu_nearest
    from .combine import clipped_mean
    from .deconvolve import gpu_richardson_lucy
    from .periods import gpu_pdm_power
    from .stack import gpu_combine

    frames = rng.normal(1000, 10, (20, 1024, 2048)).astype(np.float32)
    frames[rng.integers(0, 20, 20000), rng.integers(0, 1024, 20000), rng.integers(0, 2048, 20000)] = 60000
    centres = rng.normal(0, 3, (6, 10)).astype(np.float32)
    pixels = (centres[rng.integers(0, 6, 4_000_000)] + rng.normal(0, 1, (4_000_000, 10))).T.astype(np.float32)
    yy, xx = np.mgrid[:2048, :2048]
    sky = np.full((2048, 2048), 100.0)
    for x, y in rng.uniform(20, 2028, (400, 2)):
        sky += 5000 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.0**2))
    image = rng.poisson(sky).astype(float)
    t = np.sort(rng.uniform(0, 1460, 65_000))
    lc = 1 - 0.3 * (np.abs((t / 3.42 + 0.25) % 1 - 0.25) < 0.02) + rng.normal(0, 3e-4, len(t))
    freqs = np.linspace(0.05, 2.0, 5000)
    bls_periods, durs = 1 / np.linspace(1 / 20, 2.0, 2000), (0.04, 0.06, 0.08, 0.12, 0.16)

    def rl_cpu():
        from scipy.ndimage import gaussian_filter

        u = np.full_like(image, image.mean())
        for _ in range(20):
            u *= gaussian_filter(image / np.maximum(gaussian_filter(u, 2.0, mode="constant", truncate=4.0), 1e-12),
                                 2.0, mode="constant", truncate=4.0)  # fmt: skip
        return u

    peak = {}

    def bls_cpu():  # the power as a fraction of the CPU's peak: a point on a bin edge (float32 phases) moves a low
        # value by up to half a point's chi^2: a large change of a low value, not of the periodogram
        p = np.asarray(BoxLeastSquares(t, lc).power(bls_periods, durs).power)
        peak["bls"] = p.max()
        return p / peak["bls"]

    def bls_gpu():
        p = gpu_bls_power(t, lc, np.ones(len(t)), bls_periods, durs, force=True)
        return None if p is None else p / peak["bls"]

    return [
        ("stacking, sigma-clipped mean (20 x 1024 x 2048)",
         lambda: clipped_mean(frames, use_gpu=False)[0], lambda: _gpu_or_fail(clipped_mean(frames, use_gpu=True))),
        ("stacking, median + winsorized (20 x 1024 x 2048)",
         lambda: combine(frames, "median", "winsorized"),
         lambda: gpu_combine(frames, "median", "winsorized", force=True)),
        ("k-means classes (4 000 000 pixels x 10 bands)",
         lambda: _nearest(pixels, centres), lambda: gpu_nearest(pixels, centres, force=True)),
        ("deconvolution (2048 x 2048, 20 iterations)", rl_cpu, lambda: gpu_richardson_lucy(image, 2.0, 20, force=True)),
        ("period search, BLS (65 000 points x 2 000 periods)", bls_cpu, bls_gpu),
        ("period search, PDM (65 000 points x 5 000 frequencies)",
         lambda: _pdm_power(t, lc, 1 / freqs, 20), lambda: gpu_pdm_power(t, lc, freqs, 20, force=True)),
    ]  # fmt: skip


def _gpu_or_fail(result):
    img, _, used = result
    return img if used == "gpu" else None


def benchmark() -> list[str]:
    """The report, one line per finding."""
    return list(report())


def report(found=None):
    """The report line by line, each as soon as it is known (the jobs take about a minute). found: a dict that
    receives the same as data (adapter, jobs with times and verdicts) for gpu-report.json."""
    found = {} if found is None else found
    set_mode("gpu")  # a software adapter is found too, and reported as one
    try:
        adapter = _adapter()
    except Exception as e:  # noqa: BLE001 - every reason a GPU cannot be used is reported, not raised
        set_mode("auto")
        yield f"GPU not found ({type(e).__name__}: {e})."
        yield "Every job runs on the CPU; nothing else to test."
        return
    info = adapter.info
    found["adapter"] = {k: str(v) for k, v in dict(info).items()}
    found["jobs"] = []
    software = info["adapter_type"] == "CPU"
    yield (f"GPU found: {info['device']} [{info['backend_type']}, {info['adapter_type']}]")
    if software:
        yield ("  (a software adapter, which runs on the CPU: results are checked, times say nothing")
        yield ("   about a GPU; 'Automatic' does not use it)")
    if device() is None:
        set_mode("auto")
        yield f"GPU does not work: {_state['error']}"
        return
    yield (f"GPU works: {describe()}")
    rng = np.random.default_rng(0)
    worked = 0
    jobs = _jobs(rng)
    for name, cpu, gpu in jobs:
        set_mode("cpu")
        ref, t_cpu = _timed(cpu)
        set_mode("gpu")
        device()  # the GPU started before the clock does (0.4 s)
        out, t_gpu = _timed(gpu)
        if out is None:
            found["jobs"].append({"job": name, "cpu_s": t_cpu, "gpu_s": None, "same": False})
            yield (f"  {name}: GPU FAILED ({describe()}), CPU {t_cpu:.2f} s")
            continue
        ref, out = np.asarray(ref), np.asarray(out)
        if np.issubdtype(ref.dtype, np.integer):  # classes: a near-tie may go either way
            n_diff = int(np.count_nonzero(ref != out))
            same = n_diff <= 1e-5 * ref.size
            verdict = f"same result ({n_diff} of {ref.size} differ)" if same else f"DIFFERENT RESULT ({n_diff} differ)"
        else:
            ref, out = ref.astype(float), out.astype(float)
            diff = float(np.nanmax(np.abs(out - ref) / np.maximum(np.abs(ref), 1.0)))
            same = np.array_equal(np.isnan(ref), np.isnan(out)) and diff < 1e-3
            verdict = f"same result (largest difference {diff:.1e})" if same else f"DIFFERENT RESULT ({diff:.1e})"
        worked += same
        found["jobs"].append({"job": name, "cpu_s": t_cpu, "gpu_s": t_gpu, "same": bool(same), "verdict": verdict})
        yield (f"  {name}: CPU {t_cpu:.2f} s, GPU {t_gpu:.2f} s ({t_cpu / t_gpu:.1f}x), {verdict}")
    yield (f"{worked} of {len(jobs)} GPU jobs work.")
    if not software:
        yield (
            "'Automatic' uses the GPU for these jobs when they are large enough, except the sigma-clipped mean,"
            " which the compiled routines do faster on the CPU."
        )
    set_mode("auto")
