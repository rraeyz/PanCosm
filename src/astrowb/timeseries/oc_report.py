"""The O−C report (plans/oc.md OC-12, the parts without the interface): parameters of every fitted model side
by side in the journal styles, the next minima to observe, and the methods paragraph."""

import numpy as np

STYLES = ("aastex", "aa")


def paren(value, err, digits=2):
    """'0.365123451(31)': the value to the error's last significant digit, the error on those digits."""
    if not np.isfinite(err) or err <= 0:
        return f"{value:g}"
    decimals = max(digits - 1 - int(np.floor(np.log10(err))), 0)
    scaled = int(round(err * 10**decimals))
    return f"{value:.{decimals}f}({scaled})"


def plusminus(value, err, digits=2):
    """'0.36512345 \\pm 0.00000031' in LaTeX."""
    if not np.isfinite(err) or err <= 0:
        return f"{value:g}"
    decimals = max(digits - 1 - int(np.floor(np.log10(err))), 0)
    return f"{value:.{decimals}f} \\pm {err:.{decimals}f}"


def parameter_table(models, style="aa", form="paren", caption="Fitted O$-$C models", label="tab:oc"):
    """models: {model name: {parameter label: (value, error)}} → a LaTeX table with one column per model (a dash
    where a model has no such parameter), in the AASTeX (deluxetable) or A&A (table) style."""
    if style not in STYLES:
        raise ValueError(f"unknown table style: {style}")
    fmt = paren if form == "paren" else plusminus
    names = list(models)
    rows = []
    for p in dict.fromkeys(k for m in models.values() for k in m):
        cells = [f"${fmt(*models[n][p])}$" if p in models[n] else "--" for n in names]
        rows.append(f"{p} & " + " & ".join(cells) + " \\\\")
    cols = "l" + "c" * len(names)
    if style == "aastex":
        head = " & ".join(["\\colhead{Parameter}"] + [f"\\colhead{{{n}}}" for n in names])
        top = [f"\\begin{{deluxetable}}{{{cols}}}", f"\\tablecaption{{{caption}\\label{{{label}}}}}"]
        return "\n".join([*top, f"\\tablehead{{{head}}}", "\\startdata", *rows, "\\enddata", "\\end{deluxetable}"])
    head = " & ".join(["Parameter", *names]) + " \\\\"
    return "\n".join(["\\begin{table}", f"\\caption{{{caption}}}", f"\\label{{{label}}}", "\\centering",
                      f"\\begin{{tabular}}{{{cols}}}", "\\hline\\hline", head, "\\hline", *rows, "\\hline",
                      "\\end{tabular}", "\\end{table}"])  # fmt: skip


def next_minima(t0, period, start, end, secondary=True, model=None):
    """The minima between start and end (same time standard): [(epoch, time, kind)]; model(epochs) → times
    replaces the linear ephemeris when given (a quadratic, LTTE or apsidal prediction)."""
    first = np.ceil((start - t0) / period * 2) / 2
    epochs = np.arange(first, (end - t0) / period + 0.5, 0.5)
    if not secondary:
        epochs = epochs[epochs % 1 == 0]
    times = t0 + period * epochs if model is None else np.asarray(model(epochs), float)
    keep = (times >= start) & (times <= end)
    return [(float(e), float(t), "II" if e % 1 else "I") for e, t in zip(epochs[keep], times[keep], strict=True)]


def methods_text(n_minima, standard, timing_method, weights, models, sampler=None, sources=()):
    """The methods paragraph (English; translated in the interface) from what the session did."""
    parts = [f"We used {n_minima} times of minimum in {standard}, timed by the {timing_method} method."]
    parts.append(f"The fits are weighted by {weights}.")
    parts.append("The models fitted are " + ", ".join(models) + "; they are compared by the Bayesian information "
                 "criterion.")  # fmt: skip
    if sampler:
        parts.append(f"Uncertainties come from {sampler}.")
    if sources:
        parts.append("Literature minima were taken from " + ", ".join(sources) + ".")
    return " ".join(parts)
