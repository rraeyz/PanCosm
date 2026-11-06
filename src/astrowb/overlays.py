"""What is drawn over an image (as DS9 and AstroImageJ do): contours, a sky-coordinate grid, catalogue stars
and DS9 region files. Everything is in 0-based array pixels (x = column, y = row), the viewer's coordinates.
No Qt here: the viewer only draws the polylines, circles and labels these functions return.
"""

import re

import numpy as np


def contour_levels(data, n=6):
    """n levels spaced logarithmically from 3 sigma above the sky to 90 % of the brightest pixel."""
    from astropy.stats import sigma_clipped_stats

    d = np.asarray(data, float)
    _, med, std = sigma_clipped_stats(d[:: max(1, d.shape[0] // 512), :: max(1, d.shape[1] // 512)])
    lo, hi = med + 3 * std, med + 0.9 * (np.nanmax(d) - med)
    if not np.isfinite(lo) or hi <= lo:
        return []
    return (med + np.geomspace(lo - med, hi - med, n)).tolist()


def contours(data, levels, smooth=1.0):
    """{level: [polyline [(x, y), ...], ...]} through the (lightly smoothed) image."""
    import contourpy
    from scipy.ndimage import gaussian_filter

    d = np.nan_to_num(np.asarray(data, float), nan=float(np.nanmedian(data)))
    if smooth:
        d = gaussian_filter(d, smooth)
    gen = contourpy.contour_generator(z=d, line_type=contourpy.LineType.Separate)
    return {float(lv): [line.tolist() for line in gen.lines(lv) if len(line) > 1] for lv in levels}


def _nice_step(span_deg, n=5):
    """A round grid step (degrees) giving about n lines over the span."""
    steps = [s / 3600 for s in (1, 2, 5, 10, 15, 30)] + [s / 60 for s in (1, 2, 5, 10, 15, 30)]
    steps += [1, 2, 5, 10, 15, 30, 45]
    return next((s for s in steps if span_deg / s <= n), 90)


def wcs_grid(wcs, shape, n=5, samples=100):
    """Lines of constant RA and Dec across the image: [(kind "ra" | "dec", value deg, polyline, label)]."""
    import astropy.units as u
    from astropy.coordinates import Angle

    ny, nx = shape
    yy, xx = np.mgrid[0 : ny : complex(0, 20), 0 : nx : complex(0, 20)]
    sky = wcs.pixel_to_world(xx.ravel(), yy.ravel())
    ra, dec = sky.ra.deg, sky.dec.deg
    ra_span = np.ptp(np.unwrap(np.radians(ra))) * 180 / np.pi
    out = []
    dstep = _nice_step(np.ptp(dec), n)
    rstep = _nice_step(ra_span, n)
    dec_lo, dec_hi = dec.min(), dec.max()
    ra_c = float(np.degrees(np.arctan2(np.sin(np.radians(ra)).mean(), np.cos(np.radians(ra)).mean())) % 360)
    ra_vals = np.arange(np.floor((ra_c - ra_span) / rstep), np.ceil((ra_c + ra_span) / rstep) + 1) * rstep
    for v in ra_vals:
        d = np.linspace(dec_lo, dec_hi, samples)
        x, y = wcs.world_to_pixel_values(np.full(samples, v % 360), d)
        line = _inside(x, y, nx, ny)
        if line:
            label = Angle(v % 360, u.deg).to_string(unit=u.hourangle, sep=":", precision=0, pad=True)
            out.append(("ra", float(v % 360), line, label))
    for v in np.arange(np.floor(dec_lo / dstep), np.ceil(dec_hi / dstep) + 1) * dstep:
        r = ra_c + np.linspace(-ra_span, ra_span, samples)
        x, y = wcs.world_to_pixel_values(r % 360, np.full(samples, v))
        line = _inside(x, y, nx, ny)
        if line:
            out.append(("dec", float(v), line, Angle(v, u.deg).to_string(sep=":", precision=0, alwayssign=True)))
    return out


def _inside(x, y, nx, ny):
    ok = np.isfinite(x) & np.isfinite(y) & (x >= -0.5) & (x <= nx - 0.5) & (y >= -0.5) & (y <= ny - 0.5)
    return [(float(a), float(b)) for a, b in zip(x[ok], y[ok], strict=True)] if ok.sum() > 1 else []


# --- catalogues -----------------------------------------------------------------------------------------------
CATALOGUES = {
    "gaia": ("I/355/gaiadr3", "Source", "Gmag"),
    "vsx": ("B/vsx/vsx", "Name", "max"),
}


def query_catalogue(ra, dec, radius_deg, catalogue="gaia", mag_limit=16.0, row_limit=2000, query=None):
    """[{name, ra, dec, mag}] around (ra, dec) from VizieR (Gaia DR3 or the AAVSO VSX variable stars)."""
    cat, name_col, mag_col = CATALOGUES[catalogue]
    default = query is None  # the program's own look-up (tests give their own)
    if query is None:
        import astropy.units as u
        from astropy.coordinates import SkyCoord
        from astroquery.vizier import Vizier

        from .mirrors import cds

        def ask(server, cat, ra, dec, radius_deg, mag_col, mag_limit):
            v = Vizier(columns=["*", "_RAJ2000", "_DEJ2000"], row_limit=row_limit, vizier_server=server)
            if catalogue == "gaia":
                v.column_filters = {mag_col: f"<{mag_limit}"}
            tables = v.query_region(SkyCoord(ra * u.deg, dec * u.deg), radius=radius_deg * u.deg, catalog=cat)
            return tables[0] if len(tables) else []

        def query(*args):
            return cds("vizier", lambda server: ask(server, *args))

    esa = catalogue == "gaia" and default  # the ESA Gaia archive can stand in for VizieR
    try:
        rows = query(cat, ra, dec, radius_deg, mag_col, mag_limit)
    except Exception:
        if not esa:
            raise
        rows = []
    if esa and len(rows) == 0:  # every VizieR server down, or one that gives nothing for Gaia (Harvard)
        from .gaia import chart_stars

        return chart_stars(ra, dec, radius_deg, mag_limit, row_limit)
    out = []
    for r in rows:
        mag = r[mag_col] if mag_col in r.colnames else None
        mag = None if mag is None or np.ma.is_masked(mag) else float(mag)
        star = {"name": str(r[name_col]), "ra": float(r["_RAJ2000"]), "dec": float(r["_DEJ2000"]), "mag": mag}
        if (
            mag is not None
            and "BPmag" in r.colnames
            and not np.ma.is_masked(r["BPmag"])
            and not np.ma.is_masked(r["RPmag"])
        ):
            from .photometry.catalog import from_gaia  # Johnson V for chart labels (Riello et al. 2021)

            star["v"] = float(from_gaia("V", mag, float(r["BPmag"]) - float(r["RPmag"])))
        out.append(star)
    return out


def to_pixels(wcs, shape, stars):
    """The stars inside the image with their pixel positions (x, y added)."""
    if not stars:
        return []
    x, y = wcs.world_to_pixel_values([s["ra"] for s in stars], [s["dec"] for s in stars])
    ny, nx = shape
    return [
        s | {"x": float(a), "y": float(b)} for s, a, b in zip(stars, x, y, strict=True) if 0 <= a < nx and 0 <= b < ny
    ]


# --- DS9 region files ---------------------------------------------------------------------------------------
# DS9 "image" coordinates are 1-based FITS pixels; ours are 0-based.

_SHAPE = re.compile(r"^\s*(circle|box|line|point|text|ellipse)\s*\(([^)]*)\)\s*#?(.*)$", re.I)


def _text_of(comment):
    m = re.search(r"text\s*=\s*[{\"']([^}\"']*)", comment or "")
    return m.group(1) if m else ""


def _value(token, unit_scale):
    """A DS9 number, possibly with a unit: 5" (arcsec), 1' (arcmin), 2d, or plain (pixels / degrees)."""
    token = token.strip()
    for suffix, factor in (('"', 1 / 3600), ("'", 1 / 60), ("d", 1.0)):
        if token.endswith(suffix):
            return float(token[:-1]) * factor * unit_scale
    return float(token)


def read_regions(text, wcs=None):
    """[{shape, x, y, ...}] in 0-based pixels from a DS9 region file (image, physical or fk5/icrs with a WCS)."""
    system, out = "image", []
    pix_per_deg = None
    if wcs is not None:
        from astropy.wcs.utils import proj_plane_pixel_scales

        pix_per_deg = 1 / float(np.mean(proj_plane_pixel_scales(wcs.celestial)))
    for raw in text.splitlines():
        line = raw.strip()
        if not line or (line.startswith("#") and not line.lower().startswith("# text")):
            continue
        if line.lower().startswith("# text"):
            line = line[1:].strip()
        low = line.lower().split("#")[0].strip().rstrip(";")
        if low in ("image", "physical", "fk5", "icrs", "j2000", "fk4", "galactic", "linear"):
            system = low
            continue
        if low.startswith("global"):
            continue
        m = _SHAPE.match(line)
        if not m:
            continue
        shape, args, comment = m.group(1).lower(), [a for a in m.group(2).split(",")], m.group(3)
        sky = system in ("fk5", "icrs", "j2000")
        if sky and wcs is None:
            continue  # sky regions need the image's WCS

        def point(a, b, sky=sky):
            if sky:
                from astropy.coordinates import Angle

                ra = Angle(a, unit="hourangle" if ":" in a else "deg").deg
                dec = Angle(b, unit="deg").deg
                px, py = wcs.world_to_pixel_values(ra, dec)
                return float(px), float(py)
            return float(a) - 1, float(b) - 1

        def length(a, sky=sky):
            return _value(a, pix_per_deg) if sky else float(a)

        reg = {"shape": shape, "text": _text_of(comment)}
        if shape in ("circle", "point", "text", "box", "ellipse"):
            reg["x"], reg["y"] = point(args[0], args[1])
        if shape == "circle":
            reg["r"] = length(args[2])
        elif shape in ("box", "ellipse"):
            reg["w"], reg["h"] = length(args[2]), length(args[3])
            reg["angle"] = float(args[4]) if len(args) > 4 else 0.0
        elif shape == "line":
            (reg["x"], reg["y"]), (reg["x2"], reg["y2"]) = point(args[0], args[1]), point(args[2], args[3])
        out.append(reg)
    return out


def write_regions(regions, wcs=None):
    """DS9 region file text: circles (and texts) in fk5 when a WCS is given, else in image pixels."""
    lines = ["# Region file format: DS9 version 4.1", 'global color=green font="helvetica 10 normal"']
    if wcs is not None:
        from astropy.wcs.utils import proj_plane_pixel_scales

        arcsec_per_pix = 3600 * float(np.mean(proj_plane_pixel_scales(wcs.celestial)))
        lines.append("fk5")
    else:
        lines.append("image")
    for r in regions:
        text = f" # text={{{r['text']}}}" if r.get("text") else ""
        if wcs is not None:
            ra, dec = wcs.pixel_to_world_values(r["x"], r["y"])
            pos = f"{float(ra):.7f},{float(dec):+.7f}"
            size = f'{r.get("r", 0) * arcsec_per_pix:.3f}"'
        else:
            pos = f"{r['x'] + 1:.3f},{r['y'] + 1:.3f}"
            size = f"{r.get('r', 0):.3f}"
        if r.get("shape", "circle") == "circle":
            lines.append(f"circle({pos},{size}){text}")
        else:
            lines.append(f"point({pos}) # point=x{text}")
    return "\n".join(lines) + "\n"


# --- finder charts --------------------------------------------------------------------------------------------
HIPS2FITS = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"


def dss_image(ra, dec, fov_deg=0.3, size=800, fetch=None):
    """A north-up DSS2 red image around (ra, dec) from the CDS hips2fits service: (data, WCS)."""
    import io
    import urllib.parse
    import urllib.request

    from astropy.io import fits
    from astropy.wcs import WCS

    params = {
        "hips": "CDS/P/DSS2/red",
        "width": size,
        "height": size,
        "fov": fov_deg,
        "projection": "TAN",
        "coordsys": "icrs",
        "ra": ra,
        "dec": dec,
        "format": "fits",
    }
    if fetch is None:

        def fetch(url):
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https service)
                return r.read()

    with fits.open(io.BytesIO(fetch(HIPS2FITS + "?" + urllib.parse.urlencode(params)))) as hdul:
        return np.asarray(hdul[0].data, float), WCS(hdul[0].header).celestial


def finder_chart(path, data, wcs, target, stars=(), title="", mag_limit=None, comparison_limit=12):
    """PNG (or PDF) chart in the AAVSO style: black stars on white, sky-coordinate grid, north and east arrows, the
    target marked, the brightest catalogue stars labelled with their V magnitude x 10 without the decimal point
    (11.2 -> 112). target: (ra, dec) degrees. stars: as query_catalogue returns (with "v" when known)."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from astropy.visualization import ImageNormalize, LinearStretch, ZScaleInterval

    fig = plt.figure(figsize=(7, 7.6))
    ax = fig.add_subplot(projection=wcs)
    norm = ImageNormalize(data, interval=ZScaleInterval(), stretch=LinearStretch())
    ax.imshow(data, origin="lower", cmap="gray_r", norm=norm)
    ax.coords.grid(color="0.6", ls=":", lw=0.5)
    ax.coords[0].set_axislabel("RA (J2000)")
    ax.coords[1].set_axislabel("Dec (J2000)")
    tx, ty = wcs.world_to_pixel_values(target[0], target[1])
    ny, nx = data.shape
    ax.plot([tx - 0.06 * nx, tx - 0.025 * nx], [ty, ty], "r-", lw=1.5)  # two ticks pointing at the target
    ax.plot([tx, tx], [ty + 0.025 * ny, ty + 0.06 * ny], "r-", lw=1.5)
    labelled = sorted((s for s in stars if s.get("v") is not None), key=lambda s: s["v"])
    if mag_limit is not None:
        labelled = [s for s in labelled if s["v"] <= mag_limit]
    for s in labelled[:comparison_limit]:
        x, y = wcs.world_to_pixel_values(s["ra"], s["dec"])
        if 0 <= x < nx and 0 <= y < ny and np.hypot(x - tx, y - ty) > 0.02 * nx:
            ax.text(x + 0.012 * nx, y, f"{round(s['v'] * 10):d}", color="blue", fontsize=8, va="center")
    # compass: arrows of 10 % of the field towards north and east, from the corner
    from astropy.wcs.utils import proj_plane_pixel_scales

    cx, cy = 0.88 * nx, 0.12 * ny
    ra0, dec0 = wcs.pixel_to_world_values(cx, cy)
    step = 0.1 * ny * float(np.mean(proj_plane_pixel_scales(wcs)))
    for name, (dra, ddec) in (("N", (0, step)), ("E", (step / np.cos(np.radians(dec0)), 0))):
        ex, ey = wcs.world_to_pixel_values(ra0 + dra, dec0 + ddec)
        ax.annotate("", (ex, ey), (cx, cy), arrowprops={"arrowstyle": "->", "color": "k"})
        ax.text(ex, ey, name, fontsize=9, ha="center", va="center")
    scale = float(np.mean(proj_plane_pixel_scales(wcs))) * 60
    field = f"field {nx * scale:.1f}' x {ny * scale:.1f}'"
    ax.set_title(f"{title}   {field}" if title else field, fontsize=10)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


# --- minor planets ---------------------------------------------------------------------------------------------
SKYBOT = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php"


def parse_skybot(text):
    """[{name, number, ra, dec, mag, kind}] from SkyBoT's text answer ("# Num | Name | RA(h) | DE(deg) | ...")."""
    from astropy.coordinates import Angle

    rows, cols = [], None
    for line in text.splitlines():
        if line.startswith("# Num"):
            cols = [c.strip() for c in line[1:].split("|")]
            continue
        if not line.strip() or line.startswith("#") or cols is None:
            continue
        cells = dict(zip(cols, (c.strip() for c in line.split("|")), strict=False))
        try:
            ra = Angle(cells["RA(h)"], unit="hourangle").deg
            dec = Angle(cells["DE(deg)"], unit="deg").deg
        except (KeyError, ValueError):
            continue
        mag = cells.get("Mv", "")
        rows.append(
            {
                "name": cells.get("Name", ""),
                "number": cells.get("Num", "-"),
                "ra": float(ra),
                "dec": float(dec),
                "mag": float(mag) if mag.replace(".", "", 1).isdigit() else None,
                "kind": cells.get("Class", ""),
            }
        )
    return rows


def minor_planets(ra, dec, radius_deg, jd, mag_limit=None, fetch=None):
    """Asteroids and comets in the field at the time `jd` (UTC), from the IMCCE SkyBoT service (geocentric
    positions: the parallax is a few arcseconds for main-belt objects, more for near-Earth ones)."""
    import urllib.parse
    import urllib.request

    params = {
        "-ep": f"{jd:.6f}",
        "-ra": f"{ra:.6f}",
        "-dec": f"{dec:.6f}",
        "-rd": f"{radius_deg:.5f}",
        "-mime": "text",
        "-output": "object",
        "-loc": "500",
    }
    url = SKYBOT + "?" + urllib.parse.urlencode(params)
    if fetch is None:

        def fetch(url):
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https service)
                return r.read().decode("utf-8", errors="replace")

    found = parse_skybot(fetch(url))
    return [p for p in found if mag_limit is None or p["mag"] is None or p["mag"] <= mag_limit]
