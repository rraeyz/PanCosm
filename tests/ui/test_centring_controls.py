"""PHO-44: the window's centring box and largest move reach the measurement; the provenance names the method."""

import numpy as np

from astrowb.photometry import live
from astrowb.photometry.measure_params import MEASURE
from astrowb.ui.area_windows import _provenance
from astrowb.ui.photometry_method import method_params
from astrowb.ui.photometry_page import PhotometryPage


def test_defaults_are_the_engines_and_values_are_passed(qtbot):
    page = PhotometryPage()
    qtbot.addWidget(page)
    p = method_params(page)
    assert (p["box"], p["max_move"]) == (11, 2.5)  # recenter's own defaults
    page.centring_box.setValue(15)
    page.centring_max_move.setValue(4.0)
    page.centring.setCurrentIndex(page.centring.findData("gauss"))
    p = method_params(page)
    assert (p["box"], p["max_move"], p["centring"]) == (15, 4.0, "gauss")
    assert {"box", "max_move"} <= {x.name for x in MEASURE}


def test_live_session_takes_box_and_max_move():
    s = live.LiveLightCurve((10, 10), [(20, 20)], 4, 10, 16, box=15, max_move=4.0)
    assert (s.box, s.opts["max_move"]) == (15, 4.0)


def test_provenance_records_the_centring_method(qtbot, tmp_path):
    page = PhotometryPage()
    qtbot.addWidget(page)
    f = tmp_path / "a.fits"
    f.write_bytes(np.zeros(4).tobytes())
    page.last_measure = ([str(f)], [1, 2], [[3, 4]], "", {"centring": "gauss", "box": 15, "max_move": 4.0})
    params = _provenance(page)["params"]
    assert (params["Centring_Method"], params["box"], params["max_move"]) == ("gauss", 15, 4.0)
