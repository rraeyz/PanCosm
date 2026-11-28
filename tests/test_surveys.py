import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from astrowb.timeseries import surveys
from astrowb.timeseries.lightcurve import UPPER

STAR = SkyCoord(250.68375 * u.deg, 52.69028 * u.deg)
GEO = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)


def test_ztf_csv_with_hjd_becomes_bjd_tdb():
    t_obs = Time(2459000.5 + np.arange(5) * 37.3, format="jd", scale="utc", location=GEO)
    hjd = (t_obs + t_obs.light_travel_time(STAR, kind="heliocentric")).jd
    truth = (t_obs.tdb + t_obs.light_travel_time(STAR, kind="barycentric")).jd
    lines = ["oid,hjd,mjd,mag,magerr,catflags,filtercode"]
    for i, h in enumerate(hjd):
        lines.append(f"1,{h:.8f},0,{15 + 0.1 * i},0.01,0,zg")
    lines.append(f"1,{hjd[0]:.8f},0,14.0,0.01,32768,zg")  # flagged: dropped
    lines.append(f"2,{hjd[0]:.8f},0,14.5,0.01,0,zr")
    lines.append(f"2,{hjd[1]:.8f},0,14.6,0.01,0,zr")
    lc = surveys.to_light_curve(surveys.parse("\n".join(lines)), STAR, source="ZTF")
    assert lc["band"] == "zg" and lc["bands"] == ["zg", "zr"] and len(lc["time"]) == 5
    assert np.allclose(lc["time"], truth, atol=0.2 / 86400) and lc["time_scale"] == "BJD_TDB"
    assert np.allclose(lc["mag"], 15 + 0.1 * np.arange(5)) and lc["rel_flux"][2] == pytest.approx(1.0)


def test_aavso_and_asassn_files():
    aavso = "JD,Magnitude,Uncertainty,Band,Fainter Than\n2460000.1,8.1,0.02,V,0\n2460001.1,<9.5,,V,1\n"
    aavso += "2460002.1,8.3,0.02,V,0\n2460003.1,8.2,0.02,V,0\n2460003.2,8.9,,Vis.,0\n"
    rows = surveys.parse(aavso)
    assert len(rows) == 5 and {r[1] for r in rows} == {"jd"} and [r[5] for r in rows] == [0, UPPER, 0, 0, 0]
    lc = surveys.to_light_curve(rows, None, "V")
    assert lc["time_scale"] == "JD_UTC" and lc["mag"] == [8.1, 8.3, 8.2]
    assert lc["upper_limits"]["mag"] == [9.5] and lc["visual"]["mag"] == [8.9]
    asassn = "HJD,UT Date,Camera,FWHM,Limit,mag,mag_err,flux(mJy),flux_err,Filter\n"
    asassn += "\n".join(f"{2458000.5 + i},x,bb,1.5,17,{12 + 0.01 * i},0.02,1,0.1,V" for i in range(4))
    asassn += "\n2458010.5,x,bb,1.5,17,>17.1,99,0,0.1,V"
    lc = surveys.to_light_curve(surveys.parse(asassn), STAR)
    assert len(lc["time"]) == 4 and lc["time_scale"] == "BJD_TDB" and "visual" not in lc
    assert lc["upper_limits"]["mag"] == [17.1] and lc["upper_limits"]["time"][0] > lc["time"][-1]


def test_upper_limits_and_visual_estimates_are_their_own_sets_and_not_searched(qtbot, tmp_path, monkeypatch):
    from astrowb.timeseries import period
    from astrowb.ui.period_page import PeriodPage

    rng = np.random.default_rng(3)
    t = 2460000.0 + np.sort(rng.uniform(0, 60, 150))
    mag = 10 + 0.3 * np.sin(2 * np.pi * t / 3.7)
    lines = ["JD,Magnitude,Uncertainty,Band,Fainter Than"]
    lines += [f"{x:.5f},{m:.4f},0.01,V,0" for x, m in zip(t, mag, strict=True)]
    lines += [f"{x + 0.3:.5f},{m + 0.1:.4f},,Vis.,0" for x, m in zip(t[:40], mag[:40], strict=True)]
    # limits every 1.3 d, all at 13 mag: if searched, they would pull the periodogram to 1.3 d
    lines += [f"{x:.5f},<13.0,,V,1" for x in 2460000.0 + np.arange(45) * 1.3]
    lines += [f"{x:.5f},14.0,,Vis.,1" for x in 2460000.2 + np.arange(5) * 1.3]
    text = "\n".join(lines)
    rows = surveys.parse(text)
    assert sum(r[5] == UPPER for r in rows) == 50
    lc = surveys.to_light_curve(rows)
    assert lc["band"] == "V" and len(lc["time"]) == 150 and max(lc["mag"]) < 11
    assert len(lc["upper_limits"]["time"]) == 50 and len(lc["visual"]["time"]) == 40
    best = period.lomb_scargle(lc["time"], lc["rel_flux"], p_min=0.5, p_max=20)[2]
    assert best == pytest.approx(3.7, rel=0.02)
    path = tmp_path / "mira.csv"
    path.write_text(text)
    page = PeriodPage()
    qtbot.addWidget(page)
    page._load(str(path))
    assert len(page.time) == 150 and len(page.upper[0]) == 50
    names = [s.name for s in page.plot.figure.panels[0].series]
    assert "upper limits" in names
    sent = []
    page.search_requested.connect(lambda t, f, params: sent.append(t))
    page._search()
    assert len(sent[0]) == 150  # the limits are drawn, not searched


def test_online_queries_use_the_right_services():
    seen = []

    def fake(url, params):
        seen.append((url, params))
        return "JD,mag,uncert,band\n2460000.1,8.1,0.02,V\n"

    surveys.aavso("R Car", fetch=fake, from_jd=2459000)
    surveys.ztf(STAR, fetch=fake)
    assert seen[0][1]["ident"] == "R Car" and seen[0][1]["fromjd"] == "2459000.0"
    assert seen[1][0] == surveys.ZTF_URL and seen[1][1]["POS"].startswith("CIRCLE 250.683750 52.690280")


def test_survey_step_and_period_page_file(qtbot, tmp_path, monkeypatch):
    from astrowb.engine.steps import execute
    from astrowb.planning import targets
    from astrowb.ui.period_page import PeriodPage

    class Ctx:
        def progress(self, *a):
            pass

    monkeypatch.setattr(targets, "_simbad", lambda name: targets.Target(name, 250.68375, 52.69028, None, "SIMBAD"))
    monkeypatch.setattr(targets.Resolver.__init__, "__defaults__", (targets._simbad,))
    text = "oid,hjd,mag,magerr,catflags,filtercode\n" + "\n".join(
        f"1,{2459000.5 + i},{15 + 0.1 * (i % 2)},0.01,0,zr" for i in range(6)
    )
    monkeypatch.setattr(surveys, "_get_text", lambda url, params: text)
    out = execute("timeseries.survey_lc", {"target": "AI Dra", "cache_file": str(tmp_path / "t.json")}, {}, Ctx())
    lc = out["light_curve"]
    assert len(lc["time"]) == 6 and lc["time_scale"] == "BJD_TDB" and lc["source"] == "ZTF zr"
    path = tmp_path / "aavso.csv"
    path.write_text(
        "JD,Magnitude,Uncertainty,Band\n" + "\n".join(f"{2460000 + i},{8 + 0.01 * i},0.01,V" for i in range(12))
    )
    page = PeriodPage()
    qtbot.addWidget(page)
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", lambda *a, **k: (str(path), ""))
    page._load()
    assert len(page.time) == 12 and "(V)" in page.source.text()
    assert "not converted to BJD_TDB" in page.source.text()  # no coordinates: times kept, and said


def test_jd_utc_with_coordinates_becomes_timings_bjd_tdb():
    from astrowb import timing

    jd = 2459000.5 + np.arange(6) * 11.7
    rows = [(t, "jd", 10 + 0.01 * i, 0.01, "V") for i, t in enumerate(jd)]
    lc = surveys.to_light_curve(rows, STAR)
    truth = timing.bjd_tdb(Time(jd, format="jd", scale="utc"), STAR).jd
    assert np.allclose(lc["time"], truth, rtol=0, atol=1e-9) and lc["time_scale"] == "BJD_TDB"
    assert lc["time_scale_original"] == "JD_UTC" and "warnings" not in lc


def test_without_coordinates_times_are_kept_and_said():
    jd = 2459000.5 + np.arange(6) * 11.7
    lc = surveys.to_light_curve([(t, "jd", 10.0, 0.01, "V") for t in jd])
    assert lc["time"] == jd.tolist() and lc["time_scale"] == "JD_UTC"
    assert lc["warnings"] == [surveys.KEPT.format(standard="JD_UTC")]
    assert surveys.hjd_notes("HJD,mag\n", [2459000.5]) == [surveys.HJD_TAKEN_AS_UTC.format(s="69")]
    assert surveys.hjd_notes("HJD_UTC,mag\n", [2459000.5]) == []
