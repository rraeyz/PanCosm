"""Differential-evolution Markov chains with snooker moves (EXO-5 item 4a), written from ter Braak 2006
(Stat. Comput. 16, 239) and ter Braak & Vrugt 2008 (Stat. Comput. 18, 435), with EXOFAST's stopping rule.

The chains are split in two halves; each half is updated from differences of the other (which stays fixed
meanwhile), so a half's proposals are independent and evaluated together (vectorised or in a thread pool) and the
chain is still a valid Metropolis sampler. Moves: x + γ (z₁ − z₂) + ε with γ = 2.38 / √(2d) (1 every tenth
generation, to jump between modes), or with probability `snooker` the snooker move along x − z with its Jacobian
(|x′ − z| / |x − z|)^(d−1). Parallel tempering (optional): the same at temperatures T with target prior +
likelihood / T, and swaps between neighbours accepted with exp((β_i − β_j)(ℓ_j − ℓ_i)); only the cold chains
are kept.

Stopping: every check_every generations the burn-in is found (diagnostics.burn_in) and the run stops when every
parameter's rank-normalised split-R̂ is below rhat_limit and its bulk and tail effective sizes above ess_min; else
at max_steps or max_seconds, marked not converged. A checkpoint file makes a run resumable: resuming gives the same
chain as an uninterrupted run with the same seed.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import diagnostics
from .results import Posterior


class _State:
    """Positions, log-probabilities and log-likelihoods of every chain at every temperature (the cold chains
    first); the stored history holds the cold chains."""

    def __init__(self, pos, lp, ll, betas, rng):
        self.pos, self.lp, self.ll, self.betas, self.rng = pos, lp, ll, np.asarray(betas, float), rng
        self.cold = len(pos) // len(self.betas)
        self.chain = np.empty((1024, self.cold, pos.shape[1]))
        self.lps = np.empty((1024, self.cold))
        self.step = 0

    def store(self):
        if self.step == len(self.chain):
            self.chain = np.concatenate([self.chain, np.empty_like(self.chain)])
            self.lps = np.concatenate([self.lps, np.empty_like(self.lps)])
        self.chain[self.step], self.lps[self.step] = self.pos[: self.cold], self.lp[: self.cold]
        self.step += 1

    def save(self, path):
        tmp = path + ".part.npz"
        np.savez_compressed(tmp, pos=self.pos, lp=self.lp, ll=self.ll, betas=self.betas,
                            chain=self.chain[: self.step], lps=self.lps[: self.step],
                            rng=json.dumps(self.rng.bit_generator.state))  # fmt: skip
        os.replace(tmp, path)

    @classmethod
    def load(cls, path):
        with np.load(path) as f:
            rng = np.random.default_rng()
            rng.bit_generator.state = json.loads(str(f["rng"]))
            state = cls(f["pos"].copy(), f["lp"].copy(), f["ll"].copy(), f["betas"], rng)
            n = len(f["chain"])
            state.chain = np.concatenate([f["chain"], np.empty((max(n, 1024), *state.chain.shape[1:]))])
            state.lps = np.concatenate([f["lps"], np.empty((max(n, 1024), state.cold))])
            state.step = n
        return state


def _evaluate(problem, thetas, pool, tempered=False):
    """(log-probability, log-likelihood) of the points; the likelihood only when tempering needs it."""
    if getattr(problem, "vectorized", False):
        lp = np.asarray(problem(thetas), float)
    elif pool is None:
        lp = np.array([problem(t) for t in thetas])
    else:
        lp = np.array(list(pool.map(problem, thetas)))
    if not tempered:
        return lp, np.zeros_like(lp)
    with np.errstate(invalid="ignore"):
        return lp, np.where(np.isfinite(lp), lp - np.asarray(problem.log_prior(thetas), float), -np.inf)


def _start(problem, n, rng, spread, pool, tempered):
    """Chains scattered around the start by spread × scale; points outside the prior drawn again."""
    pos = problem.start + spread * problem.scale * rng.normal(size=(n, problem.dim))
    lp, ll = _evaluate(problem, pos, pool, tempered)
    for _ in range(100):
        bad = ~np.isfinite(lp)
        if not bad.any():
            return pos, lp, ll
        pos[bad] = problem.start + spread * problem.scale * rng.normal(size=(bad.sum(), problem.dim))
        lp[bad], ll[bad] = _evaluate(problem, pos[bad], pool, tempered)
    raise ValueError("the start is outside the prior or the model fails there")


def _proposals(x, others, rng, gamma, snooker):
    """DE and snooker proposals for the chains x from the population others; with log Jacobian terms."""
    k, d = x.shape
    pick = np.argsort(rng.random((k, len(others))), axis=1)[:, :3]
    z0, z1, z2 = others[pick[:, 0]], others[pick[:, 1]], others[pick[:, 2]]
    noise = 1e-4 * np.std(others, axis=0) * rng.normal(size=(k, d))
    prop = x + gamma * (z0 - z1) + noise
    extra = np.zeros(k)
    snook = rng.random(k) < snooker
    if snook.any():
        axis = x[snook] - z2[snook]
        length = np.linalg.norm(axis, axis=1)
        ok = length > 0
        u = axis / np.where(ok, length, 1.0)[:, None]
        step = np.sum((z0[snook] - z1[snook]) * u, axis=1)[:, None] * u
        new = x[snook] + rng.uniform(1.2, 2.2, (len(u), 1)) * step
        with np.errstate(divide="ignore"):
            jac = (d - 1) * (np.log(np.linalg.norm(new - z2[snook], axis=1)) - np.log(length))
        prop[snook] = np.where(ok[:, None], new, x[snook])
        extra[snook] = np.where(ok, jac, -np.inf)
    return prop, extra


def _generation(problem, state, halves, pool, snooker):
    """One DE step of both halves at every temperature (target: prior + β · likelihood), then swaps between
    neighbouring temperatures."""
    d, c = problem.dim, state.cold
    tempered = len(state.betas) > 1
    gamma = 1.0 if state.step % 10 == 9 else 2.38 / np.sqrt(2 * d)
    for k, beta in enumerate(state.betas):
        for me, other in (halves, halves[::-1]):
            me, other = me + k * c, other + k * c
            prop, extra = _proposals(state.pos[me], state.pos[other], state.rng, gamma, snooker)
            lp, ll = _evaluate(problem, prop, pool, tempered)
            with np.errstate(invalid="ignore"):
                delta = lp - state.lp[me] - (1 - beta) * (ll - state.ll[me]) if tempered else lp - state.lp[me]
            accept = np.log(state.rng.random(len(me))) < np.where(np.isfinite(lp), delta, -np.inf) + extra
            hit = me[accept]
            state.pos[hit], state.lp[hit], state.ll[hit] = prop[accept], lp[accept], ll[accept]
    for k in range(len(state.betas) - 1, 0, -1):  # swaps, hot to cold
        hot = np.arange(c) + k * c
        cold = state.rng.permutation(c) + (k - 1) * c
        ratio = (state.betas[k - 1] - state.betas[k]) * (state.ll[hot] - state.ll[cold])
        swap = np.log(state.rng.random(c)) < ratio
        a, b = hot[swap], cold[swap]
        for arr in (state.pos, state.lp, state.ll):
            arr[a], arr[b] = arr[b].copy(), arr[a].copy()
    state.store()


def _diagnose(problem, state):
    # a chain that never reaches the final median would discard everything: keep at least the second half
    burn = min(diagnostics.burn_in(state.lps[: state.step]), state.step // 2)
    post = state.chain[burn : state.step]
    if len(post) < 50:
        return burn, None
    # thinned to ≤ 1000 draws per chain: the effective sizes can only come out lower (the rule stays safe), and the
    # cost stays bounded as the chains grow
    post = post[:: -(-len(post) // 1000)]
    rows = [(diagnostics.rhat(post[:, :, j].T), diagnostics.ess_bulk(post[:, :, j].T),
             diagnostics.ess_tail(post[:, :, j].T)) for j in range(problem.dim)]  # fmt: skip
    return burn, dict(zip(problem.names, rows, strict=True))


def _next_check(step, every):
    """The step of the next convergence check: the checks fall at multiples of every, each at least 1.25 times
    the previous one (replayed from the start, so a resumed run checks where an uninterrupted one would)."""
    nxt = 0
    for s in range(every, step + 1, every):
        if s >= nxt:
            nxt = max(nxt, int(s * 1.25))
    return nxt


def run(problem, n_chains=None, seed=1, max_steps=20000, check_every=200, rhat_limit=1.01, ess_min=1000,
        max_seconds=None, snooker=0.1, spread=1.0, workers=1, temperatures=1, t_max=100.0, checkpoint=None,
        ctx=None, progress=(0.0, 1.0)):  # fmt: skip
    """Sample the problem; returns a results.Posterior. n_chains: at least 2 d and 16 (even). checkpoint: a file
    written every check_every generations and at the end; if it exists the run continues from it. temperatures > 1:
    parallel tempering, n_chains at each of that many temperatures spaced geometrically up to t_max (for posteriors
    with separated modes; needs a Problem, whose prior is split from the likelihood)."""
    n_chains = max(n_chains or 0, 2 * problem.dim, 16)
    n_chains += n_chains % 2
    halves = (np.arange(0, n_chains, 2), np.arange(1, n_chains, 2))
    pool = ThreadPoolExecutor(workers) if workers > 1 and not getattr(problem, "vectorized", False) else None
    try:
        if checkpoint and os.path.exists(checkpoint):
            state = _State.load(checkpoint)
        else:
            rng = np.random.default_rng(seed)
            betas = np.geomspace(1.0, 1.0 / t_max, temperatures) if temperatures > 1 else [1.0]
            start = _start(problem, n_chains * len(betas), rng, spread, pool, temperatures > 1)
            state = _State(*start, betas, rng)
        began, burn, diag, converged = time.monotonic(), 0, None, False
        next_check = _next_check(state.step, check_every)
        while state.step < max_steps:
            _generation(problem, state, halves, pool, snooker)
            if state.step % check_every == 0:
                if checkpoint:
                    state.save(checkpoint)
                if ctx is not None:
                    ctx.progress(progress[0] + (progress[1] - progress[0]) * state.step / max_steps, "MCMC")
                    ctx.check()
                if max_seconds and time.monotonic() - began > max_seconds:
                    break
                if state.step < next_check:
                    continue
                next_check = max(next_check, int(state.step * 1.25))  # the diagnostics cost grows with the chain
                burn, diag = _diagnose(problem, state)
                converged = diag is not None and all(
                    r < rhat_limit and min(b, t) > ess_min for r, b, t in diag.values()
                )
                if converged:
                    break
        if not converged:
            burn, diag = _diagnose(problem, state)
        if checkpoint:
            state.save(checkpoint)
    finally:
        if pool is not None:
            pool.shutdown()
    post = state.chain[burn : state.step]
    return Posterior(problem.names, post.reshape(-1, problem.dim), state.lps[burn : state.step].ravel(),
                     diagnostics=diag, burn=burn, steps=state.step, converged=converged,
                     chains=state.chain[: state.step], log_probs=state.lps[: state.step])  # fmt: skip


def around(log_prob, x0, scale, names, lo=None, hi=None, steps=2000, seed=1, ctx=None, progress=(0.0, 1.0)):
    """Sample log_prob(x) (flat priors between lo and hi) around a least-squares x0 with scales: the callers'
    MCMC after a fit. steps: the most generations; the run stops earlier when it has converged."""
    from .priors import Flat
    from .problem import Problem

    n = len(x0)
    lo = np.full(n, -np.inf) if lo is None else np.asarray(lo, float)
    hi = np.full(n, np.inf) if hi is None else np.asarray(hi, float)
    params = {k: (Flat(a, b), float(x), float(s)) for k, a, b, x, s in zip(names, lo, hi, x0, scale, strict=True)}
    problem = Problem(params, lambda v: log_prob(np.array([v[k] for k in names])))
    return run(problem, seed=seed, max_steps=steps, check_every=100, ctx=ctx, progress=progress)
