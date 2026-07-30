"""Example plugin: how long to expose for a wanted signal-to-noise (CCD equation, Howell 2006).

No file needed, only numbers: the star's magnitude, your system's zero point (the magnitude that gives one
electron per second; measure it once on a star of known magnitude), sky brightness in electrons per pixel per
second, read noise, aperture radius in pixels and the wanted S/N. Result: the exposure time in seconds.
"""

import math

from astrowb.engine.steps import step


@step(
    "plugin.exposure_time",
    outputs=("seconds",),
    magnitude=12.0,
    zero_point=21.0,
    sky_e_per_s=5.0,
    read_noise=10.0,
    aperture_px=5.0,
    snr=100.0,
)
def exposure_time(inputs, params, ctx):
    """Exposure time for a wanted S/N from the CCD equation."""
    star = 10 ** (-0.4 * (params["magnitude"] - params["zero_point"]))  # electrons per second
    npix = math.pi * params["aperture_px"] ** 2
    a = star**2
    b = -(params["snr"] ** 2) * (star + npix * params["sky_e_per_s"])
    c = -(params["snr"] ** 2) * npix * params["read_noise"] ** 2
    t = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)  # S/N^2 = (S t)^2 / (S t + n sky t + n RN^2)
    return {"seconds": round(t, 3)}
