"""VAL-8: the practice light curves and timings as a user goes through them (the guided tasks frequencies.toml,
oc-third-body.toml and sb2-orbit.toml, every step clicked or typed)."""

import pytest

from astrowb import sampledata


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_frequencies_of_the_practice_pulsator(walk, tmp_path, lang):
    h = walk(lang)
    h.area("timeseries")
    h.answer(sampledata.pulsator(tmp_path))
    h.click("period_page.load_button")
    h.click("frequency_page.button")
    page = h.page.frequency_page
    h.wait(lambda: page.result is not None)
    h.check()
    found = [row["freq"] for row in page.result["frequencies"]]
    assert found[0] == pytest.approx(8.123, abs=0.002) and any(abs(f - 11.470) < 0.002 for f in found[:3])


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_third_body_in_the_practice_minima(walk, tmp_path, lang):
    h = walk(lang)
    h.area("oc")
    h.answer(sampledata.minima(tmp_path))
    h.click("load_button")
    h.type("t0", "2455000.1234")
    h.type("period", "0.8123456")
    h.click("ltte")
    h.click("fit_button")
    h.wait(lambda: h.page.fit_result is not None and hasattr(h.page.fit_result, "p3"))
    h.check()
    assert h.page.fit_result.p3 == pytest.approx(2900, rel=0.15)
    assert h.page.fit_result.amplitude == pytest.approx(0.005, rel=0.3)


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_orbit_of_the_practice_double_lined_binary(walk, tmp_path, lang):
    h = walk(lang)
    h.area("spectroscopy")
    h.answer(sampledata.sb2(tmp_path))
    h.menu("Open a velocity table…")
    h.type("velocity_tab.period", 4.6)
    h.click("velocity_tab.orbit_button")
    tab = h.page.velocity_tab
    h.wait(lambda: tab.orbit_result is not None)
    h.check()
    assert tab.orbit_result["period"] == pytest.approx(4.634, abs=0.01)
