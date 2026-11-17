"""photometry.afrho: a comet's Afρ from one image (PHO-39)."""

import numpy as np

from ..engine.params import QT_TRANSLATE_NOOP, P
from ..engine.steps import step
from ..hdr import get
from ..io import fits as fitsio


def _p(name, default, unit, label, help, **kw):
    return P(name, "float", default, unit=unit, label=label, help=help, **kw)


@step(
    "photometry.afrho",
    inputs=("image", "target_xy"),
    outputs=("afrho",),
    params=(
        _p(
            "rho_km",
            10000.0,
            "km",
            QT_TRANSLATE_NOOP("Steps", "Aperture radius at the comet"),
            QT_TRANSLATE_NOOP("Steps", "Physical radius ρ of the measuring circle"),
            min=1.0,
        ),
        _p(
            "sky_in_km",
            50000.0,
            "km",
            QT_TRANSLATE_NOOP("Steps", "Sky ring inner radius"),
            QT_TRANSLATE_NOOP("Steps", "At the comet; far enough to hold no coma"),
            min=1.0,
        ),
        _p(
            "sky_out_km",
            70000.0,
            "km",
            QT_TRANSLATE_NOOP("Steps", "Sky ring outer radius"),
            QT_TRANSLATE_NOOP("Steps", "At the comet"),
            min=1.0,
        ),
        _p(
            "delta_au",
            None,
            "au",
            QT_TRANSLATE_NOOP("Steps", "Distance from the Earth (Δ)"),
            QT_TRANSLATE_NOOP("Steps", "Geocentric distance of the comet at the time of the image"),
            min=0.0,
        ),
        _p(
            "r_h_au",
            None,
            "au",
            QT_TRANSLATE_NOOP("Steps", "Distance from the Sun (r)"),
            QT_TRANSLATE_NOOP("Steps", "Heliocentric distance of the comet at the time of the image"),
            min=0.0,
        ),
        _p(
            "pixel_scale",
            None,
            "″/px",
            QT_TRANSLATE_NOOP("Steps", "Pixel scale"),
            QT_TRANSLATE_NOOP("Steps", "Arcseconds per pixel of the image"),
            min=0.0,
        ),
        _p(
            "zero_point",
            None,
            "mag",
            QT_TRANSLATE_NOOP("Steps", "Zero point"),
            QT_TRANSLATE_NOOP("Steps", "Magnitude of 1 ADU in this image and band"),
        ),
        _p(
            "m_sun",
            None,
            "mag",
            QT_TRANSLATE_NOOP("Steps", "The Sun's magnitude at 1 au"),
            QT_TRANSLATE_NOOP("Steps", "Apparent magnitude of the Sun in the same band, from a published table"),
        ),
    ),  # fmt: skip
)
def afrho_step(inputs, params, ctx):
    """Afρ (A'Hearn et al. 1984) in cm from the comet's flux in a circle of physical radius ρ, the sky from a far
    ring; the band's solar magnitude and the image's zero point come from the user (none is bundled)."""
    from .comet import afrho_mag, comet_flux

    need = ("delta_au", "r_h_au", "pixel_scale", "zero_point", "m_sun")
    missing = ", ".join(k for k in need if params[k] is None)
    if missing:
        raise ValueError(f"the Afrho step needs {missing}")
    data, header, _ = fitsio.read_image(inputs["image"])
    ctx.progress(0.2, "photometry")
    flux, err, r_px = comet_flux(
        data, inputs["target_xy"], params["rho_km"], params["delta_au"], params["pixel_scale"],
        params["sky_in_km"], params["sky_out_km"], gain=float(get(header, "EGAIN", "GAIN", default=1.0) or 1.0),
    )  # fmt: skip
    if not flux > 0:
        raise ValueError("no comet flux above the sky in the aperture")
    m = params["zero_point"] - 2.5 * np.log10(flux)
    value = afrho_mag(m, params["m_sun"], params["r_h_au"], params["delta_au"], params["rho_km"])
    return {
        "afrho": {
            "afrho_cm": float(value),
            "afrho_err_cm": float(value * err / flux),
            "flux": flux,
            "flux_err": err,
            "mag": float(m),
            "aperture_px": float(r_px),
        }  # fmt: skip
    }
