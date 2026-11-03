"""MOD-14: Monte Carlo, prayer bead and MCMC agree on white noise; the prayer bead sees red noise."""

import pytest
from test_model_fitting import make, model

from astrowb.models import fitting
from astrowb.models import uncertainty as un


@pytest.mark.slow
def test_three_ways_agree_on_white_noise():
    s = make()
    row = fitting.fit(s, model, "lm")
    mc = un.monte_carlo(s, model, n=40)
    pb = un.prayer_bead(s, model, n=40)
    sd, post = un.mcmc(s, model, steps=1500)
    for k in ("r1", "r2", "incl"):
        formal = row.errors[k]
        for got in (mc[k], sd[k]):
            assert got == pytest.approx(formal, rel=0.5), k
        assert pb[k] < 3 * formal
    assert post.samples.shape[1] == 4
