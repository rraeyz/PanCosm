"""Optional GPU acceleration through wgpu (Vulkan / Metal / DirectX 12 — no CUDA or ROCm needed).

Rules: every GPU operation has a NumPy twin giving the same result within float32 tolerance;
any GPU problem (no adapter, driver error, out of memory) falls back to the CPU and is
reported, never raised. Times and coordinates are never computed here: GPUs work in float32.

Mode: ASTROWB_COMPUTE = auto (default: real GPU if present) | cpu | gpu (also accepts a
software adapter, used by tests).
"""

import logging
import math
import os

import numpy as np

log = logging.getLogger(__name__)
MODE_ENV = "ASTROWB_COMPUTE"
MODES = ("auto", "cpu", "gpu")
WORKGROUP = 64
_state = {"device": None, "adapter": None, "tried": False, "error": None}
_pipelines = {}


def mode() -> str:
    m = os.environ.get(MODE_ENV, "auto").lower()
    return m if m in MODES else "auto"


def set_mode(m: str):
    """Set the mode for this process and the worker processes it starts."""
    if m not in MODES:
        raise ValueError(m)
    os.environ[MODE_ENV] = m
    _state.update(device=None, adapter=None, tried=False, error=None)
    _pipelines.clear()


def device():
    """The wgpu device to use, or None for CPU."""
    if mode() == "cpu":
        return None
    if not _state["tried"]:
        _state["tried"] = True
        try:
            adapter = _state["adapter"] or _adapter()
            limits = adapter.limits
            _state["device"] = adapter.request_device_sync(
                required_limits={
                    "max-storage-buffer-binding-size": limits["max-storage-buffer-binding-size"],
                    "max-buffer-size": limits["max-buffer-size"],
                }
            )
            _state["adapter"] = adapter
        except Exception as e:  # no driver, no Vulkan, broken install: CPU is always fine
            _state["error"] = f"{type(e).__name__}: {e}"
            log.info("GPU not used: %s", _state["error"])
    return _state["device"]


def _adapter():
    import wgpu

    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    if adapter is None:
        raise RuntimeError("no GPU adapter")
    if adapter.info["adapter_type"] == "CPU" and mode() != "gpu":
        raise RuntimeError(f"only a software adapter: {adapter.info['device']}")
    return adapter


def probe():
    """Look for a usable adapter ahead of time, without making a device (which holds driver memory): an idle worker
    does it before its task arrives, so a task does not wait the 0.4 s it takes."""
    if mode() == "cpu" or _state["tried"] or _state["adapter"] is not None:
        return
    try:
        _state["adapter"] = _adapter()
    except Exception as e:  # no GPU: decided now, device() returns None at once
        _state.update(tried=True, error=f"{type(e).__name__}: {e}")


def describe() -> str:
    """One line for the UI / benchmark: which device does the work."""
    if device() is None:
        return "CPU" + (f" (GPU: {_state['error']})" if _state["error"] else "")
    i = _state["adapter"].info
    return f"GPU: {i['device']} [{i['backend_type']}, {i['adapter_type']}]"


def disable(reason: str):
    """Stop using the GPU in this process after a failure."""
    _state.update(device=None, error=reason)
    log.warning("GPU disabled, using CPU: %s", reason)


def max_binding_bytes() -> int:
    return int(_state["device"].limits["max-storage-buffer-binding-size"])


def dispatch_size(n_items: int) -> tuple[int, int, int]:
    """Workgroup counts for n_items threads; >65535 groups are folded into y."""
    groups = max(1, math.ceil(n_items / WORKGROUP))
    gx = min(groups, 65535)
    return gx, math.ceil(groups / gx), 1


def run(name: str, shader: str, inputs: list, out_nbytes: int, groups) -> memoryview:
    """Run a compute shader: inputs bound at 0..k-1 (read-only), output at k (read_write)."""
    import wgpu

    dev = device()
    key = (id(dev), name)
    if key not in _pipelines:
        module = dev.create_shader_module(code=shader)
        _pipelines[key] = dev.create_compute_pipeline(layout="auto", compute={"module": module, "entry_point": "main"})
    pipeline = _pipelines[key]
    buffers = [
        dev.create_buffer_with_data(data=np.ascontiguousarray(a), usage=wgpu.BufferUsage.STORAGE) for a in inputs
    ]
    out = dev.create_buffer(size=out_nbytes, usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC)
    entries = [
        {"binding": i, "resource": {"buffer": b, "offset": 0, "size": b.size}} for i, b in enumerate(buffers + [out])
    ]
    bind_group = dev.create_bind_group(layout=pipeline.get_bind_group_layout(0), entries=entries)
    encoder = dev.create_command_encoder()
    cpass = encoder.begin_compute_pass()
    cpass.set_pipeline(pipeline)
    cpass.set_bind_group(0, bind_group)
    cpass.dispatch_workgroups(*groups)
    cpass.end()
    dev.queue.submit([encoder.finish()])
    result = dev.queue.read_buffer(out)
    for b in buffers + [out]:
        b.destroy()
    return result
