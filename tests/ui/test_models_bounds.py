"""UI-16.6: the Lower / Upper columns of the Models parameter table reach the fit and are respected."""

import numpy as np
import pytest

from astrowb.models import fit
from astrowb.settings import Settings
from astrowb.ui import models_bounds

TRUTH = {"period": 1.7, "t0": 2459500.25, "r_sum": 0.3, "k": 0.6, "incl": 86.0, "j": 0.5, "ecosw": 0.0,
         "esinw": 0.0, "l3": 0.0}  # fmt: skip


@pytest.fixture
def page(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(2459500, 2459510, 300))
    f = fit.model(t, TRUTH, (0.4, 0.2), (0.4, 0.2)) + rng.normal(0, 0.003, len(t))
    path = tmp_path / "lc.csv"
    path.write_text("BJD_TDB,rel_flux,rel_flux_err\n" + "\n".join(f"{a},{b},0.003" for a, b in zip(t, f, strict=True)))
    p = win.models_page
    p.file.edit.setText(str(path))
    for r, name in enumerate(("period", "t0")):
        p.table.item(r, 1).setText(str(TRUTH[name]))
    yield p
    win.engine.shutdown()


def test_a_limit_is_passed_to_the_fit_and_respected(page, qtbot):
    page.table.item(4, 1).setText("84")
    page.table.item(4, models_bounds.UPPER).setText("85")  # the true inclination, 86, lies above it
    page.fit_button.click()
    qtbot.waitUntil(lambda: page.result is not None, timeout=60000)
    assert page.result["params"]["incl"] <= 85 + 1e-6


def test_a_start_outside_its_limits_is_refused_and_the_row_marked(page, qtbot):
    page.table.item(4, 1).setText("80")
    page.table.item(4, models_bounds.LOWER).setText("82")
    page.fit_button.click()
    assert page.result is None
    assert "incl = 80 is outside its limits 82 to 90" in page.status.text()
    assert page.table.item(4, 1).background().color().isValid() and page.table.item(4, 1).toolTip()
    page.table.item(4, 1).setText("84")  # inside again: the mark goes with the next Fit
    assert page.undo_stack.canUndo()


def test_the_engine_refuses_a_start_outside_its_limits():
    t = np.linspace(2459500, 2459502, 50)
    with pytest.raises(ValueError, match="incl = 80 is outside its limits 82 to 90"):
        fit.fit_light_curve(t, fit.model(t, TRUTH), None, TRUTH | {"incl": 80.0}, ["incl"], bounds={"incl": (82, None)})


def test_a_log_uniform_prior_with_a_non_positive_limit_is_refused_and_undoable(page):
    from astrowb.ui import models_priors

    box = page.table.cellWidget(5, models_priors.PRIOR)  # j: the engine's lower limit is 0
    box.setCurrentIndex(1)
    assert models_priors.kinds(page.table, ("period", "t0", "r_sum", "k", "incl", "j"))[5] == "log-uniform"
    page.undo_stack.undo()
    assert box.currentIndex() == 0
    page.undo_stack.redo()
    page.fit_button.click()
    assert page.result is None and "j needs finite limits above zero" in page.status.text()
