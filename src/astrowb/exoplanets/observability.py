"""Can I see this transit, and is it worth it? (plans/exoplanets.md EXO-14): the precision of one exposure (the CCD
equation of planning.exposure and scintillation), the transit's detectability in σ, and a ranking of coming
transits by detectability and by the value of a new mid-time (how far the ephemeris has drifted).

Scintillation: photometry.aperture.scintillation (Osborn et al. 2015).
"""

import math

from ..photometry.aperture import scintillation as _osborn
from ..planning.exposure import snr


def scintillation(diameter_cm, airmass, altitude_m, seconds):
    return float(_osborn(diameter_cm / 100, seconds, airmass, altitude_m))


def precision(seconds, magnitude, zero_point, diameter_cm, airmass=1.2, altitude_m=0.0, sky=0.0, read_noise=0.0,
              aperture_px=5.0, n_comparisons=3):  # fmt: skip
    """The relative scatter of one differential measurement: the target's noise and its comparisons' (their mean as
    bright as the target, n of them) with scintillation in each."""
    phot = 1 / snr(seconds, magnitude, zero_point, sky, read_noise, aperture_px)
    one = math.hypot(phot, scintillation(diameter_cm, airmass, altitude_m, seconds))
    return one * math.sqrt(1 + 1 / n_comparisons)


def detectability(depth, sigma_exposure, cadence_s, duration_h, baseline_h):
    """The transit's depth in units of its error: σ_exp √(1/n_in + 1/n_out), n the exposures in and out."""
    n_in = duration_h * 3600 / cadence_s
    n_out = baseline_h * 3600 / cadence_s
    return depth / (sigma_exposure * math.sqrt(1 / n_in + 1 / n_out))


def rank(events, key_weights=(1.0, 1.0)):
    """events: dicts with "snr" (detectability) and "drift" (the ephemeris' 1σ at that transit, minutes);
    returns them best first by snr^a × drift^b (a, b = key_weights), those under 3σ last."""
    a, b = key_weights

    def score(ev):
        return (ev["snr"] >= 3, ev["snr"] ** a * max(ev["drift"], 1e-3) ** b)

    return sorted(events, key=score, reverse=True)
