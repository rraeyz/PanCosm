"""The light-curve container (plans/period.md PER-1 items 1, 4, 5): time with its standard, flux or magnitude
with errors, the data set and band of every point, flags, metadata; joining sets by zero points fitted with the
periodic model; weights.

Flags are bits: USER (left out by the user), OUTLIER, QUALITY (bad by the source), UPPER (an upper limit); a point
is used when its flag is 0. Selections return new containers over copies of the selected rows only.
"""

from dataclasses import dataclass, field

import numpy as np

USER, OUTLIER, QUALITY, UPPER = 1, 2, 4, 8


@dataclass
class LightCurve:
    time: np.ndarray
    value: np.ndarray
    error: np.ndarray | None = None
    set: np.ndarray | None = None
    band: np.ndarray | None = None
    flag: np.ndarray | None = None
    standard: str = "BJD_TDB"
    magnitude: bool = False
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        n = len(self.time)
        self.time = np.asarray(self.time, float)
        self.value = np.asarray(self.value, float)
        self.error = None if self.error is None else np.asarray(self.error, float)
        self.set = np.zeros(n, int) if self.set is None else np.asarray(self.set, int)
        self.band = np.full(n, "", object) if self.band is None else np.asarray(self.band, object)
        self.flag = np.zeros(n, np.uint8) if self.flag is None else np.asarray(self.flag, np.uint8)

    def __len__(self):
        return len(self.time)

    @property
    def used(self):
        return self.flag == 0

    def select(self, mask):
        err = None if self.error is None else self.error[mask]
        return LightCurve(self.time[mask], self.value[mask], err, self.set[mask], self.band[mask], self.flag[mask],
                          self.standard, self.magnitude, dict(self.meta))  # fmt: skip

    def flagged(self, mask, bit):
        """A copy with bit set where mask holds."""
        out = self.select(slice(None))
        out.flag = np.where(mask, out.flag | bit, out.flag).astype(np.uint8)
        return out

    def to_mag(self, zero_point=0.0):
        if self.magnitude:
            return self
        err = None if self.error is None else 2.5 / np.log(10) * self.error / self.value
        return LightCurve(self.time, zero_point - 2.5 * np.log10(self.value), err, self.set, self.band, self.flag,
                          self.standard, True, self.meta | {"zero_point": zero_point})  # fmt: skip

    def to_flux(self, zero_point=None):
        if not self.magnitude:
            return self
        zp = self.meta.get("zero_point", 0.0) if zero_point is None else zero_point
        flux = 10 ** (-0.4 * (self.value - zp))
        err = None if self.error is None else self.error * flux * np.log(10) / 2.5
        return LightCurve(self.time, flux, err, self.set, self.band, self.flag, self.standard, False, dict(self.meta))

    def normalised(self):
        """Each set divided by (flux) or less (magnitude) its median of used points."""
        v = self.value.copy()
        e = None if self.error is None else self.error.copy()
        for s in np.unique(self.set):
            sel = self.set == s
            ref = np.median(self.value[sel & self.used]) if (sel & self.used).any() else np.median(self.value[sel])
            if self.magnitude:
                v[sel] -= ref
            else:
                v[sel] /= ref
                if e is not None:
                    e[sel] /= ref
        return LightCurve(self.time, v, e, self.set, self.band, self.flag, self.standard, self.magnitude,
                          dict(self.meta))  # fmt: skip

    def phase(self, period, epoch):
        return ((self.time - epoch) / period) % 1.0

    def append(self, other):
        """Both curves as one, the other's sets numbered after this one's."""
        if other.magnitude != self.magnitude or other.standard != self.standard:
            raise ValueError("append curves in the same unit and time standard")
        shift = int(self.set.max()) + 1 if len(self) else 0
        err = None if self.error is None or other.error is None else np.concatenate([self.error, other.error])

        def both(name):
            return np.concatenate([getattr(self, name), getattr(other, name)])

        return LightCurve(both("time"), both("value"), err, np.concatenate([self.set, other.set + shift]),
                          both("band"), both("flag"), self.standard, self.magnitude, dict(self.meta))  # fmt: skip

    def to_table(self):
        from astropy.table import Table

        cols = {"time": self.time, "value": self.value, "set": self.set, "band": self.band.astype(str),
                "flag": self.flag}  # fmt: skip
        if self.error is not None:
            cols["error"] = self.error
        t = Table(cols)
        t.meta.update(self.meta | {"standard": self.standard, "magnitude": self.magnitude})
        return t

    @classmethod
    def from_table(cls, t):
        meta = dict(t.meta)
        standard, mag = meta.pop("standard", "BJD_TDB"), bool(meta.pop("magnitude", False))
        err = np.asarray(t["error"]) if "error" in t.colnames else None
        return cls(np.asarray(t["time"]), np.asarray(t["value"]), err, np.asarray(t["set"]),
                   np.asarray(t["band"], object), np.asarray(t["flag"]), standard, mag, meta)  # fmt: skip


def zero_points(lc, freqs, t_ref=None):
    """Per-set offsets fitted together with sinusoids of the given frequencies (Period04's "adjust zero points"):
    {set: (offset relative to the first set, its error)}; subtract them to join the sets."""
    use = lc.used
    t = lc.time[use] - (np.mean(lc.time[use]) if t_ref is None else t_ref)
    sets = np.unique(lc.set[use])
    cols = [(lc.set[use] == s).astype(float) for s in sets]
    for f in freqs:
        cols += [np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)]
    w = np.ones(use.sum()) if lc.error is None else 1 / lc.error[use]
    a = np.column_stack(cols) * w[:, None]
    coef, *_ = np.linalg.lstsq(a, lc.value[use] * w, rcond=None)
    r = lc.value[use] * w - a @ coef
    cov = np.linalg.inv(a.T @ a) * (r @ r / max(len(r) - len(coef), 1))
    out = {}
    for i, s in enumerate(sets):
        var = cov[i, i] + cov[0, 0] - 2 * cov[i, 0]
        out[int(s)] = (float(coef[i] - coef[0]), float(np.sqrt(max(var, 0.0))))
    return out


def weights(lc, kind="none", residuals=None):
    """Point weights: "none"; "errors" (1/σ²); "set" (1 / the variance of each set's residuals, which must be
    given); "deviation" (Period04's: 1 inside 2 σ of the residuals, (2σ / |r|)² outside)."""
    n = len(lc)
    if kind == "none":
        return np.ones(n)
    if kind == "errors":
        return 1 / lc.error**2
    r = np.asarray(residuals, float)
    if kind == "set":
        w = np.empty(n)
        for s in np.unique(lc.set):
            sel = lc.set == s
            w[sel] = 1 / np.var(r[sel])
        return w
    if kind == "deviation":
        cut = 2 * np.std(r)
        return np.where(np.abs(r) <= cut, 1.0, (cut / np.abs(r)) ** 2)
    raise ValueError(f"unknown weighting: {kind}")
