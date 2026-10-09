"""The compiled routines (native/, ARC-9), when they are there: every caller keeps a NumPy twin.

    fast = native.use("kepler_e")
    return fast(m, e) if fast else numpy_twin(m, e)

ASTROWB_NATIVE=off (or set_enabled(False), the setting compute.native) makes every caller use its twin.
"""

import os

ENV = "ASTROWB_NATIVE"

try:
    from . import _native
except ImportError:  # not built (a source checkout without Rust) or removed: the twins run
    _native = None


def available():
    return _native is not None


def version():
    return _native.version() if _native is not None else None


def enabled():
    return available() and os.environ.get(ENV, "auto").lower() != "off"


def set_enabled(on):
    """For this process and the workers it starts."""
    os.environ[ENV] = "auto" if on else "off"


def use(name):
    """The compiled function `name`, or None when the twin must run."""
    return getattr(_native, name, None) if enabled() else None


def describe():
    if not available():
        return "compiled routines: not available (slower)"
    return f"compiled routines: {version()}" + ("" if enabled() else " (switched off)")
