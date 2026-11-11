"""The observer's profile: site, camera and the observer's codes, entered once and used by every window
(plans/architecture.md ARC-16). Kept in the settings under "profile"; the older separate settings ("site" of the
Plan page, "mpc" of the asteroid report) move into it the first time it is read.

    site = profiles.section(settings, "site")              # {"name", "lat", "lon", "height"}
    profiles.update(settings, "observer", aavso_code="XYZ")

shortcut: one profile ("Default"); several sites and cameras with a chooser come with Settings → Profiles (UI-13).
"""

DEFAULTS = {
    "site": {"name": "", "lat": 39.9, "lon": 32.8, "height": 900.0},  # east-positive longitude, metres
    # e-/ADU, e-, e-/s, ADU (where the response stops being linear), ADU
    # pixel_size: µm (binned, as XPIXSZ gives it)
    "camera": {
        "gain": 0.0,
        "read_noise": 0.0,
        "dark_current": 0.0,
        "linearity": 0.0,
        "saturation": 0.0,
        "pixel_size": 0.0,
    },  # fmt: skip
    "optics": {"aperture": 0.0, "focal_length": 0.0},  # mm; with a reducer: the focal length with it
    "filters": {"names": {}},  # a header's filter name -> its AAVSO band, where the guess below is wrong
    "observer": {"name": "", "aavso_code": "", "mpc_code": "", "observers": "", "catalog": "Gaia3"},
}


def _profile(settings):
    profile = settings.get("profile")
    if profile is None:  # first read: the older settings move in
        profile = {"name": "Default"}
        if settings.get("site"):
            profile["site"] = dict(settings.get("site"))
        mpc = settings.get("mpc") or {}
        observer = {k: mpc[k] for k in ("observers", "catalog") if k in mpc}
        if mpc.get("code"):
            observer["mpc_code"] = mpc["code"]
        if observer:
            profile["observer"] = observer
        settings.set("profile", profile)
    return profile


def has(settings, part):
    """Whether the user has filled in this section (the defaults alone do not count)."""
    return bool(_profile(settings).get(part))


def section(settings, part):
    """One section of the profile with every field (defaults filled in)."""
    return {**DEFAULTS[part], **_profile(settings).get(part, {})}


def update(settings, part, /, **values):
    """Change fields of one section and save; unknown fields are refused (a typo would be kept silently)."""
    unknown = set(values) - set(DEFAULTS[part])
    if unknown:
        raise KeyError(f"no field {', '.join(sorted(unknown))} in the {part} profile")
    profile = dict(_profile(settings))
    profile[part] = {**profile.get(part, {}), **values}
    settings.set("profile", profile)
    if part == "site":  # shortcut: windows not moved yet read "site"; drop it when they all read the profile
        settings.set("site", section(settings, "site"))


def from_header(header):
    """{part: {field: value}} of what a FITS header says about the site, camera and observer (ARC-16 item 2: "Fill
    from a FITS header"); a field the header does not give is left out, so it never overwrites with a guess."""
    from ..hdr import get
    from ..timing import location

    out = {}
    where = location(header)
    if where is not None:
        site = {"lat": round(float(where.lat.deg), 5), "lon": round(float(where.lon.deg), 5),
                "height": round(float(where.height.value), 1)}  # fmt: skip
        name = str(header.get("SITENAME") or header.get("OBSERVAT") or "").strip()
        out["site"] = {**site, **({"name": name} if name else {})}
    camera = {
        "gain": get(header, "EGAIN", "GAIN"),
        "read_noise": get(header, "RDNOISE", "READNOIS", "RDNOIS"),
        "dark_current": get(header, "DARKCUR"),
        "saturation": get(header, "SATURATE", "DATAMAX"),
        "linearity": get(header, "MAXLIN"),
        "pixel_size": get(header, "XPIXSZ", "PIXSIZE1"),
    }
    camera = {k: float(v) for k, v in camera.items() if v is not None and v > 0}
    if camera:
        out["camera"] = camera
    optics = {"aperture": get(header, "APTDIA"), "focal_length": get(header, "FOCALLEN")}
    optics = {k: float(v) for k, v in optics.items() if v is not None and v > 0}
    if optics:
        out["optics"] = optics
    observer = str(header.get("OBSERVER") or "").strip()
    if observer:
        out["observer"] = {"name": observer}
    return out


def pixel_scale(settings):
    """Arcseconds per pixel from the camera's pixel size and the optics' focal length; None until both are given."""
    pixel, focal = section(settings, "camera")["pixel_size"], section(settings, "optics")["focal_length"]
    return 206.264806 * pixel / focal if pixel > 0 and focal > 0 else None


AAVSO_BANDS = ("V", "B", "R", "I", "CV", "CR", "TG", "TB", "TR", "SG", "SR", "SI", "U")
_GUESS = {  # what capture programs write, upper-cased, -> AAVSO's band (only names that cannot mean another band)
    **{k: "CV" for k in ("CLEAR", "C", "L", "LUM", "LUMINANCE", "NONE", "OPEN", "NO FILTER", "UNFILTERED")},
    **{k: "V" for k in ("JOHNSON V", "BESSELL V", "V-BAND", "JV", "V JOHNSON")},
    **{k: "B" for k in ("JOHNSON B", "BESSELL B", "B-BAND", "JB", "B JOHNSON")},
    **{k: "R" for k in ("COUSINS R", "BESSELL R", "RC", "R-BAND")},
    **{k: "I" for k in ("COUSINS I", "BESSELL I", "IC", "I-BAND")},
    **{k: "SG" for k in ("SDSS G", "G'", "SLOAN G", "GP")},
    **{k: "SR" for k in ("SDSS R", "R'", "SLOAN R", "RP")},
    **{k: "SI" for k in ("SDSS I", "I'", "SLOAN I", "IP")},
    **{k: "TG" for k in ("GREEN", "TRI-COLOUR GREEN", "TRICOLOR GREEN")},
    **{k: "TB" for k in ("BLUE",)},
    **{k: "TR" for k in ("RED",)},
}


def aavso_band(settings, name):
    """The AAVSO band of a filter as a header names it ("Johnson V" -> "V", "Luminance" -> "CV"), the profile's
    own table first; None when it cannot be told (the user chooses)."""
    text = str(name or "").strip()
    own = section(settings, "filters")["names"].get(text)
    if own:
        return own
    upper = text.upper()
    return upper if upper in AAVSO_BANDS else _GUESS.get(upper)
