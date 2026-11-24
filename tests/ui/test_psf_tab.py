"""PHO-18: a PSF run keeps its fit diagnostics (the measurements table's PSF_chi2 / PSF_flag columns) and its effective
PSF, which the Photometry window's PSF tab shows with the stars count."""

import numpy as np
import pytest
from astropy.io import fits
from photutils.psf import CircularGaussianPRF

from astrowb.photometry.lightcurve import light_curve
from astrowb.photometry.measurements import measurements
from astrowb.ui.photometry_psf import PsfTab

SHAPE = (240, 300)


def _night(tmp_path, n=4):
    """A crowded field: a 5 x 6 grid of stars 45 px apart, a neighbour 1.5 FWHM from the first (the target)."""
    rng = np.random.default_rng(7)
    gx, gy = np.meshgrid(np.arange(40, 280, 50.0), np.arange(40, 220, 45.0))
    x, y = gx.ravel() + rng.uniform(-3, 3, gx.size), gy.ravel() + rng.uniform(-3, 3, gx.size)
    flux = 10 ** rng.uniform(4.3, 5.0, x.size)
    x, y, flux = np.append(x, x[0] + 4.5), np.append(y, y[0]), np.append(flux, flux[0] / 3)
    yy, xx = np.mgrid[: SHAPE[0], : SHAPE[1]]
    paths = []
    for i in range(n):
        img = np.full(SHAPE, 200.0)
        for xi, yi, f in zip(x, y, flux, strict=True):
            img += CircularGaussianPRF(flux=f, x_0=xi, y_0=yi, fwhm=3.0)(xx, yy)
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 60.0})
        p = tmp_path / f"f{i}.fits"
        fits.PrimaryHDU(rng.poisson(img).astype(np.float32), h).writeto(p)
        paths.append(str(p))
    return paths, x, y


def _run(paths, x, y, **kw):
    comps = [(float(x[k]), float(y[k])) for k in (5, 12, 20)]
    return light_curve(paths, (float(x[0]), float(y[0])), comps, 5.0, 12.0, 18.0, psf=True, **kw)


@pytest.fixture(scope="module")
def night(tmp_path_factory):
    return _night(tmp_path_factory.mktemp("crowded"))


@pytest.fixture(scope="module")
def run(night):
    return _run(*night)


def test_psf_run_keeps_chi2_and_flag_per_star(run):
    cols, _flags = measurements(run)
    for name in ("T1", "C2", "C3", "C4"):
        for label in ("PSF_chi2", "PSF_flag"):
            assert len(cols[f"{label}_{name}"]) == 4
    assert np.isfinite(cols["PSF_chi2_T1"]).all()


def test_aperture_run_has_no_psf_columns(run):
    plain = {k: v for k, v in run.items() if k not in ("psf", "psf_chi2", "psf_flag")}
    cols, _flags = measurements(plain)
    assert not [c for c in cols if c.startswith("PSF_")]


def test_psf_tab_shows_the_epsf_and_the_stars_count(qtbot, run):
    info = run["psf"]
    assert info["epsf"] is not None and info["n_stars"] >= 3
    tab = PsfTab()
    qtbot.addWidget(tab)
    tab.show_psf(run)
    assert tab.view.data.shape == np.shape(info["epsf"])
    assert str(info["n_stars"]) in tab.note.text()


def test_psf_tab_is_empty_without_a_psf_run(qtbot, run):
    tab = PsfTab()
    qtbot.addWidget(tab)
    tab.show_psf(run)
    tab.show_psf({"rel_flux": []})
    assert tab.view.data is None
    tab.show_psf({"psf": {"epsf": None, "n_stars": 2, "oversampling": 2}})
    assert tab.view.data is None and "2" in tab.note.text()


def test_psf_tab_lists_the_psf_stars_with_quality_and_residual(qtbot, run):
    info = run["psf"]
    tab = PsfTab()
    qtbot.addWidget(tab)
    tab.show_psf(run)
    assert tab.stars.model.rowCount() == info["n_stars"] == len(info["stars"])
    assert np.isfinite(info["quality"]) and f"{info['quality']:.2f}" in tab.note.text()
    res = tab.residual.data
    assert res.shape == (25, 25)
    peak = info["stars"][0][2]
    assert np.sqrt(np.mean(res**2)) < 0.02 * peak
    tab.stars.row_chosen.emit(1)
    assert np.allclose(tab.residual.data, info["residuals"][1])
    tab.show_psf({"rel_flux": []})
    assert tab.stars.model.rowCount() == 0 and tab.residual.data is None


def test_a_psf_star_left_out_is_not_used(tmp_path):
    from astrowb.photometry.psf import epsf_summary

    ref = fits.getdata(_night(tmp_path, 1)[0][0]).astype(float)
    full = epsf_summary(ref)
    first = full["stars"][0][:2]
    less = epsf_summary(ref, exclude=[[first[0] + 1.0, first[1]]])
    assert less["n_stars"] == full["n_stars"] - 1
    assert not [s for s in less["stars"] if np.hypot(s[0] - first[0], s[1] - first[1]) < 2]
    assert np.allclose(less["excluded"], [first]) and full["excluded"] == []


def test_psf_tab_leave_out_measures_again_without_the_star(qtbot, night, run):
    tab = PsfTab()
    qtbot.addWidget(tab)
    tab.show_psf(run)
    assert not tab.use_all.isEnabled()
    tab.stars.row_chosen.emit(2)
    with qtbot.waitSignal(tab.exclude_changed, timeout=1000):
        tab.leave_out.click()
    assert tab.exclude == [run["psf"]["stars"][2][:2]]
    again = _run(*night, psf_exclude=tab.exclude)  # what the window's measure does with method_params
    tab.show_psf(again)
    assert tab.stars.model.rowCount() == run["psf"]["n_stars"] - 1 == again["psf"]["n_stars"]
    assert again["psf"]["excluded"] == tab.exclude and tab.use_all.isEnabled()
    with qtbot.waitSignal(tab.exclude_changed, timeout=1000):
        tab.use_all.click()
    assert tab.exclude == []
