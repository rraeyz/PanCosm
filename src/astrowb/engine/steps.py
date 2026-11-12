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
    params: tuple = ()  # engine.params.P descriptions (AUT-1); empty for a step in the old form


REGISTRY: dict[str, Step] = {}


class MissingInput(Exception):
    def __init__(self, step_id, names):
        super().__init__(f"{step_id}: missing input(s): {', '.join(names)}")
        self.step_id, self.names = step_id, list(names)


def step(id, inputs=(), outputs=(), optional=(), params=(), **defaults):
    """Decorator that registers a step function. params: engine.params.P descriptions (their defaults join the
    keyword defaults); without them the keyword defaults are the whole description (the old form)."""

    def register(func):
        if id in REGISTRY:
            raise ValueError(f"duplicate step id {id}")
        merged = {**{p.name: p.default for p in params}, **defaults}
        REGISTRY[id] = Step(id, func, tuple(inputs), tuple(outputs), tuple(optional), merged, tuple(params))
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
    if s.params:  # described settings are checked before anything runs (AUT-1 item 3)
        from .params import check

        check(s.params, s.defaults | dict(params))
    started = time.time()
    from ..services import cache

    cache.last.clear()  # what is left after the step: the online answers it used (ARC-14 item 4)
    out = s.func(dict(inputs), s.defaults | dict(params), ctx)
    absent = [n for n in s.outputs if n not in out]
    if absent:
        raise RuntimeError(f"{step_id} did not produce: {', '.join(absent)}")
    _mark_products(step_id, inputs, s.defaults | dict(params), out, started)
    return out


def _mark_products(step_id, inputs, params, out, started):
    """Every FITS or ECSV file a step wrote (named in its outputs, written since it started) carries how it was made
    (ARC-11), unless its writer marked it already."""
    from pathlib import Path

    from ..core import provenance

    def paths(value):
        if isinstance(value, str | Path):
            yield value
        elif isinstance(value, list | tuple):
            for v in value:
                yield from paths(v)

    kinds = (".fits", ".fit", ".fts", ".ecsv")
    products = [Path(p) for v in out.values() for p in paths(v) if str(p).lower().endswith(kinds)]
    # never an input file (a step may list its input frames, e.g. the good ones), except a destination it was given
    given = {str(p) for k, v in inputs.items() if not k.startswith(("output", "destination")) for p in paths(v)}
    products = [p for p in products if str(p) not in given and p.is_file() and p.stat().st_mtime >= started - 2]
    if not products:
        return
    made = {str(p) for p in products}
    files = {k: [p for p in paths(v) if Path(p).is_file() and str(p) not in made] for k, v in inputs.items()}
    record = provenance.record(step_id, params, {k: v for k, v in files.items() if v})  # inputs that are files
    from ..services import cache

    if cache.last:  # the catalogues and archives asked, with the date of each answer: the methods text cites them
        record["services"] = {svc: provenance.when(t) for svc, (t, _) in sorted(cache.last.items())}
    for path in products:
        try:
            (_mark_ecsv if path.suffix.lower() == ".ecsv" else _mark_fits)(path, step_id, record)
        except (OSError, ValueError):
            continue  # a file the step did not write in that format after all: left as it is


def _mark_fits(path, step_id, record):
    from astropy.io import fits

    from ..core import provenance

    with fits.open(path, mode="update", output_verify="silentfix") as hdul:
        if hdul[0].header.get("PROCSTEP") != step_id:  # else its writer recorded it, with this file's own inputs
            provenance.to_fits(hdul[0].header, record)


def _mark_ecsv(path, step_id, record):
    from astropy.table import Table

    from ..core import provenance

    table = Table.read(path, format="ascii.ecsv")
    if (table.meta.get("provenance") or {}).get("step") != step_id:
        table.meta = provenance.to_ecsv(table.meta, record)
        table.write(path, format="ascii.ecsv", overwrite=True)


def _load_builtin():
    from . import builtin  # noqa: F401  (registers steps on import)
    from .plugins import load_plugins

    load_plugins()  # the user's own steps, in the GUI and in every worker process
