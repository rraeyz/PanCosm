"""PHO-32: TESScut sector list and cut-outs through services/mast; the client is answered in the test."""

from pathlib import Path

import pytest
from astropy.table import Table

from astrowb.engine.steps import execute
from astrowb.services import mast


class FakeTesscut:
    def __init__(self, sectors=(20, 47)):
        self.sectors, self.calls = sectors, []

    def get_sectors(self, objectname):
        self.calls.append(("sectors", objectname))
        return Table(
            {"sectorName": [f"tess-s{s:04d}-1-2" for s in self.sectors], "sector": list(self.sectors),
             "camera": [1] * len(self.sectors), "ccd": [2] * len(self.sectors)}
        )  # fmt: skip

    def download_cutouts(self, objectname, size, sector, path):
        self.calls.append(("cutouts", objectname, size, sector))
        names = [f"tess-s{s:04d}-1-2_{size}x{size}_astrocut.fits" for s in self.sectors if sector in (None, s)]
        for n in names:
            (Path(path) / n).write_bytes(b"x")
        return Table({"Local Path": [str(Path(path) / n) for n in names]})


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_sectors_and_cutouts_are_kept_and_fetched_again_when_deleted(tmp_path):
    fake = FakeTesscut()
    assert mast.tess_sectors("WASP-12", fake) == [
        {"sector": 20, "camera": 1, "ccd": 2},
        {"sector": 47, "camera": 1, "ccd": 2},
    ]
    mast.tess_sectors("WASP-12", fake)
    paths = mast.tess_cutout("WASP-12", tmp_path, 11, 20, fake)
    assert [Path(p).name for p in paths] == ["tess-s0020-1-2_11x11_astrocut.fits"]
    assert mast.tess_cutout("WASP-12", tmp_path, 11, 20, fake) == paths
    assert [c[0] for c in fake.calls] == ["sectors", "cutouts"]  # both answers kept
    Path(paths[0]).unlink()
    assert mast.tess_cutout("WASP-12", tmp_path, 11, 20, fake) == paths and Path(paths[0]).exists()
    assert len(fake.calls) == 3


def test_no_sectors_is_an_error_and_is_not_kept(tmp_path):
    fake = FakeTesscut(sectors=())
    for _ in range(2):
        with pytest.raises(ValueError, match="no TESS full-frame images of Polaris"):
            mast.tess_sectors("Polaris", fake)
    assert len(fake.calls) == 2


def test_step_gives_one_pixel_file_per_sector(tmp_path, monkeypatch):
    fake = FakeTesscut()
    for name in ("tess_sectors", "tess_cutout"):
        real = getattr(mast, name)
        monkeypatch.setattr(mast, name, lambda *a, _r=real: _r(*a, tesscut=fake))
    out = execute("photometry.tesscut", {"target": "AI Dra", "cache": str(tmp_path)}, {}, Ctx())
    assert len(out["images"]) == 2 and [s["sector"] for s in out["sectors"]] == [20, 47]
    assert fake.calls[-1] == ("cutouts", "AI Dra", 15, None)  # default size, every sector
