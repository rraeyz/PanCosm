"""The posterior corner plot (Models and Exoplanets): histograms on the diagonal with the 16/50/84 % lines, the draws as
points below it."""

import numpy as np


def draw_corner(figure, samples, names):
    s = np.asarray(samples, float).reshape(-1, len(names))
    n = s.shape[1]
    axes = figure.subplots(n, n, squeeze=False)
    for i in range(n):
        for j in range(n):
            ax = axes[i][j]
            if j > i:
                ax.set_visible(False)
            elif i == j:
                ax.hist(s[:, i], bins=40, histtype="step")
                for q in np.percentile(s[:, i], [16, 50, 84]):
                    ax.axvline(q, ls="--" if q != np.median(s[:, i]) else "-", lw=0.8)
            else:
                ax.plot(s[:, j], s[:, i], ",", alpha=0.4)
            if i == n - 1:
                ax.set_xlabel(names[j], fontsize="small")
            if j == 0 and i > 0:
                ax.set_ylabel(names[i], fontsize="small")
            ax.tick_params(labelsize=6)
