"""The light curve of two stars drawn as surface grids (plans/models.md MOD-3): each element's intensity, limb
darkening and projected area summed over what the observer sees; an element is hidden by its own horizon (μ ≤ 0)
or by the other star.

The eclipse test (MOD-3 item 1): the sight line from an element towards the observer is clear when it misses the
other star's circumscribed sphere or passes behind it, hidden when it enters the inscribed sphere; in between, the
other star's potential is followed along the line and the element is hidden where it rises above the surface
value. Elements near the other star's limb are split into k × k sub-elements and their visible share counted, so
the curve is smooth in the parameters (item 2). Frame: star 1 at the origin, star 2 at x = 1 (separation 1),
z along the orbital axis (the orbit turns about +z); at phase 0 the observer looks along +x tilted by the
inclination, star 2 in front; in this frame the observer turns the other way.
"""

import numpy as np

from ..occult.laws import intensity as limb
from . import roche


def _cells(n_theta):
    """(direction u, θ range, φ range, solid angle) of every element: θ rows, longitudes ∝ sin θ."""
    rows = []
    edges = np.linspace(0, np.pi, n_theta + 1)
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        n_phi = max(4, int(round(2 * n_theta * np.sin(0.5 * (a + b)))))
        dw = (np.cos(a) - np.cos(b)) * 2 * np.pi / n_phi
        for j in range(n_phi):
            rows.append((a, b, 2 * np.pi * j / n_phi, 2 * np.pi * (j + 1) / n_phi, dw))
    return np.array(rows)


def _moment(cells):
    """∫ u dω over each cell, exactly (u the unit vector): the projected area of a sphere's cell is r² (M · v)."""
    a, b, p, q = cells[:, 0], cells[:, 1], cells[:, 2], cells[:, 3]
    s2 = 0.5 * (b - a) - 0.25 * (np.sin(2 * b) - np.sin(2 * a))  # ∫ sin²θ dθ
    sc = 0.5 * (np.sin(b) ** 2 - np.sin(a) ** 2)  # ∫ sin θ cos θ dθ
    return np.column_stack([s2 * (np.sin(q) - np.sin(p)), s2 * (np.cos(p) - np.cos(q)), sc * (q - p)])


def _dirs(theta, phi):
    return np.stack([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)], axis=-1)


def star(radius, intensity, ld=("quadratic", (0.0, 0.0)), n_theta=40, second=False, roche_q=None, om=None):
    """One star's grid in the binary frame. radius: a number (a sphere) or None with roche_q and om (the Roche
    surface of potential om for mass ratio roche_q, in the star's own frame); intensity: a number or a function of
    the elements' gravity; second: the star at x = 1 (its own frame turned by 180° about z)."""
    cells = _cells(n_theta)
    th, ph = 0.5 * (cells[:, 0] + cells[:, 1]), 0.5 * (cells[:, 2] + cells[:, 3])
    u = _dirs(th, ph)
    if radius is not None:
        r = np.full(len(u), float(radius))
        normal, gravity = u, np.ones(len(u))
    else:
        r = np.array([roche.radius(om, roche_q, x, z, neck=True) for x, _y, z in u])
        g = np.array(roche.gradient(*(u * r[:, None]).T, roche_q))
        gravity = np.linalg.norm(g, axis=0)
        normal = -(g / gravity).T
    area = r * r * cells[:, 4] / np.clip(np.sum(u * normal, axis=1), 1e-6, None)
    # the projected area towards v is r²/(u·n) [(n − u)·v dω + M·v]: exact for a sphere (n = u), first order else
    moment = (normal - u) * cells[:, 4, None] + _moment(cells)
    scale = r * r / np.clip(np.sum(u * normal, axis=1), 1e-6, None)
    if radius is None:  # steep cells and a contact star's neck: measured piece by piece, the neck plane left dark
        dark = _fix_rim(cells, u, normal, gravity, r, roche_q, om, area, moment, scale)
    xyz = u * r[:, None]
    own_normal = normal  # in the star's own frame, for the sub-elements
    if second:  # turned by 180° about z and moved to x = 1
        xyz = xyz * [-1, -1, 1] + [1.0, 0, 0]
        normal = normal * [-1, -1, 1]
        moment = moment * [-1, -1, 1]
    i0 = intensity(gravity) if callable(intensity) else np.full(len(u), float(intensity))
    if radius is None:
        i0 = np.where(dark, 0.0, i0)
    return {
        "xyz": xyz, "normal": normal, "normal_own": own_normal, "area": area, "moment": moment, "scale": scale,
        "r": r, "cells": cells, "i0": i0, "ld": ld, "centre": np.array([1.0 if second else 0.0, 0, 0]),
        "r_min": r.min(), "r_max": r.max(), "second": second, "roche": (roche_q, om) if radius is None else None,
        "neck": roche.lagrange(roche_q)[0] if radius is None else np.inf,
    }  # fmt: skip


def _rim(cell, q, om, l1, m=6):
    """A cell the radial rays cross badly (nearly along the surface, or partly out through a contact star's neck):
    split into m × m sub-cells, each a quadrilateral of its corners on the surface; the sub-cells on the neck plane
    are dropped. Returns (area, area-weighted normal sum, centroid, mean gravity) of the rest, or None if none."""
    a, b, p, qq, _w = cell
    th, ph = np.linspace(a, b, m + 1), np.linspace(p, qq, m + 1)
    u = _dirs(*np.meshgrid(th, ph, indexing="ij"))
    pts = u * np.array([[roche.radius(om, q, x, z, neck=True) for x, _y, z in row] for row in u])[..., None]
    on_neck = pts[..., 0] >= l1 * (1 - 1e-9)
    total, moment, centroid, gravity = 0.0, np.zeros(3), np.zeros(3), 0.0
    for i in range(m):
        for j in range(m):
            if on_neck[i : i + 2, j : j + 2].all():
                continue
            c00, c10, c11, c01 = pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]
            area = 0.5 * np.linalg.norm(np.cross(c11 - c00, c01 - c10))
            mid = 0.25 * (c00 + c10 + c11 + c01)
            g = np.array(roche.gradient(*mid, q))
            total += area
            moment += -g / np.linalg.norm(g) * area
            centroid += mid * area
            gravity += np.linalg.norm(g) * area
    return None if total == 0 else (total, moment, centroid / total, gravity / total)


def _fix_rim(cells, u, normal, gravity, r, q, om, area, moment, scale, limit=0.5):
    """Where r̂ · n̂ < limit (the area r² dω / (r̂ · n̂) diverges) or the centre ray leaves through the neck, the
    cell is measured by _rim (arrays changed in place). Returns the cells left dark (wholly on the neck plane)."""
    l1 = roche.lagrange(q)[0]
    neck = u[:, 0] * r >= l1 * (1 - 1e-9)
    dark = np.zeros(len(u), bool)
    for i in np.flatnonzero(neck | (np.sum(u * normal, axis=1) < limit)):
        got = _rim(cells[i], q, om, l1)
        if got is None:
            dark[i], normal[i] = True, [1.0, 0, 0]
            continue
        area[i], moment[i], centre, gravity[i] = got
        normal[i] = moment[i] / np.linalg.norm(moment[i])
        r[i], u[i], scale[i] = np.linalg.norm(centre), centre / np.linalg.norm(centre), 1.0
    return dark


def _inside(star_b, points):
    """True where points (n, 3) lie inside star B."""
    rel = points - star_b["centre"]
    if star_b["second"]:
        rel = rel * [-1, -1, 1]
    d = np.linalg.norm(rel, axis=1)
    if star_b["roche"] is None:
        return d < star_b["r_min"]
    q, om = star_b["roche"]
    d = np.maximum(d, 1e-12)
    # only B's own side of the L1 plane: a contact envelope's other half is the other star
    return (roche.omega(d, rel[:, 0] / d, rel[:, 2] / d, q) > om) & (rel[:, 0] < star_b["neck"])


def _hidden(points, view, star_b, samples=24):
    """True where the sight line from points towards view passes through star B."""
    to_b = star_b["centre"] - points
    s = to_b @ view  # distance along the line to the closest approach
    closest = np.linalg.norm(to_b - s[:, None] * view, axis=1)
    hidden = (s > 0) & (closest < star_b["r_min"])
    unsure = (s > 0) & ~hidden & (closest < star_b["r_max"])
    if star_b["roche"] is not None and unsure.any():
        span = np.linspace(-1, 1, samples) * star_b["r_max"]
        p = points[unsure, None, :] + (s[unsure, None, None] + span[None, :, None]) * view
        hidden[unsure] = _inside(star_b, p.reshape(-1, 3)).reshape(p.shape[:2]).any(axis=1)
    return hidden


def _limb(b, view, direction, steps=30):
    """B's projected limb distance from its centre along sky-plane directions (n, 3): bisection on the sight-line
    test from a point far behind B."""
    lo = np.full(len(direction), b["r_min"])
    hi = np.full(len(direction), b["r_max"])
    if b["roche"] is None:
        return lo
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        behind = b["centre"] + mid[:, None] * direction - 3 * b["r_max"] * view
        inside = _hidden(behind, view, b)
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    return 0.5 * (lo + hi)


def _light(a, b, view, k):
    """Each element's light towards view: I₀ · limb(μ) · μ · area · its visible share. Elements on the horizon
    (|μ| within their own angular size) are split into k × k sub-elements with their own directions and μ. An
    element near B's projected limb is seen in the share its projected width lies outside the limb (a linear ramp
    across the element: second-order accurate where point samples alias)."""
    law, coeffs = a["ld"]
    mu = a["normal"] @ view
    projected = np.clip(a["scale"] * (a["moment"] @ view), 0, None)
    light = a["i0"] * limb(np.clip(mu, 0, 1), law, coeffs) * projected
    angle = np.sqrt(a["area"]) / a["r"]
    horizon = np.abs(mu) < 2 * angle
    if horizon.any() and k > 1:
        c = a["cells"][horizon]
        f = (np.arange(k) + 0.5) / k
        th = c[:, 0, None, None] + (c[:, 1] - c[:, 0])[:, None, None] * f[:, None]
        ph = c[:, 2, None, None] + (c[:, 3] - c[:, 2])[:, None, None] * f[None, :]
        u = _dirs(np.broadcast_to(th, (len(c), k, k)), np.broadcast_to(ph, (len(c), k, k))).reshape(-1, 3)
        centre_u = _dirs(0.5 * (c[:, 0] + c[:, 1]), 0.5 * (c[:, 2] + c[:, 3]))
        normal = np.repeat(a["normal_own"][horizon] - centre_u, k * k, axis=0) + u  # the normal turns with u
        normal /= np.linalg.norm(normal, axis=1)[:, None]
        if a["second"]:
            normal = normal * [-1, -1, 1]
        m = np.clip(normal @ view, 0, None)
        light[horizon] = a["i0"][horizon] * a["area"][horizon] * (limb(m, law, coeffs) * m).reshape(-1, k * k).mean(1)
    # the eclipse by B
    to_b = b["centre"] - a["xyz"]
    s = to_b @ view
    across = to_b - s[:, None] * view  # from the element to B's centre in the sky plane
    closest = np.linalg.norm(across, axis=1)
    width = np.sqrt(a["area"] * np.clip(np.abs(mu), 0.05, 1))  # the element's projected size
    near = (s > 0) & (light > 0) & (closest < b["r_max"] + width)
    if near.any():
        direction = -across[near] / np.maximum(closest[near], 1e-12)[:, None]
        edge = _limb(b, view, direction)  # B's limb at the element's position angle
        kk = max(k, 1)
        c = a["cells"][near]
        f = (np.arange(kk) + 0.5) / kk
        th = c[:, 0, None, None] + (c[:, 1] - c[:, 0])[:, None, None] * f[:, None]
        ph = c[:, 2, None, None] + (c[:, 3] - c[:, 2])[:, None, None] * f[None, :]
        u = _dirs(np.broadcast_to(th, (len(c), kk, kk)), np.broadcast_to(ph, (len(c), kk, kk)))
        pts = u * a["r"][near, None, None, None]  # shortcut: the centre's radius for the sub-points
        if a["second"]:
            pts = pts * [-1, -1, 1] + [1.0, 0, 0]
        rel = b["centre"] - pts
        sky = rel - (rel @ view)[..., None] * view
        dist = np.linalg.norm(sky, axis=-1)
        sub_width = width[near] / kk
        shares = np.clip(0.5 + (dist - edge[:, None, None]) / sub_width[:, None, None], 0, 1)
        # each sub-point weighs its own projected area, sin θ · μ (equal weights biased the depth by 5e-4)
        w = np.sin(np.broadcast_to(th, shares.shape)) * np.clip((u @ (view * ([-1, -1, 1] if a["second"] else 1))),
                                                                1e-9, None)  # fmt: skip
        light[near] *= (w * shares).reshape(len(c), -1).sum(1) / w.reshape(len(c), -1).sum(1)
    return light


def flux(phases, incl, star1, star2, k=5):
    """The total flux at each phase (arbitrary units: divide by the out-of-eclipse value to normalise)."""
    i = np.radians(incl)
    out = []
    for ph in np.atleast_1d(np.asarray(phases, float)):
        a = 2 * np.pi * ph
        view = np.array([np.sin(i) * np.cos(a), -np.sin(i) * np.sin(a), np.cos(i)])  # the orbit turns about +z
        total = 0.0
        for me, other in ((star1, star2), (star2, star1)):
            total += float(np.sum(_light(me, other, view, k)))
        out.append(total)
    return np.array(out)


def velocities(phases, incl, star1, star2, q, a_rsun, period_days, spin=(1.0, 1.0), k=5):
    """Flux-weighted radial velocities (km/s, positive away from the observer) of both stars at each phase
    (MOD-7): every visible element moves with its star's centre about the barycentre and spins about the centre at
    F times the orbital rate (F = 1 synchronous); light as in flux(). Circular orbit."""
    i = np.radians(incl)
    omega = 2 * np.pi / (period_days * 86400.0) * a_rsun * 6.957e5  # km/s per unit of separation
    cm = np.array([q / (1 + q), 0, 0])
    z = np.array([0, 0, 1.0])
    out = []
    for ph in np.atleast_1d(np.asarray(phases, float)):
        a = 2 * np.pi * ph
        view = np.array([np.sin(i) * np.cos(a), -np.sin(i) * np.sin(a), np.cos(i)])  # the orbit turns about +z
        row = []
        for me, other, f in ((star1, star2, spin[0]), (star2, star1, spin[1])):
            light = _light(me, other, view, k)
            v = np.cross(z, me["centre"] - cm) + f * np.cross(z, me["xyz"] - me["centre"])
            row.append(-omega * float(np.sum(light * (v @ view)) / max(np.sum(light), 1e-300)))
        out.append(row)
    return np.array(out).T
