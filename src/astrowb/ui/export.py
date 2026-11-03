"""Publication-quality output: any plot as a black-on-white figure (PDF, SVG, EPS or 300 dpi PNG) whatever the
screen theme, and any table as CSV or a LaTeX tabular."""

import pickle

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
    fig = publication_copy(figure)
    fig.savefig(path, dpi=300, facecolor="white", bbox_inches="tight")
    return path


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
