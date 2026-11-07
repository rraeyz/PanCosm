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


def test_a_merged_echelle_spectrum_is_normalised_in_pieces():
    # 1500 A of HARPS at 0.012 A per pixel whose first order fades out at the blue end: one clipped cubic over all of
    # it lost the faint end and went through zero there (normalised flux -13000 ... +3800), the CCF of a real
    # spectrum against ESO's own fell to 0.009 and its velocity 5.6 km/s off
    rng = np.random.default_rng(3)
    wave = np.exp(np.arange(np.log(3780.0), np.log(5300.0), np.log(1 + 0.012 / 4500)))
    lines, depth = rng.uniform(3790, 5290, 1500), rng.uniform(0.1, 0.7, 1500)

    def star(w):
        f = np.ones_like(w)
        for c, d in zip(lines, depth, strict=True):
            lo, hi = np.searchsorted(w, [c - 0.3, c + 0.3])
            f[lo:hi] -= d * np.exp(-0.5 * ((w[lo:hi] - c) / 0.04) ** 2)
        return f

    v = 12.3
    cont = 0.03 + 0.97 / (1 + np.exp(-(wave - 3880) / 15.0)) * (wave / 3800) ** 3
    f = star(wave / (1 + v / rv.C_KMS)) * cont + rng.normal(0, 0.002, len(wave))
    r = rv.ccf(wave, rv.continuum_normalise(wave, f), wave, star(wave), -50, 50)
    assert r["rv"] == pytest.approx(v, abs=0.02) and r["peak"] > 0.9  # 0.41 with one cubic


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
    # an already-extracted 1-D spectrum and arc: wavelengths only (IRAF identify on apall output)
    fits.PrimaryHDU(np.asarray(spec["flux"], np.float32), h).writeto(tmp_path / "sci.ms.fits")
    fits.PrimaryHDU(np.asarray(spec["arc"], np.float32)).writeto(tmp_path / "arc.ms.fits")
    one = steps.execute(
        "spectroscopy.reduce",
        {"science": str(tmp_path / "sci.ms.fits"), "arc": str(tmp_path / "arc.ms.fits"), "guesses": guesses},
        {},
        Ctx(),
    )["spectrum"]
    assert one["trace"] is None and np.allclose(one["solution"]["coef"], spec["solution"]["coef"], rtol=1e-6)
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


def test_eso_archive_spectrum_already_barycentric(tmp_path):
    # ESO Phase 3 spectra (HARPS, UVES, FEROS): one table row whose cells are whole arrays, ERR, SPECSYS =
    # 'BARYCENT' and the site in ESO TEL GEO*. Six real HARPS spectra of tau Ceti read as 1 x N arrays, and
    # correcting them again would have put a constant star up to 27 km/s off
    from astropy.io import fits

    from astrowb.engine import steps
    from astrowb.spectroscopy import spectrum_io

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    tw = np.linspace(3900, 7200, 40000)
    spectrum_io.write(tmp_path / "template.fits", tw, star_spectrum(tw), np.zeros_like(tw))
    w = np.linspace(4000, 7000, 30000)
    h = fits.Header({"DATE-OBS": "2009-01-16T01:12:48", "EXPTIME": 300.0, "RA": 26.01824, "DEC": -15.93568})
    h["HIERARCH ESO TEL GEOLAT"], h["HIERARCH ESO TEL GEOLON"], h["HIERARCH ESO TEL GEOELEV"] = (
        -29.2584,
        -70.7345,
        2400.0,
    )
    h["SPECSYS"] = "BARYCENT"
    cols = [
        fits.Column(name=n, format=f"{w.size}D", array=a[None, :])
        for n, a in (("WAVE", w), ("FLUX", star_spectrum(w, -16.7)), ("ERR", np.full(w.size, 0.01)))
    ]
    fits.HDUList([fits.PrimaryHDU(header=h), fits.BinTableHDU.from_columns(cols, name="SPECTRUM")]).writeto(
        tmp_path / "eso.fits"
    )
    wave, flux, err, hdr = spectrum_io.read(tmp_path / "eso.fits")
    assert wave.shape == flux.shape == err.shape == (w.size,) and hdr["SPECSYS"] == "BARYCENT"

    def measure():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return steps.execute(
                "spectroscopy.rv",
                {"spectra": [str(tmp_path / "eso.fits")], "template": str(tmp_path / "template.fits")},
                {"v_min": -100, "v_max": 100},
                Ctx(),
            )["rvs"][0]

    r = measure()
    assert r["already_barycentric"] and r["v_corr"] == 0.0 and r["rv"] == r["rv_obs"]
    assert r["rv"] == pytest.approx(-16.7, abs=0.5) and r["bjd"] is not None
    with fits.open(tmp_path / "eso.fits", mode="update") as hdul:  # a topocentric ESO spectrum: corrected
        del hdul[0].header["SPECSYS"]
    r = measure()
    assert r["site"]["from"] == "header" and r["site"]["lat"] == pytest.approx(-29.2584)
    assert abs(r["v_corr"]) > 1 and r["rv"] == pytest.approx(r["rv_obs"] + r["v_corr"], abs=0.05)


def test_fine_template_is_matched_to_a_low_resolution_spectrum():
    # LAMOST (R 1800, 1 A pixels) against the Kurucz solar atlas (0.007 A): sampled at the coarse pixels the sharp
    # template aliased and real stars came out 30-60 km/s off; matched to the resolution they agree with LAMOST
    from scipy.ndimage import gaussian_filter1d

    rng = np.random.default_rng(3)
    tw = np.exp(np.arange(np.log(4800), np.log(6900), 1.2e-6))  # 0.36 km/s steps
    tf = np.ones_like(tw)
    for lam, depth in zip(rng.uniform(4850, 6850, 1500), rng.uniform(0.05, 0.6, 1500), strict=True):
        tf -= depth * np.exp(-0.5 * ((tw - lam) / 0.04) ** 2)
    tf = np.clip(tf, 0.02, None)
    v = -40.0
    ln_obs = np.arange(np.log(4900), np.log(6800), 1e-4 * np.log(10))  # LAMOST's log10 step 1e-4
    smooth = gaussian_filter1d(tf, 2.5 * 1e-4 * np.log(10) / 2.3548 / 1.2e-6)
    obs = np.interp(ln_obs - np.log1p(v / C), np.log(tw), smooth) + rng.normal(0, 0.01, ln_obs.size)
    w = np.exp(ln_obs)
    mw, mf = rv.match_template(w, tw, tf)
    assert mw.size < tw.size * 1.01 and np.std(mf) < np.std(tf)  # smoothed
    got = rv.ccf(w, obs, mw, mf, -300, 300)
    assert got["rv"] == pytest.approx(v, abs=2.0)
    same = rv.match_template(tw[::2], tw, tf)  # a template not much finer (HARPS against the atlas) is left as it is
    assert same[0] is tw and same[1] is tf


def test_velocity_tab_says_what_was_done_for_the_user(qtbot):
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    row = {"file": "a.fits", "bjd": 2455859.0, "rv_obs": -39.3, "rv_err": 8.5, "rv": -39.3, "v_corr": 0.0}
    tab.show_rvs([row | {"already_barycentric": True, "template_matched": True, "vacuum_to_air": True}])
    text = tab.status.text()
    assert (
        "already barycentric" in text and "smoothed to the spectra's resolution" in text and "converted to air" in text
    )
    tab.show_rvs([row])
    assert "smoothed" not in tab.status.text() and "air" not in tab.status.text()


def test_mk_suggestion_is_drawn_and_survives_without_the_template_library(qtbot):
    # the Pickles download failed (SSL in a container) and took the MK type down with it; now the MK type is
    # shown, the star drawn over the best standard, and the user told to choose a template
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    wave = np.linspace(3800, 5600, 500)
    model = {"wave": wave.tolist(), "star": np.ones(500).tolist(), "model": np.r_[np.zeros(10), np.ones(490)].tolist()}
    tab.show_classes([], [{"type": "G0 V", "score": 0.05}], None, model, "SSL: CERTIFICATE_VERIFY_FAILED")
    assert "G0 V" in tab.status.text() and "choose a template yourself" in tab.status.text()
    ax = tab.plot.figure.axes[0]
    assert len(ax.lines) == 2 and np.isnan(ax.lines[1].get_ydata()[:10]).all()  # no fake drop where it has no data


def test_bess_amateur_spectra(tmp_path):
    # 30 real ARAS spectra of AG Dra (eShel, Alpy 600, LISA, LHIRES III, UVEX, StarEx): BSS_VHEL = the heliocentric
    # correction already applied; the site in GEO_LAT / GEO_LONG (0, 0 = unknown); one spectrum outside the chosen
    # wavelengths stopped the whole batch
    from astropy.io import fits

    from astrowb import timing
    from astrowb.engine import steps
    from astrowb.spectroscopy import spectrum_io

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    tw = np.linspace(3900, 7200, 40000)
    spectrum_io.write(tmp_path / "template.fits", tw, star_spectrum(tw), np.zeros_like(tw))

    def bess(name, start, vhel, lat, lon):
        h = fits.Header({"CRVAL1": start, "CDELT1": 0.5, "CRPIX1": 1.0, "CTYPE1": "Wavelength", "CUNIT1": "Angstrom"})
        h["DATE-OBS"], h["JD-MID"], h["BSS_VHEL"] = "2026-10-07T20:10:21", 2461321.3685, vhel
        h["GEO_LAT"], h["GEO_LONG"], h["GEO_ELEV"] = lat, lon, 318
        w = start + 0.5 * np.arange(4000)
        fits.PrimaryHDU(star_spectrum(w, -150.0), h).writeto(tmp_path / name)
        return str(tmp_path / name)

    corrected = bess("a.fit", 4000.0, -0.639, 41.7203, 1.1063)
    raw = bess("b.fit", 4000.0, 0.0, 41.7203, 1.1063)
    unknown = bess("c.fit", 4000.0, 0.0, 0.0, 0.0)
    red = bess("d.fit", 6600.0, 0.0, 41.7203, 1.1063)  # 6600-8600 A only
    assert timing.location(fits.getheader(raw)).lat.deg == pytest.approx(41.7203)
    assert timing.location(fits.getheader(unknown)) is None  # 0, 0 is not a site
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = steps.execute(
            "spectroscopy.rv",
            {
                "spectra": [corrected, raw, unknown, red],
                "template": str(tmp_path / "template.fits"),
                "coord": "16 01 40.96 +66 48 10.1",
            },
            {"v_min": -400, "v_max": 100, "wave_min": 5000, "wave_max": 5800},
            Ctx(),
        )
    rows = {r["file"]: r for r in out["rvs"]}
    assert [k["file"] for k in out["skipped"]] == ["d.fit"]
    assert rows["a.fit"]["already_barycentric"] and rows["a.fit"]["v_corr"] == 0.0
    assert rows["b.fit"]["site"]["from"] == "header" and rows["b.fit"]["v_corr"] != 0.0
    assert rows["c.fit"]["v_corr"] is None  # unknown site: not corrected, the page asks for the Plan page's site
    assert (
        rows["a.fit"]["rv"] == pytest.approx(-150.0, abs=3)
        and rows["a.fit"]["rv_err"] >= rows["a.fit"]["rv_err_formal"]
    )


def test_chunk_error_reflects_disagreeing_parts():
    rng = np.random.default_rng(5)
    centres = rng.uniform(5000, 5800, 300)

    def lines(wave, v):
        f = np.ones_like(wave)
        for c in centres:
            f -= 0.4 * np.exp(-0.5 * ((wave - c * (1 + v / C)) / 0.3) ** 2)
        return f

    w = np.exp(np.linspace(np.log(5000), np.log(5800), 16000))
    obs = np.where(w < 5400, lines(w, -150.0), lines(w, -120.0))  # two halves 30 km/s apart
    assert rv.chunk_error(w, obs, w, lines(w, 0.0), -400, 100) > 5
    assert rv.chunk_error(w, lines(w, -150.0), w, lines(w, 0.0), -400, 100) < 0.5  # agreeing parts: small


def test_emission_lines_are_masked_against_an_absorption_template():
    rng = np.random.default_rng(8)
    w = np.linspace(5000, 5800, 4000)
    t = star_spectrum(w)
    obs = star_spectrum(w) + rng.normal(0, 0.005, w.size)
    obs += 0.8 * np.exp(-0.5 * ((w - 5411.5) / 1.5) ** 2)  # He II 5411 in emission (symbiotic star)
    masked, n = rv.mask_emission(obs, t)
    assert n > 5 and masked[np.argmin(np.abs(w - 5411.5))] == 1.0
    _, n_emission_template = rv.mask_emission(obs, obs)  # the template itself in emission: nothing masked
    assert n_emission_template == 0


def test_wavelength_solution_degree_chosen_by_the_lines():
    # EFOSC2 grism 11 (real ESO night): nine identified He-Ar lines need a quartic (0.2 A rms; the solver allowed
    # only a quadratic, 1-3 A); blended catalogue lines at 4 A per pixel must not be matched as single lines
    def disp(p):
        return 3041 + 4.41 * p - 2.3e-4 * p**2 + 1.6e-7 * p**3 - 8e-11 * p**4

    rng = np.random.default_rng(2)
    lines = np.sort(rng.uniform(3200, 7400, 40))
    blend = lines[5] + 1.5  # a neighbour too close to tell apart at this resolution
    px = np.linspace(0, 1030, 4001)
    peaks = np.array([px[np.argmin(np.abs(disp(px) - lam))] for lam in lines])
    guesses = [[peaks[i], lines[i]] for i in range(0, 40, 4)]
    sol = wavecal.solve(peaks, np.r_[lines, blend], guesses, order=5)
    assert sol.degree == 4 and sol.rms < 0.3
    flat = wavecal.solve(peaks, 3000 + 4.4 * peaks, [[p, 3000 + 4.4 * p] for p in peaks[::4]], order=5)
    assert flat.degree == 1


def test_zero_point_from_night_sky_lines():
    # EFOSC2, 45 min: [O I] 5577 and 6300 both -6.95 A off (flexure since the arc); an 80 s exposure: too weak
    rng = np.random.default_rng(6)
    w = np.linspace(4000, 7400, 1400)

    def sky(amplitude, shift):
        s = np.full(w.size, 100.0)
        for line, a in zip(wavecal.SKY_LINES, amplitude, strict=True):
            s += a * np.exp(-0.5 * ((w - line - shift) / 5.0) ** 2)
        return s + rng.normal(0, 1.0, w.size)

    shift, lines = wavecal.sky_shift(w, sky((60, 25, 9), -6.95))
    assert shift == pytest.approx(-6.95, abs=0.4) and len(lines) >= 2
    weak, _ = wavecal.sky_shift(w, sky((7, 2, 1), -6.95))
    assert weak is None  # one weak line does not move the zero point


def test_reduce_tab_reports_the_sky_zero_point(qtbot):
    from astrowb.ui.spectro_page import ReduceTab

    tab = ReduceTab()
    qtbot.addWidget(tab)
    assert tab.sky_lines.isChecked() and tab.state()["sky_lines"]
    assert "-6.95" not in tab._sky_text({"shift": None, "lines": []}) and "kept" in tab._sky_text(
        {"shift": None, "lines": []}
    )
    assert "+6.95 Å" in tab._sky_text(
        {"shift": -6.95, "lines": [[5577.338, -6.94, 0.1, 46], [6300.304, -6.96, 0.1, 21]]}
    )


def test_faint_spectrum_traced_with_a_brighter_ones_shape():
    # as IRAF apall's reference aperture: a curved bright trace, a faint spectrum 60 rows away
    rng = np.random.default_rng(4)
    ny, nx = 200, 600
    x = np.arange(nx)
    yb = 60 + 15 * ((x - 300) / 300) ** 2
    yy = np.arange(ny)[:, None]
    img = 2000 * np.exp(-0.5 * ((yy - yb) / 2.0) ** 2) + 5 * np.exp(-0.5 * ((yy - (yb + 60)) / 2.0) ** 2)
    img = img + rng.normal(0, 4, (ny, nx))
    with pytest.raises(ValueError, match="brighter spectrum's row"):
        longslit.trace(img, guess_row=120, nlost=1)
    coef = longslit.shifted_trace(img, longslit.trace(img, 60), 120)
    assert np.allclose(np.polyval(coef, x), yb + 60, atol=0.5)


def test_low_resolution_xenon_arc_lines_cover_part_of_the_detector():
    # LT SPRAT (real night): Xe lines only on pixels ~240-990 of 1024, dispersion 4.05-4.67 A/px. Before: two
    # identified lines 630 px apart, a straight first guess 30 A off in the middle, misnamed lines, and a quintic
    # between them that gave -1435 A at pixel 0
    def disp(p):
        q = p - 50.0
        return 3682.83 + 4.12888 * q + 7.5648e-4 * q**2 - 1.06264e-7 * q**3 - 1.69725e-10 * q**4

    catalogue = wavecal.load_line_list("xenon")
    px = np.linspace(0, 1023, 20001)
    seen = [4500.98, 4524.68, 4582.75, 4624.28, 4671.23, 4697.02, 4734.15, 4807.02, 5028.28, 5823.89, 5934.17, 6182.42]
    seen += [6318.06, 6472.84, 6595.56, 6728.01, 6827.32, 6976.18, 7119.60, 7393.8, 7584.68, 7642.02, 7802.65, 7887.40]
    lines = np.array(seen + [7967.34])  # the lines a SPRAT arc shows (ASPIRED's atlas for it)
    rng = np.random.default_rng(3)
    peaks = np.array([px[np.argmin(np.abs(disp(px) - lam))] for lam in lines]) + rng.normal(0, 0.15, lines.size)
    keep = np.r_[True, np.diff(peaks) > 3]  # lines closer than the resolution are one peak
    peaks, lines = peaks[keep], lines[keep]
    g = [[peaks[np.argmin(np.abs(lines - w))], w] for w in (4671.226, 7642.024)]
    sol = wavecal.solve(peaks, catalogue, g, order=5, n_pixels=1024)
    x = np.arange(1024)
    inside = (x >= peaks.min()) & (x <= peaks.max())
    assert np.max(np.abs(sol(x) - disp(x))[inside]) < 2 and sol.n_lines >= 15 and sol.rms < 1.5
    assert np.max(np.abs(sol(x) - disp(x))) < 20  # 240 px beyond the last line: a dispersion still


def test_arc_lines_on_a_blended_background_and_the_faintest_left_out():
    # a low-resolution arc is blended lines from end to end: the scatter about its median is no noise level
    x = np.arange(1024, dtype=float)
    rng = np.random.default_rng(5)
    centres = np.arange(40, 1000, 23.0)
    heights = np.where(np.arange(centres.size) % 3 == 0, 2e4, 2e3)
    arc = 3000 * np.exp(-0.5 * ((x - 512) / 250) ** 2) + rng.normal(0, 20, x.size)
    for c, h in zip(centres, heights, strict=True):
        arc += h * np.exp(-0.5 * ((x - c) / 1.7) ** 2)
    arc += 60 * np.exp(-0.5 * ((x - 1010) / 1.7) ** 2)  # 1/300 of the strongest: not in a lamp's list
    found = wavecal.find_lines(arc)
    assert len(found) == centres.size and np.max(np.abs(np.sort(found) - centres)) < 0.2


def test_continuum_of_a_long_spectrum_with_a_gap_is_flat_and_continuous():
    """A merged echelle spectrum (fitted in overlapping pieces) with the HARPS CCD gap written as zeros: the zeros are
    no data, and the pieces meet without a step (fitted one after the other they jumped by up to 0.45 at their
    edges on 3 of 7 real HARPS spectra)."""
    from astrowb.spectroscopy.rv import continuum_normalise

    rng = np.random.default_rng(1)
    w = 4500 + 0.02 * np.arange(100_000)
    cont = 5e4 * (1 + 0.6 * np.sin((w - 4500) / 700)) * np.exp(-(((w - 5200) / 1500) ** 2))
    lines = 1 - 0.5 * np.exp(-0.5 * ((w[:, None] - rng.uniform(4500, 6500, 400)) / 0.1) ** 2).sum(axis=1).clip(0, 1)
    f = cont * lines * (1 + rng.normal(0, 0.003, len(w)))
    f[(w > 5300) & (w < 5333)] = 0.0
    good = f > 0
    n = continuum_normalise(w, f)[good]
    level = np.array([np.percentile(n[k], 90) for k in np.array_split(np.arange(len(n)), 200)])
    assert np.all(np.abs(level - 1) < 0.01), level.round(3)
