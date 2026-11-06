"""Built-in steps. Science steps are added here (or by plugins) phase by phase."""

import numpy as np

from .. import __version__
from ..calibration import steps as _calibration_steps  # noqa: F401  (registers steps)
from ..io import fits as fitsio
from ..models import steps as _model_steps  # noqa: F401
from ..photometry import steps as _photometry_steps  # noqa: F401
from ..planning import steps as _planning_steps  # noqa: F401
from ..remotesensing import steps as _rs_steps  # noqa: F401
from ..spectroscopy import steps as _spectroscopy_steps  # noqa: F401
from ..timeseries import steps as _timeseries_steps  # noqa: F401
from .steps import step


@step(
    "fits.save_as", inputs=("source", "destination"), outputs=("destination",), overwrite=False, set_cards={}, delete=[]
)
def fits_save_as(inputs, params, ctx):
    ctx.progress(0.0, "writing")
    out = fitsio.save_as(
        inputs["source"],
        inputs["destination"],
        history=f"saved by astrowb {__version__}",
        overwrite=params["overwrite"],
        set_cards=params["set_cards"],
        delete=params["delete"],
    )
    return {"destination": str(out)}


@step("image.process", inputs=("image", "operation"), outputs=("image",), optional=("others", "output"), args={})
def image_process(inputs, params, ctx):
    """One image operation (see io.process.OPERATIONS, or "pixel_math" with an expression and other images
    named B, C, ...); the result is a new FITS file next to the input, the original is untouched."""
    import re
    from pathlib import Path

    from astropy.io import fits

    from ..io import process

    data, header, _ = fitsio.read_image(inputs["image"])
    op, args = inputs["operation"], dict(params["args"])
    if op == "pixel_math":
        images = {"A": data}
        for name, path in zip("BCDEFGH", inputs.get("others") or [], strict=False):
            images[name] = fitsio.read_image(path)[0]
        out, h = process.pixel_math(args["expression"], images, header)
        note = f"pixel math {args['expression']}"
    elif op in process.OPERATIONS:
        out, h = process.OPERATIONS[op](data, header, **args)
        note = f"{op} {args}" if args else op
    else:
        raise ValueError(f"unknown operation {op}")
    h = process.history(h, f"astrowb {__version__}: {note}")
    src = Path(inputs["image"])
    stem = re.sub(r"\.(fits?|fts)$", "", src.name, flags=re.I)
    dest = Path(inputs.get("output") or src.with_name(f"{stem}_{op}.fits"))
    k = 2
    while not inputs.get("output") and dest.exists():  # never overwrite an earlier result
        dest, k = src.with_name(f"{stem}_{op}_{k}.fits"), k + 1
    fits.PrimaryHDU(np.asarray(out, np.float32), h).writeto(
        dest, overwrite=bool(inputs.get("output")), output_verify="silentfix"
    )
    return {"image": str(dest)}


@step("image.catalogue", inputs=("image",), outputs=("stars",), catalogue="gaia", mag_limit=16.0)
def catalogue_step(inputs, params, ctx):
    """Catalogue stars (Gaia DR3 or VSX, from VizieR) inside a plate-solved image, with their pixel positions."""
    from astropy.wcs import WCS

    from .. import overlays

    data, header, _ = fitsio.read_image(inputs["image"])
    wcs = WCS(header).celestial
    if not wcs.has_celestial:
        raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
    ny, nx = data.shape
    centre = wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2)
    corner = wcs.pixel_to_world(0, 0)
    ctx.progress(0.1, "catalogue")
    stars = overlays.query_catalogue(
        centre.ra.deg, centre.dec.deg, centre.separation(corner).deg * 1.05, params["catalogue"], params["mag_limit"]
    )
    return {"stars": overlays.to_pixels(wcs, data.shape, stars)}


@step(
    "image.convert",
    inputs=("images", "output_dir"),
    outputs=("written",),
    fmt="png",
    interval="zscale",
    stretch="linear",
)
def convert_step(inputs, params, ctx):
    """Many FITS images to PNG / JPEG (as displayed, with the given interval and stretch) or 32-bit TIFF (the data).
    Names are kept (light_001.fits -> light_001.png); an existing picture is never overwritten."""
    from pathlib import Path

    from ..display import save_picture

    out = Path(inputs["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    ext = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpg", "tif": ".tif", "tiff": ".tif"}[params["fmt"].lower()]
    written = []
    for i, src in enumerate(inputs["images"]):
        ctx.check()
        ctx.progress(i / len(inputs["images"]), "writing")
        data, _, _ = fitsio.read_image(src)
        dest, k = out / (Path(src).stem + ext), 2
        while dest.exists():
            dest, k = out / f"{Path(src).stem}_{k}{ext}", k + 1
        written.append(str(save_picture(dest, data, params["interval"], params["stretch"])))
    return {"written": written}


@step("image.minor_planets", inputs=("image",), outputs=("objects",), mag_limit=20.0)
def minor_planets_step(inputs, params, ctx):
    """Asteroids and comets inside a plate-solved image at its mid-exposure time (IMCCE SkyBoT), with pixels."""
    from astropy.wcs import WCS

    from .. import overlays, timing

    data, header, _ = fitsio.read_image(inputs["image"])
    wcs = WCS(header).celestial
    if not wcs.has_celestial:
        raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
    t = timing.mid_time(header)
    ny, nx = data.shape
    centre = wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2)
    radius = centre.separation(wcs.pixel_to_world(0, 0)).deg * 1.05
    ctx.progress(0.1, "catalogue")
    found = overlays.minor_planets(centre.ra.deg, centre.dec.deg, radius, t.utc.jd, params["mag_limit"])
    return {"objects": overlays.to_pixels(wcs, data.shape, found)}


@step(
    "image.finder_chart",
    inputs=("output",),
    outputs=("chart", "labelled"),
    optional=("image", "ra", "dec"),
    fov_deg=0.3,
    mag_limit=14.0,
    title="",
)
def finder_chart_step(inputs, params, ctx):
    """Finder chart (PNG/PDF) from a plate-solved image, or from DSS around ra/dec; comparison stars labelled with
    their V magnitude x 10 from Gaia (labels left out when the catalogue cannot be reached)."""
    from astropy.wcs import WCS

    from .. import overlays

    ctx.progress(0.05, "reading")
    if inputs.get("image"):
        data, header, _ = fitsio.read_image(inputs["image"])
        wcs = WCS(header).celestial
        if not wcs.has_celestial:
            raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
        ny, nx = data.shape
        if inputs.get("ra") is None:
            centre = wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2)
            inputs = inputs | {"ra": centre.ra.deg, "dec": centre.dec.deg}
    else:
        data, wcs = overlays.dss_image(float(inputs["ra"]), float(inputs["dec"]), params["fov_deg"])
    ny, nx = data.shape
    centre = wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2)
    radius = centre.separation(wcs.pixel_to_world(0, 0)).deg * 1.05
    ctx.progress(0.4, "catalogue")
    try:
        stars = overlays.query_catalogue(centre.ra.deg, centre.dec.deg, radius, "gaia", params["mag_limit"] + 1)
    except Exception:  # offline: the chart is still useful without labels
        stars = []
    target = (float(inputs["ra"]), float(inputs["dec"]))
    path = overlays.finder_chart(inputs["output"], data, wcs, target, stars, params["title"], params["mag_limit"])
    return {"chart": path, "labelled": sum(1 for s in stars if s.get("v") is not None)}


@step("astrometry.solve", inputs=("image",), outputs=("solved",), radius_deg=30.0, refine_gaia=True)
def plate_solve(inputs, params, ctx):
    """Plate-solve an image; the solution goes into a copy (<name>_wcs.fits), the original is untouched."""
    from pathlib import Path

    src = Path(inputs["image"])
    ctx.progress(0.0, "plate solving")
    return {"solved": str(solved_copy(src, params["radius_deg"], params["refine_gaia"]))}


def solved_copy(src, radius_deg=30.0, refine_gaia=True):
    """Plate-solve src; the solution goes into a copy (<name>_wcs.fits), the original is untouched. Returns the
    copy's path. refine_gaia: the solution is then fitted again to Gaia DR3 (gaia.refine_wcs) when the catalogue
    can be reached; without internet the solver's solution stays and the header says why (ASTRNOTE)."""
    import re
    from pathlib import Path

    from astropy.io import fits

    from .. import astrometry
    from ..photometry.lightcurve import target_coord

    src = Path(src)
    from ..hdr import get

    with fits.open(src) as hdul:
        hdu = hdul[fitsio.find_image_hdu(hdul)]
        h, ny = hdu.header, hdu.shape[-2]
    hint = target_coord(h)  # the pointing and the pixel scale from the header make solving much faster
    ra, dec = (None, None) if hint is None else (hint.ra.deg, hint.dec.deg)
    pixel_um, focal_mm = get(h, "XPIXSZ", "PIXSIZE1"), get(h, "FOCALLEN")
    scale = 206.265 * pixel_um / focal_mm if pixel_um and focal_mm else None  # arcsec per (binned) pixel
    fov = scale * ny / 3600 if scale else 0.0
    wcs = astrometry.solve(src, None, ra, dec, radius_deg, fov_deg=fov, scale_arcsec=scale)
    out = src.with_name(re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", src.name, flags=re.I) + "_wcs.fits")
    fitsio.save_as(src, out, history="copy for plate solving", overwrite=True)
    astrometry.apply_solution(out, wcs, (astrometry.find_solver() or ("", []))[0])
    if refine_gaia:
        from .. import gaia

        with fits.open(out, mode="update") as hdul:
            hdu = hdul[fitsio.find_image_hdu(hdul)]
            try:
                refined, info = gaia.refine_wcs(np.asarray(hdu.data, float), hdu.header)
            except Exception as e:  # noqa: BLE001 - offline, too few stars: the solver's solution is kept
                hdu.header["ASTRNOTE"] = (f"not refined on Gaia DR3: {e}"[:68], "plate solution")
            else:
                astrometry.apply_solution_header(hdu.header, refined)
                hdu.header.add_history(
                    f"WCS refitted to {info['matched']} Gaia DR3 stars: rms {info['rms_before']:.2f} -> "
                    f"{info['rms_after']:.2f} arcsec"
                )
    return out


@step("image.rgb", inputs=("red", "green", "blue", "output"), outputs=("rgb",), stretch=0.5, q=8.0, align=True)
def image_rgb(inputs, params, ctx):
    """Colour picture (PNG) from red, green and blue frames, aligned and stretched together."""
    from matplotlib.image import imsave

    from ..io import process

    ctx.progress(0.1, "reading")
    frames = [fitsio.read_image(inputs[k])[0] for k in ("red", "green", "blue")]
    ctx.progress(0.4, "aligning")
    rgb = process.colour_image(*frames, stretch=params["stretch"], q=params["q"], align=params["align"])
    imsave(inputs["output"], rgb)
    return {"rgb": str(inputs["output"])}


@step("app.check", outputs=("report", "ok"))
def app_check(inputs, params, ctx):
    """The installation (every module, library and data file) and every web service the application uses."""
    from .. import selfcheck

    ctx.progress(0.1, "checking")
    results = selfcheck.offline() + selfcheck.online()
    return {"report": selfcheck.report(results), "ok": all(ok for _, ok, _ in results)}


@step("sample.night", inputs=("folder",), outputs=("truth",))
def sample_night(inputs, params, ctx):
    """Practice data: a simulated night of an eclipsing binary with calibration frames (see the Guide)."""
    from .. import sampledata

    ctx.progress(0.1, "simulating")
    return {"truth": sampledata.make(inputs["folder"])}
