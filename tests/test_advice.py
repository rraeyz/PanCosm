"""PHO-43: advice for the next night from a measured light curve."""

import numpy as np
import pytest

from astrowb.photometry.advice import next_night


def night(n=100, late_peak=70000.0):
    peak = np.column_stack([np.linspace(20000, late_peak, n), np.full(n, 15000.0)])  # the seeing improves late
    return {
        "time": (2460000.5 + np.arange(n) * 60 / 86400).tolist(),
        "peak": peak.tolist(),
        "sky": np.full((n, 2), 1000.0).tolist(),
        "saturation": 65535.0,
        "target_flux": np.full(n, 2e5).tolist(),
        "lost": {"f90.fits": ["comparison", 1]},
        "partial": {f"f{i}.fits": [2] for i in range(10)},
    }


def test_a_night_that_saturates_late_gets_a_shorter_exposure():
    advice = {a["kind"]: a for a in next_night(night(), exptime=60.0, linearity=50000.0)}
    a = advice["exposure"]
    assert a["star"] == 0 and a["suggest"] < 60
    # the late peak (69 000 above the sky) scaled to the suggested exposure, plus the sky, sits at 60 % of 50 000
    assert 69000 * a["suggest"] / 60 + 1000 == pytest.approx(30000, rel=0.01)
    assert advice["defocus"]["share"] == pytest.approx(np.median(np.linspace(19000, 69000, 100)) / 2e5, rel=1e-3)
    lost = [a for a in next_night(night(), exptime=60.0) if a["kind"] == "lost"]
    assert [(x["star"], x["share"]) for x in lost] == [(1, 0.01), (2, 0.1)]


def test_a_good_night_and_a_slow_cadence():
    lc = night(late_peak=35000.0) | {"target_flux": np.full(100, 3e6).tolist(), "lost": {}, "partial": {}}
    assert next_night(lc, exptime=60.0, linearity=50000.0) == []
    slow = next_night(lc, ingress_days=5 * 60 / 86400)
    assert slow == [{"kind": "cadence", "points": 5.0, "cadence_s": pytest.approx(60.0)}]


def test_advice_in_words():
    from astrowb.ui.photometry_checks import advice_lines

    lines = advice_lines(next_night(night(), exptime=60.0, linearity=50000.0, ingress_days=5 * 60 / 86400))
    assert len(lines) == 5 and lines[0].startswith("Expose 25 s instead of 60 s")
    assert "22 %" in lines[1] and "Comparison 2 was missing on 10 %" in lines[3] and "Only 5.0 points" in lines[4]


def test_the_largest_noise_term():
    lc = night() | {"radii": [[8.0, 15.0, 20.0]] * 100, "target_flux": np.full(100, 2e4).tolist()}
    noise = [a for a in next_night(lc, gain=1.0) if a["kind"] == "noise"]
    # sky 1000 e/px over 201 px = 2.0e5 against 2e4 photons: the sky is 91 % of the variance
    assert noise == [{"kind": "noise", "term": "sky", "share": pytest.approx(0.91, abs=0.005)}]
    bright = lc | {"target_flux": np.full(100, 1e7).tolist(), "scintillation": [0.002] * 100}
    assert [a["term"] for a in next_night(bright) if a["kind"] == "noise"] == ["scintillation"]


def test_noise_advice_in_words():
    from astrowb.ui.photometry_checks import advice_lines

    assert advice_lines([{"kind": "noise", "term": "sky", "share": 0.91}]) == [
        "The sky is 91 % of the target's noise: a smaller aperture, a narrower filter or a darker sky lowers it."
    ]
