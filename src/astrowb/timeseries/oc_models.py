"""O-C models beyond a polynomial ephemeris.

Light-travel-time effect (LTTE) of a third body (Irwin 1952, ApJ 116, 211): the eclipsing pair orbits the
system's centre of mass, so the eclipses come early or late by
    tau(E) = A [ (1 - e^2) / (1 + e cos nu) sin(nu + omega) + e sin omega ],   A = a12 sin i / c,
with nu the true anomaly of the third-body orbit (period P3, periastron T3) at the time of minimum.
Mass function f(m3) = (a12 sin i)^3 / P3^2 (AU, years, solar masses).

Apsidal motion, first order in e (Gimenez & Garcia-Pelayo 1983, i ~ 90 deg): with omega = omega0 + d_omega E,
    T_I  = T0 + Ps E - (Pa / pi) e cos omega
    T_II = T0 + Ps E + Pa / 2 + (Pa / pi) e cos omega
so primary and secondary O-C swing in opposite directions over the apsidal period U = 360 / d_omega cycles.
shortcut: first order in e; for e > ~0.1 the higher-order terms (and the inclination) matter.

Both are fitted by searching the slow period on a grid (for a fixed period the model is linear in the rest,
or nearly) and refining every parameter with least squares. On request (mcmc_steps > 0) an emcee chain around the
least-squares solution gives 68 % intervals of every parameter, e and omega included (as OCFit does); the
least-squares errors come from a linearised covariance and miss how the parameters depend on each other.
"""

from dataclasses import dataclass

import numpy as np

AU_PER_LIGHT_DAY = 173.1446  # c x 1 day in AU
DAYS_PER_YEAR = 365.25


@dataclass
class LTTEFit:
    t0: float
    period: float
    amplitude: float  # A = a12 sin i / c, days
    p3: float  # days
    t3: float  # periastron time of the third-body orbit
    e: float
    omega: float  # deg
    errors: dict
    chi2r: float
    epochs: np.ndarray
    o_minus_c: np.ndarray
    residuals: np.ndarray
    ref_t0: float
    ref_period: float
    mcmc: dict | None = None  # {"params": {name: (median, minus, plus)}, "acceptance": a}

    def tau(self, e_cycles):
        return _tau(
            self.ref_t0 + self.ref_period * np.asarray(e_cycles, float),
            self.amplitude,
            self.p3,
            self.t3,
            self.e,
            self.omega,
        )

    def model_o_minus_c(self, e_cycles, kind="I"):
        e_cycles = np.asarray(e_cycles, float)
        return (self.t0 - self.ref_t0) + (self.period - self.ref_period) * e_cycles + self.tau(e_cycles)

    @property
    def mass_function(self):
        """f(m3) in solar masses."""
        return (self.amplitude * AU_PER_LIGHT_DAY) ** 3 / (self.p3 / DAYS_PER_YEAR) ** 2


@dataclass
class ApsidalFit:
    t0: float
    period: float  # sidereal
    e: float
    omega0: float  # deg at E = 0
    d_omega: float  # deg per cycle
    errors: dict
    chi2r: float
    epochs: np.ndarray
    o_minus_c: np.ndarray
    residuals: np.ndarray
    ref_t0: float
    ref_period: float
    mcmc: dict | None = None

    @property
    def u_years(self):
        """Apsidal period."""
        return 360.0 / self.d_omega * self.period / DAYS_PER_YEAR if self.d_omega else np.inf

    def model_o_minus_c(self, e_cycles, kind="I"):
        e_cycles = np.asarray(e_cycles, float)
        shift = 0.5 if kind == "II" else 0.0
        e_int = e_cycles - shift
        x = _apsidal(e_int, kind, self.t0, self.period, self.e, self.omega0, self.d_omega)
        return x - (self.ref_t0 + self.ref_period * e_cycles)


def _tau(t, a, p3, t3, e, omega_deg):
    from ..models.eb import true_anomaly

    nu = true_anomaly(t, p3, t3, e)
    w = np.radians(omega_deg)
    return a * ((1 - e**2) / (1 + e * np.cos(nu)) * np.sin(nu + w) + e * np.sin(w))


def _prepare(minima, t0_ref, period_ref):
    from .ephemeris import epochs

    times = np.array([m.time for m in minima], float)
    errs = np.array([m.error if m.error else np.nan for m in minima], float)
    errs = np.where(np.isfinite(errs), errs, np.nanmedian(errs) if np.isfinite(errs).any() else 1e-3)
    kinds = np.array([m.kind for m in minima])
    return times, errs, kinds, epochs(minima, t0_ref, period_ref)


def _covariance(sol, resid):
    """Errors from J^T J with J by central differences at the solution, each step a hundredth of the error
    least_squares' own Jacobian gives: that one (two-point, steps near rounding) carries the Kepler solver's
    noise and gave T3 errors 8 times too small on a simulated orbit (MCMC and this agree)."""
    x = sol.x
    dof = max(1, len(sol.fun) - len(x))
    chi2r = float(np.sum(sol.fun**2) / dof)
    try:
        rough = np.sqrt(np.clip(np.diag(np.linalg.inv(sol.jac.T @ sol.jac)), 0, None))
        h = np.where(np.isfinite(rough) & (rough > 0), 0.01 * rough, 1e-6 * np.maximum(np.abs(x), 1e-3))
        jac = np.column_stack(
            [(resid(x + dx) - resid(x - dx)) / (2 * hi) for hi, dx in zip(h, np.diag(h), strict=True)]
        )
        cov = np.linalg.inv(jac.T @ jac) * max(chi2r, 1.0)
        return np.sqrt(np.clip(np.diag(cov), 0, None)), chi2r
    except np.linalg.LinAlgError:
        return np.full(len(x), np.nan), chi2r


def _posterior(resid, x0, err, chi2r, physical, steps, seed=1, ctx=None):
    """{name: (median, minus, plus)} (16th / 84th percentiles) of physical(x) over an emcee chain started around
    the least-squares x0 (Goodman & Weare 2010). Flat priors on the fitted parameters; chi2 is divided by
    chi2r > 1 as the least-squares errors are scaled."""
    import emcee

    s = max(chi2r, 1.0)

    def log_prob(x):
        r = resid(x)
        v = -0.5 * float(r @ r) / s
        return v if np.isfinite(v) else -np.inf

    ndim = len(x0)
    walkers = max(24, 4 * ndim)
    rng = np.random.default_rng(seed)
    scale = np.where(np.isfinite(err) & (err > 0), err, 1e-6 * np.maximum(np.abs(x0), 1.0))
    sampler = emcee.EnsembleSampler(walkers, ndim, log_prob)
    for i, _ in enumerate(sampler.sample(x0 + 0.1 * scale * rng.normal(size=(walkers, ndim)), iterations=steps)):
        if ctx and i % 50 == 0:  # a task: show progress, stop when cancelled
            ctx.check()
            ctx.progress(0.1 + 0.9 * i / steps, "MCMC")
    chain = sampler.get_chain(discard=steps // 2, thin=5, flat=True)
    best = physical(x0)
    values = {k: np.array([physical(x)[k] for x in chain]) for k in best}
    out = {}
    for k, v in values.items():
        if k.startswith("omega"):  # an angle: keep the samples on the best value's side of 0/360
            v = best[k] + (v - best[k] + 180) % 360 - 180
        p16, p50, p84 = np.percentile(v, [16, 50, 84])
        out[k] = (float(p50), float(p50 - p16), float(p84 - p50))
    return {"params": out, "acceptance": float(np.mean(sampler.acceptance_fraction))}


def _use_posterior(fit, post):
    """Errors of the fit = the larger side of the 68 % intervals."""
    fit.mcmc = post
    fit.errors.update({k: max(v[1], v[2]) for k, v in post["params"].items()})
    return fit


def _eccentric_starts(times, errs, e, base, p3, t_mid, best=6):
    """Starting points for eccentric orbits. The chi2 surface has a valley for nearly every orientation: 25 starts
    at fixed (e, omega) all stopped in neighbouring valleys on a simulated e = 0.3 orbit (chi2 115 against 79 at
    the truth). For fixed (P3, e, omega, mean anomaly) the model is linear in (T0, P, A), so a grid over those three
    is cheap and finds the right valley; the least squares refine the best few."""
    from ..models.eb import true_anomaly

    w8 = 1 / errs
    y = (times - base) * w8
    m0 = np.radians(np.arange(0, 360, 10))[:, None]
    t3 = t_mid - m0 / (2 * np.pi) * p3
    found = []
    for ecc in np.arange(0.05, 0.91, 0.05):
        nu = true_anomaly(times[None, :], p3, t3, ecc)
        for w in np.radians(np.arange(0, 180, 15)):  # omega + 180 is the same orbit with -A
            tau = (1 - ecc**2) / (1 + ecc * np.cos(nu)) * np.sin(nu + w) + ecc * np.sin(w)
            a = np.stack(np.broadcast_arrays(w8, e * w8, tau * w8), axis=-1)  # (m0, n, 3)
            coef = np.linalg.solve(np.einsum("kni,knj->kij", a, a), np.einsum("kni,n->ki", a, y)[..., None])[..., 0]
            chi2 = np.sum((np.einsum("kni,ki->kn", a, coef) - y) ** 2, axis=1)
            for k in np.argsort(chi2)[:2]:
                found.append((chi2[k], ecc, w, float(m0[k, 0]), coef[k]))
    found.sort(key=lambda f: f[0])
    out = []
    for _, ecc, w, m, (c0, c1, amp) in found[:best]:
        r = np.sqrt(ecc)
        out.append((c0, c1, amp, np.log(p3), m, r * np.cos(w), r * np.sin(w)))
    return out


def fit_ltte(minima, t0_ref, period_ref, p3_range=None, mcmc_steps=0, ctx=None):
    """Linear ephemeris + light-travel-time orbit of a third body."""
    from scipy.optimize import least_squares

    times, errs, _, e = _prepare(minima, t0_ref, period_ref)
    if len(times) < 8:
        raise ValueError("need at least 8 minima for a third-body orbit")
    base = t0_ref + period_ref * e
    span = times.max() - times.min()
    lo, hi = p3_range or (max(20 * period_ref, span / 20), 2 * span)
    best = None
    for p3 in np.geomspace(lo, hi, 300):  # circular orbit: linear in (T0, P, A cos, A sin)
        ph = 2 * np.pi * times / p3
        a = np.column_stack([np.ones_like(e), e, np.sin(ph), np.cos(ph)]) / errs[:, None]
        coef, *_ = np.linalg.lstsq(a, (times - base) / errs, rcond=None)
        chi2 = np.sum((a @ coef - (times - base) / errs) ** 2)
        if best is None or chi2 < best[0]:
            best = (chi2, p3, coef)
    _, p3, coef = best
    amp = float(np.hypot(coef[2], coef[3]))
    phase0 = np.arctan2(coef[3], coef[2])  # A sin(2 pi t/P3 + phase0) = A sin(nu + omega) for e = 0
    t3_start = -phase0 / (2 * np.pi) * p3

    t_mid = float(np.median(times))

    def resid(x):  # periastron as the mean anomaly m0 at t_mid: well scaled, no wrapping by whole orbits
        dt0, dp, a3, lp3, m0, sec, ses = x
        ecc = sec**2 + ses**2
        if ecc >= 0.95:
            return np.full(len(times), 1e6)
        w = np.degrees(np.arctan2(ses, sec))
        t3 = t_mid - m0 / (2 * np.pi) * np.exp(lp3)
        return (times - (base + dt0 + dp * e + _tau(times, a3, np.exp(lp3), t3, ecc, w))) / errs

    m_circ = 2 * np.pi * (t_mid - t3_start) / p3
    starts = [(coef[0], coef[1], amp, np.log(p3), m_circ, 0.0, 0.0)]
    starts += _eccentric_starts(times, errs, e, base, p3, t_mid)
    sol = min((least_squares(resid, s, x_scale="jac") for s in starts), key=lambda r: np.sum(r.fun**2))
    err, chi2r = _covariance(sol, resid)
    turns = 2 * np.pi * np.floor(sol.x[4] / (2 * np.pi))  # T3 is the periastron after t_mid - P3

    def physical(x):
        dt0, dp, a3, lp3, m0, sec, ses = x
        omega = np.degrees(np.arctan2(ses, sec))
        if a3 < 0:  # the same orbit with the opposite sign of A is half a turn away in omega
            a3, omega = -a3, omega + 180
        p3 = np.exp(lp3)
        return {
            "t0": t0_ref + dt0,
            "period": period_ref + dp,
            "amplitude": a3,
            "p3": p3,
            "t3": t_mid - (m0 - turns) / (2 * np.pi) * p3,
            "e": sec**2 + ses**2,
            "omega": omega % 360,
            "f_m3": (a3 * AU_PER_LIGHT_DAY) ** 3 / (p3 / DAYS_PER_YEAR) ** 2,
        }

    best = {k: float(v) for k, v in physical(sol.x).items() if k != "f_m3"}
    p3v = best["p3"]
    fit = LTTEFit(
        **best,
        errors={
            "t0": err[0],
            "period": err[1],
            "amplitude": err[2],
            "p3": p3v * err[3],
            "t3": p3v * err[4] / (2 * np.pi),
        },
        chi2r=chi2r,
        epochs=e,
        o_minus_c=times - base,
        residuals=sol.fun * errs,
        ref_t0=t0_ref,
        ref_period=period_ref,
    )
    if mcmc_steps:
        _use_posterior(fit, _posterior(resid, sol.x, err, chi2r, physical, mcmc_steps, ctx=ctx))
    return fit


def _apsidal(e_int, kinds, t0, ps, ecc, omega0, d_omega):
    w = np.radians(omega0 + d_omega * e_int)
    pa = ps / (1 - d_omega / 360.0)  # anomalistic period
    sign = np.where(np.asarray(kinds) == "II", 1.0, -1.0)
    return t0 + ps * e_int + np.where(sign > 0, pa / 2, 0.0) + sign * pa / np.pi * ecc * np.cos(w)


def fit_apsidal(minima, t0_ref, period_ref, mcmc_steps=0, ctx=None):
    """Apsidal motion from primary and secondary minima (first order in e, see the module text)."""
    from scipy.optimize import least_squares

    times, errs, kinds, e = _prepare(minima, t0_ref, period_ref)
    if (kinds == "I").sum() < 3 or (kinds == "II").sum() < 3:
        raise ValueError("apsidal motion needs at least 3 primary and 3 secondary minima")
    e_int = np.where(kinds == "II", e - 0.5, e)
    sign = np.where(kinds == "II", 1.0, -1.0)
    span = e_int.max() - e_int.min()
    best = None
    for dw in np.geomspace(360 / (20 * span), 360 / (span / 5), 400):  # linear in T0, Ps, e cos w0, e sin w0
        ph = np.radians(dw * e_int)
        pa_pi = period_ref / np.pi
        cols = [np.ones_like(e_int), e_int, sign * pa_pi * np.cos(ph), -sign * pa_pi * np.sin(ph)]
        a = np.column_stack(cols) / errs[:, None]
        y = (times - np.where(kinds == "II", period_ref / 2, 0.0)) / errs
        coef, *_ = np.linalg.lstsq(a, y, rcond=None)
        chi2 = np.sum((a @ coef - y) ** 2)
        if best is None or chi2 < best[0]:
            best = (chi2, dw, coef)
    _, dw, (t0, ps, ec, es) = best

    def resid(x):
        return (
            times - _apsidal(e_int, kinds, x[0], x[1], np.hypot(x[2], x[3]), np.degrees(np.arctan2(x[3], x[2])), x[4])
        ) / errs

    sol = least_squares(resid, (t0, ps, ec, es, dw), x_scale="jac")
    err, chi2r = _covariance(sol, resid)

    def physical(x):
        t0, ps, ec, es, dw = x
        return {
            "t0": t0,
            "period": ps,
            "e": np.hypot(ec, es),
            "omega0": np.degrees(np.arctan2(es, ec)) % 360,
            "d_omega": dw,
            "u_years": 360.0 / dw * ps / DAYS_PER_YEAR if dw else np.inf,
        }

    best = {k: float(v) for k, v in physical(sol.x).items() if k != "u_years"}
    fit = ApsidalFit(
        **best,
        errors={"t0": err[0], "period": err[1], "d_omega": err[4]},
        chi2r=chi2r,
        epochs=e,
        o_minus_c=times - (t0_ref + period_ref * e),
        residuals=sol.fun * errs,
        ref_t0=t0_ref,
        ref_period=period_ref,
    )
    if mcmc_steps:
        _use_posterior(fit, _posterior(resid, sol.x, err, chi2r, physical, mcmc_steps, ctx=ctx))
    return fit
