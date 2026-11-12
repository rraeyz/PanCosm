"""A binary-star system to fit (plans/models.md MOD-10): parameters, data sets, morphology constraints, exact
conversions between parameterisations, checks before a run, and a human-readable TOML system file.

Morphology: "detached" (no constraint), "semi-detached-1" / "semi-detached-2" (that star fills its lobe:
Ω = Ω_in(q)), "contact" (Ω₂ = Ω₁, both set by the fill-out f, which is then the free parameter). Potentials of
star 2 are in its own frame (mass ratio 1/q), as models.roche_lc builds it.
"""

import tomllib
from dataclasses import dataclass, field

import numpy as np

from . import roche


@dataclass
class Parameter:
    key: str
    value: float
    free: bool = False
    lower: float = -np.inf
    upper: float = np.inf
    prior: tuple = ()  # () none, ("uniform", lo, hi), ("gaussian", mu, sigma)
    unit: str = ""
    locked: str = ""  # why it is set by a constraint ("" when not)


@dataclass
class DataSet:
    kind: str  # "lc" (with band), "rv1", "rv2", "minima"
    time: np.ndarray
    value: np.ndarray
    error: np.ndarray | None = None
    band: str = ""
    exposure: float = 0.0
    noise_scale: float = 1.0
    zero_point: float = 0.0


@dataclass
class System:
    params: dict = field(default_factory=dict)
    data: list = field(default_factory=list)
    morphology: str = "detached"

    def __getitem__(self, key):
        return self.params[key].value

    def set(self, key, value):
        self.params[key].value = float(value)
        self.apply()

    def apply(self):
        """Impose the morphology on the potentials; the rows it sets are marked locked with the reason."""
        p = self.params
        for k in ("omega1", "omega2"):
            p[k].locked = ""
        q = p["q"].value
        if self.morphology == "semi-detached-1":
            p["omega1"].value, p["omega1"].locked = roche.critical(q)[0], "star 1 fills its Roche lobe"
        elif self.morphology == "semi-detached-2":
            p["omega2"].value, p["omega2"].locked = roche.critical(1 / q)[0], "star 2 fills its Roche lobe"
        elif self.morphology == "contact":
            om = roche.omega_from_fillout(p["fillout"].value, q)
            p["omega1"].value, p["omega1"].locked = om, "set by the fill-out (contact)"
            p["omega2"].value, p["omega2"].locked = to_own_frame(om, q), "the same surface as star 1 (contact)"
        elif self.morphology != "detached":
            morphology = self.morphology
            raise ValueError(f"unknown morphology: {morphology}")

    def free(self):
        return [k for k, v in self.params.items() if v.free and not v.locked]


def to_own_frame(omega1_frame, q):
    """Star 1's potential value of a surface → the same surface's value in star 2's frame (mass ratio 1/q)."""
    return omega1_frame / q + (q - 1) / (2 * q)


def from_own_frame(omega2_own, q):
    return q * (omega2_own - (q - 1) / (2 * q))


def default_system(q=0.8, r1=0.25, r2=0.2, incl=85.0, period=1.0, t0=0.0, t1=6000.0, t2=5500.0):
    s = System({
        "period": Parameter("period", period, unit="d"), "t0": Parameter("t0", t0, True, unit="d"),
        "q": Parameter("q", q, True, 0.01, 100.0), "incl": Parameter("incl", incl, True, 0, 90, unit="deg"),
        "omega1": Parameter("omega1", roche.omega_for_volume_radius(r1, q), True),
        "omega2": Parameter("omega2", roche.omega_for_volume_radius(r2, 1 / q), True),
        "fillout": Parameter("fillout", 0.0), "e": Parameter("e", 0.0, False, 0, 0.99),
        "w": Parameter("w", 90.0, unit="deg"), "t1": Parameter("t1", t1, unit="K"),
        "t2": Parameter("t2", t2, True, unit="K"), "l3": Parameter("l3", 0.0, False, 0, 1),
    })  # fmt: skip
    s.apply()
    return s


# --- parameterisations, both ways exact ---------------------------------------------------------------------


def radii_to_sum_ratio(r1, r2):
    return r1 + r2, r2 / r1


def sum_ratio_to_radii(total, k):
    r1 = total / (1 + k)
    return r1, total - r1


def e_w_to_cos_sin(e, w_deg):
    w = np.radians(w_deg)
    return e * np.cos(w), e * np.sin(w)


def cos_sin_to_e_w(c, s):
    return float(np.hypot(c, s)), float(np.degrees(np.arctan2(s, c)) % 360.0)


def e_w_to_sqrt(e, w_deg):
    w = np.radians(w_deg)
    return np.sqrt(e) * np.cos(w), np.sqrt(e) * np.sin(w)


def sqrt_to_e_w(c, s):
    return float(c * c + s * s), float(np.degrees(np.arctan2(s, c)) % 360.0)


# --- checks before a run ------------------------------------------------------------------------------------

CHECKS = {
    "T0_FAR": "the reference time is more than a thousand periods from the data",
    "NO_PERIOD": "the period is missing",
    "BEYOND_LOBE": "a star of a detached set-up is beyond its Roche lobe",
    "RV_FIXED_A": "velocity data are fitted with the semi-major axis fixed",
    "L3_INCL": "third light free in every band together with the inclination on a partial eclipse: they trade off",
}


def check(system, partial_eclipse=False):
    """The codes of what looks wrong (CHECKS gives the advice); none forbids a run."""
    p, out = system.params, []
    if not p["period"].value > 0:
        out.append("NO_PERIOD")
    times = np.concatenate([d.time for d in system.data]) if system.data else np.array([])
    if times.size and p["period"].value > 0 and np.min(np.abs(times - p["t0"].value)) > 1000 * p["period"].value:
        out.append("T0_FAR")
    if system.morphology == "detached":
        q = p["q"].value
        if p["omega1"].value < roche.critical(q)[0] or p["omega2"].value < roche.critical(1 / q)[0]:
            out.append("BEYOND_LOBE")
    if any(d.kind in ("rv1", "rv2") for d in system.data) and "a" in p and not p["a"].free:
        out.append("RV_FIXED_A")
    if partial_eclipse and p["incl"].free and p["l3"].free:
        out.append("L3_INCL")
    return out


# --- the system file ----------------------------------------------------------------------------------------


def _value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (tuple, list)):
        return "[" + ", ".join(_value(x) for x in v) + "]"
    v = float(v)
    return "inf" if v == np.inf else "-inf" if v == -np.inf else repr(v)


def to_toml(system):
    """The parameters and the morphology as a TOML file people can read and edit (data sets stay in the
    session)."""
    lines = [f"morphology = {_value(system.morphology)}", ""]
    for k, p in system.params.items():
        lines.append(f"[parameters.{k}]")
        for name in ("value", "free", "lower", "upper", "prior", "unit"):
            lines.append(f"{name} = {_value(getattr(p, name))}")
        lines.append("")
    return "\n".join(lines)


def from_toml(text):
    doc = tomllib.loads(text)
    params = {k: Parameter(k, v["value"], v["free"], v["lower"], v["upper"], tuple(v["prior"]), v["unit"])
              for k, v in doc["parameters"].items()}  # fmt: skip
    s = System(params, morphology=doc["morphology"])
    s.apply()
    return s
