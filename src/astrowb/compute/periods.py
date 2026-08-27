"""GPU twin of timeseries.period._pdm_power: phase dispersion minimisation, one trial frequency per thread.

Phases need more than float32 (t x f is thousands of cycles over years of data): the CPU gives each chunk of
frequencies its phase in float64, frac(t f0), and the GPU adds only t (f - f0), at most 32 cycles: the phase is good to
~1e-6 cycles. Bins use Welford's running mean and variance (float32 sums of y^2 lose the scatter in the mean). The
NumPy version stays the reference and the fallback: gpu_pdm_power returns None whenever the GPU is not to be used.
"""

import numpy as np

from . import device, disable, dispatch_size, max_binding_bytes, run

GPU_MIN_WORK = 4_000_000  # points x frequencies
MAX_BINS = 64
CHUNK = 256  # frequencies sharing one float64 phase
MAX_CYCLES = 32.0  # t (f - f0) within a chunk

_SHADER = """
struct Params { n: u32, nfreq: u32, nbins: u32, chunk: u32, row: u32, total: f32 }
@group(0) @binding(0) var<storage, read> base: array<f32>;   // frac(t f0) per chunk x point
@group(0) @binding(1) var<storage, read> t: array<f32>;
@group(0) @binding(2) var<storage, read> y: array<f32>;
@group(0) @binding(3) var<storage, read> df: array<f32>;     // f - f0 per frequency
@group(0) @binding(4) var<storage, read> p: Params;
@group(0) @binding(5) var<storage, read_write> outp: array<f32>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let k = gid.x + gid.y * p.row;
    if (k >= p.nfreq) { return; }
    let c = k / p.chunk;
    var cnt: array<f32, 64>;
    var mean: array<f32, 64>;
    var m2: array<f32, 64>;
    for (var b = 0u; b < p.nbins; b++) { cnt[b] = 0.0; mean[b] = 0.0; m2[b] = 0.0; }
    for (var i = 0u; i < p.n; i++) {
        let ph = fract(base[c * p.n + i] + t[i] * df[k]);
        let b = min(u32(ph * f32(p.nbins)), p.nbins - 1u);
        cnt[b] += 1.0;
        let d = y[i] - mean[b];
        mean[b] += d / cnt[b];
        m2[b] += d * (y[i] - mean[b]);
    }
    var within = 0.0;
    var dof = 0.0;
    for (var b = 0u; b < p.nbins; b++) {
        if (cnt[b] > 1.0) { within += m2[b]; dof += cnt[b] - 1.0; }
    }
    outp[k] = 1.0 - (within / dof) / p.total;
}
"""


def gpu_pdm_power(t, y, freqs, n_bins, force=False):
    """PDM power (1 - theta) of y(t) at the frequencies, or None (the caller uses the CPU)."""
    t, y, freqs = np.asarray(t, float), np.asarray(y, float), np.asarray(freqs, float)
    n, nf = len(t), len(freqs)
    if n_bins > MAX_BINS or (n * nf < GPU_MIN_WORK and not force) or n < 2 or device() is None:
        return None
    try:
        span = float(np.max(np.abs(t))) or 1.0
        # chunks of at most CHUNK frequencies whose phases differ from the chunk's first by at most MAX_CYCLES
        starts, s = [], 0
        while s < nf:
            e = min(s + CHUNK, nf)
            while e - s > 1 and np.ptp(freqs[s:e]) * span > MAX_CYCLES:
                e = s + (e - s) // 2
            starts.append(s)
            s = e
        starts = np.array(starts)
        ends = np.r_[starts[1:], nf]
        # the kernel finds a frequency's chunk as k / CHUNK: lay the chunks out CHUNK apart, padding the short ones
        pairs = enumerate(zip(starts, ends, strict=True))
        slot = np.concatenate([np.arange(a, b) - a + j * CHUNK for j, (a, b) in pairs])
        df = np.zeros(len(starts) * CHUNK, np.float32)
        df[slot] = freqs - np.repeat(freqs[starts], ends - starts)
        base = np.mod(np.outer(freqs[starts], t), 1.0).astype(np.float32)  # float64 phases, then float32
        if 4 * base.size > max_binding_bytes():
            return None
        yc = (y - y.mean()).astype(np.float32)
        total = float(np.var(y, ddof=1))
        groups = dispatch_size(len(df))
        params = np.array([n, len(df), n_bins, CHUNK, groups[0] * 64], np.uint32).tobytes()
        params += np.float32(total).tobytes()
        out = run("pdm", _SHADER, [base, t.astype(np.float32), yc, df, params], 4 * len(df), groups)
        return np.frombuffer(out, np.float32)[slot].astype(float)
    except Exception as e:  # driver / memory problem: the CPU does it
        disable(f"{type(e).__name__}: {e}")
        return None
