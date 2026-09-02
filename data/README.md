# Data for tests and checks

Real observations kept here so that agents do not download them again in every session. Read `PLAN.md` first.

## Rules
- **One folder per data set**, under the area that uses it (`photometry/`, `calibration/`, `spectroscopy/`,
  `astrometry/`, `reference/`, …), each with a `SOURCE.md`: what it is, where it came from, its licence and how to
  cite it, how to get the whole set, what it is used for.
- **Only data that may be shared:** public archive data (LCO, ESO, MAST, Zenodo with an open licence…). Never
  papers (PDF), other programs' code, MKCLASS files, or files whose licence forbids sharing; for those, write only
  the link in `SOURCE.md`.
- **Keep it small:** no file over 50 MB (GitHub refuses 100 MB); for a big night keep a representative part (a few
  frames of each kind, a stretch of the night) and write how to get the rest. Never store derived output
  (`fits_from_raw/`, results, plots): it is made again from the data.
- **The owner's own data** goes in `owner/` (the owner adds it). Agents use it for checks but never change or delete
  it, and never copy it anywhere outside the repository.
- **When you download new data for a check,** add it here (within these rules) and add a row below, so the next
  agent finds it.
- CI does not check this folder out (sparse checkout in `.github/workflows/ci.yml`): tests that need these files
  belong to the validation job or skip when the file is missing.

## Index

| Folder | What | Used for |
| --- | --- | --- |
| `photometry/qatar1-lco` | Qatar-1 b transit, LCO 0.4 m, 24 calibrated frames | Light curves, the aperture scan, the plate solution (Gaia), speed. Full-night results are in `plans/photometry.md`. |
| `photometry/ai-dra-tess` | AI Dra, TESS cut-out, sector 24 | Target-pixel-file photometry, minima, O−C (P = 1.19880 d). |
| `photometry/sa98-landolt-lco` | Landolt SA 98, LCO 1 m, B and V | Transformation coefficients against Landolt (2009) standards. |
| `astrometry/eros-lco` | 433 Eros, LCO 0.4 m, 3 frames | Moving-object astrometry, plate solution against Gaia, MPC report. |
| `calibration/palomar-lfc` | Palomar LFC raw night: bias, darks, flats, lights | Calibration: overscan, dead flat pixels, bias / dark / flat matching. |
| `spectroscopy/tofes-echelle` | TOFES echelle raw: bias, flats, ThAr, Sun, Arcturus, Vega | Echelle orders, 2-D wavelength solution, radial velocities (Arcturus), spectral types. |
| `spectroscopy/efosc-longslit` | EFOSC2 long-slit raw frames | Long-slit reduction: apall, He-Ar arc identification. |
| `spectroscopy/floyds-lco` | FLOYDS raw: star, lamp flat, HgAr arc | Two-order cross-dispersed long slit, curved traces. |
| `spectroscopy/feros-telluric` | FEROS spectra of tau Cet and zeta Phe | Telluric correction. |
| `spectroscopy/feros-ai-phe` | FEROS spectra of AI Phe (SB2) | SB2 radial velocities, disentangling, orbit. |
| `spectroscopy/harps-beta-pic` | HARPS spectra of beta Pic | Atmospheric parameters, rotation. |
| `reference/kurucz-solar-atlas` | Kurucz solar flux atlas | Solar template for wavelengths and radial velocities. |
| `reference/nist` | NIST Xe I lines | Arc line lists. |
| `reference/pickles` | Pickles 1998 spectral library | Spectral-type templates. |
| `owner/` | The owner's own nights (added by the owner) | Real checks of the owner's workflow |
