"""Eclipse times of a Kepler eclipsing binary from the Villanova Kepler EB catalogue (plans/oc.md OC-4): the ETV
file of one KIC star, long cadence, read as O−C minima records (timeseries/minima_table).

    rows = minima(7938468)       primaries and secondaries, times in BJD_TDB, cached (services.cache)

The file is tab-separated with `# BJD | O-C (days) | Error (days) | Eclipse`; BJD (− 2 400 000) is the computed time
of the linear ephemeris, so the observed time is BJD + O−C. Stars without ETVs (the long-period ones) answer 500.
"""

from . import http

URL = "https://keplerebs.villanova.edu/data/"
SOURCE = "Villanova Kepler EB catalogue (Conroy et al. 2014)"
CITATION = "Villanova Kepler EB catalogue: Kirk et al. 2016, AJ 151, 68; eclipse times: Conroy et al. 2014, AJ 147, 45"
_KIND = {1: "I", 2: "II"}  # 0, the whole-phase fit, is not one eclipse: left out


def parse(text):
    """The ETV file -> minima records (BJD_TDB, the file's error, method space); each (time, eclipse) once."""
    from ..timeseries.minima_table import record

    rows, seen = [], set()
    for line in text.splitlines():
        words = line.split()
        if not words or line.lstrip().startswith("#"):
            continue
        bjd, oc, err, eclipse = float(words[0]), float(words[1]), float(words[2]), int(float(words[3]))
        if eclipse not in _KIND or (bjd, eclipse) in seen:
            continue
        seen.add((bjd, eclipse))
        t = bjd + oc + 2400000.0
        rows.append(record(t, err, _KIND[eclipse], "BJD_TDB", "space", bjd_tdb=t, source=SOURCE))
    return rows


def fetch(kic):
    """The ETV file of KIC kic as text, cached; ValueError when the catalogue has no ETVs for it."""
    from .cache import cached

    kic = int(kic)

    def now():
        try:
            text = http.get(URL, {"k": f"{kic}.00", "cadence": "lc", "data": "etv"}).decode("utf-8", "replace")
        except http.HTTPError as e:
            if e.code == 500:  # the site's answer for a star outside the short-period ETV catalogue
                raise ValueError(f"no eclipse timing variations for KIC {kic} in the Villanova catalogue") from e
            raise
        parse(text)  # a page of another form raises here, so it is never kept in the cache
        return text

    return cached("villanova", kic, now)


def minima(kic):
    return parse(fetch(kic))
