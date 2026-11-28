"""The model comparison of the O−C window (plans/oc.md OC-5, OC-9): in the Model stage the weights (the errors or by
method) and a robust option, and "Compare models"; the "Models" results tab lists the linear, quadratic and cubic
ephemerides, the segmented one (one period jump), a sinusoid and a damped sinusoid on the linear ephemeris with χ²,
χ²ᵣ, BIC, AIC and ΔBIC, and under it the verdict, the F-test of the parabola, dP/dt and the updated ephemeris."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .kit.table_view import DataTable
from .oc_periodogram import errors

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcCompare", "…") calls
FEWEST = 8
# ephemeris_models.METHOD_WEIGHTS by the method codes of the minima (visual 1, photographic 3, electronic 10)
BY_CODE = {"vis": "visual", "pg": "photographic", "ccd": "electronic", "pe": "electronic"}


def names():
    return {"linear": translate("OcCompare", "linear"), "quadratic": translate("OcCompare", "quadratic"),
            "cubic": translate("OcCompare", "cubic"), "segmented": translate("OcCompare", "segmented (one jump)"),
            "sinusoid": translate("OcCompare", "linear + sinusoid"),
            "damped": translate("OcCompare", "linear + damped sinusoid")}  # fmt: skip


def method_errors(minima, errs):
    """σ ∝ 1 / √weight by method, scaled to the median error given (only the relative weights are known)."""
    from ..timeseries.ephemeris_models import weights_by_method

    w = weights_by_method([BY_CODE.get(str(m.method or "").lower(), "") for m in minima])
    return float(np.median(errs)) * np.sqrt(np.median(w) / w)


def fits(times, epochs, errs, robust=None):
    """{key: ephemeris_models fit} of every model the comparison lists."""
    from ..timeseries import ephemeris_models as em

    out = {k: em.fit(times, epochs, errs, order, robust=robust) for k, order in
           (("linear", 1), ("quadratic", 2), ("cubic", 3))}  # fmt: skip
    out["segmented"] = em.segmented(times, epochs, errs, 1, robust=robust)
    out["sinusoid"] = em.find_cycle(times, epochs, errs)
    out["damped"] = em.damped_cycle(times, epochs, errs)
    return out


def summary(found, period):
    """The verdict on the lowest BIC and the numbers of the parabola, the damped term and the updated ephemeris."""
    from ..timeseries import ephemeris_models as em

    label = names()
    best = min(found, key=lambda k: found[k]["bic"])
    second = min((k for k in found if k != best), key=lambda k: found[k]["bic"])
    f, p = em.f_test(found["linear"], found["quadratic"])
    rate, rate_err, _ = em.dp_dt(found["quadratic"])
    myr, myr_err = em.dp_dt_days_per_myr(found["quadratic"])
    d = found["damped"]
    t0, t0_err, p_new, p_err, _ = em.updated(found["linear"])
    return [
        translate("OcCompare", "{best} is preferred: ΔBIC = {d:.0f} against {second}").format(
            best=label[best], d=found[best]["bic"] - found[second]["bic"], second=label[second]
        ),
        translate("OcCompare", "F-test, quadratic against linear: F = {f:.2f}, p = {p:.2g}").format(f=f, p=p),
        translate("OcCompare", "dP/dt = {r:.3g} ± {re:.2g} s/yr ({m:.3g} ± {me:.2g} d/Myr)").format(
            r=rate, re=rate_err, m=myr, me=myr_err
        ),
        translate("OcCompare", "Damped sinusoid: period {c:.0f} cycles ({y:.2f} yr), decay τ = {t:.0f} cycles").format(
            c=d["cycles"][0], y=d["cycles"][0] * period / 365.25, t=d["damping"]
        ),
        translate("OcCompare", "Updated linear ephemeris: {line}").format(
            line=em.observer_form(t0, t0_err, p_new, p_err)
        ),
    ]


def run(page):
    from ..timeseries.ephemeris import epochs
    from .messages import translate as message

    try:
        minima, t0, period = page.reference()
        if len(minima) < FEWEST:
            raise ValueError(translate("OcCompare", "Comparing the models needs at least {n} minima.").format(n=FEWEST))
        errs = errors(minima)
        if page.weights.currentIndex() == 1:
            errs = method_errors(minima, errs)
        times = np.array([m.time for m in minima], float)
        found = fits(times, epochs(minima, t0, period), errs, page.robust.currentData())
    except ValueError as e:
        page.models_label.setText(message(str(e)))
        return None
    page.compared, page.compared_period = found, period
    label = names()
    best = min(f["bic"] for f in found.values())
    page.models_view.set_data(
        [translate("OcCompare", "Model"), translate("OcCompare", "Parameters"), "χ²", "χ²ᵣ", "BIC", "AIC", "ΔBIC"],
        [
            [
                label[k],
                f["k"],
                round(f["chi2"], 2),
                round(f["chi2r"], 3),
                round(f["bic"], 2),
                round(f["aic"], 2),
                round(f["bic"] - best, 2),
            ]
            for k, f in found.items()
        ],  # fmt: skip
    )
    page.models_label.setText("\n".join(summary(found, period)))
    return found


def add_compare(page):
    """The Model stage's choices and button; returns the "Models" tab's widget."""
    lay = page.stage_boxes["model"].layout()
    row = QHBoxLayout()
    page.weights = QComboBox(page)
    by_method = translate("OcCompare", "Weights by method (visual 1, photographic 3, electronic 10)")
    page.weights.addItems([translate("OcCompare", "Weights from the errors"), by_method])
    page.weights.setToolTip(translate("OcCompare", "How the minima are weighted in the model comparison"))
    page.robust = QComboBox(page)
    for text, key in ((translate("OcCompare", "Least squares"), None), (translate("OcCompare", "Robust (Huber)"),
                      "huber"), (translate("OcCompare", "3σ rejection"), "clip")):  # fmt: skip
        page.robust.addItem(text, key)
    page.robust.setToolTip(translate("OcCompare", "Outliers in the polynomial and segmented ephemerides"))
    row.addWidget(page.weights, 1)
    row.addWidget(page.robust)
    lay.addLayout(row)
    page.compare_button = QPushButton(translate("OcCompare", "Compare models"), page)
    page.compare_button.setToolTip(translate(
        "OcCompare", "Fits every ephemeris and a plain and a damped sinusoid; the Models tab ranks them by BIC",
    ))  # fmt: skip
    page.compare_button.clicked.connect(lambda: run(page))
    lay.addWidget(page.compare_button)
    box = QWidget(page)
    page.models_view = DataTable(box)
    page.models_view.table.setObjectName("models_table")
    page.models_label = QLabel(box)
    page.models_label.setWordWrap(True)
    page.compared = None
    box.hide()  # docked at the first comparison (oc_stages)
    tab = QVBoxLayout(box)
    tab.addWidget(page.models_view, 1)
    tab.addWidget(page.models_label)
    return box
