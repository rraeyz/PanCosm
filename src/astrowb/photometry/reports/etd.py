"""ETD / VarAstro text writer (PHO-27 item 2), moved here from photometry/export.py."""

import numpy as np


def etd_text(lc):
    """The light curve for the Exoplanet Transit Database / VarAstro upload (plans/photometry.md item 15): the format
    its FAQ gives — "a text file, where the first column is the Julian date (full or reduced) and the second column
    is the star's brightness value (magnitude or flux)" — with the error as a third column. The full JD in the light
    curve's own time standard (chosen in the upload form: BJD_TDB, or JD_UTC without the target's position), the
    magnitude when known magnitudes were given, else Δm against the comparison ensemble. Returns (text, time scale,
    unit)."""
    from ..differential import delta_mag

    if "mag" in lc:
        m, e, unit = np.asarray(lc["mag"], float), np.asarray(lc["mag_err"], float), f"{lc.get('mag_band', '')} mag"
    else:
        m, e = delta_mag(lc["rel_flux"], lc.get("rel_flux_err_scaled") or lc["rel_flux_err"])
        unit = "delta mag"
    t = np.asarray(lc["time"], float)
    ok = np.isfinite(t) & np.isfinite(m) & np.isfinite(e)
    lines = [f"{ti:.6f} {mi:.5f} {ei:.5f}" for ti, mi, ei in zip(t[ok], m[ok], e[ok], strict=True)]
    return "\n".join(lines) + "\n", lc.get("time_scale", ""), unit.strip()
