"""PHO-36: the Checks tab lists S, B and C frames with a kind each; "Leave out the flagged points" takes them all."""

import pytest

from astrowb.photometry.quality import lc_checks
from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_every_letter_has_its_kind_and_is_left_out(window):
    window.show_workspace("photometry")
    page = window.photometry_page
    n = 20
    lc = {"file": [f"f{i}.fits" for i in range(n)], "rel_flux": [1.0] * n, "xy": [[[100.0, 100.0]]] * n,
          "peak": [[2e4]] * n, "saturation": 6e4, "fwhm": [3.0] * n, "comp_flux": [[1e5]] * n,
          "flags": [["S" if i == 3 else "B" if i == 5 else "C" if i == 7 else "R" if i == 9 else ""]
                    for i in range(n)], "var_plane": [i < 5 for i in range(n)]}  # fmt: skip
    kinds = lc_checks(lc)[0]
    assert (kinds["saturated_pixel"], kinds["bad_pixel"], kinds["spike"]) == ([3], [5], [7])  # R is marked, not listed
    page.checks.show_checks(lc)
    labels = [a.text() for a in page.checks.leave_kind.menu().actions()]
    assert labels == ["cosmic ray or hot pixel in an aperture (1)", "saturated pixel in an aperture (1)",
                      "bad pixel or no data in an aperture (1)"]  # fmt: skip
    assert {r for v in page.checks.flags.values() for r in v} == {3, 5, 7}
