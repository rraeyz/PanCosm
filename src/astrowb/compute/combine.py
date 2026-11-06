"""Combine a stack of frames pixel by pixel with iterative, robust sigma clipping.

Algorithm (identical on CPU and GPU, equal to astropy ``sigma_clip(cenfunc="median",
stdfunc="mad_std")`` followed by a mean of the kept values): per pixel, start with all
finite values; repeat up to ``maxiters`` times: centre = median, scale = 1.4826 * MAD of
the kept values; reject values outside centre ± sigma·scale (rejections accumulate); stop
when nothing changes. Like astropy, the final selection is "all finite values inside the
last bounds", so a value rejected early can come back. Result: mean of the selected values
(NaN where none is left), plus their number per pixel.

Why robust: with mean/std clipping a single outlier among N frames can never lie further
than (N-1)/sqrt(N) sigma from the mean (2.3 sigma for N = 7), so a cosmic ray in one of a
few darks would never be rejected at 3 sigma.
"""

import warnings

import numpy as np

from . import device, disable, dispatch_size, max_binding_bytes, run

GPU_MIN_VALUES = 4_000_000  # below this the CPU is faster than the transfer to the GPU

MAX_GPU_FRAMES = 128  # per-thread sort buffer; larger stacks use the CPU
MAD_TO_STD = 1.482602218505602

_SHADER = """
struct Params { npix: u32, nframes: u32, maxiters: u32, row: u32, sigma: f32 }
@group(0) @binding(0) var<storage, read> stack: array<f32>;
@group(0) @binding(1) var<storage, read> p: Params;
@group(0) @binding(2) var<storage, read_write> outp: array<f32>;

fn sorted_median(a: ptr<function, array<f32, 128>>, m: u32) -> f32 {
    for (var i = 1u; i < m; i++) {          // insertion sort, m <= 128
        let v = (*a)[i];
        var j = i;
        while (j > 0u && (*a)[j - 1u] > v) { (*a)[j] = (*a)[j - 1u]; j--; }
        (*a)[j] = v;
    }
    if ((m & 1u) == 1u) { return (*a)[m / 2u]; }
    return 0.5 * ((*a)[m / 2u - 1u] + (*a)[m / 2u]);
}

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x + gid.y * p.row;
    if (i >= p.npix) { return; }
    var buf: array<f32, 128>;
    var lo = -3.0e38;
    var hi = 3.0e38;
    var last_lo = -3.0e38;  // bounds of the last iteration decide the final selection
    var last_hi = 3.0e38;
    var prev = 0xffffffffu;
    var cnt = 0u;
    for (var it = 0u; it <= p.maxiters; it++) {
        cnt = 0u;
        for (var f = 0u; f < p.nframes; f++) {
            let v = stack[f * p.npix + i];
            if (v >= lo && v <= hi) { buf[cnt] = v; cnt += 1u; }
        }
        if (cnt == 0u || cnt == prev || it == p.maxiters) { break; }
        prev = cnt;
        let med = sorted_median(&buf, cnt);
        for (var k = 0u; k < cnt; k++) { buf[k] = abs(buf[k] - med); }
        let scale = 1.482602218505602 * sorted_median(&buf, cnt);
        last_lo = med - p.sigma * scale;
        last_hi = med + p.sigma * scale;
        lo = max(lo, last_lo);
        hi = min(hi, last_hi);
    }
    var s = 0.0;
    cnt = 0u;
    for (var f = 0u; f < p.nframes; f++) {
        let v = stack[f * p.npix + i];
        if (v >= last_lo && v <= last_hi) { s += v; cnt += 1u; }
    }
    var mean = s / f32(cnt);
    if (cnt == 0u) { mean = bitcast<f32>(0x7fc00000u); }
    outp[i] = mean;
    outp[p.npix + i] = f32(cnt);
}
"""


def _median_sorted(xs, cnt):
    """Median of the first cnt values of each column of a column-sorted array (NaN where cnt == 0)."""
    c = np.maximum(cnt, 1)[None, :]
    lo = np.take_along_axis(xs, (c - 1) // 2, axis=0)[0]
    hi = np.take_along_axis(xs, c // 2, axis=0)[0]
    return np.where(cnt > 0, (lo + hi) * np.float32(0.5), np.nan).astype(np.float32)


def _cpu_block(x, sigma, maxiters):
    """x: (n, m) float32 block."""
    x = np.where(np.isfinite(x), x, np.nan).astype(np.float32)
    lo = np.full(x.shape[1], -np.inf, np.float32)
    hi = np.full(x.shape[1], np.inf, np.float32)
    last_lo, last_hi = lo, hi  # bounds of the last iteration decide the final selection
    prev = None
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pixels
        for it in range(maxiters + 1):
            kept = (x >= lo) & (x <= hi)
            cnt = np.count_nonzero(kept, axis=0)
            if it == maxiters or (prev is not None and np.array_equal(cnt, prev)):
                break
            prev = cnt
            xk = np.where(kept, x, np.nan)
            med = _median_sorted(np.sort(xk, axis=0), cnt)  # np.sort puts NaN last; faster than nanmedian
            scale = np.float32(MAD_TO_STD) * _median_sorted(np.sort(np.abs(xk - med), axis=0), cnt)
            last_lo, last_hi = med - np.float32(sigma) * scale, med + np.float32(sigma) * scale
            lo, hi = np.fmax(lo, last_lo), np.fmin(hi, last_hi)
        kept = (x >= last_lo) & (x <= last_hi)
        cnt = np.count_nonzero(kept, axis=0)
        mean = np.where(kept, x, 0).sum(0, dtype=np.float64) / cnt
    return mean.astype(np.float32), cnt.astype(np.int32)


def _cpu(stack, sigma, maxiters):
    """Cache-sized blocks on all cores (NumPy releases the GIL); the compiled twin when built (native.clipped_mean:
    the same steps pixel by pixel, equal to the last bit, 16 MP x 5 frames 4.5 s -> well under a second)."""
    from concurrent.futures import ThreadPoolExecutor

    from .. import native

    n = stack.shape[0]
    flat = stack.reshape(n, -1)
    npix = flat.shape[1]
    fast = native.use("clipped_mean")
    if fast:
        mean, cnt = np.empty(npix, np.float32), np.empty(npix, np.int32)
        step = max(1, 50_000_000 // n)  # about 200 MB of float32 at a time, whatever the number of frames
        for a in range(0, npix, step):
            mean[a : a + step], cnt[a : a + step] = fast(
                np.ascontiguousarray(flat[:, a : a + step], np.float32), np.float32(sigma), int(maxiters)
            )
        return mean, cnt
    block = max(1024, 2_000_000 // n)
    mean, cnt = np.empty(npix, np.float32), np.empty(npix, np.int32)

    def work(start):
        mean[start : start + block], cnt[start : start + block] = _cpu_block(
            np.asarray(flat[:, start : start + block], np.float32), sigma, maxiters
        )

    with ThreadPoolExecutor() as pool:
        list(pool.map(work, range(0, npix, block)))
    return mean, cnt


def _gpu(stack, sigma, maxiters):
    n = stack.shape[0]
    flat = stack.reshape(n, -1)
    npix = flat.shape[1]
    chunk = max(1, min(npix, max_binding_bytes() // (4 * n)))
    mean, cnt = np.empty(npix, np.float32), np.empty(npix, np.int32)
    for start in range(0, npix, chunk):
        part = np.ascontiguousarray(flat[:, start : start + chunk], dtype=np.float32)
        m = part.shape[1]
        groups = dispatch_size(m)
        params = np.array([m, n, maxiters, groups[0] * 64], np.uint32).tobytes() + np.float32(sigma).tobytes()
        out = np.frombuffer(run("clipped_mean", _SHADER, [part, params], 8 * m, groups), np.float32)
        mean[start : start + m], cnt[start : start + m] = out[:m], out[m:]
    return mean, cnt


def clipped_mean(stack: np.ndarray, sigma: float = 3.0, maxiters: int = 5, use_gpu: bool | None = None):
    """stack: (n_frames, ny, nx). Returns (combined float32 image, kept-count int32 image, 'cpu'|'gpu')."""
    stack = np.asarray(stack)
    shape = stack.shape[1:]
    if use_gpu is None:
        use_gpu = stack.size >= GPU_MIN_VALUES
    if use_gpu and stack.shape[0] <= MAX_GPU_FRAMES and device() is not None:
        try:
            mean, cnt = _gpu(stack, sigma, maxiters)
            return mean.reshape(shape), cnt.reshape(shape), "gpu"
        except Exception as e:  # driver/memory problem: fall back, never lose the result
            disable(f"{type(e).__name__}: {e}")
    mean, cnt = _cpu(stack, sigma, maxiters)
    return mean.reshape(shape), cnt.reshape(shape), "cpu"
