"""OC-9: Völschow et al. 2016's worked systems (their tables 1, 2 and 4) reproduced."""

import pytest

from astrowb.timeseries import applegate as ag

# name: (a/R☉, P/d, M, R, T, L, K/s, P_mod/yr, ΔP/P printed, E_sec/erg, Tian, two-zone)
SYSTEMS = {
    "HW Vir": (0.860, 0.117, 0.142, 0.175, 3084, 0.003, 563, 55, 4.1e-6, 2.0e40, 6.0, 108),
    "NN Ser": (0.934, 0.130, 0.111, 0.149, 2920, 0.00147, 27.65, 15.482, 7.1e-7, 2.7e39, 3.3, 64),
    "QS Vir": (1.27, 0.151, 0.43, 0.42, 3100, 0.0146, 43, 16.99, 1e-6, 3.0e40, 0.040, 0.71),
    "UZ For": (0.788, 0.0879, 0.14, 0.177, 2950, 0.00213, 21.6, 16, 5.4e-7, 4.1e39, 0.15, 2.7),
    "V471 Tau": (3.3, 0.522, 0.93, 0.96, 5040, 0.40, 137.2, 30.5, 1.8e-6, 2.0e42, 0.014, 0.26),
    "BX Dra": (4.06, 0.579, 2.08, 2.13, 6980, 9.66, 532, 30.2, 3.5e-6, 3.5e43, 0.00016, 0.0029),
}


@pytest.mark.parametrize("name", SYSTEMS)
def test_the_published_systems(name):
    a, p, m, r, t, lum, k, pmod, dpp, esec, tian, two = SYSTEMS[name]
    # the paper's tables disagree with themselves twice: BX Dra's ΔP/P is half of 4π K / P_mod, and V471 Tau's
    # E_sec is not P_mod L (1.5e42 erg); the energies follow from the printed ΔP/P and match
    if name != "BX Dra":
        assert ag.dp_over_p(k, pmod) == pytest.approx(dpp, rel=0.06)  # the table prints two digits
    got = ag.energy(m, r, t, lum, a, p, dpp, pmod)
    if name != "V471 Tau":
        assert got["E_sec"] == pytest.approx(esec, rel=0.05)
    assert got["tian"] == pytest.approx(tian, rel=0.05)
    assert got["two_zone"] * got["E_sec"] / esec == pytest.approx(two, rel=0.05)  # over their E_sec
    assert got["feasible"] == (two < 1)


def test_giants_without_a_solution():
    """AW Her and HR 1099: the Applegate parameter above 1, no two-zone energy (their table's dashes), Tian's
    estimate as printed. (RU Cnc and SZ Psc are left out: their table 4 rows do not follow from their table 1.)"""
    for args, tian in (((1.35, 3.0, 5110, 5.49, 24.86, 8.82, 4.4e-5, 12.8), 618), ((1.3, 4.0, 4940, 8.6, 11.2, 2.84,
                                                                                       9e-5, 35), 0.22)):  # fmt: skip
        got = ag.energy(*args)
        assert got["A"] > 1 and got["two_zone"] is None and not got["feasible"]
        assert got["tian"] == pytest.approx(tian, rel=0.06)
