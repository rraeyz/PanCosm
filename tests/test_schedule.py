"""Night scheduler on a synthetic night: events first, then the highest target in each free block."""

import numpy as np

from astrowb.planning.schedule import schedule

STEP = 5 / 1440
JD = 2461000.5 + np.arange(0, 0.5, STEP)  # 12 hours in 5-minute steps
DUSK, DAWN = JD[12], JD[132]  # 1 h after the start to 1 h before the end


def target(name, peak_jd, events=()):
    alt = 80 - 200 * np.abs(JD - peak_jd)  # a target culminating at peak_jd, ~40 deg/2.4 h either side
    return {"name": name, "alt": alt.tolist(), "events": list(events)}


def night(*entries):
    return {"jd": JD.tolist(), "dusk": DUSK, "dawn": DAWN, "targets": list(entries)}


TARGETS = [{"name": n, "ra": i * 10.0, "dec": 20.0} for i, n in enumerate("ABC")]


def test_fill_follows_the_highest_target():
    n = night(target("A", JD[30]), target("B", JD[70]), target("C", JD[115]))
    plan = schedule(n, TARGETS, min_alt=30, block_min=60)
    names = [b["name"] for b in plan]
    assert names == ["A", "B", "C"]  # each target while it is the highest; neighbouring blocks merged
    assert plan[0]["start"] == DUSK and plan[-1]["end"] <= DAWN + STEP
    assert all(a["end"] <= b["start"] + 1e-9 for a, b in zip(plan, plan[1:], strict=False))  # no overlap


def test_events_first_and_priority_on_conflict():
    eclipse = {"mid": JD[60], "start": JD[54], "end": JD[66], "full": True}
    clash = {"mid": JD[62], "start": JD[57], "end": JD[68], "full": True}
    partial = {"mid": JD[100], "start": JD[95], "end": JD[105], "full": False}
    n = night(target("A", JD[30]), target("B", JD[100], [eclipse, partial]), target("C", JD[60], [clash]))
    plan = schedule(n, [TARGETS[1], TARGETS[0], TARGETS[2]], min_alt=30, baseline_min=30)  # B first
    events = [b for b in plan if b["why"] == "event"]
    assert [b["name"] for b in events] == ["B"]  # C's clashing transit loses; the partial one is skipped
    assert events[0]["start"] <= eclipse["start"] - 29 / 1440 and events[0]["end"] >= eclipse["end"] + 29 / 1440
    assert plan[0]["name"] == "A"  # the free time before the event goes to the highest target


def test_no_night():
    assert schedule({"jd": JD.tolist(), "dusk": None, "dawn": None, "targets": []}, []) == []
