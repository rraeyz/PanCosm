"""GPU twin of calibration.stacking.combine: one value per pixel from the frames' values, with the same rejections
(none, sigma, winsorized, minmax, percentile) and methods (mean, median, sum), weights included.

The NumPy version stays the reference and the fallback: gpu_combine returns None whenever the GPU is not to be used
(mode "cpu", no adapter, a small block, more than 128 frames, a driver error), and the caller then runs the NumPy
version. Float32 on both; a value can differ in its last bits, and a pixel whose value lies exactly on a rejection
bound can be kept on one and rejected on the other.
"""

import numpy as np

from . import device, disable, dispatch_size, max_binding_bytes, run

GPU_MIN_VALUES = 4_000_000  # below this the transfer costs more than the CPU's work
MAX_FRAMES = 128  # per-thread buffers
METHODS = {"mean": 0, "median": 1, "sum": 2}
REJECTIONS = {"none": 0, "sigma": 1, "winsorized": 2, "minmax": 3, "percentile": 4}

_SHADER = """
struct Params { npix: u32, nframes: u32, method: u32, rejection: u32, row: u32, sigma: f32, low: f32, high: f32 }
@group(0) @binding(0) var<storage, read> stack: array<f32>;
@group(0) @binding(1) var<storage, read> weights: array<f32>;
@group(0) @binding(2) var<storage, read> p: Params;
@group(0) @binding(3) var<storage, read_write> outp: array<f32>;

fn finite(v: f32) -> bool { return (bitcast<u32>(v) & 0x7f800000u) != 0x7f800000u; }

fn median(a: ptr<function, array<f32, 128>>, m: u32) -> f32 {
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
    let n = p.nframes;
    var v: array<f32, 128>;
    var keep: array<bool, 128>;
    var buf: array<f32, 128>;
    var m = 0u;
    for (var f = 0u; f < n; f++) {
        v[f] = stack[f * p.npix + i];
        keep[f] = finite(v[f]);
    }
    if (p.rejection == 3u) {  // minmax: the low lowest and high highest kept values out (ties in frame order)
        var nk = 0u;
        for (var f = 0u; f < n; f++) { if (keep[f]) { nk++; } }
        var rank: array<u32, 128>;
        for (var f = 0u; f < n; f++) {
            var r = 0u;
            for (var g = 0u; g < n; g++) {
                if (keep[g] && (v[g] < v[f] || (v[g] == v[f] && g < f))) { r++; }
            }
            rank[f] = r;
        }
        for (var f = 0u; f < n; f++) {
            keep[f] = keep[f] && f32(rank[f]) >= p.low && f32(rank[f]) < f32(nk) - p.high;
        }
    } else if (p.rejection == 4u) {  // percentile: within (1 - low, 1 + high) x the median
        m = 0u;
        for (var f = 0u; f < n; f++) { if (keep[f]) { buf[m] = v[f]; m++; } }
        if (m > 0u) {
            let med = median(&buf, m);
            for (var f = 0u; f < n; f++) {
                keep[f] = keep[f] && v[f] >= med * (1.0 - p.low) && v[f] <= med * (1.0 + p.high);
            }
        }
    } else if (p.rejection == 1u || p.rejection == 2u) {  // sigma / winsorized sigma clipping, 5 iterations
        for (var it = 0u; it < 5u; it++) {
            m = 0u;
            for (var f = 0u; f < n; f++) { if (keep[f]) { buf[m] = v[f]; m++; } }
            if (m == 0u) { break; }
            let med = median(&buf, m);
            m = 0u;
            for (var f = 0u; f < n; f++) { if (keep[f]) { buf[m] = abs(v[f] - med); m++; } }
            var spread = 1.4826 * median(&buf, m);
            if (p.rejection == 2u) {  // Huber: values beyond 1.5 sigma pulled in, spread measured again
                for (var w = 0u; w < 5u; w++) {
                    var s = 0.0;
                    for (var f = 0u; f < n; f++) {
                        if (keep[f]) { s += clamp(v[f], med - 1.5 * spread, med + 1.5 * spread); }
                    }
                    let mean = s / f32(m);
                    var ss = 0.0;
                    for (var f = 0u; f < n; f++) {
                        if (keep[f]) {
                            let d = clamp(v[f], med - 1.5 * spread, med + 1.5 * spread) - mean;
                            ss += d * d;
                        }
                    }
                    spread = 1.134 * sqrt(ss / f32(m));
                }
            }
            var changed = false;
            let bound = p.sigma * max(spread, 1e-12);
            for (var f = 0u; f < n; f++) {
                if (keep[f] && abs(v[f] - med) > bound) { keep[f] = false; changed = true; }
            }
            if (!changed) { break; }
        }
    }
    var result = bitcast<f32>(0x7fc00000u);  // NaN: nothing kept
    if (p.method == 1u) {
        m = 0u;
        for (var f = 0u; f < n; f++) { if (keep[f]) { buf[m] = v[f]; m++; } }
        if (m > 0u) { result = median(&buf, m); }
    } else {
        var s = 0.0;
        var ws = 0.0;
        for (var f = 0u; f < n; f++) { if (keep[f]) { s += weights[f] * v[f]; ws += weights[f]; } }
        if (ws > 0.0) {
            result = s / ws;
            if (p.method == 2u) { result = result * f32(n); }
        }
    }
    outp[i] = result;
}
"""


def gpu_combine(block, method="mean", rejection="sigma", sigma=3.0, low=1, high=1, weights=None, force=False):
    """block (frames, rows, columns) float32 combined on the GPU, or None when the GPU is not to be used (the caller
    runs the NumPy version). force: also for a small block (tests)."""
    n = block.shape[0]
    if n > MAX_FRAMES or (block.size < GPU_MIN_VALUES and not force) or device() is None:
        return None
    try:
        flat = block.reshape(n, -1)
        npix = flat.shape[1]
        w = np.ones(n, np.float32) if weights is None else np.asarray(weights, np.float32)
        out = np.empty(npix, np.float32)
        chunk = max(1, min(npix, max_binding_bytes() // (4 * n)))
        for start in range(0, npix, chunk):
            part = np.ascontiguousarray(flat[:, start : start + chunk], dtype=np.float32)
            m = part.shape[1]
            groups = dispatch_size(m)
            params = np.array([m, n, METHODS[method], REJECTIONS[rejection], groups[0] * 64], np.uint32).tobytes()
            params += np.array([sigma, low, high], np.float32).tobytes()
            res = run("stack_combine", _SHADER, [part, w, params], 4 * m, groups)
            out[start : start + m] = np.frombuffer(res, np.float32)
        return out.reshape(block.shape[1:])
    except Exception as e:  # driver / memory problem: the CPU does it, the result is never lost
        disable(f"{type(e).__name__}: {e}")
        return None
