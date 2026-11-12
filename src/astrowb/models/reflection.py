"""Reflection: a star heated by its companion's light (plans/models.md MOD-4). The receiver's element of temperature
T absorbs the incident bolometric flux F and re-radiates the share A (the bolometric albedo):
T_new⁴ = T⁴ + A F / σ.

- point: the companion as a point of luminosity L at its centre, F = L cos θ / (4π d²) (fast; separations ≫ radii);
- detailed: F = Σ_j I_j(μ_j) cos θ_j cos θ / d² dA_j over the companion's elements that face the receiving element
  and that it faces (both horizons), I_j the bolometric intensity of element j with its limb darkening, normalised
  so that its emergent flux is σ T_j⁴.

Stars are the grids of models.roche_lc (one pass: the heated companion's own reflected light is not fed back).
"""

import numpy as np

from ..occult.laws import disc_flux
from ..occult.laws import intensity as limb

SIGMA = 5.670374419e-8


def incident_point(receiver, source, t_source):
    """Incident bolometric flux on every receiver element from the source as a point at its centre (W m⁻², with
    lengths in the grid's units: the factor of the separation squared cancels in T⁴ ratios)."""
    lum = SIGMA * np.sum(np.asarray(t_source, float) ** 4 * source["area"])
    d = source["centre"] - receiver["xyz"]
    dist = np.linalg.norm(d, axis=1)
    cos = np.clip(np.sum(receiver["normal"] * d, axis=1) / dist, 0, None)
    return lum * cos / (4 * np.pi * dist**2)


def incident_detailed(receiver, source, t_source, ld_bol=("linear", (0.5,))):
    """Incident flux element by element, both horizons respected."""
    law, coeffs = ld_bol
    i0 = SIGMA * np.asarray(t_source, float) ** 4 / (np.pi * disc_flux(law, coeffs))
    d = source["xyz"][None, :, :] - receiver["xyz"][:, None, :]  # receiver → source
    dist = np.linalg.norm(d, axis=2)
    cos_r = np.sum(receiver["normal"][:, None, :] * d, axis=2) / dist
    cos_s = -np.sum(source["normal"][None, :, :] * d, axis=2) / dist
    seen = (cos_r > 0) & (cos_s > 0)
    weight = np.where(seen, i0 * limb(np.clip(cos_s, 0, 1), law, coeffs) * cos_s * cos_r / dist**2, 0.0)
    return np.sum(weight * source["area"][None, :], axis=1)


def heated(t_receiver, incident, albedo=1.0):
    """The receiver's temperatures after re-radiating the share albedo of the incident flux."""
    return (np.asarray(t_receiver, float) ** 4 + albedo * np.asarray(incident) / SIGMA) ** 0.25
