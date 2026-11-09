"""PHO-31: trends shared with the field's stars removed; a transit keeps its depth."""

import numpy as np
import pytest

from astrowb.photometry import systematics as sy


def field(n_stars=80, n_frames=300, seed=3):
    """Magnitudes with an airmass-and-colour term, a second shared drift, and white noise of known size."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 0.3, n_frames)
    airmass = 1.1 + 12 * (t - 0.12) ** 2
    drift = np.sin(2 * np.pi * t / 0.13)
    colour = rng.uniform(0.2, 1.8, n_stars)
    sigma = rng.uniform(0.002, 0.008, n_stars)
    base = rng.uniform(10, 15, n_stars)
    mag = (base[:, None] + (0.15 + 0.05 * colour)[:, None] * airmass[None]
           + rng.normal(0, 0.004, n_stars)[:, None] * drift[None]
           + rng.normal(0, 1, (n_stars, n_frames)) * sigma[:, None])  # fmt: skip
    return t, mag, np.repeat(sigma[:, None], n_frames, 1), sigma


def test_sysrem_brings_constant_stars_to_their_white_noise():
    t, mag, err, sigma = field()
    raw = np.std(mag - mag.mean(1, keepdims=True), axis=1)
    assert np.median(raw / sigma) > 3  # the trends dominate before
    out, terms = sy.sysrem(mag, err, n_terms=2)
    after = np.std(out - out.mean(1, keepdims=True), axis=1)
    assert len(terms) == 2 and np.median(after / sigma) < 1.1  # within 10 % of the white noise


def test_a_transit_keeps_its_depth_with_its_model_and_the_blind_loss_is_said():
    t, mag, err, sigma = field(seed=5)
    i = int(np.argmin(sigma))  # the quietest star: the depth is read to a tenth of a millimagnitude
    mag, err, sigma = np.r_[mag[i : i + 1], np.delete(mag, i, 0)], err[i:], np.r_[sigma[i], np.delete(sigma, i)]
    dip = sy.box(t, 0.15, 0.04, 0.01)
    inside = dip > 0
    depth = lambda y: np.mean(y[inside]) - np.mean(y[~inside])  # noqa: E731
    known, k = sy.correct(mag[0] + dip, mag[1:], err[0], fixed=dip)  # the fitted transit model given
    assert k >= 1 and depth(known) == pytest.approx(0.01, rel=0.05)
    assert np.std((known - dip)[~inside] - np.mean((known - dip)[~inside])) < 1.15 * sigma[0]
    blind, _ = sy.correct(mag[0] + dip, mag[1:], err[0])  # blind, a dip that overlaps the airmass trend loses some
    alone, _ = sy.correct(mag[0], mag[1:], err[0])
    kept = sy.suppression(t, mag[0], mag[1:], err[0], depth=0.01, duration=0.04, t0=0.15)
    assert kept < 0.95 and kept == pytest.approx(depth(blind - alone) / 0.01, abs=1e-9)  # and the window says it


def test_tfa_with_the_known_signal_keeps_all_of_it():
    t, mag, err, sigma = field(seed=7)
    i = int(np.argmin(sigma))
    mag, err, sigma = np.r_[mag[i : i + 1], np.delete(mag, i, 0)], err[i:], np.r_[sigma[i], np.delete(sigma, i)]
    dip = sy.box(t, 0.2, 0.05, 0.02)
    target = mag[0] + dip
    blind = sy.tfa(target, mag[1:30], err[0])
    known = sy.tfa(target, mag[1:30], err[0], fixed=dip)
    inside = dip > 0
    depth = lambda y: np.mean(y[inside]) - np.mean(y[~inside])  # noqa: E731
    assert depth(known) == pytest.approx(0.02, rel=0.05)
    assert depth(blind) < depth(known)  # without the signal the templates eat some of it
    assert np.std((known - dip)[~inside] - np.mean((known - dip)[~inside])) < 1.2 * sigma[0]


def test_the_bic_takes_no_term_for_a_star_without_trends():
    rng = np.random.default_rng(1)
    t, mag, err, sigma = field(seed=9)
    basis = sy.pca_basis(mag, 6)
    flat = rng.normal(0, 0.003, mag.shape[1])
    assert sy.bic_terms(flat, basis, np.full_like(flat, 0.003)) == 0
    assert sy.bic_terms(mag[0], basis, err[0]) >= 1
