"""ARC-11 item 4: methods paragraphs of the O-C, frequency, nearby-EB, plate-solving and spectroscopy steps."""

import pytest

from astrowb.core.methods import methods


def _text(step, params):
    return methods([{"step": step, "params": params, "status": "done", "environment": {"app": "9.9.9"}}])


@pytest.mark.parametrize(
    "step,params,expected",
    [
        (
            "timeseries.oc_fit",
            {"model": "ltte", "t0": 2450000.5, "period": 0.5, "mcmc_steps": 500},
            ["light-travel-time effect", "Irwin 1952", "0.5 d", "500 steps"],
        ),
        ("timeseries.oc_fit", {"model": "apsidal"}, ["apsidal motion", "Gimenez", "T0 = 0.000000"]),
        (
            "timeseries.frequencies",
            {"f_max": 20, "n_max": 7, "snr_min": 4.5, "clean": True},
            ["up to 20 c/d", "at most 7", "below 4.5", "Breger et al. 1993", "Baluev (2008)", "CLEAN"],
        ),
        (
            "photometry.neb_check",
            {"depth_ppt": 3.0, "radius_arcsec": 120, "tc": 2460000.1, "duration_h": 2.0},
            ["120 arcsec", "3 ppt", "TFOP SG1", "6 pixels", "box was fitted"],
        ),
        ("photometry.neb_check", {"apertures": [[4, 8, 12], [6, 10, 16]]}, ["2 apertures"]),
        ("astrometry.solve", {"radius_deg": 12, "refine_gaia": True}, ["12 deg", "Gaia DR3"]),
        (
            "spectroscopy.reduce",
            {"line_list": "fear", "order": 4, "optimal": False},
            ["boxcar", "fear arc-lamp", "degree up to 4"],
        ),
        (
            "spectroscopy.echelle",
            {"deg_x": 5, "deg_m": 2},
            ["optimal extraction", "degree 5", "across them was fitted"],
        ),
        (
            "spectroscopy.rv",
            {"method": "bf", "components": 2},
            ["broadening function", "2 rotational profiles", "Rucinski"],
        ),
        ("spectroscopy.rv", {"v_min": -100, "v_max": 150}, ["-100 and 150 km/s", "Zucker & Mazeh 1994"]),
    ],
)
def test_template_states_what_the_run_recorded(step, params, expected):
    text = _text(step, params)
    for part in expected:
        assert part in text
    assert "version 9.9.9" in text and "{" not in text


def test_flags_off_leave_no_clause():
    assert "CLEAN" not in _text("timeseries.frequencies", {})
    assert "Gaia" not in _text("astrometry.solve", {"refine_gaia": False})
    assert "Markov" not in _text("timeseries.oc_fit", {})
    assert "box" not in _text("photometry.neb_check", {})
