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


def test_a_broad_star_on_the_shoulder_of_a_sharp_one():
    # TZ For on HARPS: G8 giant at v sin i 6 km/s, F giant at 46 km/s with half its light, 47 km/s apart: the F star
    # makes no peak of its own (14 of 22 real spectra failed with "fewer than 2 peaks")
    stars = [(41.0, 6.0, 0.68), (-6.0, 46.0, 0.32)]
    r = broadening_function(WAVE, broadened(stars, snr=500), WAVE, SHARP, -150, 150, components=2)
    c1, c2 = r["components"]
    assert c1["rv"] == pytest.approx(41, abs=0.5) and c2["rv"] == pytest.approx(-6, abs=3)
    assert c2["vsini"] == pytest.approx(46, rel=0.15)
    assert c2["strength"] / c1["strength"] == pytest.approx(0.47, rel=0.2)


def test_a_single_star_is_not_split_in_two():
    with pytest.raises(ValueError, match="fewer than 2 peaks"):
        broadening_function(WAVE, broadened([(20.0, 10.0, 1.0)], snr=300), WAVE, SHARP, -150, 150, components=2)


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


def test_rv_step_single_fast_rotator_with_a_dated_archive_spectrum(tmp_path):
    """One star, from a spectrum with a date and sky position (every archive spectrum): the step took the single
    star's v sin i for a second star's velocity and stopped (KeyError 'rv2_obs'), on a real HARPS beta Pic."""
    from astropy.io import fits
    from test_sb2 import _Ctx

    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io

    err = np.full(len(WAVE), 0.003)
    spectrum_io.write(tmp_path / "t.fits", WAVE, SHARP, err)
    rows = []
    for specsys in ("BARYCENT", "TOPOCENT"):  # already barycentric, and corrected here (site from the header)
        cards = {"DATE-OBS": "2019-01-22T03:44:00", "EXPTIME": 60.0, "RA": 86.82, "DEC": -51.07, "SPECSYS": specsys}
        header = fits.Header(cards | {"LATITUDE": -29.26, "LONGITUD": -70.73})
        header.comments["LONGITUD"] = "E+"
        path = spectrum_io.write(tmp_path / f"{specsys}.fits", WAVE, broadened([(20.0, 120.0, 1.0)]), err, header)
        params = {"method": "bf", "components": 1, "v_min": -300, "v_max": 300}
        [row] = execute(
            "spectroscopy.rv", {"spectra": [str(path)], "template": str(tmp_path / "t.fits")}, params, _Ctx()
        )["rvs"]
        rows.append(row)
        assert row["vsini"] == pytest.approx(120, rel=0.06) and row.get("rv2") is None and row["rv"] is not None
    assert rows[0]["already_barycentric"] and rows[1]["v_corr"] is not None
