"""PHO-18: catalogue neighbours inside the sky ring (photometry.neighbours) and the Measure stage's banner."""

from astrowb.photometry.neighbours import find

CAT = {
    "x": [100.0, 110.0, 130.0, 100.0, 90.0],
    "y": [100.0, 100.0, 100.0, 108.0, 100.0],
    "gmag": [12.0, 15.5, 14.0, 16.5, 17.0],
}


def test_rule_inside_outside_and_brightness():
    got = find([(100.0, 100.0)], CAT, r_out=16.0, target_mag=12.0)
    # the star on the target is itself; (130,100) is outside r_out; (100,108) is 16.5 > 16.0; (90,100) 17.0 too faint
    assert [n["gmag"] for n in got[0]["neighbours"]] == [15.5]
    assert got[0]["neighbours"][0]["distance"] == 10.0
    assert find([(100.0, 100.0)], CAT, r_out=35.0, target_mag=12.0)[0]["neighbours"][-1]["gmag"] == 14.0
    assert find([(100.0, 100.0)], CAT, r_out=16.0, target_mag=10.0) == []  # nothing brighter than 14
    assert find([(500.0, 500.0)], CAT, r_out=16.0, target_mag=12.0) == []


def test_banner_text_and_button(qtbot):
    from astrowb.ui.photometry_banner import neighbour_banner
    from astrowb.ui.photometry_page import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.field = {"stars": CAT}
    page.target, page.comps = (100.0, 100.0), [(300.0, 300.0)]
    page.r_out.setValue(16.0)
    banner = neighbour_banner(page)
    assert banner.text() == (
        "1 catalogue star(s) brighter than the target + 4 mag lie inside the sky ring of T1. "
        "Measuring with “Remove neighbours” may give a cleaner light curve."
    )
    assert not page.remove_neighbours.isChecked()
    banner.buttons[0].click()
    assert page.remove_neighbours.isChecked()
    assert neighbour_banner(page) is None  # already on: no banner
