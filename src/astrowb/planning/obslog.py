"""The observing log from the frames themselves (plans/planning.md PLN-13): per night and target, when it was
observed, in which filters, how many frames and how much exposure, the airmass range, and whether a predicted event
was caught whole, its ingress only or its egress only.

    rows = frames_from_headers([(path, header), ...])
    log = night_log(rows)                        [{night, target, start, end, filters, frames, exposure_s, airmass}]
    caught = coverage(span_start, span_end, event_start, event_end)   "whole" | "ingress" | "egress" | "middle" | None
    stats = statistics(log)                      hours per month and per target, nights observed

A night is named by its evening's date at the site's longitude (an observation at 02:00 belongs to the night that
began the evening before), so a night never splits at midnight UTC.
"""

from collections import defaultdict

import numpy as np


def _night_of(jd, lon=0.0):
    """The evening date of the night holding jd (UTC) at longitude lon: local solar noon to noon."""
    from astropy.time import Time

    return Time(np.floor(jd + lon / 360.0), format="jd").iso[:10]  # a JD day starts at noon: here at local noon


def frames_from_headers(items, lon=None):
    """[{path, target, jd (mid-exposure, UTC), exptime, filter, airmass, night}] from (path, FITS header) pairs."""
    from .. import timing
    from ..hdr import get

    rows = []
    for path, h in items:
        try:
            t = timing.mid_time(h).utc.jd
        except (KeyError, ValueError):
            continue  # a frame without its time cannot be placed in a night
        site_lon = lon if lon is not None else float(get(h, "SITELONG", "LONG-OBS", "OBSGEO-L", default=0.0) or 0.0)
        rows.append({"path": str(path), "target": str(h.get("OBJECT", "") or "?").strip(), "jd": float(t),
                     "exptime": float(get(h, "EXPTIME", "EXPOSURE", default=0.0) or 0.0),
                     "filter": str(h.get("FILTER", "") or "none").strip(),
                     "airmass": get(h, "AIRMASS", default=None), "night": _night_of(t, site_lon)})  # fmt: skip
    return sorted(rows, key=lambda r: r["jd"])


def night_log(rows, gap_hours=1.0):
    """One line per night, target and continuous span (a pause longer than gap_hours starts a new span)."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["night"], r["target"])].append(r)
    out = []
    for (night, target), frames in sorted(groups.items()):
        frames.sort(key=lambda r: r["jd"])
        span = [frames[0]]
        for prev, r in zip(frames, frames[1:], strict=False):
            if (r["jd"] - prev["jd"]) * 24 > gap_hours:
                out.append(_line(night, target, span))
                span = []
            span.append(r)
        out.append(_line(night, target, span))
    return out


def _line(night, target, span):
    am = [float(r["airmass"]) for r in span if r["airmass"] not in (None, "")]
    return {"night": night, "target": target, "start": span[0]["jd"] - span[0]["exptime"] / 172800,
            "end": span[-1]["jd"] + span[-1]["exptime"] / 172800, "filters": sorted({r["filter"] for r in span}),
            "frames": len(span), "exposure_s": float(sum(r["exptime"] for r in span)),
            "airmass": (min(am), max(am)) if am else None}  # fmt: skip


def coverage(start, end, ev_start, ev_end):
    """How much of an event (ev_start … ev_end) a span covered: "whole", "ingress", "egress", "middle" or None."""
    if end <= ev_start or start >= ev_end:
        return None
    before, after = start <= ev_start, end >= ev_end
    if before and after:
        return "whole"
    if before:
        return "ingress"
    if after:
        return "egress"
    return "middle"


def statistics(log):
    """{"hours_per_month": {YYYY-MM: h}, "hours_per_target": {name: h}, "nights": n}."""
    month, target = defaultdict(float), defaultdict(float)
    for line in log:
        hours = (line["end"] - line["start"]) * 24
        month[line["night"][:7]] += hours
        target[line["target"]] += hours
    return {"hours_per_month": dict(month), "hours_per_target": dict(target),
            "nights": len({line["night"] for line in log})}  # fmt: skip


def to_csv(log, path):
    import csv

    from astropy.time import Time

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["night", "target", "start_utc", "end_utc", "filters", "frames", "exposure_s", "airmass_min",
                    "airmass_max"])  # fmt: skip
        for line in log:
            am = line["airmass"] or ("", "")
            w.writerow([line["night"], line["target"], Time(line["start"], format="jd").iso[:19],
                        Time(line["end"], format="jd").iso[:19], " ".join(line["filters"]), line["frames"],
                        f"{line['exposure_s']:.0f}", am[0], am[1]])  # fmt: skip
    return path
