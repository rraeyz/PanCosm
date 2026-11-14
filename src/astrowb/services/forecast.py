"""The weather forecast for the night (plans/planning.md PLN-11): hourly cloud cover (low, middle, high and total),
humidity, dew point, wind and temperature at the site, from Open-Meteo (https://open-meteo.com).

Open-Meteo's free API is for non-commercial use and its data are CC BY 4.0: the program shows ATTRIBUTION with the
forecast. The answer is cached for an hour (services.cache), so a re-opened window does not ask again and an
offline window shows the last forecast with its age.

    f = forecast(36.82, 30.33)        {"time": [JD UTC], "cloud": [%], "cloud_low": …, "humidity", "dew_point",
                                       "wind", "temperature", "issued" (JD of the fetch), "source"}
"""

import json
import urllib.parse
import urllib.request

import numpy as np

URL = "https://api.open-meteo.com/v1/forecast"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
FIELDS = {"cloud_cover": "cloud", "cloud_cover_low": "cloud_low", "cloud_cover_mid": "cloud_mid",
          "cloud_cover_high": "cloud_high", "relative_humidity_2m": "humidity", "dew_point_2m": "dew_point",
          "wind_speed_10m": "wind", "temperature_2m": "temperature"}  # fmt: skip


def parse(answer):
    """Open-Meteo's JSON (dict, UTC times) -> plain lists, times as JD UTC."""
    from astropy.time import Time

    hourly = answer.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise LookupError("the forecast service sent no hours")
    out = {"time": Time([t if len(t) > 16 else t + ":00" for t in times], format="isot", scale="utc").jd.tolist()}
    for key, name in FIELDS.items():
        values = hourly.get(key)
        out[name] = [np.nan if v is None else float(v) for v in values] if values else [np.nan] * len(times)
    out["source"] = ATTRIBUTION
    return out


def forecast(lat, lon, days=3, fetch=None):
    from astropy.time import Time

    from .cache import cached, last

    query = {"latitude": f"{lat:.3f}", "longitude": f"{lon:.3f}", "hourly": ",".join(FIELDS), "timezone": "UTC",
             "forecast_days": str(days), "wind_speed_unit": "ms"}  # fmt: skip
    url = URL + "?" + urllib.parse.urlencode(query)

    def now():
        if fetch:
            return fetch(url)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (a fixed https service)
            return json.loads(r.read())

    out = parse(cached("forecast", url, now))
    when = last.get("forecast")
    out["issued"] = float(Time(when[0], format="unix").jd) if when else None
    return out


def during(f, start, end):
    """The forecast hours between start and end (JD UTC) and their mean total cloud cover (%), or None."""
    t = np.asarray(f["time"], float)
    inside = (t >= start - 1 / 48) & (t <= end + 1 / 48)
    if not inside.any():
        return None
    return float(np.nanmean(np.asarray(f["cloud"], float)[inside]))
