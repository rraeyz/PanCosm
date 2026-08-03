"""Spectroscopy on a synthetic long-slit observation with known truth, plus RV and orbit checks."""

import warnings

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from astrowb.spectroscopy import longslit, orbit, rv, wavecal

NX, NY = 1400, 80
C = 299792.458
V_TRUE = 45.0  # km/s
ABS_LINES = [4101.7, 4340.5, 4383.5, 4861.3, 5167.3, 5172.7, 5183.6, 5270.4, 5328.0, 5889.95, 5895.9, 6562.8]


def dispersion(x):
    return 4000.0 + 1.75 * x + 1.5e-5 * x**2  # Angstrom; ~1 % non-linear, typical of a grating


def trace_y(x):
    return 40.0 + 4e-3 * (x - 700) + 3e-6 * (x - 700) ** 2


def star_spectrum(wave, v=0.0):
    f = np.ones_like(wave)
    for line in ABS_LINES:
        lam = line * (1 + v / C)
        f -= 0.5 * np.exp(-0.5 * ((wave - lam) / 1.2) ** 2)
    return f


@pytest.fixture(scope="module")
def frames():
    rng = np.random.default_rng(11)
    x = np.arange(NX)
    y = np.arange(NY)[:, None]
    wave = dispersion(x)
    prof = np.exp(-0.5 * ((y - trace_y(x)[None, :]) / 2.0) ** 2)
    prof /= prof.sum(axis=0, keepdims=True)
    true_flux = 20000.0 * star_spectrum(wave, V_TRUE) * (1 + 0.2 * np.sin(x / 300))
    sky = 40.0 + 300 * np.exp(-0.5 * ((wave - 5577.3) / 1.5) ** 2) + 200 * np.exp(-0.5 * ((wave - 6300.3) / 1.5) ** 2)
    model = prof * true_flux[None, :] + sky[None, :]
    gain, rn = 1.5, 4.0
    obj = rng.poisson(model * gain) / gain + rng.normal(0, rn / gain, model.shape)
    obj[int(trace_y(900)), 900] += 4000  # cosmic ray on the spectrum
    henear = wavecal.load_line_list("henear")
    lines = henear[(henear > wave[0] + 5) & (henear < wave[-1] - 5)]
    arc1d = np.zeros(NX)
    for lam in lines:
        px = np.interp(lam, wave, x)
        arc1d += 5000 * np.exp(-0.5 * ((x - px) / 1.3) ** 2)
    arc = np.tile(arc1d, (NY, 1)) + rng.normal(0, 3, (NY, NX)) + 100
    return {"obj": obj, "arc": arc, "true_flux": true_flux, "wave": wave, "gain": gain, "rn": rn, "lines": lines}


def test_trace(frames):
    coef = longslit.trace(frames["obj"])
    x = np.arange(NX)
    assert np.max(np.abs(np.polyval(coef, x) - trace_y(x))) < 0.1


def test_curved_traces_of_two_orders_are_followed():
    """LCO FLOYDS: two orders on one frame, each bending by ~200 rows. A fixed window around one row lost the
    trace (it was extracted from the sky); now it is followed step by step (IRAF aptrace), the brightest by default
    and the other from a row the user gives."""
    rng = np.random.default_rng(2)
    ny, nx = 512, 2048
    yy, xx = np.mgrid[:ny, :nx]
    red = 95 + 0.8e-4 * (xx[0] - 350) ** 2  # rises to ~325 at the right edge, below the other order
    blue = 385 + 1.2e-4 * (xx[0] - 1150) ** 2
    img = rng.normal(0, 5, (ny, nx))
    img += 3000 * np.exp(-0.5 * ((yy - red) / 2.0) ** 2) * (red < ny)
    img += 800 * np.exp(-0.5 * ((yy - blue) / 2.0) ** 2) * (xx > 400)  # the fainter order starts at x 400
    x = np.arange(400, 1700)
    assert np.max(np.abs(np.polyval(longslit.trace(img), x) - red[400:1700])) < 1.0
    coef = longslit.trace(img, guess_row=400)
    assert np.max(np.abs(np.polyval(coef, x[200:]) - blue[600:1700])) < 1.0


def test_boxcar_and_optimal_extraction(frames):
    coef = longslit.trace(frames["obj"])
    box, _ = longslit.boxcar(frames["obj"], coef, width=14, sky_offset=14, sky_width=12)
    opt, err, _, rejected = longslit.optimal(frames["obj"], coef, 14, 14, 12, frames["gain"], frames["rn"])
    truth = frames["true_flux"]
    sel = np.r_[50:880, 920:1350]  # away from the cosmic ray and the ends
    assert abs(np.median(box[sel] / truth[sel]) - 1) < 0.01
    assert abs(np.median(opt[sel] / truth[sel]) - 1) < 0.01
    assert np.std((opt - truth)[sel]) < np.std((box - truth)[sel])  # optimal is less noisy
    assert 0.8 < np.median(np.abs(opt - truth)[sel] / err[sel]) / 0.6745 < 1.3  # errors honest
    assert rejected[:, 900].any() and abs(opt[900] / truth[900] - 1) < 0.05  # cosmic ray removed


def test_boxcar_matches_specreduce(frames):
    specreduce = pytest.importorskip("specreduce")
    from specreduce.extract import BoxcarExtract
    from specreduce.tracing import ArrayTrace

    coef = longslit.trace(frames["obj"])
    img = frames["obj"] - np.median(frames["obj"][:10])  # no sky step in either
    ours = np.sum(np.where(np.abs(np.arange(NY)[:, None] - np.polyval(coef, np.arange(NX))) <= 7, img, 0), axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        theirs = BoxcarExtract(img, ArrayTrace(img, np.polyval(coef, np.arange(NX))), width=15)().flux.value
    assert specreduce and np.median(np.abs(ours / theirs - 1)) < 0.02  # whole-pixel vs fractional-pixel edges


def test_wavelength_solution(frames):
    coef = longslit.trace(frames["obj"])
    arc1d, _ = longslit.boxcar(frames["arc"], coef, width=6, subtract_sky=False)
    peaks = wavecal.find_lines(arc1d)
    x = np.arange(NX)
    lines = frames["lines"]
    guesses = [(np.interp(lam, frames["wave"], x), lam) for lam in (lines[1], lines[-2])]  # user marks two lines
    sol = wavecal.solve(peaks, wavecal.load_line_list("henear"), guesses, order=3)
    assert sol.n_lines >= 0.7 * len(lines) and sol.rms < 0.05
    assert np.max(np.abs(sol(x[20:-20]) - frames["wave"][20:-20])) < 0.05


def test_ccf_rv_and_error(frames):
    wave = frames["wave"]
    tmpl_wave = np.linspace(3900, 7200, 40000)
    tmpl = star_spectrum(tmpl_wave)
    rng = np.random.default_rng(3)
    rvs, errs = [], []
    clean = star_spectrum(wave, V_TRUE)
    for _ in range(60):
        obs = clean + rng.normal(0, 0.02, wave.size)
        r = rv.ccf(wave, obs, tmpl_wave, tmpl, -200, 200)
        rvs.append(r["rv"])
        errs.append(r["rv_err"])
    rvs = np.array(rvs)
    assert abs(rvs.mean() - V_TRUE) < 3 * rvs.std() / np.sqrt(len(rvs)) + 0.3
    assert 0.6 < np.median(errs) / rvs.std() < 1.7  # Zucker error vs Monte Carlo scatter


def test_continuum_normalise():
    w = np.linspace(4000, 6000, 3000)
    f = (1 + 0.3 * (w - 5000) / 1000) * star_spectrum(w)
    n = rv.continuum_normalise(w, f)
    assert abs(np.median(n) - 1) < 0.01 and n.min() < 0.6


def test_barycentric_correction_physics():
    loc = EarthLocation.from_geodetic(30.34 * u.deg, 36.82 * u.deg, 2500 * u.m)
    star = SkyCoord(270 * u.deg, 66.56 * u.deg)  # north ecliptic pole: Earth's orbital motion is perpendicular
    eclip = SkyCoord(lon=90 * u.deg, lat=0 * u.deg, frame="barycentrictrueecliptic").icrs
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pole = rv.barycentric_correction(Time("2026-03-20T22:00:00"), star, loc)
        a = rv.barycentric_correction(Time("2026-03-20T22:00:00"), eclip, loc)
        b = rv.barycentric_correction(Time("2026-09-22T22:00:00"), eclip, loc)
    assert abs(pole) < 1.0  # only Earth's rotation and the barycentre wobble
    assert 28 < abs(a) < 31 and abs(a + b) < 1.5  # ~29.8 km/s, sign flips after half a year
    assert abs(rv.to_barycentric(10.0, 20.0) - (30.0 + 200 / C)) < 1e-12


def test_orbit_fit_recovers_parameters():
    rng = np.random.default_rng(5)
    truth = dict(period=3.4567, t_peri=2460000.37, e=0.31, omega_deg=118.0, k=42.0, gamma=-12.0)
    t = 2460000 + np.sort(rng.uniform(0, 60, 40))
    v = orbit.rv_model(t, **truth) + rng.normal(0, 1.0, t.size)
    fit = orbit.fit_orbit(t, v, np.full(t.size, 1.0), period=3.45)
    for key, tk in (("period", "period"), ("e", "e"), ("omega", "omega_deg"), ("k", "k"), ("gamma", "gamma")):
        assert abs(fit[key] - truth[tk]) < 4 * fit[f"{key}_err"], key
    assert 0.6 < fit["chi2r"] < 1.6
    # mass function from its definition: P K^3 (1-e^2)^1.5 / (2 pi G)
    fm = 3.4567 * 86400 * 42e3**3 * (1 - 0.31**2) ** 1.5 / (2 * np.pi * 6.6743e-11) / 1.98847e30
    assert abs(fit["mass_function"] / fm - 1) < 0.1


def test_kepler_equation():
    m = np.linspace(0, 2 * np.pi, 50)
    for e in (0.0, 0.5, 0.95):
        ecc = orbit.eccentric_anomaly(m, e)
        np.testing.assert_allclose(ecc - e * np.sin(ecc), m % (2 * np.pi), atol=1e-10)


def test_reduce_rv_orbit_steps(frames, tmp_path):
    from astropy.io import fits

    from astrowb.engine import steps
    from astrowb.spectroscopy import spectrum_io

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    h = fits.Header(
        {
            "DATE-OBS": "2026-11-15T22:00:00",
            "EXPTIME": 600.0,
            "OBJCTRA": "02 04 10.3",
            "OBJCTDEC": "+46 41 16",
            "GAIN": frames["gain"],
        }
    )
    fits.PrimaryHDU(frames["obj"].astype(np.float32), h).writeto(tmp_path / "sci.fits")
    fits.PrimaryHDU(frames["arc"].astype(np.float32)).writeto(tmp_path / "arc.fits")
    x = np.arange(NX)
    lines = frames["lines"]
    guesses = [[float(np.interp(lam, frames["wave"], x)), float(lam)] for lam in (lines[1], lines[-2])]
    out = steps.execute(
        "spectroscopy.reduce",
        {
            "science": str(tmp_path / "sci.fits"),
            "arc": str(tmp_path / "arc.fits"),
            "guesses": guesses,
            "output": str(tmp_path / "sci_1d.fits"),
        },
        {"read_noise": frames["rn"]},
        Ctx(),
    )
    spec = out["spectrum"]
    assert spec["solution"]["rms"] < 0.05 and spec["path"].endswith("sci_1d.fits")
    w, f, e, hdr = spectrum_io.read(spec["path"])
    assert hdr["DATE-OBS"] == "2026-11-15T22:00:00" and abs(w[700] - frames["wave"][700]) < 0.05
    tw = np.linspace(3900, 7200, 40000)
    spectrum_io.write(tmp_path / "template.fits", tw, star_spectrum(tw), np.zeros_like(tw))
    site = {"name": "", "lat": 36.82, "lon": 30.34, "height": 2500.0}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = steps.execute(
            "spectroscopy.rv",
            {"spectra": [spec["path"]], "template": str(tmp_path / "template.fits"), "site": site},
            {"v_min": -200, "v_max": 200},
            Ctx(),
        )["rvs"][0]
    assert abs(r["rv_obs"] - V_TRUE) < 3 * r["rv_err"] + 0.5
    assert r["v_corr"] is not None and abs(r["rv"] - (r["rv_obs"] + r["v_corr"])) < 0.01
    with fits.open(spec["path"], mode="update") as hdul:  # the site in the spectrum's own header (TOFES)
        hdul[0].header["LATITUDE"], hdul[0].header["LONGITUD"] = 36.82, (30.34, "[deg] Longitude (E+)")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        own = steps.execute(
            "spectroscopy.rv",
            {"spectra": [spec["path"]], "template": str(tmp_path / "template.fits")},
            {"v_min": -200, "v_max": 200},
            Ctx(),
        )["rvs"][0]
    assert own["v_corr"] == pytest.approx(r["v_corr"], abs=0.01)  # it was 'not applied' without the Plan page
    assert own["site"]["from"] == "header" and r["site"]["from"] == "plan"  # shown with the velocities
    with pytest.raises(ValueError, match="period guess"):
        steps.execute("spectroscopy.orbit", {"time": [1, 2, 3], "rv": [1, 2, 3]}, {}, Ctx())


def test_read_1d_image_with_wcs(tmp_path):
    from astropy.io import fits

    from astrowb.spectroscopy import spectrum_io

    fits.PrimaryHDU(np.arange(100.0), fits.Header({"CRVAL1": 6500.0, "CDELT1": 0.5, "CRPIX1": 1.0})).writeto(
        tmp_path / "isis.fits"
    )
    w, f, e, _ = spectrum_io.read(tmp_path / "isis.fits")
    assert w[0] == 6500.0 and w[-1] == 6549.5 and e is None
    np.savetxt(tmp_path / "s.dat", np.column_stack([w, f]))
    w2, f2, _, _ = spectrum_io.read(tmp_path / "s.dat")
    np.testing.assert_allclose(w2, w)


def test_spectroscopy_page_end_to_end(frames, tmp_path, qtbot):
    from astropy.io import fits
    from PySide6.QtWidgets import QTableWidgetItem

    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    h = fits.Header(
        {
            "DATE-OBS": "2026-11-15T22:00:00",
            "EXPTIME": 600.0,
            "OBJCTRA": "02 04 10.3",
            "OBJCTDEC": "+46 41 16",
            "GAIN": frames["gain"],
        }
    )
    fits.PrimaryHDU(frames["obj"].astype(np.float32), h).writeto(tmp_path / "sci.fits")
    fits.PrimaryHDU(frames["arc"].astype(np.float32)).writeto(tmp_path / "arc.fits")
    settings = Settings(tmp_path / "cfg")
    settings.set("site", {"name": "", "lat": 36.82, "lon": 30.34, "height": 2500.0})
    win = MainWindow(settings)
    qtbot.addWidget(win)
    try:
        tab = win.spectro_page.reduce_tab
        tab.science.edit.setText(str(tmp_path / "sci.fits"))
        tab.arc.edit.setText(str(tmp_path / "arc.fits"))
        tab.extract_button.click()
        qtbot.waitUntil(lambda: tab.result is not None, timeout=60000)
        assert len(tab.result["arc_peaks"]) > 10
        x = np.arange(NX)
        for lam in (frames["lines"][1], frames["lines"][-2]):  # what clicking a line + typing does
            r = tab.guesses.rowCount()
            tab.guesses.insertRow(r)
            px = min(tab.result["arc_peaks"], key=lambda p: abs(p - np.interp(lam, frames["wave"], x)))
            for c, v in enumerate((f"{px:.2f}", f"{lam}")):
                tab.guesses.setItem(r, c, QTableWidgetItem(v))
        tab.solve_button.click()
        qtbot.waitUntil(lambda: tab.result.get("path") is not None, timeout=60000)
        assert tab.result["solution"]["rms"] < 0.05
        vt = win.spectro_page.velocity_tab
        assert vt.files.count() == 1  # the saved spectrum is queued for radial velocities
        tw = np.linspace(3900, 7200, 40000)
        from astrowb.spectroscopy import spectrum_io

        spectrum_io.write(tmp_path / "tmpl.fits", tw, star_spectrum(tw), np.zeros_like(tw))
        vt.template.edit.setText(str(tmp_path / "tmpl.fits"))
        vt.v_min.setValue(-200)
        vt.v_max.setValue(200)
        vt.rv_button.click()
        qtbot.waitUntil(lambda: bool(vt.rvs), timeout=60000)
        assert abs(vt.rvs[0]["rv_obs"] - V_TRUE) < 2 and vt.rvs[0]["v_corr"] is not None
    finally:
        win.engine.shutdown()
