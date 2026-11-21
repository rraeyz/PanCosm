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


def test_photometry_and_timing_templates():
    text = methods(
        [
            _run("photometry.light_curve", {"r_ap": 5.5, "r_in": 12, "r_out": 18, "psf": True}),
            _run("timeseries.minimum", {"method": "kvw", "t0": 2460000.12345, "period": 0.5}),
            _run("timeseries.period", {"method": "gls", "p_min": 0.1, "p_max": 3}),
            _run("photometry.transit_fit", {"period": 2.5, "red_noise": True, "mcmc_steps": 500}),
            _run("models.eb_fit", {"free": ["t0", "k"], "mcmc_steps": 100}),
        ]
    )
    assert "aperture radius of 5.5 px" in text and "from 12 to 18 px" in text and "PSF fitting" in text
    assert "Kwee & van Woerden (1956)" in text and "T0 = 2460000.12345" in text
    assert "from 0.1 d to 3 d" in text and "Zechmeister" in text
    assert "period of 2.5 d" in text and "Winn et al. (2008)" in text and "500 MCMC" in text
    assert "free parameters being t0, k" in text and "100 MCMC" in text
    assert methods([_run("timeseries.period", {"method": "pdm"})]).count("half the time") == 1
