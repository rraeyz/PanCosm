"""Convergence diagnostics of Vehtari et al. 2021 (Bayesian Analysis 16, 667), written from the paper: the
rank-normalised split-R̂ (the larger of the bulk and the folded version) and the bulk and tail effective sample
sizes, with the multi-chain autocorrelation and Geyer's initial monotone sequence. draws: (chains, n)."""

import numpy as np
from scipy import special


def _split(draws):
    n = draws.shape[1] // 2
    return np.concatenate([draws[:, :n], draws[:, -n:]], axis=0)


def _rank_normal(draws):
    flat = draws.ravel()
    ranks = np.empty(flat.size)
    ranks[np.argsort(flat, kind="mergesort")] = np.arange(1, flat.size + 1)
    z = np.sqrt(2) * special.erfinv(2 * (ranks - 0.375) / (flat.size + 0.25) - 1)
    return z.reshape(draws.shape)


def _rhat(draws):
    n = draws.shape[1]
    w = np.mean(np.var(draws, axis=1, ddof=1))
    b = n * np.var(np.mean(draws, axis=1), ddof=1)
    return float(np.sqrt(((n - 1) / n * w + b / n) / w)) if w > 0 else np.inf


def rhat(draws):
    """The rank-normalised split-R̂ of one parameter."""
    s = _split(np.asarray(draws, float))
    folded = np.abs(s - np.median(s))
    return max(_rhat(_rank_normal(s)), _rhat(_rank_normal(folded)))


def _ess(draws):
    m, n = draws.shape
    if n < 4:
        return 0.0
    x = draws - draws.mean(axis=1, keepdims=True)
    size = 1 << int(np.ceil(np.log2(2 * n)))
    f = np.fft.rfft(x, size, axis=1)
    acov = np.fft.irfft(f * np.conj(f), size, axis=1)[:, :n] / n
    chain_var = acov[:, 0] * n / (n - 1)
    w = chain_var.mean()
    var_plus = w * (n - 1) / n + (np.var(draws.mean(axis=1), ddof=1) if m > 1 else 0.0)
    if var_plus <= 0:
        return 0.0
    rho = 1 - (w - acov.mean(axis=0)) / var_plus
    rho[0] = 1.0
    pairs = rho[: (n // 2) * 2].reshape(-1, 2).sum(axis=1)  # Geyer: sums of adjacent pairs
    positive = np.flatnonzero(pairs <= 0)
    pairs = pairs[: positive[0]] if positive.size else pairs
    pairs = np.minimum.accumulate(pairs)  # monotone
    tau = -1 + 2 * pairs.sum()
    return float(m * n / max(tau, 1.0 / np.log10(m * n)))


def ess_bulk(draws):
    return _ess(_rank_normal(_split(np.asarray(draws, float))))


def ess_tail(draws):
    s = _split(np.asarray(draws, float))
    q05, q95 = np.quantile(s, [0.05, 0.95])
    return min(_ess((s <= q05).astype(float)), _ess((s <= q95).astype(float)))


def burn_in(log_prob):
    """EXOFAST's rule: the first step at which every chain has reached the median log-probability of the last
    quarter. log_prob: (steps, chains)."""
    steps = log_prob.shape[0]
    target = np.median(log_prob[-max(steps // 4, 1) :])
    reached = log_prob >= target
    first = np.where(reached.any(axis=0), reached.argmax(axis=0), steps)
    return int(first.max())
