"""Measuring the camera from its own frames (plans/calibration.md CAL-9):

gain_read_noise(flat1, flat2, bias1, bias2)   Janesick's two-flats-two-biases (IRAF findgain):
    g  = [(F̄1 + F̄2) − (B̄1 + B̄2)] / [σ²(F1 − F2) − σ²(B1 − B2)]   (e⁻ / ADU)
    RN = g · σ(B1 − B2) / √2                                        (e⁻)
  in boxes over the frame: the median and the scatter of the estimates (a dust mote or a gradient in one box
  does not decide it)
photon_transfer(pairs, bias1, bias2)          variance against mean over flat pairs at many levels: the gain from
  the straight part, and full well where the variance stops rising (the curve turns over)
linearity(exptimes, means)                    signal against exposure time: the polynomial correction the
  program uses (masters.linearity's form, true = c0·m + c1·m² + …) and where the deviation passes 1 %
shutter_offset(exptimes, means)               the effective exposure is t + δ: δ from short and long flats
"""

import numpy as np


def _boxes(shape, size):
    ny, nx = shape
    for y in range(0, ny - size + 1, size):
        for x in range(0, nx - size + 1, size):
            yield slice(y, y + size), slice(x, x + size)


def _clipped_var(x):
    x = np.asarray(x, float).ravel()
    med = np.median(x)
    s = 1.4826 * np.median(np.abs(x - med))
    keep = np.abs(x - med) < 5 * s  # a cosmic ray or a hot pixel does not count
    return float(np.var(x[keep], ddof=1))


def gain_read_noise(flat1, flat2, bias1, bias2, box=100):
    """{"gain", "gain_err", "read_noise", "read_noise_err", "boxes"}: per box, then median and robust scatter."""
    f1, f2, b1, b2 = (np.asarray(a, float) for a in (flat1, flat2, bias1, bias2))
    gains, noises = [], []
    for sl in _boxes(f1.shape, box):
        signal = (f1[sl].mean() + f2[sl].mean()) - (b1[sl].mean() + b2[sl].mean())
        var_f, var_b = _clipped_var(f1[sl] - f2[sl]), _clipped_var(b1[sl] - b2[sl])
        if var_f <= var_b or signal <= 0:
            continue
        g = signal / (var_f - var_b)
        gains.append(g)
        noises.append(g * np.sqrt(var_b) / np.sqrt(2))
    gains, noises = np.array(gains), np.array(noises)
    if not len(gains):
        raise ValueError("the flats are no brighter than the biases: the gain cannot be measured")

    def spread(v):
        return float(1.4826 * np.median(np.abs(v - np.median(v))) / np.sqrt(len(v)))

    return {"gain": float(np.median(gains)), "gain_err": spread(gains), "read_noise": float(np.median(noises)),
            "read_noise_err": spread(noises), "boxes": len(gains)}  # fmt: skip


def photon_transfer(pairs, bias1, bias2, region=None):
    """pairs: [(flat_a, flat_b)] at increasing levels. {"mean", "variance" (ADU, per pair), "gain" (from the straight
    part, e⁻/ADU), "full_well" (ADU, where the variance turns over, or None)}."""
    b1, b2 = (np.asarray(a, float) for a in (bias1, bias2))
    sl = region or (slice(None), slice(None))
    bias_var = _clipped_var(b1[sl] - b2[sl]) / 2
    level = (b1[sl].mean() + b2[sl].mean()) / 2
    means, variances = [], []
    for a, b in pairs:
        a, b = np.asarray(a, float)[sl], np.asarray(b, float)[sl]
        means.append((a.mean() + b.mean()) / 2 - level)
        variances.append(_clipped_var(a - b) / 2 - bias_var)
    means, variances = np.array(means), np.array(variances)
    peak = int(np.argmax(variances))
    full = float(means[peak]) if peak < len(means) - 1 else None  # still rising at the last pair: not reached
    use = slice(0, max(3, int(0.7 * (peak + 1))))  # the straight part, well below the turn-over
    slope = np.polyfit(means[use], variances[use], 1)[0]
    return {"mean": means.tolist(), "variance": variances.tolist(), "gain": float(1 / slope), "full_well": full}


def linearity(exptimes, means, degree=2, low_fraction=0.3):
    """{"coefficients" (c0, c1, …: true = Σ cₖ m^(k+1)), "limit_1pct" (ADU, or None), "deviation" (per point)}: the
    straight line through the low levels (below low_fraction of the highest) is the truth; the correction maps the
    measured means onto it."""
    t, m = np.asarray(exptimes, float), np.asarray(means, float)
    low = m <= low_fraction * m.max()
    rate = np.polyfit(t[low], m[low], 1)
    true = np.polyval(rate, t)
    deviation = m / true - 1
    powers = np.column_stack([m ** (k + 1) for k in range(degree)])
    coef, *_ = np.linalg.lstsq(powers, true, rcond=None)
    over = np.flatnonzero(np.abs(deviation) > 0.01)
    limit = None
    if len(over) and over[0] > 0:  # between the last point within 1 % and the first beyond it
        j = over[0]
        a, b = abs(deviation[j - 1]), abs(deviation[j])
        limit = float(m[j - 1] + (m[j] - m[j - 1]) * (0.01 - a) / (b - a))
    elif len(over):
        limit = float(m[over[0]])
    return {"coefficients": coef.tolist(), "limit_1pct": limit,
            "deviation": deviation.tolist()}  # fmt: skip


def shutter_offset(exptimes, means):
    """δ (seconds) with mean ∝ (t + δ): the intercept of the signal against time over its slope."""
    slope, intercept = np.polyfit(np.asarray(exptimes, float), np.asarray(means, float), 1)
    return float(intercept / slope)
