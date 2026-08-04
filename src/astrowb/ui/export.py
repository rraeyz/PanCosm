"""Publication-quality output: any plot as a black-on-white figure (PDF, SVG, EPS or 300 dpi PNG) whatever the
screen theme, and any table as CSV or a LaTeX tabular."""

import pickle
from pathlib import Path

INK = "black"


def publication_copy(figure, width_in=6.5, font_size=9):
    """A copy of the figure restyled for print; the figure on screen is not touched."""
    fig = pickle.loads(pickle.dumps(figure))  # matplotlib figures pickle with all their artists
    w, h = fig.get_size_inches()
    fig.set_size_inches(width_in, width_in * h / w)
    fig.patch.set_facecolor("white")
    for ax in fig.axes:
        ax.set_facecolor("white")
        for spine in ax.spines.values():
            spine.set_color(INK)
        ax.tick_params(colors=INK, which="both", labelsize=font_size, direction="in", top=True, right=True)
        for text in (ax.title, ax.xaxis.label, ax.yaxis.label):
            text.set_color(INK)
            text.set_fontsize(font_size + 1)
        for text in ax.texts:
            text.set_color(INK)
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_edgecolor(INK)
            for text in legend.get_texts():
                text.set_color(INK)
                text.set_fontsize(font_size)
        ax.grid(False)
    return fig


def save_publication(figure, path):
    """A white, print-ready copy of the figure; a name without a picture type (or with one matplotlib cannot
    write, e.g. .fits) gets .png."""
    fig = publication_copy(figure)
    path = Path(path)
    if path.suffix.lower().lstrip(".") not in fig.canvas.get_supported_filetypes():
        path = path.with_name(path.name + ".png")
    fig.savefig(path, dpi=300, facecolor="white", bbox_inches="tight")
    return str(path)


def table_rows(table):
    """Header and cell texts of a QTableWidget (cell widgets such as combo boxes and spin boxes included)."""
    header = [
        table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else ""
        for c in range(table.columnCount())
    ]
    rows = []
    for r in range(table.rowCount()):
        row = []
        for c in range(table.columnCount()):
            item, widget = table.item(r, c), table.cellWidget(r, c)
            if widget is not None:
                text = widget.currentText() if hasattr(widget, "currentText") else getattr(widget, "text", lambda: "")()
            else:
                text = item.text() if item else ""
            row.append(text)
        rows.append(row)
    return header, rows


def _latex_escape(text):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_")):
        text = text.replace(a, b)
    return text.replace("±", r"$\pm$").replace("−", "$-$")


def export_table(table, path):
    """CSV for .csv / .txt, a LaTeX tabular (booktabs) for .tex."""
    import csv

    header, rows = table_rows(table)
    if str(path).endswith(".tex"):
        lines = [r"\begin{tabular}{" + "l" * len(header) + "}", r"\toprule"]
        lines.append(" & ".join(_latex_escape(h) for h in header) + r" \\")
        lines.append(r"\midrule")
        lines += [" & ".join(_latex_escape(c) for c in row) + r" \\" for row in rows]
        lines += [r"\bottomrule", r"\end{tabular}"]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    else:
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows([header, *rows])
    return path


def rounded(value, error):
    """(value, error) as texts for a paper: the error to two significant digits, the value to the same decimal
    place (e.g. 1.234567 ± 0.000123 -> '1.23457', '0.00012'); without an error, six significant digits."""
    import math

    if error is None or not math.isfinite(error) or error <= 0:
        return f"{value:.6g}", ""
    digits = max(0, 1 - math.floor(math.log10(error)))
    return f"{value:.{digits}f}", f"{error:.{digits}f}"


def save_results(path, rows, caption=""):
    """Fitted values as a table: rows of (parameter, value, error or None, unit). CSV (parameter, value, error,
    unit) for .csv, otherwise a LaTeX table (booktabs) with the caption."""
    import csv

    cells = [(name, *rounded(value, error), unit) for name, value, error, unit in rows]
    if str(path).endswith(".tex"):
        lines = [r"\begin{table}", r"\centering"]
        if caption:
            lines.append(r"\caption{" + _latex_escape(caption) + "}")
        lines += [r"\begin{tabular}{lll}", r"\toprule", r"Parameter & Value & Unit \\", r"\midrule"]
        for name, v, e, unit in cells:
            value = f"${v} \\pm {e}$" if e else f"${v}$"
            lines.append(f"{_latex_escape(name)} & {value} & {_latex_escape(unit)} \\\\")
        lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if caption:
                w.writerow([f"# {caption}"])
            w.writerows([("parameter", "value", "error", "unit"), *cells])
    return str(path)


def results_button(parent, rows_and_caption):
    """A button 'Export results (CSV / LaTeX)…' that writes rows_and_caption() -> (rows, caption) to a file."""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QFileDialog, QPushButton

    def tr(text):
        return QCoreApplication.translate("Export", text)

    button = QPushButton(tr("Export results (CSV / LaTeX)…"), parent)
    button.setToolTip(
        tr(
            "The fitted values with their 1σ errors, rounded as in a paper (the error to two significant digits), "
            "as CSV or as a LaTeX table ready for a manuscript"
        )
    )

    def save():
        got = rows_and_caption()
        if not got:
            return
        path, _ = QFileDialog.getSaveFileName(parent, tr("Export results"), "results.tex", "LaTeX (*.tex);;CSV (*.csv)")
        if path:
            save_results(path, *got)

    button.clicked.connect(save)
    return button
