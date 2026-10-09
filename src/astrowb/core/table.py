"""Tables of results: Astropy `Table`s (columns with units, descriptions and formats) filtered by a small expression
language and written in every format a paper or another program needs (plans/architecture.md ARC-8).

    keep = select(table, "rel_flux_err_T1 < 0.002 and not isnan(airmass)")
    write(table[keep], "minima.tex")      # by extension: .csv .ecsv .vot .tex .md .html

An error column is the value's name with "_err" (or "e_" before it); in LaTeX the pair is printed as
"value ± error" rounded by the error. No Qt here.
"""

import ast
import math
from pathlib import Path

import numpy as np

FORMATS = {".csv": "csv", ".txt": "csv", ".ecsv": "ecsv", ".vot": "votable", ".xml": "votable", ".tex": "latex",
           ".md": "markdown", ".html": "html", ".htm": "html"}  # fmt: skip
_FUNCTIONS = {"abs": np.abs, "isnan": np.isnan, "log10": np.log10, "sqrt": np.sqrt}
_COMPARE = {ast.Gt: np.greater, ast.Lt: np.less, ast.GtE: np.greater_equal, ast.LtE: np.less_equal,
            ast.Eq: np.equal, ast.NotEq: np.not_equal}  # fmt: skip
_ARITH = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide}


def rounded(value, error):
    """(value, error) as texts for a paper: the error to two significant digits, the value to the same decimal
    place (e.g. 1.234567 ± 0.000123 -> '1.23457', '0.00012'); without an error, six significant digits."""
    if error is None or not math.isfinite(error) or error <= 0:
        return f"{value:.6g}", ""
    digits = max(0, 1 - math.floor(math.log10(error)))
    return f"{value:.{digits}f}", f"{error:.{digits}f}"


def select(table, expression):
    """Boolean mask of the rows an expression keeps: column names, numbers, + − × ÷, comparisons (also chained),
    and / or / not, abs() isnan() log10() sqrt(). An empty expression keeps every row. Raises ValueError with the
    reason for anything else (no names other than columns, no attribute access, no other calls)."""
    if not expression.strip():
        return np.ones(len(table), bool)
    try:
        tree = ast.parse(expression.replace(" AND ", " and ").replace(" OR ", " or "), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"filter not understood: {expression}") from e

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in table.colnames:
                raise ValueError(f"no column {node.id} in the table")
            return np.asarray(table[node.id], float)
        if isinstance(node, ast.BoolOp):
            parts = [np.asarray(ev(v), bool) for v in node.values]
            return np.logical_and.reduce(parts) if isinstance(node.op, ast.And) else np.logical_or.reduce(parts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return ~np.asarray(ev(node.operand), bool)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in _ARITH:
            return _ARITH[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.Compare):
            out, left = True, ev(node.left)
            for op, right_node in zip(node.ops, node.comparators, strict=True):
                if type(op) not in _COMPARE:
                    raise ValueError(f"filter not understood: {expression}")
                right = ev(right_node)
                out = out & _COMPARE[type(op)](left, right)
                left = right
            return out
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
            if len(node.args) != 1 or node.keywords:
                raise ValueError(f"filter not understood: {expression}")
            return _FUNCTIONS[node.func.id](ev(node.args[0]))
        raise ValueError(f"filter not understood: {expression}")

    with np.errstate(invalid="ignore", divide="ignore"):
        mask = np.broadcast_to(np.asarray(ev(tree), bool), (len(table),))
    return np.array(mask)


def error_of(table, name):
    """The name of the error column of `name`, or None."""
    for candidate in (f"{name}_err", f"e_{name}", f"{name}_error"):
        if candidate in table.colnames:
            return candidate
    return None


def write(table, path, caption=""):
    """Write the table by the file's extension (FORMATS). Returns the path."""
    path = Path(path)
    kind = FORMATS.get(path.suffix.lower())
    if kind is None:
        raise ValueError(f"cannot write tables as {path.suffix or '?'}")
    if kind in ("csv", "ecsv", "votable", "html"):
        fmt = {"csv": "ascii.csv", "ecsv": "ascii.ecsv", "votable": "votable", "html": "ascii.html"}[kind]
        table.write(path, format=fmt, overwrite=True)
    elif kind == "latex":
        path.write_text(_latex(table, caption), encoding="utf-8")
    else:
        path.write_text(_markdown(table), encoding="utf-8")
    return path


def _cells(table):
    """(headers, rows of texts) with each error column folded into its value as 'v ± e'."""
    errors = {error_of(table, n) for n in table.colnames} - {None}
    names = [n for n in table.colnames if n not in errors]
    headers = [f"{n} [{table[n].unit}]" if table[n].unit else n for n in names]
    rows = []
    for row in table:
        cells = []
        for n in names:
            v, err = row[n], error_of(table, n)
            if err is not None and _number(v):
                value, e = rounded(float(v), float(row[err]))
                cells.append(f"{value} ± {e}" if e else value)
            elif _number(v):
                cells.append(f"{float(v):.6g}" if not float(v).is_integer() or abs(float(v)) > 1e15 else str(int(v)))
            else:
                cells.append(str(v))
        rows.append(cells)
    return headers, rows


def _number(v):
    return isinstance(v, int | float | np.integer | np.floating) and not isinstance(v, bool | np.bool_)


def _tex(text):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_")):
        text = text.replace(a, b)
    return text.replace(" ± ", r" $\pm$ ").replace("−", "$-$")


def _latex(table, caption):
    """An AASTeX deluxetable (also compiles in A&A and MNRAS with the deluxetable package)."""
    headers, rows = _cells(table)
    lines = [r"\begin{deluxetable}{" + "l" * len(headers) + "}", r"\tablecaption{" + _tex(caption) + "}"]
    lines.append(r"\tablehead{" + " & ".join(r"\colhead{" + _tex(h) + "}" for h in headers) + "}")
    lines.append(r"\startdata")
    lines += [" & ".join(_tex(c) for c in row) + r" \\" for row in rows]
    lines += [r"\enddata", r"\end{deluxetable}", ""]
    return "\n".join(lines)


def _markdown(table):
    headers, rows = _cells(table)
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(c.replace("|", r"\|") for c in row) + " |" for row in rows]
    return "\n".join(out) + "\n"
