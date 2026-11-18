"""photometry.dia_curve (plans/photometry.md PHO-29): the target's flux change on every frame by difference imaging."""

from astropy.io import fits

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step


@step(
    "photometry.dia_curve",
    inputs=("images", "target_xy"),
    outputs=("dia",),
    params=[
        P("n_best", "int", 5, min=1, label=QT_TRANSLATE_NOOP("Steps", "Frames in the reference"),
          help=QT_TRANSLATE_NOOP("Steps", "The frames of smallest FWHM that are combined into the reference")),
        P("fwhm", "float", 3.0, unit="px", min=0.5, label=QT_TRANSLATE_NOOP("Steps", "FWHM"),
          help=QT_TRANSLATE_NOOP("Steps", "Of the reference frame's stars; the PSF the flux changes are fitted with")),
    ],
)  # fmt: skip
def dia_curve_step(inputs, params, ctx):
    """Flux change of the target on every frame relative to a reference of the sharpest frames (photometry.dia_curve),
    in reference counts, with its error, the frame's scale and its mid-exposure JD (UTC)."""
    import numpy as np

    from .. import timing
    from . import dia_curve

    paths = [str(p) for p in inputs["images"]]
    ref, _ = dia_curve.reference(paths, params["n_best"])
    flux, err, scale = dia_curve.light_curve(paths, ref, np.array([inputs["target_xy"]], float), params["fwhm"])
    jd = [float(timing.mid_time(fits.getheader(p)).jd) for p in paths]
    return {"dia": {"jd_utc": jd, "flux": flux[:, 0].tolist(), "error": err[:, 0].tolist(), "scale": scale.tolist()}}
