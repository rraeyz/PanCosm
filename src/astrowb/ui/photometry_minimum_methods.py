"""The Timing stage's choice among the eclipse timing methods and the table comparing them (plans/photometry.md
PHO-26; engine: timeseries/timing_methods.py, step photometry.compare_minimum_methods)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QPushButton

translate = QCoreApplication.translate


def method_names():
    return {
        "kvw": translate("PhotometryMinimum", "Kwee–van Woerden"),
        "mikulasek": translate("PhotometryMinimum", "Mikulášek model"),
        "polynomial": translate("PhotometryMinimum", "polynomial"),
        "gaussian": translate("PhotometryMinimum", "Gaussian"),
        "lorentzian": translate("PhotometryMinimum", "Lorentzian"),
        "bisector": translate("PhotometryMinimum", "bisector"),
        "trapezoid": translate("PhotometryMinimum", "trapezoid fit"),
    }


def _tips():
    c = "PhotometryMinimum"
    return {
        "kvw": translate(c, "Kwee & van Woerden (1956): the time about which the two branches are most symmetric"),
        "mikulasek": translate(
            c,
            "The phenomenological eclipse profile of Mikulášek (2015, A&A 584, A8): depth, width and shape "
            "fitted on a linear baseline",
        ),
        "polynomial": translate(c, "A polynomial (order 2–8, chosen by BIC) fitted around the deepest point"),
        "gaussian": translate(c, "Assumes a symmetric profile: a Gaussian on a linear baseline is fitted"),
        "lorentzian": translate(c, "Assumes a symmetric profile: a Lorentzian on a linear baseline is fitted"),
        "bisector": translate(c, "The mid-points of the two branches at 20 % to 80 % of the depth, averaged"),
    }


def add_method_choice(page, box_layout, group):
    """Combo box after the eclipsing-binary radio button; enabled only while that radio is chosen."""
    group.addButton(page.kvw)
    group.addButton(page.trapezoid)
    box_layout.addWidget(page.kvw)
    page.kvw_method = QComboBox(page)
    for key, tip in _tips().items():
        page.kvw_method.addItem(method_names()[key], key)
        page.kvw_method.setItemData(page.kvw_method.count() - 1, tip, 3)  # Qt.ToolTipRole
    page.kvw_method.setToolTip(
        translate("PhotometryMinimum", "How the time of an eclipse is found; Kwee–van Woerden is the standard")
    )
    page.kvw_method.currentIndexChanged.connect(lambda i: page.kvw_method.setToolTip(page.kvw_method.itemData(i, 3)))
    page.kvw.toggled.connect(page.kvw_method.setEnabled)
    # the longest method name must not widen the narrow stage column
    page.kvw_method.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    page.kvw_method.setMinimumContentsLength(12)
    box_layout.addWidget(page.kvw_method)
    box_layout.addWidget(page.trapezoid)


def minimum_params(page):
    """The method of the Time of minimum step: the combo's while the eclipsing-binary radio is chosen."""
    return {"method": page.kvw_method.currentData() if page.kvw.isChecked() else "trapezoid"}


def add_compare(page, layout):
    """The Compare methods button beside Time of minimum, and its table (hidden until there is a result)."""
    page.compare_button = QPushButton(translate("PhotometryMinimum", "Compare methods"), page)
    page.compare_button.setEnabled(False)
    page.compare_button.setToolTip(
        translate(
            "PhotometryMinimum",
            "The same minimum timed by every eclipse method, with the difference from Kwee–van Woerden",
        )
    )
    page.compare_button.clicked.connect(lambda: compare(page))
    from .kit.table import TableView

    page.compare_table = TableView(page)
    page.compare_table.setMaximumHeight(200)
    page.compare_table.setMinimumWidth(0)
    page.compare_table.hide()
    layout.addWidget(page.minimum_button)  # one above the other: side by side they do not fit the stage column
    layout.addWidget(page.compare_button)
    layout.addWidget(page.compare_table)


def compare(page):
    page.minimum_requested.emit(page.light_curve, {"compare": True})


def show_comparison(page, c):
    from astropy.table import Table

    names = method_names()
    rows = c["rows"]
    t = translate
    page.compare_table.set_table(
        Table(
            [
                [names[r["method"]] for r in rows],
                [f"{r['time']:.6f}" for r in rows],
                [f"{r['error'] * 86400:.1f}" for r in rows],
                ["" if r["diff_s"] is None else f"{r['diff_s']:+.1f}" for r in rows],
            ],
            names=[
                t("PhotometryMinimum", "Method"),
                t("PhotometryMinimum", "Time of minimum"),
                t("PhotometryMinimum", "Error (s)"),
                t("PhotometryMinimum", "Difference from KvW (s)"),
            ],
        )
    )
    page.compare_table.show()
    if c["disagree"]:
        page.result.setText(
            translate(
                "PhotometryMinimum",
                "The methods differ by more than 3σ: the eclipse is badly covered or none of the shapes suits it.",
            )
        )
