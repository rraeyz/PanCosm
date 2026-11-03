"""Example plugin: the sky level of an image.

Input: one FITS image. Setting: sigma (how far from the median a pixel may be before it counts as a star).
Result: the median sky and its noise, in counts. Use it to compare nights or to check flats.
"""

from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level and noise of a FITS image (stars clipped)."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    ctx.progress(0.5, "reading")
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "noise": float(std)}}
