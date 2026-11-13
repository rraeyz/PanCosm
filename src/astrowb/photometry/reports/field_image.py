"""The field image with the apertures (plans/photometry.md PHO-27 item 3, TFOP's required "field image with
apertures"): the frame stretched by zscale, the target's and comparison stars' apertures labelled, and the 2.5′
circle TFOP checks neighbours within when the pixel scale is known."""

import numpy as np


def write(path, data, target, comps, r_ap, scale_arcsec=None, extras=()):
    import matplotlib

    matplotlib.use("Agg", force=False)
    from astropy.visualization import ImageNormalize, ZScaleInterval
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle

    data = np.asarray(data, float)
    fig = Figure(figsize=(7, 7 * data.shape[0] / max(data.shape[1], 1)), layout="constrained")
    ax = fig.add_subplot()
    ax.imshow(data, origin="lower", cmap="gray_r", norm=ImageNormalize(data, interval=ZScaleInterval()))
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
