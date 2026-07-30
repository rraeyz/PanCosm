"""Step contract: inputs + params -> outputs, and every run is recorded in the project.

Any step can be the entry point: the caller provides its inputs directly. A step whose
required inputs are missing raises MissingInput naming them, so the UI can ask the user.
"""

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
    out = s.func(dict(inputs), s.defaults | dict(params), ctx)
    absent = [n for n in s.outputs if n not in out]
    if absent:
        raise RuntimeError(f"{step_id} did not produce: {', '.join(absent)}")
    return out


def _load_builtin():
    from . import builtin  # noqa: F401  (registers steps on import)
    from .plugins import load_plugins

    load_plugins()  # the user's own steps, in the GUI and in every worker process
