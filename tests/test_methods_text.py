"""ARC-11 item 4, engine side: the methods paragraph of recorded runs, from templates and the runs' parameters."""

from astrowb.core.methods import methods


def _run(step, params, status="done"):
    return {"step": step, "params": params, "status": status, "environment": {"app": "9.9.9"}}


def test_paragraph_from_runs_uses_recorded_parameters_and_defaults():
    runs = [
        _run("calibration.run", {"sigma": 2.5, "cosmic_rays": True}),
        _run("stacking.stack", {"method": "median", "rejection": "mad"}),
        _run("stacking.stack", {"method": "median", "rejection": "mad"}),  # the same run again: said once
        _run("calibration.run", {"sigma": 7}, status="failed"),  # failed: not a method
        _run("photometry.quality", {}),  # no template: silent
    ]
    text = methods(runs)
    assert "bias and dark current and flat field" in text and "2.5 sigma" in text and "L.A.Cosmic" in text
    assert text.count("combined by their median with mad rejection") == 1 and "version 9.9.9" in text
    assert "7 sigma" not in text


def test_no_flat_no_cosmic_clause_and_nothing_without_templates():
    assert "flat" not in methods([_run("calibration.run", {"divide_flat": False})])
    assert methods([_run("photometry.quality", {})]) == ""
