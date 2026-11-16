import numpy as np

from astrowb.ui.photometry_page import PhotometryPage


def _page(qtbot):
    r = np.linspace(0, 20, 41)
    a = {
        "fwhm": 3.0,
        "best_snr_radius": 4.0,
        "encircled_at_aperture": 0.9,
        "r_ap": 4.0,
        "r_in": 10.0,
        "r_out": 16.0,
        "profile_r": r,
        "profile": np.exp(-(r**2) / 8),
    }
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.show_apertures(a)
    return page


def _lines(page):
    return page._aperture_lines.lines


def test_dragging_a_line_sets_its_field(qtbot):
    page = _page(qtbot)
    line = _lines(page)[1]
    line.setValue(11.27)
    line.sigPositionChangeFinished.emit(line)
    assert page.r_in.value() == 11.3
    assert [ln.value() for ln in _lines(page)] == [4.0, 11.3, 16.0]  # the line was redrawn from the fields


def test_changing_a_field_moves_its_line(qtbot):
    page = _page(qtbot)
    page.r_ap.setValue(6.5)
    assert [ln.value() for ln in _lines(page)] == [6.5, 10.0, 16.0]


def test_dragging_is_clamped_between_the_neighbours(qtbot):
    page = _page(qtbot)
    for i, to, want in ((0, 12.0, 9.9), (1, 2.0, 4.1), (1, 30.0, 15.9), (2, 5.0, 10.1)):
        line = _lines(page)[i]
        line.setValue(to)
        line.sigPositionChangeFinished.emit(line)
        spins = (page.r_ap, page.r_in, page.r_out)
        assert spins[i].value() == want
        assert _lines(page)[i].value() == want
        page.r_ap.setValue(4.0), page.r_in.setValue(10.0), page.r_out.setValue(16.0)
