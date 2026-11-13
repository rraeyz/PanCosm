"""The coverage harness (plans/validation.md VAL-7): a simulator and a fitting tool run over N realisations; for
every parameter the share of truths inside the stated 68 % and 95 % intervals, the bias in units of the stated
error, and the ratio of the stated error to the actual scatter. A row per parameter, for the report (VAL-3)."""

import numpy as np


def run(simulate, fit, truth, n=300):
    """simulate(seed) → data; fit(data) → {name: (value, stated 1σ error)}; truth: {name: value}."""
    values, errors = {k: [] for k in truth}, {k: [] for k in truth}
    for seed in range(n):
        got = fit(simulate(seed))
        for k in truth:
            values[k].append(got[k][0])
            errors[k].append(got[k][1])
    rows = {}
    for k, t in truth.items():
        v, e = np.array(values[k]), np.array(errors[k])
        z = (v - t) / e
        rows[k] = {"in68": float(np.mean(np.abs(z) < 1)), "in95": float(np.mean(np.abs(z) < 1.96)),
                   "bias": float(np.mean(z)), "ratio": float(np.mean(e) / np.std(v, ddof=1)), "n": n}  # fmt: skip
    return rows


def assert_honest(rows, in68=(0.60, 0.76), in95=(0.91, 0.985), bias=0.3):
    for k, r in rows.items():
        assert in68[0] <= r["in68"] <= in68[1], (k, r)
        assert in95[0] <= r["in95"] <= in95[1], (k, r)
        assert abs(r["bias"]) < bias, (k, r)
