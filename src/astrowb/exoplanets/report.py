"""Results for a paper (plans/exoplanets.md EXO-12, the table): parameters grouped as EXOFAST lays them out
(stellar, planetary, wavelength, transit…), each with its symbol, description and units, the median and the 68 %
interval as ^{+a}_{−b} with the digits of the smaller error (core.inference.results.rounded)."""

from ..core.inference.results import rounded


def _cell(median, minus, plus):
    v, lo, hi = rounded(median, minus, plus)
    return f"${v}^{{+{hi}}}_{{-{lo}}}$"


def latex(rows, style="aa", caption="Median values and 68 % intervals", label="tab:planet"):
    """rows: [(group, symbol, description, (median, minus, plus))] in order; the groups become sub-headings."""
    if style not in ("aa", "aastex"):
        raise ValueError(f"unknown table style: {style}")
    body, group = [], None
    for g, sym, desc, (m, lo, hi) in rows:
        if g != group:
            body.append(f"\\multicolumn{{3}}{{l}}{{\\textit{{{g}}}}} \\\\")
            group = g
        body.append(f"{sym} & {desc} & {_cell(m, lo, hi)} \\\\")
    if style == "aastex":
        return "\n".join(["\\begin{deluxetable}{llc}", f"\\tablecaption{{{caption}\\label{{{label}}}}}",
                          "\\tablehead{\\colhead{Symbol} & \\colhead{Description} & \\colhead{Value}}",
                          "\\startdata", *body, "\\enddata", "\\end{deluxetable}"])  # fmt: skip
    return "\n".join(["\\begin{table}", f"\\caption{{{caption}}}", f"\\label{{{label}}}", "\\centering",
                      "\\begin{tabular}{llc}", "\\hline\\hline", "Symbol & Description & Value \\\\", "\\hline",
                      *body, "\\hline", "\\end{tabular}", "\\end{table}"])  # fmt: skip


def markdown(rows):
    out = ["| Symbol | Description | Value |", "|---|---|---|"]
    group = None
    for g, sym, desc, (m, lo, hi) in rows:
        if g != group:
            out.append(f"| **{g}** | | |")
            group = g
        v, a, b = rounded(m, lo, hi)
        out.append(f"| {sym} | {desc} | {v} +{b} −{a} |")
    return "\n".join(out)
