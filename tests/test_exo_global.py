"""EXO-7: transits in two bands with trends and velocities from two instruments, fitted together."""

import numpy as np
import pytest

from astrowb.exoplanets import global_fit as gf
from astrowb.exoplanets.rv import Planet
from astrowb.exoplanets.rv import model as rv_model
from astrowb.occult.model import transit

P, TC, K_RP, A, B, KV = 3.2, 2459000.3, 0.11, 9.0, 0.35, 45.0
LD = {"V": ("quadratic", (0.45, 0.2)), "I": ("quadratic", (0.3, 0.25))}


def data(seed=1):
    rng = np.random.default_rng(seed)
    inc = np.degrees(np.arccos(B / A))
    nights = []
    for n, band, slope in ((0, "V", 0.02), (5, "I", -0.03), (11, "V", 0.01)):
        tc = TC + n * P
        t = np.linspace(tc - 0.14, tc + 0.14, 220)
        f = transit(t - TC, P, 0.0, K_RP, A, inc, *LD[band]) * (1 + slope * (t - t.mean()))
        nights.append((t, f + rng.normal(0, 0.0012, t.size), np.full(t.size, 0.0012), band))
    rvs = []
    for gamma, n in ((-12.0, 18), (30.0, 12)):
        t = np.sort(TC + rng.uniform(-30, 60, n))
        v = rv_model(t, [Planet(P, TC, 0.0, 0.0, KV)], np.zeros(n, int), [gamma])
        rvs.append((t, v + rng.normal(0, 4.0, n), np.full(n, 4.0)))
    return nights, rvs


@pytest.mark.slow
def test_the_global_fit_recovers_the_planet():
    nights, rvs = data()
    start = {"period": P + 3e-4, "tc": TC + 0.003, "k": 0.1, "a_rs": 8.0, "b": 0.3, "K": 30.0}
    got = gf.fit(nights, rvs, [start], LD, steps=800)
    post = got["posterior"].summary()
    for name, truth in (("period_1", P), ("k_1", K_RP), ("K_1", KV), ("b_1", B), ("ln_a_1", np.log(A))):
        med, lo, hi = post[name]["median"], post[name]["minus"], post[name]["plus"]
        assert abs(med - truth) < 3 * max(lo, hi), name
    assert post["tc_1"]["median"] + got["model"].t_ref == pytest.approx(TC, abs=3 * post["tc_1"]["plus"])
    assert got["best"]["period_1"] == pytest.approx(P, abs=5e-5)
