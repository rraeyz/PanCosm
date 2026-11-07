"""Band math, spectral indices, statistics, unsupervised classification, PCA, change detection.

Band-math expressions are parsed with Python's ast module and evaluated on numpy arrays; only
numbers, band names, + - * / ** , unary minus, parentheses, comparisons and a short list of
functions are accepted, so a typed expression can never run other code.
"""

import ast
import operator

import numpy as np

# common indices; band roles are mapped to band names by the user (e.g. NIR -> B8 for Sentinel-2)
INDICES = {
    "NDVI": ("(NIR - RED) / (NIR + RED)", "Normalised difference vegetation index (Rouse et al. 1974)"),
    "NDWI": ("(GREEN - NIR) / (GREEN + NIR)", "Normalised difference water index (McFeeters 1996)"),
    "EVI": ("2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)", "Enhanced vegetation index (Huete et al. 2002)"),
    "SAVI": ("1.5 * (NIR - RED) / (NIR + RED + 0.5)", "Soil-adjusted vegetation index, L = 0.5 (Huete 1988)"),
    "NDBI": ("(SWIR - NIR) / (SWIR + NIR)", "Normalised difference built-up index (Zha et al. 2003)"),
}

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_CMP = {ast.Lt: np.less, ast.LtE: np.less_equal, ast.Gt: np.greater, ast.GtE: np.greater_equal}
_FUNCS = {
    "sqrt": np.sqrt,
    "log": np.log,
    "log10": np.log10,
    "exp": np.exp,
    "abs": np.abs,
    "min": np.minimum,
    "max": np.maximum,
    "where": np.where,
}


class ExpressionError(ValueError):
    pass


def evaluate(expression: str, bands: dict, rows=1024):
    """Evaluate e.g. "(B8 - B4) / (B8 + B4)" with bands = {"B8": array, "B4": array, ...}, in float32 and, for large
    images, in blocks of rows (two Sentinel-2 bands of 10980 x 10980 px took 5.3 GB in float64 at once)."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"cannot read the expression: {e.msg}") from None
    arrays = [np.asarray(b) for b in bands.values()]
    if arrays and all(a.ndim == 2 and a.shape == arrays[0].shape for a in arrays) and arrays[0].shape[0] > rows:
        ny = arrays[0].shape[0]
        out = np.empty(arrays[0].shape, np.float32)
        for r0 in range(0, ny, rows):
            out[r0 : r0 + rows] = _evaluate(tree, {n: np.asarray(b)[r0 : r0 + rows] for n, b in bands.items()})
        return out
    return _evaluate(tree, bands)


def _evaluate(tree, bands):

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in bands:
                raise ExpressionError(f"unknown band {node.id}; available: {', '.join(bands)}")
            return np.asarray(bands[node.id], np.float32)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP:
            return _CMP[type(node.ops[0])](ev(node.left), ev(node.comparators[0])).astype(np.float32)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS
            and not node.keywords
        ):
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ExpressionError(f"not allowed in an expression: {ast.unparse(node)}")

    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.array(ev(tree), np.float32)  # a copy: never a view of a band
    out[~np.isfinite(out)] = np.nan
    return out


def index_expression(name, roles: dict):
    """The expression of a named index with band roles replaced by band names (e.g. NIR -> B8)."""
    expr = INDICES[name][0]
    for role in sorted(roles, key=len, reverse=True):
        expr = expr.replace(role, roles[role])
    return expr


def statistics(band, sample=4_000_000):
    """Count and extremes of every finite pixel; mean, std and percentiles from an even sample of at most `sample`
    pixels (sorting 120 million Sentinel-2 pixels took 11 s and 1.4 GB; the sample differs by far less than a
    pixel's noise)."""
    a = np.asarray(band, np.float32)
    n = int(np.count_nonzero(np.isfinite(a)))
    if n == 0:
        return {"n": 0}
    flat = a.ravel()
    v = flat[:: max(1, flat.size // sample)]
    v = v[np.isfinite(v)] if np.isfinite(v).any() else flat[np.isfinite(flat)]
    p = np.percentile(v, [2, 25, 50, 75, 98])
    return {
        "n": n,
        "min": float(np.nanmin(a)),
        "max": float(np.nanmax(a)),
        "mean": float(v.mean(dtype=np.float64)),
        "std": float(v.std(dtype=np.float64)),
        "p2": float(p[0]),
        "p25": float(p[1]),
        "median": float(p[2]),
        "p75": float(p[3]),
        "p98": float(p[4]),
    }


def _rows_of(bands):
    """(rows(r0, r1) -> (n_bands, rows, nx) float32, (n_bands, ny, nx)) for bands in memory (an array) or read from
    disk by rows (raster.Scene, for scenes larger than the computer's free memory)."""
    if hasattr(bands, "rows") and hasattr(bands, "n_bands"):
        return bands.rows, (bands.n_bands, *bands.shape)
    cube = np.asarray(bands, np.float32)
    return (lambda r0, r1: cube[:, r0:r1]), cube.shape


def _standardised(bands, block=512):
    """(rows, shape, where every band is finite, its count, each band's mean and standard deviation there) — float64
    sums block by block, the same order whether the bands are in memory or read by rows. The pixels are standardised
    block by block where they are used: a copy of every valid pixel was another 1 GB on a Sentinel-2 tile."""
    rows, shape = _rows_of(bands)
    nb, ny, nx = shape
    valid = np.empty((ny, nx), bool)
    s1, s2 = np.zeros(nb), np.zeros(nb)
    for r0 in range(0, ny, block):
        b = rows(r0, r0 + block)
        v = np.all(np.isfinite(b), axis=0)
        valid[r0 : r0 + block] = v
        for k in range(nb):
            x = b[k][v].astype(np.float64)
            s1[k], s2[k] = s1[k] + x.sum(), s2[k] + (x * x).sum()
    n = int(valid.sum())
    if n == 0:
        raise ValueError("no pixel has a value in every band")
    mean = s1 / n
    sd = np.sqrt(np.maximum(s2 / n - mean * mean, 0.0))
    sd[sd == 0] = 1.0
    return rows, shape, valid, n, mean.astype(np.float32)[:, None], sd.astype(np.float32)[:, None]


def _valid_pixels(rows, shape, valid, index, mean, sd, block=512):
    """Standardised values (n_bands, len(index)) of the index-th valid pixels (index sorted, counted in row order),
    read block by block (each block once)."""
    per_row = np.cumsum(valid.sum(axis=1))
    picks = np.searchsorted(per_row, index, side="right")  # row of each pick
    out = np.empty((shape[0], len(index)), np.float32)
    bounds = np.searchsorted(picks, np.arange(shape[1] + 1))  # index is sorted: each row's picks are one slice
    for r0 in range(0, shape[1], block):
        r1 = min(r0 + block, shape[1])
        if bounds[r1] == bounds[r0]:
            continue
        b = rows(r0, r1)
        for r in range(r0, r1):
            sel = slice(bounds[r], bounds[r + 1])
            if sel.start == sel.stop:
                continue
            cols = np.flatnonzero(valid[r])[index[sel] - (per_row[r - 1] if r else 0)]
            out[:, sel] = b[:, r - r0, cols]
    return (out - mean) / sd


def _blocks(rows, shape, valid, mean, sd, block=256):
    """(row slice, standardised valid pixels (n_bands, m), the block's validity mask) block by block."""
    for r0 in range(0, shape[1], block):
        v = valid[r0 : r0 + block]
        yield slice(r0, r0 + block), (rows(r0, r0 + block)[:, v] - mean) / sd, v


def _nearest(x, centres):
    """Index of the nearest centre (k, n_bands) for every column of x: |c|^2 - 2 c.x is the squared distance less
    |x|^2, the same for every centre, so one matrix product (the pixels x centres x bands difference took 60 % of
    k-means). On the GPU when the compute mode allows it."""
    from ..compute.classify import gpu_nearest

    labels = gpu_nearest(x, centres)
    if labels is not None:
        return labels
    c = np.asarray(centres, np.float64)
    return np.argmin((c * c).sum(axis=1)[:, None] - 2 * (c @ x), axis=0)


def kmeans(bands, k=5, seed=0, sample=200_000):
    """Unsupervised classes 0..k-1 (NaN where any band is missing); classes ordered by the mean of the
    first band so the labels are stable from run to run."""
    from scipy.cluster.vq import kmeans2

    rows, shape, valid, n, mean, sd = _standardised(bands)
    rng = np.random.default_rng(seed)
    pick = rng.choice(n, sample, replace=False) if n > sample else np.arange(n)
    order_of_pick = np.argsort(pick)
    train = np.empty((shape[0], len(pick)), np.float32)
    train[:, order_of_pick] = _valid_pixels(rows, shape, valid, pick[order_of_pick], mean, sd)
    centres, _ = kmeans2(np.asarray(train.T, np.float64), k, minit="++", seed=seed)
    centres = centres[np.argsort(centres[:, 0])].astype(np.float32)
    out = np.full(valid.shape, np.nan, np.float32)
    for r, x, v in _blocks(rows, shape, valid, mean, sd):
        out[r][v] = _nearest(x, centres)
    return out


def pca(bands, n=3, sample=4_000_000):
    """Principal components (n, ny, nx) of the standardised bands and the explained variance fractions: the
    eigenvectors of the bands' covariance from an even sample of at most `sample` pixels (an SVD of every pixel
    needs a second pixels x bands matrix: a Sentinel-2 scene ran out of memory), every pixel projected on them."""
    rows, shape, valid, count, mean, sd = _standardised(bands)
    x = _valid_pixels(rows, shape, valid, np.arange(0, count, max(1, count // sample)), mean, sd)
    var, vec = np.linalg.eigh(np.atleast_2d(np.cov(x.astype(np.float64))))
    order = np.argsort(var)[::-1]
    var, vec = var[order], vec[:, order]
    out = np.full((n, *valid.shape), np.nan, np.float32)
    w = vec[:, :n].T.astype(np.float32)
    for r, xb, v in _blocks(rows, shape, valid, mean, sd):
        proj = w @ xb
        for i in range(n):
            out[i, r][v] = proj[i]
    return out, (var[:n] / var.sum()).tolist()


def change(before, after, threshold=None):
    """Difference after - before and, with a threshold, a mask of significant change (|diff| > threshold)."""
    a, b = np.asarray(before, np.float32), np.asarray(after, np.float32)
    if a.shape != b.shape:
        raise ValueError("the two images are not on the same pixel grid")
    d = b - a
    return d, (None if threshold is None else (np.abs(d) > threshold).astype(np.float32))


def pixel_spectrum(bands, col, row):
    return np.asarray(bands, np.float32)[:, int(row), int(col)].tolist()
