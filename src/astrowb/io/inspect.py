"""Measurements on one image, as in an image-information window: a star in an aperture, the counts in a
rectangle, the pixels along a line, row and column profiles, histograms.

Coordinates are 0-based array positions (x = column, y = row; pixel centres on integers). Counts are in the
image's own unit (ADU for raw and calibrated frames); multiplied by the gain they are electrons.
"""

import numpy as np

from ..hdr import number

SATURATION_KEYS = ("SATURATE", "DATAMAX", "MAXLIN")


def saturation_level(header, data=None):
    """The level above which pixels are not trusted: SATURATE / DATAMAX / MAXLIN from the header, else the top of
    the unsigned 16-bit range when the data look like a 16-bit camera, else None."""
    for key in SATURATION_KEYS:
        if header is not None and key in header:
            if number(header[key]) is not None:
                return number(header[key])
    if data is not None and np.nanmax(data) <= 65535 and np.nanmax(data) > 4095:
        return 65535.0
    return None


def area_stats(data, x0, y0, x1, y1, gain=None):
    """Statistics of the pixels in the rectangle between the two corners (both included)."""
    ny, nx = data.shape
    xa, xb = sorted((int(round(x0)), int(round(x1))))
    ya, yb = sorted((int(round(y0)), int(round(y1))))
    xa, xb, ya, yb = max(xa, 0), min(xb, nx - 1), max(ya, 0), min(yb, ny - 1)
    if xa > xb or ya > yb:
        raise ValueError("the rectangle is outside the image")
    box = np.asarray(data[ya : yb + 1, xa : xb + 1])
    if not np.issubdtype(box.dtype, np.floating):
        box = box.astype(np.float64)
    good = np.isfinite(box)
    all_good = bool(good.all())
    vals = box.ravel() if all_good else box[good]  # no copy when every pixel is valid
    if not vals.size:
        raise ValueError("the rectangle has no valid pixels")
    total = float(vals.sum(dtype=np.float64))
    med = float(np.median(vals))
    imin = int(box.argmin()) if all_good else int(np.nanargmin(box))
    imax = int(box.argmax()) if all_good else int(np.nanargmax(box))
    width = box.shape[1]
    out = {
        "x0": xa,
        "y0": ya,
        "x1": xb,
        "y1": yb,
        "width": xb - xa + 1,
        "height": yb - ya + 1,
        "pixels": int(vals.size),
        "sum": total,
        "mean": total / vals.size,
        "median": med,
        "std": float(vals.std(dtype=np.float64, ddof=1)) if vals.size > 1 else 0.0,
        "mad_std": float(1.4826 * np.median(np.abs(vals - vals.dtype.type(med)))),
        "min": float(box.flat[imin]),
        "min_xy": (xa + imin % width, ya + imin // width),
        "max": float(box.flat[imax]),
        "max_xy": (xa + imax % width, ya + imax // width),
    }
    if gain:
        out["sum_electrons"] = out["sum"] * gain
    return out


def line_profile(data, x0, y0, x1, y1, width=1):
    """Pixel values along the line, one sample per pixel of length (bilinear interpolation). With width > 1 the
    samples are averaged across the line over that many pixels. Returns distances, values, length and the
    angle of the line (degrees, counter-clockwise from +x)."""
    from scipy.ndimage import map_coordinates

    length = float(np.hypot(x1 - x0, y1 - y0))
    n = max(2, int(np.ceil(length)) + 1)
    t = np.linspace(0.0, 1.0, n)
    xs, ys = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    angle = float(np.degrees(np.arctan2(y1 - y0, x1 - x0)))
    data = np.asarray(data, float)
    if width > 1 and length > 0:
        ux, uy = -(y1 - y0) / length, (x1 - x0) / length  # unit normal
        offsets = np.arange(width) - (width - 1) / 2
        rows = [map_coordinates(data, [ys + o * uy, xs + o * ux], order=1, mode="nearest") for o in offsets]
        values = np.mean(rows, axis=0)
    else:
        values = map_coordinates(data, [ys, xs], order=1, mode="nearest")
    return {"distance": (t * length).tolist(), "values": values.tolist(), "length": length, "angle": angle}


def box_profile(data, x0, y0, x1, y1, axis="x"):
    """Mean of the rectangle's pixels across one axis: axis "x" gives the profile along x (each column's mean,
    a row profile), "y" the profile along y (each row's mean, a column profile)."""
    s = area_stats(data, x0, y0, x1, y1)
    box = np.asarray(data[s["y0"] : s["y1"] + 1, s["x0"] : s["x1"] + 1], float)
    if axis == "x":
        return {"position": list(range(s["x0"], s["x1"] + 1)), "values": np.nanmean(box, axis=0).tolist()}
    return {"position": list(range(s["y0"], s["y1"] + 1)), "values": np.nanmean(box, axis=1).tolist()}


def histogram(values, bins=200, clip=None):
    """Histogram of the finite values; clip=(low, high) percentiles keeps outliers from squeezing the plot."""
    v = np.asarray(values).ravel()
    v = v[np.isfinite(v)]
    if not v.size:
        lo, hi = 0.0, 1.0
    elif clip:  # the display range: a regular sample of a million values gives the same limits
        lo, hi = np.percentile(v[:: max(1, v.size // 1_000_000)], clip)
    else:
        lo, hi = v.min(), v.max()
    if hi <= lo:
        hi = lo + 1.0
    counts, edges = np.histogram(v, bins=bins, range=(lo, hi))
    return {"counts": counts.tolist(), "edges": edges.tolist()}


def star_info(data, x, y, r_ap=None, r_in=None, r_out=None, gain=1.0, exptime=None, saturation=None):
    """A star measured in an aperture at (x, y): centroid, peak, background, net counts with error, signal-to-
    noise, FWHM, half-flux diameter, ellipticity, instrumental magnitude. Radii not given are chosen from the
    star's profile (photometry.aperture.choose_apertures). Works on a cut-out around the star, so a large frame
    is not copied; "profile" holds the radial profile (photometry.aperture.star_profile) for plotting."""
    half = max(150, int(4 * max(r_ap or 0, r_out or 0)) + 20)
    ny, nx = np.shape(data)
    while True:
        x0, y0 = max(0, int(x) - half), max(0, int(y) - half)
        x1, y1 = min(nx, int(x) + half + 1), min(ny, int(y) + half + 1)
        cut = np.asarray(data[y0:y1, x0:x1], float)
        out = _star_info(cut, x - x0, y - y0, r_ap, r_in, r_out, gain, exptime, saturation)
        # the cut must hold every pixel the measurement uses (sky annulus, profile); a large, defocused star can
        # need more than the first guess: then measure again on a cut large enough (same result as the full frame)
        need = int(np.ceil(max(out["r_out"], 3 * out["r_ap"]))) + 5
        whole = x0 == 0 and y0 == 0 and x1 == nx and y1 == ny
        if whole or need <= half - abs(x - int(x)) - 1:
            break
        half = need + 20
    out["x"], out["y"] = out["x"] + x0, out["y"] + y0
    return out


def _star_info(data, x, y, r_ap, r_in, r_out, gain, exptime, saturation):
    from ..photometry.aperture import choose_apertures, measure, recenter, star_profile

    cx, cy = recenter(data, [(x, y)])[0]
    if not r_ap:
        chosen = choose_apertures(data, [(cx, cy)], gain or 1.0)
        r_ap, r_in, r_out = chosen["r_ap"], chosen["r_in"], chosen["r_out"]
    r_in = r_in or 3 * r_ap
    r_out = r_out or float(np.sqrt(r_in**2 + 4 * r_ap**2))
    flux, err, sky = (float(v[0]) for v in measure(data, [(cx, cy)], r_ap, r_in, r_out, gain or 1.0))
    prof = star_profile(data, cx, cy, max(r_out, 3 * r_ap))
    v = data
    ny, nx = data.shape
    yy, xx = np.mgrid[
        max(0, int(cy - r_ap) - 1) : min(ny, int(cy + r_ap) + 2),
        max(0, int(cx - r_ap) - 1) : min(nx, int(cx + r_ap) + 2),
    ]
    rr = np.hypot(xx - cx, yy - cy)
    inside = rr <= r_ap
    pix = v[yy[inside], xx[inside]]
    peak = float(np.nanmax(pix))
    net = np.clip(pix - sky, 0, None)
    # half-flux diameter: twice the radius holding half of the net counts in the aperture
    order = np.argsort(rr[inside])
    cum = np.cumsum(net[order])
    hfd = 2 * float(rr[inside][order][np.searchsorted(cum, cum[-1] / 2)]) if cum[-1] > 0 else float("nan")
    # shape from the second moments of the net light
    w = net / net.sum() if net.sum() > 0 else np.ones_like(net) / net.size
    dx, dy = xx[inside] - cx, yy[inside] - cy
    mxx, myy, mxy = (w * dx * dx).sum(), (w * dy * dy).sum(), (w * dx * dy).sum()
    common = np.sqrt(((mxx - myy) / 2) ** 2 + mxy**2)
    a, b = np.sqrt((mxx + myy) / 2 + common), np.sqrt(max((mxx + myy) / 2 - common, 0.0))
    out = {
        "x": float(cx),
        "y": float(cy),
        "r_ap": float(r_ap),
        "r_in": float(r_in),
        "r_out": float(r_out),
        "peak": peak,
        "background": sky,
        "net_counts": flux,
        "net_counts_err": err,
        "snr": flux / err if err > 0 else float("nan"),
        "fwhm": prof["fwhm"],
        "hfd": hfd,
        "ellipticity": float(1 - b / a) if a > 0 else float("nan"),
        "position_angle": float(np.degrees(0.5 * np.arctan2(2 * mxy, mxx - myy))),
        "saturated": bool(saturation is not None and peak >= saturation),
        "pixels": int(inside.sum()),
        "profile": prof,
    }
    if flux > 0:
        rate = flux / exptime if exptime else flux
        out["instrumental_mag"] = float(-2.5 * np.log10(rate))
        out["instrumental_mag_err"] = float(1.0857 * err / flux)
    if gain:
        out["net_electrons"] = flux * gain
    return out
