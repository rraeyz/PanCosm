"""Isophote fitting of an extended object (galaxy, comet coma): a thin wrapper over photutils.isophote
(ellipse fitting after Jedrzejewski 1987). Placed in compute/ because there is no images/ package."""

import numpy as np
from photutils.isophote import Ellipse, EllipseGeometry, build_ellipse_model

from ..core.citations import cites


def surface_brightness(intensity, zero_point, pixel_scale_arcsec):
    """mag arcsec^-2 of an intensity in counts per pixel: zero_point - 2.5 log10(I / scale^2). NaN where I <= 0."""
    i = np.asarray(intensity, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(i > 0, zero_point - 2.5 * np.log10(i / pixel_scale_arcsec**2), np.nan)


@cites("jedrzejewski1987")
def fit_isophotes(data, x0, y0, sma0=10.0, eps=0.2, pa_deg=0.0, **kwargs):
    """Fit ellipses round (x0, y0) (0-based). pa_deg: starting position angle from +x, counter-clockwise (the
    photutils convention, returned the same). Returns (profile, model, residual); the profile is a dict of plain
    lists: sma, intensity, intensity_err, ellipticity, pa_deg. Extra kwargs go to Ellipse.fit_image."""
    data = np.asarray(data, float)
    geometry = EllipseGeometry(x0, y0, sma0, eps, np.radians(pa_deg))
    isolist = Ellipse(data, geometry=geometry).fit_image(**kwargs)
    if len(isolist) == 0:
        raise ValueError("no isophote could be fitted")
    profile = {
        "sma": isolist.sma.tolist(),
        "intensity": isolist.intens.tolist(),
        "intensity_err": isolist.int_err.tolist(),
        "ellipticity": isolist.eps.tolist(),
        "pa_deg": np.degrees(isolist.pa).tolist(),
    }
    model = build_ellipse_model(data.shape, isolist)
    return profile, model, data - model
