"""Precise pointing from plate solves: centre a target (slew, solve, sync, slew again) and measure the
polar-alignment error of an equatorial mount (three solves while only the RA axis turns).

Polar alignment: the image centre moves on a circle around the mount's RA axis when only that axis turns.
Three image centres in a frame that turns with the Earth (hour angle, declination) give that circle's axis;
its distance from the celestial pole, split into altitude and azimuth, is the alignment error.
"""

import numpy as np


def image_centre(wcs_header, shape):
    """Sky position (ICRS SkyCoord) of the image centre from a plate solution."""
    from astropy.wcs import WCS

    ny, nx = shape
    return WCS(wcs_header).pixel_to_world((nx - 1) / 2, (ny - 1) / 2)


def center(obs, target, take_solved_centre, tolerance_arcsec=30.0, max_iterations=5):
    """Slew to target, then until the image centre is within tolerance: sync the mount on the solved
    position and slew again. take_solved_centre() exposes, solves and returns the centre (SkyCoord).
    Returns the pointing errors in arcsec, one per image."""
    errors = []
    obs.slew(target)
    for _ in range(max_iterations):
        actual = take_solved_centre()
        errors.append(float(actual.separation(target).arcsec))
        obs.note(f"centring: {errors[-1]:.0f} arcsec from the target")
        if errors[-1] <= tolerance_arcsec:
            return errors
        ra, dec = obs._to_mount(actual, obs.now())
        obs.call("mount", "SyncToCoordinates", ra, dec)  # the mount now knows where it really points
        obs.slew(target)
    raise RuntimeError(f"not centred after {max_iterations} images ({errors[-1]:.0f} arcsec off)")


def _unit(ha_deg, dec_deg):
    h, d = np.radians(ha_deg), np.radians(dec_deg)
    return np.array([np.cos(d) * np.cos(h), -np.cos(d) * np.sin(h), np.sin(d)])  # x: meridian, z: pole


def ra_axis(points):
    """Direction (ha, dec in degrees) of the axis of the circle through three (ha, dec) points."""
    a, b, c = (_unit(*p) for p in points)
    n = np.cross(b - a, c - b)
    if np.linalg.norm(n) < 1e-9:
        raise ValueError("the three positions are too close together: turn the RA axis further")
    n /= np.linalg.norm(n)
    if n[2] < 0:  # the pole above the horizon on this side
        n = -n
    return float(np.degrees(np.arctan2(-n[1], n[0]))), float(np.degrees(np.arcsin(np.clip(n[2], -1, 1))))


def altaz(ha_deg, dec_deg, lat_deg):
    """(alt, az) in degrees of an hour-angle / declination direction at latitude lat (az from north, east)."""
    h, d, p = np.radians(ha_deg), np.radians(dec_deg), np.radians(lat_deg)
    alt = np.arcsin(np.sin(d) * np.sin(p) + np.cos(d) * np.cos(p) * np.cos(h))
    az = np.arctan2(-np.cos(d) * np.sin(h), np.sin(d) * np.cos(p) - np.cos(d) * np.sin(p) * np.cos(h))
    return float(np.degrees(alt)), float(np.degrees(az) % 360)


def polar_error(points, lat_deg):
    """Alignment error of the RA axis in arcmin: (total, altitude, azimuth). Positive altitude: the axis
    points too high; positive azimuth: too far east. Northern and southern hemisphere."""
    ha, dec = ra_axis(points)
    if lat_deg < 0:  # southern sky: the south celestial pole is the reference
        ha, dec = (ha + 180) % 360, -dec
    alt, az = altaz(ha, dec, lat_deg)
    pole_alt, pole_az = abs(lat_deg), (0.0 if lat_deg >= 0 else 180.0)
    d_az = ((az - pole_az + 180) % 360 - 180) * np.cos(np.radians(alt))  # on the sky, not along the horizon
    total = 60 * (90 - abs(dec))
    return float(total), float(60 * (alt - pole_alt)), float(60 * d_az)


def hadec(coord, time, location):
    """Apparent (hour angle, declination) in degrees of a sky position at a time and place."""
    from astropy.coordinates import HADec

    c = coord.transform_to(HADec(obstime=time, location=location))
    return float(c.ha.deg % 360), float(c.dec.deg)
