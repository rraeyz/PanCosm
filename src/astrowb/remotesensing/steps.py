"""Remote sensing as engine steps: each writes a GeoTIFF product next to the input (georeferencing kept)."""

from pathlib import Path

import numpy as np

from ..engine.steps import step
from . import analysis, raster


def _product(src, suffix, output):
    first = Path(str(src).split(";")[0])
    stem = first.parent.name if ";" in str(src) else first.stem  # bands in several files: the scene's folder
    return output or str(first.with_name(stem + f"_{suffix}.tif"))


@step("rs.expression", inputs=("raster", "expression"), outputs=("product",), optional=("output", "name"))
def expression_step(inputs, params, ctx):
    """Band math, e.g. (B8 - B4) / (B8 + B4)."""
    r = raster.load(inputs["raster"])
    ctx.progress(0.3, "band math")
    if isinstance(r, raster.Scene):  # larger than the free memory: read and evaluated by blocks of rows
        out = np.empty(r.shape, np.float32)
        for r0 in range(0, r.shape[0], 1024):
            block = r.rows(r0, r0 + 1024)
            out[r0 : r0 + 1024] = analysis.evaluate(inputs["expression"], dict(zip(r.names, block, strict=True)))
    else:
        all_bands = r.nan_bands()  # in place: a copy per band doubled the memory of a Sentinel-2 tile
        out = analysis.evaluate(inputs["expression"], {n: all_bands[i] for i, n in enumerate(r.names)})
    name = inputs.get("name") or "expr"
    path = raster.write(_product(inputs["raster"], name.lower(), inputs.get("output")), r, out)
    return {"product": {"path": path, "stats": analysis.statistics(out), "expression": inputs["expression"]}}


@step("rs.classify", inputs=("raster",), outputs=("product",), optional=("output", "bands"), k=5)
def classify_step(inputs, params, ctx):
    """Unsupervised k-means classes of the chosen bands (all bands by default)."""
    r = raster.load(inputs["raster"])
    use = inputs.get("bands") or list(range(len(r.names)))
    ctx.progress(0.3, "k-means")
    if isinstance(r, raster.Scene):  # larger than the free memory: read by rows
        bands = r if len(use) == len(r.names) else r.subset(use)
    else:
        all_bands = r.nan_bands()
        bands = all_bands if len(use) == len(r.names) else all_bands[use]
    labels = analysis.kmeans(bands, int(params["k"]))
    path = raster.write(_product(inputs["raster"], f"classes{params['k']}", inputs.get("output")), r, labels)
    return {"product": {"path": path, "stats": analysis.statistics(labels)}}


@step("rs.pca", inputs=("raster",), outputs=("product",), optional=("output",), n=3)
def pca_step(inputs, params, ctx):
    """Principal components of all bands (standardised)."""
    r = raster.load(inputs["raster"])
    n = int(min(params["n"], len(r.names)))
    comps, var = analysis.pca(r if isinstance(r, raster.Scene) else r.nan_bands(), n)  # no copy per band
    path = raster.write(_product(inputs["raster"], "pca", inputs.get("output")), r, comps)
    return {"product": {"path": path, "explained": var}}
