"""Known observatories (name -> latitude, longitude east-positive, height in metres), from astropy's site
registry (astropy-data, BSD-3-Clause), shipped so the list works offline."""

import json
from functools import cache
from importlib.resources import files


@cache
def observatories() -> dict:
    text = (files("astrowb") / "resources" / "observatories.json").read_text(encoding="utf-8")
    return {name: tuple(v) for name, v in json.loads(text).items()}


def find(name):
    """(lat, lon, height) of a known observatory, the name in any case; None when unknown."""
    key = " ".join(str(name).split()).lower()
    return next((v for n, v in observatories().items() if n.lower() == key), None)
