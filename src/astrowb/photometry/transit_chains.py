"""The chains an MCMC transit fit keeps for the Chains / Corner / Report views (UI-16.7): plain lists, thinned, with
the convergence numbers per parameter."""

import numpy as np

from ..core.inference import diagnostics

MAX_DRAWS = 2000  # in total over walkers: the project log stores the result as JSON


def chain_summary(post):
    """{"names", "chains": [walker][draw][param] (burn-in removed, thinned), "rhat", "ess_bulk": {name: float}}."""
    kept = post.chains[post.burn :]  # (draws, walkers, params)
    thin = max(1, -(-kept.shape[0] * kept.shape[1] // MAX_DRAWS))
    diag = post.diagnostics
    if diag is None:  # too few draws for the run's own check: from the full chains
        diag = {n: (diagnostics.rhat(kept[:, :, j].T), diagnostics.ess_bulk(kept[:, :, j].T))
                for j, n in enumerate(post.names)}  # fmt: skip
    return {"names": list(post.names), "chains": np.swapaxes(kept[::thin], 0, 1).tolist(),
            "rhat": {n: float(diag[n][0]) for n in post.names},
            "ess_bulk": {n: float(diag[n][1]) for n in post.names}}  # fmt: skip
