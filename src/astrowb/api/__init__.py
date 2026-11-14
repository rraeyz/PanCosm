"""Python scripting: every step of the program as a function (plans/architecture.md ARC-12 item 1).

    from astrowb import api
    out = api.photometry.light_curve(images=[...], target_xy=[512, 300], comps_xy=[[400, 280]])
    api.run("timeseries.period", time=t, flux=f, method="bls")
    api.run(...).to_table()                       # the result's columns as an astropy Table
    api.steps()                                   # every step id
    help(api.models.visual_orbit)                 # its inputs, parameters and defaults
    lights = api.calibrate_night("raw/", "cal/")  # the hand-written helpers chain several steps

Keywords that are inputs of the step are inputs, the others must be its parameters (TypeError otherwise, as for a
Python function). Steps run in this process, as `astrowb-cli run` does; the outputs are returned as a dict.
"""

from ..cli import UsageError, _split


class _Ctx:
    def progress(self, *a, **k):
        pass

    def check(self):
        pass


class Result(dict):
    """A step's outputs (a dict) that can also give its columns as an astropy Table."""

    def to_table(self, key=None):
        """The columns of output `key` (a dict of columns or a list of rows) as a Table; without a key, the
        outputs that are columns of one length (e.g. periods and power), else the first output that is a table."""
        from astropy.table import Table

        def columns(d):
            cols = {k: v for k, v in d.items() if _is_column(v)}
            if not cols:
                return None
            n = max({len(v) for v in cols.values()}, key=[len(v) for v in cols.values()].count)
            return Table({k: v for k, v in cols.items() if len(v) == n})

        def as_table(v):
            if isinstance(v, dict):
                return columns(v)
            if isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
                return Table(rows=v)
            return None

        if key is not None:
            t = as_table(self[key])
            if t is None:
                raise TypeError(f"output {key!r} is not a table")
            return t
        t = columns(self)
        if t is not None and len(t.colnames) > 1:
            return t
        for v in self.values():
            t = as_table(v)
            if t is not None:
                return t
        raise TypeError(f"no output is a table (outputs: {', '.join(self)})")


def _is_column(v):
    import numpy as np

    if isinstance(v, (str, bytes, dict)) or not hasattr(v, "__len__") or len(v) < 2:
        return False
    a = np.asarray(v, dtype=object)
    return a.ndim == 1 and not any(isinstance(x, (dict, list)) for x in a)


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
    return Result(execute(step_id, inputs, params, _Ctx()))


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


def calibrate_night(folder, output_dir, **params):
    """A night's folder of raw frames (bias, darks, flats, lights in any order) calibrated into output_dir, the way
    the Calibration window does it: the frames sorted by their headers, masters made, the lights calibrated.
    Returns the paths of the calibrated lights. Keywords are calibration.run's parameters."""
    frames = run("calibration.scan", folder=str(folder))["frames"]
    out = run("calibration.run", frames=frames, output_dir=str(output_dir), **params)
    return sorted(out["calibrated"])


def light_curve(files, target, comps, **params):
    """Differential photometry of target [x, y] against comps [[x, y], ...] on the frames `files`: the light-curve
    dict (time, rel_flux, rel_flux_err, ...) of photometry.light_curve. Keywords are that step's other inputs and
    parameters."""
    return run("photometry.light_curve", images=[str(f) for f in files], target_xy=list(target),
               comps_xy=[list(c) for c in comps], **params)["light_curve"]  # fmt: skip


def period_search(lc, method="lomb-scargle", **params):
    """A period search of a light curve: lc is the dict light_curve() returns, a .lc.ecsv path, or a table with
    time and rel_flux (and rel_flux_err) columns. Returns a Result (periods, power, best, ...; .to_table())."""
    if isinstance(lc, (str, bytes)) or hasattr(lc, "__fspath__"):
        from ..photometry import lcfile

        lc = lcfile.read(lc)
    cols = {k: list(map(float, lc[k])) for k in ("time", "rel_flux") if k in lc}
    if len(cols) < 2:
        raise ValueError("a light curve needs time and rel_flux columns")
    err = lc.get("rel_flux_err")
    return run("timeseries.period", time=cols["time"], flux=cols["rel_flux"], method=method,
               **({"err": list(map(float, err))} if err is not None else {}), **params)  # fmt: skip


def __getattr__(name):
    if name.startswith("_") or not any(s.startswith(name + ".") for s in steps()):
        raise AttributeError(name)
    return _Area(name)
