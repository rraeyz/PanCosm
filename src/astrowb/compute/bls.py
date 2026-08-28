"""GPU twin of astropy's box least squares (BoxLeastSquares.power, method "fast", objective "likelihood"; its C loop
in astropy/timeseries/periodograms/bls/bls.c): one trial period per thread. Each thread bins the folded light curve
(bin = shortest duration / oversample), wraps the first `oversample` bins to the end as astropy does, takes running
sums and slides every duration over every phase, keeping the best log likelihood 0.5 ivar_in (y_out - y_in)^2 with
y_out >= y_in.

Phases as in compute.periods (PDM): the CPU gives each chunk of trial frequencies its phase in float64, the GPU adds
at most 32 cycles. Bin counts and duration steps come from the CPU in float64 (astropy's ceil / round). Float32
sums: the power agrees with astropy's to ~1e-4, and the best period is the same. gpu_bls_power returns None
whenever the GPU is not to be used (the caller uses astropy).
"""

import numpy as np

from . import device, disable, dispatch_size, max_binding_bytes

GPU_MIN_WORK = 20_000_000  # points x periods
CHUNK = 256  # periods sharing one float64 phase
MAX_CYCLES = 32.0
MAX_DURATIONS = 16

_SHADER = """
struct Params {
    n: u32, nper: u32, ndur: u32, chunk: u32, row: u32, block: u32, over: u32, bin: f32, sum_y: f32, sum_ivar: f32
}
@group(0) @binding(0) var<storage, read> base: array<f32>;   // frac(t f0) per chunk x point
@group(0) @binding(1) var<storage, read> t: array<f32>;
@group(0) @binding(2) var<storage, read> yw: array<f32>;     // y * ivar
@group(0) @binding(3) var<storage, read> ivar: array<f32>;
@group(0) @binding(4) var<storage, read> per: array<f32>;    // period, f - f0, bins (as f32 bits) per trial
@group(0) @binding(5) var<storage, read> durs: array<u32>;
@group(0) @binding(6) var<storage, read> p: Params;
@group(0) @binding(7) var<storage, read_write> scratch: array<f32>;  // 2 x block per trial
@group(0) @binding(8) var<storage, read_write> outp: array<f32>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let k = gid.x + gid.y * p.row;
    if (k >= p.nper) { return; }
    let period = per[3u * k];
    let df = per[3u * k + 1u];
    let n_bins = bitcast<u32>(per[3u * k + 2u]);
    if (n_bins == 0u) { outp[k] = bitcast<f32>(0xff800000u); return; }  // padding of a short chunk
    let c = k / p.chunk;
    let my = 2u * k * p.block;
    let mi = my + p.block;
    for (var b = 0u; b <= n_bins; b++) { scratch[my + b] = 0.0; scratch[mi + b] = 0.0; }
    for (var i = 0u; i < p.n; i++) {
        let x = fract(base[c * p.n + i] + t[i] * df) * period;
        let ind = min(u32(floor(x / p.bin)) + 1u, n_bins);
        scratch[my + ind] += yw[i];
        scratch[mi + ind] += ivar[i];
    }
    let over = p.over;  // astropy: n_bins = ceil(period / bin) + oversample
    var ind = n_bins - over;
    for (var b = 1u; b <= over; b++) {  // wrap: the first bins copied to the end (copied, as astropy does)
        scratch[my + ind] = scratch[my + b];
        scratch[mi + ind] = scratch[mi + b];
        ind++;
    }
    for (var b = 1u; b <= n_bins; b++) {
        scratch[my + b] += scratch[my + b - 1u];
        scratch[mi + b] += scratch[mi + b - 1u];
    }
    var best = bitcast<f32>(0xff800000u);  // -inf
    for (var d = 0u; d < p.ndur; d++) {
        let dur = durs[d];
        if (dur > n_bins) { continue; }
        for (var b = 0u; b <= n_bins - dur; b++) {
            var y_in = scratch[my + b + dur] - scratch[my + b];
            let ivar_in = scratch[mi + b + dur] - scratch[mi + b];
            var y_out = p.sum_y - y_in;
            let ivar_out = p.sum_ivar - ivar_in;
            if (ivar_in < 1e-12 || ivar_out < 1e-12) { continue; }
            y_in = y_in / ivar_in;
            y_out = y_out / ivar_out;
            let arg = y_out - y_in;
            let obj = 0.5 * ivar_in * arg * arg;
            if (y_out >= y_in && obj > best) { best = obj; }
        }
    }
    outp[k] = best;
}
"""


def gpu_bls_power(t, y, ivar, periods, durations, oversample=10, force=False):
    """BoxLeastSquares(t, y, dy).power(periods, durations).power on the GPU (t sorted or not; ivar = 1 / dy^2 or
    ones), or None (the caller uses astropy)."""
    t, y, ivar = np.asarray(t, float), np.asarray(y, float), np.asarray(ivar, float)
    periods, durations = np.asarray(periods, float), np.asarray(durations, float)
    n, nper = len(t), len(periods)
    if (n * nper < GPU_MIN_WORK and not force) or len(durations) > MAX_DURATIONS or n < 2 or device() is None:
        return None
    try:
        import wgpu

        tt = t - t.min()  # as astropy: times from the first, y about its median
        yy = y - np.median(y)
        bin_duration = durations.min() / oversample
        n_bins = (np.ceil(periods / bin_duration) + oversample).astype(np.int64)
        durs = np.round(durations / bin_duration).astype(np.uint32)  # C round: half away from zero (positive)
        block = int(n_bins.max()) + 1
        freqs = 1.0 / periods
        # chunks of trial frequencies whose phases differ from the chunk's first by at most MAX_CYCLES
        span = float(tt.max()) or 1.0
        starts, s = [], 0
        while s < nper:
            e = min(s + CHUNK, nper)
            while e - s > 1 and np.ptp(freqs[s:e]) * span > MAX_CYCLES:
                e = s + (e - s) // 2
            starts.append(s)
            s = e
        starts = np.array(starts)
        ends = np.r_[starts[1:], nper]
        slots = len(starts) * CHUNK
        slot = np.concatenate(
            [np.arange(a, b) - a + j * CHUNK for j, (a, b) in enumerate(zip(starts, ends, strict=True))]
        )
        per = np.zeros((slots, 3), np.float32)
        per[slot, 0] = periods
        per[slot, 1] = freqs - np.repeat(freqs[starts], ends - starts)
        per[:, 2] = 0.0
        per[slot, 2] = n_bins.astype(np.uint32).view(np.float32)
        base = np.mod(np.outer(freqs[starts], tt), 1.0).astype(np.float32)
        dev = device()
        limit = max_binding_bytes()
        if 4 * base.size > limit:
            return None
        per_group = min(slots, limit // (8 * block))  # scratch per dispatch within the binding limit, whole chunks
        per_group -= per_group % CHUNK
        if per_group < CHUNK:
            return None
        storage = wgpu.BufferUsage.STORAGE

        def buf(a):
            return dev.create_buffer_with_data(data=np.ascontiguousarray(a), usage=storage)

        b_t, b_yw, b_iv = buf(tt.astype(np.float32)), buf((yy * ivar).astype(np.float32)), buf(ivar.astype(np.float32))
        b_durs = buf(durs)
        module = dev.create_shader_module(code=_SHADER)
        pipeline = dev.create_compute_pipeline(layout="auto", compute={"module": module, "entry_point": "main"})
        out = np.empty(slots, np.float32)
        made = [b_t, b_yw, b_iv, b_durs]
        for g0 in range(0, slots, per_group):
            g1 = min(slots, g0 + per_group)
            c0, c1 = g0 // CHUNK, -(-g1 // CHUNK)
            b_base = buf(base[c0:c1])
            b_per = buf(per[g0:g1])
            groups = dispatch_size(g1 - g0)
            params = np.array([n, g1 - g0, len(durs), CHUNK, groups[0] * 64, block, oversample], np.uint32).tobytes()
            params += np.array([bin_duration, (yy * ivar).sum(), ivar.sum()], np.float32).tobytes()
            b_par = dev.create_buffer_with_data(data=params, usage=storage)
            scratch = dev.create_buffer(size=8 * block * (g1 - g0), usage=storage)
            result = dev.create_buffer(size=4 * (g1 - g0), usage=storage | wgpu.BufferUsage.COPY_SRC)
            bufs = [b_base, b_t, b_yw, b_iv, b_per, b_durs, b_par, scratch, result]
            entries = [
                {"binding": i, "resource": {"buffer": b, "offset": 0, "size": b.size}} for i, b in enumerate(bufs)
            ]
            group = dev.create_bind_group(layout=pipeline.get_bind_group_layout(0), entries=entries)
            enc = dev.create_command_encoder()
            cp = enc.begin_compute_pass()
            cp.set_pipeline(pipeline)
            cp.set_bind_group(0, group)
            cp.dispatch_workgroups(*groups)
            cp.end()
            dev.queue.submit([enc.finish()])
            out[g0:g1] = np.frombuffer(dev.queue.read_buffer(result), np.float32)
            for b in (b_base, b_per, b_par, scratch, result):
                b.destroy()
        for b in made:
            b.destroy()
        return out[slot].astype(float)
    except Exception as e:  # driver / memory problem: astropy does it
        disable(f"{type(e).__name__}: {e}")
        return None
