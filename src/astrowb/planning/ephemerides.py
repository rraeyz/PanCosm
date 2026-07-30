"""Ephemerides from the catalogues observers use: the AAVSO International Variable Star Index (VSX) and the
NASA Exoplanet Archive (Planetary Systems Composite table). Both are queried only when the user asks.

VSX gives the epoch in HJD (for eclipsing binaries the time of primary minimum) and the eclipse duration
in per cent of the period; HJD and BJD differ by at most a few seconds, below the precision of an
observing plan. The Exoplanet Archive gives the mid-transit time in BJD_TDB and the duration in hours.
"""

import json
import urllib.parse
import urllib.request

from .targets import TargetError

VSX_URL = "https://www.aavso.org/vsx/index.php"
EXO_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"


def _get(url, params, timeout=20):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https catalogue URLs)
        return json.loads(r.read().decode("utf-8"))


def _float(value):
    try:
        return float(str(value).split()[0])
    except (TypeError, ValueError, IndexError):
        return None


def vsx(name, fetch=_get):
    """{name, ra, dec, t0, period, duration (d), secondary, type, vmag, source} from VSX."""
    data = fetch(VSX_URL, {"view": "api.object", "ident": name, "format": "json"})
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
    """{name, ra, dec, t0 (BJD_TDB), period, duration (d), vmag, source} from the NASA Exoplanet Archive."""
    planet = name.strip().replace("'", "")
    if planet[-1:].isdigit():  # "HAT-P-32" -> "HAT-P-32 b"
        planet += " b"
    query = (
        "select pl_name,ra,dec,pl_orbper,pl_tranmid,pl_trandur,sy_vmag from pscomppars "
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
