"""PLN-11: a recorded Open-Meteo answer parsed; the hour's cloud read for a block; offline shows the last forecast."""

import numpy as np
import pytest

from astrowb.services import forecast
from astrowb.services.cache import OfflineError

ANSWER = {"latitude": 36.82, "longitude": 30.33, "hourly_units": {"time": "iso8601", "cloud_cover": "%"},
          "hourly": {"time": ["2026-11-14T18:00", "2026-11-14T19:00", "2026-11-14T20:00", "2026-11-14T21:00"],
                     "cloud_cover": [100, 60, 10, None], "cloud_cover_low": [80, 20, 0, 0],
                     "cloud_cover_mid": [50, 40, 10, 0], "cloud_cover_high": [10, 10, 0, 0],
                     "relative_humidity_2m": [90, 80, 70, 65], "dew_point_2m": [3.0, 2.5, 2.0, 1.8],
                     "wind_speed_10m": [4.0, 3.5, 3.0, 2.0], "temperature_2m": [5.0, 4.5, 4.0, 3.5]}}  # fmt: skip


def test_a_recorded_answer(monkeypatch):
    calls = []
    f = forecast.forecast(36.82, 30.33, fetch=lambda url: calls.append(url) or ANSWER)
    assert "cloud_cover_low" in calls[0] and "timezone=UTC" in calls[0]
    assert f["cloud"][:3] == [100.0, 60.0, 10.0] and np.isnan(f["cloud"][3]) and f["wind"][0] == 4.0
    assert f["time"][2] == pytest.approx(2461359.3333, abs=1e-4)  # 2026-11-14 20:00 UTC
    assert f["source"] == forecast.ATTRIBUTION and f["issued"] is not None
    assert forecast.during(f, f["time"][1], f["time"][2]) == pytest.approx(35.0)
    monkeypatch.setenv("ASTROWB_OFFLINE", "1")
    again = forecast.forecast(36.82, 30.33, fetch=lambda url: calls.append(url) or {})
    assert again["cloud"][:3] == f["cloud"][:3] and len(calls) == 1  # the last forecast, from the cache
    with pytest.raises(OfflineError):
        forecast.forecast(10.0, 10.0, fetch=lambda url: ANSWER)


def test_an_empty_answer():
    with pytest.raises(LookupError):
        forecast.parse({"hourly": {}})
