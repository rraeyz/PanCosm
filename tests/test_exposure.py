"""Exposure time calculator: the time it gives reaches the wanted S/N; known limits of the CCD equation."""

import math

import pytest

from astrowb.planning.exposure import exposure_time, saturation_seconds, snr


def test_time_gives_the_wanted_snr():
    kw = dict(magnitude=12.0, zero_point=21.0, sky=5.0, read_noise=10.0, aperture_px=5.0, dark=0.1)
    t = exposure_time(100, **kw)
    assert snr(t, **kw) == pytest.approx(100, rel=1e-9)


def test_bright_star_limit_is_photon_noise():
    # no sky, no read noise: S/N = sqrt(S t) -> t = SNR^2 / S
    t = exposure_time(100, magnitude=10.0, zero_point=20.0)
    assert t == pytest.approx(100**2 / 10**4, rel=1e-9)


def test_saturation_time():
    # FWHM 3 px: the peak pixel holds 4 ln2 / (9 pi) of the flux
    t = saturation_seconds(50000, magnitude=10.0, zero_point=20.0, fwhm_px=3.0)
    assert t == pytest.approx(50000 / (1e4 * 4 * math.log(2) / (9 * math.pi)))


def test_dialog_on_the_plan_page(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.plan_page import PlanPage

    settings = Settings(tmp_path)
    page = PlanPage(settings)
    qtbot.addWidget(page)
    dlg = page.exposure_dialog()
    dlg.fields["magnitude"].setValue(10.0)
    dlg.fields["zero_point"].setValue(20.0)
    for key in ("sky", "read_noise", "dark"):
        dlg.fields[key].setValue(0.0)
    dlg.fields["snr"].setValue(100)
    assert dlg.update() == pytest.approx(1.0)  # photon noise only: 100^2 / 10^4 s
    assert "1.0 s" in dlg.result.text()
    assert settings.get("exposure_calculator")["magnitude"] == 10.0  # remembered for next time
    dlg.close()


def test_plugins_menu_shows_readable_names(qtbot, tmp_path, monkeypatch):
    from astrowb.engine import plugins, steps
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    monkeypatch.setattr(steps, "REGISTRY", dict(steps.REGISTRY))  # the examples must not stay for other tests
    monkeypatch.setattr(plugins, "_loaded", set())
    monkeypatch.setattr(plugins, "plugin_dir", lambda: tmp_path / "plugins")
    plugins.install_examples(tmp_path / "plugins")
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win._fill_plugins_menu()
    texts = [a.text() for a in win.plugins_menu.actions()]
    assert "Median sky level and noise of a FITS image (stars clipped)" in texts
    assert not any(t.startswith("plugin.") for t in texts)
    win.engine.shutdown()
