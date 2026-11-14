"""Many nights in one run (plans/calibration.md CAL-19): the frames of a folder tree split by night (the evening's
date), each night calibrated into its own folder with its own bias / darks / flats — a kind a night lacks is
borrowed from the nearest night that has it, and said — and one summary for all.

    by_night = split(frames)                   {night: [frame dicts]}
    report = run(frames, output_dir, params)   [{night, lights, masters, borrowed, calibrated, problems}]
"""

from collections import defaultdict
from pathlib import Path


def _night(frame):
    from astropy.time import Time

    from ..planning.obslog import _night_of

    date = frame.get("date_obs")
    if not date:
        return None
    try:
        return _night_of(Time(str(date)[:23], format="isot", scale="utc").jd, 0.0)
    except ValueError:
        return None


def split(frames):
    """{night: frames}; frames without a date go to the night whose lights are most numerous (one guess, said in
    the run's report as 'undated')."""
    nights = defaultdict(list)
    undated = []
    for f in frames:
        n = _night(f)
        (nights[n] if n else undated).append(f)
    if undated and nights:
        main = max(nights, key=lambda k: sum(1 for f in nights[k] if f["kind"] == "light"))
        nights[main] += undated
    elif undated:
        nights["undated"] = undated
    return dict(sorted(nights.items()))


def _days(a, b):
    from datetime import date

    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return 10**6


def run(frames, output_dir, params=None, ctx=None):
    """Calibrate every night; [per-night summary]."""
    from ..engine.steps import execute

    groups = split(frames)
    report = []
    for night, own in groups.items():
        lights = [f for f in own if f["kind"] == "light"]
        if not lights:
            continue
        use, borrowed = list(own), []
        for kind in ("bias", "dark", "flat"):
            if any(f["kind"] == kind for f in own):
                continue
            donors = [n for n, fs in groups.items() if n != night and any(f["kind"] == kind for f in fs)]
            if donors:
                donor = min(donors, key=lambda n: _days(n, night))
                use += [f for f in groups[donor] if f["kind"] == kind]
                borrowed.append({"kind": kind, "from": donor})
        out = execute("calibration.run", {"frames": use, "output_dir": str(Path(output_dir) / night)}, params or {},
                      ctx)  # fmt: skip
        report.append({"night": night, "lights": len(lights), "masters": [Path(p).name for p in out["masters"]],
                       "borrowed": borrowed, "calibrated": len(out["calibrated"]),
                       "problems": len(out.get("missing") or []) + len(out.get("failed_masters") or [])})  # fmt: skip
    return report
