"""O−C → Planning (plans/oc.md OC-5): the fitted ephemeris, moved to the latest epoch, becomes a Planning target."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcToPlanning", "…") calls


def target_from_fit(page):
    """The Planning target of the page's last polynomial fit (no coordinates: the main window resolves the name).
    T0 and P are those of the polynomial at the latest epoch, so a quadratic fit gives the instantaneous period."""
    from ..timeseries.ephemeris_models import updated

    f = page.fit_result
    if f is None or not hasattr(f, "order"):
        raise ValueError(translate("OcToPlanning", "Fit a linear or quadratic ephemeris first."))
    name = page.star.text().strip() or getattr(page, "file_stem", "")
    if not name:
        raise ValueError(translate("OcToPlanning", "Type the star's name first."))
    k = f.order + 1
    sd = np.array([f.t0_err, f.period_err, f.q_err][:k])
    rho = np.array((f.correlation or {}).get("matrix", np.eye(k)), float)
    t0, _, period, _, _ = updated({"epochs": f.epochs, "order": f.order, "coef": [f.t0, f.period, f.q][:k],
                                   "cov": rho * np.outer(sd, sd)}, at="latest")  # fmt: skip
    secondary = any(m.kind == "II" for m in page.fit_minima)
    return {"name": name, "t0": t0, "period": period, "secondary": secondary, "source": "O−C fit"}


def send(page):
    from .messages import translate as message

    try:
        page.planning_requested.emit(target_from_fit(page))
    except ValueError as e:
        page.result.setText(message(str(e)))


def add_button(page):
    """In the Fit and report stage, enabled by the first successful fit."""
    button = page.to_planning = QPushButton(translate("OcToPlanning", "Send the ephemeris to Planning"), page)
    button.setToolTip(translate(
        "OcToPlanning",
        "The fitted ephemeris, updated to the latest epoch, becomes a Planning target "
        "so tonight's minima are predicted",
    ))  # fmt: skip
    button.setEnabled(False)
    button.clicked.connect(lambda: send(page))
    page.stage_boxes["report"].layout().insertWidget(1, button)
    show = page.show_fit

    def show_fit(f, minima):
        out = show(f, minima)
        button.setEnabled(hasattr(f, "order"))
        return out

    page.show_fit = show_fit
