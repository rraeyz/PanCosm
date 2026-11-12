"""Is the peak real? (plans/period.md PER-4): the aliases of each peak, its false-alarm probability and the error of
its frequency.

    peaks = peak_table(periods, power, t)        # rank, frequency, period, power, notes ("alias of peak 1 by 1 d⁻¹")
    fap = fap_baluev(t, y, err, power, f_min, f_max)  # LS-type periodograms: Baluev 2008 (MNRAS 385, 1279), via Astropy
    fap = fap_shuffled(t, y, search, best_power) # any method: the share of shuffled light curves that score as high
    sigma_f = frequency_error(t, amplitude, noise)   # Montgomery & O'Donoghue 1999 (DSSN 13, 28)

Frequencies are in cycles per day.
"""

import numpy as np

SAMPLING = {"1 d⁻¹": 1.0, "1 yr⁻¹": 1 / 365.25}  # the windows of ground-based data


def local_peaks(freqs, power, n=8):
    """Indices of the n highest local maxima, highest first."""
    p = np.asarray(power, float)
    inner = np.flatnonzero((p[1:-1] >= p[:-2]) & (p[1:-1] >= p[2:])) + 1
    return inner[np.argsort(p[inner])[::-1][:n]]


def relation(f, g, tolerance):
    """How frequency g follows from f: "alias by 1 d⁻¹" (g = f ± k · window), "harmonic 2f", "subharmonic f/2",
    or None. tolerance in cycles per day (the peak width, about 1 / span)."""
    for name, w in SAMPLING.items():
        for k in (1, 2):
            if abs(abs(g - f) - k * w) < tolerance or abs(g + f - k * w) < tolerance:  # also the reflection at 0
                return f"alias by {name}" if k == 1 else f"alias by {k} × {name}"
    for k in (2, 3, 4):
        if abs(g - k * f) < k * tolerance:
            return f"harmonic {k}f"
        if abs(g - f / k) < tolerance:
            return f"subharmonic f/{k}"
    return None


def peak_table(periods, power, t, n=8):
    """[{rank, frequency, period, power, note}] for the n highest peaks; a peak that follows from a higher one is
    noted ("alias by 1 d⁻¹ of peak 1"), so the first unrelated peaks stand out."""
    freqs = 1 / np.asarray(periods, float)
    order = np.argsort(freqs)
    freqs, power = freqs[order], np.asarray(power, float)[order]
    tolerance = 1.5 / np.ptp(t)
    rows = []
    for rank, i in enumerate(local_peaks(freqs, power, n), 1):
        note = ""
        for earlier in rows:
            why = relation(earlier["frequency"], freqs[i], tolerance)
            if why:
                note = f"{why} of peak {earlier['rank']}"
                break
        rows.append({"rank": rank, "frequency": float(freqs[i]), "period": float(1 / freqs[i]),
                     "power": float(power[i]), "note": note})  # fmt: skip
    return rows


def fap_baluev(t, y, err, power, f_min, f_max):
    """False-alarm probability of a Lomb–Scargle power (Astropy's power normalisation) searched over f_min … f_max."""
    from astropy.timeseries import LombScargle

    ls = LombScargle(np.asarray(t, float), np.asarray(y, float), None if err is None else err)
    return float(ls.false_alarm_probability(power, method="baluev", minimum_frequency=f_min, maximum_frequency=f_max))


def fap_shuffled(t, y, search, best_power, n=100, seed=0):
    """The share of n light curves with their values shuffled among the times (the sampling kept, any period
    destroyed) whose highest power reaches best_power; search(t, y) → (periods, power, best). The smallest
    reportable value is 1 / (n + 1)."""
    rng = np.random.default_rng(seed)
    hits = sum(np.max(search(t, rng.permutation(y))[1]) >= best_power for _ in range(n))
    return (hits + 1) / (n + 1)


def frequency_error(t, amplitude, noise):
    """σ_f = √(6 / N) σ / (π T A) for a sinusoid of amplitude A in white noise σ over the span T (M&O 1999)."""
    t = np.asarray(t, float)
    return float(np.sqrt(6 / len(t)) * noise / (np.pi * np.ptp(t) * amplitude))


def verdict(row, fap=None):
    """The top peak in words (English, translated in the interface)."""
    words = []
    if fap is not None:
        words.append("significant" if fap < 0.001 else "marginal" if fap < 0.01 else "not significant")
        words[-1] += f" (FAP {fap:.2g})"
    if row.get("note"):
        words.append(row["note"])
    else:
        words.append("not an alias of the sampling; its double is also plausible: check the folded curve")
    return "; ".join(words)
