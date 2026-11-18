"""Transformation coefficients kept in the profile's filters section, per filter set and dated (PHO-35, ARC-16):
filters["transformations"] = {"BV": [{"name": "tv", "value", "error", "date"}, ...]}."""


def save(settings, band_a, band_b, result, date=None):
    """Append the three coefficients of a coefficients.transformation() result under the filter set A+B."""
    import datetime

    from . import profiles

    date = date or datetime.date.today().isoformat()
    key = f"{band_a}{band_b}"
    filters = profiles.section(settings, "filters")
    store = {k: list(v) for k, v in filters["transformations"].items()}
    for name in (f"t{band_a}{band_b}".lower(), f"t{band_b}".lower(), f"t{band_a}".lower()):
        c = result[name]
        store.setdefault(key, []).append({"name": name, "value": c["value"], "error": c["error"], "date": date})
    profiles.update(settings, "filters", transformations=store)


def latest(settings, band):
    """The newest colour term of this band over all filter sets: (set, entry) or None."""
    from . import profiles

    found = [
        (e["date"], key, e)
        for key, entries in profiles.section(settings, "filters")["transformations"].items()
        for e in entries
        if e["name"] == f"t{band}".lower()
    ]
    if not found:
        return None
    _, key, entry = max(found, key=lambda f: f[:2])
    return key, entry
