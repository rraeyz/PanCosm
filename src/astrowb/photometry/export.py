"""The ensemble magnitude behind the AAVSO Extended file (reports/aavso_extended.py).

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
