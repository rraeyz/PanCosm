"""Cut-outs by sky position and north-up pictures (plans/images.md IMG-14).

data, wcs = cutout(data, wcs, (ra, dec), size_arcmin)       the part of a solved frame around a position
data, wcs = north_up(data, wcs)                             the frame resampled with north up and east left,
                                                            at its own scale, the counts per pixel kept
"""

import numpy as np
from scipy import ndimage


def cutout(data, wcs, position, size_arcmin):
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astropy.nddata import Cutout2D

    c = Cutout2D(np.asarray(data), SkyCoord(*position, unit="deg"), size_arcmin * u.arcmin, wcs=wcs.celestial,
                 mode="partial", fill_value=np.nan)  # fmt: skip
    return c.data, c.wcs


def north_up(data, wcs, order=3):
    """The frame on a grid with north up, east left and the frame's own pixel scale (bicubic)."""
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales

    data = np.asarray(data, float)
    w = wcs.celestial
    ny, nx = data.shape
    scale = float(np.mean(proj_plane_pixel_scales(w)))
    corners = w.pixel_to_world_values([0, nx - 1, 0, nx - 1], [0, 0, ny - 1, ny - 1])
    centre = w.pixel_to_world_values((nx - 1) / 2, (ny - 1) / 2)
    out = WCS(naxis=2)
    out.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    out.wcs.crval = [float(centre[0]), float(centre[1])]
    out.wcs.cd = np.array([[-scale, 0.0], [0.0, scale]])
    cx, cy = out.wcs_world2pix(corners[0], corners[1], 0)
    size_x, size_y = int(np.ceil(np.ptp(cx))) + 1, int(np.ceil(np.ptp(cy))) + 1
    out.wcs.crpix = [(size_x - 1) / 2 + 1, (size_y - 1) / 2 + 1]
    yy, xx = np.indices((size_y, size_x))
    ra, dec = out.wcs_pix2world(xx.ravel(), yy.ravel(), 0)
    sx, sy = w.wcs_world2pix(ra, dec, 0)
    vals = ndimage.map_coordinates(data, [sy, sx], order=order, mode="constant", cval=np.nan)
    return vals.reshape(size_y, size_x).astype(np.float32), out
