"""Several filters in one night (plans/photometry.md item 11): a mixed B / V / R … sequence measured as one run, a
light curve per filter, and the colour-index curve between two filters — the differential colour Δ(a − b) of the
target against the comparison ensemble, and with a colour transformation coefficient (photometry.coefficients: T_ab
of (A − B) = T_ab (a − b) + Z_ab) and the comparison stars' catalogue colour, the target's standard colour."""

import numpy as np

from .differential import delta_mag

# the order colour indices are usually formed in (blue minus red)
ORDER = ("U", "B", "SG", "TB", "CB", "V", "G", "TG", "CV", "R", "SR", "TR", "CR", "I", "SI")


def by_filter(paths):
    """{filter name: paths} in the order met (FILTER keyword; "" when there is none)."""
    from astropy.io import fits

    from ..io.lzw import readable

    groups = {}
    for p in paths:
        groups.setdefault(str(fits.getheader(readable(p)).get("FILTER", "") or "").strip(), []).append(p)
    return groups


def colour_pair(filters):
    """The two filters to form the colour from, bluer first (B − V rather than V − B), else in the order given."""
    known = sorted((f for f in filters if f.upper() in ORDER), key=lambda f: ORDER.index(f.upper()))
    rest = [f for f in filters if f not in known]
    pair = (known + rest)[:2]
    if len(pair) < 2:
        raise ValueError("a colour needs images in two filters")
    return tuple(pair)


def colour_curve(lc_a, lc_b, max_gap=None, t_ab=None, comp_colour=None):
    """The colour-index curve: each point of the sparser curve with the nearest point of the other within max_gap
    days (default 1.5 times the larger median cadence), Δm_a − Δm_b against the mean time. With t_ab and the
    comparison ensemble's catalogue colour (A − B), also the target's standard colour
    (A − B) = comp_colour + t_ab Δ(a − b) — the zero points cancel in a differential colour. Returns {"time",
    "colour", "colour_err", "standard" or None, "filters", "pairs"}."""
    ta, tb = np.asarray(lc_a["time"], float), np.asarray(lc_b["time"], float)
    ma, ea = delta_mag(lc_a["rel_flux"], lc_a["rel_flux_err"])
    mb, eb = delta_mag(lc_b["rel_flux"], lc_b["rel_flux_err"])
    if max_gap is None:
        cad = [np.median(np.diff(np.sort(t))) for t in (ta, tb) if len(t) > 1]
        max_gap = 1.5 * max(cad) if cad else np.inf
    swap = len(ta) > len(tb)  # walk the sparser curve
    t1, m1, e1, t2, m2, e2 = (tb, mb, eb, ta, ma, ea) if swap else (ta, ma, ea, tb, mb, eb)
    order = np.argsort(t2)
    t2s = t2[order]
    rows = []
    for t, m, e in zip(t1, m1, e1, strict=True):
        j = int(np.clip(np.searchsorted(t2s, t), 1, len(t2s) - 1)) if len(t2s) > 1 else 0
        k = order[min((j - 1, j) if len(t2s) > 1 else (0,), key=lambda q: abs(t2s[q] - t))]
        if abs(t2[k] - t) <= max_gap and np.isfinite(m) and np.isfinite(m2[k]):
            ma_, mb_ = (m2[k], m) if swap else (m, m2[k])
            rows.append(((t + t2[k]) / 2, ma_ - mb_, float(np.hypot(e, e2[k]))))
    if not rows:
        raise ValueError("no two images of the two filters close enough in time to form a colour")
    t, c, ce = (np.array(x) for x in zip(*rows, strict=True))
    standard = None
    if t_ab is not None and comp_colour is not None:
        standard = (comp_colour + t_ab * c).tolist()
    return {"time": t.tolist(), "colour": c.tolist(), "colour_err": ce.tolist(), "standard": standard,
            "filters": [lc_a.get("filter"), lc_b.get("filter")], "pairs": len(rows)}  # fmt: skip
