"""The q-search and other scans (plans/models.md MOD-13): one parameter (or two) held on a grid, all the other
free ones fitted at each value warm-started from the neighbour; χ² against the grid with the minimum (a parabola
through the lowest three points), its 1σ range where χ² rises by χ²ᵣ (Δχ² = 1 after scaling to χ²ᵣ = 1), and a
verdict on how sharply the data decide the parameter."""

import numpy as np

from . import fitting


def scan(system, model, key, grid, optimiser="lm", weights="errors"):
    """{"grid", "chi2", "best", "low", "high", "depth" (χ² rise across the grid in units of χ²ᵣ), "verdict"}."""
    free = [k for k in system.free() if k != key]
    keep = system.params[key].free
    system.params[key].free = False
    start = {k: p.value for k, p in system.params.items()}
    chi = []
    try:
        for v in grid:
            system.params[key].value = float(v)
            system.apply()
            chi.append(fitting.fit(system, model, optimiser, free, weights).chi2_after)
    finally:
        system.params[key].free = keep
    chi = np.array(chi)
    n = sum(len(d.time) for d in system.data)
    s = max(chi.min() / max(n - len(free) - 1, 1), 1.0)
    rel = (chi - chi.min()) / s
    i = int(np.argmin(chi))
    best = float(grid[i])
    if 0 < i < len(grid) - 1:
        x, y = np.asarray(grid[i - 1 : i + 2], float), rel[i - 1 : i + 2]
        c = np.polyfit(x, y, 2)
        if c[0] > 0:
            best = float(-c[1] / (2 * c[0]))
    inside = np.flatnonzero(rel <= 1.0)
    low, high = float(grid[inside.min()]), float(grid[inside.max()])
    depth = float(rel.max())
    verdict = "sharp" if depth > 25 and (high - low) < 0.2 * np.ptp(grid) else "shallow"
    for k, v in start.items():  # the system back where it was, the best value of the scanned one set
        system.params[k].value = v
    system.params[key].value = best
    system.apply()
    return {"grid": np.asarray(grid, float), "chi2": chi, "best": best, "low": low, "high": high, "depth": depth,
            "verdict": verdict}  # fmt: skip


def scan2(system, model, keys, grids, optimiser="lm", weights="errors"):
    """A χ² map over two parameters (rows: the first key's grid)."""
    a, b = keys
    free = [k for k in system.free() if k not in keys]
    flags = (system.params[a].free, system.params[b].free)
    system.params[a].free = system.params[b].free = False
    start = {k: p.value for k, p in system.params.items()}
    out = np.empty((len(grids[0]), len(grids[1])))
    try:
        for i, va in enumerate(grids[0]):
            for j, vb in enumerate(grids[1]):
                system.params[a].value, system.params[b].value = float(va), float(vb)
                system.apply()
                out[i, j] = fitting.fit(system, model, optimiser, free, weights).chi2_after
    finally:
        system.params[a].free, system.params[b].free = flags
        for k, v in start.items():
            system.params[k].value = v
        system.apply()
    return out
