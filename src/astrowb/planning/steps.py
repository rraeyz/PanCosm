"""Planning as engine steps (worker processes: SIMBAD can be slow, the first ephemeris load too)."""

from dataclasses import asdict

import numpy as np
from astropy.coordinates import get_body

from ..engine.steps import step
from .targets import Resolver, Target, body_of
from .visibility import Site, airmass, altitudes, events, moon, night, night_grid, sun_altitude


@step("planning.resolve", inputs=("name", "cache_file"), outputs=("target",))
def resolve_step(inputs, params, ctx):
    return {"target": asdict(Resolver(inputs["cache_file"]).resolve(inputs["name"]))}


@step("planning.night", inputs=("site", "date", "targets"), outputs=("night",), min_alt=20.0, step_min=5.0)
def night_step(inputs, params, ctx):
    """targets: [{name, ra, dec, [t0, period, duration, secondary]}]; times in JD (UTC)."""
    site = Site(**inputs["site"])
    times = night_grid(site, inputs["date"], params["step_min"])
    dusk, dawn = night(site, inputs["date"])
    nautical = night(site, inputs["date"], "nautical")
    m = moon(times, site)
    out = {
        "jd": times.jd.tolist(),
        "sun_alt": sun_altitude(times, site).tolist(),
        "moon_alt": m["alt"].tolist(),
        "moon_illumination": float(np.mean(m["illumination"])),
        "dusk": dusk.jd if dusk else None,
        "dawn": dawn.jd if dawn else None,
        "nautical": [t.jd if t else None for t in nautical],
        "targets": [],
    }
    for i, t in enumerate(inputs["targets"]):
        ctx.progress(i / max(1, len(inputs["targets"])), t["name"])
        body = body_of(t["name"])
        coord = get_body(body, times, site.location) if body else Target(t["name"], t["ra"], t["dec"]).coord
        alt = altitudes(coord, times, site)
        sep = moon(times, site, coord)["separation"]
        entry = {
            "name": t["name"],
            "alt": alt.tolist(),
            "airmass": np.nan_to_num(airmass(alt), nan=-1).tolist(),
            "moon_sep_min": float(np.min(sep)),
            "events": [],
            "body": body,
        }
        if t.get("t0") and t.get("period") and not body:
            target = Target(t["name"], t["ra"], t["dec"])
            for e in events(
                t["t0"],
                t["period"],
                target.coord,
                site,
                dusk,
                dawn,
                t.get("duration"),
                t.get("secondary", False),
                params["min_alt"],
            ):
                entry["events"].append(
                    {
                        "kind": e.kind,
                        "mid": e.mid.jd,
                        "start": e.start.jd if e.start else None,
                        "end": e.end.jd if e.end else None,
                        "alt_mid": e.alt_mid,
                        "full": e.fully_observable,
                    }
                )
        out["targets"].append(entry)
    return {"night": out}


@step("planning.ephemeris", inputs=("name",), outputs=("target",), catalogue="auto")
def ephemeris_step(inputs, params, ctx):
    """Coordinates, period, epoch and duration from VSX or the NASA Exoplanet Archive."""
    from .ephemerides import lookup

    ctx.progress(0.0, "catalogue")
    return {"target": lookup(inputs["name"], params["catalogue"])}
