"""CAL-1: the same night in two folder layouts gives the same groups; a flat at 95 % of saturation is marked with its
reason; a frame of another level stands out; two nights in one folder give two nights of groups."""

import shutil

import numpy as np
from astropy.io import fits

from astrowb.calibration import groups
from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def night(folder, evening="2026-11-13", flat_level=30000.0, odd=False):
    rng = np.random.default_rng(1)
    shape = (64, 64)
    kinds = [("bias", "BIAS", 0.0, 300.0, None)] * 4 + [("dark", "DARK", 60.0, 340.0, None)] * 3
    kinds += [("flat", "FLAT", 1.0, flat_level, "V")] * 4 + [("light", "LIGHT", 60.0, 900.0, "V")] * 5
    for i, (name, typ, exp, level, filt) in enumerate(kinds):
        h = fits.Header({"IMAGETYP": typ, "EXPTIME": exp, "DATE-OBS": f"{evening}T20:{i:02d}:00", "XBINNING": 2,
                         "YBINNING": 2})  # fmt: skip
        if filt:
            h["FILTER"] = filt
        if odd and i == 1:
            level += 400  # a bias that is not like the others
        p = folder / f"{name}_{evening}_{i:02d}.fits"
        p.parent.mkdir(parents=True, exist_ok=True)
        fits.PrimaryHDU((level + rng.normal(0, 5, shape)).astype(np.float32), h).writeto(p)
    return folder


def scanned(folder):
    return execute("calibration.scan", {"folder": str(folder)}, {}, Ctx())["frames"]


def signature(gs):
    return sorted((g["kind"], g["filter"], g["exptime"], g["night"], g["count"]) for g in gs)


def test_layouts_give_the_same_groups(tmp_path):
    flat = night(tmp_path / "flat")
    typed = tmp_path / "typed"
    for p in flat.iterdir():  # Bias/, Dark/, Flat/, Light/ sub-folders
        (typed / p.name.split("_")[0].capitalize()).mkdir(parents=True, exist_ok=True)
        shutil.copy(p, typed / p.name.split("_")[0].capitalize() / p.name)
    assert signature(groups.group(scanned(flat))) == signature(groups.group(scanned(typed)))
    assert [g["kind"] for g in groups.group(scanned(flat))] == ["bias", "dark", "flat", "light"]


def test_marks_and_two_nights(tmp_path):
    folder = night(tmp_path / "a", flat_level=62000.0, odd=True)
    night(folder, evening="2026-11-14")
    gs = groups.group(scanned(folder))
    assert sorted({g["night"] for g in gs}) == ["2026-11-13", "2026-11-14"]
    flat = next(g for g in gs if g["kind"] == "flat" and g["night"] == "2026-11-13")
    marks = groups.outliers(flat)
    assert len(marks) == 4 and all("95%" in m for m in marks.values())
    bias = next(g for g in gs if g["kind"] == "bias" and g["night"] == "2026-11-13")
    odd = groups.outliers(bias)
    assert len(odd) == 1 and "level" in next(iter(odd.values()))
