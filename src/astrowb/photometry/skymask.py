"""PHO-45: the catalogue (Gaia) stars left out of every sky ring by position, before any sky statistic."""

import numpy as np

from .aperture import _CLIP, seeing_fwhm, star_mask

DEPTH = 7.0  # mag below the target (the plan: Gaia down to G + 7)
OWN = 2.0  # px: a catalogue star this close to a measured star is that star
MATCH = 3.0  # px: the Gaia star this close to the marked target gives its magnitude


def setup(catalogue, stars0):
    """{"xy", "g", "ref"} for light_curve's catalogue_sky: the field stage's Gaia stars ({"x", "y", "gmag"}, pixels of
    the reference frame, nothing fetched here) fainter than the target by at most DEPTH and not the measured stars
    themselves; None when there is no catalogue or no Gaia star on the target (no magnitude to scale from)."""
    if not catalogue or not len(stars0):
        return None
    xy = np.column_stack([np.asarray(catalogue["x"], float), np.asarray(catalogue["y"], float)])
    g = np.asarray(catalogue["gmag"], float)
    ref = np.asarray(stars0, float)
    d0 = np.hypot(*(xy - ref[0]).T)
    if not len(xy) or d0.min() > MATCH:
        return None
    g0 = g[np.argmin(d0)]
    own = (np.hypot(*(xy[:, None] - ref[None]).transpose(2, 0, 1)) <= OWN).any(axis=1)
    keep = ~own & (g < g0 + DEPTH)
    return {"xy": xy[keep], "g": g[keep], "g0": float(g0), "ref": ref}


def radii(setup_, fwhm, r_out):
    """Mask radius per star: 1.5 FWHM (the plan) times max(1, 10**(-0.2 (G - G_target))), at most r_out.
    The brightness law is ours, not from a source (the plan only says "scaled with brightness"): the smallest choice
    that grows with flux, 1x at the target's brightness and fainter, 10x at 5 mag brighter."""
    grow = np.maximum(1.0, 10.0 ** (-0.2 * (setup_["g"] - setup_["g0"])))
    return np.minimum(1.5 * fwhm * grow, r_out)


def mask(shape, setup_, xy, fwhm, r_out):
    """The sky mask of one frame: the catalogue stars moved by the median shift of the measured stars xy."""
    shift = np.nanmedian(np.asarray(xy, float) - setup_["ref"], axis=0)
    return star_mask(shape, setup_["xy"] + shift, radii(setup_, fwhm, r_out))


def frame_mask(data, xy, sky_mask, setup_, f, radii0, n_comp):
    """(sky_mask with the catalogue stars added, rejected pixels per star) of one frame; (sky_mask, None) when the
    option is off. f: the frame's FWHM if known, else measured on the main stars."""
    if setup_ is None:
        return sky_mask, None
    f = f if f is not None and np.isfinite(f) else seeing_fwhm(data, xy[: 1 + n_comp])
    new = mask(data.shape, setup_, xy, f if np.isfinite(f) else radii0[0] / 1.5, radii0[2])
    sky_mask = new if sky_mask is None else sky_mask | new
    return sky_mask, rejected(data, xy, radii0[1], radii0[2], sky_mask)


def series(rows):
    """{"sky_rejected": per frame, per star} when every kept frame has the counts."""
    if any(len(r) < 11 or r[10] is None for r in rows):
        return {}
    return {"sky_rejected": [list(r[10]) for r in rows]}


def rejected(data, xy, r_in, r_out, sky_mask):
    """Per star, the sky-ring pixels (centres inside the annulus) left out of the sky: masked ones plus those the
    3σ clip throws out of the rest (the pixels aperture.measure's median is taken over)."""
    from photutils.aperture import CircularAnnulus

    out = []
    for x, y in np.asarray(xy, float).reshape(-1, 2):
        m = CircularAnnulus((x, y), r_in=r_in, r_out=r_out).to_mask(method="center")
        vals, masked = m.get_values(data), m.get_values(sky_mask).astype(bool)
        kept = vals[~masked]
        out.append(
            int(masked.sum() + np.ma.getmaskarray(_CLIP(kept, masked=True)).sum()) if kept.size else int(masked.sum())
        )
    return out
