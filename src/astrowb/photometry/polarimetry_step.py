"""photometry.polarimetry: dual-beam linear polarimetry from the light curves of the two beams."""

import numpy as np

from .. import timing
from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import describe, step
from ..hdr import number
from ..io.lzw import readable
from .lightcurve import light_curve
from .measure_params import MEASURE as _MEASURE

ANGLE_KEYS = ("HWPANGLE", "HWP-ANG", "HWP", "RETANG", "RETANGLE", "POLANGLE", "POL-ANG", "WPANGLE", "ANGLE")


@step(
    "photometry.polarimetry",
    inputs=("images", "o_xy", "e_xy"),
    outputs=("polarimetry",),
    r_ap=4.0,
    r_in=10.0,
    r_out=16.0,
    angle_key=None,
    zero_point=0.0,
)
def polarimetry_step(inputs, params, ctx):
    """Dual-beam linear polarimetry: ordinary and extraordinary images of one star on each frame, the
    half-wave-plate angle from the header (or 0, 22.5, 45, 67.5 deg repeating in time order)."""
    from astropy.io import fits

    from . import polarimetry

    paths = timing.chronological(inputs["images"])
    lc = light_curve(
        paths, inputs["o_xy"], [inputs["e_xy"]], params["r_ap"], params["r_in"], params["r_out"], ctx=ctx,
        ref_path=inputs["images"][0],  # the frame the beams were marked on (the Photometry page sends it first)
    )  # fmt: skip
    angles, source = [], None
    for p in paths:
        h = fits.getheader(readable(p))
        keys = [params["angle_key"]] if params["angle_key"] else ANGLE_KEYS
        key = next((k for k in keys if k in h), None)
        if key is None:
            angles = None
            break
        source = key
        angles.append(number(h[key], 0.0))
    if angles is None:
        angles, source = [(22.5 * i) % 90 for i in range(len(paths))], "assumed 0/22.5/45/67.5"
    fo = np.array(lc["target_flux"])
    fe = np.array(lc["comp_flux"])[:, 0]
    # photon + background errors are not kept per beam by light_curve; use the residual scatter
    r = polarimetry.dual_beam(angles, fo, fe, zero_point=params["zero_point"])
    return {
        "polarimetry": r
        | {"angles": angles, "angle_source": source, "f_o": fo.tolist(), "f_e": fe.tolist(), "files": lc["file"]}
    }


describe(
    "photometry.polarimetry",
    *_MEASURE[:3],
    P(
        "angle_key",
        "text",
        None,
        label=QT_TRANSLATE_NOOP("Steps", "Angle keyword"),
        help=QT_TRANSLATE_NOOP("Steps", "The header keyword of the half-wave plate angle"),
    ),
    P(
        "zero_point",
        "float",
        0.0,
        unit="°",
        label=QT_TRANSLATE_NOOP("Steps", "Angle zero point"),
        help=QT_TRANSLATE_NOOP("Steps", "Added to the measured position angle"),
    ),
)
