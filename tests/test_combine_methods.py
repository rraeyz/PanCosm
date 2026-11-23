"""CAL-5: each rejection against a slow, per-pixel statement of its definition; a cosmic ray in one of five darks
removed; nkeep honoured."""

import numpy as np
import pytest
from scipy import stats

from astrowb.calibration import combine

GAIN, RN = 1.5, 6.0


def stack(seed=0, n=9, shape=(12, 14), level=1000.0, cosmic=True):
    rng = np.random.default_rng(seed)
    s = level + rng.normal(0, np.sqrt(level / GAIN + (RN / GAIN) ** 2), (n, *shape))
    if cosmic:
        s[2, 3, 4] += 5000  # a cosmic ray
        s[0, 7, 9] -= 300  # a cold glitch
    return s


def slow(method, s, **kw):
    """The definitions, one pixel at a time."""
    n, ny, nx = s.shape
    keep = np.zeros(s.shape, bool)
    for y in range(ny):
        for x in range(nx):
            v = s[:, y, x]
            if method == "minmax":
                k = np.zeros(n, bool)
                k[np.argsort(v)[kw["nlow"] : n - kw["nhigh"]]] = True
            elif method in ("ccdclip", "crreject"):
                k = np.ones(n, bool)
                for _ in range(10):
                    c = np.median(v[k])
                    sig = np.sqrt((RN / GAIN) ** 2 + max(c, 0) / GAIN)
                    lo = -np.inf if method == "crreject" else c - 3 * sig
                    new = (v >= lo) & (v <= c + 3 * sig)
                    if (new == k).all():
                        break
                    k = new
            elif method == "pclip":
                srt = np.sort(v)
                med = np.median(v)
                j = int(np.clip(round((n - 1) / 2 + kw["pclip"] * (n - 1) / 2), 0, n - 1))
                sig = abs(srt[j] - med)
                k = (v >= med - 3 * sig) & (v <= med + 3 * sig)
            elif method == "gesd":
                idx, vals, rmax, last = list(range(n)), v.copy(), max(1, n // 3), 0
                out = []
                for r in range(1, rmax + 1):
                    mean, sd = vals.mean(), vals.std(ddof=1)
                    i = int(np.argmax(np.abs(vals - mean)))
                    big = abs(vals[i] - mean) / sd
                    m = n - r + 1
                    t = stats.t.ppf(1 - 0.05 / (2 * m), m - 2)
                    if big > (m - 1) * t / np.sqrt((m - 2 + t * t) * m):
                        last = r
                    out.append(idx.pop(i))
                    vals = np.delete(vals, i)
                k = np.ones(n, bool)
                k[out[:last]] = False
            keep[:, y, x] = k
    return keep


@pytest.mark.parametrize(("method", "kw"), [("minmax", {"nlow": 1, "nhigh": 2}),
                                            ("ccdclip", {"gain": GAIN, "read_noise": RN}),
                                            ("crreject", {"gain": GAIN, "read_noise": RN}),
                                            ("pclip", {"pclip": -0.5}), ("gesd", {})])  # fmt: skip
def test_each_method_equals_its_definition(method, kw):
    s = stack()
    fast = combine.METHODS[method](s, **kw)
    ref = slow(method, s, **{k: v for k, v in kw.items() if k in ("nlow", "nhigh", "pclip")})
    assert np.array_equal(fast, ref)


@pytest.mark.parametrize("method", ["ccdclip", "crreject", "avsigclip", "gesd"])
def test_a_cosmic_ray_in_one_of_five_darks_is_removed(method):
    s = stack(n=5, cosmic=True)
    kw = {"gain": GAIN, "read_noise": RN} if method in ("ccdclip", "crreject") else {}
    image, kept = combine.combine(s, method, **kw)
    assert kept[3, 4] == 4 and abs(image[3, 4] - 1000) < 60  # the 5000 ADU hit gone
    clean = np.delete(np.arange(s.shape[1] * s.shape[2]), 3 * s.shape[2] + 4)
    assert np.median(kept.ravel()[clean]) == 5  # the others mostly untouched


def test_nkeep_and_the_unknown():
    s = stack(n=4)
    _, kept = combine.combine(s, "minmax", nkeep=3, nlow=1, nhigh=2)
    assert kept.min() == 3  # minmax would leave one; nkeep gives two back
    with pytest.raises(ValueError):
        combine.combine(s, "magic")


def test_linear_fit_on_a_larger_stack_with_a_gradient():
    """Siril advises it for 15–50 frames: the sky rising from frame to frame is no reason to reject."""
    s = stack(n=25, cosmic=True) + np.arange(25)[:, None, None] * 4.0  # the sky brightens through the night
    keep = combine.linear_fit(s)
    assert not keep[2, 3, 4] and keep[:, 5, 5].sum() >= 23  # the cosmic ray out, the drifting sky kept


def test_grow_rejects_the_neighbours_within_the_radius_in_the_same_frame():
    s = stack()
    base, _ = combine_keep(s, 0)
    for grow in (1, 1.5):
        _, kept = combine_keep(s, grow)
        rej = np.zeros(s.shape, bool)
        for k in range(len(s)):
            for y in range(s.shape[1]):
                for x in range(s.shape[2]):
                    near = [
                        (y + dy, x + dx) for dy in range(-2, 3) for dx in range(-2, 3) if dy * dy + dx * dx <= grow**2
                    ]
                    rej[k, y, x] = any(
                        0 <= a < s.shape[1] and 0 <= b < s.shape[2] and not base[k, a, b] for a, b in near
                    )
        assert (kept == (~rej).sum(axis=0)).all()
    assert kept.sum() < base.sum()
    # nkeep still honoured after growing
    assert (combine_keep(s, 3, nkeep=4)[1] >= 4).all()


def combine_keep(s, grow, nkeep=1):
    base = combine.ccdclip(s, gain=GAIN, read_noise=RN)
    image, kept = combine.combine(s, "ccdclip", nkeep=nkeep, grow=grow, gain=GAIN, read_noise=RN)
    return (base, kept) if nkeep == 1 else (image, kept)


def test_scale_zero_and_exposure():
    rng = np.random.default_rng(1)
    flat = rng.normal(100, 1, (3, 8, 8))
    s = flat * np.array([1.0, 2.0, 0.5])[:, None, None]
    out, _ = combine.combine(s, scale="median")
    assert abs(out.mean() - np.median(s[0])) < 0.5
    out, _ = combine.combine(s, scale="exposure", exposure=[10, 20, 5])
    assert abs(out.mean() - s[0].mean()) < 0.5
    off = flat + np.array([0.0, 50.0, -20.0])[:, None, None]
    out, _ = combine.combine(off, zero="mean", region=(0, 4, 0, 4))
    assert abs(out.mean() - flat[:, :4, :4].mean(axis=(1, 2)).mean() - (flat[0].mean() - flat[:, :4, :4].mean())) < 3
    z = combine.scale_and_zero(off, zero="mean")
    d = z.mean(axis=(1, 2))
    assert np.allclose(d, d[0])
    with pytest.raises(combine.AppError):
        combine.combine(s, scale="bogus")


def test_noise_weights_equal_the_direct_formula():
    rng = np.random.default_rng(2)
    s = 50 + rng.normal(0, 1, (3, 6, 6)) * np.array([1.0, 3.0, 0.5])[:, None, None]
    out, _ = combine.combine(s, weights="noise")
    w = np.array([1 / (1.4826 * np.median(np.abs(f - np.median(f)))) ** 2 for f in s])
    assert np.allclose(out, (w[:, None, None] * s).sum(0) / w.sum(), rtol=1e-5)
    out, _ = combine.combine(s, weights=[1, 2, 3])
    assert np.allclose(out, (np.array([1, 2, 3])[:, None, None] * s).sum(0) / 6, rtol=1e-5)
    plain, _ = combine.combine(s)
    assert np.allclose(plain, s.mean(0), rtol=1e-5)
