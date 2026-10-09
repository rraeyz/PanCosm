"""Catalogue magnitudes of the comparison stars and magnitudes of the target in the standard system.

Sources (VizieR, through astroquery): APASS DR9 (B, V, g', r', i') and Gaia DR3 (G, BP, RP). Johnson-Cousins
V, R and I are also computed from Gaia with the polynomials of Riello et al. 2021 (A&A 649, A3, table C.2;
scatter ~0.03 mag), so every star of the Gaia sky has a comparison magnitude.

Calibration (ensemble zero point with a colour term): for every frame
    m_cat - m_inst = ZP(frame) + k * colour
k is fitted once for the night from the comparison stars (needs three with colours), ZP per frame from all of
them. A comparison star that sits far from the fit is reported: it may be variable or blended.
"""

import numpy as np

# G - X = sum(c_i * (BP - RP)^i), Riello et al. 2021, valid for -0.5 < BP-RP < 2.75 (V), 4 (R, I)
GAIA_TO = {
    "V": (-0.02704, 0.01424, -0.2156, 0.01426),
    "R": (-0.02275, 0.3961, -0.1243, -0.01396, 0.003775),
    "I": (0.01753, 0.76, -0.0991),
}
APASS_BANDS = {"B": "Bmag", "V": "Vmag", "SG": "g'mag", "SR": "r'mag", "SI": "i'mag"}
BAND_OF_FILTER = {"CV": "V", "TG": "V", "CR": "R", "TR": "R", "TB": "B"}  # unfiltered / tri-colour: nearest band


def from_gaia(band, g, bp_rp):
    """Johnson-Cousins magnitude from Gaia G and BP-RP."""
    c = GAIA_TO[band]
    return g - sum(ci * bp_rp**i for i, ci in enumerate(c))


def vizier_fetch(coord, radius_arcsec=3.0):
    """{"apass": row or None, "gaia": row or None} of the nearest catalogue entries (the internet, or the cache)."""
    from ..services.cache import cached

    request = ("nearest", round(coord.ra.deg, 6), round(coord.dec.deg, 6), radius_arcsec)
    return cached("vizier", request, lambda: _vizier_fetch(coord, radius_arcsec))


def _vizier_fetch(coord, radius_arcsec):
    import astropy.units as u
    from astroquery.vizier import Vizier

    from ..mirrors import cds

    out, error = {}, None
    for key, cat, cols in (
        ("apass", "II/336/apass9", ["Bmag", "e_Bmag", "Vmag", "e_Vmag", "g'mag", "r'mag", "i'mag"]),
        ("gaia", "I/355/gaiadr3", ["Gmag", "e_Gmag", "BPmag", "RPmag"]),
    ):
        try:
            tables = cds(  # "+_r": nearest first
                "vizier",
                lambda server, cat=cat, cols=cols: Vizier(
                    columns=["+_r", *cols], row_limit=5, vizier_server=server
                ).query_region(coord, radius=radius_arcsec * u.arcsec, catalog=cat),
            )
        except Exception as e:  # noqa: BLE001 - no VizieR server answered: Gaia from the ESA archive below
            tables, error = [], e
        t = tables[0] if len(tables) and len(tables[0]) else None
        if t is None and key == "gaia":
            from ..gaia import photometry

            t = photometry(coord.ra.deg, coord.dec.deg, radius_arcsec / 3600)
            t = t[np.argsort(coord.separation(_sky(t)).arcsec)] if len(t) else None  # nearest first
        row = None if t is None else t[0]
        out[key] = None if row is None else {c: (None if np.ma.is_masked(row[c]) else float(row[c])) for c in cols}
    if error is not None and not any(out.values()):
        raise error
    return out


def _sky(t):
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    return SkyCoord(np.asarray(t["_RAJ2000"], float) * u.deg, np.asarray(t["_DEJ2000"], float) * u.deg)


def star_magnitude(entry, filt):
    """{mag, err, colour, source} of one star in the band of filt, or None."""
    band = BAND_OF_FILTER.get(filt, filt)
    apass, gaia = entry.get("apass"), entry.get("gaia")
    colour = None
    if apass and apass.get("Bmag") is not None and apass.get("Vmag") is not None:
        colour = apass["Bmag"] - apass["Vmag"]
    if apass and band in APASS_BANDS and apass.get(APASS_BANDS[band]) is not None:
        err = apass.get("e_" + APASS_BANDS[band]) or 0.03
        return {"mag": apass[APASS_BANDS[band]], "err": err, "colour": colour, "source": "APASS DR9"}
    if gaia and gaia.get("Gmag") is not None and gaia.get("BPmag") is not None and gaia.get("RPmag") is not None:
        bp_rp = gaia["BPmag"] - gaia["RPmag"]
        colour = colour if colour is not None else bp_rp
        if band == "G":
            return {"mag": gaia["Gmag"], "err": gaia.get("e_Gmag") or 0.003, "colour": colour, "source": "Gaia DR3"}
        if band in GAIA_TO and -0.5 < bp_rp < 2.75:
            return {
                "mag": from_gaia(band, gaia["Gmag"], bp_rp),
                "err": 0.04,
                "colour": colour,
                "source": "Gaia DR3 → JC",
            }
    return None


def calibrate(lc, comps, target_colour=None, colour_term=True):
    """Target magnitudes per frame from the comparison stars' catalogue magnitudes (see the module text).
    comps: [{mag, colour}] in the light curve's comparison order (None for a star without a magnitude)."""
    flux_c = np.asarray(lc["comp_flux"], float)  # frames x comps
    flux_t = np.asarray(lc["target_flux"], float)
    use = [i for i, c in enumerate(comps) if c and c.get("mag") is not None]
    if not use:
        raise ValueError(
            "no comparison star has a catalogue magnitude: plate-solve the first image, choose stars in APASS / Gaia"
        )
    m_cat = np.array([comps[i]["mag"] for i in use])
    with np.errstate(divide="ignore", invalid="ignore"):
        m_inst = -2.5 * np.log10(flux_c[:, use])
        m_t = -2.5 * np.log10(flux_t)
    diff = m_cat[None, :] - m_inst  # ZP + k * colour, per frame and star
    colours = np.array([np.nan if comps[i].get("colour") is None else comps[i]["colour"] for i in use])
    d = np.nanmean(diff - np.nanmean(diff, axis=1, keepdims=True), axis=0)  # per-star mean offset
    good = np.ones(len(use), bool)
    k = 0.0
    for _ in range(len(use)):  # drop the worst star while it is off by > 0.1 mag (variable, blended, bad entry)
        fit_k = colour_term and (good & np.isfinite(colours)).sum() >= 3
        ok = good & np.isfinite(colours)
        k, a = 0.0, np.mean(d[good])
        if fit_k and np.ptp(colours[ok]) > 0.2:
            slope, icpt = np.polyfit(colours[ok], d[ok], 1)
            spread = np.sum((colours[ok] - colours[ok].mean()) ** 2)
            s = np.sqrt(np.sum((d[ok] - slope * colours[ok] - icpt) ** 2) / max(ok.sum() - 2, 1))
            # only a colour term the stars show: four stars over 0.3 mag of colour gave k = -0.40 +- 0.25 on a real
            # LCO night, 0.27 mag off for a bluer target
            if abs(slope) > 3 * s / np.sqrt(spread):
                k, a = slope, icpt
        off = d - a - k * np.nan_to_num(colours)
        worst = int(np.argmax(np.where(good, np.abs(off), -1)))
        if abs(off[worst]) <= 0.1 or good.sum() <= 2:
            break
        good[worst] = False
    k = float(k)
    corrected = diff - k * np.nan_to_num(colours)[None, :]
    zp = np.nanmean(corrected[:, good], axis=1)
    resid = corrected - zp[:, None]
    zp_err = np.nanstd(corrected[:, good], axis=1) / np.sqrt(max(good.sum() - 1, 1))
    mag = m_t + zp + k * (target_colour or 0.0)
    rel = np.asarray(lc["rel_flux"], float)
    phot_err = 2.5 / np.log(10) * np.asarray(lc["rel_flux_err"], float) / rel
    offsets = np.nanmean(resid, axis=0)
    return {
        "mag": mag.tolist(),
        "mag_err": np.hypot(phot_err, zp_err).tolist(),
        "colour_term": k,
        "comp_offsets": {int(i): float(o) for i, o in zip(use, offsets, strict=True)},
        "suspect": [int(i) for i, g in zip(use, good, strict=True) if not g],
    }
