"""Light-curve files in, model files out.

read_light_curve: our own CSV export (time column first, rel_flux, rel_flux_err), AAVSO-like or plain
text tables (time, value[, error]); magnitudes are converted to relative flux.
export_for_phoebe: data files and starting values for PHOEBE 2 (or any other modelling program); the
user runs PHOEBE (GPL-3) in their own Python, nothing of it is bundled. read_model_curve brings a
computed model curve (two columns: time or phase, flux) back for comparison.
"""

import json
from pathlib import Path

import numpy as np

FLUX_NAMES = ("rel_flux", "flux", "norm_flux", "relflux")
MAG_NAMES = ("mag", "magnitude", "rel_mag", "dmag", "delta_mag")


def read_light_curve(path):
    """Return (time, flux, error or None, info) with flux normalised to a median of 1."""
    from astropy.table import Table

    tab = Table.read(path, format="ascii")
    names = [n.lower() for n in tab.colnames]
    cols = tab.colnames
    if len(cols) < 2:
        raise ValueError(f"{Path(path).name}: need at least a time and a value column")
    t = np.asarray(tab[cols[0]], float)
    vi = next((i for i, n in enumerate(names) if n in FLUX_NAMES), None)
    is_mag = False
    if vi is None:
        vi = next((i for i, n in enumerate(names) if n in MAG_NAMES), 1)
        is_mag = names[vi] in MAG_NAMES or (np.nanmedian(np.asarray(tab[cols[vi]], float)) > 3)
    v = np.asarray(tab[cols[vi]], float)
    ei = next((i for i, n in enumerate(names) if n.startswith(names[vi]) and "err" in n), None)
    if ei is None:
        ei = next((i for i, n in enumerate(names) if "err" in n or n in ("sigma", "e")), None)
    if ei is None and len(cols) > 2 and vi == 1 and names[2].startswith("col"):
        ei = 2  # plain three-column text: time value error
    e = None if ei is None else np.asarray(tab[cols[ei]], float)
    if is_mag:
        flux = 10 ** (-0.4 * (v - np.nanmedian(v)))
        err = None if e is None else flux * e * np.log(10) / 2.5
    else:
        med = np.nanmedian(v)
        flux, err = v / med, None if e is None else e / med
    ok = np.isfinite(t) & np.isfinite(flux)
    if err is not None:
        ok &= np.isfinite(err) & (err > 0)
    order = np.argsort(t[ok])
    info = {"time_column": cols[0], "value_column": cols[vi], "magnitudes": bool(is_mag)}
    return t[ok][order], flux[ok][order], None if err is None else err[ok][order], info


def export_for_phoebe(folder, t, flux, err, fit=None, rv=None, absolute=None):
    """Write lc.txt (time flux sigma), rv1.txt / rv2.txt (time rv sigma) and start.json with PHOEBE
    parameter names. Returns the list of written paths."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    sig = np.full(len(t), np.nan) if err is None else np.asarray(err, float)
    np.savetxt(folder / "lc.txt", np.column_stack([t, flux, sig]), fmt="%.7f %.6f %.6f", header="time flux sigma")
    written.append(folder / "lc.txt")
    if rv:
        for comp in ("1", "2"):
            if rv.get("v" + comp) is not None:
                e = rv.get("e" + comp)
                e = np.full(len(rv["t"]), np.nan) if e is None else np.asarray(e, float)
                path = folder / f"rv{comp}.txt"
                np.savetxt(
                    path,
                    np.column_stack([rv["t"], rv["v" + comp], e]),
                    fmt="%.7f %.4f %.4f",
                    header="time rv_km_s sigma",
                )
                written.append(path)
    start = {}
    if fit:
        p, d = fit["params"], fit["derived"]
        start |= {
            "period@binary": p["period"],
            "t0_supconj@binary": p["t0"],
            "incl@binary": p["incl"],
            "ecc@binary": d["e"],
            "per0@binary": d["omega"],
            "requiv_fraction_of_sma@primary": d["r1"],
            "requiv_fraction_of_sma@secondary": d["r2"],
            "surface_brightness_ratio": p["j"],
            "l3_frac": p["l3"],
        }
    if absolute:
        start |= {
            "sma@binary (Rsun)": absolute["a"],
            "q@binary": absolute["m2"] / absolute["m1"],
            "requiv@primary (Rsun)": absolute["r1"],
            "requiv@secondary (Rsun)": absolute["r2"],
        }
    (folder / "start.json").write_text(json.dumps(start, indent=2), encoding="utf-8")
    written.append(folder / "start.json")
    return [str(p) for p in written]


def read_model_curve(path):
    """Two columns (time or phase, flux) from a modelling program, e.g. PHOEBE's computed fluxes."""
    try:
        data = np.atleast_2d(np.genfromtxt(path, comments="#", invalid_raise=False))
    except (UnicodeDecodeError, ValueError):  # a binary file, not a table
        data = np.empty((0, 0))
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError("not a table with two columns (time or phase, flux)")
    data = data[np.isfinite(data[:, :2]).all(axis=1)]
    if not len(data):
        raise ValueError("not a table with two columns (time or phase, flux)")
    return data[:, 0], data[:, 1]
