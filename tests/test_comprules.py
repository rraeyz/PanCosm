"""PHO-17: one star of each rejection kind gets exactly its reason; saturation late in the night is seen."""

import numpy as np

from astrowb.photometry import comprules as cr


def frame(stars, shape=(400, 400), seed=0, peaks=None):
    rng = np.random.default_rng(seed)
    img = 100 + rng.normal(0, 5, shape)
    yy, xx = np.indices(shape)
    for (x, y, g), p in zip(stars, peaks or [None] * len(stars), strict=True):
        amp = p if p is not None else 20000 * 10 ** (-0.4 * (g - 12))
        img += amp * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / 1.3**2)
    return img


def test_every_reason():
    # target, then one star per case
    layout = [
        (200, 200, 12.0, 0.8, 0, 0.01, 0),  # 0 target
        (100, 100, 12.2, 0.8, 0, 0.01, 0),  # 1 chosen
        (120, 300, 10.0, 0.8, 0, 0.01, 0),  # 2 too_bright
        (300, 120, 13.5, 0.8, 0, 0.01, 0),  # 3 too_faint
        (300, 300, 12.1, 0.8, 0, 0.08, 0),  # 4 catalogue_error
        (250, 100, 12.1, 0.8, 1, 0.01, 0),  # 5 variable_gaia
        (100, 250, 12.1, 0.8, 0, 0.01, 1),  # 6 noisy_gaia
        (20, 200, 12.1, 0.8, 0, 0.01, 0),  # 7 edge
        (160, 160, 12.1, 0.8, 0, 0.01, 0),  # 8 neighbour (9 is 8 px away)
        (168, 160, 13.0, 0.8, 0, 0.01, 0),  # 9 neighbour too
        (330, 200, 12.1, 0.8, 0, 0.01, 0),  # 10 saturated (late in the night)
        (200, 330, 12.1, 2.5, 0, 0.01, 0),  # 11 colour (required)
        (240, 240, 12.1, 0.8, 0, 0.01, 0),  # 12 variable_vsx
    ]
    x, y, g, c, var, e, noisy = (np.array(v) for v in zip(*layout, strict=True))
    stars = {"x": x, "y": y, "gmag": g, "bp_rp": c, "variable": var, "e_gmag": e, "noisy": noisy}
    pos = list(zip(x, y, g, strict=True))
    early = frame(pos)
    late = frame(pos, peaks=[None] * 10 + [60000] + [None] * 2)
    rules = cr.ComparisonRules(saturation=65000, colour_required=True, min_snr=10, count=1)
    rows = cr.judge(stars, 0, [early, late], [(0, 0), (0, 0)], rules, vsx_xy=[(240, 240)])
    got = {r["index"]: r["verdict"] for r in rows}
    assert got == {1: "chosen", 2: "too_bright", 3: "too_faint", 4: "catalogue_error", 5: "variable_gaia",
                   6: "noisy_gaia", 7: "edge", 8: "neighbour", 9: "neighbour", 10: "saturated", 11: "colour",
                   12: "variable_vsx"}  # fmt: skip
    first_only = cr.judge(stars, 0, [early], None, cr.ComparisonRules(saturation=65000, min_snr=10, count=1))
    assert next(r for r in first_only if r["index"] == 10)["verdict"] != "saturated"  # the first frame misses it
    assert cr.most_common_reasons(rows)[0] == "neighbour"
