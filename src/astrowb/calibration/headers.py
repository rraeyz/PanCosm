"""Edit the headers of many frames at once (plans/calibration.md CAL-23; IRAF hedit / setjd / setairmass,
AstroImageJ's header updates): set, rename or delete keywords by rule, and write the keywords computed from the
time, the site and the target — after a preview, into copies unless asked otherwise.

    rules = {"set": {"OBJECT": "NY Vir"}, "rename": {"OBJCTRA": "RA_OBJ"}, "delete": ["HISTORY"],
             "target": {"name": "NY Vir", "ra": 204.70, "dec": -2.03},        # degrees
             "site": {"lat": 36.82, "lon": 30.34, "height": 2500},          # when the header has none
             "computed": ["DATE-AVG", "JD_UTC", "HJD_UTC", "BJD_TDB", "AIRMASS", "ALT", "AZ"],
             "clock_offset_s": 0.0}                                         # the camera's clock error, added
    rows = preview(paths, rules)            [{"file", "key", "old", "new"}]
    written = apply(paths, rules, out_dir)  copies in out_dir; in place only with in_place=True
"""

from pathlib import Path

import numpy as np

COMPUTED = ("DATE-AVG", "JD_UTC", "HJD_UTC", "BJD_TDB", "AIRMASS", "ALT", "AZ")


def _target(rules, header):
    from astropy.coordinates import SkyCoord

    t = rules.get("target") or {}
    if t.get("ra") is not None and t.get("dec") is not None:
        return SkyCoord(float(t["ra"]), float(t["dec"]), unit="deg")
    from ..photometry.lightcurve import target_coord

    return target_coord(header)


def _site(rules, header):
    from astropy import units as u
    from astropy.coordinates import EarthLocation

    from .. import timing

    s = rules.get("site")
    if s:
        return EarthLocation.from_geodetic(float(s["lon"]) * u.deg, float(s["lat"]) * u.deg,
                                           float(s.get("height", 0.0)) * u.m)  # fmt: skip
    return timing.location(header)


def new_values(header, rules):
    """{key: value or None (delete)} that the rules give for this header; computed keywords need the time and, for
    HJD / BJD / AIRMASS / ALT / AZ, the target and the site (left out when unknown)."""
    import astropy.units as u
    from astropy.coordinates import AltAz

    from .. import timing

    out = {k: v for k, v in (rules.get("set") or {}).items()}
    for old, new in (rules.get("rename") or {}).items():
        if old in header:
            out[new], out[old] = header[old], None
    for key in rules.get("delete") or ():
        out[key] = None
    wanted = [k for k in rules.get("computed") or () if k in COMPUTED]
    if not wanted:
        return out
    mid = timing.mid_time(header) + float(rules.get("clock_offset_s", 0.0)) * u.s
    out["DATE-AVG"] = mid.utc.isot if "DATE-AVG" in wanted else out.get("DATE-AVG")
    if "JD_UTC" in wanted:
        out["JD_UTC"] = round(float(mid.utc.jd), 9)
    target, where = _target(rules, header), _site(rules, header)
    if target is not None and ("HJD_UTC" in wanted or "BJD_TDB" in wanted):
        if "HJD_UTC" in wanted:
            out["HJD_UTC"] = round(float(timing.hjd(mid, target, where).jd), 9)
        if "BJD_TDB" in wanted:
            out["BJD_TDB"] = round(float(timing.bjd_tdb(mid, target, where).jd), 9)
    if target is not None and where is not None and {"AIRMASS", "ALT", "AZ"} & set(wanted):
        aa = target.transform_to(AltAz(obstime=mid, location=where))
        if "AIRMASS" in wanted:
            out["AIRMASS"] = round(float(timing.airmass(mid, target, where)), 5)
        if "ALT" in wanted:
            out["ALT"] = round(float(aa.alt.deg), 4)
        if "AZ" in wanted:
            out["AZ"] = round(float(aa.az.deg), 4)
    return {k: v for k, v in out.items() if not (k == "DATE-AVG" and v is None and "DATE-AVG" not in wanted)}


def preview(paths, rules):
    """[{"file", "key", "old", "new"}] of every change the rules would make (nothing written)."""
    from astropy.io import fits

    rows = []
    for p in paths:
        h = fits.getheader(p)
        for key, value in new_values(h, rules).items():
            old = h.get(key)
            if value is None and key not in h:
                continue
            if value is not None and old == value:
                continue
            rows.append({"file": Path(p).name, "key": key, "old": old, "new": value})
    return rows


def apply(paths, rules, out_dir=None, in_place=False):
    """Write the changes: into copies in out_dir (made when missing), or into the files themselves only when
    in_place is True. Returns the written paths. Each header records what changed (HISTORY)."""
    from astropy.io import fits

    if not in_place and out_dir is None:
        raise ValueError("give a folder for the copies, or allow writing into the files themselves")
    written = []
    for p in paths:
        target = Path(p) if in_place else Path(out_dir) / Path(p).name
        if not in_place:
            target.parent.mkdir(parents=True, exist_ok=True)
        with fits.open(p, memmap=False) as hdul:  # read whole, closed before writing (Windows locks open files)
            for hdu in hdul:
                _ = hdu.data
        h = hdul[0].header
        changed = new_values(h, rules)
        for key, value in changed.items():
            if value is None:
                h.remove(key, ignore_missing=True, remove_all=True)
            elif isinstance(value, float) and not np.isfinite(value):
                continue
            else:
                h[key] = value
        if changed:
            h.add_history(f"keywords edited: {', '.join(sorted(changed))[:60]}")
        hdul.writeto(target, overwrite=True)
        written.append(str(target))
    return written
