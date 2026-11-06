"""The AAVSO comparison-star sequence of a field (VSP, the Variable Star Plotter's API; plans/photometry.md PHO-25):
the chart id an AAVSO report names, and each sequence star's AUID, chart label, position and magnitudes per band.

    seq = sequence(303.0, 65.16, fov=20)        # {"chart": "X43370AGGP", "stars": [...]}
    sequence_magnitudes(seq, [(ra, dec), ...], "V")

VSP makes a new chart id at every request; the answer is cached (services.cache) so a field keeps one chart id and
works offline after the first look-up.
"""

import json
import urllib.parse
import urllib.request

URL = "https://app.aavso.org/vsp/api/chart/"
BAND = {"CV": "V", "TG": "V", "TB": "B", "TR": "Rc", "CR": "Rc", "R": "Rc", "I": "Ic"}  # AAVSO filter -> VSP band


def _sexagesimal(text, hours):
    sign = -1.0 if text.strip().startswith("-") else 1.0
    d, m, s = (abs(float(v)) for v in text.split(":"))
    return sign * (d + m / 60 + s / 3600) * (15.0 if hours else 1.0)


def parse(answer):
    """VSP's JSON (dict) -> {"chart", "stars": [{"auid", "label", "ra", "dec", "bands": {band: (mag, err)}}]}."""
    stars = []
    for p in answer.get("photometry") or []:
        bands = {b["band"]: (float(b["mag"]), float(b["error"] or 0.0)) for b in p.get("bands") or [] if b.get("mag")}
        ra, dec = _sexagesimal(p["ra"], True), _sexagesimal(p["dec"], False)
        stars.append({"auid": p.get("auid") or "", "label": str(p.get("label") or ""), "ra": ra, "dec": dec,
                      "bands": bands})  # fmt: skip
    return {"chart": answer.get("chartid") or "na", "stars": stars}


def sequence(ra, dec, fov=30.0, maglimit=16.0, fetch=None):
    """The sequence within a field of fov arcminutes around ra, dec (degrees). LookupError when VSP has none."""
    from .cache import cached

    query = {"ra": f"{ra:.5f}", "dec": f"{dec:.5f}", "fov": f"{fov:.0f}", "maglimit": f"{maglimit:.1f}",
             "format": "json"}  # fmt: skip
    url = URL + "?" + urllib.parse.urlencode(query)

    def now():
        if fetch:
            return fetch(url)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (a fixed https service)
            return json.loads(r.read())

    out = parse(cached("aavso_vsp", url, now))
    if not out["stars"]:
        raise LookupError("the AAVSO has no comparison sequence for this field")
    return out


def sequence_magnitudes(seq, positions, filt, tol_arcsec=5.0):
    """Per (ra, dec): {"label", "auid", "mag", "err"} of the sequence star within tol_arcsec having the band of the
    AAVSO filter filt, else None."""
    import numpy as np

    band = BAND.get(filt, filt)
    out = []
    for ra, dec in positions:
        best, dist = None, tol_arcsec
        for s in seq["stars"]:
            d = 3600 * np.hypot((s["ra"] - ra) * np.cos(np.radians(dec)), s["dec"] - dec)
            if d <= dist and band in s["bands"]:
                best, dist = s, d
        out.append(best and {"label": best["label"], "auid": best["auid"], "mag": best["bands"][band][0],
                             "err": best["bands"][band][1]})  # fmt: skip
    return out
