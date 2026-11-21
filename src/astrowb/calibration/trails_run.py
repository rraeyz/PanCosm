"""The trail search on the calibrated lights (plans/calibration.md CAL-12): an option of the run, found and flagged
in the DQ plane (TRAIL bit), never repaired."""

from . import trails


def search(plane, params, name):
    """(record, band mask) of the light's strongest trail, or (None, None) when the option is off or none stands
    out. The record is JSON-serialisable: the file, the angle (deg from +x), offset, width and significance."""
    if not params.get("find_trails"):
        return None, None
    t = trails.find(plane)
    if t is None:
        return None, None
    return {"file": name} | {k: float(v) for k, v in t.items()}, trails.band(plane.shape, t)
