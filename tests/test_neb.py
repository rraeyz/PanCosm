"""PHO-23: a faint neighbour's deep eclipse is a potential NEB; quiet stars are cleared."""

import numpy as np

from astrowb.photometry import neb


def test_dispositions():
    rng = np.random.default_rng(0)
    n = 400
    t = np.linspace(0, 0.3, n)
    target = 50000 * (1 + rng.normal(0, 0.001, n))
    window = (t > 0.1) & (t < 0.2)
    eclipsing = 3000 * (1 - 0.2 * window) * (1 + rng.normal(0, 0.003, n))  # 3 mag fainter, a 20 % eclipse
    quiet = 3000 * (1 + rng.normal(0, 0.003, n))
    faint = 30 * (1 + rng.normal(0, 0.05, n))  # 8 mag fainter: it would need more than all its light
    empty = 0.5 * (1 + rng.normal(0, 0.1, n))
    rows = neb.check(target, {"neb": eclipsing, "quiet": quiet, "faint": faint, "empty": empty}, 5.0, pixels=10)
    got = {r["name"]: r for r in rows}
    # about 3 mag fainter (2.5 with the buffer): a 5 ppt target depth needs about 50 ppt there
    dmag = got["quiet"]["dmag"]
    assert (
        abs(dmag - 2.5 * np.log10(50000 / 3000)) < 0.01
        and abs(got["quiet"]["required_ppt"] - 5 * 10 ** ((dmag - 0.5) / 2.5)) < 1e-9
    )
    assert got["quiet"]["disposition"] == "Cleared"
    assert got["neb"]["disposition"] in ("Not cleared", "Likely cleared")  # the eclipse inflates its scatter
    assert got["faint"]["disposition"] == "Cleared - too faint"
    assert got["empty"]["disposition"] == "Not cleared - flux too low"
    assert neb.best(["Not cleared", "Likely cleared", "Cleared - too faint"]) == "Likely cleared"
    idx = neb.candidates([1.0, 4.0, 9.0, 2.0], 5.0, 150, [30, 60, 90, 200])
    assert list(idx) == [0, 1]
