"""The light curve as a CSV file."""

import numpy as np


def export_csv(lc, path):
    """Light curve table as CSV (time, relative flux, error, raw fluxes)."""
    from astropy.table import Table

    t = Table(
        {
            lc["time_scale"]: lc["time"],
            "rel_flux": lc["rel_flux"],
            "rel_flux_err": lc["rel_flux_err"],
            "target_flux": lc["target_flux"],
            "file": lc["file"],
        }
    )
    for i, col in enumerate(np.asarray(lc["comp_flux"]).T):
        t[f"comp{i + 1}_flux"] = col
    if lc.get("hjd_utc") is not None and lc["time_scale"] != "HJD_UTC":
        t["HJD_UTC"] = lc["hjd_utc"]  # for O−C tables in HJD (item 14)
    if "airmass" in lc:
        t["airmass"] = lc["airmass"]
    from ..photometry.differential import delta_mag

    t["delta_mag"], t["delta_mag_err"] = delta_mag(lc["rel_flux"], lc["rel_flux_err"])
    if "mag" in lc:  # magnitudes from known (typed-in or catalogue) comparison magnitudes
        t[f"{lc['mag_band']}_mag"], t[f"{lc['mag_band']}_mag_err"] = lc["mag"], lc["mag_err"]
    for x in lc.get("extra") or []:  # check stars and further targets against the same ensemble
        t[f"{x['name']}_rel_flux"], t[f"{x['name']}_rel_flux_err"] = x["rel_flux"], x["rel_flux_err"]
        if "mag" in x:
            t[f"{x['name']}_mag"], t[f"{x['name']}_mag_err"] = x["mag"], x["mag_err"]
    if lc.get("fwhm"):
        t["fwhm"] = lc["fwhm"]
    t.write(path, format="csv", overwrite=True)
    return path
