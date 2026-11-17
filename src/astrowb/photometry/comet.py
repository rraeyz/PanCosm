"""Comet photometry in apertures of fixed physical radius: Afrho (A'Hearn et al. 1984), after
Afrho = (2 Delta r_h)^2 / rho * F_comet / F_sun,  with Delta and rho in cm, r_h in au, F_sun the Sun's flux at 1 au
in the same band as the comet's. No solar constant is bundled: the caller passes the Sun's flux or magnitude."""

import numpy as np
from astropy import units as u

from ..core.citations import cites
from .aperture import measure


def _cm(value, unit):
    return float((value * unit).to_value(u.cm))


@cites("ahearn1984")
def afrho(flux_comet, flux_sun_at_1au, r_h_au, delta_au, rho_km):
    """Afrho in cm. flux_comet and flux_sun_at_1au in the same flux unit and band (the Sun's flux as seen from
    1 au); r_h_au, delta_au in au (heliocentric, geocentric); rho_km: the aperture radius at the comet in km."""
    if min(flux_sun_at_1au, r_h_au, delta_au, rho_km) <= 0:
        raise ValueError("the solar flux, the distances and the aperture radius must be positive")
    return (2 * _cm(delta_au, u.au) * r_h_au) ** 2 / _cm(rho_km, u.km) * flux_comet / flux_sun_at_1au


def afrho_mag(m_comet, m_sun_at_1au, r_h_au, delta_au, rho_km):
    """Afrho in cm from magnitudes: the comet's in the aperture and the Sun's apparent magnitude at 1 au, same band."""
    return afrho(10 ** (-0.4 * (m_comet - m_sun_at_1au)), 1.0, r_h_au, delta_au, rho_km)


def aperture_px(rho_km, delta_au, pixel_scale_arcsec):
    """Radius in pixels of a circle of physical radius rho_km at geocentric distance delta_au."""
    arcsec = np.degrees(_cm(rho_km, u.km) / _cm(delta_au, u.au)) * 3600.0
    return arcsec / pixel_scale_arcsec


def comet_flux(data, xy, rho_km, delta_au, pixel_scale_arcsec, sky_in_km, sky_out_km, gain=1.0):
    """Sky-subtracted flux (ADU), its error and the radius in pixels, in a circle of rho_km round xy (0-based x, y)
    with the sky from a far annulus of sky_in_km .. sky_out_km."""
    r, r_in, r_out = (aperture_px(k, delta_au, pixel_scale_arcsec) for k in (rho_km, sky_in_km, sky_out_km))
    if not r < r_in < r_out:
        raise ValueError("the sky annulus must lie outside the aperture")
    flux, err, _ = measure(data, np.atleast_2d(xy), r, r_in, r_out, gain=gain)
    return float(flux[0]), float(err[0]), r
