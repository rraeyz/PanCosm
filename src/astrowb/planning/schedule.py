"""A night's observing schedule for several targets, from the planning result (altitudes on a time grid,
dusk, dawn, predicted eclipses and transits).

1. Time-critical events first: each observable eclipse / transit gets its window plus a baseline before and
   after; when two overlap, the target higher in the list wins.
2. The free time is filled in blocks: in each block the target that stays highest (lowest airmass) above the
   altitude limit for the whole block is observed; neighbouring blocks of one target are merged.
"""

import numpy as np


def schedule(night, targets, min_alt=30.0, block_min=60.0, baseline_min=30.0):
    """night: the planning.night result; targets: the same list (with ra, dec), in priority order.
    Returns [{name, ra, dec, start, end (JD UTC), why: "event" | "best altitude"}] in time order."""
    jd = np.asarray(night["jd"])
    if not night.get("dusk") or not night.get("dawn"):
        return []
    dark = (jd >= night["dusk"]) & (jd <= night["dawn"])
    step = float(np.median(np.diff(jd)))
    taken = np.zeros(len(jd), bool)
    blocks = []
    by_name = {t["name"]: t for t in targets}
    rank = {t["name"]: i for i, t in enumerate(targets)}
    entries = sorted(night["targets"], key=lambda e: rank.get(e["name"], len(rank)))
    for entry in entries:  # 1. events, in priority order
        for e in entry["events"]:
            if not e["full"]:
                continue
            lo = (e["start"] or e["mid"]) - baseline_min / 1440
            hi = (e["end"] or e["mid"]) + baseline_min / 1440
            window = (jd >= lo) & (jd <= hi) & dark
            if window.any() and not (taken & window).any():
                taken |= window
                blocks.append(_block(by_name[entry["name"]], jd[window][0], jd[window][-1] + step, "event"))
    n_block = max(1, int(round(block_min / 1440 / step)))
    alts = [np.asarray(e["alt"]) for e in entries]
    free = np.flatnonzero(dark & ~taken)
    i, last = 0, None
    while i < len(free):  # 2. fill the gaps
        run = [free[i]]
        while i + 1 < len(free) and free[i + 1] == free[i] + 1 and len(run) < n_block:
            i += 1
            run.append(free[i])
        i += 1
        best, best_alt = None, min_alt
        for entry, all_alt in zip(entries, alts, strict=True):
            alt = all_alt[run]
            if alt.min() >= min_alt and alt.mean() > best_alt:
                best, best_alt = entry, alt.mean()
        if best is None:
            continue
        start, end = jd[run[0]], jd[run[-1]] + step
        if last and last["name"] == best["name"] and abs(last["end"] - start) < step / 2:
            last["end"] = float(end)  # the same target goes on
            continue
        last = _block(by_name[best["name"]], start, end, "best altitude")
        blocks.append(last)
    return sorted(blocks, key=lambda b: b["start"])


def _block(target, start, end, why):
    return {
        "name": target["name"],
        "ra": target["ra"],
        "dec": target["dec"],
        "start": float(start),
        "end": float(end),
        "why": why,
    }
