"""GPU twin of io.process.deconvolve: Richardson-Lucy iterations with a Gaussian PSF, every iteration on the GPU in
one submission (the image stays there; only the result comes back).

The blur is scipy.ndimage.gaussian_filter's: separable, weights exp(-x^2 / 2 sigma^2) normalised, radius
int(4 sigma + 0.5), zero outside the image (mode "constant"). The NumPy version (float64) stays the reference and the
fallback: gpu_richardson_lucy returns None whenever the GPU is not to be used, and the caller runs it.
"""

import numpy as np

from . import device, disable, max_binding_bytes, read_buffer

GPU_MIN_PIXELS = 1_000_000  # below this the CPU's 20 iterations take under a second
MAX_RADIUS = 256

_SHADER = """
struct Params { op: u32, w: u32, h: u32, radius: u32, row: u32 }
@group(0) @binding(0) var<storage, read> a: array<f32>;
@group(0) @binding(1) var<storage, read> b: array<f32>;
@group(0) @binding(2) var<storage, read> weights: array<f32>;
@group(0) @binding(3) var<storage, read> p: Params;
@group(0) @binding(4) var<storage, read_write> outp: array<f32>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x + gid.y * p.row;
    if (i >= p.w * p.h) { return; }
    let x = i32(i % p.w);
    let y = i32(i / p.w);
    let r = i32(p.radius);
    if (p.op == 0u) {  // blur along x, zero outside
        var s = 0.0;
        for (var k = -r; k <= r; k++) {
            let xx = x + k;
            if (xx >= 0 && xx < i32(p.w)) { s += weights[u32(k + r)] * a[u32(y) * p.w + u32(xx)]; }
        }
        outp[i] = s;
    } else if (p.op == 1u) {  // blur along y
        var s = 0.0;
        for (var k = -r; k <= r; k++) {
            let yy = y + k;
            if (yy >= 0 && yy < i32(p.h)) { s += weights[u32(k + r)] * a[u32(yy) * p.w + u32(x)]; }
        }
        outp[i] = s;
    } else if (p.op == 2u) {  // the data over the blurred estimate
        outp[i] = b[i] / max(a[i], 1e-12);
    } else {  // the estimate times the blurred ratio
        outp[i] = b[i] * a[i];
    }
}
"""


def _weights(sigma):
    """scipy.ndimage's Gaussian kernel for truncate = 4."""
    radius = int(4.0 * sigma + 0.5)
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    w = np.exp(-0.5 * (x / sigma) ** 2)
    return (w / w.sum()).astype(np.float32), radius


def gpu_richardson_lucy(d, sigma, iterations, force=False):
    """d: the positive image (float64, shifted by the caller), its Gaussian PSF sigma (pixels): the estimate after
    `iterations` Richardson-Lucy steps from a flat start, or None (the caller uses the CPU)."""
    import wgpu

    h, w = d.shape
    weights, radius = _weights(sigma)
    if (d.size < GPU_MIN_PIXELS and not force) or radius > MAX_RADIUS or device() is None:
        return None
    if 4 * d.size > max_binding_bytes():
        return None
    try:
        dev = device()
        storage = wgpu.BufferUsage.STORAGE
        nbytes = 4 * d.size
        data = dev.create_buffer_with_data(data=np.ascontiguousarray(d, np.float32), usage=storage)
        start = np.full(d.size, d.mean(), np.float32)
        u = [dev.create_buffer_with_data(data=start, usage=storage | wgpu.BufferUsage.COPY_SRC),
             dev.create_buffer(size=nbytes, usage=storage | wgpu.BufferUsage.COPY_SRC)]  # fmt: skip
        t1, t2 = (dev.create_buffer(size=nbytes, usage=storage) for _ in range(2))
        wbuf = dev.create_buffer_with_data(data=weights, usage=storage)
        groups = max(1, -(-d.size // 64))
        gx = min(groups, 65535)
        gy = -(-groups // gx)
        params = [
            dev.create_buffer_with_data(data=np.array([op, w, h, radius, gx * 64], np.uint32), usage=storage)
            for op in range(4)
        ]
        module = dev.create_shader_module(code=_SHADER)
        pipeline = dev.create_compute_pipeline(layout="auto", compute={"module": module, "entry_point": "main"})
        layout = pipeline.get_bind_group_layout(0)

        def group(op, a, b, out):
            bufs = enumerate([a, b, wbuf, params[op], out])
            entries = [{"binding": k, "resource": {"buffer": x, "offset": 0, "size": x.size}} for k, x in bufs]
            return dev.create_bind_group(layout=layout, entries=entries)

        # one iteration from u[c] to u[1 - c]: blur(u) -> t2, d / blur(u) -> t1, blur(t1) -> t1, u * t1 -> u[1 - c]
        steps = [
            [
                group(0, u[c], data, t1),
                group(1, t1, data, t2),
                group(2, t2, data, t1),
                group(0, t1, data, t2),
                group(1, t2, data, t1),
                group(3, t1, u[c], u[1 - c]),
            ]  # fmt: skip
            for c in (0, 1)
        ]
        encoder = dev.create_command_encoder()
        for it in range(int(iterations)):
            for bg in steps[it % 2]:
                cpass = encoder.begin_compute_pass()
                cpass.set_pipeline(pipeline)
                cpass.set_bind_group(0, bg)
                cpass.dispatch_workgroups(gx, gy, 1)
                cpass.end()
        dev.queue.submit([encoder.finish()])
        result = np.frombuffer(read_buffer(dev, u[int(iterations) % 2]), np.float32).reshape(h, w).copy()
        for b in [data, *u, t1, t2, wbuf, *params]:
            b.destroy()
        return result
    except Exception as e:  # driver / memory problem: the CPU does it
        disable(f"{type(e).__name__}: {e}")
        return None
