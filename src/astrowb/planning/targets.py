"""Targets: typed coordinates, a local cache, then SIMBAD (astroquery).

Every name resolved online is cached (JSON in the user data folder), so a target looked up
once at home is available at an offline observatory.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord


class TargetError(LookupError):
    pass


@dataclass
class Target:
    name: str
    ra: float  # deg ICRS
    dec: float
    vmag: float | None = None
    source: str = "typed"

    @property
    def coord(self):
        return SkyCoord(self.ra * u.deg, self.dec * u.deg)


# Solar-system bodies by their names in the interface languages. They move: their altitude is computed for every
# time of the night from astropy's built-in ephemeris (offline), never from fixed coordinates or SIMBAD.
BODIES = {
    "moon": ("moon", "ay", "mond", "luna"),
    "mercury": ("mercury", "merkür", "merkur", "mercurio"),
    "venus": ("venus", "venüs"),
    "mars": ("mars", "marte"),
    "jupiter": ("jupiter", "jüpiter", "júpiter"),
    "saturn": ("saturn", "satürn", "saturno"),
    "uranus": ("uranus", "uranüs", "urano"),
    "neptune": ("neptune", "neptün", "neptun", "neptuno"),
}


def body_of(name) -> str | None:
    """astropy's name of the solar-system body called name, or None."""
    key = " ".join(str(name).lower().split())
    return next((body for body, names in BODIES.items() if key in names), None)


def parse_coordinates(text: str) -> SkyCoord | None:
    """'02 04 10.3 +46 41 16', '02:04:10.3 +46:41:16', '31.043 46.688' (degrees if no separators)."""
    parts = text.replace(",", " ").split()
    if len(parts) not in (2, 6):
        return None
    try:
        if len(parts) == 2 and ":" not in text and "h" not in text:
            return SkyCoord(float(parts[0]) * u.deg, float(parts[1]) * u.deg)
        return SkyCoord(text.replace(",", " "), unit=(u.hourangle, u.deg))
    except ValueError:
        return None


def _simbad(name: str) -> Target:
    from astroquery.simbad import Simbad

    from ..mirrors import cds

    def query(server):
        s = Simbad()
        s.server = server
        s.add_votable_fields("V")
        return s.query_object(name)

    table = cds("simbad", query)
    if table is None or len(table) == 0:
        raise TargetError(f"SIMBAD does not know '{name}'")
    row = table[0]
    cols = {c.lower(): c for c in table.colnames}
    ra, dec = row[cols["ra"]], row[cols["dec"]]
    coord = (
        SkyCoord(ra, dec, unit=(u.deg, u.deg))
        if not isinstance(ra, str)
        else SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
    )
    vmag = row[cols["v"]] if "v" in cols and not getattr(row[cols["v"]], "mask", False) else None
    return Target(name, coord.ra.deg, coord.dec.deg, float(vmag) if vmag is not None else None, "SIMBAD")


class Resolver:
    def __init__(self, cache_file: Path, online=_simbad):
        self.cache_file = Path(cache_file)
        self.online = online
        try:
            self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            self.cache = {}

    def resolve(self, text: str) -> Target:
        text = text.strip()
        coord = parse_coordinates(text)
        if coord is not None:
            return Target(coord.to_string("hmsdms", precision=1), coord.ra.deg, coord.dec.deg)
        body = body_of(text)
        if body:  # coordinates of now, for the table; the night plan follows the body through the night
            from astropy.coordinates import get_body
            from astropy.time import Time

            c = get_body(body, Time.now()).icrs
            return Target(text, float(c.ra.deg), float(c.dec.deg), source="solar system")
        key = " ".join(text.lower().split())
        if key in self.cache:
            return Target(**self.cache[key] | {"source": "cache"})
        try:
            target = self.online(text)
        except TargetError:
            raise
        except Exception as e:  # network down, service changed: say so, keep working offline
            raise TargetError(f"cannot reach SIMBAD and '{text}' is not in the local cache ({type(e).__name__})") from e
        self.cache[key] = asdict(target)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, indent=1), encoding="utf-8")
        return target
