"""AUT-1: steps describe their settings; a run with a value out of its range or kind is refused before it starts,
naming the setting."""

import json
from pathlib import Path

import pytest

from astrowb.engine import steps
from astrowb.engine.params import P, problem

LEFT = Path(__file__).parent / "data" / "steps_not_described.json"


def test_no_new_step_without_a_description():
    """A ratchet: the steps still in the old form may only become fewer (every one described is taken off the list;
    AUT-1 is done when the list is empty)."""
    steps._load_builtin()
    old_form = {k for k, s in steps.REGISTRY.items() if s.defaults and not s.params}
    allowed = set(json.loads(LEFT.read_text()))
    assert old_form <= allowed, f"describe these steps with params=[P(...)]: {sorted(old_form - allowed)}"
    assert not allowed - old_form, f"described now: take {sorted(allowed - old_form)} off {LEFT.name}"
    partly = {k: sorted(set(s.defaults) - {p.name for p in s.params}) for k, s in steps.REGISTRY.items() if s.params}
    assert not {k: v for k, v in partly.items() if v}, "every setting of a described step is described"


def test_values_out_of_range_or_kind_are_named():
    p = P("n_max", "int", 10, min=1, max=200)
    assert problem(p, 10) is None and problem(p, None) is None  # None: the step decides
    assert problem(p, 0) == "n_max = 0 is below the smallest allowed value 1"
    assert problem(p, 2.5) == "n_max must be a whole number, not 2.5"
    assert problem(P("model", "choice", "ltte", choices=("ltte", "apsidal")), "lte") == (
        "model must be one of ltte, apsidal, not lte"
    )
    assert problem(P("clean", "bool", False), "yes") == "clean must be true or false, not yes"
    with pytest.raises(ValueError, match="unknown parameter kind"):
        P("x", "colour")


def test_a_described_step_refuses_a_bad_value_before_running():
    from astrowb.engine.steps import execute

    with pytest.raises(ValueError, match="n_max = 0 is below"):
        execute("timeseries.frequencies", {"time": [1, 2, 3], "flux": [1, 2, 1]}, {"n_max": 0}, None)
    s = steps.get("timeseries.frequencies")
    assert s.defaults["f_max"] == 50.0 and {p.name for p in s.params} == set(s.defaults)  # one description


def test_a_form_is_made_from_the_description(qtbot):
    """AUT-1 item 5: calibration.run's described settings give a form with their controls and defaults; a change
    reaches the values; the plugin dialog uses the form for a described step."""
    from astrowb.ui.kit.fields import NumberField, Toggle
    from astrowb.ui.kit.stepform import StepForm
    from astrowb.ui.plugin_dialog import PluginDialog

    step = steps.get("calibration.run")
    form = StepForm(step)
    qtbot.addWidget(form)
    assert form.values() == json.loads(json.dumps(step.defaults))  # a list for a tuple, as a recipe keeps it
    assert isinstance(form.rows["sigma"].control, NumberField) and isinstance(form.rows["cosmic_rays"].control, Toggle)
    form.rows["sigma"].control.setValue(2.5)
    assert form.values()["sigma"] == 2.5 and form.rows["sigma"].label.text() == "Sigma"
    dialog = PluginDialog(steps.get("timeseries.period"))
    qtbot.addWidget(dialog)
    dialog.step_form.rows["method"].control.setValue("bls")
    assert dialog.values()[1] == {"method": "bls", "p_min": 0.05}  # p_max left automatic
