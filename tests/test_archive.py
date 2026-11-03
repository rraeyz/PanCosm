"""TESS / Kepler light curves: pipeline files read with the right time system; the download is mocked."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table

from astrowb.engine.steps import execute
from astrowb.timeseries import archive


def lc_file(path, ref=(2457000, 0.0), sector=14, n=500, level=1000.0, telescope="TESS"):
    t = np.linspace(1683.0, 1708.0, n)
    flux = level * (1 - 0.01 * (np.abs((t - 1690.0) % 2.5) < 0.1))
    q = np.zeros(n, int)
    q[::50] = 512  # pipeline flags
    flux[7] = np.nan
    cols = [
        fits.Column(name=k, format="D", array=v)
        for k, v in (
            ("TIME", t),
            ("PDCSAP_FLUX", flux),
            ("PDCSAP_FLUX_ERR", np.full(n, 0.5)),
            ("SAP_FLUX", flux),
            ("SAP_FLUX_ERR", np.full(n, 0.5)),
        )
    ]
    cols.append(fits.Column(name="QUALITY", format="J", array=q))
    hdu = fits.BinTableHDU.from_columns(cols, name="LIGHTCURVE")
    hdu.header["BJDREFI"], hdu.header["BJDREFF"] = ref
    fits.HDUList([fits.PrimaryHDU(header=fits.Header({"TELESCOP": telescope, "SECTOR": sector})), hdu]).writeto(path)
    return str(path)


def test_read_and_join():
    import tempfile
    from pathlib import Path

    d = Path(tempfile.mkdtemp())
    a = archive.read_mission_lc(lc_file(d / "a.fits", sector=14))
    b = archive.read_mission_lc(lc_file(d / "b.fits", sector=15, level=1300.0))
    assert a["time"][0] == pytest.approx(2457000 + 1683.0) and a["time_scale"] == "BJD_TDB"
    assert len(a["time"]) == 500 - 10 - 1  # flagged and NaN points dropped
    assert np.median(b["rel_flux"]) == pytest.approx(1.0) and a["source"] == "TESS 14"
    j = archive.join([b, a])
    assert np.all(np.diff(j["time"]) >= 0) and j["source"] == "TESS 15, TESS 14"


class FakeObservations:
    def query_criteria(self, **kw):
        assert kw["obs_collection"] == "TESS" and kw["objectname"] == "AI Dra"
        return Table({"obsid": [1]})

    def get_product_list(self, obs):
        return Table(
            {"productSubGroupDescription": ["LC", "TPF", "LC"], "provenance_name": ["SPOC", "SPOC", "TESS-SPOC"]}
        )

    def download_products(self, products, download_dir, cache):
        self.folder = download_dir
        return Table({"Local Path": [lc_file(f"{download_dir}/s{i}.fits", sector=i) for i in range(len(products))]})


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_mission_step_with_a_mocked_archive(tmp_path, monkeypatch):
    fake = FakeObservations()
    real = archive.download
    monkeypatch.setattr(archive, "download", lambda *a, **k: real(*a, observations=fake, **k))
    out = execute("timeseries.mission_lc", {"target": "AI Dra", "folder": str(tmp_path)}, {}, Ctx())["light_curve"]
    assert len(out["time"]) == 489 and out["source"] == "TESS 0"  # the SPOC light curve; TESS-SPOC only without it


def test_period_page_downloads_through_the_main_window(qtbot, tmp_path, monkeypatch):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        sent = []
        monkeypatch.setattr(
            win, "run_step", lambda sid, inputs, params, on_done, on_fail: sent.append((sid, inputs, params, on_done))
        )
        page = win.period_page
        page.archive_target.setText("AI Dra")
        page.mission.setCurrentText("Kepler")
        page._fetch()
        sid, inputs, params, on_done = sent[0]
        assert (
            sid == "timeseries.mission_lc" and params == {"mission": "Kepler"} and inputs["folder"].endswith("archive")
        )
        on_done({"light_curve": {"time": list(range(20)), "rel_flux": [1.0] * 20, "source": "Kepler 3"}})
        assert page.source.text() == "20 points from AI Dra (Kepler 3)" and page.search_button.isEnabled()
        page.mission.setCurrentText("ZTF")
        page._fetch()
        assert page.source.text() == "Downloading from IRSA…"  # not MAST; a failure replaces it with the error
    finally:
        win.engine.shutdown()
