# Data for tests and checks

Real observations kept here so that agents do not download them again in every session. Read `PLAN.md` first.

## Rules
- **Links, not files.** Observations are large, so the repository keeps only the notes: one folder per data set,
  under the area that uses it (`photometry/`, `calibration/`, `spectroscopy/`, `astrometry/`, `reference/`, …),
  each with a `SOURCE.md`. It says:
  - what the set is;
  - where it came from, its licence and how to cite it;
  - how to get the whole set;
  - **the exact files used in the checks**, so every agent measures the same frames;
  - what the set is used for.
- **Download into the set's folder.** `.gitignore` keeps the data files there out of git; only `.md` notes and small
  text files (`.csv`, `.txt`, `.json`, `.srl` under 1 MB: logs, line lists) are committed.
- **Before downloading, look in the scratchpad** for a copy from an earlier session of the same container.
- **Never** papers (PDF), other programs' code, MKCLASS files, or derived output.
- **The owner's own data** goes in `owner/`.
  - The owner decides what is kept there.
  - Agents read it but never change, move or delete it, and never copy it outside the repository.
- **When you use a new data set for a check,** add its folder and `SOURCE.md` here and a row below.

## How to download

- **LCO archive** (public frames), one frame by name:
  ```bash
  url=$(curl -s "https://archive-api.lco.global/frames/?basename_exact=<name without .fits.fz>" \
        | python3 -c "import sys, json; print(json.load(sys.stdin)['results'][0]['url'])")
  curl -L -o <name>.fits.fz "$url"
  ```
- **Zenodo:**
  ```bash
  curl -L -O https://zenodo.org/records/<record>/files/<file>
  ```
  Then unpack and keep the files listed in `SOURCE.md`.
- **ESO archive:** the ESO archive pages for the programme or the ARCFILE names listed in `SOURCE.md`
  (`https://archive.eso.org/`). Some downloads need a free ESO account.
- **MAST / TESScut, Kurucz, NIST, STScI:** the URL in `SOURCE.md`, with `curl -L`.

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
