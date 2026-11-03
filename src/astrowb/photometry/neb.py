"""The nearby-eclipsing-binary check (plans/photometry.md PHO-23), with the rules read from AstroImageJ's
NEBSearchMacro and the TFOP SG1 guidelines (written under PHO-23):

- candidates: stars within the radius (2.5′) bright enough that their eclipse could make the TESS depth;
- each star's Δmag to the target from the measured mean fluxes, made 0.5 mag brighter to be safe (dmagBuffer);
- required depth: NEBdepth [ppt] = target depth [ppt] / 10^(−(Δmag − 0.5) / 2.5);
- RMS of the normalised curve after dropping points beyond rms_limit × RMS from 1 and normalising again;
- dispositions in this order: "Not cleared - flux too low" (mean source − sky per aperture pixel < 2 counts),
  "Cleared - too faint" (NEBdepth ≥ 1000 ppt), "Cleared" (NEBdepth / RMS ≥ 5), "Likely cleared" (≥ 3),
  else "Not cleared"; with several apertures the best disposition per star is kept.
"""

import numpy as np

BUFFER = 0.5
ORDER = ("Cleared", "Likely cleared", "Cleared - too faint", "Not cleared", "Not cleared - flux too low")


def required_depth_ppt(target_depth_ppt, dmag):
    return target_depth_ppt / 10 ** (-(dmag - BUFFER) / 2.5)


def rms(flux, rms_limit=3.0):
    """The scatter of the normalised curve after one clipping pass at rms_limit × RMS, normalised again."""
    f = np.asarray(flux, float)
    f = f / np.median(f)
    r = np.std(f)
    keep = np.abs(f - 1) <= rms_limit * r
    g = f[keep] / np.mean(f[keep])
    return float(np.std(g))


def disposition(depth_ppt, rms_ppt, counts_per_pixel):
    if counts_per_pixel < 2:
        return "Not cleared - flux too low"
    if depth_ppt >= 1000:
        return "Cleared - too faint"
    ratio = depth_ppt / rms_ppt
    return "Cleared" if ratio >= 5 else "Likely cleared" if ratio >= 3 else "Not cleared"


def check(target_flux, star_fluxes, target_depth_ppt, pixels):
    """star_fluxes: {name: flux array (source − sky)}; pixels: the aperture's area. Returns rows with Δmag (measured),
    required depth, RMS (ppt), their ratio and the disposition."""
    t_mean = float(np.mean(target_flux))
    rows = []
    for name, flux in star_fluxes.items():
        f = np.asarray(flux, float)
        mean = float(np.mean(f))
        dmag = -2.5 * np.log10(mean / t_mean) if mean > 0 else np.inf
        need = required_depth_ppt(target_depth_ppt, dmag)
        scatter = rms(f) * 1000 if mean > 0 else np.inf
        rows.append({"name": name, "dmag": dmag, "required_ppt": need, "rms_ppt": scatter,
                     "ratio": need / scatter if scatter > 0 else np.inf,
                     "disposition": disposition(need, scatter, mean / pixels)})  # fmt: skip
    return rows


def best(dispositions):
    """The best of one star's dispositions over several apertures."""
    return min(dispositions, key=ORDER.index)


def candidates(dmag_tess, target_depth_ppt, radius_arcsec, separations_arcsec):
    """Indices of catalogue stars within the radius whose eclipse could make the depth (required depth < 100 %)."""
    dm, sep = np.asarray(dmag_tess, float), np.asarray(separations_arcsec, float)
    need = target_depth_ppt / 10 ** (-dm / 2.5)
    return np.flatnonzero((sep <= radius_arcsec) & (need < 1000))
