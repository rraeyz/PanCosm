"""A night's observing schedule for several targets, from the planning result (altitudes on a time grid,
dusk, dawn, predicted eclipses and transits).

1. Time-critical events first: each observable eclipse / transit gets its window plus a baseline before and
   after; when two overlap, the target higher in the list wins.
2. The free time is filled in blocks: in each block the target that stays highest (lowest airmass) above the
   altitude limit for the whole block is observed; neighbouring blocks of one target are merged.
"""

import numpy as np


def schedule(night, targets, min_alt=30.0, block_min=60.0, baseline_min=30.0, conflicts=None):
    """night: the planning.night result; targets: the same list (with ra, dec), in priority order.
    Returns [{name, ra, dec, start, end (JD UTC), why: "event" | "best altitude"}] in time order. conflicts: a list
    that receives each event left out because a higher target's event holds its time ({name, mid, lost_to})."""
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
            elif window.any() and conflicts is not None:
                holder = next((b["name"] for b in blocks if b["why"] == "event" and b["start"] < hi and b["end"] > lo),
                              None)  # fmt: skip
                conflicts.append({"name": entry["name"], "mid": e["mid"], "lost_to": holder})
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


def plan(night, targets, min_alt=30.0, block_min=60.0, baseline_min=30.0, overheads=None):
    """The schedule with the night's real costs (plans/planning.md PLN-7): {"blocks", "conflicts", "totals"}.
    overheads (seconds, from the equipment profile): {"slew", "settle", "centre", "focus"}; at every change of
    target an "overhead" block of their sum is put in — taken from the end of a filler block before it, or from
    the start of the block after it when the one before is an event (an event's window is never cut).
    totals: {name: hours on target}, "idle" hours of dark time with nothing to do, "overhead" hours."""
    conflicts = []
    blocks = schedule(night, targets, min_alt, block_min, baseline_min, conflicts)
    cost = sum((overheads or {}).values()) / 86400
    out = []
    for b in blocks:
        b = dict(b)
        prev = out[-1] if out else None
        if cost and prev and prev["name"] != b["name"] and prev["why"] != "overhead":
            if prev["why"] != "event" and prev["end"] - prev["start"] > 2 * cost:
                at = prev["end"] = min(prev["end"], b["start"]) - cost
            elif b["why"] != "event" and b["end"] - b["start"] > 2 * cost:
                at = b["start"]
                b["start"] += cost
            else:
                at = None  # two events back to back: the overhead eats the baseline, said in the conflicts
                conflicts.append({"name": b["name"], "mid": b["start"], "lost_to": "overhead"})
            if at is not None:
                out.append({"name": b["name"], "ra": b["ra"], "dec": b["dec"], "start": float(at),
                            "end": float(at + cost), "why": "overhead"})  # fmt: skip
        out.append(b)
    totals = {}
    for b in out:
        key = "overhead" if b["why"] == "overhead" else b["name"]
        totals[key] = totals.get(key, 0.0) + (b["end"] - b["start"]) * 24
    dark = (night["dawn"] - night["dusk"]) * 24 if night.get("dusk") and night.get("dawn") else 0.0
    totals["idle"] = max(0.0, dark - sum(totals.values()))
    return {"blocks": sorted(out, key=lambda b: b["start"]), "conflicts": conflicts, "totals": totals}
