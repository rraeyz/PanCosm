"""WD export: Roche potentials checked against the full potential at each star's pole; files written."""

import numpy as np
import pytest

from astrowb.models.wd import omega1, omega2, write_wd_files


def roche(x, y, z, q):
    """Synchronous circular Roche potential, separation 1, origin at star 1 (Wilson 1979)."""
    r1 = np.sqrt(x**2 + y**2 + z**2)
    r2 = np.sqrt((x - 1) ** 2 + y**2 + z**2)
    return 1 / r1 + q * (1 / r2 - x) + (1 + q) / 2 * (x**2 + y**2)


@pytest.mark.parametrize("q", [0.3, 0.8, 1.0, 1.7])
def test_potentials_are_those_at_the_poles(q):
    assert omega1(0.21, q) == pytest.approx(roche(0.0, 0.0, 0.21, q), rel=1e-12)
    assert omega2(0.13, q) == pytest.approx(roche(1.0, 0.0, 0.13, q), rel=1e-12)


def test_files(tmp_path):
    fit = {
        "params": {"period": 1.5, "t0": 2459500.3, "incl": 87.0, "l3": 0.0, "j": 0.6},
        "derived": {"e": 0.0, "omega": 90.0, "r1": 0.2, "r2": 0.15},
    }
    t = np.linspace(2459500, 2459503, 50)
    paths = write_wd_files(tmp_path, t, np.ones(50), np.full(50, 0.002), fit, q=0.7, orbit={"gamma": -12.0, "a": 8.1})
    sheet = (tmp_path / "wd_parameters.txt").read_text()
    assert f"PHSV    {omega1(0.2, 0.7):.5f}" in sheet and "VGA     -0.12000" in sheet and "PERR0   1.57080" in sheet
    rows = np.loadtxt(tmp_path / "lc.dat")
    assert rows.shape == (50, 3) and np.allclose(rows[:, 2], 1.0) and len(paths) == 2
    write_wd_files(tmp_path / "noq", t, np.ones(50), None, fit)
    assert "need the mass ratio" in (tmp_path / "noq" / "wd_parameters.txt").read_text()


def test_fit_step_exports_for_wd(tmp_path):
    from astrowb.engine.steps import execute
    from astrowb.models import fit

    class Ctx:
        def progress(self, *a):
            pass

    truth = {
        "period": 1.5,
        "t0": 0.3,
        "r_sum": 0.3,
        "k": 0.7,
        "incl": 87.0,
        "j": 0.6,
        "ecosw": 0.0,
        "esinw": 0.0,
        "l3": 0.0,
    }
    t = np.linspace(0, 3, 600)
    (tmp_path / "lc.csv").write_text(
        "time,rel_flux\n" + "\n".join(f"{a},{b}" for a, b in zip(t, fit.model(t, truth), strict=True))
    )
    from astrowb.spectroscopy.orbit import sb2_dimensions

    inputs = {
        "light_curve": str(tmp_path / "lc.csv"),
        "start": truth,
        "export_dir": str(tmp_path / "wd"),
        "orbit": {
            "k": 80.0,
            "k2": 100.0,
            "gamma": 5.0,
            "m1_sin3i": 1.2,
            "m1_sin3i_err": 0.01,
            "m2_sin3i": 0.96,
            "m2_sin3i_err": 0.01,
            "a_sini_rsun": 7.0,
            "a_sini_err": 0.05,
            "period": 7.0 / sb2_dimensions(1.0, 0.0, 80.0, 100.0)[2],  # a sin i = 7.0 solar radii
            "e": 0.0,
        },
    }
    out = execute("models.eb_fit", inputs, {"export_format": "wd"}, Ctx())["model"]
    assert any(p.endswith("wd_parameters.txt") for p in out["exported"])
    sheet = (tmp_path / "wd" / "wd_parameters.txt").read_text()
    import re

    assert float(re.search(r"RM +([0-9.]+)", sheet).group(1)) == pytest.approx(0.8, abs=0.002)  # q = M2/M1 = K1/K2
    assert "VGA     0.05000" in sheet and "A       7.0" in sheet
