"""Display orientation from a WCS: where North and East point on the frame, the turn and flip that put North up and
East left, and a round length for a scale bar. Display only: the data never change. No Qt here.

Scene coordinates are the viewer's: x = column, y = rows counted from the top of the shown picture (FITS y up, so
scene y grows as the FITS row falls).
"""

import numpy as np

_LENGTHS = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 18000)  # arcsec


def directions(wcs, shape):
    """(north, east, arcsec per pixel) at the centre of a frame: unit vectors in scene coordinates."""
    h, w = shape[:2]
    x, y = (w - 1) / 2, (h - 1) / 2
    ra, dec = wcs.all_pix2world([[x, y]], 0)[0]
    step = 10 / 3600  # 10 arcsec: small enough to stay linear, large enough for float precision
    n = wcs.all_world2pix([[ra, dec + step]], 0)[0] - (x, y)
    e = wcs.all_world2pix([[ra + step / np.cos(np.radians(dec)), dec]], 0)[0] - (x, y)
    north, east = np.array([n[0], -n[1]]), np.array([e[0], -e[1]])  # FITS y up -> scene y down
    scale = 10 / np.linalg.norm(north)
    return north / np.linalg.norm(north), east / np.linalg.norm(east), scale


def north_up(north, east):
    """(rotation in degrees for QTransform.rotate, flip_x) that puts North up and East left on the screen."""
    flip = north[0] * east[1] - north[1] * east[0] > 0  # on screen, up × left is negative (y down)
    n = np.array([-north[0], north[1]]) if flip else north
    return float(np.degrees(np.arctan2(-1, 0) - np.arctan2(n[1], n[0]))), bool(flip)


def scale_bar(arcsec_per_screen_pixel, target=120):
    """(length in screen pixels, label) of a round length near `target` pixels."""
    want = arcsec_per_screen_pixel * target
    arcsec = min(_LENGTHS, key=lambda v: abs(np.log(v / want)))
    label = f'{arcsec}"' if arcsec < 60 else (f"{arcsec // 60}′" if arcsec < 3600 else f"{arcsec // 3600}°")
    return arcsec / arcsec_per_screen_pixel, label
