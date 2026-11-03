"""Atmospheric parameters by grid fitting, with the Sun as the reference: a synthetic 'real world' that differs from
the grid (some lines stronger, some missing), as real stars differ from PHOENIX."""

import io

import numpy as np
import pytest
from astropy.io import fits

from astrowb.spectroscopy import atmosphere as a

RNG = np.random.default_rng(11)
N_LINES = 160
LAM = np.sort(RNG.uniform(5010, 5990, N_LINES))
STRENGTH = RNG.uniform(0.05, 1.2, N_LINES)
EXC = RNG.uniform(-1.5, 1.5, N_LINES)  # temperature sensitivity
PRESS = RNG.uniform(-0.6, 0.6, N_LINES)  # gravity sensitivity
WRONG = RNG.random(N_LINES) < 0.3  # lines the grid makes too weak (as PHOENIX does for many solar lines)
MISSING = RNG.random(N_LINES) < 0.08  # lines the grid does not have


def spectrum(wave_vac, teff, logg, feh, real=False):
    """Planck continuum times absorption lines whose depths follow Teff, log g and [Fe/H] smoothly."""
    x = 1.4388e8 / (wave_vac * teff)
    cont = 1 / (wave_vac**5 * np.expm1(x))
    tau = np.zeros_like(wave_vac)
    for i in range(N_LINES):
        if MISSING[i] and not real:
            continue
        s = STRENGTH[i] * 10**feh * np.exp(EXC[i] * (5772 - teff) / 1000) * (1 + PRESS[i] * (logg - 4.44))
        s *= 2.0 if (WRONG[i] and real) else 1.0
        width = 0.06 * (1 + 0.15 * (logg - 4.44) * PRESS[i])
        tau += s * np.exp(-0.5 * ((wave_vac - LAM[i]) / width) ** 2)
    return cont / cont.mean() * np.exp(-tau)


@pytest.fixture(scope="module")
def grid():
    wave = np.exp(np.arange(np.log(4950), np.log(6050), 1 / 100_000))
    nodes = {
        (float(t), float(g), float(z)): spectrum(wave, t, g, z)
        for t in range(5400, 6301, 100)
        for g in (3.5, 4.0, 4.5, 5.0)
        for z in (-0.5, 0.0, 0.5)
    }
    return a.Grid(nodes, wave)


def observe(teff, logg, feh, vsini=4.0, rv=17.0, R=20000, snr=150, real=True, seed=1):
    hi = np.exp(np.arange(np.log(4950), np.log(6050), 1 / 100_000))
    s = spectrum(hi, teff, logg, feh, real=real)
    dv = a.C_KMS / 100_000
    s = np.convolve(np.pad(s, 200, mode="edge"), a.rotation_kernel(vsini, dv), mode="same")[200:-200]
    w_obs = np.arange(5050.0, 5950.0, 0.09)
    f = a.degrade(a.vac_to_air(hi) * (1 + rv / a.C_KMS), s, R, w_obs) * (1 + 0.2 * (w_obs - 5500) / 900)
    f /= np.median(f)
    return w_obs, f + np.random.default_rng(seed).normal(0, 1 / snr, f.size), np.full(f.size, 1 / snr)


def test_air_wavelengths_and_kernels():
    assert a.vac_to_air(6564.61) == pytest.approx(6562.80, abs=0.01)  # H alpha, NIST
    k = a.rotation_kernel(30.0, 1.5)
    assert k.sum() == pytest.approx(1.0) and len(k) == 2 * 21 + 1 and np.argmax(k) == 21
    w = np.linspace(5000, 5010, 2001)
    f = 1 + np.sin(w)
    out = np.linspace(5001, 5009, 300)
    edges = np.r_[out[0], 0.5 * (out[1:] + out[:-1]), out[-1]]
    assert np.allclose(a._rebin(w, f, out) * np.diff(edges), np.diff(edges - np.cos(edges)), rtol=0, atol=1e-5)


def test_model_spectrum_is_recovered(grid):
    """The grid's own physics (no model errors): every parameter within 3 sigma."""
    truth = {"teff": 5930.0, "logg": 4.15, "feh": -0.2, "vsini": 6.0, "rv": 17.0}
    w, f, e = observe(5930, 4.15, -0.2, vsini=6.0, real=False)
    o = a.fit(w, f, e, grid, 20000)
    for k, v in truth.items():
        # floor: the interpolation between grid points (measured: <= 12 K, 0.04 in log g, 0.01 dex)
        assert abs(o[k] - v) < 3 * o["errors"][k] + {"teff": 20, "logg": 0.05, "feh": 0.02}.get(k, 0.3), (k, o[k])
    assert 0.7 < o["chi2_red"] < 1.4


def test_the_sun_corrects_what_the_grid_gets_wrong(grid):
    truth = (6050.0, 4.2, -0.25)
    w, f, e = observe(*truth)
    raw = a.fit(w, f, e, grid, 20000)
    sun_hi = np.exp(np.arange(np.log(4950), np.log(6050), 1 / 100_000))
    sun = spectrum(sun_hi, a.SUN["teff"], a.SUN["logg"], a.SUN["feh"], real=True)
    sun = np.convolve(np.pad(sun, 200, mode="edge"), a.rotation_kernel(2.0, a.C_KMS / 1e5), mode="same")[200:-200]
    o = a.analyse(w, f, e, grid, 20000, a.solar_reference(w, a.vac_to_air(sun_hi), sun, grid, 20000))
    err = o["errors"]
    bias_raw = [abs(raw[k] - t) / s for k, t, s in zip(("teff", "logg", "feh"), truth, (30, 0.08, 0.05), strict=True)]
    bias_new = [abs(o[k] - t) / s for k, t, s in zip(("teff", "logg", "feh"), truth, (30, 0.08, 0.05), strict=True)]
    assert max(bias_raw) > 1.5  # the wrong lines pull the plain fit away
    assert max(bias_new) < max(bias_raw) and max(bias_new) < 1.5, (raw, o)  # relative to the Sun: close
    assert abs(o["teff"] - truth[0]) < 3 * err["teff"] + 40 and abs(o["feh"] - truth[2]) < 3 * err["feh"] + 0.05
    assert 0.3 < o["used_fraction"] < 1.0 and not o["far_from_sun"]
    assert set(o["sun_offsets"]) == {"teff", "logg", "feh"}


def test_grid_with_holes_and_downloads(tmp_path):
    full = {(t, g, z): np.ones(4) for t in (1.0, 2.0, 3.0) for g in (1.0, 2.0) for z in (0.0, 1.0)}
    del full[(3.0, 2.0, 1.0)]
    assert len(a.Grid(full, np.arange(4.0)).spectra) == 8  # the largest complete box

    wave = np.linspace(2900, 10100, 20000)

    def fetch(url):
        buf = io.BytesIO()
        data = wave if "WAVE_" in url else 1e15 * (1 + 0.1 * np.sin(wave / 50))
        fits.PrimaryHDU(data).writeto(buf)
        return buf.getvalue()

    def fetch_with_hole(url):
        if "lte12000" in url:  # a point the PHOENIX grid does not have
            import urllib.error

            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return fetch(url)

    nodes = [(5800.0, 4.5, 0.0), (12000.0, 0.0, 0.0), (5800.0, 4.5, -0.5)]
    paths = a.download_phoenix(nodes, tmp_path, fetch=fetch_with_hole)
    assert [p.name for p in paths] == ["phoenix_05800_4.50_+0.0.fits", "phoenix_05800_4.50_-0.5.fits"]
    assert a.download_phoenix(nodes, tmp_path, fetch=None) == paths  # the hole is remembered, nothing fetched
    g = a.Grid.load(paths, 5000, 6000)
    assert g.wave[0] >= 5000 and g.wave[-1] <= 6000 and len(g.spectra) == 2
    s = g.spectra[(5800.0, 4.5, 0.0)]
    assert np.allclose(s, 1e15 * (1 + 0.1 * np.sin(g.wave / 50)), rtol=1e-3)  # rebinned, flux kept
    assert a.phoenix_url(5800, 4.5, -0.5).endswith("Z-0.5/lte05800-4.50-0.5.PHOENIX-ACES-AGSS-COND-2011-HiRes.fits")
    rows = [f"{w / 10:.5f} {0.9:.4f} {1e8 / w:.5f}" for w in np.arange(3000, 10000, 0.5)]
    text = "\n".join(["  14000 0."] + rows)
    sw, sf = a.download_sun(tmp_path, fetch=lambda url: text.encode())
    assert sw[0] >= 3000 and np.allclose(sf, 0.9, atol=1e-3)


def test_spectrum_tools_tab_asks_and_shows(qtbot, tmp_path):
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.spectrum_tools import SpectrumToolsTab

    w = np.linspace(5000, 6000, 3000)
    path = tmp_path / "star.fits"
    spectrum_io.write(path, w, 1 + 0.01 * np.sin(w), np.full(w.size, 0.01))
    tab = SpectrumToolsTab()
    qtbot.addWidget(tab)
    tab._atmosphere()
    assert "Open a spectrum" in tab.status.text()
    assert tab._open(str(path))
    tab._atmosphere()
    assert "resolution" in tab.status.text()
    tab.resolution.setValue(20000)
    tab.history.append(tab.flux)  # the spectrum was changed on the tab: the fit gets what is shown
    with qtbot.waitSignal(tab.atmosphere_requested) as sig:
        tab._atmosphere()
    inputs, params = sig.args
    assert params == {"resolution": 20000} and "sun" not in inputs
    assert np.allclose(spectrum_io.read(inputs["spectrum"])[1], tab.flux)
    errs = {k: 1.0 for k in ("teff", "logg", "feh", "vsini", "rv")}
    shown = {"teff": 5900.0, "logg": 4.3, "feh": -0.1, "vsini": 4.0, "rv": 12.0, "errors": errs}
    plot = {"wave": [1, 2], "flux": [1, 1], "model": [1, 1]}
    tab.show_atmosphere(
        shown | {"used_fraction": 0.5, "chi2_red": 1.1, "far_from_sun": True, "at_edge": [], "plot": plot}
    )
    assert "Teff = 5900" in tab.status.text() and "far from the Sun" in tab.status.text()
