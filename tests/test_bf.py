"""Broadening function: rotating single stars and a contact binary simulated with known profiles."""

import numpy as np
import pytest
from test_sb2 import DEPTH1, LINES1, WAVE, template

from astrowb.spectroscopy.bf import broadening_function, rotational_profile

STEP = 1.5  # km/s per pixel of WAVE
SHARP = template(LINES1, DEPTH1, 0.05)


def broadened(stars, snr=300, seed=1):
    """stars: [(v, vsini, light share)]; the sharp template convolved with their rotational profiles."""
    v = np.arange(-300, 300 + STEP, STEP)
    kernel = sum(share * rotational_profile(v, v0, vsini) for v0, vsini, share in stars) * STEP
    depth = np.convolve(1 - SHARP, kernel, mode="same")
    return 1 - depth + np.random.default_rng(seed).normal(0, 1 / snr, len(depth))


def test_rotational_profile_has_unit_area():
    v = np.linspace(-100, 100, 20001)
    assert np.trapezoid(rotational_profile(v, 10, 45), v) == pytest.approx(1, abs=1e-3)


def test_single_fast_rotator():
    r = broadening_function(WAVE, broadened([(35.0, 80.0, 1.0)]), WAVE, SHARP, -250, 250)
    [c] = r["components"]
    assert c["rv"] == pytest.approx(35, abs=1.5) and c["vsini"] == pytest.approx(80, rel=0.05)
    assert c["strength"] == pytest.approx(1, rel=0.1) and c["rv_err"] < 1.5


def test_contact_binary_two_profiles():
    stars = [(-110.0, 120.0, 0.7), (160.0, 90.0, 0.3)]  # W UMa-like: broad, close profiles
    r = broadening_function(WAVE, broadened(stars), WAVE, SHARP, -350, 350, components=2)
    c1, c2 = r["components"]
    assert c1["rv"] == pytest.approx(-110, abs=3) and c2["rv"] == pytest.approx(160, abs=4)
    assert c1["vsini"] == pytest.approx(120, rel=0.08) and c2["vsini"] == pytest.approx(90, rel=0.1)
    assert c2["strength"] / c1["strength"] == pytest.approx(0.3 / 0.7, rel=0.12)


def test_no_overlap_is_reported():
    with pytest.raises(ValueError, match="overlap"):
        broadening_function(WAVE, SHARP, WAVE * 1.2, SHARP)


def test_rv_step_and_velocity_tab_with_broadening_function(tmp_path, qtbot):
    from test_sb2 import _Ctx

    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.spectro_page import VelocityTab

    err = np.full(len(WAVE), 0.003)
    spectrum_io.write(tmp_path / "t.fits", WAVE, SHARP, err)
    paths = []
    for i, (v1, v2) in enumerate([(-110.0, 160.0), (95.0, -140.0)]):
        paths.append(
            str(
                spectrum_io.write(
                    tmp_path / f"s{i}.fits", WAVE, broadened([(v1, 120, 0.7), (v2, 90, 0.3)], seed=i), err
                )
            )
        )
    tab = VelocityTab()
    qtbot.addWidget(tab)
    sent = []
    tab.rv_requested.connect(lambda inputs, params: sent.append((inputs, params)))
    tab.files.addItems(paths)
    tab.template.edit.setText(str(tmp_path / "t.fits"))
    tab.method.setCurrentIndex(2)
    tab.v_min.setValue(-350)
    tab.v_max.setValue(350)
    tab._measure()
    inputs, params = sent[0]
    assert params["method"] == "bf" and params["components"] == 2
    rows = execute("spectroscopy.rv", inputs, params, _Ctx())["rvs"]
    assert rows[0]["rv_obs"] == pytest.approx(-110, abs=3) and rows[0]["rv2_obs"] == pytest.approx(160, abs=4)
    assert rows[1]["rv_obs"] == pytest.approx(95, abs=3) and rows[1]["rv2_obs"] == pytest.approx(-140, abs=4)
    assert rows[0]["flux_ratio"] == pytest.approx(0.3 / 0.7, rel=0.12)
    tab.show_rvs(rows)
    assert "v sin i = 120" in tab.status.text() or "v sin i = 119" in tab.status.text()
