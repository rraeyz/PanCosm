"""Registration beyond shifts (plans/calibration.md CAL-15; IRAF geomap / geotran, Siril's homography): the
transform from the reference frame's pixels to a frame's, chosen by its residuals, and the frame resampled onto the
reference grid with the flux kept.

    model = fit(ref_xy, frame_xy, "auto")      shift, similarity, affine, homography, poly2 or poly3 — the simplest
                                               whose residual is within 10 % of the best (and its RMS)
    out = resample(frame, model, shape, "bicubic")   nearest / bilinear / bicubic / lanczos3 (clamped), times the
                                               transform's Jacobian so that a star's total flux stays the same
"""

import numpy as np
from scipy import ndimage

KINDS = ("shift", "similarity", "affine", "homography", "poly2", "poly3")


def _design(xy, kind):
    x, y = xy[:, 0], xy[:, 1]
    one = np.ones_like(x)
    if kind == "affine":
        return np.column_stack([one, x, y])
    if kind == "poly2":
        return np.column_stack([one, x, y, x * x, x * y, y * y])
    if kind == "poly3":
        return np.column_stack([one, x, y, x * x, x * y, y * y, x**3, x * x * y, x * y * y, y**3])
    raise ValueError(kind)


class Model:
    def __init__(self, kind, params, centre, scale):
        self.kind, self.params, self.centre, self.scale = kind, params, centre, scale
        self.rms = None

    def __call__(self, xy):
        """Frame coordinates of reference pixels xy (n, 2)."""
        u = (np.asarray(xy, float) - self.centre) / self.scale
        p = self.params
        if self.kind == "shift":
            out = u + p
        elif self.kind == "similarity":
            a, b, tx, ty = p
            out = np.column_stack([a * u[:, 0] - b * u[:, 1] + tx, b * u[:, 0] + a * u[:, 1] + ty])
        elif self.kind == "homography":
            h = np.append(p, 1.0).reshape(3, 3)
            q = np.column_stack([u, np.ones(len(u))]) @ h.T
            out = q[:, :2] / q[:, 2:3]
        else:
            d = _design(u, self.kind)
            out = np.column_stack([d @ p[0], d @ p[1]])
        return out * self.scale + self.centre


def _fit_one(u, v, kind):
    if kind == "shift":
        return np.mean(v - u, axis=0)
    if kind == "similarity":
        n = len(u)
        a = np.zeros((2 * n, 4))
        a[0::2] = np.column_stack([u[:, 0], -u[:, 1], np.ones(n), np.zeros(n)])
        a[1::2] = np.column_stack([u[:, 1], u[:, 0], np.zeros(n), np.ones(n)])
        return np.linalg.lstsq(a, v.ravel(), rcond=None)[0]
    if kind == "homography":  # direct linear transform, h33 = 1
        rows, rhs = [], []
        for (x, y), (X, Y) in zip(u, v, strict=True):
            rows += [[x, y, 1, 0, 0, 0, -X * x, -X * y], [0, 0, 0, x, y, 1, -Y * x, -Y * y]]
            rhs += [X, Y]
        return np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)[0]
    d = _design(u, kind)
    return (np.linalg.lstsq(d, v[:, 0], rcond=None)[0], np.linalg.lstsq(d, v[:, 1], rcond=None)[0])


def fit(ref_xy, frame_xy, kind="auto"):
    """The transform (reference pixels → frame pixels) of the matched stars; "auto": the simplest kind whose
    residual RMS is within 10 % of the best (or below 0.02 px)."""
    ref, frm = np.asarray(ref_xy, float), np.asarray(frame_xy, float)
    centre, scale = ref.mean(axis=0), max(float(np.ptp(ref)), 1.0) / 2
    u, v = (ref - centre) / scale, (frm - centre) / scale
    need = {"shift": 1, "similarity": 2, "affine": 3, "homography": 4, "poly2": 6, "poly3": 10}
    kinds = KINDS if kind == "auto" else (kind,)
    models = []
    for k in kinds:
        if len(ref) < need[k] + 1:
            continue
        m = Model(k, _fit_one(u, v, k), centre, scale)
        m.rms = float(np.sqrt(np.mean(np.sum((m(ref) - frm) ** 2, axis=1))))
        models.append(m)
    if not models:
        raise ValueError("too few matched stars for the transform")
    best = min(m.rms for m in models)
    return next(m for m in models if m.rms <= max(1.1 * best, 0.02))


def _lanczos(image, coords, a=3):
    """Lanczos-a interpolation at coords (2, n) = (rows, cols), clamped to the window's range (no ringing)."""
    img = np.asarray(image, float)
    r, c = coords
    r0, c0 = np.floor(r).astype(int), np.floor(c).astype(int)
    out, lo, hi = np.zeros(len(r)), np.full(len(r), np.inf), np.full(len(r), -np.inf)
    wsum = np.zeros(len(r))
    for dr in range(-a + 1, a + 1):
        for dc in range(-a + 1, a + 1):
            rr, cc = r0 + dr, c0 + dc
            ok = (rr >= 0) & (rr < img.shape[0]) & (cc >= 0) & (cc < img.shape[1])
            val = np.where(ok, img[np.clip(rr, 0, img.shape[0] - 1), np.clip(cc, 0, img.shape[1] - 1)], 0.0)
            w = np.sinc(r - rr) * np.sinc((r - rr) / a) * np.sinc(c - cc) * np.sinc((c - cc) / a) * ok
            out += w * val
            wsum += w
            if abs(dr) <= 1 and abs(dc) <= 1:
                lo, hi = np.where(ok, np.minimum(lo, val), lo), np.where(ok, np.maximum(hi, val), hi)
    out = out / np.where(wsum == 0, 1, wsum)
    return np.clip(out, lo, hi)


def _jacobian(model, xy, eps=0.5):
    """|det| of the transform's derivative at xy: how much frame area one reference pixel covers."""
    dx = (model(xy + [eps, 0]) - model(xy - [eps, 0])) / (2 * eps)
    dy = (model(xy + [0, eps]) - model(xy - [0, eps])) / (2 * eps)
    return np.abs(dx[:, 0] * dy[:, 1] - dx[:, 1] * dy[:, 0])


def resample(frame, model, shape, kernel="bicubic", conserve_flux=True):
    """The frame on the reference grid (shape); pixels that fall outside the frame are NaN."""
    ny, nx = shape
    yy, xx = np.indices(shape)
    xy = np.column_stack([xx.ravel(), yy.ravel()]).astype(float)
    where = model(xy)
    coords = np.vstack([where[:, 1], where[:, 0]])
    if kernel == "lanczos3":
        vals = _lanczos(frame, coords)
    else:
        order = {"nearest": 0, "bilinear": 1, "bicubic": 3}[kernel]
        vals = ndimage.map_coordinates(np.asarray(frame, float), coords, order=order, mode="constant", cval=np.nan,
                                       prefilter=order > 1)  # fmt: skip
    if conserve_flux:
        vals = vals * _jacobian(model, xy)
    fh, fw = np.shape(frame)
    outside = (where[:, 0] < -0.5) | (where[:, 0] > fw - 0.5) | (where[:, 1] < -0.5) | (where[:, 1] > fh - 0.5)
    vals[outside] = np.nan
    return vals.reshape(ny, nx).astype(np.float32)
