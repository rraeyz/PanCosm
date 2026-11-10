"""Stacking choices of Siril and MaxIm DL (plans/calibration.md CAL-16): which frames go in, how much each counts,
and adjacent fields joined into one picture.

    keep = select(stats, best=0.8, max_fwhm=None)      the frames worth stacking from their quality table
    w = weights(stats, by="noise")                      noise (1/σ²), fwhm (1/FWHM²) or stars (star count)
    image = join(tiles, offsets, shape)                 tiles placed at integer offsets, each one's background
                                                        brought to its neighbours' in their overlaps, then averaged
"""

import numpy as np


def select(stats, best=1.0, max_fwhm=None, max_background=None, min_stars=None):
    """bool per frame. stats: [{"fwhm", "background", "stars", "roundness"?}]; best: the share kept, ranked by FWHM
    (then background); thresholds applied first."""
    n = len(stats)
    keep = np.ones(n, bool)
    fwhm = np.array([s.get("fwhm", np.nan) for s in stats], float)
    bg = np.array([s.get("background", np.nan) for s in stats], float)
    stars = np.array([s.get("stars", np.nan) for s in stats], float)
    if max_fwhm is not None:
        keep &= ~(fwhm > max_fwhm)
    if max_background is not None:
        keep &= ~(bg > max_background)
    if min_stars is not None:
        keep &= ~(stars < min_stars)
    if best < 1.0:
        order = np.lexsort((np.nan_to_num(bg, nan=np.inf), np.nan_to_num(fwhm, nan=np.inf)))
        allowed = [i for i in order if keep[i]][: max(1, int(round(best * keep.sum())))]
        keep = np.isin(np.arange(n), allowed)
    return keep


def weights(stats, by="noise"):
    """Relative weights (mean 1): 1/noise², 1/FWHM² or the star count."""
    if by == "noise":
        w = 1 / np.square([s["noise"] for s in stats])
    elif by == "fwhm":
        w = 1 / np.square([s["fwhm"] for s in stats])
    elif by == "stars":
        w = np.asarray([s["stars"] for s in stats], float)
    else:
        raise ValueError(f"unknown weighting {by}")
    return w / np.mean(w)


def join(tiles, offsets, shape):
    """One image of shape from tiles at integer (x, y) offsets: each tile's constant background difference to the
    others solved from the overlaps (least squares, the first tile fixed), then the overlapping pixels averaged."""
    tiles = [np.asarray(t, float) for t in tiles]
    n = len(tiles)
    boxes = [
        (int(oy), int(oy) + t.shape[0], int(ox), int(ox) + t.shape[1])
        for t, (ox, oy) in zip(tiles, offsets, strict=True)
    ]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            y0, y1 = max(boxes[i][0], boxes[j][0]), min(boxes[i][1], boxes[j][1])
            x0, x1 = max(boxes[i][2], boxes[j][2]), min(boxes[i][3], boxes[j][3])
            if y1 > y0 and x1 > x0:
                a = tiles[i][y0 - boxes[i][0] : y1 - boxes[i][0], x0 - boxes[i][2] : x1 - boxes[i][2]]
                b = tiles[j][y0 - boxes[j][0] : y1 - boxes[j][0], x0 - boxes[j][2] : x1 - boxes[j][2]]
                pairs.append((i, j, float(np.nanmedian(a - b))))
    offset = np.zeros(n)
    if pairs:  # offset_i − offset_j = −(a − b): every tile brought to the same background, tile 0 fixed
        rows = []
        for i, j, d in pairs:
            r = np.zeros(n)
            r[i], r[j] = 1, -1
            rows.append((r, -d))
        rows.append((np.eye(n)[0], 0.0))
        a = np.array([r for r, _ in rows])
        b = np.array([v for _, v in rows])
        offset = np.linalg.lstsq(a, b, rcond=None)[0]
    total, count = np.zeros(shape), np.zeros(shape)
    for t, (y0, y1, x0, x1), o in zip(tiles, boxes, offset, strict=True):
        ok = np.isfinite(t)
        total[y0:y1, x0:x1] += np.where(ok, t + o, 0.0)
        count[y0:y1, x0:x1] += ok
    with np.errstate(invalid="ignore"):
        return np.where(count > 0, total / np.maximum(count, 1), np.nan).astype(np.float32)
