"""Step contract: inputs + params -> outputs, and every run is recorded in the project.

Any step can be the entry point: the caller provides its inputs directly. A step whose
required inputs are missing raises MissingInput naming them, so the UI can ask the user.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    id: str  # stable identifier stored in project files; never rename
    func: Callable  # func(inputs: dict, params: dict, ctx) -> dict
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    optional: tuple[str, ...] = ()
    defaults: dict = field(default_factory=dict)


REGISTRY: dict[str, Step] = {}


class MissingInput(Exception):
    def __init__(self, step_id, names):
        super().__init__(f"{step_id}: missing input(s): {', '.join(names)}")
        self.step_id, self.names = step_id, list(names)


def step(id, inputs=(), outputs=(), optional=(), **defaults):
    """Decorator that registers a step function."""

    def register(func):
        if id in REGISTRY:
            raise ValueError(f"duplicate step id {id}")
        REGISTRY[id] = Step(id, func, tuple(inputs), tuple(outputs), tuple(optional), defaults)
        return func

    return register


def get(step_id) -> Step:
    _load_builtin()
    return REGISTRY[step_id]


def check_chain(step_ids, available) -> None:
    """Raise MissingInput for the first step whose inputs the chain cannot supply."""
    have = set(available)
    for sid in step_ids:
        s = get(sid)
        missing = [n for n in s.inputs if n not in have]
        if missing:
            raise MissingInput(sid, missing)
        have.update(s.outputs)


def execute(step_id, inputs, params, ctx):
    """Run one step (inside a worker process). Returns its outputs dict."""
    s = get(step_id)
    missing = [n for n in s.inputs if n not in inputs]
    if missing:
        raise MissingInput(step_id, missing)
    started = time.time()
    out = s.func(dict(inputs), s.defaults | dict(params), ctx)
    absent = [n for n in s.outputs if n not in out]
    if absent:
        raise RuntimeError(f"{step_id} did not produce: {', '.join(absent)}")
    _mark_products(step_id, inputs, s.defaults | dict(params), out, started)
    return out


def _mark_products(step_id, inputs, params, out, started):
    """Every FITS file a step wrote (named in its outputs, written since it started) carries how it was made
    (ARC-11), unless its writer marked it already."""
    from pathlib import Path

    from ..core import provenance

    def paths(value):
        if isinstance(value, str | Path):
            yield value
        elif isinstance(value, list | tuple):
            for v in value:
                yield from paths(v)

    products = [Path(p) for v in out.values() for p in paths(v) if str(p).lower().endswith((".fits", ".fit", ".fts"))]
    # never an input file (a step may list its input frames, e.g. the good ones), except a destination it was given
    given = {str(p) for k, v in inputs.items() if not k.startswith(("output", "destination")) for p in paths(v)}
    products = [p for p in products if str(p) not in given and p.is_file() and p.stat().st_mtime >= started - 2]
    if not products:
        return
    from astropy.io import fits

    record = None
    for path in products:
        try:
            with fits.open(path, mode="update", output_verify="silentfix") as hdul:
                if hdul[0].header.get("PROCSTEP") == step_id:
                    continue  # its writer recorded it, with the inputs of this one file
                if record is None:  # the inputs that are files (not text, numbers or folders)
                    made = {str(p) for p in products}
                    given = {
                        k: [p for p in paths(v) if Path(p).is_file() and str(p) not in made] for k, v in inputs.items()
                    }
                    record = provenance.record(step_id, params, {k: v for k, v in given.items() if v})
                provenance.to_fits(hdul[0].header, record)
        except OSError:
            continue  # a file the step did not write as FITS after all: left as it is


def _load_builtin():
    from . import builtin  # noqa: F401  (registers steps on import)
    from .plugins import load_plugins

    load_plugins()  # the user's own steps, in the GUI and in every worker process
