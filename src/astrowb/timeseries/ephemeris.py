"""Ephemerides and O-C diagrams.

Linear:     T(E) = T0 + P E
Quadratic:  T(E) = T0 + P E + Q E^2      ->  dP/dt = 2 Q / P  (days per day)
Weighted least squares with 1/sigma^2 weights; parameter errors are scaled by sqrt(chi2_r)
when chi2_r > 1 (scatter larger than the stated errors). Secondary minima sit at half-integer
epochs. Epochs are counted from the reference T0 the user gives; internally the fit is made
around the middle of the data (least correlated parameters) and transformed back with its
covariance. O-C values are relative to the user's reference ephemeris, as in the literature.
"""

from dataclasses import dataclass

import numpy as np

SECONDS_PER_YEAR = 365.25 * 86400


@dataclass
class Minimum:
    time: float
    error: float | None = None
    kind: str = "I"  # I = primary, II = secondary
    source: str = ""


def parse_minima(text: str) -> list[Minimum]:
    """Lines 'time [error] [I|II|p|s] [source...]', comma/space/tab separated; '#' starts a comment."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].replace(",", " ").replace(";", " ").strip()
        if not line:
            continue
        parts = line.split()
        try:
            time = float(parts[0])
        except ValueError:
            if not out:  # a header line
                continue
            raise ValueError(f"line {n}: '{parts[0]}' is not a time") from None
        error, kind, rest = None, "I", parts[1:]
        if rest:
            try:
                error = float(rest[0])
                rest = rest[1:]
            except ValueError:
                pass
        if rest and rest[0].upper() in ("I", "II", "P", "S", "1", "2", "PRI", "SEC"):
            kind = "II" if rest[0].upper() in ("II", "S", "2", "SEC") else "I"
            rest = rest[1:]
        out.append(Minimum(time, error, kind, " ".join(rest)))
    return out


def epochs(minima, t0, period):
    """Cycle numbers (half-integers for secondaries) relative to t0."""
    e = []
    for m in minima:
        shift = 0.5 if m.kind == "II" else 0.0
        e.append(np.round((m.time - t0) / period - shift) + shift)
    return np.array(e)


@dataclass
class Fit:
    """Parameters refer to the caller's epoch numbering (E = 0 at the reference T0 given)."""

    order: int
    t0: float
    t0_err: float
    period: float
    period_err: float
    q: float
    q_err: float
    chi2r: float
    epochs: np.ndarray
    o_minus_c: np.ndarray  # observed minus the reference ephemeris given by the caller (days)
    residuals: np.ndarray  # observed minus the fitted model (days)
    ref_t0: float
    ref_period: float

    def model_o_minus_c(self, e):
        """The fitted ephemeris drawn in the O-C diagram of the reference ephemeris."""
        e = np.asarray(e, float)
        return (self.t0 - self.ref_t0) + (self.period - self.ref_period) * e + self.q * e**2

    @property
    def dp_dt(self):
        """Period change in seconds per year (quadratic fits)."""
        return 2 * self.q / self.period * SECONDS_PER_YEAR

    @property
    def dp_dt_err(self):
        return 2 * self.q_err / self.period * SECONDS_PER_YEAR


def fit(minima, t0_ref, period_ref, order=1, default_error=None) -> Fit:
    """Fit a linear (order=1) or quadratic (order=2) ephemeris; epochs are counted from t0_ref."""
    times = np.array([m.time for m in minima], float)
    errs = np.array([m.error if m.error else np.nan for m in minima], float)
    if np.isnan(errs).any():
        fallback = default_error or (np.nanmedian(errs) if np.isfinite(errs).any() else 1.0)
        errs = np.where(np.isnan(errs), fallback, errs)
    if len(times) < order + 1:
        raise ValueError(f"need at least {order + 1} minima")
    e = epochs(minima, t0_ref, period_ref)
    mid = float(np.round(np.median(e)))  # fit around the middle of the data: least correlated parameters
    mid_time = t0_ref + mid * period_ref
    a = np.vander(e - mid, order + 1, increasing=True)  # columns 1, E', E'^2
    w = 1 / errs
    coef, *_ = np.linalg.lstsq(a * w[:, None], (times - mid_time) * w, rcond=None)  # small numbers: no JD rounding
    resid = times - mid_time - a @ coef
    dof = max(1, len(times) - (order + 1))
    chi2r = float(np.sum((resid / errs) ** 2) / dof)
    cov = np.linalg.inv((a * w[:, None]).T @ (a * w[:, None])) * max(chi2r, 1.0)
    # back to the caller's numbering: T(E) = T0 + P E + Q E^2 with E = E' + mid
    m = np.array([[1, -mid, mid**2], [0, 1, -2 * mid], [0, 0, 1]])[: order + 1, : order + 1]
    c = m @ coef
    sd = np.sqrt(np.diag(m @ cov @ m.T))
    return Fit(
        order=order,
        t0=float(mid_time + c[0]),
        t0_err=float(sd[0]),
        period=float(c[1]),
        period_err=float(sd[1]),
        q=float(c[2]) if order == 2 else 0.0,
        q_err=float(sd[2]) if order == 2 else 0.0,
        chi2r=chi2r,
        epochs=e,
        o_minus_c=times - (t0_ref + period_ref * e),
        residuals=resid,
        ref_t0=t0_ref,
        ref_period=period_ref,
    )
