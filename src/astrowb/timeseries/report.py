"""The period-search report (plans/period.md PER-16, the parts without figures): the peaks table in LaTeX, the
methods paragraph and the VSX submission sheet."""

from .oc_report import paren


def peaks_latex(rows, caption="Periodogram peaks", label="tab:peaks"):
    """rows: [(period, its error, power, false-alarm probability or None, note)] → an A&A-style table."""
    lines = ["\\begin{table}", f"\\caption{{{caption}}}", f"\\label{{{label}}}", "\\centering",
             "\\begin{tabular}{lccl}", "\\hline\\hline", "Period (d) & Power & FAP & Note \\\\", "\\hline"]  # fmt: skip
    for p, e, power, fap, note in rows:
        fap_text = "--" if fap is None else f"{fap:.1e}"
        lines.append(f"${paren(p, e)}$ & {power:.3f} & {fap_text} & {note} \\\\")
    return "\n".join([*lines, "\\hline", "\\end{tabular}", "\\end{table}"])


def methods_text(method, n_points, span_days, grid, significance, sources=()):
    parts = [f"The period was searched with the {method} method on {n_points} points spanning {span_days:.1f} days,",
             f"over {grid}.", f"Its significance comes from {significance}."]  # fmt: skip
    if sources:
        parts.append("The data come from " + ", ".join(sources) + ".")
    return " ".join(parts)


def vsx_sheet(name, var_type, period, period_err, epoch, epoch_err, max_mag, min_mag, band, rise_or_duration=None,
              eclipsing=False):  # fmt: skip
    """The fields of a VSX submission as text (the type is a suggestion to check, never a result)."""
    lines = [f"Name: {name}", f"Type: {var_type}", f"Period: {paren(period, period_err)} d",
             f"Epoch: {paren(epoch, epoch_err)} ({'minimum' if eclipsing else 'maximum'})",
             f"Range: {max_mag:.2f} - {min_mag:.2f} {band}"]  # fmt: skip
    if rise_or_duration is not None:
        label = "Eclipse duration" if eclipsing else "Rise time"
        lines.append(f"{label}: {rise_or_duration:.0f} %")
    return "\n".join(lines)
