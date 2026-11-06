"""The AAVSO comparison sequence (VSP): a recorded answer for Qatar-1's field parsed, matched to star positions in
the report's band, and kept: a second look-up with the network gone gives the same chart id."""

import pytest

from astrowb.services import aavso_vsp
from astrowb.services.cache import OfflineError

ANSWER = {"chartid": "X43370AGGP", "star": "Qatar-1", "fov": 20.0, "maglimit": 15.0, "photometry": [
    {"auid": "000-BLM-129", "ra": "20:11:58.03", "dec": "65:02:54.3", "label": "113", "bands": [
        {"band": "V", "mag": 11.333, "error": 0.02}, {"band": "B", "mag": 12.038, "error": 0.334},
        {"band": "Rc", "mag": 10.62, "error": 0.064}, {"band": "Ic", "mag": 9.958, "error": 0.089}]},
    {"auid": "000-BMR-629", "ra": "20:13:57.07", "dec": "65:15:08.1", "label": "116", "bands": [
        {"band": "V", "mag": 11.638, "error": 0.016}, {"band": "B", "mag": 12.265, "error": 0.315}]},
    {"auid": "000-BLM-130", "ra": "-0:12:52.16", "dec": "-05:03:14.1", "label": "117", "bands": [
        {"band": "V", "mag": 11.735, "error": 0.021}]}]}  # fmt: skip


def test_sequence_parsed_matched_and_kept_offline(monkeypatch):
    calls = []
    seq = aavso_vsp.sequence(303.38, 65.16, fov=20, fetch=lambda url: calls.append(url) or ANSWER)
    assert seq["chart"] == "X43370AGGP" and [s["label"] for s in seq["stars"]] == ["113", "116", "117"]
    s = seq["stars"][0]
    assert s["ra"] == pytest.approx(15 * (20 + 11 / 60 + 58.03 / 3600)) and s["dec"] == pytest.approx(
        65.04842, abs=1e-5
    )
    assert seq["stars"][2]["dec"] == pytest.approx(-(5 + 3 / 60 + 14.1 / 3600))  # the sign of "-05:…" kept
    near = (s["ra"] + 2 / 3600 / 0.42, s["dec"])  # 2″ east of 113
    got = aavso_vsp.sequence_magnitudes(seq, [near, (s["ra"], s["dec"] + 0.01), near], "V")
    assert got[0] == {"label": "113", "auid": "000-BLM-129", "mag": 11.333, "err": 0.02} and got[1] is None
    assert aavso_vsp.sequence_magnitudes(seq, [near], "R")[0]["mag"] == 10.62  # AAVSO's R is the sequence's Rc
    assert aavso_vsp.sequence_magnitudes(seq, [near], "U")[0] is None  # no U for that star

    monkeypatch.setenv("ASTROWB_OFFLINE", "1")
    again = aavso_vsp.sequence(303.38, 65.16, fov=20, fetch=lambda url: calls.append(url) or {})
    assert again["chart"] == "X43370AGGP" and len(calls) == 1
    with pytest.raises(OfflineError):
        aavso_vsp.sequence(10.0, 10.0, fetch=lambda url: ANSWER)


def test_a_field_without_a_sequence_says_so():
    with pytest.raises(LookupError):
        aavso_vsp.sequence(1.0, 2.0, fetch=lambda url: {"chartid": "X1", "photometry": []})


def test_report_dialog_takes_the_sequence_for_the_marked_stars(qtbot, tmp_path, monkeypatch):
    """The AAVSO report dialog's button: the comparison stars and the check star marked on a solved first frame get
    the sequence's V magnitudes, labels and the chart id; a star outside the sequence is named, nothing guessed."""
    from types import SimpleNamespace

    from astropy.wcs import WCS

    from astrowb.settings import Settings
    from astrowb.ui.aavso_dialog import AavsoDialog, from_sequence

    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [303.38, 65.16], [500, 500]
    w.wcs.cdelt = [-1 / 3600, 1 / 3600]  # 1″ pixels, east to the left
    stars = aavso_vsp.parse(ANSWER)["stars"]
    xy = [tuple(float(v) for v in w.world_to_pixel_values(s["ra"], s["dec"])) for s in stars[:2]]
    page = SimpleNamespace(field={"header": w.to_header().tostring()}, ref=0, target=(500.0, 500.0),
                           comps=[xy[0], (10.0, 10.0)], extras=[(xy[1], "check")])  # fmt: skip
    page._field_wcs = lambda: w
    monkeypatch.setattr(aavso_vsp, "sequence", lambda ra, dec, fov, maglimit: aavso_vsp.parse(ANSWER))
    d = AavsoDialog(2, settings=Settings(tmp_path), sequence=lambda filt: from_sequence(page, filt))
    qtbot.addWidget(d)
    d.filter.setCurrentText("V")
    d.sequence_button.click()
    assert d.chart.text() == "X43370AGGP" and d.check.text() == "116" and d.mags.text() == ""
    assert "C1 = 113" in d.sequence_note.text() and "C2" in d.sequence_note.text()
    page.comps = [xy[0]]
    d.sequence_button.click()
    assert d.mags.text() == "11.333" and d.values()["chart"] == "X43370AGGP"
    page.field = None
    d.sequence_button.click()
    assert "Identify the field" in d.sequence_note.text()


def test_the_sequence_drawn_over_a_solved_image(tmp_path, monkeypatch):
    """Images window → Overlays → AAVSO comparison stars: the sequence inside the frame at its pixels, labelled."""
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS

    from astrowb.engine.steps import execute

    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [303.0, 65.06], [200, 200]
    w.wcs.cdelt = [-3 / 3600, 3 / 3600]
    fits.PrimaryHDU(np.zeros((400, 400), np.float32), w.to_header()).writeto(tmp_path / "f.fits")
    asked = []
    monkeypatch.setattr(
        aavso_vsp, "sequence", lambda ra, dec, fov, maglimit: asked.append(fov) or aavso_vsp.parse(ANSWER)
    )

    class Ctx:
        def progress(self, *a):
            pass

    stars = execute("image.catalogue", {"image": str(tmp_path / "f.fits")}, {"catalogue": "aavso"}, Ctx())["stars"]
    assert [s["name"] for s in stars] == ["113"] and stars[0]["mag"] == 11.333  # 116 and 117 lie outside
    x, y = w.world_to_pixel_values(stars[0]["ra"], stars[0]["dec"])
    assert (stars[0]["x"], stars[0]["y"]) == pytest.approx((float(x), float(y)), abs=0.01)
    assert 25 < asked[0] < 32  # the frame's diagonal, 20′ × 20′


def test_comparison_magnitudes_from_the_sequence(tmp_path, monkeypatch):
    """Photometry's standard magnitudes with "AAVSO sequence": each comparison star's magnitude in the filter, its
    B − V for the colour term, the chart id kept for the report; a star outside the sequence gets none."""
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS

    from astrowb.engine.steps import execute

    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [303.0, 65.06], [200, 200]
    w.wcs.cdelt = [-3 / 3600, 3 / 3600]
    fits.PrimaryHDU(np.zeros((400, 400), np.float32), w.to_header()).writeto(tmp_path / "f.fits")
    monkeypatch.setattr(aavso_vsp, "sequence", lambda ra, dec, fov, maglimit: aavso_vsp.parse(ANSWER))
    s113 = aavso_vsp.parse(ANSWER)["stars"][0]
    comp = [float(v) for v in w.world_to_pixel_values(s113["ra"], s113["dec"])]

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    inputs = {"image": str(tmp_path / "f.fits"), "target_xy": [200, 200], "comps_xy": [comp, [20, 20]]}
    cat = execute("photometry.catalog", inputs, {"filter": "V", "source": "aavso"}, Ctx())["catalog"]
    assert cat["chart"] == "X43370AGGP" and cat["comps"][1] is None
    c = cat["comps"][0]
    assert c["mag"] == 11.333 and c["colour"] == pytest.approx(12.038 - 11.333) and c["source"].endswith("113")
