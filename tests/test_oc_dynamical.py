"""OC-10: the dynamical delay of a close third star against its light-time effect — the warning fires for
P₂ / P₁ = 30 and not for 3000."""

import pytest

from astrowb.timeseries import oc_dynamical as dyn


def test_the_warning_fires_only_for_a_compact_triple():
    close = dyn.check(1.0, 30.0)
    wide = dyn.check(1.0, 3000.0)
    assert close["warn"] and close["ratio"] > 1  # the dynamical term dominates
    assert not wide["warn"] and wide["ratio"] < 0.01


def test_the_amplitudes_by_hand():
    a_dyn, a_ltte = dyn.amplitudes(1.0, 30.0, m_ab=2.0, m_c=1.0)
    assert a_dyn == pytest.approx(1 / 3 / 30 / (2 * 3.141592653589793), rel=1e-9)  # 2.5 minutes
    assert a_ltte * 1440 == pytest.approx(0.756, abs=0.01)  # a₂ = 0.272 AU, a third of it over c
    ecc, _ = dyn.amplitudes(1.0, 30.0, e2=0.5)
    assert ecc == pytest.approx(a_dyn * 0.75**-1.5)


def test_a_light_time_fit_is_checked(qapp):
    from types import SimpleNamespace

    from astrowb.ui.oc_page import OCPage

    a_dyn, a_ltte = dyn.amplitudes(1.0, 30.0, 2.0, 1.0)
    fm = (a_ltte * dyn.C) ** 3 / (30.0 / 365.25) ** 2  # the mass function of a third solar mass on a 30-day orbit
    fit = SimpleNamespace(period=1.0, p3=30.0, e=0.0, omega=90.0, mass_function=fm)
    d = dyn.for_ltte_fit(fit)
    assert d["m3"] == pytest.approx(1.0, rel=1e-3) and d["warn"]
    page = OCPage.__new__(OCPage)  # only its text helper
    line = OCPage._dynamical_line(page, fit)
    assert line and "dynamical delay" in line[0]
    assert OCPage._dynamical_line(page, SimpleNamespace(period=1.0, p3=3000.0, e=0.0, omega=90.0,
                                                        mass_function=fm)) == []  # fmt: skip
