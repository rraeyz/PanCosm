"""AAVSO Extended File Format export (differential ensemble photometry, untransformed).

Columns (in this order): NAME, DATE, MAG, MERR, FILT, TRANS, MTYPE, CNAME, CMAG, KNAME, KMAG,
AIRMASS, GROUP, CHART, NOTES; header lines #TYPE, #OBSCODE, #SOFTWARE, #DELIM, #DATE, #OBSTYPE;
unused optional fields are "na". DATE is the mid-exposure JD (UTC).

Ensemble magnitude:  m = -2.5 log10(F_target / sum F_comp) + m_ens,
m_ens = -2.5 log10(sum 10^(-0.4 m_comp,catalogue)); MERR = 1.0857 * sigma_rel / rel.
"""

import numpy as np

from .. import __version__


def ensemble_magnitudes(lc, comp_mags):
    comp_mags = np.asarray(comp_mags, float)
    if len(comp_mags) != np.asarray(lc["comp_flux"]).shape[1]:
        raise ValueError("give one catalogue magnitude per comparison star")
    rel = np.asarray(lc["rel_flux"], float)
    m_ens = -2.5 * np.log10(np.sum(10 ** (-0.4 * comp_mags)))
    mag = -2.5 * np.log10(rel) + m_ens
    merr = 2.5 / np.log(10) * np.asarray(lc["rel_flux_err"], float) / rel
    return mag, merr


def aavso_extended(
    lc, star_name, obscode, filt, comp_mags, chart="na", notes="na", software_name="", check=None, check_name=None
) -> str:
    """check: the check star's relative flux per frame (against the same ensemble); its magnitude goes into KMAG
    with check_name (its chart label) in KNAME, as the AAVSO asks for ensemble photometry."""
    if not star_name or not obscode or not filt:
        raise ValueError("star name, observer code and filter are required")
    mag, merr = ensemble_magnitudes(lc, comp_mags)
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
        if not (np.isfinite(m) and np.isfinite(e)):
            continue  # a lost star or a bad frame is not reported
        am_text = f"{am:.4f}" if isinstance(am, float) else "na"
        k = f"{check_name or 'check'},{kmag[i]:.3f}" if kmag is not None and np.isfinite(kmag[i]) else "na,na"
        lines.append(f"{star_name},{jd:.5f},{m:.3f},{e:.3f},{filt},NO,STD,ENSEMBLE,na,{k},{am_text},na,{chart},{notes}")
    return "\n".join(lines) + "\n"
