"""photometry.isophotes: the surface-brightness profile of an extended object (PHO-39)."""

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step
from ..io import fits as fitsio


@step(
    "photometry.isophotes",
    inputs=("image", "target_xy"),
    outputs=("isophotes",),
    params=(
        P(
            "sma0",
            "float",
            10.0,
            unit="px",
            min=1.0,
            label=QT_TRANSLATE_NOOP("Steps", "First semi-major axis"),
            help=QT_TRANSLATE_NOOP("Steps", "The ellipse the fit starts from"),
        ),
        P(
            "eps",
            "float",
            0.2,
            min=0.0,
            max=0.95,
            label=QT_TRANSLATE_NOOP("Steps", "First ellipticity"),
            help=QT_TRANSLATE_NOOP("Steps", "1 − b/a of the first ellipse"),
        ),
        P(
            "pa_deg",
            "float",
            0.0,
            unit="°",
            label=QT_TRANSLATE_NOOP("Steps", "First position angle"),
            help=QT_TRANSLATE_NOOP("Steps", "From the +x axis, counter-clockwise"),
        ),
        P(
            "zero_point",
            "float",
            None,
            unit="mag",
            label=QT_TRANSLATE_NOOP("Steps", "Zero point"),
            help=QT_TRANSLATE_NOOP("Steps", "With the pixel scale: the surface brightness in mag/arcsec²"),
        ),
        P(
            "pixel_scale",
            "float",
            None,
            unit="″/px",
            min=0.0,
            label=QT_TRANSLATE_NOOP("Steps", "Pixel scale"),
            help=QT_TRANSLATE_NOOP("Steps", "With the zero point: the surface brightness in mag/arcsec²"),
        ),
    ),
)
def isophotes_step(inputs, params, ctx):
    """Ellipses fitted round the object (photutils isophote): semi-major axis, intensity and its error, ellipticity,
    position angle; with a zero point and a pixel scale (arcsec) also the surface brightness in mag arcsec⁻²."""
    from ..compute.isophote import fit_isophotes, surface_brightness

    data, _, _ = fitsio.read_image(inputs["image"])
    x0, y0 = inputs["target_xy"]
    ctx.progress(0.1, "fit")
    profile, _, _ = fit_isophotes(data, x0, y0, params["sma0"], params["eps"], params["pa_deg"])
    if params["zero_point"] is not None and params["pixel_scale"]:
        sb = surface_brightness(profile["intensity"], params["zero_point"], params["pixel_scale"])
        profile["surface_brightness"] = [None if v != v else float(v) for v in sb]  # NaN is not JSON
    return {"isophotes": profile}
