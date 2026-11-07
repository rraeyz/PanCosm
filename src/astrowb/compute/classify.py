"""GPU twin of remotesensing.analysis._nearest: the index of the nearest centre for every pixel (k-means classes).
gpu_nearest returns None whenever the GPU is not to be used, and the caller runs the NumPy version."""

import numpy as np

from . import device, disable, dispatch_size, max_binding_bytes, run

GPU_MIN_VALUES = 4_000_000  # pixels x bands; below this the transfer costs more than the CPU's work
MAX_CENTRES, MAX_BANDS = 64, 64

_SHADER = """
struct Params { npix: u32, nbands: u32, k: u32, row: u32 }
@group(0) @binding(0) var<storage, read> x: array<f32>;        // bands x pixels
@group(0) @binding(1) var<storage, read> centres: array<f32>;  // k x bands
@group(0) @binding(2) var<storage, read> p: Params;
@group(0) @binding(3) var<storage, read_write> outp: array<u32>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x + gid.y * p.row;
    if (i >= p.npix) { return; }
    var best = 0u;
    var best_d = 3.0e38;
    for (var c = 0u; c < p.k; c++) {
        var d = 0.0;
        for (var b = 0u; b < p.nbands; b++) {
            let e = x[b * p.npix + i] - centres[c * p.nbands + b];
            d += e * e;
        }
        if (d < best_d) { best_d = d; best = c; }
    }
    outp[i] = best;
}
"""


def gpu_nearest(x, centres, force=False):
    """x (bands, pixels), centres (k, bands): the nearest centre of every pixel, or None (the caller uses the CPU)."""
    nb, npix = x.shape
    k = len(centres)
    if k > MAX_CENTRES or nb > MAX_BANDS or (x.size < GPU_MIN_VALUES and not force) or device() is None:
        return None
    try:
        c = np.ascontiguousarray(centres, np.float32)
        out = np.empty(npix, np.int64)
        chunk = max(1, min(npix, max_binding_bytes() // (4 * nb)))
        for start in range(0, npix, chunk):
            part = np.ascontiguousarray(x[:, start : start + chunk], np.float32)
            m = part.shape[1]
            groups = dispatch_size(m)
            params = np.array([m, nb, k, groups[0] * 64], np.uint32)
            out[start : start + m] = np.frombuffer(run("nearest", _SHADER, [part, c, params], 4 * m, groups), np.uint32)
        return out
    except Exception as e:  # driver / memory problem: the CPU does it
        disable(f"{type(e).__name__}: {e}")
        return None
