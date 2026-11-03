"""Visual binary orbit: Kepler's equation, Thiele-Innes <-> Campbell, a simulated orbit recovered."""

import numpy as np
import pytest

from astrowb.models import visual as v

TRUE = {"P": 12.3, "T": 2005.4, "e": 0.42, "a": 0.85, "i": 63.0, "node": 118.0, "omega": 227.0}


def simulate(n=40, seed=3, sig_rho=0.005, sig_th=0.4):
    rng = np.random.default_rng(seed)
    A, B, F, G = v.thiele_innes(TRUE["a"], *np.radians([TRUE["i"], TRUE["node"], TRUE["omega"]]))
    t = np.sort(rng.uniform(1998, 2024, n))
    th, rho = v.to_polar(*v.xy_of(t, TRUE["P"], TRUE["T"], TRUE["e"], A, B, F, G))
    return t, th + rng.normal(0, sig_th, n), rho + rng.normal(0, sig_rho, n), np.full(n, sig_rho), np.full(n, sig_th)


def test_kepler_equation_is_solved():
    m = np.linspace(0, 2 * np.pi, 200)
    for e in (0.0, 0.3, 0.8, 0.95):
        ecc = v.kepler(m, e)
        assert np.max(np.abs(ecc - e * np.sin(ecc) - np.mod(m, 2 * np.pi))) < 1e-10


def test_thiele_innes_and_campbell_round_trip():
    rng = np.random.default_rng(1)
    for _ in range(200):
        a, i, node, w = rng.uniform(0.1, 3), rng.uniform(0.05, 3.09), rng.uniform(0, np.pi), rng.uniform(0, 2 * np.pi)
        back = v.campbell(*v.thiele_innes(a, i, node, w))
        assert back[0] == pytest.approx(a) and back[1] == pytest.approx(i)
        assert back[2] == pytest.approx(node, abs=1e-9) and np.cos(back[3] - w) == pytest.approx(1.0)


def test_simulated_orbit_is_recovered_with_honest_errors():
    t, th, rho, s_r, s_t = simulate()
    o = v.fit(t, th, rho, s_r, s_t, p_range=(2, 60), parallax=0.05)
    for k, true in TRUE.items():
        assert abs(o[k] - true) < 4 * o["errors"][k] + 1e-6, (k, o[k], true, o["errors"][k])
    mass = TRUE["a"] ** 3 / (0.05**3 * TRUE["P"] ** 2)
    assert o["mass"] == pytest.approx(mass, abs=4 * o["mass_err"])
    assert 0.3 < o["chi2_red"] < 2.0 and o["rms_rho"] < 0.01
    th_e, rho_e = v.ephemeris(o, [2030.0])
    A, B, F, G = v.thiele_innes(TRUE["a"], *np.radians([TRUE["i"], TRUE["node"], TRUE["omega"]]))
    th_t, rho_t = v.to_polar(*v.xy_of(np.array([2030.0]), TRUE["P"], TRUE["T"], TRUE["e"], A, B, F, G))
    assert rho_e[0] == pytest.approx(rho_t[0], abs=0.01) and abs((th_e[0] - th_t[0] + 180) % 360 - 180) < 1.0


def test_parse_measures_and_refusals():
    t, th, rho, se, te = v.parse_measures("# WDS order\n2001.5 128.4 0.512 0.005\n2002.5, 130.0, 0.50, 0.004\n")
    assert list(t) == [2001.5, 2002.5] and te is None and list(se) == [0.005, 0.004]
    with pytest.raises(ValueError):
        v.parse_measures("2001.5 128.4")
    with pytest.raises(ValueError):
        v.fit(t, th, rho)  # fewer measures than elements


def test_step_and_tab(qtbot):
    from astrowb.engine.steps import execute
    from astrowb.ui.models_page import ModelsPage

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    t, th, rho, s_r, s_t = simulate(n=25, seed=9)
    text = "\n".join(f"{a:.4f} {b:.3f} {c:.4f} {d} {e}" for a, b, c, d, e in zip(t, th, rho, s_r, s_t, strict=True))
    o = execute("models.visual_orbit", {"measures": text}, {"p_min": 2, "p_max": 60, "parallax_mas": 50}, Ctx())[
        "orbit"
    ]
    assert o["P"] == pytest.approx(TRUE["P"], abs=4 * o["errors"]["P"]) and "mass" in o and len(o["epoch"]) == 25
    page = ModelsPage()
    qtbot.addWidget(page)
    assert page.tabs.count() == 2
    page.visual_tab.measures.setPlainText(text)
    page.visual_tab.parallax.setValue(50)
    with qtbot.waitSignal(page.visual_tab.fit_requested) as sig:
        page.visual_tab.fit_button.click()
    assert sig.args[1] == {"parallax_mas": 50.0}
    page.visual_tab.show_orbit(o)
    assert page.visual_tab.table.rowCount() == 10 and page.visual_tab.plot.figure.axes
