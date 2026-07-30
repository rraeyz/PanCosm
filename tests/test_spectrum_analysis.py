import numpy as np
import pytest
from astropy.io import fits

from astrowb.spectroscopy import analysis, spectrum_io


@pytest.fixture
def absorption():
    """Gaussian absorption line, known EW, on a sloped continuum with S/N 200."""
    rng = np.random.default_rng(4)
    w = np.arange(6500.0, 6620.0, 0.25)
    cont = 1000 + 0.5 * (w - 6500)
    depth, centre, sigma = 0.6, 6562.8, 1.8
    f = cont * (1 - depth * np.exp(-0.5 * ((w - centre) / sigma) ** 2))
    return w, f * (1 + rng.normal(0, 0.005, w.size)), depth * sigma * np.sqrt(2 * np.pi)


@pytest.mark.parametrize("profile", ["gauss", "voigt"])
def test_line_measurement(absorption, profile):
    w, f, ew_true = absorption
    m = analysis.measure_line(w, f, 6540, 6585, profile=profile)
    assert abs(m["ew"] - ew_true) < 3 * m["ew_err"] and 0.02 < m["ew_err"] < 0.06  # Monte Carlo scatter: 0.041
    assert abs(m["centre"] - 6562.8) < 5 * m["centre_err"] + 0.01
    assert abs(m["fwhm"] - 2.3548 * 1.8) < 0.08
    assert abs(m["ew_fit"] - ew_true) < 0.05
    assert abs(m["snr"] - 200) < 40


def test_emission_ew_is_negative_and_v_over_r():
    w = np.arange(6520.0, 6605.0, 0.2)
    c = 6562.8
    blue = 1.2 * np.exp(-0.5 * ((w - c + 3) / 1.5) ** 2)
    red = 0.8 * np.exp(-0.5 * ((w - c - 3) / 1.5) ** 2)
    f = 1 + blue + red
    assert analysis.measure_line(w, f, 6545, 6580)["ew"] < -5
    vr = analysis.v_over_r(w, f, c, 10)
    assert abs(vr["v_over_r"] - 1.5) < 0.05
    assert abs(vr["v_velocity"] + 3 / c * analysis.C_KMS) < 15 and vr["r_velocity"] > 0


def test_arithmetic_smoothing_and_resampling():
    w = np.linspace(4000, 5000, 1001)
    a, b = np.full(w.size, 4.0), np.full(500, 2.0)
    wb = np.linspace(4100, 4900, 500)
    q = analysis.arithmetic(w, a, wb, b, "/")
    assert np.isnan(q[0]) and np.allclose(q[(w > 4100) & (w < 4900)], 2.0)
    assert np.allclose(analysis.arithmetic(w, a, None, 3.0, "-"), 1.0)
    spike = np.zeros(101)
    spike[50] = 1
    for kind in ("boxcar", "gauss"):
        s = analysis.smooth(spike, kind, 5)
        assert abs(s.sum() - 1) < 1e-6 and s.max() < 0.3
    assert analysis.smooth(spike, "median", 3).max() == 0
    g, f = analysis.resample(w, w, 2.5)
    assert np.allclose(np.diff(g), 2.5) and np.allclose(f, g)
    cont = analysis.continuum_from_points(w, 2 + 0.001 * (w - 4000), [4010, 4300, 4600, 4990])
    assert np.allclose(cont, 2 + 0.001 * (w - 4000), atol=1e-3)


def test_instrument_response_recovers_known_sensitivity():
    w = np.arange(3900.0, 7200.0, 1.0)
    star = (w / 5000) ** -3 * (1 - 0.7 * np.exp(-0.5 * ((w - 4861.3) / 5) ** 2))  # reference star with Hβ
    sens = np.exp(-0.5 * ((w - 5600) / 900) ** 2)  # camera + grating response
    obs = star * sens * 3000
    resp = analysis.response(w, obs, w, star)
    calibrated = obs / resp
    ratio = calibrated / star
    assert np.std(ratio[(w > 4200) & (w < 6800)]) / np.mean(ratio) < 0.01


def test_bess_export(tmp_path):
    w = np.linspace(6500, 6600, 401) + np.random.default_rng(0).normal(0, 0.01, 401)
    path = analysis.write_bess(
        tmp_path / "b.fits",
        w,
        np.ones(401),
        {"object": "gam Cas", "observer": "X", "date_obs": "2026-11-02T20:00:00", "exptime": 600, "telluric": 1},
    )
    h = fits.getheader(path)
    for key in ("OBJNAME", "OBSERVER", "DATE-OBS", "EXPTIME", "BSS_INST", "BSS_SITE", "BSS_VHEL", "BSS_TELL"):
        assert key in h
    assert h["CTYPE1"] == "Wavelength" and h["CUNIT1"] == "Angstrom" and h["BSS_TELL"] == 1
    wave, flux, _, _ = spectrum_io.read(path)  # readable by the application's own reader
    assert abs(wave[0] - w.min()) < 1e-6 and np.allclose(flux, 1)


def test_spectrum_tools_tab(qtbot, tmp_path):
    from astrowb.ui.spectrum_tools import SpectrumToolsTab

    tab = SpectrumToolsTab()
    qtbot.addWidget(tab)
    w = np.arange(6400.0, 6700.0, 0.5)
    sens = 1 + 0.002 * (w - 6400)
    emission = 1 + 1.2 * np.exp(-0.5 * ((w - 6559.8) / 1.5) ** 2) + 0.8 * np.exp(-0.5 * ((w - 6565.8) / 1.5) ** 2)
    header = fits.Header({"DATE-OBS": "2026-11-02T20:00:00", "OBJECT": "gam Cas", "EXPTIME": 300})
    star = spectrum_io.write(tmp_path / "s.fits", w, 500 * sens * emission, np.zeros(w.size), header)
    ref = spectrum_io.write(tmp_path / "ref.fits", w, np.ones(w.size), np.zeros(w.size))
    assert tab._open(star)
    tab.markers.setChecked(True)  # draws the line markers
    tab.lo.setValue(6545)
    tab.hi.setValue(6580)
    m = tab._measure()
    assert m["ew"] < 0 and tab.table.rowCount() == 1
    tab._normalise()
    vr = tab._vr()
    assert abs(vr["v_over_r"] - 1.5) < 0.1
    tab._undo()
    assert tab.flux.max() > 100
    tab.compute_response(ref)  # the "reference star" is flat: the response is the sensitivity slope
    tab._apply_response()
    edges = tab.flux[(w < 6500) | (w > 6620)]
    assert np.std(edges) / np.mean(edges) < 0.01
    tab.constant.setText("2")
    tab.op.setCurrentText("×")
    before = tab.flux.copy()
    tab._arith()
    assert np.allclose(tab.flux, 2 * before)
    tab._smooth()
    tab.points = [6420, 6500, 6620, 6690]
    tab._normalise_points()
    assert abs(np.median(tab.flux) - 1) < 0.02
    rows = tab.measure_series([star, star])
    assert len(rows) == 2 and rows[0][0].startswith("2026-11-02") and tab.table.rowCount() == 3
    out = tab._bess(str(tmp_path / "b.fits"), {"object": "gam Cas"})
    assert fits.getheader(out)["OBJNAME"] == "gam Cas"
    assert spectrum_io.read(tab._save(str(tmp_path / "saved.fits")))[0].size == w.size
