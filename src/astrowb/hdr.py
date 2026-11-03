"""Numbers from FITS header values as capture programs write them: plain numbers, but also text such as
'2496.00 / Meters', '10 s', '-95.5C' or '1,5'. A value with no number in front gives the default."""

import math
import re

_NUMBER = re.compile(r"\s*([-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eEdD][-+]?\d+)?)")


def number(value, default=None):
    """The number a header value starts with, as float; default when there is none (or it is NaN)."""
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else default
    m = _NUMBER.match(str(value))
    if not m:
        return default
    x = float(m[1].replace(",", ".").replace("d", "e").replace("D", "e"))
    return x if math.isfinite(x) else default


def get(header, *keys, default=None):
    """The first of keys whose value is a number."""
    for key in keys:
        if key in header:
            x = number(header[key])
            if x is not None:
                return x
    return default
