"""PER-6: the frequency list fitted at once, combinations identified, errors, variations."""

import numpy as np
import pytest

from astrowb.timeseries import frequency as fq

F1, F2, F3 = 10.137, 13.411, 7.902


def three_modes(seed, n=3000, span=30.0, noise=1.0):
    rng = np.random.default_rng(seed)
    t = np.sort(rng.uniform(0, span, n))
    parts = [(10, F1, 0.1), (8, F2, 0.3), (6, F3, 0.7), (2.0, 2 * F1, 0.2), (1.5, F1 + F2, 0.5), (1.2, F2 - F3, 0.9)]
    y = sum(a * np.sin(2 * np.pi * (f * t + ph)) for a, f, ph in parts)
    return t, y + rng.normal(0, noise, n)


def start_terms(jitter=0.0):
    names = [("F1", F1), ("F2", F2), ("F3", F3), ("F4", 2 * F1), ("F5", F1 + F2), ("F6", F2 - F3)]
    return [fq.term(n, f + jitter) for n, f in names]


def test_improve_all_recovers_the_signal_and_relations_tie_frequencies():
    t, y = three_modes(1)
    terms, info = fq.improve_all(t, y, start_terms(2e-4), linear_start=True)
    truth = [F1, F2, F3, 2 * F1, F1 + F2, F2 - F3]
    for v, f in zip(terms, truth, strict=True):
        assert abs(v["freq"] - f) < 4 * v["freq_err"] + 1e-9
    assert info["rms"] == pytest.approx(1.0, rel=0.05)
    tied = start_terms(2e-4)
    tied[3]["relation"], tied[4]["relation"] = {"F1": 2}, {"F1": 1, "F2": 1}
    got, _ = fq.improve_all(t, y, tied, linear_start=True)
    assert got[3]["freq"] == pytest.approx(2 * got[0]["freq"], abs=1e-12)
    assert got[4]["freq"] == pytest.approx(got[0]["freq"] + got[1]["freq"], abs=1e-12)
    assert got[3]["freq_err"] == pytest.approx(2 * got[0]["freq_err"], rel=1e-6)
    tied[0]["relation"] = {"F2": 1}
    with pytest.raises(ValueError):
        fq.improve_all(t, y, tied)


def test_combinations_are_found_and_none_invented():
    false = 0
    for seed in range(200):
        t, y = three_modes(seed, n=1500)
        terms, _ = fq.improve_all(t, y, start_terms(), linear_start=True)
        proposals, close = fq.identify(terms, np.ptp(t))
        assert proposals["F4"][0] == {"F1": 2} and proposals["F5"][0] == {"F1": 1, "F2": 1}
        assert proposals["F6"][0] == {"F2": 1, "F3": -1}
        false += any(k in proposals for k in ("F1", "F2", "F3"))
        assert not close
    assert false <= 10  # no false one in at least 95 % of 200 realisations


def test_monte_carlo_and_analytic_errors_agree_on_white_noise():
    t, y = three_modes(3, n=2000)
    terms, info = fq.improve_all(t, y, start_terms(), linear_start=True)
    resid = y - fq.evaluate(terms, info, t)
    analytic = fq.analytic_errors(t, terms, info["rms"], resid)
    mc = fq.monte_carlo_errors(t, y, terms, info, n=120)
    for a, m, cov in zip(analytic, mc, terms, strict=True):
        for k in ("freq_err", "amp_err", "phase_err"):
            assert m[k] == pytest.approx(a[k], rel=0.25), k
            assert cov[k] == pytest.approx(a[k], rel=0.25), k
    assert fq.correlation_factor(np.random.default_rng(0).normal(size=5000)) == pytest.approx(1.0, abs=0.05)
    red = np.convolve(np.random.default_rng(0).normal(size=5000), np.ones(8), "same")
    assert fq.correlation_factor(red) > 1.5


def test_amplitude_and_phase_per_subset():
    rng = np.random.default_rng(4)
    t = np.sort(rng.uniform(0, 40, 4000))
    amp = 5 + 0.1 * t  # a growing amplitude
    y = amp * np.sin(2 * np.pi * (F1 * t + 0.25)) + rng.normal(0, 0.5, t.size)
    terms, info = fq.improve_all(t, y, [fq.term("F1", F1)], linear_start=True)
    out = fq.variations(t, y, terms, info, np.floor(t / 5))["F1"]
    assert len(out) == 8
    for row in out:
        assert row["amp"] == pytest.approx(5 + 0.1 * row["time"], abs=4 * row["amp_err"] + 0.05)
        assert row["amp_err"] < 0.05 and row["phase_err"] < 0.005


def test_improve_all_fits_fifty_terms_together():  # its speed on 10^5 points: tools/speed.py
    rng = np.random.default_rng(5)
    t = np.sort(rng.uniform(0, 100, 20_000))
    f = 1 + np.arange(50) * 0.731
    y = sum(np.sin(2 * np.pi * (fk * t + 0.1 * k)) for k, fk in enumerate(f)) + rng.normal(0, 0.1, t.size)
    terms = [fq.term(f"F{k + 1}", fk + 1e-5, 1.0, 0.1 * k) for k, fk in enumerate(f)]
    got, info = fq.improve_all(t, y, terms, t_ref=0.0)
    assert info["rms"] == pytest.approx(0.1, rel=0.03)
    assert np.allclose([v["freq"] for v in got], f, atol=5e-6)


def test_the_periodic_time_shift_of_a_pulsator_in_a_binary():
    from astrowb.timeseries.oc_models import _tau

    rng = np.random.default_rng(6)
    t = np.sort(rng.uniform(0, 200, 6000))
    orbit = {"period": 50.0, "a": 100 / 86400, "t_peri": 12.0, "e": 0.3, "omega": 60.0}
    emitted = t - _tau(t, orbit["a"], orbit["period"], orbit["t_peri"], orbit["e"], orbit["omega"])
    y = 10 * np.sin(2 * np.pi * (15.0 * emitted + 0.2)) + 6 * np.sin(2 * np.pi * (18.7 * emitted + 0.6))
    y = y + rng.normal(0, 1.0, t.size)
    terms, info = fq.improve_all(t, y, [fq.term("F1", 15.0), fq.term("F2", 18.7)], linear_start=True)
    start = {"period": 51.0, "a": 70 / 86400, "t_peri": 15.0, "e": 0.2, "omega": 80.0}
    terms, info, got, err = fq.time_shift(t, y, terms, info, start)
    assert info["rms"] == pytest.approx(1.0, rel=0.03)
    for key in ("period", "a", "e", "omega"):
        assert abs(got[key] - orbit[key]) < 4 * err[key], key
    assert err["a"] * 86400 < 5  # the light-time amplitude to a few seconds


def test_the_table_in_both_units_and_its_exports(tmp_path):
    from astropy.table import Table

    t, y = three_modes(2, n=1500)
    terms = start_terms()
    terms[3]["relation"] = {"F1": 2}
    terms, info = fq.improve_all(t, y, terms, linear_start=True)
    cd = fq.to_table(terms, info, amp_unit="mmag")
    uhz = fq.to_table(terms, info, "uHz")
    assert uhz["frequency"][0] == pytest.approx(cd["frequency"][0] * 1e6 / 86400)
    assert cd["relation"][3] == "2F1" and cd["relation"][0] == ""
    cd.write(tmp_path / "f.ecsv", format="ascii.ecsv")
    back = Table.read(tmp_path / "f.ecsv")
    assert back.meta["t_ref"] == info["t_ref"] and str(back["amplitude"].unit) == "mmag"
    cd.write(tmp_path / "f.tex", format="ascii.latex")
    assert "\\begin{table}" in (tmp_path / "f.tex").read_text()
    with pytest.raises(ValueError):
        fq.to_table(terms, info, "Hz")
