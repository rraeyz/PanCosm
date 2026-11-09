"""PLN-4: an event's time uncertainty grows with the cycles since T0; missing errors are estimated from the digits."""

import numpy as np
import pytest

from astrowb.planning import events


def test_sigma_grows_with_the_epoch():
    assert events.sigma(0, 1e-4, 1e-6) == pytest.approx(1e-4)
    assert events.sigma(1000, 1e-4, 1e-6) == pytest.approx(np.hypot(1e-4, 1e-3))
    assert events.sigma(1000, 1e-4, 1e-6, cov=-5e-11) < events.sigma(1000, 1e-4, 1e-6)  # anticorrelated T0 and P


def test_errors_from_the_digits():
    assert events.digits_error("0.1010159") == pytest.approx(5e-8)
    assert events.digits_error("2455867.4027") == pytest.approx(5e-5)
    assert events.digits_error("1.5e-3") == pytest.approx(5e-5)  # half of 0.1, times 1e-3
    assert events.digits_error("12") is None


def test_a_night_event_carries_its_sigma():
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    site = {"name": "TUG", "lat": 36.8242, "lon": 30.3356, "height": 2500.0}
    hat = {"name": "HAT-P-32 b", "ra": 31.04, "dec": 46.69, "t0": 2455867.4027, "period": 2.15, "duration": 0.13}
    known = execute("planning.night", {"site": site, "date": "2026-11-13", "targets": [hat | {"t0_err": 2e-4,
                    "period_err": 1e-6}]}, {"min_alt": 20.0, "step_min": 10.0}, Ctx())["night"]  # fmt: skip
    e = known["targets"][0]["events"][0]
    n = e["epoch"]
    assert n > 1000 and e["sigma_min"] == pytest.approx(np.hypot(2e-4, n * 1e-6) * 1440, rel=1e-6)
    assert not e["sigma_estimated"]
    texts = {"t0_text": "2455867.4027", "period_text": "2.15"}
    guessed = execute("planning.night", {"site": site, "date": "2026-11-13", "targets": [hat | texts]},
                      {"min_alt": 20.0, "step_min": 10.0}, Ctx())["night"]  # fmt: skip
    g = guessed["targets"][0]["events"][0]
    assert g["sigma_estimated"] and g["sigma_min"] > 60  # P to two decimals: hours off after a thousand cycles
