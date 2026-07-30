import numpy as np

from astrowb.engine.steps import execute
from astrowb.models import fit


class Ctx:
    def progress(self, *a):
        pass


def test_transit_report_files_and_mid_time(tmp_path):
    rng = np.random.default_rng(13)
    truth = {"period": 2.15000820, "t0": 2455867.402743, "r_sum": 0.165, "k": 0.1, "incl": 88.9}
    truth |= {"j": 0.0, "ecosw": 0.0, "esinw": 0.0, "l3": 0.0}
    tc = truth["t0"] + 1500 * truth["period"]  # this night's transit, 1500 orbits after the reference
    t = tc + np.linspace(-0.12, 0.12, 500)
    flux = fit.model(t, truth, (0.4, 0.25)) + rng.normal(0, 0.001, t.size)
    (tmp_path / "hatp32.csv").write_text(
        "time,rel_flux,rel_flux_err\n" + "\n".join(f"{a:.6f},{b:.6f},0.001" for a, b in zip(t, flux, strict=True))
    )
    inputs = {"light_curve": str(tmp_path / "hatp32.csv"), "start": truth | {"t0": tc + 0.003, "k": 0.12}}
    inputs["export_dir"] = str(tmp_path / "report")
    params = {"export_format": "transit", "free": ["t0", "r_sum", "k", "incl"], "ld1": (0.4, 0.25)}
    out = execute("models.eb_fit", inputs, params, Ctx())["model"]
    s = out["transit"]
    assert s["epoch"] == 0 and abs(s["tc"] - tc) < 4 * s["tc_err"] + 1e-5 and s["tc_err"] < 0.001
    assert abs(s["depth"] - 0.0115) < 0.002 and abs(s["rp_rs"] - 0.1) < 0.01
    assert 2.5 < s["t14"] * 24 < 3.5
    etd, exo, summ = (np.loadtxt(p) if p.endswith(("ETD.txt", "ExoClock.txt")) else p for p in out["exported"])
    assert etd.shape == (500, 3) and abs(np.median(etd[:, 1])) < 0.01 and abs(etd[0, 2] - 0.0011) < 0.0002
    assert np.allclose(exo[:, 0], t, atol=1e-6) and "Mid-transit time" in open(summ).read()
