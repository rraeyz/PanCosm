"""OC-2: one eclipse timed by every method with honest errors, and the verdicts of the method comparison."""

import numpy as np
import pytest

from astrowb.timeseries.timing_methods import METHODS, asymmetry, compare_methods, time_minimum

T = 2458107.6123


def v_shaped(t, asym=0.0):
    x = (t - T) / 0.02
    return 1 - 0.3 * np.exp(-0.5 * x**2) * (1 + asym * np.tanh(x))  # asym: one branch deeper (a spot)


def flat_bottomed(t):
    return 1 - 0.2 * np.clip((0.035 - np.abs(t - T)) / 0.012, 0, 1)


SUITED = {  # the methods whose shape suits the eclipse (the others report large errors, see below); Mikulášek's is
    # biased by 0.5–0.8 σ with one branch covered to 60 %, the bisector's error is 4 × too large on a flat bottom
    # (both in timing_methods' docstring)
    "v": ("kvw", "gaussian", "bisector", "polynomial"),
    "flat": ("kvw", "trapezoid", "polynomial"),
}


@pytest.mark.slow
@pytest.mark.parametrize("shape", ["v", "flat"])
def test_every_suited_method_is_unbiased_and_its_error_honest(shape):
    """The plan's acceptance in small: 40 noise realisations at S/N 50, coverage 60 % on one side, bias below
    0.3 × the reported error (within the sampling error of the mean) and the reported error 0.7–1.7 × the scatter
    (the plan asks 0.8–1.3 from 500 realisations; the largest of three errors errs on the safe side)."""
    t = T + np.linspace(-0.06, 0.045, 140)
    curve = v_shaped if shape == "v" else flat_bottomed
    for method in SUITED[shape]:
        times, errors = [], []
        for seed in range(40):
            y = curve(t) + np.random.default_rng(seed).normal(0, 0.006, t.size)
            r = time_minimum(t, y, method=method, bootstrap=30, seed=seed)
            times.append(r.t_min)
            errors.append(r.error)
        times, err = np.array(times), float(np.median(errors))
        scatter = times.std()
        assert abs(times.mean() - T) < 0.3 * err + 3 * scatter / np.sqrt(len(times)), (method, times.mean() - T)
        assert 0.7 < err / scatter < 1.7, (method, err / scatter)


def test_a_shape_that_does_not_suit_reports_it_in_its_error():
    """A polynomial or a Gaussian on a flat-bottomed transit: their times wander, and their errors say so — the
    comparison weighs them little and does not call the eclipse asymmetric."""
    t = T + np.linspace(-0.06, 0.06, 160)
    y = flat_bottomed(t) + np.random.default_rng(1).normal(0, 0.003, t.size)
    c = compare_methods(t, y, bootstrap=40)
    assert set(c["results"]) == set(METHODS)
    good = c["results"]["mikulasek"]
    assert abs(good.t_min - T) < 3 * good.error
    assert c["results"]["polynomial"].error > 10 * good.error
    assert not c["disagree"] and not c["asymmetric"]


def test_the_bisector_tilts_on_an_asymmetric_eclipse_only():
    t = T + np.linspace(-0.06, 0.06, 400)
    noise = np.random.default_rng(2).normal(0, 0.0005, t.size)
    assert asymmetry(t, v_shaped(t, 0.05) + noise, T, samples=100)[2]
    assert not asymmetry(t, v_shaped(t) + noise, T, samples=100)[2]


def test_one_branch_only_is_said():
    t = T + np.linspace(-0.05, -0.002, 100)  # the egress not observed
    y = v_shaped(t) + np.random.default_rng(3).normal(0, 0.003, t.size)
    r = time_minimum(t, y, method="mikulasek", bootstrap=0)
    assert r.quality["right"] < 0.3 and "one branch only" in r.notes[0]


def test_errors_are_the_largest_of_three_and_a_jd_keeps_its_digits():
    t = T + np.linspace(-0.06, 0.06, 160)
    y = v_shaped(t) + np.random.default_rng(4).normal(0, 0.003, t.size)
    r = time_minimum(t, y, method="gaussian", bootstrap=50)
    assert set(r.errors) == {"analytic", "bootstrap", "prayer_bead"} and r.error == max(r.errors.values())
    assert abs(r.t_min - T) < 4 * r.error and r.error * 86400 < 30  # seconds, from a JD of 2.46e6
    with pytest.raises(ValueError, match="unknown timing method"):
        time_minimum(t, y, method="psychic")


def test_the_minimum_step_times_with_any_method():
    from astrowb.engine.steps import execute

    t = T + np.linspace(-0.06, 0.06, 160)
    y = v_shaped(t) + np.random.default_rng(5).normal(0, 0.003, t.size)
    lc = {"time": list(t), "rel_flux": list(y), "time_scale": "BJD_TDB"}
    out = execute("timeseries.minimum", {"light_curve": lc}, {"method": "gaussian"}, None)["minimum"]
    assert out["method"] == "gaussian" and abs(out["time"] - T) < 4 * out["error"] and "prayer_bead" in out["errors"]
    with pytest.raises(ValueError, match="must be one of"):
        execute("timeseries.minimum", {"light_curve": lc}, {"method": "psychic"}, None)
