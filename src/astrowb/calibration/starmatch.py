"""Star-pattern matching: the rotation, scale and shift between two frames from their stars, for frames that
are turned (meridian flip, alt-az mount, field rotator) or come from another telescope.

Method (Groth 1986, AJ 91, 1244; Valdes et al. 1995, PASP 107, 1119): the brightest stars of each frame;
triangles of every star with pairs of its nearest neighbours; each triangle described by the ratios of its
sides (b/a, c/a with a >= b >= c), which do not change with rotation, scale or shift; triangles of the two
frames with the same ratios vote for the star pairs at their corners; the pairs with most votes are fitted with a
similarity transform by RANSAC (two pairs fix rotation, scale and shift), then by least squares on every pair
that agrees. In complex numbers z = x + iy the transform is z_frame = a z_ref + b (a = scale e^{i angle}), so the
least-squares fit is one linear solve.
"""

import numpy as np

N_STARS = 40
NEIGHBOURS = 6


def stars(data, n=N_STARS, fwhm=3.0):
    """(x, y) of the n brightest stars, brightest first (0-based pixels)."""
    from astropy.stats import sigma_clipped_stats
    from photutils.detection import DAOStarFinder

    from ..photometry.aperture import despike

    clean = despike(data)
    _, med, std = sigma_clipped_stats(clean[::2, ::2])
    found = DAOStarFinder(fwhm=fwhm, threshold=5 * std)(clean - med)
    if found is None:
        return np.empty((0, 2))
    order = np.argsort(-np.asarray(found["flux"]))[:n]
    return np.column_stack([np.asarray(found["x_centroid"])[order], np.asarray(found["y_centroid"])[order]])


def _triangles(xy, k=NEIGHBOURS):
    """Invariants (b/a, c/a) and corner indices (ordered by the side opposite them, longest first)."""
    from itertools import combinations

    from scipy.spatial import cKDTree

    k = min(k, len(xy) - 1)
    _, nbrs = cKDTree(xy).query(xy, k + 1)
    seen, inv, corners = set(), [], []
    for i, row in enumerate(nbrs):
        for j, m in combinations(row[1:], 2):
            tri = tuple(sorted((i, int(j), int(m))))
            if tri in seen:
                continue
            seen.add(tri)
            p = xy[list(tri)]
            opp = np.array([np.hypot(*(p[1] - p[2])), np.hypot(*(p[0] - p[2])), np.hypot(*(p[0] - p[1]))])
            order = np.argsort(-opp)
            a, b, c = opp[order]
            if c < 2 or c / a < 0.05:  # tiny or flat triangles are unstable
                continue
            inv.append((b / a, c / a))
            corners.append(np.asarray(tri)[order])
    return np.asarray(inv), np.asarray(corners)


def similarity(ref, img):
    """Least-squares a, b with img = a ref + b in complex numbers."""
    zr, zi = ref[:, 0] + 1j * ref[:, 1], img[:, 0] + 1j * img[:, 1]
    (a, b), *_ = np.linalg.lstsq(np.column_stack([zr, np.ones_like(zr)]), zi, rcond=None)
    return a, b


def as_matrix(a, b):
    """The complex transform as (2 x 2 matrix, shift): img = M ref + t."""
    return np.array([[a.real, -a.imag], [a.imag, a.real]]), np.array([b.real, b.imag])


def match(ref_xy, img_xy, tolerance=0.01, max_error=2.0, rng=None):
    """Transform from the reference frame's pixels to the other frame's: (M, t, matched pairs, rms in px).
    Raises ValueError when the star patterns do not match."""
    from scipy.spatial import cKDTree

    if len(ref_xy) < 4 or len(img_xy) < 4:
        raise ValueError("too few stars to match the frames")
    inv_r, cor_r = _triangles(ref_xy)
    inv_i, cor_i = _triangles(img_xy)
    if not len(inv_r) or not len(inv_i):
        raise ValueError("too few stars to match the frames")
    votes = np.zeros((len(ref_xy), len(img_xy)), int)
    for r, cand in enumerate(cKDTree(inv_i).query_ball_point(inv_r, tolerance)):
        for c in cand:
            votes[cor_r[r], cor_i[c]] += 1
    pairs = [
        (i, int(np.argmax(v))) for i, v in enumerate(votes) if v.max() >= 2 and np.argmax(votes[:, np.argmax(v)]) == i
    ]
    if len(pairs) < 3:
        raise ValueError("the star patterns of the frames do not match")
    pr, pi = ref_xy[[p[0] for p in pairs]], img_xy[[p[1] for p in pairs]]
    rng = rng or np.random.default_rng(0)
    best = np.zeros(len(pairs), bool)
    for _ in range(200):  # RANSAC on pairs of pairs
        s = rng.choice(len(pairs), 2, replace=False)
        a, b = similarity(pr[s], pi[s])
        m, t = as_matrix(a, b)
        ok = np.hypot(*(pr @ m.T + t - pi).T) < max_error
        if ok.sum() > best.sum():
            best = ok
    if best.sum() < 3:
        raise ValueError("the star patterns of the frames do not match")
    a, b = similarity(pr[best], pi[best])
    m, t = as_matrix(a, b)
    rms = float(np.sqrt(np.mean(np.sum((pr[best] @ m.T + t - pi[best]) ** 2, axis=1))))
    return m, t, int(best.sum()), rms


def describe(m):
    """Rotation (degrees, counter-clockwise) and scale of a transform matrix."""
    return float(np.degrees(np.arctan2(m[1, 0], m[0, 0]))), float(np.hypot(m[0, 0], m[1, 0]))
