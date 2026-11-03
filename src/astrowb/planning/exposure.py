"""Exposure time for a wanted signal-to-noise, and the signal-to-noise of an exposure (the CCD equation,
Howell 2006, "Handbook of CCD Astronomy", eq. 4.4).

S/N = S t / sqrt(S t + n (B + D) t + n R^2), with S the star's electrons per second (from its magnitude and the
system's zero point: the magnitude giving one electron per second), B the sky and D the dark current in electrons
per pixel per second, R the read noise in electrons and n the pixels in the aperture.
"""

import math


def star_rate(magnitude, zero_point):
    """Electrons per second from the star."""
    return 10 ** (-0.4 * (magnitude - zero_point))


def snr(seconds, magnitude, zero_point, sky=0.0, read_noise=0.0, aperture_px=5.0, dark=0.0):
    s, n = star_rate(magnitude, zero_point), math.pi * aperture_px**2
    signal = s * seconds
    return signal / math.sqrt(signal + n * (sky + dark) * seconds + n * read_noise**2)


def exposure_time(target_snr, magnitude, zero_point, sky=0.0, read_noise=0.0, aperture_px=5.0, dark=0.0):
    """Seconds needed for target_snr: the positive root of (S t)^2 = SNR^2 (S t + n (B + D) t + n R^2)."""
    s, n = star_rate(magnitude, zero_point), math.pi * aperture_px**2
    a = s * s
    b = -(target_snr**2) * (s + n * (sky + dark))
    c = -(target_snr**2) * n * read_noise**2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def saturation_seconds(full_well, magnitude, zero_point, sky=0.0, fwhm_px=3.0, dark=0.0):
    """Seconds until the brightest pixel of a Gaussian star reaches full_well (peak = 4 ln 2 / (pi FWHM^2) of the
    flux)."""
    peak = star_rate(magnitude, zero_point) * 4 * math.log(2) / (math.pi * fwhm_px**2)
    return full_well / (peak + sky + dark)
