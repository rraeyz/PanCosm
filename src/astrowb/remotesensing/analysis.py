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


def evaluate(expression: str, bands: dict):
    """Evaluate e.g. "(B8 - B4) / (B8 + B4)" with bands = {"B8": array, "B4": array, ...}."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"cannot read the expression: {e.msg}") from None

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in bands:
                raise ExpressionError(f"unknown band {node.id}; available: {', '.join(bands)}")
            return np.asarray(bands[node.id], np.float64)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP:
            return _CMP[type(node.ops[0])](ev(node.left), ev(node.comparators[0])).astype(np.float64)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCS
            and not node.keywords
        ):
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ExpressionError(f"not allowed in an expression: {ast.unparse(node)}")

    with np.errstate(divide="ignore", invalid="ignore"):
        out = ev(tree)
    out = np.asarray(out, np.float64)
    out[~np.isfinite(out)] = np.nan
    return out.astype(np.float32)


def index_expression(name, roles: dict):
    """The expression of a named index with band roles replaced by band names (e.g. NIR -> B8)."""
    expr = INDICES[name][0]
    for role in sorted(roles, key=len, reverse=True):
        expr = expr.replace(role, roles[role])
    return expr


def statistics(band):
    v = np.asarray(band, np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0}
    p = np.percentile(v, [2, 25, 50, 75, 98])
    return {
        "n": int(v.size),
        "min": float(v.min()),
        "max": float(v.max()),
        "mean": float(v.mean()),
        "std": float(v.std()),
        "p2": float(p[0]),
        "p25": float(p[1]),
        "median": float(p[2]),
        "p75": float(p[3]),
        "p98": float(p[4]),
    }


def _pixels(bands):
    """(n_valid, n_bands) standardised pixel vectors and the validity mask."""
    cube = np.asarray(bands, np.float64)
    valid = np.all(np.isfinite(cube), axis=0)
    x = cube[:, valid].T
    mu, sd = x.mean(axis=0), x.std(axis=0)
    return (x - mu) / np.where(sd > 0, sd, 1.0), valid


def kmeans(bands, k=5, seed=0, sample=200_000):
    """Unsupervised classes 0..k-1 (NaN where any band is missing); classes ordered by the mean of the
    first band so the labels are stable from run to run."""
    from scipy.cluster.vq import kmeans2, vq

    x, valid = _pixels(bands)
    rng = np.random.default_rng(seed)
    train = x[rng.choice(len(x), min(sample, len(x)), replace=False)] if len(x) > sample else x
    centres, _ = kmeans2(train, k, minit="++", seed=seed)
    order = np.argsort(centres[:, 0])
    labels, _ = vq(x, centres[order])
    out = np.full(valid.shape, np.nan, np.float32)
    out[valid] = labels
    return out


def pca(bands, n=3):
    """Principal components (n, ny, nx) of the standardised bands and the explained variance fractions."""
    x, valid = _pixels(bands)
    _, s, vt = np.linalg.svd(x - x.mean(axis=0), full_matrices=False)
    comps = x @ vt[:n].T
    out = np.full((n, *valid.shape), np.nan, np.float32)
    for i in range(n):
        out[i][valid] = comps[:, i]
    var = s**2 / np.sum(s**2)
    return out, var[:n].tolist()


def change(before, after, threshold=None):
    """Difference after - before and, with a threshold, a mask of significant change (|diff| > threshold)."""
    a, b = np.asarray(before, np.float32), np.asarray(after, np.float32)
    if a.shape != b.shape:
        raise ValueError("the two images are not on the same pixel grid")
    d = b - a
    return d, (None if threshold is None else (np.abs(d) > threshold).astype(np.float32))


def pixel_spectrum(bands, col, row):
    return np.asarray(bands, np.float32)[:, int(row), int(col)].tolist()
