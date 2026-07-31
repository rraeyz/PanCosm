# Handoff: full test & fix campaign (state on 2026-11-03)

Notes for whoever continues the work. The owner speaks Turkish: answer in Turkish; code, comments
and commits in English. Delete this file once the work is finished.

## The owner's request

- Test the application from top to bottom: every feature, every button, every menu, with real data.
- It must work with **any** data, not only the owner's (MaxIm DL files from the TUG T100 telescope):
  phone pictures (JPEG/PNG/TIFF), DSLR raw, cubes, compressed FITS, odd headers, other observatories.
- Problems that only show up on one distribution (Arch / CachyOS) must be fixed too. The owner also tests on Windows.
- Push straight to `main`. A new release only after CI is fully green, and only after asking the owner.

## Rules of the repository

- The product name may appear only in `brand.toml`, `README.md` and `packaging/install.sh`
  (`tools/check_brand.py`). Everywhere else, this file included, write "the application".
- Before every push: `QT_QPA_PLATFORM=offscreen sh tools/precommit.sh`
  (ruff check, ruff format --check, brand check, i18n check, pytest; about 7 minutes, ~520 tests).
- Every user-visible string goes through i18n: `python tools/i18n.py update`, fill the tr/de/es
  translations, then `python tools/i18n.py` to compile. Messages raised in engine steps need a template in
  `src/astrowb/ui/messages.py` and a case in `tests/test_messages.py`.
- The user guide is in `resources/guide/{en,tr,de,es}`; all four must have the same `##` sections.
- Engine steps (`@step`) run in worker processes started with *spawn*: any script that drives the
  application needs an `if __name__ == "__main__":` guard.
- Never commit the owner's data files.

## Done (all pushed to main)

- Packaged application: SSL certificates via certifi (Arch failed on HTTPS); PyInstaller hooks for
  astroquery, pyvo and photutils data and metadata; `selfcheck.py` checks modules, data files and
  libraries during the CI smoke test; `--check-online` and Help → "Check the installation and internet
  services" test every online service (SIMBAD, VizieR, VSX, Exoplanet Archive, SkyBoT, hips2fits, ZTF, AAVSO,
  MAST, spectral libraries, IERS) and show the report in a window.
- Uncaught errors in the interface show a dialog and go to `error.log`; the window opens sized to the screen.
- Real-observatory FITS headers: non-standard cards (written with `silentfix`), values with units
  (`hdr.py`: `number()` / `get()`, used everywhere headers are read), SITELONG written in hours
  (`timing._longitude` checks it against the sidereal time), 16-bit files with BZERO, cubes (first plane).
- Any picture opens everywhere: JPEG/PNG/TIFF/BMP/WebP and DSLR raw get a FITS copy (`io/bayer.py`:
  `fits_copy`, `fits_paths`); pictures next to FITS frames are treated as previews, not frames.
  Drag and drop onto the window works.
- Calibrate page: explanation of which folder to choose, several folders (`;`), message when there are
  no lights, a master group that fails (e.g. flats darker than the bias) is reported and skipped instead of
  stopping the whole calibration.
- Star-pattern alignment works on real frames (star detection margins and saturation).
- Photometry page: cross cursor, aperture rings follow the mouse, clicking a star again removes it,
  ring colour shows the next role, Graph tab selector filled.
- Moving objects: unsolved frames are plate-solved automatically (scale hint) or skipped.
  astrometry.net called with flags that avoid its Python helpers.
- Period search on a too-short light curve gives a clear message.
- Plan page: list of observatories (astropy sites + `resources/observatories.json`) with completion;
  exposure-time calculator dialog.
- Saving publication figures / pictures falls back to PNG for unknown extensions; model curves read
  files in any encoding.
- Installer (`packaging/install.sh`): menu icon fixed.
- The three example plugins are documented in the Plugins menu.
- Intel Mac: `cryptography<49` there (from 49 PyPI has no Intel-Mac wheel; the source build linked
  Homebrew OpenSSL and the bundle failed with "Symbol not found: _SSL_get0_group_name").
- On the owner's real TUG night every engine step runs; the end-of-night, eclipsing-binary and transit
  automations run through.

## In progress / to do

1. **CI**: check that the run for commit `c508204` (cryptography pin) and later is green on every job,
   above all `package (macos-15-intel)`. If the smoke test still fails there, read its log.
2. **Done in the handoff commit**: `OPEN_PATTERNS` in `src/astrowb/io/bayer.py` now lists every
   FITS suffix (`.fit.gz`, `.fts.gz` were missing from the open dialog). Covered by the existing tests.
3. **Timing headers** (`src/astrowb/timing.py`, was being reviewed): make sure every common way of writing
   the time works: `DATE-OBS` with date only plus `TIME-OBS` / `UT` / `UTSTART` / `TIME_OBS`, `DATE` + `UT`,
   only `JD` / `MJD-OBS`, `EXPOSURE` vs `EXPTIME`, local times with a time zone. `UTSTART` and `TIME_OBS`
   are not read yet. Add a test for each.
4. **GUI sweep on real data**: click every button and menu entry of every page with real frames loaded,
   with file dialogs answered automatically, and collect exceptions and "Task failed" boxes. The last sweep
   was started but its result was not read. Earlier sweeps' findings are all fixed.
5. **Spectroscopy** with real data: the owner offered to send spectra; ask for them.
6. Test unusual data more: colour (RGB) FITS, one-shot-colour Bayer FITS, data only in an extension (MEF),
   8-bit / float / negative / NaN images, very large frames, phone night through photometry.
7. Build the package locally (`packaging/build.py`) and run `--smoke-test` and `--check-online` in it.
8. When everything is green and tested: ask the owner about a new release (tag `v*` starts the release job).
