"""PHO-18: catalogue neighbours that call for "aperture after removing neighbours"."""

import numpy as np


def find(measured, catalogue, r_out, target_mag, margin=4.0, own_tol=2.0):
    """Per measured star, the catalogue stars inside its sky ring (within r_out) brighter than target_mag + margin.

    measured: [(x, y), ...]; catalogue: {"x", "y", "gmag"} lists. A catalogue star within own_tol px of the measured
    star is that star itself. Returns [{"index", "neighbours": [{"x", "y", "gmag", "distance"}]}] for the stars that
    have any (JSON-safe), nearest first."""
    cx, cy, cg = (np.asarray(catalogue[k], float) for k in ("x", "y", "gmag"))
    out = []
    for i, (x, y) in enumerate(measured):
        d = np.hypot(cx - x, cy - y)
        hit = np.flatnonzero((d > own_tol) & (d <= r_out) & (cg < target_mag + margin))
        if hit.size:
            hit = hit[np.argsort(d[hit])]
            rows = [{"x": float(cx[j]), "y": float(cy[j]), "gmag": float(cg[j]), "distance": float(d[j])} for j in hit]
            out.append({"index": i, "neighbours": rows})
    return out
