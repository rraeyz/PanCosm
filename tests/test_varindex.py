"""PHO-30: variables found among the stars of a field: 2000 constant stars and 10 variables of 2–5 × their noise."""

import time

import numpy as np

from astrowb.photometry import varindex


def field(n_stars=2000, n_frames=300, seed=11):
    rng = np.random.default_rng(seed)
    t = np.sort(rng.uniform(0, 0.4, n_frames))  # days
    mean = rng.uniform(10, 17, n_stars)
    sigma = 0.002 + 0.03 * 10 ** (0.4 * (mean - 17))  # brighter stars are less noisy
    zp = 0.3 * (t - 0.2) ** 2 + rng.normal(0, 0.01, n_frames)  # airmass and thin clouds, common to all
    mag = mean[None] + zp[:, None] + rng.normal(0, 1, (n_frames, n_stars)) * sigma[None]
    var = rng.choice(n_stars, 10, replace=False)
    for k, j in enumerate(var):
        amp = (2 + 3 * k / 9) * sigma[j]
        period = rng.uniform(0.05, 0.3)
        mag[:, j] += amp * np.sin(2 * np.pi * t / period + rng.uniform(0, 6.3))
    err = np.repeat(sigma[None], n_frames, 0)
    lost = rng.random(mag.shape) < 0.01  # a few points missing
    mag[lost] = np.nan
    return mag, err, set(var.tolist()), zp


def test_ten_variables_among_two_thousand_stars():
    mag, err, variables, zp = field()
    start = time.perf_counter()
    out = varindex.search(mag, err)
    took = time.perf_counter() - start
    found = set(np.flatnonzero(out["candidate"]).tolist())
    assert len(found & variables) >= 9, sorted(variables - found)
    assert len(found - variables) <= 5, sorted(found - variables)
    assert np.std(out["zp"] - (zp - zp.mean())) < 0.001  # the frames' zero points recovered
    assert not out["used"][list(variables)].any() or out["used"][list(variables)].sum() <= 2  # kept out of them
    assert took < 60


def test_indices_of_a_constant_star_and_a_slow_variable():
    rng = np.random.default_rng(0)
    n = 400
    e = np.full((n, 2), 0.01)
    r = rng.normal(0, 0.01, (n, 2))
    r[:, 1] += 0.03 * np.sin(np.linspace(0, 4 * np.pi, n))
    idx = varindex.indices(r, e)
    assert abs(idx["chi2"][0] - 1) < 0.2 and idx["chi2"][1] > 4
    assert idx["inv_eta"][0] < 0.7 < 2 < idx["inv_eta"][1]  # white noise: η ≈ 2, so 1/η ≈ 0.5
    assert abs(idx["stetson_j"][0]) < 0.1 < idx["stetson_j"][1]
    assert abs(idx["stetson_k"][0] - np.sqrt(2 / np.pi)) < 0.05  # Gaussian noise
