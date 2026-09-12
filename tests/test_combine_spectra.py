"""Several exposures of one star combined into one spectrum (plans/spectroscopy.md step 0, IRAF scombine)."""

import numpy as np
import pytest

from astrowb.spectroscopy.combine import combine, noise


def _exposures(n=3, seed=1, sigma=0.02):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        wave = np.linspace(5000 + 0.3 * i, 5100 + 0.3 * i, 2000)  # grids a little apart, as from different arcs
        line = 1 - 0.5 * np.exp(-0.5 * ((wave - 5050) / 0.8) ** 2)
        level = 1.0 + 0.2 * i  # exposures of different length / transparency
        out.append((wave, level * (line + rng.normal(0, sigma, wave.size)), None))
    return out


def test_three_exposures_gain_root_three_in_signal_to_noise_and_lose_a_cosmic_ray():
    spectra = _exposures()
    spectra[1][1][700] += 5.0  # a cosmic ray in the middle exposure
    r = combine(spectra)
    inside = (r["wave"] > 5005) & (r["wave"] < 5095)
    one = noise(spectra[0][1]) / np.median(spectra[0][1])
    both = noise(r["flux"][inside]) / np.median(r["flux"][inside])
    assert one / both == pytest.approx(np.sqrt(3), rel=0.1)
    hit = np.argmin(np.abs(r["wave"] - spectra[1][0][700]))
    assert abs(r["flux"][hit] / np.median(r["flux"][inside]) - 1) < 0.1 and r["rejected"] >= 1
    assert r["n"][inside].min() >= 2 and r["n"][0] == 1  # the blue end is in the first exposure only
    near = np.abs(r["wave"] - 5050) < 2
    depth = 1 - r["flux"][near] / np.median(r["flux"][inside])
    assert abs(np.sum(r["wave"][near] * depth) / np.sum(depth) - 5050) < 0.05  # the line stays where it was
    assert np.isfinite(r["error"][inside]).all()


def test_median_sum_minmax_and_too_few():
    spectra = _exposures(4)
    spectra[0] = (spectra[0][0], spectra[0][1], np.full(spectra[0][0].size, np.nan))  # an error column of NaN
    med = combine(spectra, method="median", rejection="none")
    total = combine(spectra, method="sum", rejection="minmax", scale="none")
    inside = (med["wave"] > 5005) & (med["wave"] < 5095)
    assert np.median(total["flux"][inside]) == pytest.approx(4 * 1.3, rel=0.05)  # sum of levels 1.0 … 1.6
    assert np.isfinite(med["flux"][inside]).all()
    with pytest.raises(ValueError):
        combine(spectra[:1])


def test_the_step_writes_the_combined_spectrum(tmp_path):
    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io

    class Ctx:
        def progress(self, *a):
            pass

    from astropy.io import fits

    from astrowb.ui.messages import translate

    paths = []
    for i, (w, f, _) in enumerate(_exposures()):
        header = fits.Header({"MJD-OBS": 60000.1 + 0.05 * i})  # one night
        paths.append(spectrum_io.write(tmp_path / f"e{i}.fits", w, f, np.full(w.size, 0.02), header))
    out = execute("spectroscopy.combine", {"spectra": paths, "output": str(tmp_path / "sum.fits")}, {}, Ctx())
    w, f, e, header = spectrum_io.read(out["combined"]["path"])
    assert header["NCOMBINE"] == 3 and len(w) == len(out["combined"]["wave"]) and np.nanmedian(e) < 0.02
    assert out["combined"]["warnings"] == []
    w, f, _ = _exposures(1)[0]
    paths.append(
        spectrum_io.write(tmp_path / "later.fits", w, f, np.full(w.size, 0.02), fits.Header({"MJD-OBS": 60048.2}))
    )
    warned = execute("spectroscopy.combine", {"spectra": paths}, {}, Ctx())["combined"]["warnings"]
    assert len(warned) == 1 and "48.1 days" in warned[0] and translate(warned[0]) == warned[0]


def test_combine_exposures_from_spectrum_tools(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.main_window import MainWindow

    paths = [
        spectrum_io.write(tmp_path / f"e{i}.fits", w, f, np.full(w.size, 0.02))
        for i, (w, f, _) in enumerate(_exposures())
    ]
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    try:
        tools = win.spectro_page.tools_tab
        assert tools._combine(paths[:1]) is False and "at least two" in tools.source.text()
        assert tools._combine(paths)
        qtbot.waitUntil(lambda: tools.path.endswith("e0_combined3.fits"), timeout=60000)
        assert "3 exposures combined" in tools.source.text() and tools.wave.size > 2000
    finally:
        win.engine.shutdown()
