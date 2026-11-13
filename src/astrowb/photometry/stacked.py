"""Faint targets measured on running stacks (plans/photometry.md PHO-42): groups of N consecutive frames aligned on
the stars and combined with rejection (calibration.stacking), each written as one frame whose counts are the
group's sum (so the gain still turns counts into electrons), EXPTIME the summed exposure and DATE-AVG the mean
mid-time; the light curve is then measured on them as on any frames."""

import numpy as np


def running_stacks(paths, n, folder, ctx=None):
    """The frames in time order, in groups of n (a last group shorter than n / 2 joins the one before); returns the
    stacked files written into folder."""
    from pathlib import Path

    from .. import timing
    from ..calibration.stacking import save_stack, stack
    from ..hdr import get

    paths = timing.chronological([str(p) for p in paths])
    groups = [paths[i : i + n] for i in range(0, len(paths), n)]
    if len(groups) > 1 and len(groups[-1]) < n / 2:
        groups[-2] += groups.pop()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for k, group in enumerate(groups):
        if ctx:
            ctx.check()
            ctx.progress(0.5 * k / len(groups), "stacking")
        # few frames give no σ to reject against (4 values: the clipping itself adds noise): a plain mean then
        image, count, header = stack(group, align="translation", rejection="sigma" if len(group) >= 8 else "none")
        exptime = get(header, "EXPTIME", "EXPOSURE", default=0.0) or 0.0
        header["EXPTIME"] = (float(exptime) * len(group), "summed exposure of the combined frames")
        header["NCOMBINE"] = (len(group), "frames combined")
        out.append(save_stack(folder / f"stack_{k:04d}.fits", np.asarray(image) * count, count, header))
    return out


def combined(images, inputs, ref, n, ctx=None):
    """The step's frames, inputs and reference frame with n > 1: the running stacks in a temporary folder, the first
    stack taking the first frame's place as the frame the stars were marked on."""
    if n <= 1:
        return images, inputs, ref
    import tempfile

    first = str(ref) == str(images[0])
    images = running_stacks(images, int(n), tempfile.mkdtemp(prefix="stacks_"), ctx)
    inputs = dict(inputs) | ({"ref_image": images[0]} if first else {})
    return images, inputs, inputs.get("ref_image") or images[0]
