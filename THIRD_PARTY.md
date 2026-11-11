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
| Xenon arc line list (`resources/linelists/xenon.dat`, Xe I air wavelengths, selected by intensity) | NIST Atomic Spectra Database (physics.nist.gov/asd) | Public domain (U.S. Government work) |
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
| pyqtgraph | MIT | interactive plots |
| Inter 4.1 (font, src/astrowb/resources/fonts/InterVariable.ttf) | SIL Open Font License 1.1 (Inter-OFL.txt beside it) | interface text |
| JetBrains Mono 2.304 (font, src/astrowb/resources/fonts/JetBrainsMono-Regular.ttf) | SIL Open Font License 1.1 (JetBrainsMono-OFL.txt beside it) | numbers in tables and read-outs |
| Lucide 0.460.0 (icons, src/astrowb/resources/icons/lucide/) | ISC (LICENSE.txt beside them) | toolbar and menu icons |
| Rust crates compiled into the compiled routines (native/Cargo.lock): pyo3, rayon, ndarray, crossbeam, libc, num-*, syn, quote, proc-macro2 and the others the lock lists | MIT or Apache-2.0 (numpy crate: BSD-2-Clause; unicode-ident also Unicode-3.0; target-lexicon Apache-2.0 with LLVM exception) | compiled routines (`astrowb._native`) |
| rendercanvas (dependency of wgpu) | BSD-2-Clause (from the LICENSE file in the wheel; no licence metadata) | — |

## Data downloaded by the application on request (not bundled)

| Data | Source | Use |
|---|---|---|
| Pickles (1998) stellar spectral library, 131 stars | STScI CDBS grid (ssb.stsci.edu/cdbs/grid/pickles) | spectral type, RV templates |
| MK standard stars, libnor36 (Gray & Corbally 2014, AJ 147, 80; Dark Sky Observatory) | the MKCLASS page, appstate.edu/~grayro/mkclass (mklib.tar.gz; only libnor36 kept) | MK spectral type; cite Gray & Corbally 2014 |
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

## Licences of the bundled libraries (generated from the locked build set)

<!-- licences: generated by tools/check_licenses.py --table -->
| Package | Version | Licence |
| --- | --- | --- |
| alpyca | 3.1.3 | MIT License; Other/Proprietary License |
| altgraph | 0.17.5 | MIT License |
| astropy | 8.0.2 | BSD-3-Clause |
| astropy-iers-data | 0.2026.11.9.0.35.9 | BSD-3-Clause |
| astroquery | 0.4.11 | BSD License; BSD License |
| astroscrappy | 1.3.0 | BSD-3-Clause |
| beautifulsoup4 | 4.15.0 | MIT License |
| certifi | 2026.10.23 | Mozilla Public License 2.0 (MPL 2.0) |
| cffi | 2.1.1 | MIT-0 |
| charset-normalizer | 3.5.2 | MIT |
| colorama | 0.4.6 | BSD License |
| contourpy | 1.4.0 | BSD-3-Clause |
| cryptography | 48.0.1 | Apache-2.0 OR BSD-3-Clause |
| cycler | 0.12.1 | BSD License |
| emcee | 3.1.6 | MIT License |
| enum-tools | 0.13.0 | GNU Lesser General Public License v3 or later (LGPLv3+) |
| fonttools | 4.68.0 | MIT |
| h5py | 3.16.0 | BSD-3-Clause |
| html5lib | 1.1 | MIT License |
| idna | 3.20 | BSD-3-Clause |
| ifaddr | 0.2.0 | MIT License |
| imagecodecs | 2026.10.10 | BSD-3-Clause |
| jaraco.classes | 3.4.0 | MIT License |
| jaraco.context | 6.1.2 | MIT |
| jaraco.functools | 4.6.0 | MIT |
| jeepney | 0.9.0 | MIT |
| keyring | 25.7.0 | MIT |
| kiwisolver | 1.5.1 | BSD License |
| matplotlib | 3.11.2 | Python Software Foundation License |
| more-itertools | 11.2.1 | MIT |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| photutils | 3.1.1 | BSD-3-Clause |
| pillow | 13.0.0 | MIT-CMU |
| platformdirs | 4.14.5 | MIT |
| pycparser | 3.12 | BSD-3-Clause |
| pyerfa | 2.0.1.5 | BSD License |
| Pygments | 2.21.0 | BSD-2-Clause |
| pyparsing | 3.3.3 | MIT |
| pyproj | 3.8.0 | MIT |
| pyqtgraph | 0.14.0 | MIT |
| PySide6_Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| python-dateutil | 2.9.0.post0 | BSD License; Apache Software License |
| pyvo | 1.10.0 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT License |
| rawpy | 0.28.0 | MIT |
| rendercanvas | 3.0.0 | BSD 2-Clause License |
| requests | 2.34.2 | Apache Software License |
| scipy | 1.18.1 | BSD License |
| SecretStorage | 3.5.0 | BSD-3-Clause |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| six | 1.17.0 | MIT License |
| soupsieve | 4.1 | MIT; MIT License |
| tifffile | 2026.11.8 | BSD-3-Clause |
| typing_extensions | 4.16.0 | PSF-2.0 |
| urllib3 | 2.8.0 | MIT |
| webencodings | 0.6.1 | BSD License |
| wgpu | 0.33.0 | BSD 2-Clause License |
<!-- end of generated licences -->
