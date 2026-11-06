"""Arc lines identified once, used again: IRAF identify / ecidentify databases and reference arcs ("atlases").

An observatory keeps, per spectrograph and setting, a wavelength-calibrated reference arc and the lines identified
in it (e.g. the LCO FLOYDS pipeline: `archive/<tel>/en06/arc/red/2.0/ftn_red_2.0.fits` with its IRAF database
`database/idftn_red_2.0`). Read here:

- `read_database`: the text databases IRAF's identify and ecidentify write (noao/onedspec/identify/iddb.x,
  ecidentify/ecdb.x): `begin identify <image>`, `features N`, then per line `pixel fit user width ftype weight
  [label]` (identify) or `aperture order pixel fit user width ftype weight` (ecidentify). The user's wavelength is
  taken, the fitted one when the user's is INDEF; lines with weight 0 were rejected in IRAF and are left out.
- `from_reference`: the night's arc is matched to a reference arc as PypeIt's reidentification does (Brodrick
  et al., wvutils.xcorr_shift_stretch): cross-correlation over a range of dispersions (a stretch) and shifts, either
  direction of the wavelength axis; then each reference line is carried to the nearest arc peak and the
  polynomial pixel → wavelength is refitted with tightening tolerance (as IRAF reidentify refits its features).
- `shift_features`: a database made on the same spectrograph's raw pixels (no reference spectrum): the shift is the
  mode of the differences between the database pixels and the arc's peaks (IRAF id_shift1), then each line is
  re-centred on its nearest peak.

The result is a list of (pixel, wavelength) identifications for the user to check — the application never uses
them unseen; the wavelength solution itself is then fitted as usual with the line list.
"""

import re
from pathlib import Path

import numpy as np

_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def read_database(path):
    """[{task, image, aperture, features: [{pixel, wave, label, order?, aperture?}]}] from an IRAF database file."""
    records, current = [], None
    lines = Path(path).read_text(errors="replace").splitlines()
    i = 0
    while i < len(lines):
        words = lines[i].split()
        if words[:1] == ["begin"] and len(words) > 1:
            current = {"task": words[1], "image": " ".join(words[2:]), "aperture": None, "features": []}
            records.append(current)
        elif current is not None and words[:1] == ["aperture"] and len(words) > 1:
            current["aperture"] = int(float(words[1]))
        elif current is not None and words[:1] == ["features"]:
            echelle = current["task"] == "ecidentify"
            while i + 1 < len(lines) and lines[i + 1].split() and _NUMBER.match(lines[i + 1].split()[0]):
                i += 1
                v = lines[i].split()
                try:
                    if echelle:  # aperture order pixel fit user width ftype weight
                        ap, order, pixel, fit, user, weight, label = int(v[0]), int(v[1]), v[2], v[3], v[4], v[7], ""
                    else:  # pixel fit user width ftype weight label
                        pixel, fit, user, weight, label = v[0], v[1], v[2], v[5], " ".join(v[6:])
                    wave = float(fit if user.upper() == "INDEF" else user)
                    feature = {"pixel": float(pixel), "wave": wave, "label": label}
                except (IndexError, ValueError):
                    continue  # a damaged line: skipped, the others are still read
                if float(weight) <= 0:
                    continue  # rejected in IRAF
                if echelle:
                    feature |= {"aperture": ap, "order": order}
                current["features"].append(feature)
        i += 1
    records = [r for r in records if r["features"]]
    if not records:
        raise ValueError(f"{Path(path).name}: no identified lines (not an IRAF identify / ecidentify database?)")
    return records


def _scaled(y):
    """Arc for correlation: background removed, square root (bright lines do not dominate), zero mean, unit sd."""
    y = np.nan_to_num(np.asarray(y, float))
    y = np.sqrt(np.clip(y - np.percentile(y, 20), 0, None))
    return (y - y.mean()) / (y.std() + 1e-12)


def coarse_solution(arc, ref_wave, ref_flux, n_stretch=400):
    """(correlation, coefficients of a linear wavelength(pixel)) of the arc against a reference arc, searched over
    dispersions from a third to three times the reference's step and over all shifts, in both directions."""
    from scipy.signal import correlate

    a = _scaled(arc)
    n = a.size
    w, f = np.asarray(ref_wave, float), _scaled(ref_flux)
    step = float(np.median(np.abs(np.diff(w))))
    best = (-np.inf, None)
    for flip in (False, True):
        aa = a[::-1] if flip else a
        for d in np.geomspace(step / 3, step * 3, n_stretch):
            grid = np.arange(w.min() - n * d, w.max() + n * d, d)
            r = np.interp(grid, w, f, left=0.0, right=0.0)
            cc = correlate(r, aa, mode="valid", method="fft") / n  # cc[k] = sum_j r[k + j] aa[j]
            k = int(np.argmax(cc))
            if cc[k] > best[0]:
                w0 = grid[k]  # wavelength of aa[0]
                coef = np.array([-d, w0 + d * (n - 1)]) if flip else np.array([d, w0])
                best = (float(cc[k]), coef)
    return best


def _carry(peaks, waves, coef, n, steps=((1, 8.0), (2, 4.0), (3, 2.0), (3, 1.5))):
    """Each wavelength placed at the nearest peak of its predicted pixel; the polynomial refitted each time with a
    higher degree and a tighter tolerance (in pixels). Returns [(pixel, index of the wave)], coefficients."""
    peaks = np.sort(np.asarray(peaks, float))
    x = np.arange(n, dtype=float)
    pairs = []
    for deg, tol in steps:
        lam = np.polyval(coef, x)
        order = np.argsort(lam)
        pairs = []
        for k, wv in enumerate(waves):
            p = np.interp(wv, lam[order], x[order], left=np.nan, right=np.nan)
            if not np.isfinite(p) or peaks.size == 0:
                continue
            j = int(np.argmin(np.abs(peaks - p)))
            if abs(peaks[j] - p) <= tol and all(peaks[j] != q for q, _ in pairs):
                pairs.append((float(peaks[j]), k))
        deg = min(deg, max(1, len(pairs) // 3))  # never more terms than the lines can carry
        if len(pairs) >= deg + 2:
            coef = np.polyfit([p for p, _ in pairs], [waves[k] for _, k in pairs], deg)
    return pairs, coef


def from_reference(arc, peaks, ref_wave, ref_flux, lines):
    """Identifications in the night's arc from a reference arc and its identified lines [(wave, label)].
    Returns {pairs: [(pixel, wave, label)], correlation, rms (Angstrom), matched, of}."""
    corr, coef = coarse_solution(arc, ref_wave, ref_flux)
    waves = [w for w, _ in lines]
    pairs, coef = _carry(peaks, waves, coef, len(arc))
    resid = [waves[k] - np.polyval(coef, p) for p, k in pairs]
    return {
        "pairs": [(p, waves[k], lines[k][1]) for p, k in sorted(pairs)],
        "correlation": corr,
        "rms": float(np.sqrt(np.mean(np.square(resid)))) if len(resid) > 2 else float("nan"),
        "matched": len(pairs),
        "of": len(lines),
    }


def shift_features(peaks, features, nbin=10, tolerance=3.0):
    """Database pixels made on this spectrograph's raw frames: shift = mode of the differences peak - feature
    (the narrowest window holding nbin differences, as IRAF id_shift1; fewer when there are fewer lines), then
    each line on its nearest peak. Returns (shift in pixels, [(pixel, feature)])."""
    peaks = np.sort(np.asarray(peaks, float))
    pix = np.array([f["pixel"] for f in features])
    if peaks.size == 0 or pix.size == 0:
        return 0.0, []
    diff = np.sort((peaks[None, :] - pix[:, None]).ravel())
    nbin = min(nbin, pix.size, diff.size) - 1  # a window as many differences wide as lines can agree
    if nbin < 1:
        shift = float(diff[0])
    else:
        widths = diff[nbin:] - diff[:-nbin]
        i = int(np.argmin(widths))
        shift = float(diff[i] + widths[i] / 2)
    out = []
    for f in features:
        j = int(np.argmin(np.abs(peaks - (f["pixel"] + shift))))
        if abs(peaks[j] - f["pixel"] - shift) <= tolerance:
            out.append((float(peaks[j]), f))
    return shift, out


def reference_arc(path):
    """(wave, flux) of a reference arc: a 1-D FITS image with a wavelength WCS, a FITS table or a text file."""
    from . import spectrum_io

    wave, flux, *_ = spectrum_io.read(path)
    return np.asarray(wave, float), np.asarray(flux, float)


def is_frame(path):
    """True for a 2-D frame: the raw arc an IRAF database's pixels were measured on (PESSTO's EFOSC2 references),
    which is matched by a pixel shift, not as a calibrated 1-D spectrum."""
    from astropy.io import fits

    try:
        with fits.open(path) as h:
            return any(x.is_image and x.data is not None and x.data.ndim == 2 for x in h)
    except (OSError, ValueError):
        return False


def find_reference(database):
    """The reference arc an IRAF database was made on: database/id<name> -> <name>.fits next to the folder."""
    path = Path(database)
    name = path.name[2:] if path.name.startswith(("id", "ec")) else path.name
    for folder in (path.parent.parent, path.parent):
        for ext in (".fits", ".fit", ".fits.fz", ".imh"):
            if (folder / (name + ext)).exists():
                return folder / (name + ext)
    return None
