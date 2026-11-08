"""Cosmic-ray cleaning with astroscrappy's result, faster (user feedback UF-12).

astroscrappy (L.A.Cosmic; BSD-3, McCully et al.) repeats its whole-frame detection up to four times, each pass on
the frame cleaned by the pass before. Cleaning changes only the masked pixels, and every quantity of the detection
reaches at most 9 pixels (Laplacian 1, noise median 3, its large-structure median 3 more, the fine-structure medians
6, the two neighbour growths 2); so a later pass can find something new only within that reach of a pixel the last
cleaning changed. This module runs astroscrappy's steps (its own compiled filters, the same order of operations)
once over the frame and the later passes only in boxes around the changed pixels: the mask and the cleaned frame are
those of `astroscrappy.detect_cosmics` with its defaults (sepmed, fsmode "median", cleantype "meanmask"), bit for
bit (tests/test_cosmics.py), in about the time of its first pass.
"""

import numpy as np
from astroscrappy.utils import (
    dilate3,
    dilate5,
    laplaceconvolve,
    median,
    rebin,
    sepmedfilt5,
    sepmedfilt7,
    sepmedfilt9,
    subsample,
)
from scipy import ndimage

REACH = 9  # pixels from a changed pixel within which a later pass can differ
PAD = REACH + 6  # each box's margin, so that its filters' edges stay out of the pixels it decides


def _detect(clean, var, good, sigclip, sigcliplow, objlim):
    """One L.A.Cosmic detection (astroscrappy's loop body for sepmed and fsmode "median")."""
    clean, var = np.ascontiguousarray(clean), np.ascontiguousarray(var)
    conved = laplaceconvolve(subsample(clean))
    conved[conved < 0] = 0.0
    s = rebin(conved)
    m5 = sepmedfilt7(var)
    m5[m5 < 0.00001] = 0.00001
    noise = np.sqrt(m5)
    s /= 2.0 * noise
    sp = s - sepmedfilt7(s)
    good = np.ascontiguousarray(good)
    cosmics = np.logical_and(sp > sigclip, good)
    f = sepmedfilt5(clean)
    f = (f - sepmedfilt9(f)) / noise
    f[f < 0.01] = 0.01
    cosmics = np.logical_and(cosmics, (sp / f) > objlim)
    cosmics = np.logical_and(np.logical_and(dilate3(cosmics), good), sp > sigclip)
    return np.logical_and(np.logical_and(dilate3(cosmics), good), sp > sigcliplow)


def _clean(arr, crmask, mask, level):
    """astroscrappy's masked 5 × 5 mean on the masked pixels (the frame's outer two rows and columns stay)."""
    ny, nx = arr.shape
    j, i = np.nonzero(crmask[2 : ny - 2, 2 : nx - 2])
    j, i = j + 2, i + 2
    bad = crmask | mask.astype(bool)
    s = np.zeros(len(j), np.float32)
    n = np.zeros(len(j), np.int32)
    for dl in range(-2, 3):  # its order of summing, so the sums round the same way
        for dk in range(-2, 3):
            ok = ~bad[j + dl, i + dk]
            s = np.where(ok, s + arr[j + dl, i + dk], s)
            n += ok
    with np.errstate(divide="ignore", invalid="ignore"):
        value = np.where(n == 0, np.float32(level), (s.astype(np.float64) / n).astype(np.float32))
    arr[j, i] = value


def _boxes(changed, shape):
    """Boxes around the groups of changed pixels: (the slice to compute on, the slice whose answer is kept)."""
    near = ndimage.binary_dilation(changed, iterations=REACH)
    ny, nx = shape
    for sl in ndimage.find_objects(ndimage.label(near)[0]):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        a = (slice(max(0, y0 - PAD), min(ny, y1 + PAD)), slice(max(0, x0 - PAD), min(nx, x1 + PAD)))
        yield a, (slice(y0 - a[0].start, y1 - a[0].start), slice(x0 - a[1].start, x1 - a[1].start)), sl


def detect_cosmics(data, gain=1.0, readnoise=6.5, sigclip=4.5, sigfrac=0.3, objlim=5.0, satlevel=65536.0, niter=4):
    """(mask, cleaned frame) as astroscrappy.detect_cosmics(data, gain=…, readnoise=…) gives them."""
    f32 = np.float32
    sigclip, objlim = f32(sigclip), f32(objlim)
    sigcliplow = f32(f32(sigfrac) * sigclip)
    clean = np.ascontiguousarray(data, dtype=np.float32) * float(f32(gain))
    var = clean + float(f32(readnoise) * f32(readnoise))
    mask = np.zeros(clean.shape, np.uint8)
    sat = np.logical_and(clean >= float(f32(satlevel)), sepmedfilt7(clean) > float(f32(satlevel)) / 10.0)
    mask[:, :] = np.logical_or(dilate5(sat, 2), dilate3(mask))  # astroscrappy's update_mask
    good = np.logical_not(mask)
    level, var_level = median(clean[good], int(good.sum())), median(var[good], int(good.sum()))

    crmask, changed = np.zeros(clean.shape, bool), None
    found = _detect(clean, var, good, sigclip, sigcliplow, objlim)  # the first pass: the whole frame
    for k in range(niter):
        if k:  # later passes: only near what the last cleaning changed
            found = np.zeros(clean.shape, bool)
            for a, keep, at in _boxes(changed, clean.shape):
                found[at] |= _detect(clean[a], var[a], good[a], sigclip, sigcliplow, objlim)[keep]
        if not found.any():
            break
        crmask |= found
        before, var_before = clean.copy(), var.copy()
        _clean(clean, crmask, mask, level)
        _clean(var, crmask, mask, var_level)
        changed = (clean != before) | (var != var_before)
    return crmask, clean / float(f32(gain))
