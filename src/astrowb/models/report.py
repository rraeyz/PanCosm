"""The binary's solution for a paper (plans/models.md MOD-19, the table): every parameter with its value and error
(value(error) to the error's digits), fixed ones marked, the error method named in the caption."""

from ..timeseries.oc_report import paren

LABELS = {"incl": "$i$ (deg)", "q": "$q$", "omega1": "$\\Omega_1$", "omega2": "$\\Omega_2$", "t2": "$T_2$ (K)",
          "t1": "$T_1$ (K)", "l3": "$\\ell_3$", "r1": "$r_1$", "r2": "$r_2$", "j": "$J$", "e": "$e$",
          "w": "$\\omega$ (deg)", "period": "$P$ (d)", "t0": "$T_0$", "fillout": "$f$"}  # fmt: skip


def solution_latex(system, errors, method="formal (covariance)", caption="Light-curve solution", label="tab:sol"):
    """errors: {key: σ} of the fitted parameters (fitting.Row.errors or MOD-14's); the rest marked fixed."""
    rows = []
    for k, p in system.params.items():
        name = LABELS.get(k, k)
        if k in errors and p.free and not p.locked:
            rows.append(f"{name} & ${paren(p.value, errors[k])}$ \\\\")
        else:
            why = p.locked or "fixed"
            rows.append(f"{name} & {p.value:g} ({why}) \\\\")
    return "\n".join(["\\begin{table}", f"\\caption{{{caption}; errors: {method}}}", f"\\label{{{label}}}",
                      "\\centering", "\\begin{tabular}{lc}", "\\hline\\hline", "Parameter & Value \\\\", "\\hline",
                      *rows, "\\hline", "\\end{tabular}", "\\end{table}"])  # fmt: skip
