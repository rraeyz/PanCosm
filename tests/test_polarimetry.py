"""Polarimetry on simulated beams with known q, u, beam transmission differences and photon noise."""

import numpy as np
import pytest

from astrowb.photometry import polarimetry


def beams(q, u, angles, flux=2e6, gain_e=0.93, rng=None):
    th = np.radians(angles)
    mod = q * np.cos(4 * th) + u * np.sin(4 * th)
    fo = flux / 2 * (1 + mod)
    fe = gain_e * flux / 2 * (1 - mod)  # the e-beam transmits 7 % less
    if rng is not None:
        fo, fe = rng.poisson(fo).astype(float), rng.poisson(fe).astype(float)
    return fo, fe


def test_dual_beam_recovers_q_u_despite_beam_transmission():
    angles = np.tile([0.0, 22.5, 45.0, 67.5], 3)
    fo, fe = beams(0.012, -0.004, angles)
    r = polarimetry.dual_beam(angles, fo, fe)
    # the transmission difference cancels to first order with four angles (second order ~ 1e-5 here)
    assert r["q"] == pytest.approx(0.012, abs=2e-4) and r["u"] == pytest.approx(-0.004, abs=2e-4)
    assert r["theta"] == pytest.approx((0.5 * np.degrees(np.arctan2(-0.004, 0.012))) % 180, abs=0.5)


def test_errors_match_monte_carlo_and_bias_correction():
    rng = np.random.default_rng(4)
    angles = np.array([0.0, 22.5, 45.0, 67.5])
    qs, us, sq = [], [], []
    for _ in range(400):
        fo, fe = beams(0.002, 0.001, angles, flux=4e5, gain_e=1.0, rng=rng)
        r = polarimetry.dual_beam(angles, fo, fe, np.sqrt(fo), np.sqrt(fe))
        qs.append(r["q"])
        us.append(r["u"])
        sq.append(r["q_err"])
    assert np.std(qs) / np.median(sq) == pytest.approx(1.0, abs=0.12)
    assert np.mean(qs) == pytest.approx(0.002, abs=3 * np.std(qs) / 20)
    # an unpolarised star: P is biased upward by noise; the debiased value is not
    fo, fe = beams(0.0, 0.0, angles, flux=4e5, gain_e=1.0, rng=rng)
    r = polarimetry.dual_beam(angles, fo, fe, np.sqrt(fo), np.sqrt(fe))
    assert r["p_debiased"] <= r["p"]


def test_single_beam_and_bad_input():
    q, u = 0.03, 0.02
    i = {a: 1e5 / 2 * (1 + q * np.cos(np.radians(2 * a)) + u * np.sin(np.radians(2 * a))) for a in (0, 45, 90, 135)}
    r = polarimetry.single_beam(i[0], i[45], i[90], i[135], zero_point=2.0)
    assert r["q"] == pytest.approx(q, abs=1e-9) and r["u"] == pytest.approx(u, abs=1e-9)
    assert r["theta"] == pytest.approx(0.5 * np.degrees(np.arctan2(u, q)) + 2.0, abs=1e-6)
    with pytest.raises(ValueError):
        polarimetry.dual_beam([0, 0, 90], [1, 1, 1], [1, 1, 1])


def test_polarimetry_from_frames_through_the_page(qtbot, tmp_path):
    from astropy.io import fits

    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    rng = np.random.default_rng(6)
    y, x = np.mgrid[:60, :60]
    angles = np.tile([0.0, 22.5, 45.0, 67.5], 2)
    fo, fe = beams(0.02, 0.01, angles, flux=4e5)
    paths = []
    for i, (a, o, e) in enumerate(zip(angles, fo, fe, strict=True)):
        img = rng.normal(100, 2, (60, 60))
        for (sx, sy), f in (((30, 20), o), ((30, 40), e)):
            img += f / (2 * np.pi * 1.6**2) * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / (2 * 1.6**2))
        h = fits.Header({"DATE-OBS": f"2026-10-01T21:{i:02d}:00", "EXPTIME": 10.0, "HWPANGLE": a})
        p = tmp_path / f"pol{i}.fits"
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(p)
        paths.append(p)
    win = MainWindow(Settings(tmp_path / "s"))
    qtbot.addWidget(win)
    try:
        page = win.photometry_page
        page.set_images(paths)
        page._clicked(30, 20)
        page._clicked(30, 40)
        page.r_ap.setValue(6)
        page.pol_button.click()
        qtbot.waitUntil(lambda: "q = " in page.result.text(), timeout=60000)
        text = page.result.text()
        q = float(text.split("q = ")[1].split(" ")[0])
        u = float(text.split("u = ")[1].split(" ")[0])
        assert q == pytest.approx(0.02, abs=0.001) and u == pytest.approx(0.01, abs=0.001) and "HWPANGLE" in text
    finally:
        win.engine.shutdown()
