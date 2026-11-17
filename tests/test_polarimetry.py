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


def _standards(rng, n=12, sig=0.0005, qi=0.003, ui=0.0, phi=12.0):
    p = np.where(np.arange(n) % 3 == 0, 0.0, rng.uniform(0.02, 0.06, n))  # a third are unpolarised
    th = rng.uniform(0, 180, n)
    qc, uc = p * np.cos(np.radians(2 * th)), p * np.sin(np.radians(2 * th))
    c, s = np.cos(np.radians(2 * phi)), np.sin(np.radians(2 * phi))
    qm = c * qc + s * uc + qi + rng.normal(0, sig, n)
    um = -s * qc + c * uc + ui + rng.normal(0, sig, n)
    return qm, um, p, th, sig


def test_fit_standards_recovers_instrument_within_1_sigma_and_corrects():
    rng = np.random.default_rng(7)
    pulls = []
    for _ in range(200):
        qm, um, p, th, sig = _standards(rng)
        f = polarimetry.fit_standards(qm, um, p, th, sigma=sig)
        pulls += [(f["q_inst"] - 0.003) / f["q_inst_err"], (f["u_inst"]) / f["u_inst_err"]]
        pulls.append((f["zero_point"] - 12.0) / f["zero_point_err"])
    assert np.std(pulls) == pytest.approx(1.0, abs=0.12) and abs(np.mean(pulls)) < 0.15
    qm, um, p, th, sig = _standards(rng, sig=0.0)
    f = polarimetry.fit_standards(qm, um, p, th)
    assert f["q_inst"] == pytest.approx(0.003, abs=1e-9) and f["zero_point"] == pytest.approx(12.0, abs=1e-6)
    qc, uc = polarimetry.correct(qm, um, f)
    assert np.allclose(qc, p * np.cos(np.radians(2 * th)), atol=1e-9)


def test_fit_standards_bad_input():
    with pytest.raises(ValueError):
        polarimetry.fit_standards([0.1], [0.0], [0.05], [10.0])
    with pytest.raises(ValueError):
        polarimetry.fit_standards([0.1, 0.0], [0.0, 0.0], [0.0, 0.0], [10.0, 20.0])
    with pytest.raises(ValueError):
        polarimetry.fit_standards([0.1, 0.0], [0.0], [0.05, 0.0], [10.0, 20.0])
    with pytest.raises(ValueError):
        polarimetry.debias_mas(0.01, 0.0)


def test_mas_unbiased_at_p_over_sigma_2_and_error_propagation():
    rng = np.random.default_rng(11)
    sigma, p_true, n = 0.005, 0.01, 200000
    q = p_true + rng.normal(0, sigma, n)  # theta = 0
    u = rng.normal(0, sigma, n)
    p = np.hypot(q, u)
    debias = polarimetry.debias_mas(p, sigma)
    assert np.mean(debias) == pytest.approx(p_true, rel=0.10)
    assert np.mean(p) > 1.1 * p_true  # the raw P is clearly biased
    assert np.all(debias <= p) and polarimetry.debias_mas(0.0, sigma) == 0.0
    assert polarimetry.debias_wk(0.004, sigma) == 0.0
    assert polarimetry.debias_mas(1.0, sigma) == pytest.approx(1.0, abs=1e-4)
    # propagated sigma_P and sigma_theta against Monte Carlo at high S/N
    q0, u0, s = 0.03, 0.02, 0.001
    qq, uu = q0 + rng.normal(0, s, 50000), u0 + rng.normal(0, s, 50000)
    r = polarimetry._result(q0, u0, s, s, 0.0)
    assert r["p_err"] == pytest.approx(np.std(np.hypot(qq, uu)), rel=0.03)
    assert r["theta_err"] == pytest.approx(np.std(0.5 * np.degrees(np.arctan2(uu, qq))), rel=0.03)


def test_time_series_lists():
    angles = np.tile([0.0, 22.5, 45.0, 67.5], 2)
    frames = []
    for q in (0.01, 0.02):
        fo, fe = beams(q, 0.0, angles)
        frames.append({"angles_deg": angles, "f_o": fo, "f_e": fe})
    s = polarimetry.time_series(frames)
    assert isinstance(s["p"], list) and len(s["q"]) == 2 and s["q"][1] > s["q"][0]
    assert polarimetry.time_series([]) == {}
