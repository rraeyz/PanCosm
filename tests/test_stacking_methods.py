"""Stacking choices: combination, rejection, normalisation and weights, on frames with known values."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import stacking as st

RNG = np.random.default_rng(11)


def block_with_cosmic(n=15):
    b = RNG.normal(100.0, 10.0, (n, 20, 30)).astype(np.float32)
    b[3, 5, 7] = 1e4  # a cosmic-ray hit in one frame
    b[0, 0, :5] = np.nan  # a frame that does not cover a few pixels
    return b


@pytest.mark.parametrize(
    "rejection,low,high", [("sigma", 1, 1), ("winsorized", 1, 1), ("minmax", 1, 1), ("percentile", 0.5, 0.5)]
)
def test_every_rejection_removes_the_cosmic_ray(rejection, low, high):
    b = block_with_cosmic()
    keep = st.reject(b, rejection, 3.0, low, high)
    assert not keep[3, 5, 7] and not keep[0, 0, 0]
    out = st.combine(b, "mean", rejection, 3.0, low, high)
    assert out[5, 7] == pytest.approx(100, abs=10) and np.isfinite(out).all()


def test_rejection_keeps_good_data():
    b = RNG.normal(0.0, 1.0, (40, 50, 50))
    for rejection in ("sigma", "winsorized"):
        assert st.reject(b, rejection, 3.0).mean() > 0.99  # a Gaussian loses well under 1 % at 3 sigma
    assert st.reject(b, "minmax", low=2, high=3).sum(axis=0).max() == 35
    assert st.combine(b, "mean", "none").std() == pytest.approx(1 / np.sqrt(40), rel=0.1)


def test_combinations_and_weights():
    b = block_with_cosmic()
    assert st.combine(b, "median", "sigma")[10, 10] == pytest.approx(100, abs=8)
    assert st.combine(b, "sum", "sigma").mean() == pytest.approx(1500, rel=0.01)
    noisy = np.concatenate([RNG.normal(100, 2, (5, 30, 30)), RNG.normal(100, 40, (5, 30, 30))]).astype(np.float32)
    w = np.r_[np.full(5, 1 / 4), np.full(5, 1 / 1600)]
    plain = st.combine(noisy, "mean", "none").std()
    weighted = st.combine(noisy, "mean", "none", weights=w).std()
    assert weighted < 0.2 * plain  # inverse-variance weights let the good frames count


def write(tmp_path, levels, star=True):
    yy, xx = np.mgrid[:40, :50]
    paths = []
    for i, (sky, gain) in enumerate(levels):
        img = (
            sky
            + gain * (500 * np.exp(-((xx - 25) ** 2 + (yy - 20) ** 2) / 6.0) if star else 0)
            + RNG.normal(0, 1, (40, 50))
        )
        fits.PrimaryHDU(img.astype(np.float32)).writeto(tmp_path / f"s{i}.fits")
        paths.append(tmp_path / f"s{i}.fits")
    return paths


def test_normalisation_and_weighting_in_the_stack(tmp_path):
    paths = write(tmp_path, [(100, 1.0), (200, 2.0), (150, 1.5)])  # transparency and sky change together
    zero = [(0.0, 0.0)] * 3
    img, cnt, h = st.stack(paths, offsets=zero, normalize="multiplicative", method="median", rejection="none")
    assert np.median(img) == pytest.approx(100, abs=1) and img[20, 25] == pytest.approx(600, rel=0.02)
    assert h["STACKNRM"] == "multiplicative" and h["STACKMTH"].startswith("median") and (cnt == 3).all()
    add = st.stack(paths, offsets=zero, normalize="additive", method="mean", rejection="none", weighting="noise")[0]
    assert np.median(add) == pytest.approx(100, abs=1)
    default = st.stack(paths, offsets=zero)[0]  # the fast sigma-clipped mean is unchanged
    assert np.median(default) == pytest.approx(150, abs=2)


def test_calibrate_page_stack_options(qtbot):
    from astrowb.ui.calibrate_page import CalibratePage

    page = CalibratePage()
    qtbot.addWidget(page)
    assert page.stack_params() == {
        "method": "mean",
        "rejection": "sigma",
        "normalize": "none",
        "weighting": "none",
        "align": "translation",
        "sigma": 3.0,
        "low": 1.0,
        "high": 1.0,
    }
    page.stack_opts["rejection"].setCurrentIndex(page.stack_opts["rejection"].findData("percentile"))
    page.clip_low.setValue(20)
    page.clip_high.setValue(10)
    assert (page.stack_params()["low"], page.stack_params()["high"]) == (0.2, 0.1)
    page.stack_opts["rejection"].setCurrentIndex(page.stack_opts["rejection"].findData("minmax"))
    page.clip_low.setValue(2)
    assert page.stack_params()["low"] == 2 and isinstance(page.stack_params()["low"], int)


def test_calibrate_page_sends_the_calibration_options(qtbot, tmp_path):
    from astrowb.ui.calibrate_page import CalibratePage

    page = CalibratePage()
    qtbot.addWidget(page)
    page.output.setText(str(tmp_path))
    page.optimize_dark.setChecked(True)
    page.fix_defects.setChecked(True)
    page.frames = []
    with qtbot.waitSignal(page.run_requested) as sig:
        page._run()
    params = sig.args[-1]
    assert params["optimize_dark"] and params["fix_defects"]


def test_calibrate_page_spectra_option(qtbot, tmp_path):
    from astrowb.ui.calibrate_page import CalibratePage

    page = CalibratePage()
    qtbot.addWidget(page)
    page.output.setText(str(tmp_path))
    with qtbot.waitSignal(page.run_requested) as sig:
        page._run()
    assert sig.args[-1]["divide_flat"]
    page.spectra.setChecked(True)
    with qtbot.waitSignal(page.run_requested) as sig:
        page._run()
    assert not sig.args[-1]["divide_flat"]
