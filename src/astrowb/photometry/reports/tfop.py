"""The notes text of a TFOP SG1 observation (plans/photometry.md PHO-27 item 3), filled from the night: aperture in
pixels and arcseconds, pixel scale, FWHM, detrending, depth, mid-time, duration, whether the event was on time
against the predicted Tc, and the nearby-eclipsing-binary summary."""

import numpy as np


def notes(lc, fit=None, scale=None, predicted_tc=None, neb=None):
    lines = []
    r = np.median(np.asarray(lc["radii"], float), axis=0) if lc.get("radii") else None
    if r is not None:
        arcsec = f" ({r[0] * scale:.1f}″)" if scale else ""
        lines.append(f"Aperture radius {r[0]:.1f} px{arcsec}; sky annulus {r[1]:.1f}–{r[2]:.1f} px.")
    if scale:
        lines.append(f"Pixel scale {scale:.3f}″/px.")
    fwhm = [f for f in lc.get("fwhm") or [] if f is not None]
    if fwhm:
        f = float(np.median(fwhm))
        lines.append(f"Median FWHM {f:.2f} px" + (f" ({f * scale:.1f}″)." if scale else "."))
    lines.append(f"{len(lc['time'])} frames, times in {lc.get('time_scale', 'unknown scale')}.")
    if fit:
        v, e, d = fit["values"], fit["errors"], fit["derived"]
        trend = [k for k in v if k not in ("tc", "k", "a_rs", "b", "u1", "u2", "baseline")]
        lines.append(f"Detrending: {', '.join(trend) if trend else 'none'}.")
        lines.append(f"Depth {d['depth_ppt']:.2f} ppt; Tc {v['tc']:.5f} ± {e.get('tc', float('nan')):.5f} "
                     f"{lc.get('time_scale', '')}; T14 {d.get('t14_h', float('nan')):.2f} h.")  # fmt: skip
        if predicted_tc is not None:
            oc = (v["tc"] - predicted_tc) * 1440
            err = e.get("tc", float("nan")) * 1440
            on_time = "on time" if abs(oc) <= max(3 * err, 5.0) else "early" if oc < 0 else "late"
            lines.append(f"Against the predicted Tc: {oc:+.1f} ± {err:.1f} min ({on_time}).")
    if neb:
        cleared = sum(r["disposition"] in ("Cleared", "Likely cleared", "Cleared - too faint") for r in neb)
        lines.append(f"NEB check: {cleared} of {len(neb)} neighbours within 2.5′ cleared.")
    return "\n".join(lines) + "\n"
