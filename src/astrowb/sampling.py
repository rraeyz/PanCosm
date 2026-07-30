"""Random draws from a fit's covariance, used for the errors of derived quantities."""

import numpy as np


def draws(mean, cov, n, seed=0):
    """n samples of N(mean, cov). A covariance from (J^T J)^-1 is symmetric and positive semi-definite in exact
    arithmetic; rounding (near-degenerate fits, e.g. e ~ 0 where omega is undefined) can leave it slightly
    asymmetric or with tiny negative eigenvalues, which would distort the draws. Those are removed first; a valid
    covariance is unchanged."""
    cov = np.asarray(cov, float)
    w, v = np.linalg.eigh(0.5 * (cov + cov.T))
    clean = (v * np.clip(w, 0, None)) @ v.T
    return np.random.default_rng(seed).multivariate_normal(np.asarray(mean, float), clean, n, method="eigh")
