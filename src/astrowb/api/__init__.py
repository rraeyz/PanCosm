"""Python scripting: every step of the program as a function (plans/architecture.md ARC-12 item 1).

    from astrowb import api
    out = api.photometry.light_curve(images=[...], target_xy=[512, 300], comps_xy=[[400, 280]])
    api.run("timeseries.period", time=t, flux=f, method="bls")
    api.steps()                                   # every step id
    help(api.models.visual_orbit)                 # its inputs, parameters and defaults

Keywords that are inputs of the step are inputs, the others must be its parameters (TypeError otherwise, as for a
Python function). Steps run in this process, as `astrowb-cli run` does; the outputs are returned as a dict.
"""

from ..cli import UsageError, _split


class _Ctx:
    def progress(self, *a, **k):
        pass

    def check(self):
        pass


def steps():
    from ..engine import steps as registry

    registry._load_builtin()
    return sorted(registry.REGISTRY)


def run(step_id, **values):
    """Run one step with its inputs and parameters given as keywords; returns its outputs."""
    from ..engine.steps import execute

    try:
        inputs, params = _split(step_id, values)
    except UsageError as e:
        raise TypeError(str(e)) from None
    return execute(step_id, inputs, params, _Ctx())


def _function(step_id):
    from ..engine import steps as registry

    s = registry.get(step_id)

    def call(**values):
        return run(step_id, **values)

    params = ", ".join(f"{k}={v!r}" for k, v in s.defaults.items())
    call.__name__ = step_id.split(".")[-1]
    call.__qualname__ = step_id
    call.__doc__ = (
        f"{(s.func.__doc__ or '').strip()}\n\ninputs: {', '.join(s.inputs) or 'none'}"
        + (f" (optional: {', '.join(s.optional)})" if s.optional else "")
        + f"\nparameters: {params or 'none'}\noutputs: {', '.join(s.outputs) or 'none'}"
    )
    return call


class _Area:
    def __init__(self, name):
        self._name = name

    def __getattr__(self, name):
        step_id = f"{self._name}.{name}"
        if step_id not in steps():
            raise AttributeError(f"no step {step_id} (astrowb.api.steps() lists them)")
        return _function(step_id)

    def __dir__(self):
        return [s.split(".", 1)[1] for s in steps() if s.startswith(self._name + ".")]


def __getattr__(name):
    if name.startswith("_") or not any(s.startswith(name + ".") for s in steps()):
        raise AttributeError(name)
    return _Area(name)
