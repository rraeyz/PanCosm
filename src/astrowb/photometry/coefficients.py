"""Photometric coefficients (what VPhot and IRAF photcal give):

- Extinction coefficient of the night, k (mag per airmass), from the comparison stars of a light curve:
  m_ij = c_j + k X_i (one constant per star, one k), least squares with outlier clipping (Bouguer line).
- Transformation coefficients from a standard field (two filters A, B, catalogue magnitudes known), the
  AAVSO convention for e.g. B and V:
      (A - B) = T_ab (a - b) + Z_ab        colour transformation  (e.g. Tbv)
      (B - b) = T_b  (A - B) + Z_b         magnitude transformation (e.g. Tv)
      (A - a) = T_a  (A - B) + Z_a                                   (e.g. Tb)
  with a, b the instrumental magnitudes measured on the two images.
"""

import numpy as np

from ..hdr import get


def _clipped_line(x, y, clip=3.0, iterations=5):
    """Slope, intercept, their errors, rms, mask of points used."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = np.isfinite(x) & np.isfinite(y)
    for _ in range(iterations):
        if keep.sum() < 3:
            raise ValueError("fewer than 3 usable stars")
        (a, b), cov = np.polyfit(x[keep], y[keep], 1, cov=True)
        r = y - (a * x + b)
        sd = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep])))
        new = keep & (np.abs(r) <= clip * max(sd, 1e-6))
        if np.array_equal(new, keep):
            break
        keep = new
    rms = float(np.std(r[keep], ddof=2)) if keep.sum() > 2 else float("nan")
    return float(a), float(b), float(np.sqrt(cov[0, 0])), float(np.sqrt(cov[1, 1])), rms, keep


def extinction(airmass, flux):
    """k (mag / airmass) and its error from the instrumental fluxes [frames x stars] of constant stars."""
    x = np.asarray(airmass, float)
    f = np.asarray(flux, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = -2.5 * np.log10(np.where(f > 0, f, np.nan))
    if np.ptp(x[np.isfinite(x)]) < 0.05:
        raise ValueError("the airmass hardly changed during the series: no extinction from it")
    # per-star constants removed: residual magnitudes against airmass, all stars on one line
    xm = np.repeat(x[:, None], m.shape[1], axis=1)
    centred = m - np.nanmean(m, axis=0)
    xc = xm - np.nanmean(np.where(np.isfinite(m), xm, np.nan), axis=0)
    k, _, k_err, _, rms, keep = _clipped_line(xc.ravel(), centred.ravel())
    return {"k": k, "k_err": k_err, "rms": rms, "n": int(keep.sum())}


def transformation(cat_a, cat_b, inst_a, inst_b, names=("A", "B")):
    """Coefficients from matched standard stars (arrays of equal length; NaN where unknown)."""
    ca, cb, ia, ib = (np.asarray(v, float) for v in (cat_a, cat_b, inst_a, inst_b))
    colour = ca - cb
    a, b = names
    out = {"n": int(np.sum(np.isfinite(colour) & np.isfinite(ia - ib)))}
    for key, x, y in (
        (f"T{a}{b}".lower(), ia - ib, colour),
        (f"T{b}".lower(), colour, cb - ib),
        (f"T{a}".lower(), colour, ca - ia),
    ):
        t, z, te, ze, rms, keep = _clipped_line(x, y)
        out[key] = {
            "value": t,
            "error": te,
            "zero_point": z,
            "zero_point_error": ze,
            "rms": rms,
            "used": int(keep.sum()),
        }
    return out


def standard_stars(image_a, image_b, band_a, band_b, max_stars=150, catalogue=None):
    """Instrumental magnitudes on two plate-solved images of the same field and catalogue magnitudes (APASS,
    or Johnson-Cousins V, R, I from Gaia) of the stars found; returns arrays for transformation()."""
    from astropy.wcs import WCS

    from ..calibration.masters import load
    from .aperture import choose_apertures, measure, recenter
    from .fieldstars import detect_stars

    da, ha = load(image_a)
    db, hb = load(image_b)
    wa, wb = WCS(ha).celestial, WCS(hb).celestial
    if not (wa.has_celestial and wb.has_celestial):
        raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
    xy_a = recenter(da, detect_stars(da, max_stars), 11)
    if len(xy_a) < 5:
        raise ValueError("fewer than 5 stars found on the first frame")
    sky = wa.pixel_to_world(xy_a[:, 0], xy_a[:, 1])
    xb, yb = wb.world_to_pixel(sky)
    ny, nx = db.shape
    inside = (xb > 15) & (xb < nx - 15) & (yb > 15) & (yb < ny - 15)
    xy_a, sky = xy_a[inside], sky[inside]
    xy_b = recenter(db, np.column_stack([xb[inside], yb[inside]]), 11)
    ra = choose_apertures(da, xy_a[:10], get(ha, "EGAIN", "GAIN", default=1.0) or 1.0)
    radii = (ra["r_ap"], ra["r_in"], ra["r_out"])
    fa = measure(da, xy_a, *radii)[0] / (get(ha, "EXPTIME", "EXPOSURE", default=1.0) or 1.0)
    fb = measure(db, xy_b, *radii)[0] / (get(hb, "EXPTIME", "EXPOSURE", default=1.0) or 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ia, ib = -2.5 * np.log10(np.where(fa > 0, fa, np.nan)), -2.5 * np.log10(np.where(fb > 0, fb, np.nan))
    cat = (catalogue or catalogue_magnitudes)(sky, (band_a, band_b))
    return {
        "inst_a": ia.tolist(),
        "inst_b": ib.tolist(),
        "cat_a": cat[band_a],
        "cat_b": cat[band_b],
        "ra": sky.ra.deg.tolist(),
        "dec": sky.dec.deg.tolist(),
    }


def catalogue_magnitudes(sky, bands, match_arcsec=2.0):
    """{band: [mag or NaN]} for each position: APASS for B, V, SG, SR, SI; Gaia-derived for R and I (and V
    where APASS has none). One region query per catalogue (needs the internet)."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.vizier import Vizier

    from .catalog import APASS_BANDS, from_gaia

    centre = SkyCoord(np.mean(sky.ra.deg) * u.deg, np.mean(sky.dec.deg) * u.deg)
    radius = centre.separation(sky).max() + 5 * u.arcsec
    out = {b: np.full(len(sky), np.nan) for b in bands}
    from ..mirrors import cds

    error = None
    for cat in ("II/336/apass9", "I/355/gaiadr3"):
        try:
            tables = cds(
                "vizier",
                lambda server, cat=cat: Vizier(
                    columns=["*", "_RAJ2000", "_DEJ2000"], row_limit=-1, vizier_server=server
                ).query_region(centre, radius=radius, catalog=cat),
            )
        except Exception as e:  # noqa: BLE001 - no VizieR server answered: Gaia from the ESA archive below
            tables, error = [], e
        if not len(tables) and cat.startswith("I/355"):
            from ..gaia import photometry

            tables = [photometry(centre.ra.deg, centre.dec.deg, radius.to_value(u.deg))]
        if not len(tables) or not len(tables[0]):
            continue
        t = tables[0]
        cc = SkyCoord(np.asarray(t["_RAJ2000"]) * u.deg, np.asarray(t["_DEJ2000"]) * u.deg)
        idx, sep, _ = sky.match_to_catalog_sky(cc)
        ok = sep.arcsec < match_arcsec
        for band in bands:
            if cat.startswith("II/336") and band in APASS_BANDS:
                vals = np.asarray(np.ma.filled(t[APASS_BANDS[band]], np.nan), float)[idx]
            elif cat.startswith("I/355") and band in ("V", "R", "I"):
                g, bp, rp = (np.asarray(np.ma.filled(t[c], np.nan), float)[idx] for c in ("Gmag", "BPmag", "RPmag"))
                vals = from_gaia(band, g, bp - rp)
            else:
                continue
            fill = ok & np.isnan(out[band]) & np.isfinite(vals)
            out[band][fill] = vals[fill]
    if error is not None and not any(np.isfinite(v).any() for v in out.values()):
        raise error
    return {b: out[b].tolist() for b in bands}
