"""The observation summary (plans/photometry.md PHO-27 item 4): one page for any night — the target, the night's
numbers, the light curve, the comparison stars and the timing or transit result."""

import numpy as np
from matplotlib.figure import Figure


def summary_page(path, lc, fit=None, title=""):
    t = np.asarray(lc["time"], float)
    f = np.asarray(lc["rel_flux"], float)
    n = len(t)
    comp = np.asarray(lc.get("comp_flux") or [[]], float).reshape(n, -1)
    fig = Figure(figsize=(8.27, 11.69))  # A4 portrait
    fig.suptitle(title or "Observation summary", fontsize=14, x=0.08, ha="left")
    lines = [f"Frames: {n}    Span: {(t.max() - t.min()) * 24:.2f} h    Times: {lc.get('time_scale', '')}",
             f"Start {t.min():.5f}   End {t.max():.5f}"]  # fmt: skip
    if lc.get("coord"):
        lines.append(f"Target position: {lc['coord']}")
    if lc.get("radii"):
        r = np.median(np.asarray(lc["radii"], float), axis=0)
        lines.append(f"Aperture {r[0]:.1f} px, sky annulus {r[1]:.1f}–{r[2]:.1f} px; {comp.shape[1]} comparison stars")
    if lc.get("fwhm"):
        fw = np.asarray([x for x in lc["fwhm"] if x is not None], float)
        if fw.size:
            lines.append(f"FWHM median {np.median(fw):.2f} px (from {fw.min():.2f} to {fw.max():.2f})")
    ok = np.isfinite(f)
    lines.append(f"Relative flux scatter: {np.std(f[ok] / np.median(f[ok])) * 1000:.2f} ppt")
    if fit:
        v, e, d = fit["values"], fit["errors"], fit["derived"]
        lines.append(f"Transit: Tc {v['tc']:.5f} ± {e.get('tc', float('nan')):.5f}, depth {d['depth_ppt']:.2f} ppt, "
                     f"T14 {d['t14_h']:.2f} h, reduced χ² {fit.get('chi2r', float('nan')):.2f}")  # fmt: skip
    fig.text(0.08, 0.93, "\n".join(lines), va="top", fontsize=9, family="monospace")
    ax = fig.add_axes((0.1, 0.42, 0.85, 0.32))
    x = (t - t.min()) * 24
    ax.plot(x, f / np.nanmedian(f), ".", ms=3, label="target / ensemble")
    if fit and fit.get("model") is not None and len(fit["model"]) == n:
        ax.plot(x, np.asarray(fit["model"]) / np.nanmedian(f), "-", lw=1.2, label="transit fit")
    ax.set_xlabel(f"Hours from {t.min():.5f}")
    ax.set_ylabel("Relative flux")
    ax.legend(loc="lower left", fontsize=8)
    if comp.shape[1]:
        tab = fig.add_axes((0.1, 0.05, 0.85, 0.3))
        tab.axis("off")
        med = np.nanmedian(comp, axis=0)
        rows = [[f"C{k + 1}", f"{med[k]:.0f}", f"{np.nanstd(comp[:, k] / med[k]) * 1000:.2f}"]
                for k in range(comp.shape[1])]  # fmt: skip
        tab.table(cellText=rows, colLabels=["Comparison", "Median counts", "Scatter (ppt)"], loc="upper center")
    fig.savefig(path)
    return path
