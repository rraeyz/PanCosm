"""A posterior (EXO-5 item 6): samples with their log-probabilities and diagnostics; medians, 68 % and 95 %
intervals, the mode, the correlation matrix, values with asymmetric errors to the right digits, storage as NPZ."""

import json

import numpy as np


def rounded(value, minus, plus, digits=2):
    """The value and its errors to `digits` significant digits of the smaller error, as text."""
    err = min(abs(minus), abs(plus))
    if not np.isfinite(err) or err == 0:
        return f"{value:g}", f"{minus:g}", f"{plus:g}"
    places = max(digits - 1 - int(np.floor(np.log10(err))), 0)
    return f"{value:.{places}f}", f"{minus:.{places}f}", f"{plus:.{places}f}"


class Posterior:
    def __init__(self, names, samples, log_prob, diagnostics=None, burn=0, steps=0, converged=False, chains=None,
                 log_probs=None, derived=None):  # fmt: skip
        self.names = list(names)
        self.samples = np.asarray(samples, float)
        self.log_prob = np.asarray(log_prob, float)
        self.diagnostics = diagnostics
        self.burn, self.steps, self.converged = burn, steps, converged
        self.chains, self.log_probs = chains, log_probs
        self.derived = dict(derived or {})

    @property
    def acceptance(self):
        """The share of moves accepted over the kept generations (a chain stays put when one is rejected)."""
        if self.chains is None or len(self.chains) - self.burn < 2:
            return float("nan")
        kept = self.chains[self.burn :]
        return float(np.mean(np.any(np.diff(kept, axis=0) != 0, axis=-1)))

    def column(self, name):
        if name in self.derived:
            return np.asarray(self.derived[name], float)
        return self.samples[:, self.names.index(name)]

    def add_derived(self, name, function):
        """A derived quantity from every sample: function(dict of parameter values) on arrays."""
        self.derived[name] = np.asarray(function(dict(zip(self.names, self.samples.T, strict=True))), float)

    def summary(self):
        """{name: {"median", "minus", "plus", "lo95", "hi95", "mode"}} for parameters and derived quantities."""
        out = {}
        best = int(np.argmax(self.log_prob)) if len(self.log_prob) else 0
        for name in [*self.names, *self.derived]:
            x = self.column(name)
            q = np.quantile(x, [0.025, 0.15865, 0.5, 0.84135, 0.975])
            out[name] = {"median": q[2], "minus": q[2] - q[1], "plus": q[3] - q[2], "lo95": q[0], "hi95": q[4],
                         "mode": x[best]}  # fmt: skip
        return out

    def summary_table(self):
        """The summary as an astropy Table (one row per parameter or derived quantity), with the diagnostics."""
        from astropy.table import Table

        rows = self.summary()
        diag = self.diagnostics or {}
        t = Table(names=("name", "median", "minus", "plus", "lo95", "hi95", "mode", "rhat", "ess_bulk", "ess_tail"),
                  dtype=(str, float, float, float, float, float, float, float, float, float))  # fmt: skip
        for name, r in rows.items():
            d = diag.get(name, (np.nan, np.nan, np.nan))
            t.add_row((name, r["median"], r["minus"], r["plus"], r["lo95"], r["hi95"], r["mode"], *d))
        t.meta.update({"converged": bool(self.converged), "steps": int(self.steps), "burn": int(self.burn)})
        return t

    def export(self, path):
        """The summary as ECSV or a FITS table (by the file's extension)."""
        fmt = "fits" if str(path).lower().endswith((".fits", ".fit")) else "ascii.ecsv"
        self.summary_table().write(path, format=fmt, overwrite=True)

    def correlation(self):
        return np.corrcoef(self.samples, rowvar=False)

    def save(self, path):
        np.savez_compressed(path, names=json.dumps(self.names), samples=self.samples, log_prob=self.log_prob,
                            derived=json.dumps({k: v.tolist() for k, v in self.derived.items()}),
                            meta=json.dumps({"burn": self.burn, "steps": self.steps, "converged": self.converged,
                                             "diagnostics": self.diagnostics}))  # fmt: skip

    @classmethod
    def load(cls, path):
        with np.load(path) as f:
            meta = json.loads(str(f["meta"]))
            return cls(json.loads(str(f["names"])), f["samples"], f["log_prob"], meta["diagnostics"], meta["burn"],
                       meta["steps"], meta["converged"], derived=json.loads(str(f["derived"])))  # fmt: skip
