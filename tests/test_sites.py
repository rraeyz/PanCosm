"""Known observatories: offline list, any case; the Plan page fills the site from a name."""

import pytest

from astrowb.planning.sites import find, observatories


def test_known_observatories():
    assert len(observatories()) > 300
    lat, lon, height = find("tug")
    assert lat == pytest.approx(36.824, abs=1e-3) and lon == pytest.approx(30.336, abs=1e-3) and height > 2000
    assert find("TUBITAK National Observatory") == find("TUG")
    assert find("nowhere at all") is None


def test_plan_page_fills_the_site(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.site_name.setText("Roque de los Muchachos")
    page.site_name.editingFinished.emit()
    assert page.lat.value() == pytest.approx(28.76, abs=0.01) and page.lon.value() == pytest.approx(-17.88, abs=0.01)
    assert page.site_name.completer().model().rowCount() > 300
