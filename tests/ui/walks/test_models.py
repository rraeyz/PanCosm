"""VAL-8: the Models window as a user goes through it: an eclipsing binary's light curve chosen, the period, the
primary minimum and a starting inclination typed into the table, Fit."""

import numpy as np
import pytest

from astrowb.models import fit

TRUTH = {"period": 1.7, "t0": 2459500.25, "r_sum": 0.3, "k": 0.6, "incl": 86.0, "j": 0.5, "ecosw": 0.0, "esinw": 0.0,
         "l3": 0.0}  # fmt: skip


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_fit_an_eclipsing_binary_light_curve(walk, tmp_path, lang):
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(2459500, 2459510, 800))
    f = fit.model(t, TRUTH, (0.4, 0.2), (0.4, 0.2)) + rng.normal(0, 0.003, len(t))
    path = tmp_path / "lc.csv"
    path.write_text("BJD_TDB,rel_flux,rel_flux_err\n" + "\n".join(f"{a},{b},0.003" for a, b in zip(t, f, strict=True)))
    h = walk(lang)
    h.area("orbits")
    page = h.page
    h.answer(path)
    h.click("file.browse_button")
    h.cell("table", 0, 1, "1.7")
    h.cell("table", 1, 1, "2459500.25")
    h.cell("table", 4, 1, "84")
    h.click("fit_button")
    h.wait(lambda: page.result is not None)
    h.check()
    assert abs(page.result["params"]["incl"] - 86) < 4 * page.result["errors"]["incl"]
