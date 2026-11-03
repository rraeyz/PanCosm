"""MOD-19: the solution table marks fixed and constrained parameters."""

from astrowb.models import report
from astrowb.models import system as sm


def test_the_solution_table():
    s = sm.default_system()
    s.morphology = "semi-detached-2"
    s.apply()
    text = report.solution_latex(s, {"incl": 0.123, "q": 0.0042, "t2": 31.0}, "MCMC (DE-MC, R̂ < 1.01)")
    assert "$i$ (deg) & $85.00(12)$ \\\\" in text and "$q$ & $0.8000(42)$" in text
    assert "(star 2 fills its Roche lobe)" in text and "$T_1$ (K) & 6000 (fixed)" in text
    assert "errors: MCMC (DE-MC" in text
