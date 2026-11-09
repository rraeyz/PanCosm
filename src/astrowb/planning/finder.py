"""What can I observe tonight? (plans/planning.md PLN-5): every star of an ephemeris table whose event (an eclipse
minimum, a transit) falls in tonight's dark hours high enough, ranked.

    found = tonight_events(table, site, "2026-11-14", min_alt=30, ...)

table: columns name, ra, dec, mag, period, t0 (BJD_TDB; HJD accepted as it is to a few seconds), duration (days,
or NaN), kind ("EA", "EB", "EW", "transit", …), optional depth (mag), secondary (bool). The whole table is filtered
first by what needs no astronomy (magnitude, period, declination reachable from the site), then every event of
the night is found at once and its altitudes computed in one call — a VSX-sized table in seconds.
"""

import numpy as np

from .visibility import Site, night


def _arrays(table):
    cols = {k: np.asarray(v) for k, v in table.items()}
    n = len(cols["name"])
    for k, default in (("duration", np.nan), ("depth", np.nan), ("mag", np.nan), ("secondary", False)):
        cols.setdefault(k, np.full(n, default))
    cols.setdefault("kind", np.full(n, ""))
    return cols, n


def tonight_events(table, site: Site, date, min_alt=30.0, mag_range=(-5.0, 99.0), period_range=(0.0, 1e9),
                   kinds=None, min_depth=0.0, whole=True, secondary=True, max_events=500):  # fmt: skip
    """[{name, kind, which (primary / secondary), mid, start, end (JD UTC), alt_mid, alt_start, alt_end, mag, depth,
    period, score, why}] best first. whole: the event from start to end in darkness and above min_alt (when the
    duration is known); else only the middle has to be."""
    import astropy.units as u
    from astropy.coordinates import AltAz, SkyCoord
    from astropy.time import Time

    dusk, dawn = night(site, date)
    if dusk is None or dawn is None:
        return []
    c, n = _arrays(table)
    mag, period, dec = c["mag"].astype(float), c["period"].astype(float), c["dec"].astype(float)
    keep = np.isnan(mag) | ((mag >= mag_range[0]) & (mag <= mag_range[1]))
    keep &= (period >= period_range[0]) & (period <= period_range[1]) & (period > 0)
    keep &= 90 - np.abs(site.lat - dec) >= min_alt  # it never rises high enough here
    if kinds:
        keep &= np.isin(c["kind"], list(kinds))
    if min_depth:
        keep &= np.nan_to_num(c["depth"].astype(float), nan=np.inf) >= min_depth
    idx = np.flatnonzero(keep)
    lo, hi = dusk.utc.jd, dawn.utc.jd
    rows = []
    for shift, which in ((0.0, "primary"), (0.5, "secondary")):
        if shift and not secondary:
            continue
        sub = idx if not shift else idx[c["secondary"][idx].astype(bool) | np.isin(c["kind"][idx], ["EB", "EW"])]
        p, t0 = period[sub], c["t0"][sub].astype(float)
        first = np.ceil((lo - t0) / p - shift)
        count = np.floor((hi - t0) / p - shift) - first + 1  # events of the night (a short period: several)
        for k in range(int(np.nanmax(count, initial=0))):
            on = count > k
            mids = t0[on] + (first[on] + k + shift) * p[on]
            rows += [(int(j), which, m) for j, m in zip(sub[on], mids, strict=True)]
    if not rows:
        return []
    j = np.array([r[0] for r in rows])
    mid = np.array([r[2] for r in rows])
    half = np.nan_to_num(c["duration"][j].astype(float), nan=0.0) / 2
    times = Time(np.concatenate([mid - half, mid, mid + half]), format="jd", scale="utc")
    coords = SkyCoord(np.tile(c["ra"][j].astype(float), 3) * u.deg, np.tile(dec[j], 3) * u.deg)
    alt = coords.transform_to(AltAz(obstime=times, location=site.location)).alt.deg.reshape(3, -1)
    inside = (mid - half >= lo) & (mid + half <= hi) if whole else (mid >= lo) & (mid <= hi)
    high = (alt.min(axis=0) >= min_alt) if whole else (alt[1] >= min_alt)
    ok = inside & high
    out = []
    for r in np.flatnonzero(ok):
        jj = j[r]
        score = float(np.clip((alt[:, r].min() - min_alt) / (90 - min_alt), 0, 1))
        score *= 0.85 if rows[r][1] == "secondary" else 1.0  # a primary minimum first
        out.append({"name": str(c["name"][jj]), "kind": str(c["kind"][jj]), "which": rows[r][1], "mid": float(mid[r]),
                    "start": float(mid[r] - half[r]) if half[r] else None,
                    "end": float(mid[r] + half[r]) if half[r] else None, "alt_mid": float(alt[1, r]),
                    "alt_start": float(alt[0, r]), "alt_end": float(alt[2, r]), "mag": float(mag[jj]),
                    "depth": float(c["depth"][jj]), "period": float(period[jj]), "score": score,
                    "why": f"lowest {alt[:, r].min():.0f}° during the event"})  # fmt: skip
    out.sort(key=lambda e: (-e["score"], e["mid"]))
    return out[:max_events]
