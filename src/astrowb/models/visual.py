"""Orbit of a visual (resolved) binary from position angles and separations of the companion.

Model (Thiele-Innes form, e.g. Heintz 1978, "Double Stars"; conventions of the USNO orbit catalogues: Hartkopf,
Mason & Worley 2001, AJ 122, 3472, continued as ORB6): with the eccentric anomaly E from Kepler's equation
M = E - e sin E, M = 2 pi (t - T) / P,
    X = cos E - e,   Y = sqrt(1 - e^2) sin E
    x (north) = rho cos(theta) = A X + F Y,   y (east) = rho sin(theta) = B X + G Y
and the Thiele-Innes constants follow from the Campbell elements a, i, Omega, omega:
    A = a ( cos w cos W - sin w sin W cos i)     B = a ( cos w sin W + sin w cos W cos i)
    F = a (-sin w cos W - cos w sin W cos i)     G = a (-sin w sin W + cos w cos W cos i)
For fixed P, T, e the four constants are linear: a weighted least-squares solve. P, T, e are first searched on a
grid (the period range given, every phase of periastron, e from 0 to 0.95), then all seven elements are refined
together by Levenberg-Marquardt; their errors come from the covariance of that fit, scaled by the reduced chi^2.
Omega is the node in 0..180 deg (the ambiguity of visual orbits: without radial velocities Omega and omega can
both be turned by 180 deg), omega is measured from that node in the direction of motion.
Total mass (Kepler's third law): M1 + M2 = a^3 / (parallax^3 P^2) solar masses (a, parallax in arcsec, P in years).
"""

import numpy as np

YEAR = 365.25  # days in a Julian year; epochs are fractional (Besselian-style) years


def kepler(m, e):
    """Eccentric anomaly for mean anomaly m (radians), Newton iterations (|dE| < 1e-12)."""
    m = np.mod(np.asarray(m, float), 2 * np.pi)
    ecc = np.where(e > 0.8, np.pi, m)
    for _ in range(50):
        d = (ecc - e * np.sin(ecc) - m) / (1 - e * np.cos(ecc))
        ecc = ecc - d
        if np.max(np.abs(d)) < 1e-12:
            break
    return ecc


def thiele_innes(a, i, node, omega):
    ci, sw, cw, sn, cn = np.cos(i), np.sin(omega), np.cos(omega), np.sin(node), np.cos(node)
    return (
        a * (cw * cn - sw * sn * ci),
        a * (cw * sn + sw * cn * ci),
        a * (-sw * cn - cw * sn * ci),
        a * (-sw * sn + cw * cn * ci),
    )


def campbell(A, B, F, G):
    """Campbell elements (a, i, Omega, omega in radians) from the Thiele-Innes constants; Omega in [0, pi)."""
    u = (A**2 + B**2 + F**2 + G**2) / 2
    v = A * G - B * F
    a = np.sqrt(u + np.sqrt((u + v) * (u - v)))
    w_plus_n = np.arctan2(B - F, A + G)
    w_minus_n = np.arctan2(-B - F, A - G)
    omega, node = (w_plus_n + w_minus_n) / 2, (w_plus_n - w_minus_n) / 2
    if node < 0:
        node, omega = node + np.pi, omega + np.pi
    if node >= np.pi:
        node, omega = node - np.pi, omega - np.pi
    i = np.arccos(np.clip(v / a**2, -1, 1))
    # the half-angle formulas leave omega + Omega and omega - Omega ambiguous by pi: keep the pair that gives back A
    if not np.allclose(thiele_innes(a, i, node, omega), (A, B, F, G), atol=1e-9 * a):
        omega += np.pi
    return a, i, node, np.mod(omega, 2 * np.pi)


def xy_of(t, P, T, e, A, B, F, G):
    ecc = kepler(2 * np.pi * (np.asarray(t, float) - T) / P, e)
    X, Y = np.cos(ecc) - e, np.sqrt(1 - e**2) * np.sin(ecc)
    return A * X + F * Y, B * X + G * Y


def _linear(t, x, y, w, P, T, e):
    """Best Thiele-Innes constants for fixed P, T, e and the weighted residual sum."""
    ecc = kepler(2 * np.pi * (t - T) / P, e)
    X, Y = np.cos(ecc) - e, np.sqrt(1 - e**2) * np.sin(ecc)
    m = np.column_stack([X, Y]) * w[:, None]
    (A, F), *_ = np.linalg.lstsq(m, x * w, rcond=None)
    (B, G), *_ = np.linalg.lstsq(m, y * w, rcond=None)
    chi2 = np.sum(((A * X + F * Y - x) * w) ** 2) + np.sum(((B * X + G * Y - y) * w) ** 2)
    return (A, B, F, G), chi2


def to_xy(theta_deg, rho):
    t = np.radians(np.asarray(theta_deg, float))
    rho = np.asarray(rho, float)
    return rho * np.cos(t), rho * np.sin(t)


def to_polar(x, y):
    return np.mod(np.degrees(np.arctan2(y, x)), 360.0), np.hypot(x, y)


def fit(epoch, theta_deg, rho, rho_err=None, theta_err_deg=None, p_range=None, parallax=None, n_grid=60):
    """Orbit from epochs (years), position angles (degrees, north through east) and separations (arcsec).
    p_range: (shortest, longest) period in years to search (default: 0.5 to 10 times the time span).
    Returns the elements (P, T, e, a, i, Omega, omega with errors), residuals and, with a parallax (arcsec),
    the total mass."""
    from scipy.optimize import least_squares

    t = np.asarray(epoch, float)
    x, y = to_xy(theta_deg, rho)
    if len(t) < 7:
        raise ValueError("a visual orbit needs at least 7 measures (seven elements)")
    sig_r = np.full(len(t), 0.01) if rho_err is None else np.asarray(rho_err, float)
    sig_t = np.radians(np.full(len(t), 1.0) if theta_err_deg is None else np.asarray(theta_err_deg, float))
    w = 1 / np.sqrt(sig_r**2 + (np.asarray(rho, float) * sig_t) ** 2)  # one positional error per measure
    span = np.ptp(t)
    lo, hi = p_range or (0.5 * span, 10 * span)
    best = (np.inf, None)
    for P in np.geomspace(lo, hi, n_grid):
        for e in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95):
            for T in t.min() + P * np.linspace(0, 1, 24, endpoint=False):
                _, chi2 = _linear(t, x, y, w, P, T, e)
                if chi2 < best[0]:
                    best = (chi2, (P, T, e))
    P0, T0, e0 = best[1]
    (A0, B0, F0, G0), _ = _linear(t, x, y, w, P0, T0, e0)

    def resid(p):
        P, T, e, A, B, F, G = p
        mx, my = xy_of(t, P, T, e, A, B, F, G)
        return np.r_[(mx - x) * w, (my - y) * w]

    start = [P0, T0, e0, A0, B0, F0, G0]
    bounds = (
        [lo * 0.5, -np.inf, 0.0, -np.inf, -np.inf, -np.inf, -np.inf],
        [hi * 2, np.inf, 0.99, np.inf, np.inf, np.inf, np.inf],
    )
    r = least_squares(resid, start, bounds=bounds, x_scale="jac")
    P, T, e, A, B, F, G = r.x
    a, i, node, omega = campbell(A, B, F, G)
    dof = max(1, 2 * len(t) - 7)
    chi2_red = float(np.sum(r.fun**2) / dof)
    errors = _campbell_errors(r, chi2_red)
    mx, my = xy_of(t, P, T, e, A, B, F, G)
    th_c, rho_c = to_polar(mx, my)
    out = {
        "P": float(P),
        "T": float(T),
        "e": float(e),
        "a": float(a),
        "i": float(np.degrees(i)),
        "node": float(np.degrees(node)),
        "omega": float(np.degrees(omega)),
        "errors": errors,
        "thiele_innes": [float(A), float(B), float(F), float(G)],
        "chi2_red": chi2_red,
        "n": int(len(t)),
        "rho_resid": (np.asarray(rho, float) - rho_c).tolist(),
        "theta_resid": (((np.asarray(theta_deg, float) - th_c) + 180) % 360 - 180).tolist(),
        "rms_rho": float(np.sqrt(np.mean((np.asarray(rho, float) - rho_c) ** 2))),
    }
    if parallax:
        m = a**3 / (float(parallax) ** 3 * P**2)
        out["mass"] = float(m)
        out["mass_err"] = float(m * np.hypot(3 * errors["a"] / a, 2 * errors["P"] / P))
    return out


def _campbell_errors(r, chi2_red):
    """1-sigma errors of P, T, e, a, i, Omega, omega: the fit covariance carried through the Thiele-Innes ->
    Campbell conversion by its numerical Jacobian."""
    j = r.jac
    try:
        cov = np.linalg.inv(j.T @ j) * max(chi2_red, 1e-12)
    except np.linalg.LinAlgError:
        return {k: float("nan") for k in ("P", "T", "e", "a", "i", "node", "omega")}
    p = r.x

    def elements(q):
        a, i, n, w = campbell(*q[3:])
        return np.array([q[0], q[1], q[2], a, np.degrees(i), np.degrees(n), np.degrees(w)])

    base = elements(p)
    jac = np.zeros((7, 7))
    for k in range(7):
        h = 1e-6 * max(abs(p[k]), 1e-3)
        q = p.copy()
        q[k] += h
        d = elements(q) - base
        d[5:] = (d[5:] + 180) % 360 - 180  # angles across the wrap
        jac[:, k] = d / h
    err = np.sqrt(np.clip(np.diag(jac @ cov @ jac.T), 0, None))
    return dict(zip(("P", "T", "e", "a", "i", "node", "omega"), map(float, err), strict=True))


def ephemeris(orbit, epochs):
    """Predicted (theta degrees, rho arcsec) at the epochs (years)."""
    A, B, F, G = orbit["thiele_innes"]
    x, y = xy_of(epochs, orbit["P"], orbit["T"], orbit["e"], A, B, F, G)
    th, rho = to_polar(x, y)
    return th.tolist(), rho.tolist()


def parse_measures(text):
    """Lines "epoch theta rho [rho_err] [theta_err]" (WDS order: position angle before separation); blank lines
    and lines starting with # are skipped. Returns arrays (epoch, theta, rho, rho_err or None, theta_err or None)."""
    rows = []
    for line in text.splitlines():
        line = line.split("#")[0].replace(",", " ").strip()
        if line:
            rows.append([float(v) for v in line.split()])
    if not rows:
        raise ValueError("no measures")
    width = min(len(r) for r in rows)
    if width < 3:
        raise ValueError("each line needs epoch, position angle and separation")
    a = np.array([r[:width] for r in rows])
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3] if width > 3 else None, a[:, 4] if width > 4 else None
