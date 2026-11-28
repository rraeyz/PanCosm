"""The magnetic-cycle check of the O−C window (plans/oc.md OC-9): "Magnetic cycle (Applegate)…" in the Model stage
takes the cyclic term of the last third-body fit, or else of the last comparison's sinusoid (its semi-amplitude K and
period P_mod), the active star's mass, radius, temperature and luminosity and the binary's separation typed, and gives
the energy the Applegate mechanism needs against what the star radiates in one cycle (timeseries/applegate.py)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QPushButton

from .kit.dialogs import Dialog

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcApplegate", "…") calls


def cyclic_term(page):
    """(K in seconds, P_mod in years, the binary's period in days, where from) or None."""
    f = page.fit_result
    if f is not None and hasattr(f, "p3"):
        return f.amplitude * 86400.0, f.p3 / 365.25, f.period, translate("OcApplegate", "the third-body fit")
    found = getattr(page, "compared", None)
    if found:
        from ..timeseries.ephemeris_models import cyclic_terms

        (term,) = cyclic_terms(found["sinusoid"])
        p = float(found["sinusoid"]["coef"][1])
        return term["amplitude"] * 86400.0, term["cycles"] * p / 365.25, p, translate("OcApplegate", "the sinusoid")
    return None


def verdict(term, m, r, t, lum, a):
    from ..timeseries.applegate import dp_over_p, energy

    k, p_mod, p_bin, source = term
    dpp = dp_over_p(k, p_mod)
    out = energy(m, r, t, lum, a, p_bin, dpp, p_mod)
    two = translate("OcApplegate", "no solution") if out["two_zone"] is None else f"{out['two_zone']:.3g}"
    word = translate("OcApplegate", "feasible") if out["feasible"] else translate("OcApplegate", "not feasible")
    return translate(
        "OcApplegate",
        "From {source}: K = {k:.1f} s, P_mod = {p:.2f} yr, ΔP/P = {dpp:.2e}. Energy needed / energy radiated in one "
        "cycle: {tian:.3g} (Tian et al. 2009), {two} (two-zone, Völschow et al. 2016); Applegate parameter "
        "A = {big:.3g}: energetically {word}.",
    ).format(source=source, k=k, p=p_mod, dpp=dpp, tian=out["tian"], two=two, big=out["A"], word=word)


def dialog(page):
    d = Dialog(translate("OcApplegate", "Magnetic cycle (Applegate)"), page, getattr(page, "settings", None),
               "oc_applegate")  # fmt: skip
    form = QFormLayout()
    d.values = []
    for label, value, top in ((translate("OcApplegate", "Active star's mass (M☉)"), 1.0, 100.0),
                              (translate("OcApplegate", "Its radius (R☉)"), 1.0, 1000.0),
                              (translate("OcApplegate", "Its temperature (K)"), 5772.0, 100000.0),
                              (translate("OcApplegate", "Its luminosity (L☉)"), 1.0, 1e6),
                              (translate("OcApplegate", "Binary separation (R☉)"), 1.0, 1e4)):  # fmt: skip
        box = QDoubleSpinBox(d)
        box.setDecimals(3)
        box.setRange(0.001, top)
        box.setValue(value)
        form.addRow(label, box)
        d.values.append(box)
    d.body.addLayout(form)
    d.result = QLabel(d)
    d.result.setWordWrap(True)
    d.body.addWidget(d.result)
    term = cyclic_term(page)

    def update():
        if term is None:
            d.result.setText(translate("OcApplegate", "Fit a third body or compare the models first."))
        else:
            d.result.setText(verdict(term, *(b.value() for b in d.values)))

    for b in d.values:
        b.valueChanged.connect(update)
    update()
    d.add_buttons(translate("OcApplegate", "Close")).setDefault(True)
    return d


def add_applegate(page):
    page.applegate_button = QPushButton(translate("OcApplegate", "Magnetic cycle (Applegate)…"), page)
    page.applegate_button.setToolTip(translate(
        "OcApplegate", "Could the active star's magnetic cycle make this O−C wave instead of a third body? Its energy "
        "against the star's (Applegate 1992; Völschow et al. 2016)",
    ))  # fmt: skip
    page.applegate_button.clicked.connect(lambda: dialog(page).open())
    page.stage_boxes["model"].layout().addWidget(page.applegate_button)
