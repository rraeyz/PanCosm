"""Ephemerides from the catalogues observers use: the AAVSO International Variable Star Index (VSX) and the
NASA Exoplanet Archive (Planetary Systems Composite table). Both are queried only when the user asks.

VSX gives the epoch in HJD (for eclipsing binaries the time of primary minimum) and the eclipse duration
in per cent of the period; HJD and BJD differ by at most a few seconds, below the precision of an
observing plan. The Exoplanet Archive gives the mid-transit time in BJD_TDB and the duration in hours.
"""

import json

from .targets import TargetError

VSX_URL = "https://www.aavso.org/vsx/index.php"
EXO_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"


def _get(url, params, timeout=20):
    from ..services import http
    from ..services.cache import cached

    def now():
        return json.loads(http.get(url, params, timeout, agent="Mozilla/5.0").decode("utf-8"))

    return cached("ephemerides", (url, params), now)


def _float(value):
    try:
        return float(str(value).split()[0])
    except (TypeError, ValueError, IndexError):
        return None


def _vsx_vizier(name):
    """The VSX entry from its copy in VizieR (B/vsx/vsx, kept up to date with VSX; no eclipse duration), shaped
    like the VSX API's answer: used when aavso.org does not answer. A name VSX does not list (an alias such as
    Algol) is looked up in SIMBAD and the VSX star within 10" taken, as the VSX API does."""
    import astropy.units as u

    from ..services import vizier
    from .targets import _simbad

    def ask(**where):
        if "coord" in where:
            return vizier.region(where["coord"], 10 * u.arcsec, "B/vsx/vsx", ["**"], 5)
        return vizier.constraints("B/vsx/vsx", ["**"], 5, Name=name)

    def same(a):
        return " ".join(str(a).lower().split()) == " ".join(name.lower().split())

    tables = ask()
    rows = [r for r in (tables[0] if len(tables) else []) if same(r["Name"])]
    if not rows:
        tables = ask(coord=_simbad(name).coord)
        rows = list(tables[0]) if len(tables) else []
    if not rows:
        return {}
    r = rows[0]

    def value(col):
        v = r[col]
        return None if v is None or str(v).strip() in ("", "--") else v

    keys = {"RA2000": "RAJ2000", "Declination2000": "DEJ2000", "MaxMag": "max", "Period": "Period", "Epoch": "Epoch"}
    obj = {k: value(c) for k, c in keys.items()}
    return {"VSXObject": obj | {"Name": str(r["Name"]).strip(), "VariabilityType": str(r["Type"]).strip()}}


def vsx(name, fetch=_get):
    """{name, ra, dec, t0, period, duration (d), secondary, type, vmag, source} from VSX."""
    try:
        data = fetch(VSX_URL, {"view": "api.object", "ident": name, "format": "json"})
    except OSError:  # aavso.org down or blocked: the same catalogue through VizieR
        data = _vsx_vizier(name)
    obj = data.get("VSXObject") if isinstance(data, dict) else None
    if not obj or not isinstance(obj, dict):
        raise TargetError(f"VSX does not know '{name}'")
    kind = str(obj.get("VariabilityType", ""))
    period, epoch = _float(obj.get("Period")), _float(obj.get("Epoch"))
    eclipsing = kind.upper().startswith("E")
    out = {
        "name": obj.get("Name", name),
        "ra": _float(obj.get("RA2000")),
        "dec": _float(obj.get("Declination2000")),
        "type": kind,
        "vmag": _float(obj.get("MaxMag")),
        "period": period,
        "source": "VSX",
    }
    if eclipsing and period and epoch:  # only eclipses have predictable events on the Plan page
        out |= {"t0": epoch, "secondary": True}
        width = _float(obj.get("EclipseDuration"))
        if width:
            out["duration"] = width / 100 * period
    return out


def exoplanet(name, fetch=_get):
    """{name, ra, dec, t0 (BJD_TDB), period, duration (d), vmag, source, and when known k (Rp/R★), a_rs, b} from
    the NASA Exoplanet Archive."""
    planet = name.strip().replace("'", "")
    if planet[-1:].isdigit():  # "HAT-P-32" -> "HAT-P-32 b"
        planet += " b"
    query = (
        "select pl_name,ra,dec,pl_orbper,pl_tranmid,pl_trandur,sy_vmag,pl_ratror,pl_ratdor,pl_imppar from pscomppars "
        f"where lower(pl_name)=lower('{planet}')"
    )
    rows = fetch(EXO_URL, {"query": query, "format": "json"})
    if not rows:
        raise TargetError(f"the NASA Exoplanet Archive does not know '{planet}'")
    r = rows[0]
    out = {
        "name": r["pl_name"],
        "ra": float(r["ra"]),
        "dec": float(r["dec"]),
        "period": r.get("pl_orbper"),
        "t0": r.get("pl_tranmid"),
        "vmag": r.get("sy_vmag"),
        "type": "transit",
        "secondary": False,
        "source": "NASA Exoplanet Archive",
    }
    if r.get("pl_trandur"):
        out["duration"] = float(r["pl_trandur"]) / 24
    for key, col in (("k", "pl_ratror"), ("a_rs", "pl_ratdor"), ("b", "pl_imppar")):  # the transit fit's start
        if r.get(col) is not None:
            out[key] = float(r[col])
    return out


def lookup(name, catalogue="auto", fetch=_get):
    """catalogue: 'vsx', 'exoplanet' or 'auto' (exoplanet archive first for names like 'WASP-12 b',
    otherwise VSX, then the other one)."""
    order = {"vsx": [vsx], "exoplanet": [exoplanet]}.get(catalogue)
    if order is None:
        looks_planet = name.strip()[-2:-1] == " " and name.strip()[-1:].isalpha() and name.strip()[-1:].islower()
        order = [exoplanet, vsx] if looks_planet else [vsx, exoplanet]
    errors = []
    for f in order:
        try:
            return f(name, fetch=fetch)
        except (TargetError, OSError, ValueError, KeyError) as e:
            errors.append(str(e))
    raise TargetError("; ".join(errors))


def transiting_planets(fetch=None):
    """Every transiting planet of the Exoplanet Archive (Planetary Systems Composite) with an ephemeris, as the
    table planning.finder.tonight_events reads: name, ra, dec, mag (V), period, t0 (BJD_TDB), duration (days),
    depth (mag), kind "transit". Asked only when the user presses for it; kept a week (services.cache)."""
    import csv
    import io

    import numpy as np

    from ..services.cache import cached

    query = ("select pl_name,ra,dec,pl_orbper,pl_tranmid,pl_trandur,sy_vmag,pl_trandep from pscomppars "
             "where tran_flag=1 and pl_orbper is not null and pl_tranmid is not null")  # fmt: skip
    from ..services import http

    url = http.url_of(EXO_URL, {"query": query, "format": "csv"})

    def table(text):
        reader = csv.DictReader(io.StringIO(text))
        if "pl_name" not in (reader.fieldnames or []):  # an HTML page or nothing, not a table with no rows
            raise ValueError("the service sent an answer in an unexpected form")
        return list(reader)

    def now():
        if fetch:
            text = fetch(url)
        else:
            text = http.get(url, timeout=60).decode("utf-8")
        table(text)  # a page of the wrong form raises here, so it is never kept in the cache
        return text

    rows = table(cached("ephemerides", url, now))

    def col(key, scale=1.0):
        return np.array([float(r[key]) * scale if r.get(key) not in (None, "") else np.nan for r in rows])

    depth = -2.5 * np.log10(1 - np.clip(col("pl_trandep"), 0, 99) / 100)  # the archive's depth in per cent
    return {"name": np.array([r["pl_name"] for r in rows]), "ra": col("ra"), "dec": col("dec"), "mag": col("sy_vmag"),
            "period": col("pl_orbper"), "t0": col("pl_tranmid"), "duration": col("pl_trandur", 1 / 24),
            "depth": depth, "kind": np.full(len(rows), "transit")}  # fmt: skip
