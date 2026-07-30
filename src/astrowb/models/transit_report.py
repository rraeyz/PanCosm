"""Transit observations in the forms the transit databases take: the Exoplanet Transit Database (ETD:
BJD, magnitude, error) and ExoClock (BJD_TDB, relative flux, error; the observation details are entered in
its upload form), plus a summary of the fitted transit (mid-time of this transit, depth, duration, Rp/R*,
a/R*, inclination). The times must already be BJD_TDB (the light curves of the application are).
"""

from pathlib import Path

import numpy as np


def summary(t, fit, model_fn):
    """Mid-time of the transit covered by t (epoch nearest to the data) with its error, depth, total duration
    T14 (days), Rp/R*, a/R* and inclination. model_fn(times) gives the fitted model."""
    p, e, d = fit["params"], fit["errors"], fit["derived"]
    epoch = int(np.round((np.mean(t) - p["t0"]) / p["period"]))
    tc = p["t0"] + epoch * p["period"]
    tc_err = float(np.hypot(e.get("t0", 0.0) or 0.0, epoch * (e.get("period", 0.0) or 0.0)))
    window = np.linspace(tc - 0.25 * p["period"], tc + 0.25 * p["period"], 20001)
    m = model_fn(window)
    inside = window[m < 1 - 1e-6 * (1 - m.min())] if m.min() < 1 else window[:0]
    return {
        "epoch": epoch,
        "tc": float(tc),
        "tc_err": tc_err,
        "depth": float(1 - m.min()),
        "t14": float(np.ptp(inside)) if inside.size else 0.0,
        "rp_rs": float(p["k"]),
        "a_rs": float(1 / d["r1"]) if d.get("r1") else None,
        "incl": float(p["incl"]),
        "period": float(p["period"]),
    }


def write(folder, t, flux, err, fit, model_fn, name="transit"):
    """ETD and ExoClock upload files and a summary in folder; returns the paths written."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    t = np.asarray(t, float)
    f = np.asarray(flux, float) / fit.get("scale", 1.0)
    e = np.full(t.size, np.nan) if err is None else np.asarray(err, float) / fit.get("scale", 1.0)
    s = summary(t, fit, model_fn)
    head = (
        f"Tc = {s['tc']:.6f} +- {s['tc_err']:.6f} BJD_TDB (epoch {s['epoch']} from T0 = {fit['params']['t0']:.6f}, "
        f"P = {s['period']:.8f} d); depth {s['depth']:.5f}; T14 {s['t14'] * 24:.3f} h"
    )
    etd = folder / f"{name}_ETD.txt"
    np.savetxt(
        etd,
        np.column_stack([t, -2.5 * np.log10(f), 1.0857 * e / f]),
        fmt="%.6f %.5f %.5f",
        header=f"ETD upload: BJD_TDB, magnitude (relative), error\n{head}",
    )
    exo = folder / f"{name}_ExoClock.txt"
    np.savetxt(
        exo,
        np.column_stack([t, f, e]),
        fmt="%.6f %.6f %.6f",
        header=f"ExoClock upload: time BJD_TDB, flux relative (detrended), flux error\n{head}",
    )
    summ = folder / f"{name}_summary.txt"
    lines = [
        f"Mid-transit time Tc    {s['tc']:.6f} +- {s['tc_err']:.6f} BJD_TDB (epoch {s['epoch']})",
        f"Depth                  {s['depth']:.5f}  ({s['depth'] * 1000:.2f} ppt)",
        f"Total duration T14     {s['t14'] * 24:.3f} h",
        f"Rp/R*                  {s['rp_rs']:.4f}",
        f"a/R*                   {s['a_rs']:.3f}" if s["a_rs"] else "a/R*                   -",
        f"Inclination            {s['incl']:.2f} deg",
        f"Residual rms           {fit.get('rms', float('nan')):.5f}  ({fit.get('n', len(t))} points)",
    ]
    summ.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [str(etd), str(exo), str(summ)], s
