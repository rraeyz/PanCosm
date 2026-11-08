"""A star list saved from one night and put back on another (plans/photometry.md item 7): the target, the comparison
stars, check stars and further targets, and the three radii, kept in RA / Dec so that another night's plate solution
puts them on the right pixels whatever the pointing, rotation or camera. Pixel positions are kept too, for frames
without a solution (the same pointing). As AstroImageJ saves its apertures in RA / Dec when the frame has a WCS.

The file is small JSON (".stars.json")."""

import json

import numpy as np

VERSION = 1


def save_star_list(path, target, comps, extras=(), radii=None, wcs=None, name=""):
    """target, comps: 0-based (x, y) on the frame the WCS belongs to; extras: [((x, y), role)] with role "check" or
    "target". Without a WCS only the pixels are written. Returns the path."""

    def star(xy, role):
        out = {"role": role, "x": float(xy[0]), "y": float(xy[1])}
        if wcs is not None:
            ra, dec = wcs.pixel_to_world_values(float(xy[0]), float(xy[1]))
            out |= {"ra": float(ra), "dec": float(dec)}
        return out

    stars = [star(target, "target")] + [star(c, "comparison") for c in comps]
    stars += [star(xy, "check" if role == "check" else "extra target") for xy, role in extras]
    doc = {
        "version": VERSION,
        "name": name,
        "stars": stars,
        "radii": None if radii is None else list(map(float, radii)),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    return path


def load_star_list(path, wcs=None, shape=None):
    """{"target": (x, y), "comps": [...], "extras": [((x, y), role)], "radii": [...] or None, "by": "sky" | "pixels",
    "outside": [names of stars off the frame]}: through the WCS when the file and the frame both have one, else the
    saved pixels. shape (ny, nx): stars off the frame are named in "outside" and left out. Raises ValueError for a file
    that is not a star list."""
    with open(path, encoding="utf-8") as f:
        try:
            doc = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError("not a star list (.stars.json)") from e
    stars = doc.get("stars") if isinstance(doc, dict) else None
    if not stars or stars[0].get("role") != "target":
        raise ValueError("not a star list (.stars.json)")
    by_sky = wcs is not None and all("ra" in s for s in stars)
    out = {"target": None, "comps": [], "extras": [], "radii": doc.get("radii"), "by": "sky" if by_sky else "pixels",
           "outside": []}  # fmt: skip
    counts = {}
    for s in stars:
        if by_sky:
            x, y = (float(v) for v in wcs.world_to_pixel_values(s["ra"], s["dec"]))
        else:
            x, y = float(s["x"]), float(s["y"])
        role = s.get("role")
        counts[role] = counts.get(role, 0) + 1
        label = "T1" if role == "target" else f"{role} {counts[role]}"
        inside = shape is None or (0 <= x < shape[1] and 0 <= y < shape[0])
        if not inside or not np.isfinite([x, y]).all():
            out["outside"].append(label)
            continue
        if role == "target":
            out["target"] = (x, y)
        elif role == "comparison":
            out["comps"].append((x, y))
        else:
            out["extras"].append(((x, y), "check" if role == "check" else "target"))
    if out["target"] is None:
        raise ValueError("the target of the star list is outside this frame")
    return out
