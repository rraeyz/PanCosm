"""1-D spectra on disk.

Written: a FITS binary table (WAVE [Angstrom, air], FLUX, ERROR) with the science frame's
header in the primary HDU (times, object, site), readable by specutils and TOPCAT.
Read: that table; a 1-D image with a linear or log-linear wavelength WCS (CRVAL1/CDELT1 or
CD1_1, CRPIX1, CTYPE1; the format of ISIS, BASS, IRAF onedspec); or a text file with
wavelength and flux columns.
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
    fits.HDUList([prim, fits.BinTableHDU.from_columns(cols, name="SPECTRUM")]).writeto(path, overwrite=True)
    return str(path)


def _clean(header):
    h = header.copy()
    for key in ("NAXIS1", "NAXIS2", "BITPIX", "NAXIS", "BZERO", "BSCALE", "EXTEND", "SIMPLE"):
        h.remove(key, ignore_missing=True, remove_all=True)
    return h


def read(path):
    """Return (wave, flux, error or None, header)."""
    path = Path(path)
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
                err = np.asarray(d[names["ERROR"]], float) if "ERROR" in names else None
                return (
                    np.asarray(d[names["WAVE"]], float),
                    np.asarray(d[names["FLUX"]], float),
                    err,
                    hdul[0].header.copy(),
                )
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
        return wave, flux, None, h.copy()
