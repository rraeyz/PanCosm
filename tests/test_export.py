"""Publication output: figures restyled black on white without touching the screen; tables to CSV and LaTeX."""

import matplotlib as mpl
import numpy as np


def test_publication_copy_is_black_on_white(qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui import theme
    from astrowb.ui.workspaces import PlotCanvas

    theme.apply(QApplication.instance(), "dark")
    canvas = PlotCanvas()
    qtbot.addWidget(canvas)
    ax = canvas.figure.add_subplot()
    ax.plot(np.arange(5), np.arange(5) ** 2, label="data")
    ax.set_xlabel("time")
    ax.legend()
    screen_colour = ax.xaxis.label.get_color()
    path = canvas.export_publication(str(tmp_path / "fig.pdf"))
    assert (tmp_path / "fig.pdf").stat().st_size > 1000 and path.endswith(".pdf")
    from astrowb.ui.plot.export import publication_copy

    copy = publication_copy(canvas.figure)
    assert mpl.colors.to_hex(copy.axes[0].xaxis.label.get_color()) == "#000000"
    assert mpl.colors.to_hex(copy.axes[0].get_facecolor()) == "#ffffff"
    assert ax.xaxis.label.get_color() == screen_colour  # the screen keeps its theme
    canvas.export_publication(str(tmp_path / "fig.png"))
    from PIL import Image

    assert Image.open(tmp_path / "fig.png").info.get("dpi", (300, 300))[0] > 299


def test_table_to_csv_and_latex(qtbot, tmp_path):
    from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem

    from astrowb.ui.plot.export import export_table

    t = QTableWidget(2, 3)
    qtbot.addWidget(t)
    t.setHorizontalHeaderLabels(["Star", "V_mag", "Note"])
    for r, row in enumerate((("A", "11.20 ± 0.02", "50%"), ("B", "12.01", "x_1"))):
        for c, v in enumerate(row):
            t.setItem(r, c, QTableWidgetItem(v))
    combo = QComboBox()
    combo.addItems(["light", "dark"])
    t.setCellWidget(1, 2, combo)
    export_table(t, tmp_path / "t.csv")
    assert (tmp_path / "t.csv").read_text(encoding="utf-8").splitlines() == [
        "Star,V_mag,Note",
        "A,11.20 ± 0.02,50%",
        "B,12.01,light",
    ]
    export_table(t, tmp_path / "t.tex")
    tex = (tmp_path / "t.tex").read_text(encoding="utf-8")
    assert r"Star & V\_mag & Note \\" in tex and r"11.20 $\pm$ 0.02 & 50\%" in tex and r"\toprule" in tex
