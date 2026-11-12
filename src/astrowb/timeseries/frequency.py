"""Frequency analysis as Period04 does it, and beyond (plans/period.md PER-6, the engine): a frequency list whose
terms are fitted all at once, combinations and harmonics identified, three kinds of errors, amplitude and phase
per subset.

Model: y = c + Σ_k A_k sin(2π (f_k (t − t_ref) + φ_k)), phases in cycles of a sine at the stated t_ref. A term is
independent (f free or fixed) or related: f = Σ n_j f_j over independent terms (e.g. {"F1": 2} or
{"F1": 1, "F2": 1}), then computed from them, not fitted; its amplitude and phase stay free.
"""

import itertools

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def term(name, freq, amp=0.0, phase=0.0, fit=("f", "a", "p"), relation=None, note=""):
    return {"name": name, "freq": float(freq), "amp": float(amp), "phase": float(phase), "fit": tuple(fit),
            "relation": dict(relation) if relation else None, "note": note}  # fmt: skip


def _layout(terms):
    """Indices of the fitted values in the parameter vector: [c, (f of free independent terms), A, φ]."""
    names = [x["name"] for x in terms]
    f_free = [i for i, x in enumerate(terms) if not x["relation"] and "f" in x["fit"]]
    a_free = [i for i, x in enumerate(terms) if "a" in x["fit"]]
    p_free = [i for i, x in enumerate(terms) if "p" in x["fit"]]
    # the matrix n (terms × terms): f = n @ f_independent (identity rows for independent terms)
    n = np.zeros((len(terms), len(terms)))
    for i, x in enumerate(terms):
        if x["relation"]:
            for parent, coef in x["relation"].items():
                j = names.index(parent)
                if terms[j]["relation"]:
                    child = x["name"]
                    raise ValueError(f"{child} is related to {parent}, which is itself related")
                n[i, j] = coef
        else:
            n[i, i] = 1.0
    return f_free, a_free, p_free, n


def _unpack(p, terms, layout):
    f_free, a_free, p_free, n = layout
    base = np.array([x["freq"] for x in terms])
    amp = np.array([x["amp"] for x in terms])
    ph = np.array([x["phase"] for x in terms])
    k = 1
    base[f_free] = p[k : k + len(f_free)]
    k += len(f_free)
    amp[a_free] = p[k : k + len(a_free)]
    k += len(a_free)
    ph[p_free] = p[k : k + len(p_free)]
    return p[0], n @ base, amp, ph


def model(t, zero_point, freq, amp, phase, t_ref=0.0):
    arg = 2 * np.pi * (np.outer(freq, np.asarray(t, float) - t_ref) + np.asarray(phase)[:, None])
    return zero_point + np.asarray(amp) @ np.sin(arg)


def _linear_start(t, y, w, freq):
    """Amplitudes and phases for fixed frequencies by linear least squares."""
    cols = [np.ones_like(t)]
    for f in freq:
        cols += [np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)]
    coef = np.linalg.lstsq(np.column_stack(cols) * w[:, None], y * w, rcond=None)[0]
    s, c = coef[1::2], coef[2::2]
    return coef[0], np.hypot(s, c), (np.arctan2(c, s) / (2 * np.pi)) % 1.0


def _levenberg_marquardt(resid, jac_t, p, max_iter=100, tol=1e-12):
    """Levenberg–Marquardt on the normal equations (JᵀJ through BLAS: a 10⁵ × 150 Jacobian costs milliseconds
    where a QR without BLAS took seconds). Returns (p, residuals, JᵀJ at the solution)."""
    r = resid(p)
    cost, lam = r @ r, 1e-3
    for _ in range(max_iter):
        j = jac_t(p)
        a, g = j @ j.T, j @ r
        d = np.diag(a).copy()
        d[d == 0] = 1.0
        while True:
            try:
                step = -cho_solve(cho_factor(a + lam * np.diag(d)), g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            r_new = resid(p + step)
            c_new = r_new @ r_new
            if c_new <= cost or lam > 1e12:
                break
            lam *= 10
        if c_new > cost:
            break
        p, r, done = p + step, r_new, cost - c_new <= tol * cost
        cost, lam = c_new, max(lam / 10, 1e-12)
        if done:
            break
    j = jac_t(p)
    return p, r, j @ j.T


def improve_all(t, y, terms, err=None, t_ref=None, linear_start=False):
    """Non-linear least squares of every free frequency, amplitude and phase at once (Levenberg–Marquardt with the
    analytic Jacobian; weights 1/err²). Returns (terms with values and covariance errors, info) where info holds
    zero_point, rms, t_ref, chi2r and the covariance matrix with its parameter labels."""
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    t_ref = float(np.round(np.mean(t), 1)) if t_ref is None else float(t_ref)
    x = t - t_ref
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)
    terms = [dict(v) for v in terms]
    layout = _layout(terms)
    f_free, a_free, p_free, n = layout
    if linear_start:
        f0 = n @ np.array([v["freq"] for v in terms])
        c0, a0, ph0 = _linear_start(x, y, w, f0)
        for v, a, ph in zip(terms, a0, ph0, strict=True):
            v["amp"], v["phase"] = a, ph
    else:
        c0 = float(np.average(y - model(x, 0.0, n @ [v["freq"] for v in terms], [v["amp"] for v in terms],
                                        [v["phase"] for v in terms]), weights=w**2))  # fmt: skip
    p0 = np.concatenate([[c0], [terms[i]["freq"] for i in f_free], [terms[i]["amp"] for i in a_free],
                         [terms[i]["phase"] for i in p_free]])  # fmt: skip

    def resid(p):
        c, f, a, ph = _unpack(p, terms, layout)
        return (model(x, c, f, a, ph) - y) * w

    def jac_t(p):  # the transposed Jacobian (parameters × points), its rows written in place
        _c, f, a, ph = _unpack(p, terms, layout)
        arg = 2 * np.pi * (np.outer(f, x) + ph[:, None])
        s, co = np.sin(arg), np.cos(arg)
        co *= (2 * np.pi * w)[None, :]
        out = np.empty((len(p), len(x)))
        out[0] = w
        k = 1
        if f_free:
            out[k : k + len(f_free)] = n[:, f_free].T @ (a[:, None] * co * x)
            k += len(f_free)
        out[k : k + len(a_free)] = s[a_free] * w
        k += len(a_free)
        out[k:] = a[p_free, None] * co[p_free]
        return out

    p, r, normal = _levenberg_marquardt(resid, jac_t, p0)
    c, f, a, ph = _unpack(p, terms, layout)
    flip = a < 0  # a negative amplitude is the same sine half a cycle on
    a, ph = np.abs(a), (ph + 0.5 * flip) % 1.0
    dof = max(len(y) - len(p), 1)
    chi2r = float(r @ r / dof)
    try:
        cov = np.linalg.inv(normal) * (chi2r if err is None else max(chi2r, 1.0))
    except np.linalg.LinAlgError:
        cov = np.full((len(p), len(p)), np.nan)
    e = np.sqrt(np.clip(np.diag(cov), 0, None))
    e_base = np.zeros(len(terms))
    e_base[f_free] = e[1 : 1 + len(f_free)]
    sub = cov[1 : 1 + len(f_free), 1 : 1 + len(f_free)]
    nf = n[:, f_free]
    e_freq = np.sqrt(np.clip(np.einsum("ij,jk,ik->i", nf, sub, nf), 0, None))  # related terms: propagated
    for i, v in enumerate(terms):
        v.update(freq=float(f[i]), amp=float(a[i]), phase=float(ph[i]), freq_err=float(e_freq[i]))
        v["amp_err"] = float(e[1 + len(f_free) + a_free.index(i)]) if i in a_free else 0.0
        v["phase_err"] = float(e[1 + len(f_free) + len(a_free) + p_free.index(i)]) if i in p_free else 0.0
    rms = float(np.sqrt(np.mean((model(x, c, f, a, ph) - y) ** 2)))
    labels = ["c"] + [f"f:{terms[i]['name']}" for i in f_free] + [f"A:{terms[i]['name']}" for i in a_free]
    labels += [f"phi:{terms[i]['name']}" for i in p_free]
    return terms, {"zero_point": float(c), "rms": rms, "t_ref": t_ref, "chi2r": chi2r, "covariance": cov,
                   "labels": labels}  # fmt: skip


def evaluate(terms, info, t):
    return model(np.asarray(t, float) - info["t_ref"], info["zero_point"], [v["freq"] for v in terms],
                 [v["amp"] for v in terms], [v["phase"] for v in terms])  # fmt: skip


def correlation_factor(residuals):
    """√D of Schwarzenberg-Czerny 1991 (MNRAS 253, 198): D from the mean length of runs of residuals with one
    sign (white noise: runs of 2 on average, D = 1)."""
    r = np.asarray(residuals, float)
    signs = np.sign(r[r != 0])
    runs = 1 + int(np.count_nonzero(np.diff(signs)))
    return float(np.sqrt(max(len(signs) / runs / 2.0, 1.0)))


def analytic_errors(t, terms, rms, residuals=None):
    """Montgomery & O'Donoghue 1999: σ_f = √6 σ / (√N π T A), σ_A = √(2/N) σ, σ_φ = σ_A / (2π A) cycles; times
    the correlated-noise factor √D when the residuals are given."""
    t = np.asarray(t, float)
    n, span = len(t), np.ptp(t)
    k = correlation_factor(residuals) if residuals is not None else 1.0
    out = []
    for v in terms:
        sa = np.sqrt(2 / n) * rms * k
        out.append({"freq_err": np.sqrt(6 / n) * rms * k / (np.pi * span * v["amp"]), "amp_err": sa,
                    "phase_err": sa / (2 * np.pi * v["amp"])})  # fmt: skip
    return out


def monte_carlo_errors(t, y, terms, info, n=100, seed=1, err=None, workers=4):
    """Standard deviations over n simulated data sets: the fitted model plus the shuffled residuals, each fitted
    again (in threads)."""
    from concurrent.futures import ThreadPoolExecutor

    t = np.asarray(t, float)
    fitted = evaluate(terms, info, t)
    resid = np.asarray(y, float) - fitted
    rng = np.random.default_rng(seed)
    sets = [fitted + rng.permutation(resid) for _ in range(n)]

    def one(ys):
        got, _ = improve_all(t, ys, terms, err, info["t_ref"])
        return [(v["freq"], v["amp"], v["phase"]) for v in got]

    with ThreadPoolExecutor(workers) as pool:
        values = np.array(list(pool.map(one, sets)))  # (n, terms, 3)
    ph = values[:, :, 2]
    ph = ph - np.round(ph - np.array([v["phase"] for v in terms]))  # unwrap around the fitted phase
    return [{"freq_err": float(np.std(values[:, i, 0], ddof=1)), "amp_err": float(np.std(values[:, i, 1], ddof=1)),
             "phase_err": float(np.std(ph[:, i], ddof=1))} for i in range(len(terms))]  # fmt: skip


def identify(terms, span, max_terms=3, max_coef=3, resolution=1.5, n_sigma=4.0):
    """Proposed relations: for every term, the simplest combination Σ n_j f_j of stronger independent terms
    (at most max_terms parents, |n| ≤ max_coef) within the tolerance — the resolution resolution / span, or
    n_sigma times the frequency errors when they are known and smaller. Also the pairs closer than the resolution.
    Returns ({name: (relation, distance)}, [(name, name)] unresolved)."""
    order = sorted(range(len(terms)), key=lambda i: -terms[i]["amp"])
    res = resolution / span
    proposals, parents = {}, []
    for i in order:
        v = terms[i]
        best = None
        for k in range(1, max_terms + 1):
            for chosen in itertools.combinations(parents, k):
                for coefs in itertools.product([c for c in range(-max_coef, max_coef + 1) if c], repeat=k):
                    if k == 1 and coefs[0] == 1:
                        continue  # the parent itself
                    f = sum(c * terms[j]["freq"] for c, j in zip(coefs, chosen, strict=True))
                    if f <= 0:
                        continue
                    e2 = v.get("freq_err", 0.0) ** 2 + sum(
                        (c * terms[j].get("freq_err", 0.0)) ** 2 for c, j in zip(coefs, chosen, strict=True)
                    )
                    tol = min(res, n_sigma * np.sqrt(e2)) if e2 > 0 else res
                    d = abs(f - v["freq"])
                    if d <= tol:
                        key = (k, sum(abs(c) for c in coefs), d)
                        if best is None or key < best[0]:
                            best = (key, {terms[j]["name"]: c for c, j in zip(coefs, chosen, strict=True)}, d)
            if best is not None:
                break
        if best is None:
            parents.append(i)
        else:
            proposals[v["name"]] = (best[1], best[2])
    freqs = [(v["freq"], v["name"]) for v in terms]
    close = [(a[1], b[1]) for a, b in itertools.combinations(freqs, 2) if abs(a[0] - b[0]) < res]
    return proposals, close


def variations(t, y, terms, info, groups, err=None):
    """Amplitude and phase of every term per subset (frequencies fixed; a zero point per subset): a list of
    {"group", "time", "amp", "amp_err", "phase", "phase_err"} per term name."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    groups = np.asarray(groups)
    w_all = np.ones_like(y) if err is None else 1 / np.asarray(err, float)
    out = {v["name"]: [] for v in terms}
    freq = np.array([v["freq"] for v in terms])
    for g in np.unique(groups):
        sel = groups == g
        if sel.sum() < 2 * len(terms) + 2:
            continue
        x, w = t[sel] - info["t_ref"], w_all[sel]
        cols = [np.ones_like(x)] + [fn(2 * np.pi * f * x) for f in freq for fn in (np.sin, np.cos)]
        a = np.column_stack(cols) * w[:, None]
        coef, *_ = np.linalg.lstsq(a, y[sel] * w, rcond=None)
        r = y[sel] * w - a @ coef
        cov = np.linalg.pinv(a.T @ a) * (r @ r / max(sel.sum() - len(coef), 1))
        for k, v in enumerate(terms):
            s, c = coef[1 + 2 * k], coef[2 + 2 * k]
            amp = np.hypot(s, c)
            vs, vc, vsc = cov[1 + 2 * k, 1 + 2 * k], cov[2 + 2 * k, 2 + 2 * k], cov[1 + 2 * k, 2 + 2 * k]
            amp_err = np.sqrt(max((s * s * vs + c * c * vc + 2 * s * c * vsc) / amp**2, 0.0))
            ph_err = np.sqrt(max((c * c * vs + s * s * vc - 2 * s * c * vsc) / amp**4, 0.0)) / (2 * np.pi)
            phase = float(np.arctan2(c, s) / (2 * np.pi) % 1.0)
            out[v["name"]].append({"group": g.item() if hasattr(g, "item") else g, "time": float(np.mean(t[sel])),
                                   "amp": float(amp), "amp_err": float(amp_err), "phase": phase,
                                   "phase_err": float(ph_err)})  # fmt: skip
    return out
