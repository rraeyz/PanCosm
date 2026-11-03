"""Remote sensing as engine steps: each writes a GeoTIFF product next to the input (georeferencing kept)."""

from pathlib import Path

from ..engine.steps import step
from . import analysis, raster


def _product(src, suffix, output):
    return output or str(Path(src).with_name(Path(src).stem + f"_{suffix}.tif"))


@step("rs.expression", inputs=("raster", "expression"), outputs=("product",), optional=("output", "name"))
def expression_step(inputs, params, ctx):
    """Band math, e.g. (B8 - B4) / (B8 + B4)."""
    r = raster.read(inputs["raster"])
    bands = {n: r.band(i) for i, n in enumerate(r.names)}
    ctx.progress(0.3, "band math")
    out = analysis.evaluate(inputs["expression"], bands)
    name = inputs.get("name") or "expr"
    path = raster.write(_product(inputs["raster"], name.lower(), inputs.get("output")), r, out)
    return {"product": {"path": path, "stats": analysis.statistics(out), "expression": inputs["expression"]}}


@step("rs.classify", inputs=("raster",), outputs=("product",), optional=("output", "bands"), k=5)
def classify_step(inputs, params, ctx):
    """Unsupervised k-means classes of the chosen bands (all bands by default)."""
    r = raster.read(inputs["raster"])
    use = inputs.get("bands") or list(range(len(r.names)))
    ctx.progress(0.3, "k-means")
    labels = analysis.kmeans([r.band(i) for i in use], int(params["k"]))
    path = raster.write(_product(inputs["raster"], f"classes{params['k']}", inputs.get("output")), r, labels)
    return {"product": {"path": path, "stats": analysis.statistics(labels)}}


@step("rs.pca", inputs=("raster",), outputs=("product",), optional=("output",), n=3)
def pca_step(inputs, params, ctx):
    """Principal components of all bands (standardised)."""
    r = raster.read(inputs["raster"])
    n = int(min(params["n"], len(r.names)))
    comps, var = analysis.pca([r.band(i) for i in range(len(r.names))], n)
    path = raster.write(_product(inputs["raster"], "pca", inputs.get("output")), r, comps)
    return {"product": {"path": path, "explained": var}}
