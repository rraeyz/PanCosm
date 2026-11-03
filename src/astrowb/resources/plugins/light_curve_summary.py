"""Example plugin: a short summary of a light-curve CSV file (as written by the Photometry page).

Input: the CSV file. Result: number of points, time span, mean relative flux, scatter in millimagnitudes and
the deepest point. A template for any tool that reads a table and returns numbers.
"""

from astrowb.engine.steps import step


@step("plugin.light_curve_summary", inputs=("csv_file",), outputs=("summary",))
def light_curve_summary(inputs, params, ctx):
    """Points, time span, scatter (mmag) and the deepest point of a light-curve CSV."""
    import numpy as np
    from astropy.table import Table

    t = Table.read(inputs["csv_file"], format="ascii.csv")
    time = np.asarray(t[t.colnames[0]], float)
    name = "rel_flux" if "rel_flux" in t.colnames else t.colnames[1]
    flux = np.asarray(t[name], float)
    ok = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[ok], flux[ok]
    return {
        "summary": {
            "points": int(time.size),
            "span_hours": float(np.ptp(time) * 24),
            "mean_flux": float(np.mean(flux)),
            "scatter_mmag": float(1085.7 * np.std(flux) / np.mean(flux)),
            "deepest_time": float(time[np.argmin(flux)]),
        }
    }
