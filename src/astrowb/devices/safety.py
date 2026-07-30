"""Safety rules for telescope control. Pure functions: no device, no UI.

Every slew and every exposure start is checked here first; the observatory supervisor applies
the same rules continuously. The rules are deliberately conservative and fail closed: when a
value cannot be determined (no time, no weather data, device not answering), the answer is
"not safe".

1. Sun:      target farther than sun_min_sep from the Sun; no slews while the Sun is above
             sun_max_alt unless daytime is explicitly allowed (and the Sun rule still applies).
             The supervisor applies the same to an unparked mount: at dawn it parks and closes.
2. Horizon:  target above the horizon profile (azimuth -> minimum altitude) and min_alt.
3. Weather:  SafetyMonitor IsSafe and every configured ObservingConditions limit.
4. Link:     a device that has not answered for longer than link_timeout_s is unsafe.
"""

from dataclasses import dataclass, field

import numpy as np
from astropy.coordinates import AltAz, SkyCoord, get_body
from astropy.time import Time

from .. import timing  # noqa: F401  (offline IERS settings)


@dataclass
class Rules:
    sun_min_sep: float = 30.0  # deg between target and Sun
    sun_max_alt: float = -6.0  # deg; above this it is "day"
    allow_daytime: bool = False
    min_alt: float = 15.0  # deg
    horizon: list = field(default_factory=list)  # [(az_deg, min_alt_deg), ...]
    max_humidity: float | None = 90.0  # %
    max_wind: float | None = 12.0  # m/s
    max_rain_rate: float | None = 0.0  # mm/h; any rain is unsafe
    max_cloud_cover: float | None = None  # %
    link_timeout_s: float = 30.0

    def horizon_alt(self, az_deg):
        """Minimum altitude at azimuth (linear interpolation of the profile, wrapping at 360)."""
        if not self.horizon:
            return self.min_alt
        az, alt = np.array(self.horizon, float).T
        return max(self.min_alt, float(np.interp(az_deg % 360, az % 360, alt, period=360)))


def check_target(coord: SkyCoord, time: Time, location, rules: Rules) -> list[str]:
    """Reasons why pointing at coord now is unsafe; empty list = safe."""
    reasons = []
    frame = AltAz(obstime=time, location=location)
    sun = get_body("sun", time, location)
    sun_alt = sun.transform_to(frame).alt.deg
    sep = sun.separation(coord.transform_to(sun)).deg  # both in the Sun's (GCRS) frame
    if sep < rules.sun_min_sep:
        reasons.append(f"target is {sep:.1f} deg from the Sun (limit {rules.sun_min_sep:.0f})")
    if sun_alt > rules.sun_max_alt and not rules.allow_daytime:
        reasons.append(f"the Sun is up ({sun_alt:.1f} deg); daytime slews are not allowed")
    aa = coord.transform_to(frame)
    limit = rules.horizon_alt(aa.az.deg)
    if aa.alt.deg < limit:
        reasons.append(f"target altitude {aa.alt.deg:.1f} deg is below the limit {limit:.1f} deg at az {aa.az.deg:.0f}")
    return reasons


def check_sun(pointing: SkyCoord | None, time: Time, location, rules: Rules) -> list[str]:
    """For an unparked telescope: the Sun must be below sun_max_alt (unless daytime is allowed) and
    the telescope must not point within sun_min_sep of it."""
    frame = AltAz(obstime=time, location=location)
    sun = get_body("sun", time, location)
    reasons = []
    sun_alt = sun.transform_to(frame).alt.deg
    if sun_alt > rules.sun_max_alt and not rules.allow_daytime:
        reasons.append(f"the Sun is up ({sun_alt:.1f} deg): night is over")
    if pointing is not None:
        sep = sun.separation(pointing.transform_to(sun)).deg
        if sep < rules.sun_min_sep:
            reasons.append(f"the telescope points {sep:.1f} deg from the Sun")
    return reasons


def check_weather(is_safe, conditions: dict, rules: Rules) -> list[str]:
    """is_safe: SafetyMonitor value or None (no monitor). conditions: {humidity, windspeed, rainrate,
    cloudcover} with None for sensors that are absent. Absent sensors are not checked; a monitor or
    sensor that failed to answer must be passed as the string "error" and makes it unsafe."""
    reasons = []
    if is_safe == "error":
        reasons.append("safety monitor is not answering")
    elif is_safe is False:
        reasons.append("safety monitor reports unsafe")
    limits = (
        ("humidity", rules.max_humidity, "%"),
        ("windspeed", rules.max_wind, " m/s"),
        ("rainrate", rules.max_rain_rate, " mm/h"),
        ("cloudcover", rules.max_cloud_cover, "%"),
    )
    for key, limit, unit in limits:
        value = conditions.get(key)
        if value == "error":
            reasons.append(f"{key} sensor is not answering")
        elif limit is not None and value is not None and value > limit:
            reasons.append(f"{key} {value:g}{unit} is above the limit {limit:g}{unit}")
    return reasons


def check_link(last_answer_s_ago: dict, rules: Rules) -> list[str]:
    """last_answer_s_ago: {device name: seconds since its last successful answer}."""
    return [
        f"{name} has not answered for {age:.0f} s"
        for name, age in last_answer_s_ago.items()
        if age > rules.link_timeout_s
    ]
