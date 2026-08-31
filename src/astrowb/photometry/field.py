"""What is in the field: a plate solution of a frame against Gaia DR3 without installing a solver, the known
variable stars in it (AAVSO VSX), whether the OBJECT the header names is in it at all, and comparison stars chosen
from the catalogue.

The owner's NY Vir night: the files said OBJECT = NSVS07826147, a star 30 degrees away; the field held NY Vir, and
nothing in the program said so. AstroImageJ and Siril work from a plate solution; Siril chooses comparison stars from
a catalogue by magnitude, colour and known variability (findcompstars).

Solution: the bright stars of the frame and of Gaia around the header's pointing, projected on the sky plane with the
pixel scale from the header (FOCALLEN and XPIXSZ, or a scale keyword), are matched by their triangles
(calibration.starmatch: rotation, scale and shift; tried mirrored too, for a flipped camera), then a TAN solution is
fitted to every star that agrees. Positions are 0-based pixels, as everywhere in photometry.
"""

import numpy as np

SOLVE_STARS = 40  # bright stars of the frame used for the triangles
MIN_MATCHED = 8  # stars that must agree for a solution
MAX_RMS_PX = 2.0


def pixel_scale(header):
    """Arcseconds per pixel from the header, or None: a scale keyword, else the pixel size (XPIXSZ, µm, as the
    camera software writes it: binned) over the focal length (FOCALLEN, mm)."""
    from ..hdr import get

    for key in ("SCALE", "PIXSCALE", "SECPIX", "SECPIX1"):
        v = get(header, key)
        if v:
            return abs(float(v))
    pix, focal = get(header, "XPIXSZ", "PIXSIZE1"), get(header, "FOCALLEN")
    if pix and focal:
        if get(header, "PIXSIZE1") and not get(header, "XPIXSZ"):  # PIXSIZE1 is the unbinned size
            pix = float(pix) * float(get(header, "XBINNING", default=1) or 1)
        return 206.264806 * float(pix) / float(focal)
    return None


def solve(data, header, catalogue=None):
    """{"wcs": astropy WCS, "matched", "rms_px", "scale" (arcsec/px), "rotation" (deg), "flipped"} for the frame.
    catalogue: Gaia rows as gaia.stars returns them (fetched around the header's pointing when None). Raises
    ValueError saying what is missing (pointing, scale) or that the stars do not match."""
    from astropy.coordinates import SkyCoord
    from astropy.wcs.utils import fit_wcs_from_points

    from ..calibration import starmatch
    from .fieldstars import detect_stars
    from .lightcurve import target_coord

    centre = target_coord(header)
    if centre is None:
        raise ValueError("the frame has no pointing (OBJCTRA / OBJCTDEC or RA / DEC) in its header to solve it from")
    scale = pixel_scale(header)
    if not scale:
        raise ValueError("the pixel scale is unknown (no FOCALLEN and XPIXSZ in the header) to solve the frame")
    ny, nx = np.shape(data)
    ra0, dec0 = centre.ra.deg, centre.dec.deg
    half_diag = 0.5 * np.hypot(nx, ny) * scale / 3600
    radius = 1.3 * half_diag + 0.1  # the pointing written by the mount can be some arcminutes off
    if catalogue is None:
        from .. import gaia

        catalogue = gaia.stars(ra0, dec0, radius, mag_limit=18.0)
    cat = _at_epoch(catalogue, header)
    img = starmatch.stars(data, n=SOLVE_STARS)
    if len(img) < 6 or len(cat["ra"]) < 6:
        raise ValueError("too few stars to solve the frame (clouds, or too short an exposure?)")
    x, y = _plane(cat["ra"], cat["dec"], ra0, dec0, scale)
    near = np.hypot(x, y) <= radius * 3600 / scale
    # as many catalogue stars per area as the frame gives, so that both lists show the same stars
    n_cat = int(np.clip(len(img) * np.pi * (radius * 3600 / scale) ** 2 / (nx * ny), 30, 400))
    order = np.flatnonzero(near)[np.argsort(cat["gmag"][near])][:n_cat]
    best = None
    for flip in (1, -1):
        try:
            m, t, n, rms = starmatch.match(np.c_[flip * x[order], y[order]], img, max_error=3.0)
        except ValueError:
            continue
        if best is None or n > best[2]:
            best = (m, t, n, rms, flip)
    if best is None or best[2] < 6:
        raise ValueError("the stars of the frame do not match the Gaia stars around its pointing")
    m, t, _, _, flip = best
    # every star that agrees, from more stars of the frame and the catalogue, fitted with a TAN solution
    stars = detect_stars(data, max_stars=200)
    px = np.c_[flip * x, y] @ m.T + t
    from scipy.spatial import cKDTree

    dist, idx = cKDTree(px).query(stars)
    ok = dist < 2.5
    if ok.sum() < MIN_MATCHED:
        raise ValueError("the stars of the frame do not match the Gaia stars around its pointing")
    sky = SkyCoord(cat["ra"][idx[ok]], cat["dec"][idx[ok]], unit="deg")
    xy = stars[ok]
    wcs = fit_wcs_from_points((xy[:, 0], xy[:, 1]), sky, projection="TAN")
    for _ in range(2):  # stars that the first fit puts far off (a wrong pair) are left out
        res = np.hypot(*(np.array(wcs.world_to_pixel(sky)) - xy.T))
        keep = res < max(3 * np.median(res), 0.5)
        if keep.all() or keep.sum() < MIN_MATCHED:
            break
        sky, xy = sky[keep], xy[keep]
        wcs = fit_wcs_from_points((xy[:, 0], xy[:, 1]), sky, projection="TAN")
    res = np.hypot(*(np.array(wcs.world_to_pixel(sky)) - xy.T))
    rms = float(np.sqrt(np.mean(res**2)))
    if len(xy) < MIN_MATCHED or rms > MAX_RMS_PX:
        raise ValueError("the stars of the frame do not match the Gaia stars around its pointing")
    cd = wcs.pixel_scale_matrix * 3600
    return {
        "wcs": wcs,
        "matched": len(xy),
        "rms_px": rms,
        "scale": float(np.sqrt(abs(np.linalg.det(cd)))),
        "rotation": float(np.degrees(np.arctan2(cd[1, 0], cd[1, 1]))),
        "flipped": bool(np.linalg.det(cd) > 0),  # north up and east left on the sky is a negative determinant
    }


def _plane(ra, dec, ra0, dec0, scale):
    """Gnomonic projection about (ra0, dec0), in pixels of the given scale: x towards east, y towards north."""
    r, d, r0, d0 = (np.radians(np.asarray(v, float)) for v in (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(r - r0)
    xi = np.cos(d) * np.sin(r - r0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(r - r0)) / cosc
    k = np.degrees(1.0) * 3600 / scale
    return xi * k, eta * k


def _at_epoch(cat, header):
    """Gaia positions moved to the date of the frame (DATE-OBS), when it is known."""
    from .. import gaia

    try:
        from astropy.time import Time

        year = Time(header["DATE-OBS"]).decimalyear
    except (KeyError, ValueError):
        return cat
    ra, dec = gaia.at_epoch(cat, year)
    return dict(cat) | {"ra": np.asarray(ra), "dec": np.asarray(dec)}


def identify(path, ctx=None, catalogue=None, variables=None, resolve=None):
    """The field of a frame: its solution (a FITS header with the WCS), the VSX variable stars in it with their
    pixels, the Gaia stars in it (for comparison stars), and the OBJECT of the header: where it is and whether it is
    in the field. catalogue / variables / resolve: Gaia rows, [{name, ra, dec, mag}] and name -> (ra, dec), for tests.
    """
    from astropy.coordinates import SkyCoord

    from ..calibration.masters import load

    data, header = load(path)
    if ctx:
        ctx.progress(0.1, "solving")
    sol = solve(data, header, catalogue)
    wcs = sol["wcs"]
    ny, nx = np.shape(data)
    centre = wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2)
    radius = 0.5 * np.hypot(nx, ny) * sol["scale"] / 3600
    if ctx:
        ctx.progress(0.5, "catalogues")
    if catalogue is None:
        from .. import gaia

        catalogue = gaia.stars(centre.ra.deg, centre.dec.deg, radius, mag_limit=18.0)
    cat = _at_epoch(catalogue, header)
    gx, gy = wcs.world_to_pixel(SkyCoord(cat["ra"], cat["dec"], unit="deg"))
    on = (gx >= 0) & (gx <= nx - 1) & (gy >= 0) & (gy <= ny - 1)
    if variables is None:
        variables = _vsx(centre.ra.deg, centre.dec.deg, radius)
    found = []
    for v in variables:
        vx, vy = wcs.world_to_pixel(SkyCoord(v["ra"], v["dec"], unit="deg"))
        if 0 <= vx <= nx - 1 and 0 <= vy <= ny - 1:
            found.append(dict(v) | {"x": float(vx), "y": float(vy)})
    found.sort(key=lambda v: (v.get("mag") is None, v.get("mag") or 0))
    obj = _object(header, wcs, (nx, ny), resolve)
    return {
        "header": wcs.to_header().tostring(),
        "matched": sol["matched"],
        "rms_px": sol["rms_px"],
        "scale": sol["scale"],
        "rotation": sol["rotation"],
        "flipped": sol["flipped"],
        "centre": [float(centre.ra.deg), float(centre.dec.deg)],
        "variables": found,
        "object": obj,
        "stars": {
            "x": gx[on].tolist(),
            "y": gy[on].tolist(),
            "ra": np.asarray(cat["ra"])[on].tolist(),
            "dec": np.asarray(cat["dec"])[on].tolist(),
            "gmag": np.asarray(cat["gmag"])[on].tolist(),
            "bp_rp": np.asarray(cat.get("bp_rp", np.full(len(gx), np.nan)))[on].tolist(),
            "variable": np.asarray(cat.get("variable", np.zeros(len(gx))))[on].tolist(),
        },
    }


def _vsx(ra, dec, radius):
    """AAVSO VSX variable stars in the cone: [{name, ra, dec, mag}] (none when VizieR does not answer)."""
    from ..overlays import query_catalogue

    try:
        return query_catalogue(ra, dec, radius, catalogue="vsx")
    except Exception:  # noqa: BLE001 - the catalogue is a help: a solution without it is still a solution
        return []


def _object(header, wcs, size, resolve=None):
    """The OBJECT keyword: its sky position (SIMBAD) and pixel, and whether it is in the field; None without one."""
    from astropy.coordinates import SkyCoord

    name = str(header.get("OBJECT", "") or "").strip()
    if not name:
        return None
    try:
        if resolve is None:
            from ..planning.targets import Resolver
            from ..settings import config_dir

            t = Resolver(config_dir() / "targets.json").resolve(name)
            ra, dec = t.ra, t.dec
        else:
            ra, dec = resolve(name)
    except Exception:  # noqa: BLE001 - an unknown name or no network: said as unknown, never an error
        return {"name": name, "known": False}
    x, y = wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
    centre = wcs.pixel_to_world((size[0] - 1) / 2, (size[1] - 1) / 2)
    inside = bool(0 <= x <= size[0] - 1 and 0 <= y <= size[1] - 1)
    away = float(centre.separation(SkyCoord(ra, dec, unit="deg")).deg)
    return {"name": name, "known": True, "ra": ra, "dec": dec, "x": float(x), "y": float(y), "in_field": inside,
            "distance_deg": away}  # fmt: skip


def comparison_stars(field, target_xy, data, saturation=None, n=5, r_out=15.0, margin=60):
    """Comparison stars from the Gaia stars of the field (identify()["stars"]), with the criteria of Siril's
    findcompstars (which uses APASS): about as bright as the target (|ΔG| <= 2.5, closest first), not variable
    (Gaia's flag, VSX), alone (no Gaia star brighter than 5 mag fainter inside the sky ring), not saturated on this
    frame and at least margin px inside it; stars of a similar colour (|Δ(BP-RP)| <= 0.5) first. A hot subdwarf like
    NY Vir (BP-RP -0.4) has no such star in its field: then the closest in brightness, and "colour" says so.
    Returns {"stars": [(x, y, G, BP-RP)], "colour": target BP-RP, "same_colour": all chosen within 0.5}."""
    st = {k: np.asarray(v, float) for k, v in field["stars"].items()}
    x, y, g, colour = st["x"], st["y"], st["gmag"], st["bp_rp"]
    ny, nx = np.shape(data)
    i_t = int(np.argmin(np.hypot(x - target_xy[0], y - target_xy[1])))
    if np.hypot(x[i_t] - target_xy[0], y[i_t] - target_xy[1]) > 3:
        raise ValueError("the target is not a Gaia star of the field: mark it on the star")
    g_t, c_t = g[i_t], colour[i_t]
    vsx = np.array([[v["x"], v["y"]] for v in field.get("variables", [])]).reshape(-1, 2)
    usable = []
    for i in np.argsort(np.abs(g - g_t)):
        if i == i_t or abs(g[i] - g_t) > 2.5 or st["variable"][i]:
            continue
        if not (margin <= x[i] <= nx - 1 - margin and margin <= y[i] <= ny - 1 - margin):
            continue
        if len(vsx) and np.hypot(*(vsx - [x[i], y[i]]).T).min() < 3:
            continue
        d = np.hypot(x - x[i], y - y[i])
        if np.any((d > 0.5) & (d < r_out) & (g < g[i] + 5)):  # a neighbour that would light the aperture or sky
            continue
        if saturation:
            yi, xi = int(round(y[i])), int(round(x[i]))
            if np.nanmax(data[max(0, yi - 3) : yi + 4, max(0, xi - 3) : xi + 4]) >= 0.8 * saturation:
                continue
        usable.append(i)
    same = [i for i in usable if np.isfinite(c_t) and np.isfinite(colour[i]) and abs(colour[i] - c_t) <= 0.5]
    others = sorted((i for i in usable if i not in same), key=lambda i: abs(g[i] - g_t) + 0.5 * _gap(colour[i], c_t))
    chosen = (same + others)[:n]
    return {
        "stars": [(float(x[i]), float(y[i]), float(g[i]), float(colour[i])) for i in chosen],
        "colour": float(c_t),
        "same_colour": bool(chosen) and all(i in same for i in chosen),
    }


def _gap(a, b):
    """Colour difference, 0 when either is unknown (then brightness alone decides)."""
    return abs(a - b) if np.isfinite(a) and np.isfinite(b) else 0.0
