"""Save all (plans/photometry.md PHO-27 item 5, as AstroImageJ's): everything one night's photometry made, into one
folder — the light curve whole (ECSV, PHO-48), the measurements table (CSV, AstroImageJ's columns), the star list,
the transit fit's numbers, the plot. Returns the files written."""

import csv
import json
from pathlib import Path

import numpy as np

from .. import lcfile
from ..measurements import measurements
from ..starlist import save_star_list


def save_all(folder, lc, stars=None, fit=None, figure=None, provenance=None, aavso=None):
    """stars: {"target", "comps", "extras", "radii", "wcs"} (starlist.save_star_list); fit: the transit fit's dict;
    aavso: the AAVSO exoplanet header values (OBSCODE, STAR_NAME, FILTER, …): the file is written when they suffice."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = [lcfile.write(lc, folder / "light_curve.lc.ecsv", provenance)]
    cols, _flags = measurements(lc)
    path = folder / "measurements.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(cols))
        w.writerows(zip(*cols.values(), strict=True))
    out.append(path)
    if stars and stars.get("target") is not None:
        out.append(Path(save_star_list(folder / "stars.json", stars["target"], stars.get("comps", ()),
                                       stars.get("extras", ()), stars.get("radii"), stars.get("wcs"))))  # fmt: skip
    if fit:
        keep = {k: fit[k] for k in ("values", "errors", "derived", "chi2", "chi2r", "bic", "dof", "rms_ppt", "beta")
                if k in fit}  # fmt: skip
        path = folder / "transit_fit.json"
        path.write_text(json.dumps(keep, indent=1, default=_plain), encoding="utf-8")
        out.append(path)
    if lc.get("time_scale") == "BJD_TDB":  # the ExoClock upload and the form's values to paste
        from . import exoclock

        out.append(exoclock.write(lc, folder / "ExoClock.txt", fit))
        (folder / "ExoClock_form.txt").write_text(exoclock.form(lc, fit) + "\n", encoding="utf-8")
        out.append(folder / "ExoClock_form.txt")
    if lc.get("time_scale") == "BJD_TDB" and aavso:  # the AAVSO Exoplanet Database file, normalised flux
        from . import aavso_exoplanet

        f, e = np.asarray(lc["rel_flux"], float), np.asarray(lc.get("rel_flux_err_scaled") or lc["rel_flux_err"], float)
        m = np.nanmedian(f)
        from ... import __version__
        from ...brand import BRAND

        header = {"SOFTWARE": f"{BRAND.display_name} {__version__}", "OBSTYPE": "CCD", "MEASUREMENT_TYPE": "Rnflux"}
        header |= aavso
        try:
            out.append(aavso_exoplanet.write(folder / "AAVSO_exoplanet.txt", lc["time"], f / m, e / m, header))
        except ValueError:  # a required value is missing (observer code, star, filter): the other files still go
            pass
    from .methods import methods
    from .summary import summary_page

    out.append(Path(summary_page(folder / "summary.pdf", lc, fit)))

    text, bib = methods(lc, fit)  # the paragraph for a paper and what it cites
    (folder / "methods.txt").write_text(text + "\n", encoding="utf-8")
    out.append(folder / "methods.txt")
    if bib:
        (folder / "references.bib").write_text(bib, encoding="utf-8")
        out.append(folder / "references.bib")
    if figure is not None:
        for ext in ("png", "pdf"):
            figure.savefig(folder / f"light_curve.{ext}", dpi=200)
            out.append(folder / f"light_curve.{ext}")
    return [Path(p) for p in out]


def _plain(x):
    return x.item() if isinstance(x, np.generic) else str(x)
