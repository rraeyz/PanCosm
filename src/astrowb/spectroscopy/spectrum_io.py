"""1-D spectra on disk.

Written: a FITS binary table (WAVE [Angstrom, air], FLUX, ERROR) with the science frame's
header in the primary HDU (times, object, site), readable by specutils and TOPCAT.
Read: that table (also ESO Phase 3 spectra: one row of WAVE / FLUX / ERR arrays); a 1-D image with a
linear or log-linear wavelength WCS (CRVAL1/CDELT1 or CD1_1, CRPIX1, CTYPE1; the format of ISIS, BASS,
IRAF onedspec, LAMOST); or a text file with wavelength and flux columns. Vacuum wavelengths (VACUUM = T)
are converted to air.
"""

from pathlib import Path

import numpy as np
from astropy.io import fits


def write(path, wave, flux, error, header=None):
    cols = [
        fits.Column(name="WAVE", format="D", unit="Angstrom", array=np.asarray(wave, float)),
        fits.Column(name="FLUX", format="D", array=np.asarray(flux, float)),
        fits.Column(name="ERROR", format="D", array=np.asarray(error, float)),
    ]
    prim = fits.PrimaryHDU(header=fits.Header() if header is None else _clean(header))
    fits.HDUList([prim, fits.BinTableHDU.from_columns(cols, name="SPECTRUM")]).writeto(
        path, overwrite=True, output_verify="silentfix"
    )
    return str(path)


def _clean(header):
    h = header.copy()
    for key in ("NAXIS1", "NAXIS2", "BITPIX", "NAXIS", "BZERO", "BSCALE", "EXTEND", "SIMPLE"):
        h.remove(key, ignore_missing=True, remove_all=True)
    return h


def read(path):
    """Return (wave, flux, error or None, header). A gap filled with zeros (HARPS's s1d between its two CCDs,
    5304–5337 A) comes back as NaN: read as flux it was the deepest "line" of the spectrum, and correlating with
    such a template collapsed TODCOR's light ratio (AI Phe: FEROS 0.30 against HARPS 0.61 for the same stars)."""
    wave, flux, err, header = _read(Path(path))
    return wave, _gaps_to_nan(flux), err, header


def _gaps_to_nan(flux, run=3):
    """Runs of at least `run` exact zeros (an instrument gap) as NaN; single zeros are left (a saturated core)."""
    flux = np.asarray(flux, float).copy()
    zero = np.r_[False, flux == 0, False]
    starts, ends = np.flatnonzero(zero[1:] & ~zero[:-1]), np.flatnonzero(~zero[1:] & zero[:-1])
    for a, b in zip(starts, ends, strict=True):
        if b - a >= run:
            flux[a:b] = np.nan
    return flux


def _read(path):
    if path.suffix.lower() in (".txt", ".dat", ".csv", ".asc"):
        data = np.genfromtxt(
            path, delimiter="," if path.suffix.lower() == ".csv" else None, comments="#", invalid_raise=False
        )
        data = data[np.isfinite(data[:, :2]).all(axis=1)]
        return data[:, 0], data[:, 1], data[:, 2] if data.shape[1] > 2 else None, fits.Header()
    with fits.open(path) as hdul:
        for hdu in hdul:
            if isinstance(hdu, fits.BinTableHDU) and "WAVE" in [c.upper() for c in hdu.columns.names]:
                d = hdu.data
                names = {c.upper(): c for c in hdu.columns.names}
                err_name = next((names[k] for k in ("ERROR", "ERR") if k in names), None)

                def column(name, d=d):  # ESO Phase 3 spectra: one row whose cells are the whole arrays
                    return np.asarray(d[name], float).ravel()

                header = hdul[0].header.copy()
                header.update((k, v) for k, v in hdu.header.items() if k in ("SPECSYS", "VACUUM"))
                wave = _air(column(names["WAVE"]), header)
                return (wave, column(names["FLUX"]), column(err_name) if err_name else None, header)
        hdu = hdul[0]
        if hdu.data is None or hdu.data.ndim < 1:
            raise ValueError(f"{path.name}: no spectrum found")
        flux = np.asarray(hdu.data, float).reshape(-1) if hdu.data.ndim == 1 else np.asarray(hdu.data[0], float)
        h = hdu.header
        step = h.get("CDELT1", h.get("CD1_1"))
        if step is None or "CRVAL1" not in h:
            raise ValueError(f"{path.name}: 1-D image without a wavelength solution (CRVAL1/CDELT1)")
        pix = np.arange(flux.size) + 1 - h.get("CRPIX1", 1.0)
        wave = h["CRVAL1"] + step * pix
        if str(h.get("CTYPE1", "")).upper().startswith(("AWAV-LOG", "WAVE-LOG")) or h.get("DC-FLAG") == 1:
            wave = 10**wave if wave.max() < 10 else np.exp(wave)  # log10 (IRAF) or natural log
        h = h.copy()
        return _air(wave, h), flux, None, h


def _air(wave, header):
    """Air wavelengths, as everything here uses (line lists, templates, the files written). Vacuum is converted
    only when the file says so (VACUUM = T: LAMOST, SDSS-style files; one LAMOST star would have been 83 km/s
    off); the header is changed to say the wavelengths are now in air."""
    if header.get("VACUUM") is not True:
        return wave
    from ..core.units import vac_to_air

    header["VACUUM"] = (False, "converted to air on reading (Morton 2000)")
    return vac_to_air(wave)
