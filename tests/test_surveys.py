import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from astrowb.timeseries import surveys

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
    assert len(rows) == 4 and {r[1] for r in rows} == {"jd"}
    lc = surveys.to_light_curve(rows, None, "V")
    assert lc["time_scale"] == "JD_UTC" and lc["mag"] == [8.1, 8.3, 8.2]
    asassn = "HJD,UT Date,Camera,FWHM,Limit,mag,mag_err,flux(mJy),flux_err,Filter\n"
    asassn += "\n".join(f"{2458000.5 + i},x,bb,1.5,17,{12 + 0.01 * i},0.02,1,0.1,V" for i in range(4))
    asassn += "\n2458010.5,x,bb,1.5,17,>17.1,99,0,0.1,V"
    lc = surveys.to_light_curve(surveys.parse(asassn), STAR)
    assert len(lc["time"]) == 4 and lc["time_scale"] == "BJD_TDB"


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
