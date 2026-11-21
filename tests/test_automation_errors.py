"""Per-step "on_error" of automations: stop (default), skip, continue."""

import pytest

from astrowb.engine import automation


def _drive(auto, inputs, fail):
    """Run `calls`; a call whose step id is in `fail` gets Failed."""
    made, gen = [], automation.calls(auto, inputs)
    call = next(gen)
    try:
        while True:
            made.append(call)
            bad = call[0] in fail
            call = gen.send(automation.Failed(ValueError("boom")) if bad else {"destination": "d", "y": 1})
    except StopIteration as stop:
        return made, stop.value


def test_stop_is_the_default_and_raises():
    auto = {"steps": [{"step": "fits.save_as"}]}
    with pytest.raises(ValueError, match="boom"):
        _drive(auto, {"source": "a", "destination": "b"}, {"fits.save_as"})


def test_skip_drops_outputs_and_continue_goes_on():
    first = {"step": "fits.save_as", "on_error": "skip"}
    second = {"step": "fits.save_as", "inputs": {"source": "destination"}}
    auto = {"steps": [first, second]}
    # the first call fails: its outputs are not kept, so the second still sees the given "destination"
    gen = automation.calls(auto, {"source": "a", "destination": "b"})
    next(gen)
    call = gen.send(automation.Failed("x"))
    assert call[1]["source"] == "b"  # nothing from step 1 replaced it
    auto["steps"][0]["on_error"] = "continue"
    gen = automation.calls(auto, {"source": "a", "destination": "b"})
    next(gen)
    assert gen.send(automation.Failed("x"))[0] == "fits.save_as"


def test_each_skip_leaves_at_once_and_continue_takes_the_next_item():
    def run(mode):
        auto = {"steps": [{"step": "fits.save_as", "each": "source", "on_error": mode}]}
        gen = automation.calls(auto, {"source": ["a", "b", "c"], "destination": "d"})
        seen, call = [], next(gen)
        try:
            while True:
                seen.append(call[1]["source"])
                call = gen.send(automation.Failed("x") if call[1]["source"] == "a" else {"destination": "o"})
        except StopIteration as stop:
            return seen, stop.value

    assert run("skip") == (["a"], {"source": ["a", "b", "c"], "destination": "d"})
    seen, data = run("continue")
    assert seen == ["a", "b", "c"] and data["destination"] == ["o", "o"]  # the failed item has no value


def test_user_templates_are_listed_as_templates_and_names_are_unique():
    auto = {"name": "mine", "steps": [{"step": "fits.save_as"}]}
    path = automation.save_template(auto, "Mine 2")
    assert path.parent == automation.user_dir() / "templates"
    assert [a["name"] for a in automation.available() if a["template"] and a["path"] == str(path)] == ["Mine 2"]
    with pytest.raises(ValueError, match="exists"):
        automation.save_template(auto, "mine 2")
    shipped = automation.text(automation.available()[0]["name"])
    with pytest.raises(ValueError, match="exists"):
        automation.save_template(auto, shipped)
