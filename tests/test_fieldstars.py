import numpy as np
from astropy.io import fits
from photutils.psf import CircularGaussianPRF

from astrowb.photometry import fieldstars

SHAPE = (160, 200)


def stars(n=40, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.uniform(25, SHAPE[1] - 25, n)
    y = rng.uniform(25, SHAPE[0] - 25, n)
    keep = [0]
    for i in range(1, n):  # isolated: at least 12 px apart
        if np.min(np.hypot(x[keep] - x[i], y[keep] - y[i])) > 12:
            keep.append(i)
    x, y = x[keep], y[keep]
    flux = 10 ** rng.uniform(3.6, 5.0, len(x))
    return x, y, flux


def frame(x, y, flux, rng, sky=200.0, fwhm=3.0):
    yy, xx = np.mgrid[: SHAPE[0], : SHAPE[1]]
    img = np.full(SHAPE, sky)
    for xi, yi, f in zip(x, y, flux, strict=True):
        img += CircularGaussianPRF(flux=f, x_0=xi, y_0=yi, fwhm=fwhm)(xx, yy)
    return rng.poisson(img).astype(np.float32)


def test_variable_star_found_among_constant_ones(tmp_path):
    rng = np.random.default_rng(5)
    x, y, flux = stars()
    var = int(np.argsort(flux)[len(flux) // 2])  # a middle-brightness star varies by 0.15 mag
    paths = []
    for i in range(30):
        f = flux.copy()
        f[var] *= 10 ** (-0.4 * 0.15 * np.sin(2 * np.pi * i / 12))
        f *= 1 - 0.3 * (i % 7 == 3)  # passing clouds dim every star alike
        shift = (0.3 * i, -0.2 * i)  # the field drifts
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 60.0})
        p = tmp_path / f"f{i:02d}.fits"
        fits.PrimaryHDU(frame(x + shift[0], y + shift[1], f, rng), h).writeto(p)
        paths.append(p)
    out = fieldstars.field_photometry(paths, max_stars=100)
    found = np.asarray(out["xy"])
    assert len(found) >= len(x) - 2
    v = fieldstars.variability(out["mag"], out["err"])
    j = int(np.argmin(np.hypot(found[:, 0] - x[var], found[:, 1] - y[var])))
    candidates = np.flatnonzero(v["candidate"])
    assert candidates.tolist() == [j]
    assert 0.08 < v["rms"][j] < 0.14  # sine of 0.15 mag amplitude: rms 0.106
    constant = [k for k in range(len(found)) if k != j and v["mean"][k] < np.median(v["mean"])]
    assert np.median(np.asarray(v["rms"])[constant]) < 0.02  # clouds removed by the common zero point


def test_psf_photometry_separates_a_blend():
    rng = np.random.default_rng(1)
    x, y, f = np.array([60.0, 63.5, 120.0]), np.array([80.0, 81.0, 40.0]), np.array([4e4, 2e4, 1e4])
    img = frame(x, y, f, rng)
    flux, err, sky = fieldstars.psf_measure(img, np.column_stack([x, y]), 3.0, 10, 16)
    assert np.all(np.abs(flux - f) < 4 * err) and np.all(err < 0.02 * f)
    assert np.allclose(sky, 200, atol=2)


def _series(tmp_path, n=8):
    rng = np.random.default_rng(5)
    x, y, flux = stars()
    var = int(np.argsort(flux)[len(flux) // 2])
    paths = []
    for i in range(n):
        f = flux.copy()
        f[var] *= 10 ** (-0.4 * 0.3 * (i % 2))
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 60.0})
        p = tmp_path / f"f{i:02d}.fits"
        fits.PrimaryHDU(frame(x, y, f, rng), h).writeto(p)
        paths.append(str(p))
    return paths, x, y, flux, var


def test_psf_light_curve_agrees_with_apertures(tmp_path):
    from astrowb.photometry.lightcurve import light_curve

    paths, x, y, flux, var = _series(tmp_path, 4)
    comps = [(float(x[k]), float(y[k])) for k in np.argsort(-flux)[:3] if k != var]
    args = (paths, (float(x[var]), float(y[var])), comps, 5.0, 12.0, 18.0)
    a, p = light_curve(*args), light_curve(*args, psf=True)
    ra, rp = np.asarray(a["rel_flux"]), np.asarray(p["rel_flux"])
    assert np.allclose(rp / rp[0], ra / ra[0], atol=0.02)
    assert abs(rp[1] / rp[0] - 10 ** (-0.12)) < 0.02  # the 0.3 mag step


def test_varfind_tab(qtbot, tmp_path):
    from astrowb.photometry.steps import varfind_step
    from astrowb.ui.varfind_page import VarFindPage

    paths, x, y, flux, var = _series(tmp_path, 10)

    class Ctx:
        def check(self):
            pass

        def progress(self, *a):
            pass

    page = VarFindPage()
    qtbot.addWidget(page)
    page.set_images(paths)
    got = []
    page.search_requested.connect(lambda images, params: got.append(params))
    page.button.click()
    out = varfind_step({"images": paths}, got[0], Ctx())
    page.show_result(out)
    assert page.table.rowCount() == 1 and page.star is not None
    sent = []
    page.light_curve_chosen.connect(lambda t, f, label: sent.append(f))
    page.send.click()
    assert len(sent[0]) == 10 and abs(max(sent[0]) / min(sent[0]) - 10**0.12) < 0.05
