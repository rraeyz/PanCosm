"""Mean stellar density of a transiting planet's host from the fitted a/R★ and the period (UI-16.7).

ρ★ = 3π (a/R★)³ / (G P²), Seager & Mallén-Ornelas 2003, ApJ 585, 1038, eq. 30, neglecting the planet's mass
(exoplanets.derived.density_from_a). The error is the scatter of ρ★ over the MCMC draws of a/R★ when the fit kept
them, else first-order propagation of the a/R★ and P errors (independent)."""

import numpy as np
from astropy import constants as c

from ..exoplanets.derived import density_from_a

RHO_SUN = float(c.M_sun.value / (4 / 3 * np.pi * c.R_sun.value**3) / 1000.0)  # g cm⁻³


def stellar_density(out, period, period_err=0.0):
    """out: a transit_fit result; period in days. {"rho", "err"} in g/cm³ and {"rho_sun", "err_sun"} in ρ☉."""
    a, ea = out["values"]["a_rs"], out["errors"].get("a_rs", 0.0)
    m = out.get("mcmc")
    if m and "a_rs" in m.get("names", ()):
        draws = np.asarray(m["chains"])[:, :, m["names"].index("a_rs")].ravel()
        err = float(np.std(density_from_a(draws, period)))
    else:
        err = float(density_from_a(a, period) * np.hypot(3 * ea / a, 2 * period_err / period))
    rho = float(density_from_a(a, period))
    return {"rho": rho, "err": err, "rho_sun": rho / RHO_SUN, "err_sun": err / RHO_SUN}
