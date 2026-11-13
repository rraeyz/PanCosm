"""The field image with the apertures (plans/photometry.md PHO-27 item 3, TFOP's required "field image with
apertures"): the frame stretched by zscale, the target's and comparison stars' apertures labelled, and the 2.5′
circle TFOP checks neighbours within when the pixel scale is known."""

import numpy as np


def write(path, data, target, comps, r_ap, scale_arcsec=None, extras=()):
    import matplotlib

    matplotlib.use("Agg", force=False)
    from astropy.visualization import ZScaleInterval
    from matplotlib.colors import Normalize
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle

    data = np.asarray(data, float)
    fig = Figure(figsize=(7, 7 * data.shape[0] / max(data.shape[1], 1)), layout="constrained")
    ax = fig.add_subplot()
    lo, hi = ZScaleInterval().get_limits(data)
    if not lo < hi:  # a noiseless frame (zscale's line fit gave them crossed on Windows): the whole range
        lo, hi = float(np.nanmin(data)), float(np.nanmax(data)) + 1e-9
    ax.imshow(data, origin="lower", cmap="gray_r", norm=Normalize(lo, hi, clip=True))
    rings = [(target, "T1", "tab:green"), *((c, f"C{i + 2}", "tab:red") for i, c in enumerate(comps))]
    rings += [(xy, f"X{i + 1}", "tab:blue") for i, (xy, _role) in enumerate(extras)]
    for (x, y), label, colour in rings:
        ax.add_patch(Circle((x, y), r_ap, fill=False, color=colour, lw=1))
        ax.annotate(label, (x + r_ap, y + r_ap), color=colour, fontsize=8)
    if scale_arcsec:
        ax.add_patch(Circle(target, 150.0 / scale_arcsec, fill=False, color="tab:orange", lw=1, ls="--"))
        ax.text(0.01, 0.01, "2.5′", transform=ax.transAxes, color="tab:orange", fontsize=8)
    ax.set_xlabel("x (px)")
    ax.set_ylabel("y (px)")
    fig.savefig(path, dpi=150)
    return path


def seeing_profile(path, data, xy, radii):
    """The target's radial profile (TFOP's seeing-profile plot): every pixel's value against its distance from the
    centre, sky taken off, with the aperture and the sky ring drawn; radii (aperture, inner, outer) in px."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    from matplotlib.figure import Figure

    data = np.asarray(data, float)
    r_ap, r_in, r_out = radii
    half = int(np.ceil(r_out)) + 2
    x0, y0 = int(round(xy[0])), int(round(xy[1]))
    cut = data[max(0, y0 - half) : y0 + half + 1, max(0, x0 - half) : x0 + half + 1]
    yy, xx = np.indices(cut.shape)
    d = np.hypot(xx + max(0, x0 - half) - xy[0], yy + max(0, y0 - half) - xy[1])
    sky = float(np.median(cut[(d >= r_in) & (d < r_out)]))
    fig = Figure(figsize=(6, 4), layout="constrained")
    ax = fig.add_subplot()
    ax.plot(d.ravel(), (cut - sky).ravel(), ".", ms=2)
    for r, style in ((r_ap, "-"), (r_in, "--"), (r_out, "--")):
        ax.axvline(r, color="gray", ls=style, lw=1)
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xlim(0, r_out + 2)
    ax.set_xlabel("radius (px)")
    ax.set_ylabel("counts − sky (ADU)")
    fig.savefig(path, dpi=150)
    return path
