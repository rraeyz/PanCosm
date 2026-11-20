"""The nearby-eclipsing-binary check's plots (plans/photometry.md PHO-23 item 3): one light curve per neighbour with
the depth its eclipse would need drawn, the Δmag-vs-RMS summary, and the field with every neighbour labelled and
coloured by disposition. Rows are neb.run's."""

import numpy as np

from ..neb import BUFFER, required_depth_ppt

COLOURS = {"Cleared": "tab:green", "Likely cleared": "yellowgreen", "Cleared - too faint": "tab:gray",
           "Not cleared": "tab:red", "Not cleared - flux too low": "tab:orange"}  # fmt: skip


def _figure(figsize=(7, 4)):
    import matplotlib

    matplotlib.use("Agg", force=False)
    from matplotlib.figure import Figure

    return Figure(figsize=figsize, layout="constrained")


def write(folder, rows, image=None, target=None):
    """Writes into folder: star_NN.png for each row that carries its time and flux, dmag_vs_rms.png and, with the
    frame and the target's pixel position, field_neb.png; returns the paths."""
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for k, r in enumerate(rows, 1):
        if "flux" not in r:
            continue
        t = np.asarray(r["time"], float)
        fig = _figure()
        ax = fig.add_subplot()
        ax.plot(t - t.min(), r["flux"], ".", ms=3)
        ax.axhline(1 - r["required_ppt"] / 1000, color="tab:red", ls="--", label="depth needed")
        if r.get("window"):
            ax.axvspan(min(r["window"]) - t.min(), max(r["window"]) - t.min(), color="gray", alpha=0.2)
        close = r.get("close")
        ax.set_title(
            f"{r['name']}: {r['disposition']}" + (f"\nwithin 10″: {', '.join(close)}" if close else ""), fontsize=9
        )
        ax.set_xlabel(f"Days from {t.min():.5f}")
        ax.set_ylabel("Relative flux")
        ax.legend(fontsize=8)
        out.append(_save(fig, folder / f"star_{k:02d}.png"))
    fig = _figure()
    ax = fig.add_subplot()
    for d, c in COLOURS.items():
        sel = [r for r in rows if r["disposition"] == d]
        ax.plot([r["dmag"] for r in sel], [r["rms_ppt"] for r in sel], "o", color=c, label=d)
    if rows:  # the boundaries: RMS at which required depth / RMS is 5 (cleared) and 3 (likely cleared); the target's
        # depth comes back from any row (required = depth / 10^(−(Δmag − 0.5) / 2.5))
        r0 = rows[0]
        depth = r0["required_ppt"] * 10 ** (-(r0["dmag"] - BUFFER) / 2.5)
        dm = np.linspace(min(r["dmag"] for r in rows) - 0.5, max(r["dmag"] for r in rows) + 0.5, 50)
        for ratio, style in ((5, "-"), (3, ":")):
            ax.plot(
                dm, required_depth_ppt(depth, dm) / ratio, style, color="gray", label=f"depth needed / RMS = {ratio}"
            )
    ax.set_yscale("log")
    ax.set_xlabel("Δmag to the target")
    ax.set_ylabel("RMS (ppt)")
    ax.legend(fontsize=8)
    out.append(_save(fig, folder / "dmag_vs_rms.png"))
    if image is not None and target is not None:
        out.append(_field(folder / "field_neb.png", rows, image, target))
    return out


def _field(path, rows, image, target):
    from astropy.visualization import ZScaleInterval
    from matplotlib.colors import Normalize

    data = np.asarray(image, float)
    fig = _figure((7, 7 * data.shape[0] / max(data.shape[1], 1)))
    ax = fig.add_subplot()
    lo, hi = ZScaleInterval().get_limits(data)
    if not lo < hi:  # a noiseless frame: the whole range
        lo, hi = float(np.nanmin(data)), float(np.nanmax(data)) + 1e-9
    ax.imshow(data, origin="lower", cmap="gray_r", norm=Normalize(lo, hi, clip=True))
    ax.plot(*target, "+", color="tab:blue", ms=12)
    for k, r in enumerate(rows, 1):
        ax.plot(r["x"], r["y"], "o", mfc="none", color=COLOURS[r["disposition"]], ms=12)
        crowded = r.get("nearest_px", np.inf) <= 3 * r.get(
            "r_ap", 0
        )  # the macro's red label: a neighbour within 3 radii
        ax.annotate(str(k), (r["x"], r["y"]), xytext=(8, 8), textcoords="offset points", fontsize=8,
                    color="red" if crowded else COLOURS[r["disposition"]])  # fmt: skip
    ax.set_xlabel("x (px)")
    ax.set_ylabel("y (px)")
    return _save(fig, path)


def _save(fig, path):
    fig.savefig(path, dpi=150)
    return path
