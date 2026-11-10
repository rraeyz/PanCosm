"""PLN-9: for a stored night the suggested telluric standard stands at the target's airmass within 0.1 at the
proposed time; a pair brackets the night's airmass range; the list carries its reference."""

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time

from astrowb.planning import standards
from astrowb.planning.visibility import Site, airmass, altitudes, night_grid

SITE = Site("Ankara", 39.84, 32.78, 1250.0)


def test_telluric_standards_for_a_target():
    rows = standards.load("telluric")
    assert len(rows) > 500 and any("van Leeuwen 2007" in c for c in rows.meta["comments"])
    regulus = rows[rows["name"] == "HIP 49669"][0]  # a known bright hot star, at its known place
    assert abs(regulus["ra"] - 152.093) < 0.01 and abs(regulus["dec"] - 11.967) < 0.01
    target = SkyCoord(195.0 * u.deg, 5.0 * u.deg)
    time = Time("2026-04-15T21:00:00")
    best = standards.matching(target, time, SITE, rows)
    assert best and all(abs(b["airmass"] - b["target_airmass"]) <= 0.1 for b in best)
    first = SkyCoord(best[0]["ra"] * u.deg, best[0]["dec"] * u.deg)
    x = float(airmass(altitudes(first, time, SITE)))
    assert abs(x - float(airmass(altitudes(target, time, SITE)))) <= 0.1
    assert [b["separation"] for b in best] == sorted(b["separation"] for b in best)

    times = night_grid(SITE, "2026-04-15", step_min=20)
    times = times[(times > Time("2026-04-15T19:00")) & (times < Time("2026-04-16T02:00"))]
    xs = np.asarray(airmass(altitudes(target, times, SITE)), float)
    low, high = standards.extinction_pair(times, SITE, rows, (np.nanmin(xs), 2.0))
    assert abs(low["airmass"] - np.nanmin(xs)) <= 0.1 and abs(high["airmass"] - 2.0) <= 0.1
