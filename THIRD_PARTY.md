# Third-party code and data

Every piece of code copied or adapted from another project is listed here with its source
and licence, and marked at the top of the file that contains it.

## Copied / adapted code

None. Other projects' source code may be read to learn (GPL included); it is never
copied. Projects consulted are listed below.

## Consulted (read to learn, nothing copied)

| Project | Licence | For |
|---|---|---|
| — | — | Methods so far were written from the published papers cited in each module's docstring |
| astroalign (README only) | MIT | that triangle matching suits astronomical frames; not used as a library (its `sep` dependency is LGPL) — written from Groth 1986 and Valdes et al. 1995 |
| AstroImageJ (user documentation only) | GPL-3.0 | which aperture choices observers expect: seeing profile, variable aperture scaled by FWHM. The method itself follows Howell (1989) and Merline & Howell (1995); no code read or copied |

## Bundled data

| Data | Source | Licence |
|---|---|---|
| Arc-lamp line lists (IRAF: henear, thar, cuar, fear, ctiohear, ctiohenear, idhenear; air wavelengths) | github.com/astropy/specreduce-data | BSD-3-Clause (`resources/linelists/LICENSE-specreduce-data.rst`) |
| Observatory positions (`resources/observatories.json`: names, latitude, longitude, height) | astropy site registry, github.com/astropy/astropy-data (`coordinates/sites.json`) | BSD-3-Clause |

## Runtime dependencies (used as libraries, not copied)

| Package | Licence | Use |
|---|---|---|
| numpy | BSD-3-Clause | arrays |
| astropy | BSD-3-Clause | FITS, WCS, display stretch |
| platformdirs | MIT | per-user settings folders |
| PySide6 (Qt for Python) | LGPL-3.0 | user interface |
| photutils | BSD-3-Clause | aperture photometry, centroids |
| scipy | BSD-3-Clause | fitting, filters |
| emcee | MIT | MCMC uncertainties of model fits |
| h5py | BSD-3-Clause | HDF5 / NetCDF-4 rasters |
| imagecodecs | BSD-3-Clause | JPEG2000 rasters |
| rawpy (bundles LibRaw: LGPL-2.1 or CDDL-1.0, as a separate shared library; source: https://www.libraw.org) | MIT | DSLR / mirrorless raw files (CR2, NEF, ARW, DNG…) read as the undeveloped sensor mosaic |
| cryptography | Apache-2.0 or BSD-3-Clause | self-signed certificate for the observatory API (HTTPS) |
| matplotlib | Matplotlib licence (PSF-based, permissive) | plots |
| astroscrappy | BSD-3-Clause | cosmic-ray removal (L.A.Cosmic) |
| astroquery | BSD-3-Clause | SIMBAD look-ups |
| alpyca | MIT | ASCOM Alpaca device clients |
| wgpu (wgpu-py, wgpu-native) | BSD-2-Clause (wgpu-native: MIT/Apache-2.0) | GPU compute |
| tifffile | BSD-3-Clause | GeoTIFF / COG read and write |
| pyproj (bundles PROJ: MIT, sqlite: public domain, libtiff: libtiff licence, curl: curl licence) | MIT | map projections, latitude/longitude |
| rendercanvas (dependency of wgpu) | BSD-2-Clause (from the LICENSE file in the wheel; no licence metadata) | — |

## Data downloaded by the application on request (not bundled)

| Data | Source | Use |
|---|---|---|
| Pickles (1998) stellar spectral library, 131 stars | STScI CDBS grid (ssb.stsci.edu/cdbs/grid/pickles) | spectral type, RV templates |
| APASS DR9, Gaia DR3 | VizieR (CDS) | comparison-star magnitudes |
| TESS / Kepler / K2 light curves | MAST (STScI) | light curves |

## Test data (downloaded by CI, not redistributed)

| Data | Source | Use |
|---|---|---|
| HAT-P-32 b transit, MicroObservatory, 2017-12-20 | github.com/rzellem/EXOTIC_sampledata | `tests/validation` |

## Build / test tools

| Package | Licence |
|---|---|
| PyInstaller | GPL-2.0 with bootloader exception (bundled apps may use any licence) |
| Inno Setup | Inno Setup licence (free, incl. commercial) |
| appimagetool | MIT |
| pytest, pytest-qt, ruff | MIT |
| ccdproc, specreduce (tests only, reference implementations) | BSD-3-Clause |

## Data downloaded on first use (not bundled)

| Data | Source | Terms | Use |
|---|---|---|---|
| PHOENIX-ACES synthetic spectra | Husser et al. 2013, A&A 553, A6; phoenix.astro.physik.uni-goettingen.de | cite Husser et al. 2013 | stellar parameters (grid points downloaded as needed) |
| Solar flux atlas | Kurucz 2005, kurucz.harvard.edu/sun/fluxatlas2005 | cite Kurucz 2005 | the Sun as the reference for stellar parameters |

