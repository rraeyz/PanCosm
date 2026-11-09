"""AAVSO Extended File Format export (differential ensemble photometry; transformed with PHO-35's coefficients).

Columns (in this order): NAME, DATE, MAG, MERR, FILT, TRANS, MTYPE, CNAME, CMAG, KNAME, KMAG,
AIRMASS, GROUP, CHART, NOTES; header lines #TYPE, #OBSCODE, #SOFTWARE, #DELIM, #DATE, #OBSTYPE;
unused optional fields are "na". DATE is the mid-exposure JD (UTC).

Ensemble magnitude:  m = -2.5 log10(F_target / sum F_comp) + m_ens,
m_ens = -2.5 log10(sum w 10^(-0.4 m_comp,catalogue)) (w: the page's ensemble weights, 1 without);
MERR = 1.0857 * sigma_rel / rel, with the scatter of the comparison stars' zero points in that frame added (their
standard deviation over sqrt(n)): the photon error alone was 0.003 mag on a real LCO night whose check star was 0.05
off.
"""

import numpy as np

from .. import __version__


def ensemble_magnitudes(lc, comp_mags):
    comp_mags = np.asarray(comp_mags, float)
    if len(comp_mags) != np.asarray(lc["comp_flux"]).shape[1]:
        raise ValueError("give one catalogue magnitude per comparison star")
    rel = np.asarray(lc["rel_flux"], float)
    w = np.ones(len(comp_mags)) if lc.get("weights") is None else np.asarray(lc["weights"], float)
    m_ens = -2.5 * np.log10(np.sum(w * 10 ** (-0.4 * comp_mags)))
    mag = -2.5 * np.log10(rel) + m_ens
    merr = 2.5 / np.log(10) * np.asarray(lc.get("rel_flux_err_scaled") or lc["rel_flux_err"], float) / rel
    if len(comp_mags) >= 2:
        with np.errstate(divide="ignore", invalid="ignore"):
            zp = comp_mags[None, :] + 2.5 * np.log10(np.asarray(lc["comp_flux"], float))
        merr = np.hypot(merr, np.nanstd(zp, axis=1, ddof=1) / np.sqrt(len(comp_mags)))
    return mag, merr


def aavso_extended(
    lc,
    star_name,
    obscode,
    filt,
    comp_mags,
    chart="na",
    notes="na",
    software_name="",
    check=None,
    check_name=None,
    transform=None,
) -> str:
    """check: the check star's relative flux per frame (against the same ensemble); its magnitude goes into KMAG
    with check_name (its chart label) in KNAME, as the AAVSO asks for ensemble photometry. transform: {"colour_c"
    (the comparison stars' colours), "colour_t" (the target's, one or per frame), "coefficient", "name" (e.g.
    Tv_bv), optional "error"}: the magnitudes in the standard system (photometry/transform.py), TRANS=YES, and the
    coefficient written in NOTES (PHO-35)."""
    if not star_name or not obscode or not filt:
        raise ValueError("star name, observer code and filter are required")
    if transform:
        from .transform import transformed

        mag, merr = transformed(lc, comp_mags, transform["colour_c"], transform["colour_t"],
                                transform["coefficient"], transform.get("error", 0.0))  # fmt: skip
        note = f"{transform.get('name', 'T')}={transform['coefficient']:.3f}"
        notes, trans = (note if notes in ("", "na") else f"{notes}|{note}"), "YES"
    else:
        mag, merr = ensemble_magnitudes(lc, comp_mags)
        trans = "NO"
    kmag = ensemble_magnitudes(lc | {"rel_flux": check, "rel_flux_err": check}, comp_mags)[0] if check else None
    airmass = lc.get("airmass") or ["na"] * len(mag)
    lines = [
        "#TYPE=Extended",
        f"#OBSCODE={obscode}",
        f"#SOFTWARE={software_name} {__version__}".strip(),
        "#DELIM=,",
        "#DATE=JD",
        "#OBSTYPE=CCD",
        "#NAME,DATE,MAG,MERR,FILT,TRANS,MTYPE,CNAME,CMAG,KNAME,KMAG,AIRMASS,GROUP,CHART,NOTES",
    ]
    for i, (jd, m, e, am) in enumerate(zip(lc["jd_utc"], mag, merr, airmass, strict=True)):
        if not (np.isfinite(m) and np.isfinite(e) and np.isfinite(jd)):
            continue  # a lost star, a bad frame or a frame without its time is not reported
        am_text = f"{am:.4f}" if isinstance(am, float) else "na"
        k = f"{check_name or 'check'},{kmag[i]:.3f}" if kmag is not None and np.isfinite(kmag[i]) else "na,na"
        lines.append(
            f"{star_name},{jd:.5f},{m:.3f},{e:.3f},{filt},{trans},STD,ENSEMBLE,na,{k},{am_text},na,{chart},{notes}"
        )
    return "\n".join(lines) + "\n"


def etd_text(lc):
    """The light curve for the Exoplanet Transit Database / VarAstro upload (plans/photometry.md item 15): the format
    its FAQ gives — "a text file, where the first column is the Julian date (full or reduced) and the second column
    is the star's brightness value (magnitude or flux)" — with the error as a third column. The full JD in the light
    curve's own time standard (chosen in the upload form: BJD_TDB, or JD_UTC without the target's position), the
    magnitude when known magnitudes were given, else Δm against the comparison ensemble. Returns (text, time scale,
    unit)."""
    from .differential import delta_mag

    if "mag" in lc:
        m, e, unit = np.asarray(lc["mag"], float), np.asarray(lc["mag_err"], float), f"{lc.get('mag_band', '')} mag"
    else:
        m, e = delta_mag(lc["rel_flux"], lc.get("rel_flux_err_scaled") or lc["rel_flux_err"])
        unit = "delta mag"
    t = np.asarray(lc["time"], float)
    ok = np.isfinite(t) & np.isfinite(m) & np.isfinite(e)
    lines = [f"{ti:.6f} {mi:.5f} {ei:.5f}" for ti, mi, ei in zip(t[ok], m[ok], e[ok], strict=True)]
    return "\n".join(lines) + "\n", lc.get("time_scale", ""), unit.strip()
