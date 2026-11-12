"""EXO-4: derived quantities against cases worked by hand from their papers' equations."""

import numpy as np
import pytest

from astrowb.exoplanets import derived as d

A_EARTH = d.AU / d.R_SUN  # a/R☉ of the Earth: 215.03


def test_constants_are_the_iau_2015_nominal_values():
    assert d.R_SUN == 6.957e8 and d.R_JUP == 7.1492e7 and d.R_EARTH == 6.3781e6
    assert d.S_EARTH == 1361.0


def test_the_sun_from_the_earth_orbit():
    assert d.density_from_a(A_EARTH, 365.25636) == pytest.approx(1.41, abs=0.01)  # the Sun's mean density
    assert d.a_from_density(1.41, 365.25636) == pytest.approx(A_EARTH, rel=0.003)
    assert d.equilibrium_temperature(5772, A_EARTH, albedo=0.3) == pytest.approx(255, abs=1)
    s, earths = d.incident_flux(5772, A_EARTH)
    assert earths == pytest.approx(1.0, abs=0.005)


def test_a_hot_jupiters_geometry():
    """P = 3 d, a/R★ = 8, i = 86°, k = 0.1 (Winn 2010 eqs. 7, 14, 15, 9 by hand)."""
    b = 8 * np.cos(np.radians(86))
    assert d.impact_parameter(8, 86) == pytest.approx(b)
    t14 = 3 / np.pi * np.arcsin(np.sqrt(1.1**2 - b * b) / (8 * np.sin(np.radians(86))))
    t23 = 3 / np.pi * np.arcsin(np.sqrt(0.9**2 - b * b) / (8 * np.sin(np.radians(86))))
    assert d.t14(3, 8, 86, 0.1) == pytest.approx(t14) and d.t23(3, 8, 86, 0.1) == pytest.approx(t23)
    assert d.transit_probability(8, 0.1) == pytest.approx(1.1 / 8)
    # eccentric: the transit is shorter when the planet passes near periastron (ω = 90°)
    b_e = b * 0.96 / 1.2  # b shrinks by (1 − e²)/(1 + e sin ω)
    t14_e = 3 / np.pi * np.arcsin(np.sqrt(1.1**2 - b_e**2) / (8 * np.sin(np.radians(86)))) * np.sqrt(0.96) / 1.2
    assert d.t14(3, 8, 86, 0.1, e=0.2, w=90) == pytest.approx(t14_e) and t14_e < t14
    assert d.impact_parameter(8, 86, 0.2, 90, occultation=True) > d.impact_parameter(8, 86, 0.2, 90)


def test_jupiter_mass_and_gravity_from_the_suns_velocity():
    """The Sun moves at 12.5 m/s around the Sun–Jupiter barycentre over 4332.6 d: 1 M_J; Jupiter's gravity."""
    assert d.planet_mass(0.01247, 4332.59, 1.0, e=0.0489) == pytest.approx(1.0, rel=0.01)
    a = 778.5e9  # m
    g = d.surface_gravity(0.01247, 4332.59, d.R_JUP / a, 90.0, e=0.0489)
    assert g == pytest.approx(24.8, rel=0.03)


def test_safronov_and_tsm():
    assert d.safronov(8.0, 0.1, 1.0, 1.0) == pytest.approx(80 * d.M_JUP / d.M_SUN)
    # Kempton et al. 2018 eq. 1 for a 2 R⊕, 5 M⊕, 500 K planet of a 0.5 R☉ star with J = 9
    assert d.tsm(2.0, 5.0, 500.0, 0.5, 9.0) == pytest.approx(1.26 * 8 * 500 / (5 * 0.25) * 10 ** (-9 / 5))
