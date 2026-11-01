"""Circular spots on the surface grids of models.roche_lc (plans/models.md MOD-8).

A spot is (colatitude, longitude, angular radius, temperature factor), angles in degrees, measured from the star's
own centre: colatitude from its rotation pole (+z), longitude from the line towards the companion, increasing in
the sense the orbit and the star turn (counter-clockwise seen from +z, as WD). A factor < 1 is a cool spot, > 1 hot.
Where spots overlap the factors multiply (rule "product", as WD) or the later spot wins (rule "later").

Each element is split into k × k sub-points, each in or out of each spot, so an element cut by a spot's edge takes
the share of its area inside (the curve stays smooth as the spot crosses the limb). The element's intensity is
scaled by the sub-point mean of I(T f) / I(T), I the normal intensity in the band as a function of temperature.
Spots turn with the star: at F ≠ 1 (or with a drift) their longitudes move with the cycle (longitude_at).
"""

import numpy as np

MAX_SPOTS = 8


def _sub_points(cells, k):
    """Unit vectors (n, k·k, 3) and area weights (n, k·k) of k × k sub-points of every cell (own frame)."""
    f = (np.arange(k) + 0.5) / k
    th = cells[:, 0, None, None] + (cells[:, 1] - cells[:, 0])[:, None, None] * f[:, None]
    ph = cells[:, 2, None, None] + (cells[:, 3] - cells[:, 2])[:, None, None] * f[None, :]
    th, ph = np.broadcast_to(th, (len(cells), k, k)), np.broadcast_to(ph, (len(cells), k, k))
    u = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], axis=-1)
    return u.reshape(len(cells), -1, 3), np.sin(th).reshape(len(cells), -1)


def factors(star, spots, rule="product", k=6):
    """The temperature factor at every sub-point (n, k·k) and the sub-points' weights (n, k·k)."""
    if len(spots) > MAX_SPOTS:
        raise ValueError(f"at most {MAX_SPOTS} spots per star")
    if rule not in ("product", "later"):
        raise ValueError(f"unknown spot overlap rule: {rule}")
    u, w = _sub_points(star["cells"], k)
    out = np.ones(u.shape[:2])
    for colat, lon, radius, factor in spots:
        c, p = np.radians(colat), np.radians(lon)
        centre = np.array([np.sin(c) * np.cos(p), np.sin(c) * np.sin(p), np.cos(c)])
        inside = u @ centre > np.cos(np.radians(radius))
        out = np.where(inside, out * factor if rule == "product" else factor, out)
    return out, w


def spotted(star, spots, temperature, intensity_of_t=lambda t: t**4, rule="product", k=6):
    """A copy of the star with its elements' intensities scaled by its spots. temperature: a number or the
    elements' temperatures; intensity_of_t: the band's normal intensity of a temperature (default bolometric)."""
    if not spots:
        return star
    f, w = factors(star, spots, rule, k)
    t = np.broadcast_to(np.asarray(temperature, float), (len(f),))[:, None]
    ratio = np.sum(w * intensity_of_t(t * f), axis=1) / (np.sum(w, axis=1) * intensity_of_t(t[:, 0]))
    return {**star, "i0": star["i0"] * ratio}


def longitude_at(longitude, cycle, spin=1.0, drift=0.0):
    """A spot's longitude after cycle orbits: it turns with the star at F = spin times the orbital rate (relative
    to the line of centres, (F − 1) turns per orbit) plus a drift in degrees per cycle."""
    return (longitude + 360.0 * (spin - 1.0) * np.asarray(cycle, float) + drift * np.asarray(cycle, float)) % 360.0


def flux(phases, incl, star1, star2, spots=((), ()), temperature=(1.0, 1.0), intensity_of_t=lambda t: t**4,
         spin=(1.0, 1.0), drift=(0.0, 0.0), rule="product", k=6, lc_k=5):  # fmt: skip
    """roche_lc.flux with spots; the phases count cycles (phase 1.3 is cycle 1, phase 0.3), so asynchronous spots
    move between cycles."""
    from . import roche_lc

    def both(sets):
        pairs = zip((star1, star2), sets, temperature, strict=True)
        return [spotted(s, sp, t, intensity_of_t, rule, k) for s, sp, t in pairs]

    static = all(s == 1.0 for s in spin) and all(d == 0.0 for d in drift)
    stars = both(spots)
    out = []
    for ph in np.atleast_1d(np.asarray(phases, float)):
        if not static:
            stars = both([[(c, longitude_at(lon, ph, f, d), r, x) for c, lon, r, x in sp]
                          for sp, f, d in zip(spots, spin, drift, strict=True)])  # fmt: skip
        out.append(roche_lc.flux([ph], incl, *stars, k=lc_k)[0])
    return np.array(out)
