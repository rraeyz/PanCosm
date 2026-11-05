"""MK type against MK standard stars (a toy library in MKCLASS's file layout; the real one is downloaded)."""

import io
import tarfile

import numpy as np
import pytest

from astrowb.spectroscopy import mkstandards

GRID = np.arange(3800.0, 5600.0, 1.0)
BALMER = (4861.3, 4340.5, 4101.7, 3970.1, 3889.1)
METALS = (3933.7, 3968.5, 4226.7, 4307.9, 4383.5, 4957.6, 5167.3, 5183.6, 5269.5)


def _intrinsic(t, lum, wave):
    """A toy star at high resolution: Balmer lines strongest at A0 (t 16), broader in dwarfs (pressure), metal
    lines growing to the cool side; the flux slope is left to the instrument response."""
    balmer = 0.6 * np.exp(-0.5 * ((t - 16) / 7) ** 2)
    metal = 0.6 / (1 + np.exp(-(t - 26) / 3))
    f = np.ones_like(wave)
    for lam in BALMER:
        f -= balmer * np.exp(-0.5 * ((wave - lam) / (1.0 + 2.5 * lum / 5)) ** 2)
    for lam in METALS:
        f -= metal * np.exp(-0.5 * ((wave - lam) / 0.2) ** 2)
    return f


def _observed(t, lum, wave, fwhm):
    from scipy.ndimage import gaussian_filter1d

    fine = np.arange(wave[0] - 20, wave[-1] + 20, 0.05)
    f = gaussian_filter1d(_intrinsic(t, lum, fine), fwhm / 2.355 / 0.05)
    return np.interp(wave, fine, f)


def _library(folder, temps=(14.0, 16.0, 19.0, 23.0, 26.0, 30.0, 32.0, 34.0, 36.0), lums=(3.0, 5.0)):
    folder.mkdir(parents=True, exist_ok=True)
    for t in temps:
        for lum in lums:
            name = f"t{round(t * 10):03d}l{round(lum * 10):02d}p00.rbn"
            flux = _observed(t, lum, GRID, mkstandards.RESOLUTION) * (1 + 0.2 * (GRID - 4700) / 900)
            np.savetxt(folder / name, np.column_stack([GRID, flux]), fmt="%.6f")
    return folder


def test_type_names():
    assert mkstandards.type_name(31.0, 5.0) == "G2 V" and mkstandards.type_name(16.1, 3.0) == "A0 III"
    assert mkstandards.type_name(35.4, 4.5) == "K1 IV-V" and mkstandards.type_name(40.7, 1.0) == "M0 Ib"


@pytest.mark.parametrize(("t", "lum"), [(31.0, 5.0), (21.0, 3.0), (35.0, 3.0)])
def test_types_between_the_standards(tmp_path, t, lum):
    """A star between two standards, observed at a higher resolution, with noise and an instrument response."""
    lib = _library(tmp_path / "lib")
    wave = np.arange(3850.0, 5550.0, 0.2)
    rng = np.random.default_rng(2)
    flux = _observed(t, lum, wave, 1.0) * (1.4 - 0.3 * (wave - 3850) / 1700) * 900
    flux += rng.normal(0, 900 / 60, wave.size)
    ranked, best = mkstandards.classify(wave, flux, lib, fwhm=1.0)
    assert abs(ranked[0]["t"] - t) <= 1.0 and ranked[0]["lum"] == lum
    assert ranked[0]["score"] <= ranked[1]["score"] and len({r["type"] for r in ranked}) == len(ranked)
    assert len(best["model"]) == len(best["wave"]) == GRID.size


def test_outside_the_range_is_refused(tmp_path):
    lib = _library(tmp_path / "lib")
    wave = np.arange(6000.0, 7000.0, 1.0)
    with pytest.raises(ValueError, match="3800-5600"):
        mkstandards.classify(wave, np.ones_like(wave), lib)


def test_download_keeps_only_the_standards(tmp_path):
    lib = _library(tmp_path / "src", temps=(16.0, 19.0), lums=(5.0,))
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in lib.glob("*.rbn"):
            tar.add(p, arcname=f"mkclass/libnor36/{p.name}")
        tar.add(p, arcname="mkclass/libr18/t160l50p00.rbn")  # another library: not kept
        tar.add(p, arcname="../evil.rbn")  # never written outside the folder
    calls = []
    out = mkstandards.download(tmp_path / "mk", fetch=lambda url: calls.append(url) or buf.getvalue())
    assert sorted(x.name for x in out.iterdir()) == ["t160l50p00.rbn", "t190l50p00.rbn"]
    assert not (tmp_path / "evil.rbn").exists() and calls == [mkstandards.MK_URL]
    mkstandards.download(tmp_path / "mk", fetch=lambda url: 1 / 0)  # once there, never fetched again


def test_velocity_tab_shows_the_mk_type_as_a_suggestion(qtbot):
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    mk = [{"type": "K1 III", "score": 0.0624, "t": 35.0, "lum": 3.0}, {"type": "K2 III", "score": 0.063}]
    tab.show_classes([{"type": "K2III", "rms": 0.02, "template": "/lib/k2iii.fits"}], mk)
    text = tab.status.text()
    assert "K1 III (0.0624), K2 III" in text and "suggestion" in text and tab.template.text() == "/lib/k2iii.fits"
    tab.show_classes([{"type": "K2III", "rms": 0.02, "template": "x"}], None, "no internet")
    assert "No MK type: no internet" in tab.status.text()


def test_quality_words_and_peculiar_a_star_hint(qtbot):
    from astrowb.spectroscopy.mkstandards import quality
    from astrowb.ui.spectro_page import VelocityTab

    assert [quality(s) for s in (0.012, 0.025, 0.05, 0.09, 0.2)] == ["excellent", "vgood", "good", "fair", "poor"]
    tab = VelocityTab()
    qtbot.addWidget(tab)
    w = np.linspace(3800, 5600, 300)
    model = {"wave": w.tolist(), "star": np.ones(300).tolist(), "model": np.ones(300).tolist()}
    model["peculiarity"] = {"k": "A1", "h": "A1", "metal": "F0", "hint": "Am"}
    tab.show_classes([], [{"type": "A2 III", "score": 0.025, "quality": "vgood"}], None, model)
    text = tab.status.text()
    assert "very good" in text and "K line A1, the hydrogen lines A1, the metal lines F0" in text and "(Am)" in text


def test_peculiarity_from_separate_k_hydrogen_and_metal_types():
    grid = np.arange(3800.0, 5600.0, 1.0)

    def lines(centres, depth):
        f = np.zeros_like(grid)
        for c in centres:
            f += depth * np.exp(-0.5 * ((grid - c) / 2.0) ** 2)
        return f

    def star(tk, th, tm):  # K line deepens to later types, hydrogen peaks at A2 (18), metals deepen
        return (
            1.0
            - lines([3933.7], 0.05 * (tk - 14))
            - lines([4101.7, 4340.5, 4861.3], 0.6 - (0.03 if th < 18 else 0.05) * abs(th - 18))
            - lines([4226.7, 4271.8, 4383.5, 4404.8, 4415.1, 4549.6, 5167.3, 5172.7, 5183.6, 5269.5], 0.03 * (tm - 14))
        )

    lib = {(float(t), 5.0): star(t, t, t) for t in range(14, 30)}
    assert mkstandards.peculiarity(star(20, 20, 20), grid, lib, 20.0, 5.0)["hint"] is None
    am = mkstandards.peculiarity(star(17, 18, 23), grid, lib, 19.0, 5.0)
    assert am["hint"] == "Am" and am["metal"] in ("F0", "F2") and am["k"] in ("A0", "A1", "A2")
    weak = mkstandards.peculiarity(star(16, 20, 16), grid, lib, 19.0, 5.0)
    assert weak["hint"] == "metal-weak"
    assert mkstandards.peculiarity(star(33, 33, 33), grid, lib, 33.0, 5.0) is None  # G8: not an A-F star


def test_strong_sr_line_points_to_an_ap_star(qtbot):
    grid = np.arange(3800.0, 5600.0, 1.0)
    model = np.ones_like(grid)
    s = 3.6 / 2.355
    star = 1 - 0.5 / (s * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((grid - 4077.7) / s) ** 2)  # EW 0.5 A
    found = mkstandards.strong_lines(star, model, grid, 20.0, 5.0)
    assert [x["hint"] for x in found] == ["Ap (Sr)"] and found[0]["excess"] > 0.4
    assert mkstandards.strong_lines(star, model, grid, 34.0, 3.0) == []  # Sr II is not checked for a K giant
    assert mkstandards.strong_lines(model, model, grid, 20.0, 5.0) == []
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    m = {"wave": grid.tolist(), "star": star.tolist(), "model": model.tolist(), "strong_lines": found}
    tab.show_classes([], [{"type": "A5 V", "score": 0.03, "quality": "vgood"}], None, m)
    assert "Sr II 4077 (+0.4" in tab.status.text() and "Ap (Sr)" in tab.status.text()
