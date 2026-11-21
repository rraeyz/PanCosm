"""Extended objects (PHO-39): Afrho of a 1/rho coma, isophote profile of a Sersic galaxy."""

import numpy as np
import pytest
from astropy.modeling import fitting, models

from astrowb.compute.isophote import fit_isophotes, surface_brightness
from astrowb.photometry.comet import afrho, afrho_mag, aperture_px, comet_flux

SCALE, DELTA, RH = 0.2, 1.0, 1.5  # arcsec / px, au, au


def test_afrho_independent_of_aperture():
    n = 801
    yy, xx = np.mgrid[:n, :n]
    r = np.hypot(xx - 400, yy - 400)
    data = 5.0 + np.where(r < 200, 1000.0 / np.maximum(r, 1.0), 0.0)  # sky + 1/rho coma ending before the sky ring
    vals = []
    for rho_km in (3000, 5000, 8000, 12000):
        flux, _, _ = comet_flux(data, (400, 400), rho_km, DELTA, SCALE, 40000, 50000)
        vals.append(afrho(flux, 1e6, RH, DELTA, rho_km))
    assert max(vals) / min(vals) - 1 < 0.02


def test_afrho_units_and_helpers():
    assert afrho(1.0, 1.0, 1.0, 1.0, 1e3) == pytest.approx((2 * 1.495978707e13) ** 2 / 1e8, rel=1e-6)
    assert afrho_mag(10.0, 10.0, 1.0, 1.0, 1e3) == pytest.approx(afrho(1.0, 1.0, 1.0, 1.0, 1e3))
    assert aperture_px(149597.870700, 1.0, 1.0) == pytest.approx(206.265, rel=1e-5)  # 1e-3 au at 1 au
    with pytest.raises(ValueError):
        afrho(1.0, 0.0, 1.0, 1.0, 1e3)


def test_sersic_profile_recovered():
    n = 301
    yy, xx = np.mgrid[:n, :n]
    ell, theta = 0.4, np.radians(40.0)
    img = models.Sersic2D(1000.0, 25.0, 2.0, 150, 150, ell, theta)(xx, yy)
    profile, model, resid = fit_isophotes(img, 150, 150, sma0=20, eps=0.3, pa_deg=30)
    sma = np.array(profile["sma"])
    sel = (sma > 15) & (sma < 70)
    assert np.median(np.array(profile["ellipticity"])[sel]) == pytest.approx(ell, rel=0.03)
    assert np.median(np.array(profile["pa_deg"])[sel]) == pytest.approx(40.0, rel=0.03)
    k = (sma > 3) & (sma < 100)  # the centre and the noisy rim are left out
    fit = fitting.LevMarLSQFitter()(models.Sersic1D(1000, 25, 2), sma[k], np.array(profile["intensity"])[k])
    assert fit.r_eff.value == pytest.approx(25.0, rel=0.03)
    ring = (np.hypot(xx - 150, yy - 150) > 10) & (np.hypot(xx - 150, yy - 150) < 60)
    assert np.abs(resid[ring] / img[ring]).max() < 0.05
    assert isinstance(profile["sma"][0], float)
    assert surface_brightness(100.0, 25.0, 0.5) == pytest.approx(25.0 - 2.5 * np.log10(400.0))
