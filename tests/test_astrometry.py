import sys
import textwrap

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb import astrometry

FAKE = textwrap.dedent(
    """
    import sys
    from astropy.io import fits
    args = sys.argv[1:]
    open(sys.argv[0] + ".args", "w").write(" ".join(args))
    kind = "{kind}"
    if kind == "astap-fail":
        sys.exit(2)
    if kind == "astap":
        out = args[args.index("-o") + 1] + ".wcs"
    else:
        out = args[args.index("--dir") + 1] + "/" + args[args.index("--out") + 1] + ".wcs"
    h = fits.Header({{"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRPIX1": 40.0, "CRPIX2": 30.0,
                      "CRVAL1": 31.04, "CRVAL2": 46.69, "CD1_1": -0.00145, "CD1_2": 0.0, "CD2_1": 0.0,
                      "CD2_2": 0.00145, "EQUINOX": 2000.0, "NOTAWCS": 1}})
    if kind == "astrometry":
        h["COMMENT"] = "index id: 4206"  # as astrometry.net records the index that solved it
    h.tofile(out, overwrite=True)
    """
)


def fake(tmp_path, kind):
    script = tmp_path / f"fake_{kind}.py"
    script.write_text(FAKE.format(kind=kind))
    return ("astap" if kind.startswith("astap") else "astrometry.net"), [sys.executable, str(script)]


@pytest.fixture
def image(tmp_path):
    p = tmp_path / "img.fits"
    fits.PrimaryHDU(np.zeros((60, 80), np.float32), fits.Header({"OBJECT": "X", "CRVAL1": 1.0})).writeto(p)
    return p


@pytest.mark.parametrize("kind", ["astap", "astrometry"])
def test_solve_and_apply(tmp_path, image, kind):
    solver = fake(tmp_path, kind)
    wcs = astrometry.solve(image, solver, ra_deg=31.0, dec_deg=46.7, radius_deg=5)
    assert "NOTAWCS" not in wcs and WCS(wcs).has_celestial
    assert wcs.get("ASTCAT") == (None if kind == "astap" else "2MASS")  # the 4200 indexes are built from 2MASS
    args = (tmp_path / f"fake_{kind}.py.args").read_text().split()
    if kind == "astap":
        assert args[args.index("-ra") + 1].startswith("2.0666") and args[args.index("-spd") + 1] == "136.7"
    else:
        assert args[args.index("--ra") + 1] == "31.0"
    astrometry.apply_solution(image, wcs, kind)
    h = fits.getheader(image)
    assert h["CRVAL1"] == 31.04 and h["OBJECT"] == "X" and "plate solving" in str(h["HISTORY"])
    sky = WCS(h).pixel_to_world(39, 29)  # CRPIX is 1-based
    assert abs(sky.ra.deg - 31.04) < 1e-9


def test_astap_error_codes_are_explained(tmp_path, image):
    with pytest.raises(astrometry.SolveError, match="not enough stars"):
        astrometry.solve(image, fake(tmp_path, "astap-fail"))


def test_no_solver(monkeypatch, image):
    monkeypatch.setattr(astrometry, "find_solver", lambda: None)
    with pytest.raises(astrometry.SolveError, match="install ASTAP"):
        astrometry.solve(image)


def test_solve_step_writes_a_copy(tmp_path, image, monkeypatch):
    from astrowb.engine import steps

    monkeypatch.setattr(astrometry, "find_solver", lambda: fake(tmp_path, "astap"))

    class Ctx:
        def progress(self, *a):
            pass

    out = steps.execute("astrometry.solve", {"image": str(image)}, {}, Ctx())
    assert out["solved"].endswith("img_wcs.fits")
    assert fits.getheader(out["solved"])["CRVAL1"] == 31.04
    assert fits.getheader(image)["CRVAL1"] == 1.0  # original untouched
