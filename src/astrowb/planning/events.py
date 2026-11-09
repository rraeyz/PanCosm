"""How well an event's time is known (plans/planning.md PLN-4): the ephemeris T0 + E·P carries the errors of T0 and
P, and the error of P grows with the number of cycles since T0 (Mallonn et al. 2019; Kokori et al. 2022, ExoClock):

    σ(E) = √(σ_T0² + (E σ_P)² + 2 E cov(T0, P))

A catalogue that gives no error still says how precisely it knows a number by the digits it prints (VSX gives the
period to the digits its authors trust): half a unit of the last digit, and the result says it was estimated.
"""

import numpy as np


def digits_error(text):
    """Half a unit of the last printed digit of a number as text ("0.1010159" → 5e-8); None for no decimals."""
    text = str(text).strip().lower()
    mantissa, _, exponent = text.partition("e")
    if "." not in mantissa:
        return None
    decimals = len(mantissa.split(".")[1])
    return 0.5 * 10.0 ** (-decimals) * 10.0 ** (int(exponent) if exponent else 0)


def sigma(epoch, t0_err, period_err, cov=0.0):
    """σ of the predicted time (days) E cycles after T0."""
    e = np.asarray(epoch, float)
    return np.sqrt(np.square(t0_err) + np.square(e * period_err) + 2 * e * cov)


def ephemeris_errors(target):
    """(σ_T0, σ_P, cov, estimated) of a target dict: its t0_err / period_err when given, else estimated from the
    digits of t0_text / period_text, else (None, None, 0, False)."""
    t0_err, p_err = target.get("t0_err"), target.get("period_err")
    estimated = False
    if t0_err is None and target.get("t0_text"):
        t0_err, estimated = digits_error(target["t0_text"]), True
    if p_err is None and target.get("period_text"):
        p_err, estimated = digits_error(target["period_text"]), True
    if t0_err is None or p_err is None:
        return None, None, 0.0, False
    return float(t0_err), float(p_err), float(target.get("cov", 0.0)), estimated


def annotate(event, target):
    """The event dict (planning.night's) with "epoch", "sigma_min" and "sigma_estimated" when the target's
    ephemeris errors are known or can be estimated."""
    t0_err, p_err, cov, estimated = ephemeris_errors(target)
    if t0_err is None:
        return event
    shift = 0.5 if event.get("kind") == "secondary" else 0.0
    epoch = round((event["mid"] - target["t0"]) / target["period"] - shift)
    s = float(sigma(epoch + shift, t0_err, p_err, cov)) * 1440
    return event | {"epoch": int(epoch), "sigma_min": s, "sigma_estimated": estimated}
