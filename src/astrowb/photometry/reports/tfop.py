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


def tfop_files(folder, lc, fit, stars, neb, image):
    """Save all's TFOP pieces (PHO-27 item 3): field.png and seeing_profile.png from the marked frame, notes.txt,
    NEB_check.csv after the nearby-eclipsing-binary check."""
    import csv
    from pathlib import Path

    out = []
    if image is not None and stars and stars.get("target") is not None:
        from .field_image import seeing_profile
        from .field_image import write as field_png

        r_ap = (stars.get("radii") or (5,))[0]
        path = field_png(folder / "field.png", image, stars["target"], stars.get("comps", ()), r_ap,
                         stars.get("scale"), stars.get("extras", ()))  # fmt: skip
        out.append(Path(path))
        if stars.get("radii"):
            out.append(Path(seeing_profile(folder / "seeing_profile.png", image, stars["target"], stars["radii"])))
    st = stars or {}
    (folder / "notes.txt").write_text(notes(lc, fit, st.get("scale"), st.get("predicted_tc"), neb), encoding="utf-8")
    out.append(folder / "notes.txt")
    if neb:
        path = folder / "NEB_check.csv"
        cols = ("disposition", "gmag", "separation", "dmag", "required_ppt", "rms_ppt", "ratio", "x", "y")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows([r[c] for c in cols] for r in neb)
        out.append(path)
    return [Path(p) for p in out]
