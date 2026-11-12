"""MOD-4: the light a star intercepts from its companion, by a point source and element by element."""

import numpy as np
import pytest

from astrowb.models import reflection
from astrowb.models import roche_lc as lc


def pair(r1, r2, n=24):
    return lc.star(r1, 1.0, n_theta=n), lc.star(r2, 1.0, n_theta=n, second=True)


def test_a_far_sphere_intercepts_its_solid_angle_of_the_light():
    rec, src = pair(0.02, 0.1)
    t_src = np.full(len(src["area"]), 20000.0)
    lum = reflection.SIGMA * np.sum(t_src**4 * src["area"])
    for incident in (reflection.incident_point(rec, src, t_src), reflection.incident_detailed(rec, src, t_src)):
        caught = np.sum(incident * rec["area"])
        assert caught == pytest.approx(lum * np.pi * 0.02**2 / (4 * np.pi * 1.0**2), rel=0.005)


def test_re_radiated_power_with_albedo_one_equals_the_intercepted():
    rec, src = pair(0.15, 0.12)
    t_rec, t_src = np.full(len(rec["area"]), 5000.0), np.full(len(src["area"]), 20000.0)
    incident = reflection.incident_detailed(rec, src, t_src)
    t_new = reflection.heated(t_rec, incident, albedo=1.0)
    extra = reflection.SIGMA * np.sum((t_new**4 - t_rec**4) * rec["area"])
    assert extra == pytest.approx(np.sum(incident * rec["area"]), rel=1e-9)
    assert t_new.max() > 5000 and t_new[np.argmin(rec["xyz"][:, 0])] == pytest.approx(5000)  # the far side cold


def test_point_and_detailed_agree_for_small_stars():
    rec, src = pair(0.15, 0.12, n=30)  # r1 + r2 = 0.27 < 0.3
    t_src = np.full(len(src["area"]), 20000.0)
    p = np.sum(reflection.incident_point(rec, src, t_src) * rec["area"])
    d = np.sum(reflection.incident_detailed(rec, src, t_src) * rec["area"])
    assert d == pytest.approx(p, rel=0.02)
