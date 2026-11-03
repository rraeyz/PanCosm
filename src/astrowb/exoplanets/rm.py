"""The Rossiter–McLaughlin anomaly (plans/exoplanets.md EXO-8), as the first moment of the light the planet hides:
ΔV = − Σ_hidden I v / Σ_visible I over a grid of the stellar disc (limb darkening of occult.laws, solid-body
rotation v = v sin i★ · x′, x′ along the stellar equator turned by the projected obliquity λ). This is the
"centroid" anomaly; the line-profile terms of Hirano et al. 2011 for cross-correlation measurements are not in it.

Sky frame: the planet moves along +X at mid-transit, Y = −b at mid-transit (circular orbit), units of R★.
"""

import numpy as np

from ..occult.laws import intensity

_N = 401
_G = np.linspace(-1, 1, _N)
_X, _Y = np.meshgrid(_G, _G)
_R2 = _X**2 + _Y**2
_DISC = _R2 < 1


def anomaly(t, period, tc, k, a_rs, inc, vsini, lam_deg, law="quadratic", coeffs=(0.4, 0.2)):
    """ΔV (the units of vsini) at times t."""
    phase = 2 * np.pi * (np.asarray(t, float) - tc) / period
    x_p = a_rs * np.sin(phase)
    y_p = -a_rs * np.cos(np.radians(inc)) * np.cos(phase)
    front = np.cos(phase) > 0
    mu = np.sqrt(np.clip(1 - _R2, 0, 1))
    i_map = np.where(_DISC, intensity(mu, law, coeffs), 0.0)
    lam = np.radians(lam_deg)
    v_map = vsini * (_X * np.cos(lam) + _Y * np.sin(lam))
    total = i_map.sum()
    out = np.zeros(len(phase))
    for j, (x, y, f) in enumerate(zip(x_p, y_p, front, strict=True)):
        if not f or np.hypot(x, y) > 1 + k:
            continue
        hidden = ((_X - x) ** 2 + (_Y - y) ** 2 < k * k) & _DISC
        lost = i_map[hidden].sum()
        out[j] = -(i_map[hidden] * v_map[hidden]).sum() / (total - lost)
    return out
