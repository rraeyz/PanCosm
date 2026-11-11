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
    "camera": {"gain": 0.0, "read_noise": 0.0, "dark_current": 0.0, "linearity": 0.0, "saturation": 0.0},
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
