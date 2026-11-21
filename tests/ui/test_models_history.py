"""UI-16.6: the Models window's Fit history and Report result tabs; synthetic light curve, two quick fits."""

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from astrowb.models import fit
from astrowb.settings import Settings

TRUTH = {"period": 1.7, "t0": 2459500.25, "r_sum": 0.3, "k": 0.6, "incl": 86.0, "j": 0.5, "ecosw": 0.0,
         "esinw": 0.0, "l3": 0.0}  # fmt: skip


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_history_lists_each_fit_and_restores_values_and_report_copies(window, qtbot, tmp_path):
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(2459500, 2459510, 300))
    f = fit.model(t, TRUTH, (0.4, 0.2), (0.4, 0.2)) + rng.normal(0, 0.003, len(t))
    path = tmp_path / "lc.csv"
    path.write_text("BJD_TDB,rel_flux,rel_flux_err\n" + "\n".join(f"{a},{b},0.003" for a, b in zip(t, f, strict=True)))
    page = window.models_page
    page.file.edit.setText(str(path))
    for r, name in enumerate(("period", "t0")):
        page.table.item(r, 1).setText(str(TRUTH[name]))
    for start in ("84", "85"):
        page.table.item(4, 1).setText(start)
        page.result = None
        page.fit_button.click()
        qtbot.waitUntil(lambda: page.result is not None, timeout=60000)
    assert len(page.fit_history) == 2 and page.history_view.table.rowCount() == 2
    assert page.history_view.table.columnCount() == 6
    first = page.fit_history[0]["params"]["incl"]
    page.table.item(4, 1).setText("70")
    page.history_view.table.setCurrentCell(0, 0)
    assert page.restore_button.isEnabled()
    page.restore_button.click()
    assert float(page.table.item(4, 1).text()) == pytest.approx(first, rel=1e-6)
    assert page.undo_stack.canUndo()
    assert "χ²ᵣ" in page.report_view.toPlainText()
    page.report_copy.click()
    assert QApplication.clipboard().text() == page.report_view.toPlainText()
