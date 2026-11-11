"""ARC-12: scripts written against astrowb.api keep working — no step or keyword disappears unnoticed.

A step or keyword removed on purpose: update tests/data/api_steps.json in the same commit and say so in its message.
"""

import json
from pathlib import Path

import pytest

from astrowb import api

STORED = json.loads((Path(__file__).parent / "data" / "api_steps.json").read_text(encoding="utf-8"))


def test_no_step_or_keyword_was_removed():
    from astrowb.engine import steps as registry

    registry._load_builtin()
    for step_id, names in STORED.items():
        assert step_id in registry.REGISTRY, f"step {step_id} was removed"
        s = registry.REGISTRY[step_id]
        assert not set(names) - set(s.inputs) - set(s.optional) - set(s.defaults), step_id


def test_steps_are_functions_with_their_help():
    f = api.models.visual_orbit
    assert "inputs: measures" in f.__doc__ and "parallax_mas=None" in f.__doc__
    assert "visual_orbit" in dir(api.models)
    with pytest.raises(TypeError, match="no input or parameter radius"):
        api.models.visual_orbit(measures="x", radius=3)
    with pytest.raises(AttributeError):
        api.models.nothing_here  # noqa: B018
    with pytest.raises(AttributeError):
        api.not_an_area  # noqa: B018


def test_a_step_runs_from_a_script():
    from test_visual_orbit import simulate

    t, th, rho, s_r, s_t = simulate(n=25, seed=9)
    text = "\n".join(f"{a:.4f} {b:.3f} {c:.4f} {d} {e}" for a, b, c, d, e in zip(t, th, rho, s_r, s_t, strict=True))
    out = api.models.visual_orbit(measures=text, p_min=2, p_max=60)
    assert 2 < out["orbit"]["P"] < 60
