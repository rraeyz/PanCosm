"""The ExoClock upload file from a measured light curve (plans/photometry.md PHO-27): three columns, time BJD_TDB,
flux normalised to the out-of-transit level (divided by the fitted trend when there is a transit fit), its error;
comment lines start with '#'. `form` is the text of the observation form's values to paste."""

import numpy as np


def write(lc, path, fit=None):
    if lc.get("time_scale") != "BJD_TDB":
        raise ValueError("ExoClock needs BJD_TDB times: give the target's position when measuring")
    t = np.asarray(lc["time"], float)
    f, e = np.asarray(lc["rel_flux"], float), np.asarray(lc.get("rel_flux_err_scaled") or lc["rel_flux_err"], float)
    ok = np.isfinite(t) & np.isfinite(f) & np.isfinite(e)
    if fit and fit.get("trend") is not None and len(fit["trend"]) == len(t):
        norm = np.asarray(fit["trend"], float)  # the baseline times the detrending the fit found
    else:
        norm = np.nanmedian(f[ok])
    f, e = f / norm, e / norm
    head = (
        "time BJD_TDB, flux (normalised"
        + (", detrended by the fit" if fit and fit.get("trend") is not None else "")
        + "), flux error"
    )
    np.savetxt(path, np.column_stack([t[ok], f[ok], e[ok]]), fmt="%.6f %.6f %.6f", header=head)
    return path


def validate(path):
    """Problems found re-reading the file: [] when it is a valid upload."""
    problems = []
    rows = [line.split() for line in open(path, encoding="utf-8") if line.strip() and not line.startswith("#")]
    if not rows:
        return ["no data rows"]
    for i, r in enumerate(rows, 1):
        if len(r) != 3:
            problems.append(f"row {i}: {len(r)} columns, 3 expected")
            continue
        t, f, e = (float(x) for x in r)
        if not 2400000 < t < 2500000:
            problems.append(f"row {i}: time {t} is not a BJD")
        if not (0 < f < 2 and e > 0):
            problems.append(f"row {i}: flux {f} or error {e} out of range")
    times = [float(r[0]) for r in rows if len(r) == 3]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        problems.append("times are not increasing")
    return problems


def form(lc, fit=None, exptime=None, filter_name=None):
    """The observation form's values, one per line, to paste."""
    t = np.asarray(lc["time"], float)
    lines = [f"Observation start (BJD_TDB): {t.min():.5f}", f"Observation end (BJD_TDB): {t.max():.5f}",
             f"Number of points: {len(t)}"]  # fmt: skip
    if exptime:
        lines.append(f"Exposure time (s): {exptime:g}")
    if filter_name:
        lines.append(f"Filter: {filter_name}")
    if fit:
        v, e = fit["values"], fit["errors"]
        lines += [f"Mid-transit time (BJD_TDB): {v['tc']:.5f} ± {e.get('tc', float('nan')):.5f}",
                  f"Depth (ppt): {fit['derived']['depth_ppt']:.2f}"]  # fmt: skip
    return "\n".join(lines)
