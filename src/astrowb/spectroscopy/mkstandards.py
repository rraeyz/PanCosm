"""MK spectral type against the MK standard stars, as MKCLASS does (Gray & Corbally 2014, AJ 147, 80).

The standards are Gray & Corbally's libnor36 library: MK standard stars observed with one spectrograph (Dark Sky
Observatory, 3800-5600 A, 3.6 A resolution, 1 A steps, flux normalised), O6 to M5, all luminosity classes. They
are not bundled (no licence to redistribute): they are downloaded once from the authors' MKCLASS page and only
the libnor36 spectra are kept. Each file is named tNNNlnnp00.rbn: NNN the temperature-type running number x 10
(MKCLASS's scale: B0 = 7, A0 = 16, F0 = 23, G0 = 30, K0 = 34, M0 = 40.7), nn the luminosity class x 10
(Ia = 0, Ib = 1, II = 2, III = 3, IV = 4, V = 5).

Method (MKCLASS's matching step; of its rule-based refinement, the separate K-line / hydrogen / metal types of A-F
stars below): the program spectrum is
smoothed to 3.6 A and put on the library's grid; for every luminosity class the standards are interpolated in
temperature (between neighbours at most 4 running numbers apart, as MKCLASS interpolates its library), each
multiplied by a quadratic in wavelength (the unknown instrument response; Gray & Corbally's spectra are flux
normalised, ours are rarely flux calibrated) and compared with the star where its signal is clear. The ranked
types are suggestions with their scores, never applied silently.

Quality (MKCLASS rates each type poor / fair / good / vgood / excellent from the S/N and the match): from the score,
which on the standards themselves behaves as sqrt(0.012^2 + (1 / S/N)^2) (every third standard left out, with
noise): <= 0.02 excellent (S/N above ~100), 0.03 vgood (~50), 0.055 good (~20), 0.10 fair (~10), else poor.

Peculiar A and early F stars (Gray & Corbally 2014, section 3.4: "MKCLASS first determines separate temperature
types for the Ca II K-line, the hydrogen lines, and then for the general metallic-line spectrum"): for a best type
between B9 and F5 the same direct comparison is made in three regions alone — the K line, the hydrogen lines (Hdelta,
Hgamma, Hbeta) and metal-line regions between them — within the best luminosity class. Metal lines three or more
running numbers later than the hydrogen lines, with the K line earlier, suggest an Am star; the K line and the metal
lines both three or more earlier than the hydrogen lines suggest a metal-weak star (lambda Boo, horizontal branch).
These are shown as hints with the three types, as a classifier would write kA1hA5mF0. Lines that mark Ap and barium
stars are checked against the best standard (LINES below).

Checked: (1) every third standard left out of the library, tilted by a random response and given S/N 50, is
classified from the others: 86 % within one subclass, all within two; luminosity class right in 90 %. (2) TOFES
echelle spectra (R 32000): the Sun G0 V (G2 V), Vega A0 V (A0 Va), Arcturus K2 III (K1.5 III).
"""

import io
import re
import tarfile
from pathlib import Path

import numpy as np

MK_URL = "https://www.appstate.edu/~grayro/mkclass/mklib.tar.gz"
RESOLUTION = 3.6  # Angstrom, FWHM of the libnor36 spectra
RANGE = (3800.0, 5600.0)
_NAME = re.compile(r"t(\d{3})l(\d{2})p00\.rbn$")
# MKCLASS temperature running numbers (Gray, MKCLASS documentation, section 5)
TYPES = (
    (3.0, "O6"), (4.0, "O7"), (5.0, "O8"), (6.0, "O9"), (7.0, "B0"), (8.0, "B1"), (9.0, "B2"), (10.0, "B3"),
    (12.0, "B5"), (13.0, "B7"), (14.0, "B8"), (15.0, "B9"), (16.0, "A0"), (17.0, "A1"), (18.0, "A2"),
    (19.0, "A3"), (20.0, "A5"), (21.0, "A7"), (22.0, "A9"), (23.0, "F0"), (24.0, "F2"), (25.0, "F3"),
    (26.0, "F5"), (27.0, "F6"), (28.0, "F8"), (29.0, "F9"), (30.0, "G0"), (31.0, "G2"), (32.0, "G5"),
    (33.0, "G8"), (34.0, "K0"), (35.0, "K1"), (36.0, "K2"), (37.0, "K3"), (38.0, "K4"), (39.0, "K5"),
    (40.0, "K7"), (40.7, "M0"), (41.6, "M1"), (42.5, "M2"), (43.5, "M3"), (44.0, "M3.5"), (44.5, "M4"),
    (45.5, "M5"),
)  # fmt: skip
LUMINOSITY = {0.0: "Ia", 0.5: "Iab", 1.0: "Ib", 1.5: "Ib-II", 2.0: "II", 2.5: "II-III", 3.0: "III", 3.5: "III-IV",
              4.0: "IV", 4.5: "IV-V", 5.0: "V"}  # fmt: skip


def type_name(t, lum):
    """'G2 V' from running numbers."""
    letter = min(TYPES, key=lambda x: abs(x[0] - t))[1]
    return f"{letter} {LUMINOSITY.get(round(lum * 2) / 2, '')}".strip()


def download(folder, fetch=None):
    """The libnor36 standards into folder (once); returns the folder."""
    folder = Path(folder)
    if any(folder.glob("t*l*p00.rbn")):
        return folder
    import urllib.request

    def fetch_url(url):  # the server refuses Python's default client name: the application says what it is
        req = urllib.request.Request(url, headers={"User-Agent": "astronomy-workbench (MK standards download)"})
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (a fixed https URL)
            return r.read()

    fetch = fetch or fetch_url
    data = fetch(MK_URL)
    folder.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if member.isfile() and "libnor36" in parts and _NAME.search(parts[-1]):  # nothing else is written
                f = tar.extractfile(member)
                tmp = folder / (parts[-1] + ".part")
                tmp.write_bytes(f.read())
                tmp.replace(folder / parts[-1])
    if not any(folder.glob("t*l*p00.rbn")):
        raise ValueError("the MK standards could not be read from the download")
    return folder


def load(folder):
    """(wavelengths, {(temperature number, luminosity number): flux}) of the standards in folder."""
    wave, lib = None, {}
    for path in sorted(Path(folder).glob("t*l*p00.rbn")):
        m = _NAME.search(path.name)
        d = np.loadtxt(path)
        if wave is None:
            wave = d[:, 0]
        if d.shape[0] == wave.size:
            flux = d[:, 1].copy()
            covered = np.flatnonzero(flux > 0)
            if covered.size > 4:  # the first and last pixels are cut by the rebinning (K0 V ends at 0.08)
                flux[covered[:2]] = flux[covered[-2:]] = 0.0
            lib[(int(m.group(1)) / 10, int(m.group(2)) / 10)] = flux
    if not lib:
        raise ValueError("no MK standards in the library folder")
    return wave, lib


def _prepare(wave, flux, grid, fwhm):
    from scipy.ndimage import gaussian_filter1d, median_filter

    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    ok = np.isfinite(wave) & np.isfinite(flux)
    wave, flux = wave[ok], flux[ok]
    order = np.argsort(wave)
    wave, flux = wave[order], flux[order]
    step = float(np.median(np.diff(wave)))
    fwhm = fwhm or 2 * step
    if fwhm < RESOLUTION:
        flux = gaussian_filter1d(flux, (RESOLUTION**2 - fwhm**2) ** 0.5 / 2.355 / step)
    obs = np.interp(grid, wave, flux, left=np.nan, right=np.nan)
    level = median_filter(np.nan_to_num(obs), 51)
    obs[level < 0.2 * np.nanpercentile(level, 90)] = np.nan  # where the star is too faint (a red star's blue end)
    return obs


QUALITY = ((0.02, "excellent"), (0.03, "vgood"), (0.055, "good"), (0.10, "fair"))
REGIONS = {  # Angstrom
    "k": ((3922.0, 3945.0),),
    "h": ((4085.0, 4120.0), (4325.0, 4356.0), (4845.0, 4880.0)),
    "metal": ((4140.0, 4300.0), (4370.0, 4460.0), (4500.0, 4620.0), (5150.0, 5350.0)),
}


def quality(score):
    """MKCLASS's words for how good a classification is, from the match score (see the module text)."""
    return next((word for limit, word in QUALITY if score <= limit), "poor")


def _region_type(obs, grid, lib, lum, regions, near, step=0.25):
    """Temperature running number of the standards (luminosity class lum) that best match obs in the regions,
    searched within 6 running numbers of the overall type `near` (the Balmer lines peak at A2: on its own a
    hydrogen strength fits an earlier and a later type, and a classifier brackets around the rough type)."""
    inside = np.zeros(grid.size, bool)
    for a, b in regions:
        inside |= (grid >= a) & (grid <= b)
    temps = sorted(t for t, lc in lib if lc == lum and abs(t - near) <= 6.01)
    best = None
    for a, b in zip(temps[:-1], temps[1:], strict=True):
        if b - a > 4.01:
            continue
        sa, sb = lib[(a, lum)], lib[(b, lum)]
        m = inside & (sa > 0) & (sb > 0) & np.isfinite(obs)
        if m.sum() < 15:
            return None
        x = (grid[m] - grid[m].mean()) / max(np.ptp(grid[m]), 1.0)
        for t in np.arange(a, b + 1e-6, step):
            w = (t - a) / (b - a)
            s = (1 - w) * sa[m] + w * sb[m]
            design = np.vstack([s, s * x]).T  # a straight response within the regions
            coef, *_ = np.linalg.lstsq(design, obs[m], rcond=None)
            score = float(np.sqrt(np.mean((obs[m] - design @ coef) ** 2)))
            if best is None or score < best[0]:
                best = (score, float(t))
    return None if best is None else best[1]


def peculiarity(obs, grid, lib, t, lum):
    """For a B9-F5 star: the types from the K line, the hydrogen lines and the metal lines, and a hint when they
    disagree as in Am or metal-weak stars (see the module text). None outside that range."""
    if not 15.0 <= t <= 26.0:
        return None
    types = {k: _region_type(obs, grid, lib, lum, r, t) for k, r in REGIONS.items()}
    if None in types.values():
        return None
    k, h, m = types["k"], types["h"], types["metal"]
    hint = None
    if m - h >= 3 and k < m:
        hint = "Am"
    elif h - k >= 3 and h - m >= 3:
        hint = "metal-weak"
    letter = {key: type_name(v, lum).split()[0] for key, v in types.items()}
    return {"k": letter["k"], "h": letter["h"], "metal": letter["metal"], "hint": hint, "t": types}


# Lines that mark peculiar stars (Gray & Corbally 2014, section 3.4: "MKCLASS also examines certain specific spectral
# lines, such as Sr II 4077, Si II 4128-30, etc. to detect an Ap star"; barium stars by Ba II 4554): the equivalent
# width in the star minus that in its best-matching standard, over the same local continuum. Limit from normal
# standards (every second one left out, S/N 50): they differ by 0.07-0.10 A, at most 0.29 A -> 0.35 A.
# CN-strong and CH giants: not as equivalent widths (over the Lick windows normal standards differ from their best
# match by 3-4 A, as much as a CN-strong star does) but as the star divided by its best standard, band against the
# nearby continuum (BANDS below).
# name: (feature band, continuum bands, applies to (t_min, t_max, lum_max), hint, limit in A)
LINES = {
    "Sr II 4077": ((4075.2, 4080.2), (4068.0, 4073.0), (4083.0, 4088.0), (15.0, 26.0, 5.0), "Ap (Sr)", 0.35),
    "Si II 4128-30": ((4127.5, 4132.5), (4118.0, 4123.0), (4137.0, 4142.0), (15.0, 26.0, 5.0), "Ap (Si)", 0.35),
    "Ba II 4554": ((4551.5, 4556.5), (4545.0, 4549.0), (4559.0, 4563.0), (32.0, 39.0, 3.5), "Ba star", 0.35),
}


def _ew(grid, f, band, c1, c2):
    def level(b):
        return np.nanmedian(f[(grid >= b[0]) & (grid <= b[1])])

    m = (grid >= band[0]) & (grid <= band[1])
    x1, x2 = np.mean(c1), np.mean(c2)
    cont = level(c1) + (level(c2) - level(c1)) * (grid[m] - x1) / (x2 - x1)
    return float(np.nansum(1 - f[m] / cont))


# Bands of CN-strong and CH giants (G5-K7, III and brighter), over the Lick windows CN1 and G4300 (Worthey et al. 1994,
# ApJS 94, 687): mean of star / best standard in the band over that in the continuum windows. Normal giants (each left
# out, S/N 50): CN 0.985 +- 0.032, never below 0.917; G band 0.998 +- 0.014, never below 0.971. Limits below those:
# a G band 10 % deeper than the standard's is always found, a CN band 20 % deeper always (10 % deeper: half).
BANDS = {
    "CN 4142-4177": ((4142.1, 4177.1), ((4080.1, 4117.6), (4244.1, 4284.1)), 0.87, "CN-strong"),
    "G band (CH) 4281-4316": ((4281.4, 4316.4), ((4266.4, 4282.6), (4318.9, 4335.1)), 0.945, "CH star"),
}


def _model_without(obs, grid, lib, lum, near, masked, step=0.25):
    """The best standard of class lum (within 6 types of `near`) times a quadratic response, fitted with the masked
    wavelengths left out: a strong band must not pull the type that the band is then compared with."""
    use = np.isfinite(obs) & ~masked
    x = (grid - grid.mean()) / np.ptp(grid)
    temps = sorted(t for t, lc in lib if lc == lum and abs(t - near) <= 6.01)
    best = None
    for a, b in zip(temps[:-1], temps[1:], strict=True):
        if b - a > 4.01:
            continue
        for t in np.arange(a, b + 1e-6, step):
            w = (t - a) / (b - a)
            s = (1 - w) * lib[(a, lum)] + w * lib[(b, lum)]
            m = use & (s > 0)
            design = np.vstack([s[m] * x[m] ** j for j in range(3)]).T
            coef, *_ = np.linalg.lstsq(design, obs[m], rcond=None)
            score = float(np.mean((obs[m] - design @ coef) ** 2))
            if best is None or score < best[0]:
                best = (score, s * np.polyval(coef[::-1], x))
    return None if best is None else best[1]


def strong_bands(star, grid, lib, t, lum):
    """[{band, ratio, hint}] for the CN and CH bands much deeper than in the best standard (G0-K7, IV-I); the
    standard is fitted without the band region, as a classifier types the star by its other lines first."""
    if not (30.0 <= t <= 40.5 and lum <= 4.0):  # G0-K7, subgiants to supergiants (CH subgiants exist)
        return []
    star = np.asarray(star, float)
    model = _model_without(star, grid, lib, lum, t, (grid >= 4140.0) & (grid <= 4340.0))
    if model is None:
        return []
    ok = np.isfinite(star) & (model > 0)
    r = np.where(ok, star / np.where(model > 0, model, 1.0), np.nan)
    out = []
    for name, (band, conts, limit, hint) in BANDS.items():
        inside = (grid >= band[0]) & (grid <= band[1])
        cont = np.zeros(grid.size, bool)
        for a, b in conts:
            cont |= (grid >= a) & (grid <= b)
        if np.isfinite(r[inside]).sum() < 10 or np.isfinite(r[cont]).sum() < 10:
            continue
        ratio = float(np.nanmean(r[inside]) / np.nanmean(r[cont]))
        if ratio < limit:
            out.append({"band": name, "ratio": ratio, "hint": hint})
    return out


def strong_lines(star, model, grid, t, lum):
    """[{line, excess (A), hint}] for the lines and bands of LINES much stronger than in the best standard."""
    out = []
    for name, (band, c1, c2, (t0, t1, lum_max), hint, limit) in LINES.items():
        if not (t0 <= t <= t1 and lum <= lum_max):
            continue
        excess = _ew(grid, star, band, c1, c2) - _ew(grid, model, band, c1, c2)
        if np.isfinite(excess) and excess > limit:
            out.append({"line": name, "excess": excess, "hint": hint})
    return out


# Luminosity of G5-M stars from the lines a classifier uses for it (Gray & Corbally 2009): Sr II 4077 and 4216
# (with the CN band and Ca I 4226), the Fe II / Ti II blend 4172-4179, Y II 4376 / Fe I 4383, Mg b and the MgH band
# 4780 (strong in K-M dwarfs), with Fe I 4045 for reference; the standards of every class at the star's temperature
# type are compared in these regions alone. Every late standard left out of the library (S/N 50 and 20): luminosity
# class right in 48 of 56, against 45 from the whole-spectrum match (mixing the two scores did worse).
LATE = 32.0  # G5
GRAVITY_REGIONS = ((4070, 4082), (4210, 4232), (4166, 4182), (4370, 4392), (5160, 5190), (4040, 4050), (4760, 4800))


def _standard_at(lib, t, lum):
    temps = sorted(x for x, lc in lib if lc == lum)
    if t in temps:
        return lib[(t, lum)]
    for a, b in zip(temps[:-1], temps[1:], strict=True):
        if a <= t <= b and b - a <= 4.01:
            w = (t - a) / (b - a)
            return (1 - w) * lib[(a, lum)] + w * lib[(b, lum)]
    return None


def luminosity_from_lines(obs, grid, lib, t):
    """The luminosity class whose standard at temperature type t matches obs best in GRAVITY_REGIONS (each region
    with its own straight response), or None."""
    scores = {}
    for lum in sorted({lc for _, lc in lib}):
        s = _standard_at(lib, t, lum)
        if s is None:
            continue
        total, n = 0.0, 0
        for a, b in GRAVITY_REGIONS:
            m = (grid >= a) & (grid <= b) & np.isfinite(obs) & (s > 0)
            if m.sum() < 5:
                continue
            x = (grid[m] - grid[m].mean()) / 10
            design = np.vstack([s[m], s[m] * x]).T
            coef, *_ = np.linalg.lstsq(design, obs[m], rcond=None)
            total += float(np.sum(((obs[m] - design @ coef) / np.median(obs[m])) ** 2))
            n += int(m.sum())
        if n >= 40:
            scores[lum] = total / n
    return min(scores, key=scores.get) if scores else None


def classify(wave, flux, folder, fwhm=None, top=5, step=0.25, degree=4):
    """[{type, score, t, lum}] best first (score: rms of the relative residual), and the best model on the
    library's wavelengths ({wave, star, model}). fwhm: resolution of the spectrum in A (default two pixels)."""
    grid, lib = load(folder)
    obs = _prepare(wave, flux, grid, fwhm)
    if np.isfinite(obs).sum() < 500:
        raise ValueError("the MK standards cover 3800-5600 A: the spectrum has too little of that range")
    x = (grid - grid.mean()) / np.ptp(grid)
    results = {}
    for lum in sorted({k[1] for k in lib}):
        temps = sorted(t for t, lc in lib if lc == lum)
        for a, b in zip(temps[:-1], temps[1:], strict=True):
            if b - a > 4.01:
                continue
            sa, sb = lib[(a, lum)], lib[(b, lum)]
            m = (sa > 0) & (sb > 0) & np.isfinite(obs)
            if m.sum() < 500:
                continue
            norm = np.median(obs[m])
            for t in np.arange(a, b + 1e-6, step):
                w = (t - a) / (b - a)
                s = (1 - w) * sa[m] + w * sb[m]
                design = np.vstack([s * x[m] ** j for j in range(degree + 1)]).T
                coef, *_ = np.linalg.lstsq(design, obs[m], rcond=None)
                score = float(np.sqrt(np.mean(((obs[m] - design @ coef) / norm) ** 2)))
                key = (round(float(t), 2), lum)
                if key not in results or score < results[key][0]:
                    results[key] = (score, coef, a, b)
    if not results:
        raise ValueError("the MK standards cover 3800-5600 A: the spectrum has too little of that range")
    ranked = sorted(results.items(), key=lambda kv: kv[1][0])
    lines_lum = None
    (t0, lum0), _ = ranked[0]
    if t0 >= LATE:  # G5 and later: the luminosity class from the gravity-sensitive lines at this temperature type
        lines_lum = luminosity_from_lines(obs, grid, lib, t0)
        if lines_lum is not None and lines_lum != lum0 and (t0, lines_lum) in results:
            first = ((t0, lines_lum), results[(t0, lines_lum)])
            ranked = [first] + [kv for kv in ranked if kv[0] != (t0, lines_lum)]
    out, seen = [], set()
    for (t, lum), (score, *_rest) in ranked:
        name = type_name(t, lum)
        if name not in seen:
            seen.add(name)
            out.append({"type": name, "score": score, "t": t, "lum": lum, "quality": quality(score)})
        if len(out) == top:
            break
    (t, lum), (score, coef, a, b) = ranked[0]
    w = (t - a) / (b - a)
    model = ((1 - w) * lib[(a, lum)] + w * lib[(b, lum)]) * np.polyval(coef[::-1], x)
    best = {"wave": grid.tolist(), "star": np.where(np.isfinite(obs), obs, np.nan).tolist(), "model": model.tolist()}
    best["luminosity_from_lines"] = lines_lum is not None and t >= LATE
    best["peculiarity"] = peculiarity(obs, grid, lib, t, lum)
    best["strong_lines"] = strong_lines(obs, model, grid, t, lum)
    best["strong_bands"] = strong_bands(obs, grid, lib, t, lum)
    return out, best
