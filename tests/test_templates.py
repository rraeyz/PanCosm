"""Spectral type from a template library: simulated stars whose line pattern changes with type."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine.steps import execute
from astrowb.spectroscopy import templates

WAVE = np.arange(3800.0, 7400.0, 2.5)
TYPES = {"A0V": (0.6, 0.05), "F5V": (0.35, 0.25), "G2V": (0.15, 0.45), "K5V": (0.05, 0.7)}  # Balmer, metals
METALS = np.random.default_rng(1).uniform(3900, 7300, 60)


def spectrum(balmer, metal, wave=WAVE, width=4.0):
    f = np.ones_like(wave)
    for lam in (6563, 4861, 4341, 4102, 3970):
        f -= balmer * np.exp(-0.5 * ((wave - lam) / (3 * width)) ** 2)
    for lam in METALS:
        f -= metal * 0.5 * np.exp(-0.5 * ((wave - lam) / width) ** 2)
    return f * (1 + 2e-4 * (wave - 5000))  # a continuum slope


def pickles_like(path, sptype, balmer, metal, width=4.0):
    cols = [
        fits.Column(name="WAVELENGTH", format="E", array=WAVE),
        fits.Column(name="FLUX", format="E", array=spectrum(balmer, metal, width=width)),
    ]
    head = fits.Header({"COMMENT1": f"spectral type: {sptype}"})
    fits.HDUList([fits.PrimaryHDU(header=head), fits.BinTableHDU.from_columns(cols)]).writeto(path)


@pytest.fixture
def library(tmp_path):
    folder = tmp_path / "lib"
    folder.mkdir()
    for i, (t, (b, m)) in enumerate(TYPES.items()):
        pickles_like(folder / f"pickles_uk_{i + 1}.fits", t, b, m)
    return folder


def test_read_and_classify(library, tmp_path):
    w, f, t = templates.read_template(library / "pickles_uk_3.fits")
    assert t == "G2V" and len(w) == len(f) == len(WAVE)
    obs_wave = np.arange(4000.0, 7000.0, 3.0)
    response = np.interp(obs_wave, [4000, 7000], [0.3, 1.0])  # a camera far less sensitive in the blue
    obs = spectrum(*TYPES["F5V"], wave=obs_wave) * response + np.random.default_rng(2).normal(0, 0.01, len(obs_wave))
    ranked = templates.classify(obs_wave, obs, sorted(library.glob("*.fits")))
    assert ranked[0][0] == "F5V" and ranked[0][1] < ranked[1][1]


def test_classify_step_downloads_an_empty_library(tmp_path, monkeypatch, library):
    from astrowb.spectroscopy import spectrum_io

    class Ctx:
        def progress(self, *a):
            pass

    sources = sorted(library.glob("*.fits"))
    monkeypatch.setattr(templates, "PICKLES_N", len(sources))
    real = templates.download_pickles
    monkeypatch.setattr(
        templates,
        "download_pickles",
        lambda folder: real(folder, fetch=lambda url: sources[int(url.split("_")[-1][:-5]) - 1].read_bytes()),
    )
    from astrowb.spectroscopy import mkstandards

    def offline(folder):
        raise OSError("no internet")

    monkeypatch.setattr(mkstandards, "download", offline)  # the MK standards: tested in test_mkstandards.py
    spectrum_io.write(tmp_path / "star.fits", WAVE, spectrum(*TYPES["K5V"]), np.full(len(WAVE), 0.01))
    out = execute(
        "spectroscopy.classify", {"spectrum": str(tmp_path / "star.fits"), "library": str(tmp_path / "new")}, {}, Ctx()
    )
    assert out["classes"][0]["type"] == "K5V" and len(list((tmp_path / "new").glob("*.fits"))) == 4
    assert out["mk"] is None and out["mk_note"] == "no internet"  # the library ranking stays


def test_velocity_tab_shows_the_type_and_takes_the_template(qtbot):
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    sent = []
    tab.classify_requested.connect(sent.append)
    tab.files.addItem("/data/star.fits")
    tab._classify()
    assert sent == ["/data/star.fits"]
    tab.show_classes(
        [{"type": "G2V", "rms": 0.01, "template": "/lib/g2v.fits"}, {"type": "G5V", "rms": 0.02, "template": "x"}]
    )
    assert "G2V (0.010), G5V" in tab.status.text() and tab.template.text() == "/lib/g2v.fits"


def test_a_noisy_echelle_spectrum_is_classified_at_the_library_resolution(tmp_path):
    """The TOFES spectrum of Arcturus (R 32000, 5 s on a 20 cm telescope): sharp lines with noise, and noise around
    zero in the blue. Compared at its own resolution, smooth hot-star templates won (Arcturus came out B2IV)."""
    for i, (t, (b, m)) in enumerate(TYPES.items()):  # a library at Pickles' 5 A resolution
        pickles_like(tmp_path / f"pickles_uk_{i + 1}.fits", t, b, m, width=5 / 2.355)
    wave = np.arange(3900.0, 7300.0, 0.08)
    for sptype in ("G2V", "A0V"):
        balmer, metal = TYPES[sptype]
        flux = np.ones_like(wave)  # Balmer lines broad by nature (as in the library), metal lines sharp
        for lam in (6563, 4861, 4341, 4102, 3970):
            flux -= balmer * np.exp(-0.5 * ((wave - lam) / (3 * 5 / 2.355)) ** 2)
        for lam in METALS:  # the library's equivalent widths
            flux -= metal * 0.5 * np.exp(-0.5 * ((wave - lam) / 0.8) ** 2) * (5 / 2.355) / 0.8
        rng = np.random.default_rng(3)
        flux = 300 * flux * (1 + 2e-4 * (wave - 5000)) * (1 + 0.3 * np.sin(wave / 40))  # merged-order ripples
        flux += rng.normal(0, 30, wave.size)
        flux[wave < 4500] = rng.normal(0, 100, (wave < 4500).sum())  # the blue: noise around zero
        ranked = templates.classify(wave, flux, sorted(tmp_path.glob("*.fits")))
        assert ranked[0][0] == sptype
