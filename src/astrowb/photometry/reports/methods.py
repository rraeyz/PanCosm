"""The methods paragraph of one night's photometry for a paper, with its BibTeX (plans/architecture.md ARC-11 item
4, the photometry part): what was measured, how, and what to cite, filled from the light curve itself."""

import numpy as np

from ...core.citations import bibtex, short


def methods(lc, fit=None):
    """(paragraph in English, BibTeX text)."""
    n = len(lc["time"])
    n_comp = np.asarray(lc.get("comp_flux") or [[]], float).reshape(n, -1).shape[1] if n else 0
    r = np.median(np.asarray(lc["radii"], float), axis=0) if lc.get("radii") else None
    keys, parts = [], []
    radii = (f" with an aperture of {r[0]:.1f} px and a sky annulus from {r[1]:.1f} to {r[2]:.1f} px"
             if r is not None else "")  # fmt: skip
    parts.append(f"Differential aperture photometry of {n} frames was made{radii}, against an ensemble of {n_comp} "
                 f"comparison star{'s' if n_comp != 1 else ''}.")  # fmt: skip
    if lc.get("time_scale") == "BJD_TDB":
        keys.append("eastman2010")
        parts.append(f"Mid-exposure times were converted to BJD_TDB following {short('eastman2010')}.")
    if lc.get("scintillation"):
        parts.append(f"Flux errors include scintillation noise for a {lc.get('aperture_m') or 0:.2f} m aperture.")
    if fit:
        keys += ["mandel2002", "winn2008"]
        v, e, d = fit["values"], fit["errors"], fit["derived"]
        trend = [k for k in v if k not in ("tc", "k", "a_rs", "b", "u1", "u2", "baseline")]
        parts.append(
            f"The transit was fitted with a quadratically limb-darkened model ({short('mandel2002')})"
            + (f" times an exponential trend in {', '.join(trend)}" if trend else "")
            + f"; the mid-transit time is {v['tc']:.5f} ± {e.get('tc', float('nan')):.5f} BJD_TDB and the depth "
            f"{d['depth_ppt']:.2f} ppt. The time-correlated noise was judged by the β factor of {short('winn2008')} "
            f"(β = {fit.get('beta', float('nan')):.2f})."
        )
    return " ".join(parts), bibtex(keys) if keys else ""
