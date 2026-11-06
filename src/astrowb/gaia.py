"""Gaia DR3 stars around a position, carried to the epoch of an observation, and a plate solution refined on them.

Stars come from VizieR (CDS and its mirrors, mirrors.cds) or, when it does not answer or gives nothing (the Harvard
VizieR returns no rows for Gaia), straight from the ESA Gaia archive (gea.esac.esa.int, ADQL). Positions are at the
Gaia DR3 epoch J2016.0 and are moved to the observation's epoch with the proper motions (a star of 100 mas/yr moves
1" in ten years — more than a good plate solution's error).

refine_wcs: the solver's WCS (astrometry.net's index catalogue is 2MASS or Tycho-2, ASTAP's a Gaia extract) is
fitted again to the Gaia positions of the stars in the frame — TAN with SIP distortion (astropy
fit_wcs_from_points), matched stars clipped at 3 sigma — so that the astrometry rests on Gaia DR3 and an MPC report
can say so (astCat Gaia3). On a real LCO frame of 433 Eros solved offline with 2MASS indexes: 0.60" median against
Gaia before, see HANDOFF for after.
"""

import numpy as np

GAIA_EPOCH = 2016.0


_CACHE = []  # (ra, dec, radius, mag_limit, rows): the frames of one field are not fetched again (the ESA archive
# took 8–53 s for one cone from the agent's network)


def _cached(ra, dec, radius_deg, mag_limit):
    for c_ra, c_dec, c_r, c_mag, rows in _CACHE:
        d = _sep(ra, dec, c_ra, c_dec)
        if d + radius_deg <= c_r and mag_limit <= c_mag:  # the cone asked for lies inside one fetched
            inside = (_sep(rows["ra"], rows["dec"], ra, dec) <= radius_deg) & (rows["gmag"] < mag_limit)
            return {k: v[inside] for k, v in rows.items()}
    return None


def _sep(ra1, dec1, ra2, dec2):
    """Angular separation in degrees (haversine)."""
    r1, d1, r2, d2 = (np.radians(np.asarray(v, float)) for v in (ra1, dec1, ra2, dec2))
    h = np.sin((d2 - d1) / 2) ** 2 + np.cos(d1) * np.cos(d2) * np.sin((r2 - r1) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(h, 0, 1))))


def stars(ra, dec, radius_deg, mag_limit=17.0, row_limit=4000):
    """dict of arrays ra, dec (deg, J2016.0), pmra, pmdec (mas/yr, pmra includes cos dec), gmag, sorted bright first."""
    hit = _cached(ra, dec, radius_deg, mag_limit)
    if hit is not None:
        return hit
    radius_deg = radius_deg * 1.3  # a little more: the next frames of a series (dithers, drift) fall inside
    try:
        rows = _vizier(ra, dec, radius_deg, mag_limit, row_limit)
    except Exception:  # noqa: BLE001 - every VizieR server down or refusing: the ESA archive
        rows = None
    if rows is None or len(rows["ra"]) == 0:
        rows = _esa(ra, dec, radius_deg, mag_limit, row_limit)
    order = np.argsort(rows["gmag"])
    rows = {k: np.asarray(v, float)[order] for k, v in rows.items()}
    if len(rows["ra"]) < row_limit:  # a complete cone (not cut at row_limit) can serve later frames
        _CACHE.append((float(ra), float(dec), float(radius_deg), float(mag_limit), rows))
        del _CACHE[:-8]
    return rows


def _vizier(ra, dec, radius_deg, mag_limit, row_limit):
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.vizier import Vizier

    from .mirrors import cds

    def ask(server):
        v = Vizier(columns=["RA_ICRS", "DE_ICRS", "pmRA", "pmDE", "Gmag"], row_limit=row_limit, vizier_server=server)
        v.column_filters = {"Gmag": f"<{mag_limit}"}
        t = v.query_region(SkyCoord(ra * u.deg, dec * u.deg), radius=radius_deg * u.deg, catalog="I/355/gaiadr3")
        return t[0] if len(t) else []

    t = cds("vizier", ask)
    if len(t) == 0:
        return None
    return {
        "ra": t["RA_ICRS"],
        "dec": t["DE_ICRS"],
        "pmra": np.ma.filled(t["pmRA"].astype(float), 0.0),
        "pmdec": np.ma.filled(t["pmDE"].astype(float), 0.0),
        "gmag": t["Gmag"],
    }


def _esa(ra, dec, radius_deg, mag_limit, row_limit):

    query = (
        f"SELECT TOP {int(row_limit)} ra, dec, pmra, pmdec, phot_g_mean_mag FROM gaiadr3.gaia_source "
        f"WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {float(ra)}, {float(dec)}, {float(radius_deg)})) "
        f"AND phot_g_mean_mag < {float(mag_limit)}"
    )
    t = _run(query)
    return {
        "ra": t["ra"],
        "dec": t["dec"],
        "pmra": np.ma.filled(t["pmra"].astype(float), 0.0),
        "pmdec": np.ma.filled(t["pmdec"].astype(float), 0.0),
        "gmag": t["phot_g_mean_mag"],
    }


def _run(query):
    """An ADQL query on the ESA Gaia archive: synchronous, or through its asynchronous queue when the synchronous
    queue is full (HTTP 503 "server overloaded", seen from the agent's network on 2026-11-06)."""
    from astroquery.gaia import Gaia

    try:
        return Gaia.launch_job(query).get_results()
    except Exception as e:  # noqa: BLE001 - the queue is full or the answer timed out: the asynchronous queue
        if "503" not in str(e) and "overloaded" not in str(e).lower() and "timed out" not in str(e).lower():
            raise
        return Gaia.launch_job_async(query).get_results()


def photometry(ra, dec, radius_deg, row_limit=5000):
    """Table of Gaia DR3 photometry in a cone from the ESA archive, with VizieR's column names (Gmag, e_Gmag, BPmag,
    RPmag, _RAJ2000, _DEJ2000), for when no VizieR server answers. The positions are J2016.0: within 1" of J2000 for
    all but the fastest stars, which a 2" match allows."""
    t = _run(
        f"SELECT TOP {int(row_limit)} ra, dec, phot_g_mean_mag, phot_g_mean_flux_over_error, phot_bp_mean_mag, "
        "phot_rp_mean_mag FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {float(ra)}, {float(dec)}, {float(radius_deg)})) ORDER BY phot_g_mean_mag"
    )
    t["e_Gmag"] = 1.0857 / t["phot_g_mean_flux_over_error"]  # magnitude error from the flux S/N
    for old, new in (
        ("ra", "_RAJ2000"),
        ("dec", "_DEJ2000"),
        ("phot_g_mean_mag", "Gmag"),
        ("phot_bp_mean_mag", "BPmag"),
        ("phot_rp_mean_mag", "RPmag"),
    ):
        t.rename_column(old, new)
    return t


def at_epoch(cat, year):
    """(ra, dec) in degrees at the decimal year, from J2016.0 and the proper motions (linear; fine for decades)."""
    dt = float(year) - GAIA_EPOCH
    dec = cat["dec"] + cat["pmdec"] * dt / 3.6e6
    ra = cat["ra"] + cat["pmra"] * dt / 3.6e6 / np.cos(np.radians(cat["dec"]))
    return ra, dec


def refine_wcs(data, header, cat=None, year=None, max_stars=150, sip_degree=3):
    """(new WCS header, info) with the WCS refitted to Gaia DR3. info: matched, rms (arcsec) before and after.
    Raises ValueError when too few stars match (a wrong solution, or a field with few stars)."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.wcs import WCS
    from astropy.wcs.utils import fit_wcs_from_points, proj_plane_pixel_scales

    from .calibration.starmatch import stars as find_stars

    wcs = WCS(header).celestial
    ny, nx = data.shape
    scale = float(np.mean(proj_plane_pixel_scales(wcs))) * 3600  # arcsec per pixel
    if year is None:
        from . import timing

        try:
            year = timing.mid_time(header).jyear
        except Exception:  # noqa: BLE001 - no time in the header: the Gaia epoch itself
            year = GAIA_EPOCH
    xy = np.array(find_stars(data, n=max_stars), float)
    if len(xy) < 8:
        raise ValueError(f"only {len(xy)} stars found in the image: too few to refine the plate solution")
    if cat is None:  # after the stars are found: an image without stars costs no catalogue query
        centre = wcs.pixel_to_world(nx / 2, ny / 2)
        radius = 0.5 * np.hypot(nx, ny) * scale / 3600 * 1.05
        cat = stars(centre.ra.deg, centre.dec.deg, radius)
    ra, dec = at_epoch(cat, year)
    sky = SkyCoord(ra * u.deg, dec * u.deg)
    tol = max(3.0, 4.0 / scale)  # pixels: a few arcsec or 3 px, whichever is larger

    def match(w):
        gx, gy = w.world_to_pixel(sky)
        inside = (gx > -5) & (gx < nx + 5) & (gy > -5) & (gy < ny + 5)
        gx, gy, idx = gx[inside], gy[inside], np.flatnonzero(inside)
        pairs = []
        for x, y in xy:
            d = np.hypot(gx - x, gy - y)
            j = int(np.argmin(d)) if d.size else -1
            if j >= 0 and d[j] < tol:
                pairs.append((x, y, idx[j], d[j]))
        return pairs

    def residual(w, pairs):
        if not pairs:
            return np.array([])
        p = w.pixel_to_world([q[0] for q in pairs], [q[1] for q in pairs])
        return p.separation(sky[[q[2] for q in pairs]]).arcsec

    pairs = match(wcs)
    if len(pairs) < 8:
        raise ValueError(f"only {len(pairs)} stars match Gaia DR3: too few to refine the plate solution")
    before = residual(wcs, pairs)
    new, keep = wcs, pairs
    for _ in range(3):  # fit, clip at 3 times the median residual (blended stars), match again with the better WCS
        res = residual(new, pairs)
        keep = [q for q, r in zip(pairs, res, strict=True) if r <= max(3 * np.median(res), 0.05)]
        deg = sip_degree if len(keep) >= 40 else (2 if len(keep) >= 15 else None)
        x = np.array([q[0] for q in keep])
        y = np.array([q[1] for q in keep])
        new = fit_wcs_from_points((x, y), sky[[q[2] for q in keep]], proj_point="center", sip_degree=deg)
        pairs = match(new)
    res = residual(new, pairs)
    keep = [q for q, r in zip(pairs, res, strict=True) if r <= max(3 * np.median(res), 0.05)]
    after = residual(new, keep)  # the stars the solution rests on (blends left out)
    out = new.to_header(relax=True)
    out["ASTCAT"] = ("Gaia3", "star catalogue of the plate solution (ADES astCat)")
    out["ASTRRMS"] = (round(float(np.sqrt(np.mean(after**2))), 3), "[arcsec] rms of the Gaia DR3 stars after the refit")
    out["ASTRNST"] = (len(keep), "Gaia DR3 stars used in the refit")
    info = {
        "matched": len(keep),
        "rms_before": float(np.sqrt(np.mean(before**2))),
        "rms_after": float(np.sqrt(np.mean(after**2))),
        "median_after": float(np.median(after)),
        "epoch": float(year),
    }
    return out, info


def chart_stars(ra, dec, radius_deg, mag_limit=16.0, row_limit=2000):
    """[{name, ra, dec, mag (G), v (Johnson V)}] from the ESA Gaia archive, as overlays.query_catalogue gives them."""

    from .photometry.catalog import from_gaia

    query = (
        f"SELECT TOP {int(row_limit)} source_id, ra, dec, phot_g_mean_mag, bp_rp FROM gaiadr3.gaia_source "
        f"WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {float(ra)}, {float(dec)}, {float(radius_deg)})) "
        f"AND phot_g_mean_mag < {float(mag_limit)} ORDER BY phot_g_mean_mag"
    )
    out = []
    for r in _run(query):
        g = float(r["phot_g_mean_mag"])
        star = {"name": f"Gaia DR3 {int(r['source_id'])}", "ra": float(r["ra"]), "dec": float(r["dec"]), "mag": g}
        if not np.ma.is_masked(r["bp_rp"]):
            star["v"] = float(from_gaia("V", g, float(r["bp_rp"])))
        out.append(star)
    return out
