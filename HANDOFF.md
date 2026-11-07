# Handoff: full test & fix campaign (state on 2026-11-04)

Notes for whoever continues the work. The owner speaks Turkish: answer in Turkish; code, comments
and commits in English. Delete this file once the work is finished.

## The owner's request

- Test the application from top to bottom: every feature, every button, every menu, with real data.
- It must work with **any** data, not only the owner's (MaxIm DL files from the TUG T100 telescope):
  phone pictures (JPEG/PNG/TIFF), DSLR raw, cubes, compressed FITS, odd headers, other observatories.
- Problems that only show up on one distribution (Arch / CachyOS) must be fixed too. The owner also tests on Windows.
- Push straight to `main`. A new release only after CI is fully green, and only after asking the owner.
  How: raise `__version__` in `src/astrowb/__init__.py`, push, then run the `ci` workflow by hand on `main` with
  `release` ticked (GitHub MCP `actions_run_trigger` run_workflow, inputs {"release": true}); the release job makes
  the tag v<version> itself. Pushing a tag from the agent's container is cut off by its proxy.
- Latest (2026-11-04), in the owner's words, summarised:
  - Use the newest `main`, never the v0.1.0 release (its errors are known).
  - After the work is done, test again from the start **like a scientist**: download real observations and spectra
    from the internet (or, if impossible, generate realistic FITS / FIT / TIFF data) and really use the application,
    down to the smallest button. Real problems only show up that way.
  - Error messages must say what happened and what to do, in every interface language.
  - **Look at the code of the established programs for each topic** (IRAF, ccdproc / astropy, Siril, AstroImageJ,
    lightkurve, specreduce, PypeIt, iSpec, MKCLASS, PHOEBE, ...) instead of working from memory or tuning a method
    on a few known stars. A method must hold for an unknown star and an unknown spectrograph.
  - **The user must stay in control.** Calibration steps (e.g. identifying arc lines) may stay with the user; the
    astronomy community does not like everything automatic and opaque. Automatic help is fine as a suggestion the
    user can see, check and override.
  - On wavelength calibration the owner remembers IRAF work with a ThAr *atlas* made for the spectrograph in use.
    (Facts: the line *wavelengths* are physics and the same for every instrument, so one line list serves all; an
    *atlas* is pictures of the lamp spectrum at a given resolution that help a person recognise the pattern. IRAF's
    identify / ecidentify leave the identification to the user, then reidentify / autoidentify with the line list.
    Keep that model: the user identifies, the application fits and matches, and shows every line it used.)
  - Write everything done, downloaded and planned into this file so another agent can continue.
  - Newest (2026-11-04, after the third campaign): the most correct choice must be the default (on when right,
    off when not); **every control shows a short, explanatory tooltip** ("not everyone understands"); **undo / redo
    with Ctrl+Z / Ctrl+Y** (the owner's biggest problem with IRAF). The goal stays: IRAF-quality results, easier
    than IRAF. Keep this file up to date.
  - Latest (2026-11-04, evening): on the Minimum tab both methods stay, the user chooses by what they study,
    Kwee–van Woerden (eclipsing binaries) is the default, shown so a user understands it. **Do every open item**
    (task board below), write each step into this file *before* starting it (claimed) and after finishing it (done),
    so another agent can continue when this one's quota ends. The aim: a complete, high-quality program whose
    output is at the level of a journal paper — a professor working with it must see that.
  - **Newest (2026-11-05, evening) — the fifth campaign, the "last heavy test".** Commits in the owner's name only
    (see the rules). If anything is unfinished, finish it; then test **everything, one by one**, not only the science
    but the use: every button, label, tooltip and text, sitting at the program like an astronomer. Run every feature
    on **real data from the internet**. Then find **raw data together with its published processed version**, reduce
    the raw data here and compare; where no processed version exists, process it with an established program
    (IRAF etc., installed here) and compare. Re-test after every fix. **Note the time** every operation takes (speed
    log below), give an opinion, and fix anything slow (then measure again). Concretely asked: a warning for contact
    (W UMa) binaries about the Roche geometry; the Plan page must explain "ephemeris" and give short explanations on
    its "add to ephemeris" button and the button next to it; several objects (e.g. NY Vir, Saturn, Jupiter,
    Betelgeuse, Moon, Arcturus) in **one** visibility chart, the Moon drawn dashed even when not typed (as other
    programs do); the O−C MCMC must not freeze the page and must be tried on a real minimum-times list. The
    Basic / Expert interface is postponed — **do not forget it** (task U11). Work step by step through the task
    board (claim before, done after), never stop until finished.

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
- **Commits are made in the owner's name**: `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`
  (GitHub user `rraeyz`). No "Claude" anywhere in a commit: no author, no co-author or session trailer (the owner's
  explicit wish, 2026-11-05).
- Network from the agent's container: CDS in Strasbourg (vizier.cds.unistra.fr, simbad.cds.unistra.fr, cdsarc) cuts
  the connection; the Harvard mirrors `vizier.cfa.harvard.edu` and `simbad.harvard.edu` work, as do MAST, ESO, LCO,
  Gaia, IRSA, the Exoplanet Archive, JPL Horizons, PyPI and the Ubuntu archive (IRAF: `apt-get install iraf
  iraf-noao`). github.com release downloads and aavso.org answer 403.

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

## Second campaign (real mouse events on real-like data, all pushed to main)

Driving scripts with QTest clicks on generated data that imitates MaxIm DL nights, phone pictures, long-slit
spectra, eclipsing binaries, a delta Scuti star, O-C minima, a visual binary and a 5-band UTM GeoTIFF, plus the
INDI simulators (`apt install indi-bin`). Fixed on the way, each with a test:

- Marked stars visible on a zoomed-out frame (fixed-size rings); gzipped FITS thumbnails 44 s -> instant;
  8-bit pictures (phone, JPEG, colour PNG) readable on every astropy version (quantised data found from the data).
- Plan page look-ups failed on a background thread (Qt crash risk): `run_step(..., on_fail=...)` runs on the GUI
  thread; error texts drop module paths.
- Observation times: date + UTSTART / UT-START / TIME_OBS / UTC, old dd/mm/yy, MJD, EXP_TIME / ITIME; a date
  without a time of day is an error instead of midnight.
- Spectroscopy: a line window that cuts the line is pointed out; reduced spectra not listed twice.
- Light curves: "Remove outliers" judged points against the median and deleted the eclipses; now against the
  neighbours in time (per night) and, with a period, in phase (cf. lightkurve: flatten, then clip).
- Downloads name their archive and show their error; O-C asks for T0 and P; MCMC shows T0 with decimals; model
  and automation failures are shown on their pages; the area tool's 3-D surface exports as CSV.
- 98 engine error messages had no template (shown in English in every language): translated, and
  `test_every_engine_error_has_a_template` keeps it so.
- A target or comparison star outside the frame is named (photutils gave an array message).
- Observe page: a finished slew shows 100 % and "Finished.".
- Camera clock: one setting (Calibrate page, saved) now applies to pictures and raw files opened on every page;
  default = the computer's UTC offset (as Siril via libraw); the Photometry page shows the offset used.

Checked and correct, nothing to fix: Images page tools and all 16 Process operations, levels, blink, overlays,
save/convert; period search (BLS/PDM exact, LS/ANOVA give P/2 on an Algol, as expected); frequency analysis
(12.3454 / 15.0994 c/d vs 12.3456 / 15.1); O-C linear/quadratic/LTTE/apsidal; EB fit (i 86.46 vs 86.5);
transit export; visual orbit (P 31.38 vs 31.4 yr); remote sensing (pixel read-out, UTM -> lon/lat, NDVI,
k-means, PCA); eclipsing-binary automation (minimum 15.7 s from an independent astropy BJD, 2 sigma); Observe
page with INDI simulators (slew, preview, cooler, focuser, filter, sequence, abort, resume, park).


## Third campaign: real data from the internet (2026-11-04)

All data below were downloaded into `/tmp/claude-0/realdata/` of the build container. **That directory and the
driving scripts in `/tmp/claude-0/real/` are lost when the container ends**; the sources are listed so they can be
fetched again. None of it is committed (data files never go into the repository). The scripts drive the real main
window with QTest clicks; `harness.py` there collects every dialog and exception (`App`, `wait`, `click`, `report`).

### Data used (sources, licences)

| Data | Source | What it is |
|---|---|---|
| Palomar 5 m LFC chip 0, raw night | Zenodo record 3254683, `example-cryo-LFC.tar.bz2` (162 MB) — astropy CCD Data Reduction Guide | bias, darks (sub-folder), g' and i' flats, two 300 s VV 124 frames; overscan in BIASSEC, DATASEC; DATE-OBS date only + UT; LATITUDE / LONGITUD |
| Thermo-electric CCD (MaxIm DL 6), raw night | Zenodo record 3245296, `example-thermo-electric.tar.bz2` (483 MB) — same guide | 10 bias, 10 darks 90 s, 10 r flats, 2 KELT-16 b frames; TRIMSEC '[1:4096, :]', BIASSEC '[4096:4109]' (overscan contaminated by light) |
| TESS FFI cut-out of AI Dra | MAST TESScut API `https://mast.stsci.edu/tesscut/api/v0.1/astrocut?ra=254.0758&dec=52.6983&y=21&x=21&sector=24` (follow the 303 redirect, `curl -L`) | target pixel file, 1226 cadences of 30 min, TIME in BTJD, CADENCENO 0 on every row |
| TOFES fibre echelle, raw | Zenodo record 17968312, `TOFES_testobservations_2024-06-21.tar.gz` (720 MB, CC-BY 4.0), Tartu Observatory | R 32000, 46 orders 87-42 (index 0 = order 87, numbers decrease upwards), ThAr ('comp'), flats, bias, darks; Sun (sky), Vega, Arcturus, CN Boo |
| Kurucz solar flux atlas | `http://kurucz.harvard.edu/sun/fluxatlas2005/fluxspliced.2005` | air wavelengths in nm, normalised flux; telluric-free (the daylight sky spectrum has H2O bands it lacks) |
| LCO FLOYDS raw (2-order cross-dispersed long slit) | LCO archive API `https://archive-api.lco.global/frames/?INSTRUME=en06&RLEVEL=0&public=true&start=2026-10-26&end=2026-10-28` (file URLs in the JSON) | BD+28 4211 spectrum, lamp flat, HgAr arc of 2026-10-27 (OGG); TRIMSEC 'UNKNOWN', DATASEC includes the overscan |
| lightkurve 2.6.0 source | `pip download --no-deps lightkurve` | read for the outlier clipping and the TESS quality bitmask |
| Siril source (src/io) | `https://gitlab.com/free-astro/siril/-/archive/master/siril-master.tar.gz?path=src/io` | read for how camera EXIF times are taken (libraw timestamp, local time zone) |

Reachable from the container: Zenodo, MAST, Exoplanet Archive, LCO archive, JPL Horizons, NED, HEASARC, Kurucz,
PyPI. Blocked: CDS (SIMBAD, VizieR, hips2fits), AAVSO, IRSA/ZTF, data.astropy.org, SDSS, NOIRLab, GitHub API
(git clone of public repositories works). Plate solving is not installed in the container (ASTAP / astrometry.net).

### What the real data showed, and what was fixed (each with a test; commits on main)

- `bb63dc6` Palomar LFC: dead flat pixels (1e-5 of the median) gave calibrated values of 1e8 → flat below 5 % of
  the median is dead (NaN, repaired with *fix defects*), as IRAF ccdproc's `minreplace`. One frame per filter is
  not "stacked"; stack names without a stray "_". Measured FWHM 0.87" agrees with the night log's 0.9" seeing.
- `a8beacc` TE-cooled night: lights had READOUTM and READMODE, calibration frames only READOUTM → nothing matched,
  lights stayed uncalibrated. Readout settings now compared where both headers state them. Sections with a whole
  axis (`[1:4096, :]`, `[*,1:100]`) are read; a one-axis BIASSEC is ignored (this camera's overscan holds leaked
  light, as the astropy guide also says).
- `269faf5` TESS: a target pixel file opened as its 21x21 APERTURE mask. Now `io/tpf.py` writes one frame per
  good cadence (lightkurve's default quality bitmask) into `fits_from_raw/<name>/`, with DATE-AVG chosen so the
  application's BJD_TDB equals the archive's (to < 1 ms). Photometry without comparison stars (space data; the
  page explains what that means from the ground). With T0 and P every primary and secondary minimum is timed in
  its own window and sent to O-C with its type; without them the page asks. AI Dra sector 24: P = 1.19880448 ±
  0.00006527 d from 42 minima (literature 1.19881).
- `3b8e009` TOFES: ThAr frames (`IMAGETYP='comp'`) were "unknown, ignored" → arc lamps are a kind of their own,
  bias / dark subtracted, never flat-fielded or stacked. The echelle 2-D wavelength fit, started from lines in three
  middle orders, ran away in the other orders (order 87 at −1700 Å) → it now grows one order at a time with few
  terms in m while few orders are matched, ignores catalogue lines that cannot be told apart at the tolerance, and
  clips on a robust scale. Solar spectrum: 886 lines, rms 0.005 Å; Na D, Hα, Hβ, Ca 6122 within 0.02 Å of the
  laboratory values. NOTE: an earlier bad result (rms 0.13 Å) came from *my own wrong identifications* made with
  the generic line list; with lines identified properly (checked against the solar Na D lines and the grating
  equation between neighbouring orders) the solver worked. That is the owner's point about atlases: the user must
  be able to identify lines with confidence.
- `a60d3c1` TOFES velocities: the barycentric correction used only the Plan page's site → the spectrum's own
  LATITUDE / LONGITUD are used when the longitude's sign is known (the comment says E+/W+, or the header's LST
  agrees). Arcturus −5.77 ± 0.20 km/s against the solar spectrum (literature −5.19; the solar template carries the
  Sun's +0.64 km/s gravitational redshift). Vega against the Sun is meaningless (A0 vs G2 template) — expected.
  Spectral types: a R 32000 spectrum was compared with the 5 Å Pickles library at full resolution and with an
  underexposed blue → Arcturus "B2IV" with equal scores. Now both are compared at the coarser resolution, each over
  a local continuum, only where the signal is clear: Sun G0-G2, Vega A2-A0, Arcturus G8-K2 (true K1.5 III).
  **Owner's objection (valid, open):** this must be checked against established classification codes (MKCLASS,
  Gray & Corbally; iSpec) and must not be tuned on a few stars; it should stay a *suggestion* shown with its
  scores, never a silent automatic decision.

### Wavelength identifications used for TOFES (for re-running)

Order index 0 = absolute order 87, numbers decrease upwards (Echelle tab: lowest order 87, "decrease upwards").
Found from the solar spectrum: Na D2/D1 at x 1079.7 / 1149.5 in index 29 and Hα at x 1009.2 in index 35 give
m = 58 for index 29 through the grating equation (m λ the same at the same pixel). ThAr lines (pixel, Å):
order 58: 994.49 5882.6242, 1030.00 5885.7016, 1063.52 5888.5841, 1096.89 5891.451, 1195.52 5899.8441;
order 57: 857.72 5973.6649, 1011.27 5987.3016, 1053.47 5991.0071, 1089.25 5994.1287, 1239.29 6007.0722;
order 59: 1073.55 5789.6451, 1106.59 5792.4304, 1149.88 5796.0683, 1206.94 5800.8297, 1246.84 5804.1412.
The lamp also shows Na D emission (x 1079.4 / 1149.3 in order 58).

## Fourth round: undo / redo, defaults, tooltips

- `7cd4187` **Undo / redo**: Edit menu, Ctrl+Z, Ctrl+Y (and Ctrl+Shift+Z). `ui/undo.py`: a page that takes part
  mixes in `Undoable`, calls `init_undo()`, gives `undo_state()` (plain values) and `set_undo_state(state)`, and
  wraps each edit in `self.edit(text, function, ...)`; a value typed into a table is recorded with `record()`
  (`_track_typing` in `spectro_page.py`). The main window's `QUndoGroup` follows the page shown and its open tab.
  Covered: Photometry (stars marked / removed / suggested, deleted and restored points, detrending), Period search
  (outliers, binning, flux / magnitude, points), Images (image operations go back to the image before; header
  changes), Spectroscopy Reduce and Echelle (lines identified, typed, left out; orders removed on the flat).
  Tests: `tests/test_undo.py` (real key presses). Not yet covered: Spectrum tools has its own Undo button (history
  list), the Plan and Observe tables, the Models parameter table.
- **Defaults audit** (every checkbox and choice with its default, `/tmp` script listing them): all were judged right
  (e.g. optimal extraction on, cosmic-ray removal off because stacking with rejection does it, drizzle off, colour
  split on, fibre-fed off). One question for the owner: on the Photometry page's Minimum tab, Kwee–van Woerden
  (eclipsing binaries) or the trapezoid (exoplanet transits) as default — now the trapezoid.
- **Tooltips**: every button, box, list and field on every page has a short explanation (≈180 new strings, all in
  tr / de / es). `tests/test_tooltips.py` fails when a new control has none, and checks one Turkish tooltip.
  Not covered by the test: dialogs (exposure, AAVSO, BeSS, observatory set-up) — most of their fields have tips.

## >>> WHERE THE LAST AGENT STOPPED (read this first) <<<

### >>> START HERE (state on 2026-11-06 ~22:30 UTC, session 019Lu3 stopped: the owner's quota) <<<

**Owner's latest instructions (2026-11-06), on top of the R plan below:**
1. "Do NOT force any order. I have a reduced spectrum and only want the calibration — must I start from the
   beginning? Absurd. Never do that." → no step may be locked behind another; the order of work is a *guide*.
2. "These issues were not only in the spectrum part, they were in ALL of them" (not knowing what to do and how).
   "If it would fill the screen, make it something that opens and closes, called workflow — up to you."
3. Push everything; keep this file clean (old DONE work stays), describe exactly where work stopped.

**Done in this last stretch (all pushed to main, newest last):**
- `7d26165` CI fix: run 137 (`c459063`) failed on all three OS in `tests/test_messages.py::
  test_every_engine_error_has_a_template` — the new `aperture.centroid_1dg` raises "Input data must have a nonzero
  sum and nonconstant values to fit 1D Gaussians." without a template. Template + tr/de/es added in
  `ui/messages.py`. **CI for 7d26165 and later was NOT checked yet** (runs 140+): check it first.
- `3ca2ffc` **Spectra already extracted / only the wavelength calibration** (owner's point 1):
  - `spectroscopy/steps.py`: `looks_extracted(header)` (1-D data, IRAF `APNUM1` / `WAT0_001 multispec`, ESO
    `PRO CATG` E2DS, HARPS DRS e2ds = `ESO DRS CAL LOC NBO == NAXIS2`), `_extracted(path, params, force)` → (flux one
    row per order, IRAF sigma band or None, header), `_poisson` (shortcut: photon noise only when no sigma band).
    `reduce_step` was split into extraction + `_wavelengths(...)`; a 1-D input goes `_reduce_extracted` (no trace,
    no sky lines). `echelle_step` was split into extraction + `_echelle_wavelengths(...)`; new param
    `extracted=None` (None: from the header; True/False: the user's tick); `_echelle_extracted` checks the arc /
    flat have the same shape ("… extract it with the same apertures", template in messages.py).
  - Echelle tab: the lock "First check the orders…" is **removed** (unchecked → orders found automatically are
    extracted; checked rows are still used when present). New tick **Already extracted: one row per order (IRAF
    apall output, an e2ds)**, set by itself from the science file's header (`extracted(path)` in spectro_page.py),
    disables "3. Find the orders", marks guide steps 0 and 2 skipped. Reduce tab: a 1-D science file is detected
    the same way; the trace plot is left out (`_draw` handles `trace is None`). Stale "then 3. Solve" text fixed.
  - Real check (scratchpad `real/r6_extracted.py`, HARPS 2010-08-27 raw + `_e2ds_A`): orders extracted first and
    written as an IRAF-style APNUM file, then calibrated alone → identical wavelengths to the raw path (max 1.2e-10 Å),
    rms 0.0003 Å / 1496 lines both, 22.2 m/s rms vs ESO DRS; the ESO e2ds_A is recognised (72 × 4096) and an arc
    of another extraction (46 orders) is refused with the reason. 1.5 s.
  - Tests: `test_echelle.py::test_already_extracted_orders_are_only_wavelength_calibrated`,
    `test_spectroscopy.py::test_reduce_rv_orbit_steps` (1-D part), `test_order_of_work_and_the_atlas_on_the_echelle_tab`
    (rewritten: no lock, the tick).
- `40e80e0` **"Workflow" on every working page** (owner's point 2): `StepGuide` (ui/workspaces.py) is now a folded
  `Collapsible` whose one-line header reads "Workflow — next: N. <step>" (opens to the steps ✓ / – / ▶, a grey line
  "The usual order, not a rule…" and "Next: <what to do>"); `reset()` added. New guides with state hooks on:
  Calibrate (show_frames → 1, show_result → 2–3, photometry / stack → 4), Period search (set_light_curve, edits,
  show_result), Frequency analysis, Variable star search, Plan, Remote sensing, Telluric, Spectrum tools — besides
  the existing Photometry, O−C, Models, Reduce, Echelle, Radial velocity. All texts translated (tr/de/es; button
  names in the hints copied from the existing translations). Guide pages (4 languages): 01-getting-started (new
  paragraph on the Workflow line), 06-photometry, 08-spectroscopy (Workflow wording, the lock sentences replaced,
  new section "Spectra already reduced"). Test: `test_ui.py::test_every_working_page_has_a_folded_workflow`.
  Not given a guide (no sequence to follow): Images viewer, Observe, Automation, IFU cube, Visual orbit (has its
  own hint line), Start, Guide.
- The full suite was NOT run after `3ca2ffc` / `40e80e0` (only the touched tests: test_echelle, test_spectroscopy,
  test_messages, test_ui -k "photometry or oc or models or spectro or reduce or folded_workflow" — all passed;
  then test_ui + test_spectroscopy + test_echelle + test_messages + the period / frequency / varfind / plan /
  remote-sensing / spectrum-tools tests on the final code: 150 passed). **First thing: `sh tools/precommit.sh` and CI.**

**Session 01RxUU resumed (2026-11-06 ~22:00 UTC) — R5.1 and R4 open questions:**
- R5.1: `sh tools/precommit.sh` green (668 passed, 3 skipped); CI run 146 (`7c65418`) green on all three OS.
- R4 `r2_echelle_atlas` 609 s: the script waited for `tab.order_rows`, which the unlocked Echelle tab no longer sets
  when "Extract" is pressed first (orders are found and extracted in one go) -> 600 s timeout. Script fixed on the
  scratch copy (waits for `order_rows or result`). **Found on the way (program bug, fixed):** choosing ESO raw
  `.fits.Z` files raised `ModuleNotFoundError: uncompresspy` in the tab's header checks `calibrated()` /
  `extracted()` (astropy cannot read LZW without that package). Both now read through `io.lzw.ready_copy` (the
  decompressed copy in fits_from_raw when it exists; otherwise "unknown" / not extracted — a 64 MB HARPS frame is
  not decompressed on the GUI thread; the step's worker makes the copy). Test in `tests/test_lzw.py`. With it the
  Echelle tab extracts raw HARPS (46 orders) in 5.2 s from the GUI (the step alone 12.7 s cold incl. decompression).
  Re-run of `r2_echelle_gui.py` with the fixed wait (and this container's file names, `_` for `:`): 5.5 s instead
  of 609 s; labels unchanged (order 153: 36, 0 wrong, 0.2 mA; index 30/20/44: 41/45/10, 0 wrong, 0.3–0.4 mA).
- R4 `t10_rv_aras` "robust scatter nan": the script's `np.median` over a list with one NaN (a spectrum with no site
  or coordinates keeps only its observed velocity, as designed) — script issue, not the program.
- R4 PESSTO AT 2018hyz -8.5 A: its sky shift is None (night-sky lines too weak in that exposure), so the arc's zero
  point is kept (arc taken later; SN 2018kzr the same night measured -7.2 A of flexure from its sky). Expected
  limit, the status line says so; not re-measured (the raw frame is not in this container).
- Four-language sweep (`real/u6_sweep.py`, tr/en/de/es on the current code): 282 clicks each, 0 exceptions,
  0 untranslated, 0 cut texts, 0 controls without a tooltip; only slow click "Plan the night" 4.2–4.4 s (known:
  worker start + Sun/Moon ephemeris).

**Session 01RxUU, speed / memory against other programs (owner's request of 2026-11-06 ~23:00: "try the rest, compare
every feature's speed with other programs, can the slow ones be faster, RAM / CPU / GPU against other programs"):**
- TESS / Kepler pixel files, compared with **lightkurve 2.6** (NASA's tool) on the same file (WASP-12 b, sector 20,
  16 942 cadences, same 2.07 px aperture): lightkurve 4.1 s; ours was 267 s (43.6 s writing one FITS frame per
  cadence + 224 s measuring) and scattered 3x more. Two causes: (1) every cadence re-centred: the aperture drifted
  onto the wings / a neighbour (x 5.0 -> 7.0 px), 216 cadences 5 % off; (2) per-frame Python overhead. Now
  (`0b88f2d`, `9caea30`): `tpf.source(paths)` recognises frames made from one pixel file, `tpf.cube` reads the
  cadences at once, `photometry.lightcurve._pixel_file_rows` centres the stars once on the median of the cadences and
  `aperture.measure_cube` measures every cadence at once (= measure() per frame to 1e-9, test), fixed apertures as
  SPOC and lightkurve do; `timing.chronological` orders such frames from the file's rows (no 17 000 headers); the
  frames are written by `tpf._FrameWriter` (header made once, only 4 cards formatted). Result: open 13.6 s, measure
  7.4 s, total 21 s (12.7x faster); peak 292 MB (lightkurve 313 MB). Scatter now differs from lightkurve only in a few
  cadences where the sky ring catches a transient (sky 55 000 e- vs 1 360 typical at BJD 2458856.60x; lightkurve
  does not subtract a ring: TESS FLUX is background-subtracted already) — robust spread ours 0.979–1.008 (1–99 %),
  lightkurve 0.975–1.019. WASP-12 transit (P10 re-run): Tc 41 s from SPOC's (was 47), rms 0.00260 (0.00264).
  PSF photometry or "follow the seeing" keep the frame-by-frame path.
- Tried and NOT kept: a NumPy Levenberg–Marquardt instead of scipy least_squares in `centroid_1dg` — only 22 %
  faster and 19 % of faint stamps moved by 1e-4–0.03 px (flat minima): not worth changing results.
- Sentinel-2 memory (`d1d6dce`): PCA / k-means block by block without a copy of every valid pixel: 3.85 -> 2.21 GB
  (PCA, 16.6 -> 18.3 s) and 3.85 -> 1.84 GB (k-means, 31.9 -> 32.1 s) on S2B_36TVK_20250828 B04 + B08 (Element84
  STAC, sentinel-cogs), same explained variance (0.88975 / 0.11025) and classes (test against the old version).
  For scale: QGIS / ESA SNAP stream such rasters in tiles (a few hundred MB); ours still holds the bands whole
  (2 x 120 Mpx float32 = 0.96 GB) — tiled reading would be the next step if 8 GB machines matter.
- Startup (R4 run 34): imports 0.45 s, window 0.08 s, 0.54 s total, 126 MB; 278 MB after opening 6 pages.
- GPU (run 33): no GPU in the container (llvmpipe refused, as designed); stacking 20 x 2048² clipped mean 2.2 s on
  the CPU path. Only stacking has a GPU path (wgpu); never measured on a real GPU.
- Published speed figures of other programs are almost absent: prose (Python photometry framework, arXiv 2111.02814)
  gives ~10 ms per image per star on an i5; AstroImageJ, PixInsight, MaxIm DL publish none (forum anecdotes only).
  Real comparisons therefore only where the other program runs here: IRAF (ccdred 11 s vs ours 18.4 s on 40 LCO
  frames; apphot.phot 1.0 s vs 8.9 s, ours also tracks and centres), lightkurve (above).
- R4 run 31 `phot_steps_timed` (Qatar-1, 265 LCO BANZAI frames 2400 x 2400 fpack, re-downloaded: LCO archive
  `OBJECT=Qatar-1&RLEVEL=91&start=2026-11-02&end=2026-11-04`, 265 files 3.2 GB): quality 69.5 s (262 ms / frame),
  suggest comparisons 37.7 s, apertures 0.3 s, light curve 52.3 s (197 ms / frame); 2 min 41 s in all, 198 % CPU
  (2 of 4 cores), peak 0.89 GB. Half of every frame's time is astropy's fpack (RICE) decompression: 96 ms per frame,
  and the three steps read the 265 frames three times (~76 s). A faster reader (fitsio / cfitsio) has no Windows
  wheels — not taken; sharing the decompressed frames between steps would need ~6 GB of disk for this night.
- IRAF spectroscopy timing (Community IRAF 2.17.1 from Ubuntu, `apt-get install iraf iraf-noao`, USER=root, irafcl
  < script): EFOSC2 LTT 3864 + He-Ar arc: apall (find, trace, extract with background fit) + arc with the same
  aperture + dispcor: all within one second; ours `spectroscopy.reduce` 1.29 s cold (extract), 0.2 s with the
  wavelength solution (13 lines, 0.215 A). IRAF autoidentify found "No solution" from crval 5410 / cdelt 4.2;
  reidentify against itself added no line — IRAF's own solution was therefore not compared (scripts in scratchpad
  iraf_spec/).

**Session 01RxUU, second speed round (owner, 2026-11-07: "use every core; compare everything IRAF and other
programs do; RAM must really be optimised, but never at the cost of time — measure again after every change"):**
- `engine/parallel.py` `pmap(fn, items, ctx)`: frame-by-frame work on processes (spawn). Threads gave nothing:
  astropy's fpack decompression holds the GIL (24 frames 2.34 s serial, 2.37 s on 4 threads). A task worker is a
  daemon process; `pmap` clears the flag so it may start its pool. From a script without `if __name__ ==
  "__main__":` the pool breaks and `pmap` runs on one core instead. Test `test_frames_on_every_core_from_inside_a_
  task_worker`.
- Photometry, 265 Qatar-1 frames, in a task worker (`c942654`): quality 70.1 -> 37.9 s (identical rows; whole tree
  0.76 -> 1.30 GB: each helper loads numpy / astropy), comparison suggestion 37.5 -> 24.9 s (`align_offsets` in runs
  of consecutive frames: identical offsets and stars), light curve 49.5 -> 35.1 s (with 24+ frames: shifts first,
  then each frame read, re-centred from the shifted positions and measured on its own core; relative flux within
  6.4e-5 rms / 4e-4 max of the frame-to-frame path, scatter 0.01146 both, centroids within 0.09 px). Tried and
  dropped: reading ahead on processes (pickling a 23 MB frame costs as much as decompressing it: 50.0 vs 49.5 s).
- Stacking vs **Siril 1.2.1** (apt) and **IRAF imcombine**, 40 Qatar-1 frames (`022f958`, `94e9d18`): sigma
  rejection + additive normalisation 127 -> 26 s, winsorized 171 -> 36 s, identical pixels (the median now from one
  sort, `stacking._median0`, instead of numpy's masked-array nanmedian: 30 of 53 s; bands of rows and frame_stats
  on every core); Siril (convert + star registration + winsorized stack) 11.5 s, 1.2 GB; sky noise ours 1.315 vs
  Siril's 1.294 ADU. Combine only (no alignment, plain FITS): ours 9.7 s / 1.5 GB (block budget `STACK_BUDGET` 128 MB,
  was 512: 11.0 s / 2.3 GB), IRAF imcombine 9.6 s / 0.42 GB, ours - IRAF median 0.012 ADU. The 2.5 GB peak of a
  full stack is the alignment (4 processes with full-resolution float64 FFTs, as before: the serial version also
  peaked at 2.46 GB); float32 FFTs would halve it but change the shifts in the last digits — not done.
- Radial velocities vs **IRAF fxcor** (`32831ae`): the CCF interpolated the template again for every lag; now once
  (`rv.shifted`, `rv.lag_dot`: np.correlate + cumulative sums), also in TODCOR. 7 HARPS stars vs tau Ceti (4500–6500
  A): 35.8 -> 2.1 s (archive files 109.8 -> 3.2 s), fxcor 1.4 s; velocities ours vs fxcor (relative to tau Ceti):
  iot Hor 33.53 / 33.48, Arcturus 11.34 / 11.37, Procyon 13.87 / 13.92, HD 10647 44.31 / 44.26, alf Hya 12.05 /
  12.07, del Pav -4.91 / -4.95, zet Dor (broad) 15.25 / 15.09 km/s; ours unchanged by the rewrite to 1e-3 km/s.
  TODCOR 4 TZ For spectra 56.2 -> 5.0 s, same velocities to 1e-4 km/s.
- Light curve vs IRAF phot, 40 frames: ours 8.2 s plain FITS / 10.5 s fpack (aligns, centres, errors, process start
  included); IRAF phot 1.0 s with positions given per frame.
- Idle cost of the window (owner's question: does O-C work pay for the other pages?): pages are made on first use
  (`_Lazy`), steps run in worker processes that exit after each task; window alone 121 MB, 9 pages opened 289 MB,
  idle 20 s with every page open 0.3 % of one core. The only timers poll an observatory (only when connected) and
  live photometry (only when started).
- Branches: `wip-t11-results-export` was merged long ago (T11 notes) — obsolete, can be deleted (owner to decide);
  `test-scripts` is the real-data scripts branch, never for main. Local `ccr-*` branches are session branches.
- Not done yet / next: IRAF daophot (PSF), continuum, ecidentify (echelle) comparisons; period analysis vs astropy;
  KvW timing of 801 Kepler minima (125 s, bootstrap); GPU paths beyond stacking (no GPU here to measure).

**Session 01RxUU, third speed round (owner, 2026-11-07: "lightkurve takes seconds, why are we 21 s? bring Qatar-1
down too; could other things run on the GPU?"). Machine: this container after a restart (4 cores; the same Qatar-1
runs were ~15 % slower here than before the restart: quality 44.4 s instead of 37.9 s at the start of this round):**
- **CI was red** since `c942654` (validation HAT-P-32 b: out-of-transit scatter 0.0167 > 0.012). Cause, not the
  parallel path: `recenter` median-filtered the whole stamp (`despike`) before the Gaussian centroid; on the
  undersampled MicroObservatory stars (FWHM ~1.5 px) the 3x3 median halved the core (1770 -> 843 ADU) and the centroid
  went ~2 px off (frames 21, 58, 138; the serial path was hit on other frames: 0.0124). Now `aperture._unspike` replaces
  only single hot / cold pixels (a pixel above its brightest neighbour by more than twice that neighbour's height over
  the median, or below all neighbours): HAT-P-32 0.0120 parallel / 0.0119 serial; Qatar-1 unchanged (scatter 0.00503
  vs 0.00502, centroids within 0.12 px). Test `test_centroid_of_an_undersampled_star_next_to_a_hot_pixel` (fails on
  the old code at all 4 sub-pixel positions). `c33e3d6`.
- **TESS pixel file** (WASP-12 s20, 16 942 cadences; lightkurve 4.1 s, which writes no frames): 21 s -> 7.3 s the
  first time, 2.0 s when the frames are kept (0.34 s to open them again). What went: per-cadence UTC conversion
  (now `tpf._utc` at 1000 nodes + both sides of every data gap, interpolated: 12 us off; a straight line over the
  mid-sector gap was 2.7 ms off), astropy reading the IERS polar-motion table to place an observer at the geocentre
  (`tpf._light_travel_time`, identical to 2e-13 s), the archive BJD used as it is in the light curve, header cards
  (`_FrameWriter.card`: the value field only, each card checked against astropy's on its first value), `.part` +
  rename per frame (the listing is written last anyway), writing from 8 threads. What is left: the file system
  creating 16 942 files (~3 s here). `a365dea`.
- **Qatar-1, 265 LCO fpack frames, in task workers** (this container): quality 44.4 -> 32.7 s (`focus.hfr`: sky
  statistics from every 4th pixel each way on frames over 4 MP; FWHM / background / noise within 0.3 %, star counts
  within 0.6 %, the same frames good); light curve 41.4 -> 32.0 s alone (`masters.load(path, crop)`: the measurement
  pass reads only the part of each frame around the stars, margin 155 px + box (the widest centroid box), 5 x r_out
  with radii following the seeing; a tile-compressed frame decompresses only the rows it touches; identical light
  curve, 5e-16); shifts between consecutive frames kept in `<config>/shifts.json` (key: both files' resolved path,
  size, mtime_ns and the binning; 20 000 pairs at most), so comparison suggestion then light curve: 26.5 + 11.1 s
  (was 28.2 + 32.0), again with other radii: 6.1 + 10.9 s. Whole chain 161 s (start of R4) -> 115 s (start of this
  round) -> 70 s. Per frame now: decompression 0.18 s of the 0.5 s quality work; the shift pass 0.33 s (half of it
  decompression) — both already ~3.8x on 4 cores.
- **GPU** (owner asked why only stacking): see the answer in the session log; nothing new on the GPU in this round
  (no GPU in the container or on CI to measure a gain; llvmpipe only proves correctness). Candidates by expected gain:
  median / winsorized stacking (sort per pixel), k-means / PCA of remote-sensing scenes, BLS / Lomb-Scargle on long
  series, Richardson-Lucy deconvolution. Not candidates: fpack decompression (serial bit decoding), file I/O,
  anything with times (float64; wgpu is float32), photometry of a few stars per frame (transfer costs more).

**Session 01RxUU, fourth speed round (owner, 2026-11-07: "do the IRAF daophot / continuum / ecidentify comparisons
and the 801 Kepler minima; write GPU code with the CPU as fallback, it serves the auto / CPU / GPU setting"):**
- **CI** was red on `cb3ba6c` (Windows only): `test_offsets_of_the_same_frames_are_kept` overwrote a frame it had read
  with a memory map (`fits.getdata(..., memmap=False)` now). `d7482f9`.
- **Kwee-van Woerden** (`timeseries.minima`): S(T) for every trial and every bootstrap sample in one go
  (`_s_curves`: the interpolation weights depend on the times only; the bootstrap parabolas from one 9-point fit
  matrix). 753 synthetic Kepler minima (65 267 points, 29.4 min cadence; the real KIC 6525196 file is not in the
  container) 123.7 -> 6.1 s, times identical, errors within 2e-9. Test against a direct np.interp loop. `f35f30d`.
- **IRAF daophot** (phot + pstselect + psf + allstar, empirical PSF, `iraf_dao/`), one Qatar-1 frame (2400 x 2400,
  plain FITS), the same 300 star positions: IRAF 10.5 s / 86 MB; ours (`fieldstars.psf_measure`, Gaussian PRF,
  photutils) 1.6 s / 425 MB (the Python process with numpy / astropy / photutils is most of it). Ours - IRAF: zero
  point 0.026 mag, robust scatter 0.010 mag, the size of either one's errors (0.010 / 0.011).
- **IRAF continuum** (onedspec, spline3, 13 pieces, rejection 1.5 / 3 sigma, 8 iterations) on the 7 HARPS spectra
  of the fxcor comparison: found two faults of ours and fixed them (`1ea2bdb`): the 1 647 exact zeros of the HARPS CCD
  gap (5300 A) counted as data, and the pieces of a long spectrum were fitted one after the other (jumps of up to 0.45
  where they met, 3 of 7 spectra). Now pieces overlap by half and are blended, exact zeros are no data. The level of
  the normalised continuum (95th percentile in 20 A bins) varies 0.004-0.047 over the spectrum, IRAF's 0.015-39.
  Normal equations instead of polyfit: 0.074 -> 0.049 s per 100 000-pixel spectrum; IRAF 0.69 s for the 7 with its
  start. Radial velocities unchanged (within 0.002 km/s), 2.4 -> 2.1 s (archive files 3.5 -> 3.1 s).
- **IRAF ecidentify** (`iraf_ech/`): our extracted HARPS blue-chip arc (46 orders) written as an IRAF multispec image,
  the 1 496 lines our 2-D solution used written as an ecidentify database, IRAF fitting its 2-D Chebyshev (xorder 5,
  yorder 4, 3 iterations of 3-sigma rejection: our deg_x 4 / deg_m 3) through a cursor file (graphics=stdvdm: no
  terminal needed). Against ESO's DRS solution: IRAF rms 22.1 m/s, ours 22.2 m/s (median 0.2 both, max 208 / 209);
  residuals at the lines 23.0 / 22.9 m/s. IRAF needs the lines identified by hand; ours finds them from 9 guesses in
  0.18 s.
- **GPU** (wgpu, the existing rule: every kernel has a NumPy twin, `auto` uses a real GPU only, `gpu` also the software
  adapter the tests use, any failure -> CPU and `compute.disable`):
  - `compute/stack.py` `gpu_combine`: the whole stacking `combine` (mean / median / sum x none / sigma / winsorized /
    minmax / percentile, weights) per pixel, up to 128 frames. On llvmpipe the 15 combinations equal the NumPy version
    within 3e-7 relative, same NaN pixels (`test_gpu_stack_combine_matches_numpy`); a whole stack with normalisation,
    and a GPU failure half-way (the CPU finishes in quarters of rows, within the memory budget), equal to the CPU
    stack (`test_gpu_stack_matches_cpu_stack`). `stack()` decides once whether the GPU is used and tells the bands
    (each band process looked for a GPU before: 0.43 s each without one); on the GPU the blocks are 4x larger (no
    masks and sorts in memory).
  - `compute/classify.py` `gpu_nearest`: the k-means class of every pixel. Same classes as NumPy
    (`test_gpu_nearest_centre_matches_numpy`). The CPU version became one matrix product (`|c|^2 - 2 c.x`): k-means
    of a 10-band 4000 x 4000 scene 7.2 -> 4.6 s (1 pixel of 16 M changed class: a tie); on llvmpipe 5.2 s.
  - `compute.probe()`: the idle spare worker looks for an adapter before its task arrives (no device made: drivers
    hold memory per process), so no task waits the 0.4 s.
  - Measured on the CPU (no GPU here or on CI): 40-frame sigma stack 28.9 s before, 29.1 / 28.7 s after, identical
    pixels (a first version copied the block for the CPU path: +3 s; caught by measuring, fixed). **The GPU speed
    itself is not measured** (llvmpipe is the CPU): to be timed on a machine with a graphics card (`python -m astrowb
    --benchmark` covers the clipped mean; time a median / winsorized stack and k-means there with Settings -> GPU).

**R4 (third full test round) — where it stopped.** The round was run by `real/T3_run.sh` (35 runs in a row, each with
its wall time; a /proc sampler for CPU / RAM ran beside it). **The scripts, the logs and the translation helpers are
saved on the branch `test-scripts`** (not main; see its README: set `SCRATCH` to a folder with `data/` and `env.sh`,
`REPO` to the checkout). Downloaded data are not saved anywhere (rule) — each script / note names the source.

The container restarted while run 31 of 35 (`phot_steps_timed`) was going: runs 1–30 finished, 31–35 did not run
(`phot_steps_timed`, `tpf_open`, `gpu_path`, `startup`, and the resource summary `real/T2_resources.py
work/T3/resources.csv` was never made — the CPU / RAM numbers of round 3 are lost).

**Caveat on the timings:** while runs 4–10 went, the agent was running pytest on the same 4 cores (u8a_calibrate,
u8d_iraf_ccdproc, u6g_fgvir look slower for that reason only). Re-measure on an idle machine before concluding.

| Run | Round 3 (s) | Round 2 (s) | Science result in round 3 (log on `test-scripts`) | Same as round 2? |
|---|---|---|---|---|
| t9_photometry (Qatar-1, 265 LCO frames, whole Photometry page) | 221.5 | 586.8 | transit measured, predicted BJD_TDB 2461347.61115, no message box left open | yes (faster: R3 fixes) |
| t9var_fixed10px | 65.5 | 61.0 | scatter 0.0050, trapezoid O−C +0.1 min, depth 0.0224, T14 1.56 h, KvW O−C −0.4 min | yes |
| bench_photutils | 38.8 | 41.1 | centres vs independent photutils 0.015–0.048 px | yes |
| u5_standard_mags (APASS, AAVSO report) | 224.5 | 346.8 | AAVSO file 272 lines, V ≈ 12.72 | yes (12.745 vs APASS 12.761 in round 2; check the mean) |
| u8a_calibrate (LCO raw vs BANZAI) | 159.0 (step itself 44.9) | 81.1 | 40 frames, scale 1.2678, pixel difference 0.919 ADU (sky noise 9.72) | yes; time see caveat |
| u8d_iraf_ccdproc | 129.3 | 114.2 | ours/IRAF scale 1.00139, pixel difference 0.000 ADU; light curve rms 0.679 vs 0.681 % | yes |
| u8d_iraf_phot | 11.5 | 12.4 | centres 0.038 px median; flux ratio 1.00056; relative flux difference rms 0.063 % | yes |
| u8c_tess_tpf (W UMa s21, 18 758 cadences) | 268.6 | 322.3 | SAP: correlation 1.00000, rms 0.020 %, amplitude 0.5402 vs 0.5403 | yes |
| u1_wuma (Models page on TESS W UMa) | 57.3 | 50.1 | the contact-binary (Roche) warning appears (fills 120 % of the lobe) | yes |
| u6g_fgvir (FG Vir frequencies vs Breger) | 26.9 | 17.3 | frequency table produced (all modes in round 2; not re-compared) | to compare |
| u4_ltte_kepler (KIC 6525196 LTTE) | 293.7 | 236.4 | e3 0.348 ± 0.044, ω3 285 ± 7°, f(m3) 0.102 M☉ (literature P3 418 d) | to compare P3 |
| u6h_efosc_gui (EFOSC2 long slit in the GUI) | 15.5 | 12.5 | 13 lines, degree 4, rms 0.207 Å, 4.23 Å/px | yes |
| u8b_harps_solve (raw HARPS echelle vs ESO DRS) | 11.5 | 144.2 | 22.2 m/s rms vs ESO, median 0.2 m/s | yes (faster: other agent's P5/P6) |
| u8b_harps_rv | 10.0 | 9.7 | rv −0.6 / −9.8 m/s vs ESO's 0 (BERV-corrected), flux correlation 0.9965 | yes |
| t10_rv_archive (tau Ceti ESO archive) | 98.5 | 95.1 | −16.060 ± 0.008 km/s (HARPS DRS −16.68; the solar template adds +0.64) | yes |
| t10_rv_aras (amateur spectra) | 23.6 | 22.8 | median −154.4 km/s; low-R Alpy/LHIRES ±28–72 km/s | yes; "robust scatter nan" printed — check the script |
| t10_mk_lamost (MK types vs LAMOST) | 6.0 | 3.5 | G2 → G0 V (×3), G7 → G8 V | yes (known: metal-weak stars look earlier) |
| u6i_visual_orb6 (η CrB vs ORB6) | 7.5 | 7.5 | rms 0.0259″, total mass 2.075 ± 0.104 M☉ | yes |
| u6j_sentinel2 (NDVI, PCA, k-means) | 155.5 | 189.2 | PCA 89.0 / 11.0 %, k-means 5 classes; GUI 2.44 GB | yes (R3 memory fix holds) |
| u6e_images (every image-processing tool) | 40.7 | 39.9 | 0 problems | yes |
| u3_plan | 16.3 | 16.6 | all targets drawn, Moon dashed | yes |
| u6l_project | 14.8 | 18.5 | 0 problems | yes |
| u6k_automation (raw → calibrate → photometry → minimum) | 52.7 | 70.6 | stops with "no eclipse or transit stands out of the noise…" | **check:** did round 2 find the minimum? (the 40 raw frames may not cover the transit; if they do, it is a bug) |
| u6_sweep_tr (every page and button, Turkish) | 8.5 | 8.2 | 282 clicks, 0 exceptions, 0 untranslated; 1 slow click: Plan → "Geceyi planla" 4.48 s | yes |
| pessto_bench2 (EFOSC2 vs PESSTO) | 2.8 | — | SN 2018kzr correlation 0.84, −1.01 Å; AT 2018hyz 0.70, **−8.51 Å offset** | new; look at AT 2018hyz's offset (sky shift None for it) |
| r1_tzfor_todcor_bf (TZ For vs Gallenne 2016) | 491.2 | — | TODCOR primary +0.33 km/s; BF primary +0.30 rms 0.31, secondary 2 blended epochs ±10 km/s, 0 of 22 failed | as R1 |
| r1_tzfor_orbit | 1.5 | — | circular fit K1 39.0 (Gallenne 38.90) | as R1 |
| r2_echelle_atlas (atlas labels on HARPS) | 609.0 | — | orders 20 / 30 / 44: 45 / 41 / 10 labels, 0 wrong, 0.3–0.4 mÅ | yes. **609 s is too long — find out why** (the step alone takes ~5 s; probably the script waits on the GUI or traces the orders many times) |
| r2_longslit_atlas (EFOSC2 residual plot, leave a line out) | 5.4 | — | 13 lines 0.210 Å → 12 lines 0.090 Å | as R2 |
| horizons_plan (Plan vs JPL Horizons) | 7.3 | — | Moon max 0.080° (rms 0.007), Sun 0.004°; dusk/dawn within 1 min | yes |

**What the next agent does for R4:**
1. Check out `test-scripts`, download the data again (sources in this file: "Second full test round", R1–R3 notes,
   the campaign notes), set `SCRATCH` / `REPO`, run `real/T3_run.sh` **alone on the machine** with
   `real/T2_monitor.py work/T3/resources.csv` beside it; then `python real/T2_resources.py work/T3/resources.csv`.
   At least run 31–35 and the ones marked "to compare" / "check" above.
2. The new paths of this session need a real run too: `real/r6_extracted.py` (spectra already extracted: HARPS,
   expected identical wavelengths, 22 m/s vs ESO), and a GUI pass over the new Workflow lines in the four languages
   (`real/u6_sweep.py work/T3/u6 <lang>` for tr / en / de / es).
3. Open questions found: `r2_echelle_atlas` 609 s; `u6k_automation` no minimum; PESSTO AT 2018hyz −8.5 Å;
   `t10_rv_aras` "robust scatter nan"; Plan "Geceyi planla" 4.5 s. Look at each, fix if it is the program, measure
   again, write the result here.

**R5 still to do (in order):**
1. `sh tools/precommit.sh` green; CI green for the newest commit (GitHub Actions `ci`, runs 140+).
2. Last check of every page and button in the four languages (offscreen screenshots of each page in tr/en/de/es;
   look at texts cut off, untranslated texts, buttons that do nothing; the Workflow lines must fit when folded).
3. Release: raise `__version__` in `src/astrowb/__init__.py` (now "0.2.2") to "0.2.3", push, then run the `ci`
   workflow by `workflow_dispatch` on main with input `release=true` (tags pushed from the container are cut by the
   proxy). The owner HAS authorised this release ("publish the latest release when you think it is ready"). Update
   this file.
4. Give the owner (in Turkish, plain language) the final explanation (he asked for it twice; detailed, with an example
   for each method): BLS / ANOVA / PDM / Lomb–Scargle, RV (CCF,
   BF, TODCOR, orbit, Lucy–Sweeney), spectra (long slit, echelle, atlas, already-extracted path), O−C, photometry;
   what was tested against what (tables in this file) and what was fixed; **step by step how to use Spectroscopy,
   RV and O−C, mapped to the IRAF tasks he knows** (ccdproc → Calibrate; apall → Extract / Find the orders;
   identify / ecidentify → click arc lines + atlas labels; dispcor → Fit wavelengths…; continuum → Spectrum tools;
   telluric → Telluric; fxcor → Radial velocity). This explanation goes in the chat, not in the repo.

### Release campaign R (session 019Lu3, from 2026-11-06 ~16:00 UTC) — CURRENT PLAN, read first

**Owner's request (2026-11-06, summarised):** finish the other agent's open work (P12 stopped half-way, then P13);
when all is done, repeat the tests on the finished program and do whatever they show needs doing. The owner does not
know how to use the RV, spectrum and O−C parts: "I know IRAF: first the science frames are cleaned (bias, dark,
flat), the same for the ThAr and the flat; then the orders are found — even if found automatically the user must
check them by hand; then the wavelength calibration with an atlas. Today I loaded data, pressed something and a
spectrum appeared on the right; I did not know what to do. That is what I mean by 'the program is confusing': not
knowing what to do and how. New methods cannot be invented: the steps the astronomy community is used to must be
followed — for spectra and for every other topic." Then: tests, RAM / CPU / GPU / speed tests, fix what the
measurements show and **measure again after each fix**; a last check of buttons, interface and operations; everything
planned in stages, this file updated as each step is claimed and done; when the program is ready, publish the release.

| Stage | What | Status |
|---|---|---|
| R1 | Finish P12 (TZ For: TODCOR / BF velocities vs Gallenne 2016, orbit, disentangling, MK of the components) | DONE (see the R1 note below the table) |
| R2 | Guided, IRAF-order workflow on the Spectroscopy page (long slit and echelle: calibrate → find / check orders by hand → extract → identify lines with the atlas / line list → fit and check residuals → apply → normalise → velocity), and the same "what to do next" for RV and O−C; guide chapter "If you know IRAF" (IRAF task ↔ page / button) | DONE (note below) |
| R3 | Speed / memory fixes from the second test round (Photometry quality + comparison suggestion 0.5 s per frame, remote-sensing memory 9.3 GB, TESS pixel files split into 18 758 files, single-core work), each measured before and after | DONE (note below) |
| R4 | P13 + third full test round on the finished program (all features on real data, against other programs, timings, CPU / RAM / GPU), fix, measure again | IN PROGRESS — see **START HERE** below |
| R5 | Last check of every page / button in four languages, full suite, CI green, release, plain-Turkish explanation for the owner (incl. how to use spectra, RV, O−C) | open — see **START HERE** below |

**R3 progress (session 019Lu3).** (1) Photometry page before the light curve, 265 Qatar-1 frames (2400 x 2400 fpack),
measured with the same script before / after on a warm disk cache: `photometry.quality` 137 s -> 80 s (frames
measured four at a time in threads: the engine's workers are daemon processes and may not start processes; numpy /
photutils give 1.7x on 4 cores, identical rows); `photometry.suggest_comparisons` 136 s -> 42 s (`align_offsets` reads
the next frame while one is correlated and takes `binning`: the in-frame check needs no stacking precision, 2x2 for
frames over 4 Mpx as the light curve does; the same four comparison stars). Notes: a cold disk makes the first step of
a session up to 2x slower (239 s once for quality); header reading is only 6 ms per fpack file when warm. (2) TESS pixel files
(W UMa s21, 18 758 cadences): opening on the Photometry page 106 s -> 44 s (the frame list opened every file again to
read the time `chronological` had just read: `chronological(paths, times)` now hands the times over, formatted in one
go); measuring 273 s -> 224 s (`aperture.centroid_1dg`: photutils' 1-D Gaussian centroid with the same start values and
least-squares settings without astropy.modeling around it, 3.8 -> 2.5 ms per star, identical centres on 120 real
frames); SPOC SAP agreement unchanged (0.020 % rms). Left as it is: one FITS frame per cadence by design (every tool
works on them); the 44 s are the 18 758 headers read once for the time order. (3) Remote sensing, one Sentinel-2 L2A tile (B04 +
B08, 10980 x 10980), the same GUI script with the resource sampler: whole process tree peak 9.34 GB -> 6.41 GB, the page
4.26 -> 2.42 GB after NDVI + PCA + k-means, the worker's peak per step NDVI 2.56 -> 1.67, PCA and k-means 5.70 -> 3.91
GB; identical products (NDVI = numpy, the same classes and components). How: the page keeps (file, band) of each
product and reads the one shown (`raster.band_count` reads the band count from the TIFF header); `read_bands` fills one
array allocated once (concatenate kept the scene twice); the steps make the nodata value NaN in place
(`Raster.nan_bands`) instead of a copy per band. (4) Echelle step on a raw HARPS chip: now 5.2 s (orders + extraction + arc) and 4.4 s with the
solution, against 77 / 66 s in the second test round — the speed came with the other agent's echelle work (P5 / P6)
that the second round (run on `90e106f`) did not have; the result is the same (1496 lines, 0.0003 A, 22.2 m/s rms
from ESO). **R3 DONE.**

**R2 progress (session 019Lu3).** Done and pushed: `StepGuide` (ui/workspaces.py) — "Order of work" at the top of
the Reduce, Echelle and Radial velocity tabs and the O−C page: the steps in IRAF's order (task names in brackets), each
✓ done / – skipped / ▶ now, and a "Now:" line saying what to do. Echelle: buttons renumbered 3–6 to match; (the first version made extraction wait for the order check — **the
owner rejected that on 2026-11-06, it is removed: nothing may be locked**, see START HERE); raw (uncalibrated) frames are named in the
status (`calibrated()` reads CALB / CALD / ZEROCOR / DARKCOR / CCDPROC). **Atlas help** (Reduce and Echelle): after three
identified lines in an order (or five in two orders for the others) the line list's lines that fall on arc peaks are
labelled on the arc, only between the identified lines and never an ambiguous (blended) line; a click on such a peak
fills in its wavelength (IRAF identify's *l*). Real checks: HARPS raw blue chip, 3 lines in order 153 → 36 labels, 0
wrong, 0.2 mÅ from ESO's solution; other orders 10–45 labels, 0 wrong; EFOSC2 grism 11, 3 lines → 5 labels, max 0.31 Å
(4.2 Å per pixel). Reduce tab: residual plot after the fit, click a line to leave it out, Refit (`exclude` in
`spectroscopy.reduce`): EFOSC2 13 lines 0.210 Å → 12 lines 0.090 Å. Radial velocity tab: each spectrum's correlation
(CCF, BF with the fitted profiles, or TODCOR's best value along each star) is kept (`row["profile"]`) and drawn when a row
is clicked (as fxcor). Guide: new section "If you know IRAF" (IRAF task → page / button) in 08-spectroscopy and the
steps renumbered (4 languages). Tests: `test_order_of_work_and_the_atlas_on_the_echelle_tab`. Then also on the
Photometry page (images → bad frames → target and comparisons → radii → measure → check / minimum / export, as IRAF
phot / AstroImageJ) and the Orbits & models page (light curve → starting values → fit and warnings → errors / table);
the Calibrate page was already numbered (Scan, 3. Calibrate, 4. Measure them on the Photometry page →). Every "Now:"
line names the buttons exactly as they read in each language (checked against the translations). **R2 DONE.**

**R1 / P12 result (done).** TZ For, 22 HARPS ADP s1d (ESO TAP `target_name LIKE '%TZ%For%'`, dataportal), PHOENIX
templates written in air (4900 K / 3.0 for the G8 III primary, 6300 K / 3.5 for the F7 III secondary; v sin i 6.1 and
45.7 km/s from Gallenne et al. 2016, arXiv:1511.07971, Table 1 = their HARPS velocities). Found and fixed:
(1) **TODCOR lost the broad-lined F star** with sharp templates (secondary 40–80 km/s off, light ratio 1.06): new
`template_vsini` / `template2_vsini` (rv step, `rv.rotate`, Velocity tab "Template v sin i (km/s)") — primary
+0.28 +- 0.03 km/s off Gallenne (a constant zero-point difference), secondary within 0.4–0.8 km/s at 6 of 8 epochs.
(2) **The broadening function failed on 14 of 22 spectra** ("fewer than 2 peaks": the F star's broad, low profile
sits on the G star's shoulder and makes no peak): `bf._fit` now fits what it finds, looks for the next star in what
is left (the found stars' profiles left out, 5 sigma of the rest), and fits them together; the model is smoothed like
the BF it is fitted to (a sharp star's profile otherwise left wings). Now 22 of 22: primary +0.30 +- 0.03 km/s,
secondary 0.2–1.4 km/s at 6 of 8 epochs; the 2 epochs where the stars are only ~46 km/s apart (= the F star's
v sin i) stay ~10 km/s off with both methods (Gallenne iterate BF with two templates) — written in the guide.
(3) **SB2 orbit of a circular binary:** with e free, T_peri and omega were undefined, the covariance spoiled every
error (K +- 15 km/s) and a sin i came out 16.7 instead of 120 R_sun (median of the broken draws). Lucy & Sweeney
(1971) test in `fit_orbit` and `fit_sb2` (e < 2.45 sigma_e -> refit with e = 0, omega = 90 fixed, `circular` flag,
said on the Velocity tab and in the export caption); a sin i at the best fit. All 22 epochs: K1 39.01 +- 0.87, K2 39.3
(pulled by the 2 blended epochs), a sin i 117.1 +- 1.8 R_sun; the 10 epochs > 60 km/s apart: K1 39.06, K2 41.52,
gamma 18.6 (Gallenne 38.90 / 40.87 / 17.99–18.35). (4) **Disentangling** (orbit velocities, 3900–5600 A, 18 s): the
components' narrow lines are right — CCF against PHOENIX picks 4900 K for the primary (literature 4930 K) and a hotter
star for the secondary — but their MK types (F8 V, A3 Ia) are wrong because the separable width is 160 km/s = 2.5 A
and the MK types rest on Balmer wings: the Velocity tab already says so after disentangling. Tests:
`test_a_broad_star_on_the_shoulder_of_a_sharp_one`, `test_a_single_star_is_not_split_in_two` (test_bf.py),
`test_a_circular_double_lined_orbit_is_fitted_circular`, `test_a_template_broadened_to_a_fast_rotator`
(test_sb2.py). Timings: TODCOR 22 spectra 4500–6500 A 340–540 s (15–25 s each), BF 22 spectra 155 s. Not changed:
PHOENIX cache files have no VACUUM keyword (they are not offered as templates; noted).


**Owner's go of 2026-11-06 ~12:50 UTC: "start, do all of them in order, do not stop until done"; for missing
data: download real data with astropy / astroquery / archives (Gaia, TESS…) and try every feature with them.**
Network from the agent container (12:50 UTC): ESA Gaia archive gea.esac.esa.int OK; VizieR: CDS no answer, CfA OK
(empty for Gaia / APASS), IDIA slow; ESO archive OK; NASA Exoplanet Archive OK; IRSA OK; MAST API answers; AAVSO 403
(bot check — never try to get around it); BeSS 500.
**Note (session 019Lu3, ~15:30 UTC):** a second full test round (real data against IRAF, BANZAI, photutils, SPOC,
ESO DRS, PESSTO, ORB6, JPL Horizons; timings; CPU / memory / GPU use) was run on `90e106f`, i.e. **before** P1–P3
below, with no code changed — see the section "Second full test round, 2026-11-06" further down. Its speed / memory
ideas are **suggestions only** for the owner to decide on.
Plan (claim → done, in this order):
- P1 **DONE** Photometry: MaxIm-like list of all frames beside the image (name, time, FWHM, sky, use box; click shows the
  frame; bad frames red) + "blink" button. Done: `PhotometryPage.frame_table` (name, mid-exposure UTC, FWHM, sky,
  check box = use), kept in step with the arrows / slider / "Use this frame"; "Blink" (QTimer 450 ms) steps through
  the frames in use and the viewer keeps the zoom (`ImageViewer.set_image(keep_view=True)` for same-size frames);
  "Find the bad frames" fills FWHM / sky, colours bad frames red and now shows its plot (the lower panel was hidden);
  "Leave out the bad frames" unticks them instead of deleting them from the list (deleting broke the frame numbers
  of marked stars). Test `test_frame_list_quality_and_blink`. Guide 06 (4 languages).
- P2 **DONE** Basic / Expert interface mode (U11): Start page radio buttons + Settings → Expert mode, kept as `ui.mode`
  (default basic). `Collapsible(mode=...)`: "expert" sections (more calibration options, stacking options, the new
  "More measuring options" on Photometry = follow seeing / PSF / telescope aperture, other tools) open in Expert and
  are folded in Basic; "basic" sections (Spectroscopy's order of work) the other way; applied to every built page
  and to pages built later (`MainWindow.set_ui_mode`, `_apply_mode`). Nothing is hidden for good. Test
  `test_basic_and_expert_mode`. Guide 01 (4 languages).
- P3 **DONE** Gaia DR3 refinement of plate solutions (`astrowb/gaia.py`): stars from VizieR (mirrors) or the ESA Gaia
  archive (gea.esac.esa.int; when its synchronous queue answers 503 "overloaded" the asynchronous queue is used),
  moved to the frame's epoch by proper motion, cached per cone (x1.3 radius) so a series is fetched once (the ESA
  archive took 8–53 s per cone here); `refine_wcs` detects the frame's stars (starmatch.stars, not re-centred:
  median 0.03 px), matches them, fits TAN-SIP (astropy fit_wcs_from_points, degree 3 with ≥ 40 stars), clips
  blends at 3x the median residual, re-matches 3x; header ASTCAT = Gaia3, ASTRRMS, ASTRNST. `astrometry.solve` step:
  `refine_gaia=True` (offline → ASTRNOTE says why, solver's WCS kept). The Gaia overlay falls back to the ESA archive
  too (`gaia.chart_stars`). Real checks: LCO 0.4 m frame of 433 Eros (cpt0m439-sq39-20260808-0080-e91): 141 Gaia
  stars, against 64 Gaia stars G < 15 centroided independently: BANZAI WCS 0.444", 2MASS solve 0.646", Gaia refit
  0.021" (median). Eros against JPL Horizons (astrometric, topocentric, mid-exposure), frames 0080/0081/0082:
  BANZAI dRA +0.26..+0.31 dDec +0.20..+0.24"; 2MASS +0.44..+0.76 / +0.15..+0.38"; Gaia refit −0.108..+0.022 /
  −0.023..+0.027". Tests `tests/test_gaia_refine.py` (synthetic field shifted 1.9" and turned 0.05°: 0.1" over the
  frame; too few stars said; cache). Guide 05 (4 languages).
- P4 **DONE** Period page errors: `PeriodPage.err` from the Photometry page (rel_flux_err), TESS / Kepler / ZTF /
  AAVSO downloads, survey files and a third CSV column; error bars on the light curve and the folded curve; kept
  through clipping, binning (`fourier.bin_time(..., err)`: sqrt(Σσ²)/n or the bin's scatter/√n if larger), deleted
  points, flux ↔ mag (σm = 1.0857 σF/F), undo; saved as a third column; `timeseries.period` has an optional input
  `err` and weights Lomb–Scargle and BLS by 1/σ² (PDM / ANOVA unweighted). Tests in `test_period_search_tab`,
  `test_binned_errors_and_a_weighted_period_search`. Guide 07 (4 languages).
- P5 **DONE** Echelle: zero point from the night-sky lines for slit echelles (`sky` on, not fibre): the inter-order
  sky (extraction without minus with sky subtraction) of the orders holding [O I] 5577 / 6300 / 6363
  (`wavecal.sky_shift_orders`, combined with the long-slit rule `combine_sky`), shift applied to every order,
  `WAVSKYSH`, status line. **Bug found and fixed on the way:** `wavecal.sky_shift` fitted the line in absolute
  wavelengths; at echelle dispersion (0.03 A/px) curve_fit did not converge at all (every line rejected) — now fitted
  as an offset from the line, started at the brightest pixel (long-slit tests unchanged). Not checked on real data:
  the only raw echelle frames here (TOFES, HARPS) are fibre-fed — no sky between the orders. Test
  `test_zero_point_from_the_sky_lines_over_the_orders`. Guide 08 (4 languages).
- P6 **DONE** HARPS night drift: only one evening ThAr was downloaded (21:59:48, WAVE,WAVE,THAR2), but the science
  frame (05:33:35, STAR,WAVE,G8) has the simultaneous ThAr in fibre B — the drift over the night is fibre B of the
  science frame against fibre B of the evening ThAr, as the ESO pipeline measures it. New `echelle.drift(reference,
  spectrum)`: Bouchy, Pepe & Queloz (2001) photon-weighted shift per order (cosmic rays > 6σ left out), combined by
  inverse variance. Script: traces on the flat (fibre A), fibre B found 16 px away from the science frame's ThAr light,
  boxcar 1.2 FWHM; velocity per pixel 818.8 m/s from ESO's e2ds_B wavelength polynomials. Result (blue chip, 46
  orders): **+0.21 +- 0.08 m/s**; ESO DRS (`ESO DRS DRIFT SPE RV`, ccf_G2_A of ADP.2014-09-24T09:42:58.973):
  +0.423 +- 0.08 m/s against the 22:05:43 ThAr (THAR1; ours is the 21:59 one) — agrees to 0.2 m/s (1.9 sigma, part
  of it the 6 min between the two reference frames). Per-order scatter 1.5 m/s. Not in the interface (HARPS-like
  simultaneous-reference spectrographs only): a library function with test `test_drift_of_a_lamp_spectrum_as_harps_
  measures_it`. Data: /tmp/claude-0/realdata/harps (ESO archive raw files listed in U8b above; anc.tar = the ESO
  products of ADP.2014-09-24T09:42:58.973).
- P7 **DONE — two bugs.** TODCOR light ratio of AI Phe (tau Ceti HARPS s1d as template for both stars): FEROS 0.33,
  HARPS 0.66. Window by window (4500–5000 / 5000–5500 / 5500–6000 / 6000–6500 A) both agreed (0.68/0.66, 0.53/0.52,
  0.50/0.49) except 5000–5500, where FEROS gave ~0 and the correlation peak fell to 0.2: **HARPS's s1d fills the gap
  between its CCDs (5304–5337 A) with zeros**, read as flux — in the template (and HARPS spectra) the deepest "line" of
  all. (1) `spectrum_io.read` now returns runs of >= 3 exact zeros as NaN (single zeros stay); the RV step drops a
  template's NaN (bridged: no lines); every other reader already filters NaN (checked: MK classify, telluric, Pickles
  classify, disentangle, atmosphere). (2) With the gap gone, the HARPS spectra collapsed onto v1 = v2: with one
  template for both stars C12 -> 1 beside the diagonal and 1 − C12² -> 0 made a false peak from rounding (the gap had
  hidden it). `sb2.todcor` now leaves out the band |s2 − s1| where the templates still overlap by half (C12 > 0.5) —
  two stars closer than that cannot be split anyway. Result: flux ratio FEROS 0.609–0.630 (median 0.623), HARPS
  0.607–0.608; velocities within 0.05 km/s of before. Tests `test_a_zero_filled_gap_is_missing_data_not_a_line`,
  `test_one_smooth_template_does_not_pull_both_stars_together` (guards; the false peak needs the real template's
  rounding to appear).
- P8 **DONE — one bug, one default changed.** MK type suggestion on HARPS 1-D spectra (ESO archive, ADP s1d, S/N
  ~400) of 23 bright stars with SIMBAD types (list and files: /tmp/claude-0/realdata/mkcheck/list.json; script
  /tmp/claude-0/work/mk_check.py, `run(degree)`): at first rms 2.0 subclasses, late-G/early-K dwarfs typed G0 V.
  (1) **Bug:** the first and last pixel of each libnor36 standard are cut by the rebinning (K0 V ends at 0.08, G5 V
  at 0.40, starts at 0.09–0.34): one such pixel against a real spectrum weighs as much as all the lines of the last
  100 A, and it penalised some standards (K0 V, G5 V, K0 IV) and not others. `mkstandards.load` now leaves out the
  first and last two covered pixels (test `test_the_rebinning_cut_at_the_ends_of_a_standard_is_left_out`).
  (2) **Default degree of the response polynomial 2 -> 4:** HARPS's uncalibrated response over 3800–5600 A is not a
  parabola. Degrees 2/4/6/8 after the fix: temperature rms 1.59/1.06/0.93/1.01 subclasses, within 2 subclasses
  78/91/96/96 %, luminosity class exact 74/78/70/74 %, within one class 96/100/96/96 %. 4 is chosen: 6 is slightly
  better in temperature but puts beta Vir F9 V among the giants. (My own selection error found on the way: the
  "alpha Cen B" file was alpha Cen A — a 36" cone around B catches A; refetched by target name HD128621.)
  Result with degree 4: Fomalhaut A4V -> A3 V; alf Hyi F0IV -> F0 V; Procyon F5IV-V -> F5 V; bet Hyi G0V -> F9 V;
  alf Cen A G2V -> G0 V; alf Cen B K1V -> K1 V; tau Cet G8V -> G8 V; eps Eri K2V -> K2 V; del Pav G8IV -> G5 V;
  18 Sco G2Va -> G0 V; 51 Peg G2IV -> G0 V; Arcturus K1.5III -> K2 III; alf Hya K3IIIa -> K3 III; eps Ind K5V -> K3 V;
  HD 10647 F9V -> F8 V; zet Dor F9V -> F8 V; gam Pav F9V Fe-1.4 -> F6 V (metal-poor: weak lines look earlier, as for
  a classifier); bet Vir F9V -> G0 V; iot Hor F8V -> F8 V; eta Boo G0IV -> F8 V; HD 20794 G6V -> G0 V; 61 Vir G6.5V
  -> G8 V; Achernar B6Vpe -> B2 V (Be star, fast rotator). Summary: median -0.5 subclass, rms 1.06, 78 % within one
  subclass, 91 % within two; luminosity exact 78 %, within one class 100 %. Guide 08 (4 languages) gives this.
- P9 **DONE — five bugs, all from real data.** Data (LCO public archive, archive-api.lco.global, anonymous, limit
  <= 100 per page): Landolt SA 98, elp 1 m fa16, 2024-12-12, request 3723427, B 0096 and V 0101 (1 s; note: request
  3737867 is indexed as SA98 by the archive but its frames are NGC 2240); TV Boo (RRc, VSX V 10.57–11.23, P 0.3125615
  d), 0.4 m kb27/kb81/kb82/kb88, 2020-06-21, 10 B + 10 V frames. Files in /tmp/claude-0/realdata/{landolt,tvboo};
  scripts /tmp/claude-0/work/p9_sa98.py, p9_esa.py, p9_tvboo.py.
  (1) `mirrors.cds`: Harvard's VizieR answers Gaia and APASS queries with **no rows**; once remembered (it answers
  SIMBAD-era queries fast) every catalogue lookup came back empty ("0 stars with B and V"). An empty VizieR answer now
  passes to the next server and is not remembered (an empty answer from all of them is returned as empty). Test
  `test_a_vizier_mirror_with_no_rows_is_passed_over`.
  (2) No VizieR at all: Gaia now comes from the ESA archive (`gaia.photometry`, VizieR's column names) in
  `catalog.vizier_fetch` and `coefficients.catalogue_magnitudes`; APASS-less stars still get V, R, I. Real: 297 stars
  of SA 98 in 3 s, V from Gaia vs APASS median 0.000, rms 0.075. Test `test_gaia_from_the_esa_archive_when_no_vizier_
  server_answers`.
  (3) `masters.load` crashed on LCO 0.4 m e91 frames: BANZAI trims them but leaves the raw frame's BIASSEC
  [3100:3135] and TRIMSEC [18:3071] in the header, outside the 3054-pixel frame. A section reaching outside the frame
  is now ignored (DATASEC is then used). Test in `test_section_overscan_and_trim`.
  (4) `catalog.calibrate` fitted a colour term from any three comparison stars spread over > 0.2 in colour: on TV Boo
  (V) four red comps (B−V 0.53–0.86) gave k = −0.40 from their catalogue scatter, and carried to the blue target
  (0.12) it made V = 11.55, below the star's minimum; check star 0.33 off. The term is now used only when its slope is
  more than 3 times its error. After: V 11.32 / 11.10 / 10.66, check star within 0.04–0.10 of APASS. Test
  `test_no_colour_term_from_scatter_over_a_narrow_colour_range`.
  (5) AAVSO report: MERR was the photon error only (0.003) while the comparison stars disagreed by 0.05; it now adds
  the scatter of the comps' zero points in each frame (as the page's own error). The ensemble magnitude also honours
  the page's ensemble weights (m_ens = −2.5 log Σ w 10^(−0.4 m)); before it assumed equal weights.
  Results. SA 98 transformation from APASS (59 stars): Tbv 0.944 +- 0.019, Tv +0.005 +- 0.016, Tb −0.033 +- 0.019;
  from Landolt (2009, J/AJ/137/4186, 31 stars): Tbv 0.969 +- 0.014, Tv −0.024 +- 0.012, Tb −0.037 +- 0.012. The APASS
  transformation applied to the 31 Landolt stars: V median −0.008, rms 0.032; B−V median −0.003, rms 0.054 (1 s
  exposures). TV Boo: page magnitudes and AAVSO report now agree within 0.02 (flux ensemble vs magnitude mean),
  MERR 0.03–0.07; V 10.66–11.33 over the night, B−V 0.03–0.17 (an RRc of type A7–F2). Guide 06 (4 languages).
- P10 **DONE — three bugs in TESS pixel-file photometry.** WASP-12 b, TESS sector 20 (MAST, astroquery
  Observations: tess2019357164649-s0020-0000000086396382-0165-s_tp.fits and _lc.fits, in /tmp/claude-0/realdata/wasp12;
  script /tmp/claude-0/work/p10_wasp12.py). One transit (±0.15 d around the middle one of the sector, epoch 10 from the
  sector's first) measured here from the TPF without comparison stars, fitted on the Models step (`models.eb_fit`,
  t0, r_sum, k, incl free, period from the sector, TESS quadratic limb darkening 0.32/0.22) and exported for
  ExoClock / ETD. Reference: the same transit in the SPOC PDCSAP light curve, and the ephemeris of all the sector's
  transits fitted from PDCSAP (P = 1.091413 +- 0.000015 d). NASA Exoplanet Archive now answers scripts with a
  Cloudflare challenge: not bypassed, not used.
  (1) Errors 3.3x too large (chi2r 0.09, Tc +- 221 s against SPOC's 44 s): in the 11 x 11 px stamp the sky ring's
  scatter (1957 e-) is the star's wings and a neighbour, while FLUX_ERR says 264 e- per pixel. `tpf.frames` now writes
  PIXNOISE (median FLUX_ERR x exposure) and `aperture.measure` uses it instead of the ring's scatter (frames are
  converted again once: listing frames2.txt). After: chi2r 1.75, Tc +- 66 s. Test
  `test_errors_of_a_small_stamp_come_from_the_archive_noise` (fails with the old errors: 3.4x).
  (2) Automatic radii for small stamps put the sky ring in the corners (5.5–7.3 px, where a neighbour sits): scatter
  0.0036; now a ring from 2 FWHM, 2 px wide (4.1–6.1 px): 0.0028 (best by hand 0.0026). Unchanged for the 21 x 21 px
  TESScut file (its ring fits).
  (3) The page's default rings (4 / 10 / 16 px) do not fit an 11 x 11 px frame: every flux was NaN, silently. The
  light curve now chooses the radii from the stars when the inner ring is beyond half the frame, and the page says so
  (translated). Same test.
  Result: Tc = 2458853.919719 +- 0.000768 BJD_TDB; SPOC same transit 2458853.919176 +- 0.000515: +47 s; sector
  ephemeris +42 +- 70 s. Depth 1.591 % (SPOC 1.579 %), k 0.1213 (0.1181), T14 3.17 h (3.02 h), i 76.9 (82.3; one
  transit of a noisier light curve: ingress shape poorly fixed). Files: <name>_ExoClock.txt (BJD_TDB, flux, error),
  _ETD.txt (BJD_TDB, magnitude, error), _summary.txt — formats as before. Guide 06 and 09 (4 languages).
- P11 **DONE — a missing lamp and three wavelength-solution bugs.** Raw long-slit frames of a simple, low-resolution
  spectrograph: Liverpool Telescope SPRAT (R ~ 350, 4.6 A/px, Xe arc), the raw set ASPIRED ships with its examples
  (`git clone --depth 1 https://github.com/cylammarco/ASPIRED-example`, example_LT_SPRAT/sprat_LHS6328_Hiltner102_raw:
  Hiltner 102 standard 60 s, LHS 6328 5 x 120 s, Xe arcs, dark, slit flat; 2.7 GB clone, in /tmp/claude-0/realdata/
  sprat). Reference: ASPIRED's own solution of the same arc (example_output/example_02_..._science_0.fits ext 4:
  quartic, pixel origin 50 px in). Amateur raw sets (Alpy, LHIRES, Star'Ex) are still nowhere public: ARAS / BAA only
  on request. Scripts /tmp/claude-0/work/p11_*.py.
  (1) No xenon line list: added `resources/linelists/xenon.dat`, 110 Xe I lines 3800–10000 A (air) from the NIST ASD
  (public domain; intensity >= 100 or Aki >= 4e5); specreduce-data's xenon list is infrared only. THIRD_PARTY updated.
  (2) `wavecal.find_lines` took its noise from the arc's scatter about the median: a low-resolution arc is blended
  lines end to end, so only 14 of the SPRAT lines passed (ASPIRED finds 70). Noise now from pixel-to-pixel
  differences, threshold on each line's prominence, and lines under 1/200 of the strongest left out (without that cut
  the real EFOSC2 He-Ar night found 34 peaks and its solution went from 0.21 to 2.4 A rms; with it 16 peaks, 13 lines,
  0.215 A as before). Test `test_arc_lines_on_a_blended_background_and_the_faintest_left_out`.
  (3) `wavecal.solve` grew the matching window from the span between the identified lines: with two lines 630 px
  apart the straight first guess was 30 A off in the middle and the lines there were misnamed. The window now grows
  around each identified line; another peak can no longer take an identified line's wavelength (269 and 280 px were
  both 4671 A).
  (4) The leave-one-out degree took a quintic through 11 lines on pixels 269–963 — -1435 A at pixel 0.
  `_best_degree(..., n_pixels)` (the reduce step passes the spectrum's length) refuses a degree whose curve turns
  back or whose A/px changes more than 3x over the detector. Test
  `test_low_resolution_xenon_arc_lines_cover_part_of_the_detector` (both new tests fail on the old code).
  Result, Hiltner 102 with two identified lines (279.74 px = 4671.23, 912.08 px = 7642.02): 23 lines, cubic, 1.46 A
  rms (0.3 px); against ASPIRED's solution +2.1..+7.4 A over the spectrum (median +3.4, under 1.5 px); night-sky
  zero point -1.38 A from [O I] 5577 and 6300. Features (centroid at 18 A resolution): H-alpha +5.1, Na D +4.8,
  H-beta +5.5, O2 B -0.1 A; the same measurement on ASPIRED's calibrated standard: +6.0, -4.2, +10.3, +9.1 — both at
  the 1-pixel level. Known limit: two identified lines both in the blue half (280 and 606 px) still fail (the user's
  lines can be clipped as outliers); identify lines across the range, as the guide says. Guide 08 (4 languages).
  Side effects checked on real data: EFOSC2 (9 PESSTO lines) 13 lines, 0.215 A, degree 4 as before; raw HARPS
  echelle (9 ThAr lines from ESO's e2ds polynomials in orders 153/138/123) 1484 lines, 0.00034 A, ours - ESO
  median +0.2 m/s, rms 22.2 m/s (was 0.0 / 21.6; script p11_harps.py).
- P12 **IN PROGRESS — stopped here by the owner (quota), next agent continues.** Disentangling on a real SB2 series
  over the whole orbit. Target chosen: **TZ For** (G8 III + F7 III, P = 75.66647 d, circular; Gallenne et al. 2016,
  A&A 586, A35 = arXiv:1511.07971: K1 = 38.90 +- 0.01, K2 = 40.87 +- 0.02 km/s, gamma1 17.99, gamma2 18.35; Table 1
  gives the HARPS velocities of both stars per epoch — barycentric, MJD). Data: the same 22 HARPS ADP s1d spectra
  (ESO TAP ivoa.ObsCore target_name LIKE '%TZ%For%', downloaded via dataportal.eso.org/dataPortal/file/<dp_id>) in
  /tmp/claude-0/realdata/tzfor (list.json: dp, mjd, snr, path); the paper's text in /tmp/claude-0/work/tzfor.txt
  (pdftotext); scripts /tmp/claude-0/work/p12_*.py (p12_rv.py, p12_tpl.py, p12_pairs.py; p12_trv.json = template
  velocities). Other candidates with many ESO spectra: LL Aqr (21 HARPS + 15 FEROS), AL Dor (18 + 12), AL Ari (22 +
  22), V4089 Sgr (23 + 11), HD 172189 (196 FEROS), zet Phe (34 FEROS).
  **Found and fixed (uncommitted work committed with this note):** velocities were measured against the template
  but a real star used as template is not at rest — with tau Ceti (-16.53 km/s) every TZ For velocity came out
  +15.2 km/s off. `spectroscopy.rv` now takes `template_rv` and `template2_rv` (km/s, added to the measured
  velocities; the 2nd defaults to the 1st; for the broadening function's 2nd star the first template's); Velocity tab
  has "Template's own velocity (km/s)" and "Second template's velocity (km/s)" (tooltips, tr/de/es translated); test
  in `tests/test_sb2.py::test_rv_and_orbit_steps_in_sb2_mode`. Template velocities measured with the program against
  tau Ceti (-16.532, ESO CCF): iot Hor +16.993, Arcturus -5.194, Procyon -2.667, zet Dor -0.997, HD 10647 +27.783,
  alf Hya -4.490, del Pav -21.451 km/s (literature-like).
  **Open, next steps:**
  1. TODCOR on TZ For with templates (tau Cet, iot Hor): which template goes with which star is not what one expects
     (iot Hor F8V followed the giant, L2/L1 0.115) and the secondary came out about +-5-6 km/s off Gallenne, always
     pushed AWAY from the primary (separation overestimated). With one template for both (tau Cet + tau Cet) the
     secondary locked 6.8 km/s from the primary (just outside the blend band `sb2.todcor` leaves out: false peak
     again — see P7). Run p12_pairs.py (args: template1 template2 sub|all) for the pairs Arcturus|Procyon,
     del Pav|Procyon, tau Cet|iot Hor, iot Hor|tau Cet (it was running when stopped; each takes ~2-5 min); compare
     primary/secondary with Gallenne (rms), and the light ratio. If the secondary is still pushed away, look at
     `sb2.todcor` (blend band width, the alpha / light-ratio fit, the 4500-6500 A window) and also try the broadening
     function (method bf, components 2: Gallenne used BF in RaveSpan).
  2. Fit the orbit (`spectroscopy.orbit`, period 75.66647 fixed or free) from our velocities: K1, K2, gamma against
     Gallenne's.
  3. Disentangle (`spectroscopy.disentangle`, our velocities, light ratio from TODCOR/BF) and check the components:
     MK type of each (should be G8 III and F7 III / F-type), `separable_width` (the separation changes by ~160 km/s
     over the orbit, so Balmer wings should be determined), cross-correlation of each component with a template.
  4. Then P13 (every other feature once more on fresh real data, full local test run, push, CI, release v0.2.3 by
     hand: raise __version__, push, run ci.yml with release=true).
  **State at hand-over (session 01RxUU, 2026-11-06):** full local suite after P12's commit: 661 passed, 3 skipped,
  0 failed (8 min). Main is clean, nothing uncommitted. CI not run for these last commits (no release made).
  **For the next agent — start here:** read this P-list from P8 on (P8–P11 DONE with data, scripts and results;
  P12 IN PROGRESS above). Real data and scripts live only in /tmp/claude-0 (realdata/, work/) of the old container:
  in a new container they are gone — re-download with the recipes written in each P entry (ESO TAP + dataportal,
  LCO archive-api (anonymous, limit <= 100 per page), MAST via astroquery Observations, ASPIRED-example git clone,
  NIST ASD lines1.pl CSV, Gallenne 2016 = arXiv:1511.07971 PDF -> pdftotext). Rules unchanged: commits as İdris
  Avlar (git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com"), no co-author trailers, push to main,
  owner data and downloads never committed, every UI text in self.tr and translated tr/de/es (tools/i18n.py update,
  tools/fill_translations.py, tools/i18n.py), guide in 4 languages with the same sections, tools/check_brand.py,
  ruff check + format, `set -o pipefail` when piping pytest, report to the owner in Turkish.
- P3 (detail) Plate solution refined against Gaia DR3 when online (TAN-SIP refit, ~0.1–0.2"); astCat then Gaia3. Gaia also
  straight from the ESA Gaia archive when VizieR does not answer.
- P4 Period page: error bars (the measurement errors carried there).
- P5 Echelle step: zero point from the night-sky lines (as long-slit).
- P6 HARPS: drift between the evening's two ThAr frames.
- P7 TODCOR light ratio FEROS 0.33 vs HARPS 0.66 for the same stars: find why.
- P8 MK type suggestion: validate against many stars of published type (archive spectra), report the scatter.
- P9 Standard magnitudes and the AAVSO report on real data (catalogue magnitudes via Gaia archive / VizieR CfA).
- P10 ExoClock / ETD export from the Models page with a light curve we measure (TESS transit).
- P11 Raw long-slit frames of a small spectrograph (search public archives again).
- P12 Disentangling on a real SB2 series that covers the whole orbit (ESO archive).
- P13 Then every other feature once more on freshly downloaded real data; release.

**Owner's feedback of 2026-11-06 (~09:00 UTC), after trying v0.2.0 — the plan, in this order (claim each before
starting, mark DONE with results):**
- O1 **DONE** SIMBAD: a slow mirror is left after 15 s for the next (`mirrors._within`, `patience`); SIMBAD now has
  four addresses (CDS, Harvard, CfA Harvard, the old Strasbourg name). Measured here: CDS did not answer in 15 s,
  Harvard in 0.7 s; 'AI Phe' resolved in 16.8 s on the first try, then Harvard is remembered and asked first.
  Test `test_a_slow_cds_server_is_left_for_the_next`.
- O2 **DONE** Photometry page layout: the light-curve band across the page hid the controls (buttons only found by
  scrolling). Now: controls the whole height on the right (all visible at 1366 x 768, checked on screenshots in
  English and Turkish); on the left the image alone until a star is marked, then the image above the star table /
  light curve (3:2, draggable); the result tabs scroll vertically instead of taking height (never cut sideways).
- O4 **DONE** Aperture rings: they were already drawn in image pixels, but while smaller than 9 screen pixels a
  fixed-size ring replaced them (meant to show which star is marked) — at the usual zoom the owner saw only that
  ring and took it for the aperture ("same area when I zoom"). Now a fixed-size cross (not a ring) and only below
  4 screen pixels; the radii are labelled "Ring 1 — the star's light inside / Ring 2 — the sky starts / Ring 3 —
  the sky ends" with a note (1–2 not measured, 2–3 sky, rings grow with zoom); Shift + wheel on the image changes
  all three by 0.5 px. Guide 06 (4 languages). Tests: `test_marked_stars_stay_visible_on_a_zoomed_out_frame`
  (cross, rings scale with zoom), `test_photometry_star_picking` (lower panel hidden until a star, Shift + wheel).
- O3 **DONE** Photometry: every frame can be seen — arrows and a slider under the image count, the frame's name and
  UTC; stars are marked on any frame (that frame becomes the reference: `PhotometryPage.ref`, kept in undo), drawn
  on that frame only, marking on another frame is refused with the reason; "Use this frame" leaves a frame out.
  The page sends the reference frame first (`_series`); `photometry.light_curve` has an optional input
  `ref_image` and `lightcurve.light_curve(..., ref_path=)` re-centres there and carries the positions to the first
  frame in time by `frame_shift`; apertures / suggestion / polarimetry steps take the first frame given (the
  reference) instead of re-sorting. Test `test_stars_marked_on_a_later_frame_are_carried_to_the_others` (frames
  drifting 7 px: marking on frame 4 gives the same fluxes as on frame 1 to 1e-6). Guide 06 (4 languages).
- O5 **DONE** The Plot tab had seven views but not the classic one. New first (default) view "Differential":
  target − comparison (Δm) below, the check star − comparison above it (or C1 − C2 without a check star), with its
  scatter in mmag in the legend, magnitude axis inverted (`PhotometryPage._plot_differential`).
- O6 **DONE** Under the result: a note that photometry only measures and where the fits are, and two buttons:
  "Period search and O−C →" (that page already gets the curve) and "Fit an eclipse or transit model →" (saves the
  CSV where the user says, next to the frames by default, and opens it on Orbits & models; `next_requested`,
  `MainWindow._photometry_next`). PSF photometry already has a tooltip (crowded fields). Test
  `test_differential_view_first_and_the_way_on_to_the_fits`. Guide 06 (4 languages).
- O7 **DONE** Calibrate page: a note under the table says how the type is found (header IMAGETYP / FRAME /
  OBSTYPE…, then words in the file name, 0 s = bias; anything else "unknown" and left out — NOT taken as a light,
  answering the owner's question); double-click a type to change it (a list; `CalibratePage._edit_kind`; the run
  uses the page's frame list, the files are not changed). The stack button now reads "Or: stack them into one deep
  picture (not for a light curve)" with a tooltip saying why (a stack has one time). Guide 04 (4 languages).
- O8 **DONE** "4. Measure them on the Photometry page →" after calibration (`photometry_requested` →
  `MainWindow.send_to_photometry`: several filters → the user picks one; the largest first). The Images page's
  right-click menu starts with "Send the open images to Photometry" (no star to choose). Tests in
  `test_calibrate_page_scan_and_run` and the image-menu test.
- O9 **DONE** Plan page. (a) "Open in a new window" did nothing: `PlotCanvas.open_window` copies the figure by
  pickle, and the Plan chart's axis formatters / secondary axes are functions that cannot be pickled, so it
  returned None silently. Now such a figure opens as a picture drawn at 3x resolution (zoomable with the toolbar)
  — any page's chart. (b) "The chart starts at 20°": the axis was 0–90° already; on a short window (1100 x 600,
  or a laptop with 125 % scaling) the whole page (min. height 522 px) scrolled and the chart's lower part was out of
  sight. The fields now scroll on their own (page min. height 221 px), the chart keeps the window's height. Test in
  `test_plan_page_resolve_and_plan`. Still taller than a 459 px page area (they scroll as a whole): Observe 610,
  Calibrate 523, Light curves 486, Spectroscopy 683 — same treatment next if the owner meets it (O12).
- O10 **DONE** "Check frame quality" is now "Find the bad frames (clouds, focus, trails)" with a tooltip saying it is
  optional, what it measures and that nothing is removed by itself; guide 01 / 06 use the new name (4 languages).
- O11 **DONE (after the v0.2.1 build started; in the next release)** Spectroscopy page: "In what order? (click)"
  above the tabs opens the order of work — 1 raw frames: Reduce or Echelle (calibrate first); 2 archive spectra
  start at 3; 3 Telluric (optional); 4 Radial velocity and orbit; 5 Spectrum tools — with the tab names as the
  translations show them. Test in `test_spectroscopy_instrument_profiles`.
- O12 **DONE** Every page fits a 1100 x 600 window (test `test_every_page_fits_a_short_window`): in every splitter a
  block of fields taller than 200 px scrolls on its own (`main_window._fields_scroll`, applied when a page is built;
  proportions kept with saveState/restoreState); Calibrate is two columns (1. frames | 2.–4. steps). Was: Observe
  610, Calibrate 523, Light curves 486, Spectroscopy 683 px in a 459 px area. Old note:
- O12 (old) Pages still taller than a short window's page area (1100 x 600 → 459 px): Observe 610, Calibrate 523 (fits a
  1366 x 768 window), Light curves 486, Spectroscopy 683 — give them the Plan / Photometry treatment (fields in
  their own scroll area, plots in splitters) if the owner meets it. Measuring script: show every workspace in a
  1100 x 600 window and print `page.minimumSizeHint().height()` against the scroll area's viewport height.
- Release v0.2.1: **DONE** (12:06 UTC). Run 107 failed on Windows only: `test_deleting_points_and_curve_spacing`
  clicked 2 px from a point and the new default (differential) view put a neighbour nearer; the test now clicks on
  the point (de6377f). Run 108 green, release published with the installers.
- O13 **DONE** (owner, after v0.2.1): frames named after the star (his NY Vir data: nsvs***.fits, no IMAGETYP) were
  "unknown, ignored". (a) `frames.classify`: a frame that states no type and has no type word in its name is a
  light; only a type the header states that we do not know (FOCUS, TEST…) stays unknown. (b) His better idea, done:
  the Calibrate page has two folders, **Lights** (data) and **BDF** — every frame in the light folder is a light
  whatever its name (a header stating bias / dark / flat / arc still wins); the BDF folder is sorted as before; one
  mixed folder still works (give it as BDF). `calibration.scan` has an optional input `lights`; the output folder
  defaults to <lights>/calibrated. Tests `test_a_light_folder_and_a_bdf_folder`, `test_classify_fallbacks`, the
  Calibrate page test. Guide 04 (4 languages).
- Release v0.2.2: **DONE** (run 111 green, published 12:38 UTC; local check 644 passed).
- O14 **PROPOSED, waiting for the owner's yes** (he asked whether the Photometry page still shows one picture or works
  like MaxIm DL): now one frame at a time with arrows / slider / "Use this frame". Proposed: a MaxIm-like list of all
  frames beside the image (name, time, FWHM, sky, a "use" box; click a row to show it; bad frames from "Find the bad
  frames" marked red) and a "blink" button that plays the frames in turn.

**Second update by agent session 01RxUU (2026-11-06, ~07:30 UTC).** The owner asked (in Turkish): (1) a release now
to try the program; (2) are Lomb–Scargle / BLS / PDM / ANOVA explained in the guide, and do buttons / boxes have hover
explanations; (3) do all fits follow real mathematical models (not made up) — document their mathematics; (4) do the
open items; (5) then another release.
- (1) **DONE.** Version 0.2.0 (`e95a636`). Tag pushes from the agent container are cut off by its proxy, so the `ci`
  workflow got a `release` input (`9147928`): run `ci` by hand on `main` with release = true (GitHub MCP
  `actions_run_trigger`, method run_workflow, workflow_id ci.yml, ref main, inputs {"release": true}); the release
  job creates tag v<version> at that commit and uploads the installers. Run 97 published v0.2.0 (the repository's Releases page, 07:47 UTC, all jobs green). Do not push to
  `main` while such a run is going: the push cancels it (same concurrency group).
- (2) **DONE.** The guide had one line per method; now each says how it works (07-lightcurves, 4 languages) and each
  item of the method list has its own tooltip with the paper (Lomb 1976 / Scargle 1982, Kovács et al. 2002,
  Stellingwerf 1978, Schwarzenberg-Czerny 1996). Every control already has a tooltip (`tests/test_tooltips.py`).
- (3) **DONE.** New guide chapter `13-methods.md` "Mathematics of the methods" (en/tr/de/es, 11 sections): least
  squares / errors / MCMC, the four period searches, Fourier + prewhitening + CLEAN, KvW / polynomial / trapezoid
  minima, ephemeris + dP/dt, LTTE and apsidal motion, the EB sphere model, CCF / TODCOR / BF / Keplerian orbits /
  absolute dimensions, visual orbits, wavelength / atmosphere / telluric / disentangling, aperture photometry /
  extinction / transformation. Every formula was checked against the code (module docstrings and functions), not
  written from memory; corrections made on the way: CLEAN gain is 0.2, third light is a fraction of the total,
  `oc_models` cited Irwin 1952 as AJ 57, 211 — it is ApJ 116, 211 (fixed). Result: every fit is a published model.
- (4a) **DONE — disentangling on real data, with the cause found.** Synthetic AI Phe built from PHOENIX K (5000/4.5)
  and F (6000/4.0) spectra at R 48000, the real ESO epochs and Gallenne's orbit, light ratio 0.32, S/N 70, with and
  without spikes and continuum waves (the construction is all in this paragraph). Findings: (i) even without noise the F
  component is off by 0.04 rms, almost all of it in broad features (≥ 9 A): the velocity separation v1 − v2 changes
  by only 58 km/s across these spectra (≈ 1 A), so broader features (Balmer wings) are not set by the data. The true
  F spectrum is typed F9 III / G0 V by the MK standards, the disentangled one B1 Ia — exactly the real result. With
  ten epochs over the whole orbit (separation changes by 199 km/s) both types come out right (K2 V, F8 III / G0 V).
  (ii) An exact sparse least-squares solution (LSQR, Simon & Sturm 1994 style) does not help: with AI Phe's
  coverage it amplifies noise in those undetermined modes (F rms 0.098 vs 0.044); the iteration's early stop acts as
  regularisation. (iii) A median combination drifts with more iterations (0.033 at 40 → 0.146 at 400): rejected.
  (iv) Spikes did leak: F rms 0.052 / max error 0.82 with spikes against 0.044 / 0.37 without.
  **Changed** (`spectroscopy/disentangle.py`): every 10 iterations pixels more than 5 robust sigma above the model are
  masked (bright spikes only; a line core the model misses is not masked), each mean is over the spectra that see
  the pixel (the plain mean where the mask would leave none), NaN are ignored; result with spikes = result without.
  New `separable_width(v1, v2)`; the step returns `separable_kms` / `separable_a` and the Velocity tab says which
  feature widths the series separates and not to read broader ones (or a type resting on them), translated.
  Test `test_spikes_and_gaps_stay_out_of_the_components` (fails without the change).
  Real AI Phe again (10 spectra, TODCOR with tau Ceti for both, 4500–6500 A): separable 57.9 km/s = 0.99 A; K star
  F8 III / G0 V (score 0.08), F star B1 Ia — as the synthetic test predicts for this coverage. FEROS alone (7):
  same; HARPS alone (3): 12 km/s. Also seen: TODCOR's light ratio is 0.33 on FEROS and 0.66 on HARPS for the same
  stars (template = HARPS tau Ceti for both; resolution or normalisation difference) — not investigated; a mixed
  series breaks the constant-light-ratio assumption of disentangling. Conclusion for the owner: the code is right,
  these archive data cannot give the components' types; a series over the whole orbit can.
- (4b) **DONE — drizzle on real frames: two bugs found and fixed.** Data: the three LCO 0.4 m BANZAI frames of the
  433 Eros field already used for astrometry (cpt0m439-sq39-20260808-0080/0081/0082-e91, archive-api.lco.global).
  Their offsets are real non-integer shifts (5.48 / 1.62 and 9.47 / 2.66 px). The drizzled image's WCS agrees with
  the stack's within 0.05 drizzled px (0.02 arcsec) over 40 stars. (i) **Flux:** aperture sums on the drizzled image
  were 4.011 x the stack's — the output was surface brightness, without Fruchter & Hook's s^2 factor (eq. 3; also
  drizzlepac), so photometry with the gain on a drizzled frame was wrong; now counts are kept: 1.0027 +- 0.006. The
  guide already said "the flux is kept". The synthetic test had codified the old behaviour; changed. (ii) **SIP:**
  `scaled_header` scaled CD / CRPIX but not the SIP distortion terms our plate solver writes; A_p_q, B_p_q, AP, BP now
  scale as scale^(1-p-q) (test `test_scaled_header_keeps_the_distortion`, fails without). Not checked: frames with a
  rotation between them (drizzle, like stacking, aligns by translation only — documented shortcut).
- (4c) **DONE — offline plate solving on a real frame; one reporting bug fixed.** astrometry.net 0.93 from Ubuntu
  (`apt-get install astrometry.net astrometry-data-tycho2-07-littleendian astrometry-data-tycho2-08-littleendian`) +
  `index-4205-06.fits` / `index-4206-06.fits` from data.astrometry.net/4200/ (2MASS, healpix 6 = RA 135–225,
  |Dec| < 41.8; `get-healpix -N 1 -- ra dec` names the tile) copied to /usr/share/astrometry. Frame: the LCO Eros
  frame 0080 with its WCS removed (2400 x 2400, 0.74"/px, 29.6'). With the Tycho-2 indexes only (quads 22–42', too
  large for a 30' field): no solution (hint) / timeout (blind, 300 s). With 4205/4206: blind 7 s, with hint 4 s, SIP
  written. Against Gaia DR3 (64 stars G < 15, VizieR): ours median 0.60" (rms 0.80), BANZAI's own WCS 0.43" (0.76);
  the two WCS differ by 0.45" median, 1.3" at the corners — 2MASS (epoch ~2000) limits ours. **Bug fixed:** the MPC
  report always wrote astCat = Gaia3 (the dialog's default, its tooltip said "ASTAP and astrometry.net: Gaia"), but
  an astrometry.net solution rests on the index's catalogue. Now `astrometry.solve` reads "index id: NNNN" from the
  solution and writes ASTCAT (4100 Tyc2, 4200 2MASS, 5000/5200 Gaia2; ASTAP: not set, its databases are Gaia-based
  but the release is not recorded); `moving.track` carries it and the dialog fills the Catalogue field and says so
  (or warns when frames disagree). Guide (05-images, 4 languages): which index files a field needs, and the
  catalogue field. Tests in `test_astrometry.py` / `test_moving.py`. Possible next step (not done): refit the WCS
  against Gaia DR3 when online (astropy `fit_wcs_from_points`) to reach ~0.1" and report Gaia3 honestly.
- (5) Next: full local check, push, CI green, then release v0.2.1 by the manual `release` run.

**Update by agent session 01RxUU (2026-11-06, after 019Lu3).** Continued "Still to do" below in order; each item
there now says DONE / IN PROGRESS with its results. Commits: `e2a8d69` (brand check), `95714a4` (CHECKSUM fix,
side-effect checks), `c5985a4` (echelle 10x faster, .Z 5x), `70a42b0` (TODCOR star swap with one template),
`e298843` (BF one-star crash), `6cf535a` (telluric plot), `1805e02`, `bd18410`, `0a1d9f6` (handoff). CI: all test jobs
green at `70a42b0`; check the later runs. Open: disentangling on real data (item 4), drizzle and offline plate
solving on real frames (item 4, not possible in the agent container), item 6 (the plain-Turkish explanation for the
owner, in the chat), U11 and a release (ask the owner). Data used are listed under each item with their archive ids.

Agent session 019Lu3 stopped on **2026-11-06 (~06:00 UTC)** because the owner's weekly quota ran out. The owner hands
the work to the next agent with this file. State at that moment:

### Repository state
- `main` = `339bb16`, pushed. Everything on it passed `tools/precommit.sh` locally (634 passed, 3 skipped, ~8–9 min).
  Commits of this session, newest first: `339bb16` Plan chart in English with local time + echelle velocities,
  `3748b5a` raw HARPS echelle fixes, `41f4dfb` `show_minimum` CI fix + Project / Guide checked, `aa311ae`, `f3f2d17`,
  `9b6ba9d`, `1ed1bcd`, `6303702`, `5de120e`, `75ca8ab`, `a2b0113`, `1f9fa16`, `97b70ab`, `f8d523a`, `44948e5`.
- **CI:** green up to `9b6ba9d` (run 81). Runs for `aa311ae`, `41f4dfb`, `3748b5a`, `339bb16` were NOT checked yet —
  check them first (GitHub MCP `actions_list`, method `list_workflow_runs`, owner and repo of this repository; on a red
  run `get_job_logs` with `failed_only`). Run 80 (`1ed1bcd`) was red from an intermittent `IndexError` in
  `ui/workspaces.py show_minimum` (marker drawn on a figure with no axes); fixed in `41f4dfb` (guard + test).
  Cancelled runs are normal: a newer push cancels the older run.
- No release was made (a release only after asking the owner).
- Uncommitted work: none. No wip branches.

### The owner's standing rules (do not break them)
- **Commits in the owner's name only:** `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`.
  No `Co-Authored-By`, no `Claude-Session` trailer, the word "Claude" nowhere in a commit. Push straight to `main`.
- **Talk to the owner in Turkish** (every reply and every line of narration). Code, comments, commits and this file
  in English.
- **Push right after each finished piece** (owner, 2026-11-06: "Direkt push at her an kota dolabilir"): run the
  tests the change touches (+ `ruff check src tests` and `ruff format --check src tests`), push, let CI run the
  full suite, then check CI.
- The product name appears only in `brand.toml`, `README.md` and `packaging/install.sh`. Never commit owner data or
  downloaded data. Never touch the owner's GitHub token. Releases only after asking.
- i18n: every new UI text in `self.tr(...)`; then `python tools/i18n.py update`, fill the translations (tr, de, es)
  with `tools/fill_translations.py <ts file> "en=>translation" ...`, and `python tools/i18n.py` must say
  "0 unfinished" for all three. Engine error messages need a template in `src/astrowb/ui/messages.py`. The guide
  (`src/astrowb/resources/guide/{en,tr,de,es}`) is updated in all four languages when a feature changes.
- The owner's last explicit asks this campaign: see "The owner's request" above (fifth campaign), plus 2026-11-06:
  **the Plan chart must be in English** (done) **with UTC and local time** (done: top axis + box, see the U8b /
  Plan note in the task board notes); and at the very end **a detailed explanation in plain Turkish** of what was
  done and what the methods are (see "Still to do" item 6).

### Environment of the agent container (only matters if the next agent runs in a similar container)
- Venv: `<checkout>/.venv` (`export PATH=<checkout>/.venv/bin:$PATH`); GUI tests with
  `QT_QPA_PLATFORM=offscreen`. Engine `@step` functions run in spawn worker processes: driver scripts need
  `if __name__ == "__main__":` and must be files. To run a step directly in one process:
  `import astrowb.spectroscopy.steps; from astrowb.engine.steps import execute; execute(step_id, inputs, params, ctx)`
  with a ctx object having `progress(f, msg)`, `check()`, `cancelled`.
- Network from the container: CDS Strasbourg is blocked (the app falls back to the IDIA / Harvard mirrors by
  itself); MAST, ESO TAP (`https://archive.eso.org/tap_obs/sync`), ESO raw/ADP downloads
  (`https://dataportal.eso.org/dataportal_new/file/<dp_id>`), LCO archive API, Earth Search STAC, arXiv and GSU WDS
  (plain http) answer; aavso.org and GitHub releases give 403. IRAF 2.17.1 is installed from Ubuntu (needs
  `USER=root`, `mkiraf`, short paths, plain FITS). The scratch data and driver scripts of this session lived in the
  container's scratchpad (`data/`, `real/*.py`) and are gone with it; everything needed to redo them is in the notes
  (sources, dp_ids, numbers).

### What this session did (fifth campaign), in short — details in the task-board notes below
- U1 Roche-lobe (contact binary) warning; U2/U3 Plan page explanations, several targets + planets + Moon in one chart;
  U4 O−C MCMC as a background task, tried on KIC 6525196 (P3 418.3 d); U5 CDS mirror fallback, AAVSO report and
  standard magnitudes on a real LCO night.
- U6 every page used on real data in four languages (0 missing tooltips, 0 untranslated texts, 0 exceptions):
  Plan, Observe (INDI simulators), Calibrate, Images (all 16 process operations), Photometry, Light curves & O−C,
  Spectroscopy, Orbits & models (incl. eta CrB visual orbit vs ORB6), Remote sensing (Sentinel-2), Automation,
  Project, Guide.
- U8 raw vs published: LCO raw vs BANZAI (0.92 ADU / 0.021 %), IRAF ccdred + apphot (0.012 % / 0.063 %), TESS
  pixels vs SPOC SAP (0.020 %), times of minimum vs published, EFOSC2 vs PESSTO, **raw HARPS vs ESO DRS** (22 m/s
  rms in wavelength, ~10 m/s in velocity).
- U9 speed: PDM/BLS 280 s -> 2.6 s / >300 s -> 0.8 s, light curves 35 -> 14 s, calibration 110 -> 18 s, remote
  sensing out-of-memory -> seconds, RL deconvolution 19 -> 7 s, histogram matching 7.8 -> 2.9 s (speed log).
- 2026-11-06, last pieces: ESO prescan/overscan, primary-header inheritance for multi-extension frames, HARPS frame
  types per fibre, echelle order finding (fibre-B ghosts), extraction width from the orders' FWHM, piecewise
  continuum normalisation for long spectra, Plan chart English + local time axis + "Local time (hours from UTC)" box.

### Older to-do list of the fifth campaign (every item done or moved into campaign R; kept for its details)
1. **Check CI** for `aa311ae` … `339bb16`; fix anything red (reproduce locally first, then push).
   Watch especially: `tests/test_calibration.py::test_harps_raw_frames_two_fibres_prescan_and_primary_header`,
   `tests/test_echelle.py` (two new tests), `tests/test_spectroscopy.py::test_a_merged_echelle_spectrum_is_normalised_in_pieces`,
   `tests/test_ui.py::test_plan_page_resolve_and_plan` (uses a fixed UTC offset 3; Auto depends on the machine's
   time zone, the test only checks the range).
2. **DONE (session 01RxUU, 2026-11-06)** — results: EFOSC2 raw night re-downloaded (ESO TAP `dbo.raw`,
   `exp_start > '2018-12-31' AND exp_start < '2019-01-02'`; files biases 2018-12-31T19:21:38.992 … 19:23:41.429, arc
   2019-01-01T08:35:33.795, LTT 3864 07:49:08.109, SN 2018kzr 04:06:59.255, PESSTO ADP.2021-03-23T16:54:29.889).
   Frames now 1024 x 1024 after the prescan; the 16 arc peaks are at exactly the same pixels as before (the 6
   prescan columns are on the spatial axis, EFOSC2 disperses along y), so the wavelengths are unchanged: LTT 3864
   13 lines, rms 0.209 A, degree 4; SN 2018kzr 14 lines, rms 0.211 A, sky zero point -7.06 A (3 [O I] lines; was
   -7.14). The spatial positions moved by 6 as expected: SN 2018kzr's trace centre is now row 541.7 (PESSTO's 449.4
   + 99 - 6), not 548 (the step still finds it from 548). Against PESSTO's reduction: feature correlation 0.78 with a
   simpler normalisation than the earlier 0.84 (81-pixel running median on a 2.5 A grid), best shift 1.4 A.
   MEF headers: an LCO `.fits.fz` and an HST-like MEF read without duplicated keywords; **found and fixed:**
   `io/fits.inherited` also copied CHECKSUM / DATASUM (from the primary, and kept the HDU's own), so every image
   saved from a read header failed astropy's checksum verification; they are dropped now (test
   `test_a_copied_header_drops_the_checksums`). Echelle: the real TOFES master flat still gives 46 of 46 orders.
   Original task text: **Check the side effects of `3748b5a`** that were reasoned about but not measured on real data again:
   - ESO frames are now overscan/prescan-subtracted and trimmed from `ESO DET OUT1 PRSCX/OVSCX/PRSCY/OVSCY/NX/NY`
     when these add up to the frame (`calibration/masters.py _eso_sections`). EFOSC2 frames become 1024 x 1024
     (6 prescan columns removed): x pixel positions shift by 6 against before. Re-run the EFOSC2 long-slit reduction
     (raw PESSTO night, notes U6h / U8e) once and confirm the wavelength solution (0.21 A rms, 13 lines) and the
     PESSTO comparison still hold.
   - `io/fits.inherited()` now copies the primary header's cards into the image header for every multi-extension
     file (read_image, masters.load, read_frame, extract_extension). Check one HST/JWST-style MEF and one fpack
     `.fits.fz` (LCO) open, save and process as before (header size, no duplicated keywords).
   - `echelle.find_orders` drops a peak a tenth of its neighbour or fainter; check the synthetic TOFES-like data /
     any real slit echelle still finds all orders (tests pass).
3. **DONE for the red chip (session 01RxUU, 2026-11-06):** the raw .fits.Z frames opened as a user would (Images
   page: `fits_copy`, then `extract_extension` of image HDU 2 -> `<name>_CCD-44_2.fits` in fits_from_raw); Echelle
   step, orientation y, reverse, no sky, first order 114 decreasing: 26 orders found (ESO's e2ds_A rows 46–71: 26),
   ~100 ThAr peaks per order, 3.5 s. Nine lines identified in orders 110, 102, 94 (wavelengths read from ESO's e2ds
   polynomial at our pixels, as a user identifies lines; e2ds_A from ADP.2014-09-24T09:42:58.973, same pixel
   direction as ours): 770 lines, rms 0.0005 A; our wavelengths minus ESO's over all 26 x 4096 pixels: median
   0.2 m/s, rms 15.1 m/s (blue chip: 21.6 m/s). Not done: the drift between the evening's two ThAr frames.
   Original text: **U8b leftovers (optional):** the HARPS red chip (extension 2; same procedure, absolute orders 114 … 89 in ESO's
   e2ds rows 46–71); the two raw ThAr arcs of the evening could be compared with each other (drift). The tau Ceti
   files: science HARPS.2010-08-27T05:33:35.086, flat HARPS.2010-08-26T21:53:56.126 (LAMP,DARK,TUN), bias
   HARPS.2010-08-26T21:53:03.653, ThAr HARPS.2010-08-26T21:59:48.245; ESO products ADP.2014-09-24T09:43:29.897
   (s1d, Phase 3) and ADP.2014-09-24T09:42:58.973 (tar: e2ds_A/B, s1d_A/B, ccf_G2_A, bis). Our settings: orientation
   y, reverse on, sky off, first order 161, order step -1; 9 guesses (3 lines in orders 153, 138, 123) from the
   thar list. ESO's e2ds wavelengths: `HIERARCH ESO DRS CAL TH COEFF LL{4*o+i}` (degree 3, pixel 0-based).
4. **IN PROGRESS (session 01RxUU, 2026-11-06).** Done so far:
   - **SB2 / TODCOR on a real double-lined binary — found and fixed a real bug.** AI Phe (F7 V + K0 IV, P 24.59 d),
     ESO archive Phase 3 spectra (TAP `ivoa.ObsCore`, `target_name IN ('AI Phe','AI-Phe')`): 7 FEROS
     ADP.2016-09-27T11:56:48.124/.254/.546/.622, 11:56:49.113/.549/.655 (2014 Sep) + 3 HARPS ADP.2017-06-11T01:04:35.219,
     2017-06-12T01:03:34.222, 2017-06-14T07:30:18.279; template the HARPS s1d of tau Ceti ADP.2014-09-24T09:43:29.897 for
     both stars, 4500–6500 A. Literature: Gallenne et al. 2019 (arXiv 1910.03393, Table 2: P 24.59215, Tp 2453248.603,
     e 0.1872, ω 110.36, K1 51.166, K2 49.118, γ −2.111 km/s), Maxted et al. 2020 (arXiv 2003.09295: K1 51.164, K2
     49.106; star 1 = the F star, star 2 the more massive K star). Found: with one template for both stars the TODCOR
     surface is symmetric — (v1, v2, α) and (v2, v1, 1/α) fit equally — and noise chose, so the two stars swapped in
     3 of 10 spectra; the Wilson mass ratio came out 0.99 (neither 1.042 nor 0.960). Fixed in `sb2.todcor`: with
     identical templates star 1 is the one that gives more light (α ≤ 1), constant along the orbit (test
     `test_one_template_for_both_stars_keeps_the_brighter_as_component_one`, fails without the fix). Now: star 1 = the
     brighter K star in all 10; Wilson diagram with one γ per epoch (the third body moves γ between 2014 and 2017):
     K_K/K_F = 0.9625 ± 0.0049 against 49.118/51.166 = 0.9600; rms 0.107 km/s; the velocity separation v1 − v2
     agrees with Gallenne's orbit within 0.02–0.3 km/s in every spectrum. γ came out +11.7/+12.6 km/s against −2.1:
     the velocities are relative to the template (tau Ceti −16.6 km/s); the Velocity tab now says so (and that star
     1 is the brighter one when one template is used), translated.
   - **Disentangling on the same spectra: NOT good yet (open).** `spectroscopy.disentangle` with the TODCOR
     velocities (rv_obs, rv2_obs) and the light ratio from TODCOR (0.32): 3–7 s, but the components carry broad
     continuum waves (around H-alpha, tens of A) and FEROS's blue spikes (3890 A); the MK type of the components is
     "poor" (F6–F8 III for the K star, O9 Ia nonsense for the F star). The fainter component does have the deep, broad
     H-alpha (it is the F star, as expected). Cause: the low-frequency (continuum) part of disentangled spectra is not
     constrained with this velocity coverage (a known property; FDBinary / Ilijić and Hadrava work in short windows
     and renormalise each component) plus input normalisation differences. To do: disentangle in windows of a few
     hundred A with a renormalisation of each component per window, clip spikes; then re-run this check (expect
     F7 V and K0 IV from the MK standards; the plot script is in the notes below).
     Tried after that (not committed; experiment code was in the session scratchpad): (a) median instead of mean in
     the shift-and-add (robust to FEROS spikes): MK match score 0.120 -> 0.070 for the K star and 0.236 -> 0.091 for
     the F star ("poor" -> "fair") but the types stay wrong (K star G0 V / F8 III, F star B1 Ia); (b) high-pass of
     the second component (running median 8x or 20x the velocity range) made it worse; (c) renormalising each
     component by a 25 or 60 A running upper envelope: K star G0 V (fair), F star B1 Ia. Two further reasons the
     check is weak: the F star gives only ~0.32 of the light, so its disentangled noise is ~4x the input's; and the
     MK classifier itself puts tau Ceti (G8 V, [Fe/H] −0.5) at G0 V on these FEROS / HARPS spectra (metal-weak stars
     look earlier by their metal lines; the Sun came out G0 V for G2 V before) — so judge a disentangled component
     against a template of known type (CCF peak / line depths), not only by the MK type. Suggested next step: median
     combination (a) + per-window disentangling (100–200 A windows, overlapping) + a test on synthetic composites
     with spikes and a continuum tilt, then this real check again.
   - **v sin i / broadening function on a real fast rotator — found and fixed a crash.** beta Pic (A6 V), HARPS s1d
     ADP.2025-09-11T01:01:26.555 (S/N 571); template a PHOENIX-ACES model 8000 K / log g 4.0 / [Fe/H] 0 fetched with
     `atmosphere.download_phoenix` and converted to air wavelengths (`vac_to_air`; checked: tau Ceti with a 5400 K
     PHOENIX template gives −16.22 km/s in air, −99.7 if left in vacuum). **Bug:** the RV step with method "bf" and
     one component stopped with KeyError 'rv2_obs' on every spectrum with a date and sky position (the single star's
     v sin i made `r2` non-empty, read as a second star) — i.e. on every archive spectrum; fixed in `rv_step`
     (test `test_rv_step_single_fast_rotator_with_a_dated_archive_spectrum`, fails without the fix). Result: BF over
     4400–4800 A: RV +20.9 km/s, v sin i 123.7 ± 0.7 km/s; 4150–4320 A: +20.7, 119.9 ± 0.4; literature RV +20 km/s,
     v sin i 122–130 km/s (Wikipedia 130; Royer et al. 2007 not checked). CCF fails on this star (peak 0.02–0.2), as
     expected for a fast rotator. 5000–5400 A has too few lines in an A star (BF nonsense): use the blue.
     **Data caveat found:** the older ESO product ADP.2019-01-22T01:15:12.551 of the same star (HARPS DRS 3.8) has
     an uncorrected blaze ripple (±40 %, period ~33 A) — no line measurement is possible on it; the 2025 product
     of the same DRS version is clean (spread 0.89–1.11). Not handled in the code (a user would see it on the plot).
   - **Telluric correction on real FEROS spectra (done).** Same night as AI Phe: science tau Ceti
     ADP.2016-09-27T11:56:49.579 (airmass 1.475), standard zeta Phe (B6 V) ADP.2016-09-27T11:56:49.619 (airmass 1.174,
     one hour later). Telluric step 1.4 s: optical-depth scale 1.139, shift 15.1 km/s. O2 B band (6868–6884 A): median
     depth 0.127 -> 0.052, scatter 0.234 -> 0.055; H2O 7180–7300 A: scatter 0.128 -> 0.068; O2 A band: the
     saturated cores are left out (NaN) in the saved file, the rest within 0.66–1.2 of the continuum. Fixed on the
     way: the Telluric tab plotted the division through those saturated cores (spikes to ±10) although the saved
     file leaves them out; the step's `corrected` is now the saved spectrum (test in `test_telluric_step_and_tab`).
   - **Asteroid astrometry on real frames (checked, nothing to fix).** 433 Eros, LCO 0.4 m at SAAO (cpt0m439),
     2026-08-08, three BANZAI e91 frames (`archive-api.lco.global/frames/?OBJECT=neo433eros&RLEVEL=91&public=true
     &start=2026-08-08&end=2026-08-09`: cpt0m439-sq39-20260808-0080/0081/0082-e91, 120 s rp). `astrometry.moving` with
     the object marked at the pixels JPL Horizons predicts (Horizons API, topocentric for the frames' LATITUDE /
     LONGITUD / HEIGHT, QUANTITIES 1 = astrometric ICRF, mid-exposure UT): our positions minus Horizons RA +0.25 to
     +0.30", Dec +0.21 to +0.25" in all three (a constant offset ~0.6 px, the size of BANZAI's WCS error), straight-
     motion fit residuals 0.02–0.03". Times written at mid-exposure (DATE-OBS + EXPTIME / 2).
   - Not started yet from this list: drizzle on real dithered frames, offline plate solving (ASTAP / astrometry.net
     are not installed in the agent container; installing them was not tried).
   **CI:** all test jobs green on Ubuntu, macOS and Windows at `70a42b0` (run 90).
   Original text: **U7 (more real data, partly done):** features not yet run on new real data from the internet: spectral
   disentangling (`spectroscopy.disentangle`) and SB2 / TODCOR on a real double-lined binary with published
   velocities (e.g. HARPS or FEROS ADP spectra of a known SB2 from the ESO archive, compare K1, K2 with the
   literature); broadening function / v sin i on a real fast rotator (compare with a published v sin i); telluric
   correction on a real red spectrum with a telluric standard; moving-object (asteroid) photometry on real frames
   (LCO archive has asteroid programmes); drizzle / stacking on real dithered frames; plate solving offline on a real
   frame. Record each source and comparison in the notes and the speed log.
5. **DONE (session 01RxUU, 2026-11-06):** profiled with cProfile on the raw tau Ceti HARPS frames: the extraction built whole-frame masks per order (now only the rows around each trace, `longslit._band`: 54.6 s -> 5.7 s, sky on 183.6 s -> 9.8 s, identical arrays) and the .Z decoder took 20 s per frame (now 3.8 s, byte-identical); speed log. Original text: **U9 speed:** the echelle step takes ~60 s per HARPS chip (46 orders x 4096 columns); profile it (likely the
   optimal / boxcar extraction loops in `spectroscopy/longslit.py` and `echelle.extract`) and vectorise if it is
   clearly the bottleneck; measure again. Everything else in the speed log is "fine" or fixed.
6. **At the very end, the owner asked for a detailed explanation in plain Turkish** (owner, 2026-11-05: "BLS, ANOVA,
   PDM ... RV, tayf, O−C, fotometri ile neyle uğraştığını anlamadım; en son her şey bittikten sonra bana detaylıca
   açıkla"). Write it as an answer in the chat (not in the repository): what photometry, light curves, period search
   (Lomb–Scargle, PDM, ANOVA, BLS), times of minimum and O−C (and the third-body / apsidal models, MCMC),
   spectroscopy (long slit, echelle, wavelength calibration with arc lamps), radial velocity (RV) and orbits, MK
   classification, visual binaries, remote sensing are, in simple words with an example each; then what was tested
   on which real data, what was wrong and how it was fixed, with the comparison numbers (see the notes and the
   summary above).
6b. **Second test round (2026-11-06):** results and optional speed / memory suggestions in the section "Second full test round" below — suggestions only, ask the owner first.
7. **U11 Basic / Expert interface mode** — postponed by the owner, must not be forgotten; ask the owner before
   starting it.
8. A release only after asking the owner (and after CI is green).

## Second full test round, 2026-11-06 (session 019Lu3; code at `90e106f`, NOTHING was changed)

The owner asked for one more detailed test, with real data, against other programs' output, with timings and CPU /
memory / GPU use, **and no fixes**. Results below; the suggestions at the end are **suggestions only** — the owner
decides whether and when to do them (ask before starting).

**How it was run.** The same real-data driver scripts as the fifth campaign (Photometry, Calibrate, IRAF, TESS,
Kepler, EFOSC2, HARPS, LAMOST / ARAS, ORB6, Sentinel-2, Images, Plan, Project, Automation, interface sweep), one
after the other, plus a 1-second sampler of total CPU, memory and the running test's whole process tree (GUI + engine
workers). Container: 4 cores (Xeon 2.1 GHz), 16 GB, no GPU. It had just been restarted: the data were read from a
cold disk (iowait ~6 % of CPU time, steal 4.5 %), so timings are noisier than in the speed log (IRAF itself went from
11 s to 59 s); differences under ~25 % are not code changes.

### Science: all results unchanged, no regression

| Test | Compared with | Result |
|---|---|---|
| Raw LCO frames calibrated (40 lights) | LCO's BANZAI | 0.919 ADU per pixel (sky noise 9.7 ADU) |
| Same calibration | IRAF ccdred | identical frames (0.000 ADU, flat scale 1.00139); light curves 0.012 % apart |
| Aperture photometry, 40 frames | IRAF apphot.phot | centres 0.038 px; light curves 0.063 % apart |
| Aperture photometry, 265 frames | photutils (independent script) | 0.030 % rms flux, BJD within 0.24 s, centres 0.02–0.05 px |
| Standard magnitude of Qatar-1 | APASS DR9 | 12.745 vs 12.761 |
| Transit time, whole night, automation (one click) | ExoClock ephemeris | O−C +0.27 min (same as before) |
| TESS pixel photometry (W UMa, 18 758 cadences) | SPOC SAP | 0.020 % rms, correlation 1.00000 |
| W UMa period (TESS, 3 sectors) | literature 0.33363 d | BLS 0.333632 d; Roche warning 119 % |
| FG Vir frequencies (TESS s46) | Breger et al. 2005 | all 8 modes recovered |
| KIC 6525196 third body (801 Kepler minima) | literature ~418 d | P3 = 1.1453 yr = 418.3 d, MCMC 20 s, page responsive |
| EFOSC2 long slit **with the new prescan trim** (1024 x 1024) | PESSTO (IRAF) | SN 2018kzr 0.84, AT 2018hyz 0.88 feature correlation, −1.0 / −1.1 A — identical to the untrimmed frames; wavelength solution 13 lines 0.207 A (GUI) |
| Raw HARPS (tau Ceti) | ESO DRS 3.5 | wavelengths 0.0 m/s median, 21.6 m/s rms; velocity +9 +- 8 m/s |
| tau Ceti, 6 HARPS archive spectra | each other | scatter 9 m/s |
| ARAS amateur spectra (AG Dra), LAMOST MK types | previous round | identical |
| eta CrB visual orbit (227 INT4 measures) | ORB6 grade 1 | P 41.66 +- 0.27 yr vs 41.63 |
| **New:** Plan altitudes, La Palma 2026-04-15 | NASA JPL Horizons (airless) | Saturn / Jupiter / Moon rms 0.005–0.010 deg (max 0.11 deg, grid interpolation), Sun 0.001 deg; astronomical dusk / dawn 20:59 / 05:22 vs 20:58 / 05:21 |
| Sentinel-2 NDVI | numpy | identical |
| Images page, 16 Process operations | — | 14 make an image (0.9–7.3 s); Crop and Pixel math need the user's region / expression (same as before) |
| Interface sweep, Turkish, 273 clicks | — | 0 exceptions, 0 missing tooltips, 0 cut texts, 0 untranslated |
| Project page, Guide | — | as before (history, run again, reopen; 103 topics x 4 languages) |

A scratch benchmark script of the earlier round (`bench_spec.py`, guess row 652) crashed: it measured the *control
star*, not the supernova (row 548); it had crashed the same way before. Not a program problem.

### Timings (now / speed log)

| Operation | Now | Before |
|---|---|---|
| Start the application (from source) | 0.5 s, 125 MB; 275 MB after opening 6 pages | — |
| TESS download (3 sectors) + LS / BLS / PDM / ANOVA | 20 s + 3.0 / 2.0 / 5.9 / 5.9 s | 21 s + 2.8 / 1.7 / 6.1 / 5.9 s |
| Orbits & models fit, 47 645 points | 11.2 s | 11.3 s |
| Plan the night (6 targets) | 4.4–4.6 s | 4.1–4.2 s |
| 801 Kepler minima / MCMC 3000 steps | 125.5 s / 20.1 s | 125 s / 20 s |
| Photometry page, 265 frames: quality + suggest + apertures + light curve | 339–587 s in all | 447 s |
| — the four steps alone (same process) | quality 137 s, suggest comparisons 136 s, apertures 2.4 s, light curve 64 s | — |
| Standard magnitudes | 2.7 s | 19.5 s (the working catalogue mirror is now remembered) |
| Calibrate 40 LCO lights / IRAF ccdred | 28.5 s / 59.3 s | 18.4 s / 11 s (cold disk this time) |
| Our photometry vs IRAF phot, 40 frames | 9.4 s vs 1.4 s | 8.9 s vs 1.0 s |
| TESS pixel file: open / measure 18 758 cadences | 28 s / 273 s | 17 s / 235 s |
| Sentinel-2: open / NDVI / PCA / k-means | 29 / 25 / 52 / 62 s | 7–21 / 33–40 / 44 / 56 s |
| Automation: 40 raw frames / whole night 265 frames | 71 s / 335 s | 81 s / 378 s |
| FG Vir frequency analysis | 6.9 s | 7.5 s |
| Images operations | 0.9–7.3 s | 1–8 s |
| HARPS echelle: orders + arc / with solution | 77 s / 66 s | 60 s / 61 s |
| Merged echelle velocity (script total) | 9.7 s | 3–6 s |

### CPU, memory, GPU

- **CPU:** almost every operation uses on average 0.6–1.6 of the 4 cores (peaks 2–3.9). Measured averages (cores):
  photometry steps 1.3, light curve 1.6, calibration 0.9, TESS pixels 1.0, Kepler minima 0.7, echelle 1.0, RV 1.0,
  Sentinel-2 1.1, automation 1.2–1.3. Most of the work is single-threaded.
- **Memory (process tree, peak):** Sentinel-2 two-band scene (2 x 120 Mpx): **9.3 GB** (system 9.9 of 15.7 GB) —
  too much for an 8 GB computer; Images operations 1.9 GB; GPU combine test 1.8 GB; photometry 1.1–1.4 GB;
  everything else 0.2–1.0 GB.
- **GPU:** the container has none, so GPU speed could not be measured (needs the owner's machine). With Mesa's
  software Vulkan driver (llvmpipe, installed in the container only) the GPU code path was checked: the 5 tests in
  `tests/test_compute.py` (normally skipped here) pass, and `clipped_mean` on 15 real LCO bias frames (2400 x 2400)
  gives **bit-identical** results on the CPU and GPU paths. The application refuses a software adapter in "auto"
  mode (correct). The GPU is used only for master-frame combining and stacking.

### Suggestions (NOT tasks — for the owner to decide; do not start without asking)

1. **Photometry page, quality check and comparison-star suggestion** (~0.5 s per frame each, ~4.5 min before the
   light curve on 265 frames): process frames in parallel (the light curve already reads ahead with a thread pool)
   and/or work on a sample of frames for the suggestion. Expected 2.5–3.5x on 4 cores.
2. **Remote sensing memory** (9.3 GB on one Sentinel-2 tile): the band math is already block-wise; the GUI and the
   worker each keep full copies of the scene. Keeping only one copy (memory-mapped or block-wise display) would fit 8 GB
   machines.
3. **TESS / Kepler target pixel files:** opened by splitting into one FITS file per cadence (18 758 files, 28 s; then
   12–15 ms per cadence). Reading the TPF cube directly would make both open and measure much faster.
4. **Use the cores:** frame-by-frame steps (quality, suggestions, TESS pixels, echelle extraction per order) could run
   in parallel; most operations now use about one core of four.
5. **GPU:** measure on the owner's computer (a real GPU), e.g. Calibrate with large stacks, CPU vs GPU mode.
6. **Compatibility note:** since `3748b5a` ESO frames are trimmed by their prescan (EFOSC2: x shifts by 6 px); a row
   or position saved in an older session is 6 px off on such frames. Results are unaffected.

## Task board (keep this up to date: it is how agents hand work over)

**Protocol.** Before starting a task, change its status to `CLAIMED by <agent / session>, <date>` and push that
change at once, so that a second agent does not take the same task and break half-done work. While working, add
what was done and found under the task (commits, files, results, what is left). When finished, set
`DONE (<commits>)`. A task claimed by an agent whose quota ended may be taken over: read its notes first, check
`git log`, and continue from there. The owner's quota for one agent may end at any moment: push small, finished
steps (each passing `tools/precommit.sh`), never a large unpushed change.

Status of everything so far:

| # | Task | Status |
|---|---|---|
| 1-4 | Campaigns 1-3 (sections above) and the fourth round (undo / redo, defaults audit, tooltips on pages) | DONE (up to `433f6f2`) |
| A | Long slit, curved traces (FLOYDS): trace followed as IRAF aptrace, "Spectrum at row", traced line drawn | DONE (`c4168a9`) |
| T1 | Minimum tab: both methods visible as a clear choice, Kwee–van Woerden (eclipsing binaries) the default | DONE (`aeb876e`) |
| T2 | Undo / redo for the remaining editors: Spectrum tools (into Ctrl+Z), Plan targets, Observe exposure rows, Models parameters | DONE (see notes) |
| T3 | Tooltips in the dialogs (exposure calculator, AAVSO, BeSS, observatory set-up, levels, blink, coefficients, moving objects, plugins) with a test | DONE (see notes) |
| T4 | User-control review, page by page: every automatic choice visible, explained, overridable | DONE (see notes) |
| T5 | FLOYDS-type headers: TRIMSEC 'UNKNOWN', DATASEC that includes the BIASSEC columns | DONE (see notes) |
| T6 | "Load identifications from an IRAF database" (Reduce and Echelle tabs) + reidentify-style shift search; FLOYDS wavelengths end to end | DONE (see notes) |
| T7 | Spectral classification checked against MKCLASS (Gray & Corbally) / iSpec; shown as a ranked suggestion with scores | DONE (see notes) |
| T8 | Error messages (old task 38): every message says what happened and what to do, in all four languages | DONE (see notes) |
| T9 | Real ground photometry time series through the whole Photometry page, AAVSO export, standard magnitudes | DONE for the photometry and timing (see notes); AAVSO export and standard magnitudes still need CDS (blocked here) |
| T10 | Real long-slit data of a simple spectrograph; reduced archive spectra (ESO / LAMOST) through RV and line tools | DONE: ESO, LAMOST, 30 ARAS amateur spectra, and a raw ESO EFOSC2 night (see notes); raw amateur frames not found |
| T11 | Paper-quality output: every result exported as a figure (vector, error bars, labelled axes, units) and a table with uncertainties (CSV and LaTeX); a reviewer can reproduce it | DONE (see notes) |
| T12 | CI green for the latest commits; a release only after asking the owner | green at `37f1073` (2026-11-05); keep checking after each push |
| T13 | Turkish terms as "English/Türkçe" where both are used (order/mertebe, seeing/görüş, airmass/hava kütlesi…), translations and guide | DONE (see notes) |
| U1 | Contact (W UMa) binaries: warn that the Models page's detached (spheres) model does not hold, point to the PHOEBE export | DONE (see notes) |
| U2 | Plan page: explain "ephemeris"; short explanation (tooltip) on "add to ephemeris" and the button next to it | DONE (see notes) |
| U3 | Plan page: several objects (stars by name, planets, Moon) in one visibility chart; the Moon always drawn dashed | DONE (see notes) |
| U4 | O−C MCMC in the background (page stays usable, progress, cancel); tried on a real published minimum-times list | DONE (see notes) |
| U5 | Online catalogues: fall back to CDS mirrors (Harvard) when Strasbourg does not answer; then T9's leftovers: AAVSO report and standard magnitudes on the real LCO night | DONE (see notes) |
| U6 | Heavy use test, page by page, as an astronomer (every button, tooltip, text, dialog, menu, language, theme), with timings: U6a Start, U6b Plan, U6c Observe, U6d Calibrate, U6e Images, U6f Photometry, U6g Light curves & O−C, U6h Spectroscopy, U6i Orbits & models, U6j Remote sensing, U6k Automation, U6l Project, U6m Guide, U6n menus / settings / dialogs | DONE (session 019Lu3, 2026-11-06): sweep in 4 languages; real-data use of every page (Plan, Observe with INDI simulators, Calibrate, Images, Photometry, Light curves & O−C, Spectroscopy long slit, Orbits & models incl. a visual orbit on real measures, Remote sensing, Automation, Project, Guide); the echelle on raw HARPS is U8b |
| U7 | Every feature on new real data from the internet (list in the notes; record sources) | PARTLY: real data so far: LCO (raw + BANZAI), TESS (W UMa, FG Vir), Kepler (KIC 6525196, KIC 8462852), K2, ESO EFOSC2 raw, ESO HARPS raw + DRS products, WDS INT4 / ORB6 (eta CrB), Sentinel-2 L2A, SIMBAD / VizieR / VSX / Exoplanet Archive through mirrors; left: see 'Still to do' 4 |
| U8 | Raw vs published processed data: U8a LCO raw (e00) vs BANZAI-reduced (e91) frames and photometry; U8b ESO raw echelle (HARPS / FEROS) vs ESO's reduced spectra; U8c TESS FFI photometry vs the SPOC light curve; U8d IRAF installed here: the same raw long-slit and photometry reduced in IRAF vs here; U8e times of minimum vs published | DONE (session 019Lu3, 2026-11-06): U8a, U8b (raw HARPS vs ESO DRS: 22 m/s), U8c, U8d, U8e |
| U9 | Speed: every operation timed (speed log below), slow ones fixed and measured again | DONE: period search, light curves, calibration, remote sensing, deconvolution, histogram matching, echelle extraction (54.6 -> 5.7 s) and .Z decompression (20 -> 3.8 s) made faster (speed log) |
| U10 | Re-run the tests touched by every fix; CI green | each fix re-tested on its real data; CI green up to 9b6ba9d; aa311ae … 339bb16 not checked yet (see 'Still to do' 1) |
| U11 | Basic / Expert interface mode (chosen on the Start page, changeable later; settings stay where they are, only folded) | DONE 2026-11-06 (P2) |

### Notes on the fifth campaign (U tasks)

**U1 (done).** `models.fit.roche_check(r1, r2, q)`: Eggleton (1983) lobe radius; "contact" when a star fills >= 90 % of
its lobe, "distorted" when a radius > 0.25 a. The fit step returns `roche`; the Models page shows a warning (contact:
spheres model not valid, export PHOEBE / WD; distorted: errors too small). Real test: W UMa, 3 TESS sectors
downloaded on the Light curves page, saved, fitted on the Models page: "fills 119 % of its Roche lobe". Found on the
way and fixed: (a) **TESS / Kepler / K2 downloads were broken**: MAST's product list names the pipeline in "project"
(no "provenance_name"), Kepler / K2 light curves are "LLC" not "LC" (`timeseries/archive.py`); K2 source label "K2 C1".
(b) The Light curves page had **no way to save** a downloaded / edited light curve, so it could not reach the Models
page: "Save light curve (CSV)…" added. (c) **PDM and BLS took minutes to hours** on several sectors / seasons:
`period.search` searches the densest stretch first, then all data around the best peaks (speed log). (d) Periods from
data in stretches far apart are ambiguous by one cycle across the gap (W UMa: Lomb–Scargle and ANOVA chose the
neighbouring alias 0.166777 d; BLS 0.333632 d and PDM 2 x 0.166816 d agree with the true 0.333633 d from the times of
minimum and with VSX 0.3336334 d): the result now says so and gives the two neighbouring periods.
**U2 (done).** Plan page: visible line under the buttons ("Add: position only…; Add with ephemeris: also the times of
its eclipses or transits (an ephemeris = T0 and period…)"), longer tooltips on both buttons explaining "ephemeris".
**U3 (done).** Planets and the Moon by name (English, Turkish, German, Spanish names: `planning.targets.BODIES`) are
followed through the night with astropy's built-in ephemeris (offline), all targets in one chart; the Moon is drawn
dashed when not typed, as a normal line when typed. UTC axis wraps at 24 h. The Moon distance no longer floods the
log with a frame warning. Tested on the owner's example (NY Vir, Saturn, Jupiter, Betelgeuse, Moon, Arcturus) in
English and Turkish.
**U5 (mirrors done).** `astrowb/mirrors.py`: SIMBAD and VizieR are tried at Strasbourg, then IDIA (VizieR) and
Harvard; the working server is remembered (also in `mirrors.json` in the config folder, for later worker processes).
Harvard's VizieR returns nothing for Gaia / APASS, hence IDIA first. VSX ephemerides fall back to VSX's copy in VizieR
(B/vsx/vsx; aliases such as Algol through SIMBAD's position) when aavso.org does not answer. Still open in U5: the
AAVSO report and standard magnitudes on the real LCO night.
**U4 (done).** The O−C page hands an MCMC to the task engine (`timeseries.oc_fit` step; progress, cancel in Tasks);
least squares alone stay instant on the page. Real test: KIC 6525196 (Kepler, 18 quarters, 65 267 points) -> BLS ->
"time every minimum" (801 minima) -> O−C page, third body: P3 = 1.1453 +- 0.0032 yr = 418.3 +- 1.2 d (literature:
the outer orbit of this spectroscopic triple is ~418 d), A = 4.25 +- 0.10 min, e3 = 0.34 +- 0.04. MCMC 3000 steps as a
task: 20 s, the page answered throughout (longest pause 0.05 s). Note: BLS gave 1.7103 d = P/2 (equal eclipses);
the timings were still right (all eclipses as "I"), but a user must know the true period is 3.42 d.
**U5 (done).** Real LCO Qatar-1 night (265 frames): "Standard magnitudes (APASS / Gaia)" found the four comparison
stars in APASS DR9 through the VizieR mirror in 19.5 s; the target came out at 12.745 (median, CV), APASS gives
12.761 +- 0.031. The AAVSO Extended report (#DATE=JD from jd_utc, ENSEMBLE / CMAG=na, MTYPE=STD, AIRMASS) is well
formed. Note: MERR (0.003) is the photon error; the scatter is 0.012 because scintillation is only added when the
telescope aperture is known (the page says so).
**U6 sweep (done).** `scratchpad/real/u6_sweep.py`: every page and tab in Turkish, German, Spanish (and English):
every control's tooltip, cut texts, texts left untranslated, every enabled button clicked with no data (dialogs,
menus and file pickers answered "cancel"), with the time of each click. Found and fixed: "Export results (CSV /
LaTeX)…" and its tooltip were English in every language (a module-level tr() helper made the translation tool file
them under an empty context; test `test_no_translation_is_filed_without_a_context`); two buttons in the image side
panel cut in Turkish / German / Spanish (keyword buttons now one under the other, "Export data (CSV)" keeps its
width). Now: 0 controls without a tooltip, 0 untranslated texts, 0 cut texts, 0 exceptions in 273 clicks per
language; the only click over 1 s is "Plan the night" (4.2 s, empty target list: the worker start and the Sun /
Moon ephemeris).
**U9 photometry speed.** Profile of the light curve (30 LCO frames of 2400 x 2400): 0.76 s per frame, mostly the
frame-to-frame shift (despike + statistics + FFT of the whole frame) and reading the compressed file. Now the shift of
large frames (> 4 MP) is found on 2x2-binned frames (every star is re-centred afterwards anyway; stacking keeps the
full resolution) and the next frame is read in a thread while one is measured: 60 frames 35.2 s -> 13.6 s, relative
fluxes identical to 2.5e-5. Test `test_binned_frame_shift_is_close_enough_for_re_centring`.
**U8a (done): LCO raw (e00) through the Calibrate page vs BANZAI (e91).** Data: LCO archive, public: 40 raw Qatar-1
frames (`OBJECT=Qatar-1&RLEVEL=0&start=2026-11-02&end=2026-11-04`), 30 raw bias and 20 raw darks of that night
(`INSTRUME=sq41&OBSTYPE=BIAS|DARK&RLEVEL=0&start=2026-11-02T12:00&end=2026-11-03T18:00`), BANZAI's master skyflat
(`basename=elp0m415-sq41-20261027-skyflat-central30x30-bin1x1-Astrodon-Exo`; only one raw Astrodon-Exo skyflat that
week). Found and fixed: (a) **LCO science frames were "type unknown, ignored"**: OBSTYPE EXPOSE (and FLOYDS SPECTRUM,
STANDARD) were not read as lights; (b) **BANZAI's master flat was not used**: it states GAIN = 17291 (the lights 0.78)
and flats had to agree in gain / offset; flats now match on the read-out mode only (the gain is normalised away,
the offset is the bias), bias and darks still on every setting. Result: our calibrated frames = BANZAI's x 1.2678
(constant: e- vs ADU, gain 0.78) to 0.92 ADU per pixel (sky noise 9.7 ADU; our 30-bias / 20-dark masters' own noise
~0.74 ADU); light curves of Qatar-1 from both sets of frames differ by 0.021 % rms (each scatters 0.679 %).
**U8d (done): IRAF.** Community IRAF 2.17.1 from Ubuntu (`apt-get install iraf iraf-noao`; `export USER=root`,
`mkiraf`; IRAF cannot open long paths: short symlinks in its working folder; it reads plain FITS only: the .fz
frames unpacked with astropy, LCO's DATASEC / TRIMSEC / BIASSEC / CCDSEC / DETSEC removed, which IRAF cannot parse).
Scripts `scratchpad/real/u8d_iraf_phot.py`, `u8d_iraf_ccdproc.py`. (1) **apphot.phot** on our 40 calibrated frames
(centroid, cbox 11, mode sky, same radii, IRAF given starts 1.5 px off): centres agree to 0.038 px (median), target
flux IRAF / ours = 1.00056 +- 0.00048, light curves 0.700 % (IRAF) and 0.679 % (ours) rms, difference 0.063 % rms.
(2) **ccdred** (zerocombine avsigclip, darkcombine scale=exposure, ccdproc zero+dark+flat) on the same raw frames:
master bias and dark identical to ours (0.000 ADU); calibrated frames identical up to the flat normalisation
(IRAF divides by the flat's mean, we by its median: x 1.00139 everywhere), light curves differ by 0.012 % rms.
IRAF pitfall met: ccdproc bias-subtracts a finished master flat unless its header says ZEROCOR / DARKCOR /
CCDPROC done (our Calibrate page used BANZAI's master flat correctly). Found on the way (fixed): half the LCO bias /
darks of that night were full-chip (6422 x 9600) next to the lights' 2400 x 2400 crop and all were combined: groups
no light needs are no longer combined (the page says so; without lights every group is still made): 40 lights
110 s -> 18.4 s (IRAF 11 s + unpacking). Test `test_groups_no_light_needs_are_not_combined`.
**U8c (done): TESS pixels vs SPOC.** W UMa, sector 21: the SPOC target pixel file (13 x 11 px, 19 694 cadences)
opened on the Photometry page (18 758 frames kept, 936 flagged left out), star clicked at SPOC's aperture centre,
"Choose apertures", measure. Found and fixed: on a 13 x 11 stamp the aperture chooser gave FWHM 200 px and radii
200 / 600 / 721 px (its profile looked for sky 17–25 px away): radii are now limited to the stamp (FWHM 1.65 px,
aperture 2.5 px = 94 % of the light, sky in the corners 4.9–7.0 px); test `test_apertures_fit_a_small_tess_stamp`.
Result: ours = SPOC SAP_FLUX to 0.020 % rms (correlation 1.00000, amplitude 0.5402 vs 0.5403). PDCSAP's amplitude
is larger (0.755) because SPOC removes the light of neighbouring stars (CROWDSAP) - the application's light curve
is the SAP kind.
**U8e (done).** KIC 6525196 against the Kepler EB catalogue (Kirk et al. 2016, VizieR J/AJ/151/68): P 3.4206042 +-
0.0000062 d, BJD0 2454954.3521 +- 0.024; ours (linear ephemeris of the 801 minima, both eclipses as "I", so x 2)
P 3.4205978 +- 0.0000007 d (within the catalogue's 1 sigma), T0 2454954.35372 (within its error; 2.3 min, the third
body's light-time swing is +-4.25 min).
**U6h (done): a raw EFOSC2 night on the Calibrate and Spectroscopy pages, as a user.** Found and fixed: (a) the Reduce
tab said "Working…" behind an error box when a step failed: spectroscopy steps (and remote sensing) now write the
error on their tab; "ValueError:" is no longer shown to the user; (b) with the default "Dispersion along rows" the
EFOSC2 spectrum (which runs along y) gave "could not be followed": when the other orientation traces, the message now
says to change "Dispersion along"; (c) "Lines from a reference arc / IRAF database" with PESSTO's database found 0 of
9 lines: its reference is the raw 2-D arc frame, read as if it were a 1-D calibrated spectrum; a 2-D reference now
takes the database's pixels with IRAF reidentify's shift (9 of 9, +2.4 px); (d) the wavelength solver moved an
identified line to another catalogue line (He I 3888.7 -> 3928.6) and grew its window in steps of 15 % of the arc,
so the curved grism-11 dispersion ran 27 A off in the blue and five correct lines by hand gave 3.1 A rms: identified
lines now stay as given and the window grows in 5 % steps. Now every start (2 lines, 4 or 5 by hand in the middle,
PESSTO's 9) gives 13 lines, degree 4, rms 0.21 A, as before with nine. Tests `tests/test_wavecal_real.py`,
`test_task_error_drops_the_generic_value_error_name`. Times: scan 3 s, calibrate 3 s, extract 2 s, solve 1.3 s.
**U6j (done): a real Sentinel-2 L2A scene on the Remote sensing page.** Data: Element84 Earth Search STAC
(`https://earth-search.aws.element84.com/v1/search`, collection sentinel-2-l2a, point 32.85 E 39.93 N, cloud < 2 %):
S2B_36TVK_20250828_0_L2A, B04 and B08 COGs (10980 x 10980 px, 232 MB each, from sentinel-cogs.s3.us-west-2). Found
and fixed: (a) Sentinel-2 / Landsat give one file per band and the page opened one file only, so NDVI (red + NIR)
was impossible: several files of one scene now open as one image (bands named B04, B08…, roles from Sentinel-2 band
names; the source is the paths joined with ';', which the steps read back); (b) roles with no band showed the first
band and an index (NDWI with no green band) would silently use the wrong one: they stay empty and the formula says
"unknown band GREEN"; (c) **out of memory**: the page took 7 GB and the NDVI task 6.6 GB and the machine killed
it; band math is now float32 in blocks of rows (NDVI 11.8 s -> 1.4 s, 5.3 GB -> 3 GB), statistics from a 4-M-pixel
sample for mean / std / percentiles (11.4 s -> 0.43 s), PCA from the covariance of a sample instead of an SVD of
every pixel and pixels kept as contiguous band rows (k-means labels in blocks): PCA ran out of memory, now 44 s;
k-means 56 s (reading 10 s and writing the GeoTIFF 14 s of it). NDVI equals numpy's to 0; pixel read-out UTM 36N ->
lon / lat agrees with pyproj. Open question (not changed): L2A since baseline 04.00 needs reflectance = DN/1e4 - 0.1;
this scene's red band has DN < 1000 (p2 = 199), so whether the offset applies to these COGs is unclear - check before
telling users to subtract it.
**U6g frequencies (checked, nothing to fix).** FG Vir (delta Scuti), TESS sector 46 downloaded on the Light curves
page (15 988 points, 7 s), Frequency analysis to 50 c/d: 8 frequencies with S/N >= 4 in 7.5 s: 12.7163, 24.2116,
12.1539, 9.6561, 23.406, 19.8682, 9.1997, 21.0512 c/d - the known FG Vir modes (Breger et al. 2005: 12.716, 23.403,
21.052, 19.868, 12.154, 9.656, 9.199; their 24.228 is 0.016 c/d away, inside one sector's resolution ~0.04 c/d).
**U6k automation.** "Exoplanet transit" on the raw LCO folder + master-flat folder (inputs typed as a user):
scan, calibrate, quality, suggested comparisons, light curve all ran (~100 s for 40 raw frames); the minimum step said
"the light curve shows 3 eclipses" although those 40 frames (the night's last 20 min) hold no transit: `dips()` never
asked whether the lowest points stand out of the noise. Fixed: a dip must be deeper than 5 sigma of the smoothed
curve, and with none the step says "no eclipse or transit stands out of the noise… do the frames cover it?" instead
of fitting noise. Checked on real data: the full night (265 frames) still 1 dip, the last 40 frames 0. Test
`test_noise_alone_is_no_eclipse`. The same automation on the whole night (265 BANZAI frames, one click): 378 s,
transit mid-time 2461347.61134 BJD_TDB against ExoClock's prediction 2461347.61115 (O−C +0.27 min), depth 2.24 %
(literature 2.3–2.5 %), T14 1.57 h. Observe page: `tests/test_indi_simulators.py` passes against the real INDI
simulators (`apt-get install indi-bin`): mount, CCD, filter wheel, focuser.
**U8b raw HARPS echelle vs ESO's DRS (done).** tau Ceti, HARPS.2010-08-27T05:33:35 (60 s) with the evening's bias,
fibre-A tungsten flat (LAMP,DARK,TUN) and ThAr (WAVE,WAVE,THAR2), raw from the ESO archive
(`https://dataportal.eso.org/dataportal_new/file/<dp_id>`), against ESO's reduction of the same exposure (DRS 3.5:
e2ds_A with its per-order wavelength polynomials, s1d, CCF; ADP.2014-09-24T09:43:29.897 + ancillary tar). Blue chip
on the Echelle tab's step (orientation y, reverse, no sky, first order 161 decreasing). Found and fixed: (1) faint
bumps beside the orders on the flat (fibre B leak / ghost, 33–119 ADU next to 2000–25000) counted as orders and
tracing failed -> a peak a tenth of its neighbour or fainter is not an order (46 orders, as ESO); (2) the extraction
width (70 % of the order spacing) took in fibre B's simultaneous ThAr 17 px away (emission spikes in the star, flux
correlation with s1d 0.31) -> 3 x the orders' FWHM measured on the flat (0.996); (3) 245 ADU of bias stayed in: ESO
writes prescan / overscan sizes (DET OUT1 PRSCX/OVSCX/NX), not BIASSEC -> used when they add up to the frame (EFOSC2
frames are now trimmed to 1024 x 1024 too); (4) a multi-extension frame lost the primary header (no RA / site: no
barycentric correction) -> the primary's keywords are inherited (read_image, masters.load, read_frame); (5) HARPS
frame types per fibre (STAR,WAVE = light; LAMP,DARK,TUN = flat; DARK,LAMP,TUN = unknown); (6) the velocity over the
whole merged spectrum was 5.6 km/s off (CCF peak 0.009): one clipped cubic over 1500 A went through zero at the faint
blue end -> spectra of more than 8000 pixels are normalised in pieces. Result, 9 ThAr lines identified by hand in 3
orders: 1591 lines, 0.0004 A rms; our wavelengths minus ESO's over all 46 x 4096 pixels: median 0.0 m/s, rms 21.6
m/s (per order medians -22 ... +36 m/s; ESO fits each order alone, we fit one 2-D polynomial); barycentric correction
18.607 vs ESO's BERV 18.602 km/s; velocity against ESO's s1d +9 +- 8 m/s over 3783–5304 A (-1 m/s over 4000–5000 A),
i.e. the same tau Ceti RV as ESO's CCF (-16.532 km/s) to about 10 m/s. Not done: the red chip (same steps).
**Plan chart in English with local time (owner's request, done).** The chart's texts are English whatever the
interface language (for papers), planets and the Moon by their English names; the top axis gives the local time;
"Local time (hours from UTC)" box (Auto = this computer's time zone on the night's date, summer time included);
the events table has the middle in local time and the status line the night in UTC and local time. Guide (4 languages).
**U6e Images page (done).** Every Image > Process operation on a real calibrated LCO frame (2400 x 2400), dialogs
accepted with their defaults: 0 errors; flip / rotate / bin / Gaussian / unsharp 1.0–1.8 s, median 2.0 s, background
2.6 s, resample (to 4800 x 4800) 7.8 s. Made faster: Richardson–Lucy 20 iterations (two FFT convolutions per
iteration, the PSF's transform recomputed each time) now with the separable Gaussian filter, same zero-padded edges:
19 s -> 7.3 s (on the page 8.4 s); histogram matching interpolates directly on its two even grids instead of
searching (np.interp): 7.8 s -> 2.9 s, identical result (page 3.9 s). (A first run looked slow because the test had
switched on "Apply to all open images" - the program behaved correctly.)
**U6i visual binary (checked, nothing to fix).** eta CrB AB (WDS 15232+3017, STF1937AB): 227 measures 1934–2015
from the Fourth Interferometric Catalog (`http://www.astro.gsu.edu/wds/int4/int4_15.html`; https and ORB6 on VizieR
do not answer here, `http://www.astro.gsu.edu/wds/orb6/orb6orbits.html` does) on the Visual-orbit tab, parallax
55.6 mas: P 41.66 +- 0.27 yr, e 0.287 +- 0.012, a 0.852 +- 0.014", i 59.7 +- 1.0 deg, Omega 20.3 / omega 225.0 deg
(+180 deg: 200.3 / 45.0), T 1975.86 +- 0.30, total mass 2.08 +- 0.10 Msun, 5.7 s - ORB6's grade-1 orbit (Muterspaugh
et al. 2010): 41.63 yr, 0.279, 0.862", 58.1, 202.8 / 39.9, 1975.55: all within 1–2 sigma (unweighted measures).
**CI (fixed).** Run 80 failed once: a minimum arriving after the Photometry plot was cleared (IndexError in
show_minimum); the marker is skipped then, test extended.
**Environment note (agent container only):** the container's CA bundle lacks STScI's root (emSign); Python
scripts here use `scratchpad/ca-all.pem` (container bundle + certifi) via `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`.
Users are not affected (certifi has it).

**U6l / U6m Project and Guide (checked, nothing to fix).** New project 0.02 s; the quality step on 12 real LCO frames (9.1 s) lands in the history with its inputs in the details; "Run again" 8.1 s adds a second row; the project reopened after a restart shows both. Guide: 12 categories and 103 topics in each of the four languages, no file missing. The unused "planned for a later version" page class was removed (no page used it).

### Speed log (fifth campaign; machine: the agent's cloud container, 4 cores, no GPU)

| Operation | Data | Time | Opinion / action |
|---|---|---|---|
| TESS light curve download (Light curves page, 3 sectors, MAST) | W UMa, 47 645 points | 21 s (files cached; first time ~14 s per 2 files) | fine |
| Period search PDM | W UMa 2 sectors 736 d apart, 35 158 points | before 279.8 s, now 2.6 s | was far too slow (frequency grid over the whole span x every point): two-stage search |
| Period search PDM | 1 sector, 18 659 points | before 5.4 s, now 1.5 s | fine |
| Period search BLS | 2 sectors | before > 300 s (stopped, 2.5 GB), now 0.8 s | was unusable: same two-stage search |
| Period search BLS | 1 sector | before 3.9 s, now 0.7 s | fine |
| Period search Lomb–Scargle / ANOVA | 2 sectors | 0.4 s / 2.4 s (unchanged) | fine (astropy's fast methods); a two-stage ANOVA picked a wrong alias: kept single-stage |
| Period search, from the page (worker start included) | 3 sectors, 47 645 points | LS 2.8 s, BLS 1.7 s, PDM 6.1 s, ANOVA 5.9 s | fine |
| Orbits & models fit (spheres model) | W UMa, 47 645 points | 11.3 s | acceptable |
| Plan: add a target by name (SIMBAD) | NY Vir, Betelgeuse, Arcturus | first 12–14 s each (Strasbourg times out, then the mirror), now 0.6–2 s | fixed: the working mirror is remembered across worker processes |
| Plan: add a planet / the Moon | Saturn, Jupiter, Moon | 0.5–1.5 s | fine (offline) |
| Plan: plan the night | 6 targets incl. planets and the Moon | 4.1–4.2 s | fine |
| Add with ephemeris (VSX through VizieR when aavso.org does not answer) | NY Vir, W UMa, Algol | 1.1–2.6 s (Algol 16 s: alias through SIMBAD on the first call) | fine |
| Kepler download, 18 quarters (MAST) | KIC 6525196, 65 267 points | 216 s | MAST itself answered slowly then (astroquery query 90–120 s; minutes later 1.3 s): not the program |
| Time every minimum (Kwee–van Woerden + bootstrap) | 801 Kepler eclipses | 125 s | slow-ish (0.16 s per minimum, the bootstrap); acceptable for a one-off, keep an eye on it |
| O−C fits on the page | 801 minima | linear 0.2 s, third body 1.0 s, apsidal 0.3 s | fine |
| O−C third body + MCMC 3000 steps (task) | 801 minima | 20 s, page responsive (longest pause 0.05 s) | fine; before it froze the page |
| Photometry: measure a light curve (GUI, 265 LCO frames 2400 x 2400, 5 stars) | Qatar-1 | 447 s before (1.7 s / frame, other work running alongside) | too slow: profiled and fixed, see next line |
| Photometry: light curve, 60 frames (same data, script) | Qatar-1 | before 35.2 s, now 13.6 s | 2x2-binned frame shift + reading ahead; same fluxes |
| Photometry: standard magnitudes (APASS / Gaia, mirror) | 4 comparison stars + target | 19.5 s | acceptable (network) |
| Every button of every page with no data (sweep) | 273 clicks per language | all < 1 s except "Plan the night" 4.2 s | fine |
| IRAF apphot.phot, 40 frames (positions given per frame) | same | 1.0 s (ours 8.9 s, which also tracks the field) | fine |
| Photometry: open a TESS target pixel file (19 694 cadences) | W UMa s21 | 17 s | fine |
| Photometry: measure 18 758 TESS cadences (13 x 11 px) | W UMa s21 | 235 s (12.5 ms each) | acceptable |
| Remote sensing: open 2 Sentinel-2 band files (2 x 120 Mpx) | S2B_36TVK_20250828 | 7–21 s | acceptable |
| Remote sensing: NDVI (task, incl. writing and showing) | same | 33–40 s (band math itself 1.4 s, before 11.8 s and 5.3 GB) | acceptable |
| Remote sensing: PCA / k-means (steps) | same | 44 s / 56 s (PCA before: out of memory) | acceptable; reading and GeoTIFF writing are half of it |
| Automation "Exoplanet transit", one click | 40 raw LCO frames + flat / 265 BANZAI frames | 81 s / 378 s | fine |
| Frequency analysis (TESS, 15 988 points, to 50 c/d) | FG Vir | 7.5 s | fine |
| Images: every Process operation on 2400 x 2400 | LCO frame | 1–8 s each (RL deconvolution before ~22 s, histogram match before ~10 s) | fine |
| Calibrate: scan 91 raw LCO frames | 30 bias, 20 darks, 40 lights, 1 master flat | 3.3 s | fine |
| Calibrate: masters + 40 lights (2400 x 2400, compressed) | same | before 110 s, now 18.4 s (IRAF ccdred 11 s) | the full-chip masters no light needed are skipped |
| Echelle reduction (Echelle tab, engine step) | raw HARPS blue chip 4096 x 2048, 46 orders, flat + ThAr | before 54.6 s (sky off) / 183.6 s (sky on), now 5.7 s / 9.8 s, identical output (session 01RxUU) | fixed: every order's windows were built over the whole frame; now only over the rows around its trace (`longslit._band`) |
| Opening a .fits.Z (ESO raw, LZW) | HARPS frame, 20 MB -> 35 MB | before 20 s, now 3.8 s, byte-identical to gzip -dc (session 01RxUU) | fixed: the decoder keeps each code's whole string instead of rebuilding it byte by byte; done once per file anyway (the copy in fits_from_raw is reused) |
| Velocity of a merged echelle spectrum (CCF, ESO s1d as template) | 124 k pixels, 3783–5304 A | 3–6 s | fine |

### Notes per task

(Each agent adds its notes here under the task number.)

**T11 (done; agent session 019Lu3 finished the wip branch, rebased it on main, merged. The remote branch `wip-t11-results-export` is still there (deleting it was refused by the session's
safety check): the owner can delete it on GitHub; nothing on it is missing from main).** On top
of the wip commit: Models page `fit_table()` (free parameters with covariance errors, MCMC medians with the larger
side of the 68 % interval where sampled, fixed ones marked "(fixed)", derived r1, r2, e, ω, L2/L1, absolute
dimensions and the transit mid-time when present, rms and χ²ᵣ; the caption names the model and where the errors come
from) and its "Export results (CSV / LaTeX)…" button; Period page time axis "Time − 2459500 (d)" (point deletion
still hits the right point); Frequency page amplitude axis in mag or relative flux. Tests:
`tests/test_results_export.py` (rounding, both formats, O−C table), Models table in `tests/test_ui.py`. Not done:
error bars on the Period page (it keeps no errors). The guide describes the export button (pages 07, 08, 09, four
languages).

**T13 (done).** In the Turkish translations and the Turkish guide the first use of the term in each text (each
UI string, each guide paragraph) is "order/mertebe", "seeing/görüş", "airmass/hava kütlesi" (capitalised at the
start: "Order/mertebe numaraları"); later uses in the same text stay Turkish only. The old "Düzenleri flat üzerinde
izler" (order mistranslated as "düzen") is "Order/mertebeleri…". Unit texts stay short ("kadir / hava kütlesi").
Kept in English already: flat, bias, dark, light, arc, blaze, FWHM, detrend. The script used: first match of
`(?<![/\w])([Mm])ertebe`, `([Gg])örüş(?!me|ler)`, `([Hh])ava kütle` per `<translation>` and per guide line.

**T8 (done).** Every error text shown in the interface now goes through `messages.translate()` (it passes unknown
text through unchanged): Models, Plan, Spectrum tools, Observe (connection, copying, configuration), observatory
search, update check, Calibrate scan problems, Images statistics, AAVSO report, Period page file reading. Ten common
engine errors got the remedy after a colon, with templates and tr / de / es translations naming the real page and
option names: no frames to combine, too few stars / star patterns do not match (→ Align "shift only"), no image data,
images of different size, no observation time (→ add DATE-OBS on the Images page's Header tab), no minimum found,
no orders found (→ add them by hand on the flat), no whole eclipse at the predicted times (→ check T0, P, time scale),
no catalogue magnitude (→ plate-solve, APASS / Gaia). Left: library errors (astropy, OSError) stay in English; the
other observatory / device messages name their cause and were judged clear enough.

**T9 (photometry and timing done; agent session 019Lu3).** Data: LCO public archive, 265 BANZAI-reduced frames
(e91, `.fits.fz`, SCI + CAT + BPM + ERR extensions) of Qatar-1 b, 0.4 m at McDonald (elp, sq41), 2026-11-03
01:21–03:45 UTC, 30 s, Astrodon-Exo filter, 13.6 MB each:
`https://archive-api.lco.global/frames/?RLEVEL=91&public=true&OBJECT=Qatar-1&start=2026-11-02&end=2026-11-04&limit=100`
(anonymous users: limit ≤ 100, use `&offset=100`, `&offset=200`; the JSON's `url` fields are signed S3 links valid
48 h). Reference ephemeris: ExoClock `https://www.exoclock.space/database/planets_json` → Qatar-1b T0 2457980.733187
± 0.000031 BJD_TDB, P 1.420024447 d, duration 1.66 h, depth 25.4 mmag: predicted mid-transit epoch 2371 =
2461347.611151 BJD_TDB (02:38:54 UTC). The NASA Exoplanet Archive answered with a Cloudflare block this time.
Driving script (GUI, real clicks): open the 265 files, quality check, click the target (its pixel from the WCS),
Suggest comparison stars, radii from the profiles, Measure, detrend (airmass, transit left out), Time of minimum.
Found and fixed (each with a test):
- Detrending with a left-out range that left only 7 points at the start (airmass 1.2332–1.2355 fitted, 1.24–1.45
  left out) carried the trend 100× beyond its data: the curve ran off to 2.8 while the page said "scatter 0.70 % →
  0.46 %". Now refused with "airmass in the left-out range is far from its values at the fitted points: leave out
  only the eclipse"; the success line says the scatter is that of the N points fitted.
- Time of minimum with T0 and P given still counted dips and answered "the light curve shows 3 eclipses: give T0
  and the period" — the ephemeris now says which eclipse it is. `minima.dips()` counted one noisy 2.4 % transit as 3–4
  dips: now smoothed for the noise, baseline from the upper half (the median of all points lies inside a long
  transit), and low runs merge unless the curve stays out of the dip longer than the dips last.
- Suggested comparison stars were ranked by brightness only and came out at the frame's extreme edges
  (y = 52 and 2378 of 2400): now similar brightness *and* near the target (AstroImageJ practice).
Result with the defaults (before the centring fix below): transit at 2461347.608994 ± 0.000595 BJD_TDB, O−C −3.1 ± 0.9 min against ExoClock (with a
fixed 14 px aperture −0.5 min; KvW −2.3 to −4.5 min); depth 3.1 % (r = 10 px) / 2.4 % (r = 14 px), literature
2.3–2.5 %. BJD_TDB of the frames checked against astropy (same frame: identical).
**Finding on "Radii follow the seeing" — corrected (agent session 019Lu3).** The −22 min with radii following the
seeing (and the extra growth of the target's light between 10 and 14 px, first read as a faint neighbour in its
wings) came from centring: the clicked position, 2.7 px off Qatar-1, was kept because `recenter` refused moves over
2.5 px, so the aperture sat off the star all night. Now the clicked positions are snapped once on the first frame
within half the centroid box (`lightcurve.py`, also `live.py`, `inspect.py`, `choose_apertures`); test
`test_a_click_three_pixels_off_is_snapped_onto_the_star` (fails on the old code). After the fix: O−C +0.1 min with
fixed radii, +0.4 min with radii following the seeing. `target_excess` and its warning stay (they catch a real
blend; tested on a synthetic one, on stars without one the value stays within ±0.4 %).
**Benchmark against an independent astropy/photutils reduction (owner's request).** Same 265 frames, same stars,
plain photutils apertures and astropy BJD_TDB written from scratch: relative flux rms difference 0.031 %, BJD within
0.235 s, transit time the same within 0.1 min. (The first comparison differed by 0.72 % — that is how the centring
bug above was found.)

**O−C MCMC and two LTTE bugs (agent session 019Lu3, owner asked for a user-selectable MCMC as in OCFit).** O−C page:
"MCMC uncertainties" checkbox + steps (only for third body / apsidal; linear and quadratic are linear problems).
`fit_ltte(..., mcmc_steps=)` / `fit_apsidal(..., mcmc_steps=)` → `fit.mcmc = {"params": {name: (median, −, +)},
"acceptance"}`, errors = larger side, e/ω/f(m3)/U get errors too. Building it found two bugs in the third-body fit,
on the existing simulated test orbit (e 0.3, ω 120°): (1) all 25 least-squares starts stopped in neighbouring valleys
(ω 134°, χ² 115 against 79 at the truth) — now a grid over (e, ω, mean anomaly) with the linear (T0, P, A) solved
for each picks the starts (`_eccentric_starts`), recovers e 0.05–0.8 at any ω, and is faster; (2) the errors used
least_squares' two-point Jacobian, which carries the Kepler solver's noise: T3 error 4.4 d where MCMC and a central-
difference Jacobian give 35 d. `_covariance` now differentiates centrally with steps of 1 % of the rough error.
Not done: AAVSO report and standard magnitudes (need VizieR / APASS, blocked here); the ExoClock / ETD export from
the Models page with this light curve.

**T10 (ESO archive spectra done; agent session 019Lu3).** Data: ESO archive, reduced HARPS spectra (Phase 3 ADP)
of tau Ceti (HD 10700), six epochs 2003–2013. Query: TAP `https://archive.eso.org/tap_obs/sync` with
`SELECT dp_id, t_min, snr FROM ivoa.ObsCore WHERE dataproduct_type='spectrum' AND instrument_name='HARPS' AND
target_name='HD10700' AND snr > 150`; file: `https://dataportal.eso.org/dataportal_new/file/<dp_id>` (5 MB each).
Template: the Kurucz solar flux atlas (third campaign's table) written as a FITS spectrum 3800–6900 Å.
Found and fixed (test `tests/test_spectroscopy.py::test_eso_archive_spectrum_already_barycentric`, fails on the old
code): ESO's format is one table row whose cells are whole arrays (WAVE, FLUX, ERR) — they were read as 1 × N
arrays and the ERR column was ignored; the spectra carry `SPECSYS = 'BARYCENT'` (wavelengths already on the
barycentric scale) and would have been corrected a second time (up to 27 km/s for tau Ceti, BERV −27.5 on one epoch):
now not corrected again and the Velocity tab says so; ESO's site keywords (`ESO TEL GEOLAT / GEOLON / GEOELEV`,
east-positive) are read as the site for ESO spectra that are not yet barycentric.
Result: tau Ceti −16.058 km/s with a scatter of 0.006 km/s over the six epochs (CCF against the Kurucz Sun,
5000–6800 Å). Independent check by Gaussian centres of 16 Fe I lines against laboratory air wavelengths: tau Ceti
−16.22, the Kurucz Sun −0.16, difference −16.06 (identical). The HARPS pipeline value −16.68 differs by the known
template zero-point (gravitational redshift / convective blueshift of the template). Spectrum tools on the 313 109
points: opens in 0.2 s; equivalent widths Fe I 6173 62.0 ± 0.6 mÅ (direct integration 62.3), Fe I 6151 44.5 (44.8),
centres at the star's velocity. Not done: the spectral type of these spectra (the library download from
ssb.stsci.edu failed with an SSL error in this container, also with curl: the container's proxy or the server's
chain; it worked the day before); raw long-slit data of a small spectrograph (none found on Zenodo;
specreduce-data holds only reference files).
LAMOST (low resolution, R ≈ 1800, the level of a small spectrograph): `https://dr7.lamost.org/v2.0/spectrum/fits/<obsid>`
(gzipped FITS, e.g. obsids 101001–101070, plate F5902 of 2011-10-24; the server resets some connections when many
are fetched at once). Format: a 5 × N primary image (flux, inverse variance, wavelength, masks), log10-linear WCS
(DC-FLAG 1), `VACUUM = T`, `HELIO = T` (already heliocentric, HELIO_RV given), DATE-OBS = "the observation median
UTC". Found and fixed (tests in `tests/test_spectroscopy.py`): vacuum wavelengths were used as air (83 km/s) →
`spectrum_io._air` converts when VACUUM = T (only then: some amateur programs write CTYPE1 'WAVE' for air data);
HELIO = T is treated as already corrected like SPECSYS; a DATE-OBS whose comment says median / mid is the mid-time
(not + EXPTIME/2, 45 min here). **Main finding:** a template much finer than the spectrum was point-sampled at the
observed pixels and aliased (LAMOST against the Kurucz atlas: +21 instead of −42 km/s); `rv.match_template` now
smooths it to the spectrum's resolution (Gaussian of 2.5 observed pixels, only when the template is > 4× finer;
HARPS against the atlas is unchanged), for CCF, broadening function and TODCOR. Result on 13 LAMOST stars with
S/N > 20 (F6–K3): median difference to the LAMOST pipeline +2.5 km/s, robust scatter 1.7 km/s (LAMOST's own errors
≈ 7 km/s); one F6 at S/N 23 off by −20. MK types (libnor36 standards) against LAMOST's subclasses: 9 of 13 within
2 subclasses (G0→G0, F6→F6, K3→K4, G7→G8, G2→G0 ×3, …), three 5 subclasses off (two F9→G8, G7→K2) — not tuned
(owner's rule); worth a look with more stars and with MKCLASS's own rules (T7 follow-up).

**T4 (done; agent session 019Lu3).** Every automatic choice, how the user sees it and overrides it:

| Automatic choice | Shown | Overridden by |
|---|---|---|
| Suggested comparison stars | new: "{n} comparison stars suggested: similar brightness, near the target, unsaturated, no neighbour in the sky ring, inside every frame…" + rings on the image | clicking a star off / others on; Ctrl+Z |
| Radii from the star profiles | the radii, FWHM, S/N and light fraction in the result line, rings drawn | the three spin boxes |
| Variable apertures | off by default; tooltip warns about crowded fields | checkbox |
| Comparison weights | "Weights: C1 …" line | checkbox "Weight comparison stars by their scatter" |
| Detrending | "Detrended (k): scatter of the N points fitted a → b %"; refused with the reason when it would extrapolate | boxes, range, degree; "Undo detrending"; Ctrl+Z |
| Outlier clipping (Period page) | a step of its own, "outliers removed" in the source line | σ box; Ctrl+Z |
| Camera clock offset | Photometry page line "Times: camera clock − h" | Calibrate page setting |
| Dark optimisation | new: "Dark scaled by lo–hi (DARKSCAL in each file's header)" | checkbox (off by default) |
| Master that cannot be made | warnings box: which, from how many frames, why | — (frames) |
| Plate-solving for asteroid astrometry | "k frames could not be plate-solved and were left out" | choose solved frames |
| Arc lines matched from a reference / database | filled into the editable table, agreement stated | table edits, "left out" clicks; Ctrl+Z |
| Orders traced on the flat | drawn on the flat | click to delete / add |
| Barycentric site | "Barycentric correction for: site from the Plan page / file header (lat, lon)" | Plan page site |
| Spectra already barycentric (SPECSYS, HELIO) | new: "{n} spectra are already barycentric … not corrected again" | — (the file's statement) |
| Template smoothed to the spectrum's resolution | new: "The template was smoothed to the spectra's resolution" | choose a template of similar resolution |
| Vacuum → air | new: Velocity tab and Spectrum tools source line say so | — (the file's statement) |
| MK type / Pickles template | ranked list with scores, "suggestion" | template field |

**T10, amateur spectra (agent session 019Lu3).** ARAS Spectral Database (`https://aras-database.github.io/database/`,
star pages such as `agdra.html` link `spectra/asdb_<star>_<date>_<n>.fit`; terms: the observations stay their
observers' — used here only for testing, never committed). 30 reduced spectra of AG Dra (symbiotic, halo star,
γ ≈ −148 km/s) from 19 instruments: eShel, echelle9000, Alpy 600, LISA, LHIRES III, UVEX, StarEx (R 500–11000), BeSS
format (1-D image, CTYPE1 'Wavelength', JD-MID). All 30 are read. Found and fixed (tests `test_bess_amateur_spectra`,
`test_chunk_error_reflects_disagreeing_parts`): `BSS_VHEL` ≠ 0 means the heliocentric correction is already applied
(four spectra would have been corrected twice); the site in `GEO_LAT / GEO_LONG / GEO_ELEV` (and the BeSS
`BSS_LAT / BSS_LONG / BSS_ELEV` our own export writes) was not read, and 0, 0 means unknown, not a site; one spectrum
of 6578–8634 Å among 5000–5800 Å ones crashed the whole batch with a numpy message — it is now left out and named;
the formal CCF errors were 5–10× too small at R ≈ 500 — an empirical error from four wavelength chunks
(`rv.chunk_error`, as pipelines check order by order) is used when larger. Result (5000–5800 Å against the Kurucz
Sun): R ≥ 9000 spectra mostly −151 to −155 km/s (median of all −154), errors 0.5–5 km/s; R 500–1100 spectra scatter
−53 to −309 km/s with errors now 8–69 km/s (still several σ off for a few: an emission-line star at R 500 holds
little velocity information in that range; worth a note in the guide). Not done: raw amateur frames (none found).
Second pass: emission lines are set to the continuum before correlating with an absorption template
(`rv.mask_emission`, not when the template has emission itself; the page says in how many spectra) — the worst
AG Dra case went from −304 to −158 km/s; the empirical error is now a **jackknife** over four chunks (the whole
spectrum with one chunk at the continuum), because the chunks' own scatter overstated LAMOST errors tenfold
(telluric / arm-join chunks are far off alone but hardly move the whole). LAMOST: agreement unchanged (scatter 1.9
km/s), errors ~5 km/s; HARPS 14–48 m/s; ARAS R ≥ 9000 0.5–2 km/s. Several R ≈ 500 spectra stay 30–100 km/s off
with ±6–35 km/s: most likely their own wavelength calibration (1 Å = 55 km/s at 5500 Å), a data limit.

**T10, raw low-resolution long-slit night: ESO EFOSC2 (agent session 019Lu3).** The closest professional analogue of
a small spectrograph (R ≈ 300–1000). ESO raw frames are public without a login:
TAP `https://archive.eso.org/tap_obs/sync`, `SELECT ... FROM dbo.raw WHERE instrument='EFOSC' AND exp_start > '...'`
(dates as 'YYYY-MM-DD'), file `https://dataportal.eso.org/dataportal_new/file/<dp_id>` → `.fits.Z`. Night used:
PESSTO, 2018-12-31/2019-01-01 (5 biases 19:21–19:23, flats Gr#16 03:00–06:36, LTT 3864 in Gr#11/16/13 07:49–07:55,
He-Ar arc Gr#11 08:35). Reference identifications: the PESSTO pipeline (MIT,
`git clone --depth 1 https://github.com/svalenti/pessto`, `trunk/src/ntt/archive/efosc/arc/Gr11/Free/slit1.0/`:
reference arc + IRAF database, 9 lines He I 3888.7 … Ar I 7383.9). Found and fixed (tests `tests/test_lzw.py`,
`test_eso_raw_frames_are_classified_with_their_grism`, `test_wavelength_solution_degree_chosen_by_the_lines`):
- `.fits.Z` (Unix compress, how ESO and older archives deliver raw frames) could not be opened (astropy needs an extra
  package; installing it was refused here): `io/lzw.py` decodes it (written from the format's description, checked
  byte for byte against `gzip -dc` on four real frames, 0.3–0.5 s each); `readable()` in `read_image`,
  `masters.load`, `fits_copy`; the Calibrate scan decompresses `.fits.Z` into fits_from_raw; open dialogs list it.
- ESO frames have no IMAGETYP: `ESO DPR TYPE` is read (STD = science, WAVE = arc); the grism / grating
  (`GRISM`, `GRATING`, `DISPERSR`, `ESO INS GRIS1/GRAT1 NAME`) is part of the filter, so a Gr#16 flat is never used
  for a Gr#11 spectrum (before, all four flats would have been); binning from `ESO DET WIN1 BINX/Y` and `CCDSUM`.
- Wavelength solution: the degree was capped at n_lines // 4 (a quadratic for nine lines: 1–3 Å rms) and the Reduce
  tab offers no degree at all — now the lines choose it by leave-one-out up to 5 (the step's `order`), shown on the
  page; catalogue lines with a neighbour closer than the tolerance are not auto-matched (blended Ar lines at 4 Å/px).
  Result with the nine identified lines: 13 lines, 0.21 Å rms (PESSTO's own solution uses order 5).
- Flexure: the four Balmer lines of LTT 3864 all sit 3.1–3.7 Å blue (a constant shift in Å, not a velocity). Validated
  on a 45 min exposure of the same night (SN 2018kzr, Gr#11, `EFOSC.2019-01-01T04:06:59.255`): [O I] 5577, 6300, 6363
  are all −6.9 to −8.0 Å off — flexure since the arc. Done: `wavecal.sky_shift` (fit of the three [O I] lines in the
  extraction's sky bands; used when two agree within 3σ or one has S/N ≥ 15; each needs S/N ≥ 8, noise from the fit
  residuals) shifts the zero point in the Reduce step (`sky_lines=True`, checkbox "Zero point from the night-sky
  lines", status line says the shift or that the arc's zero point was kept; header WAVSKYSH). SN 2018kzr: −7.14 Å
  from 3 lines; LTT 3864 (80 s): no line strong enough, nothing shifted. Echelle step: not done.

**Benchmark against an IRAF pipeline (agent session 019Lu3, the owner asked for IRAF-level spectra).** ESO publishes
PESSTO's reduced spectra (IRAF-based pipeline) of the same EFOSC2 night: TAP `ivoa.ObsCore` with
`instrument_name='EFOSC' AND dataproduct_type='spectrum' AND t_min BETWEEN 58484 AND 58485` → SN 2018kzr
`ADP.2021-03-23T16:54:29.889` (from raw `EFOSC.2019-01-01T04:06:59.255`), AT 2018hyz `ADP.2021-03-23T16:54:29.601`
(raw `EFOSC.2019-01-01T08:03:09.038`); both carry WAVE, FLUX (flux-calibrated), BGFLUX (the sky). PESSTO trims about 99
columns off the start: their aperture centre 449.4 is our row 548. Our reduction of the same raw frames (bias, nine
He-Ar lines, sky zero point, optimal extraction) against theirs, on a 2.5 Å grid 4000–7300 Å:
SN 2018kzr feature correlation 0.84 (ratio ours/theirs smooth within 3.1 %), AT 2018hyz 0.88 (1.5 %), a different star
as control 0.00 (10 %); wavelength difference ours − PESSTO −1.0 and −1.1 Å (a quarter of a pixel). Night-sky lines
against the laboratory: ours +0.23, +0.15, −0.87 Å ([O I] 5577, 6300, 6363); PESSTO's sky −0.40, +1.62, +0.41 Å.
Added on the way: "Trace shape from row" (IRAF apall's reference aperture: a faint spectrum traced with a brighter
one's shape, `longslit.shifted_trace`), and the trace error now says so. Not compared: flux calibration (ours is not
flux-calibrated in this run).

**T1 (done).** Photometry page, Minimum tab: a box "What kind of minimum is it?" with two radio buttons,
"Eclipsing binary: Kwee–van Woerden method" (default) and "Exoplanet transit: trapezoid fit", a one-line note on
how to choose, a tooltip on each. `self.kvw` / `self.trapezoid` in `PhotometryPage`. The engine step
`timeseries.minimum` defaults to `method="kvw"` too (both automations set the method explicitly). Guide pages
01 and 06 in four languages updated. Test: `tests/test_ui.py::test_minimum_method_is_a_visible_choice_with_kvw_first`.

**T2 (done).** `ui/undo.py` gained `same()` (state equality that also compares numpy arrays) and
`track_typing(page, table, text)` (moved from `spectro_page.py`; changes made inside an `edit()` are part of that
step, not separate "typed" steps — `Undoable._editing`). Now in Ctrl+Z / Ctrl+Y: Spectrum tools (every change of
the spectrum, resampling, continuum points; the tab's own Undo button is the same stack; a newly opened spectrum
clears it), Plan (targets added, removed, typed, the Secondary box), Observe (exposure rows added, removed, typed,
their type / time / count / binning; a loaded sequence), Models (parameters typed, free / fixed, limb darkening,
the fitted values written into the table). Tests: `tests/test_undo.py` (8 tests, real key presses).
Not done (deliberately): the line-edit fields (they keep Qt's own Ctrl+Z while they have the keyboard).

**T3 (done).** Every control of the ten dialogs (exposure calculator, AAVSO report, BeSS export, observatory
set-up incl. its device rows, display levels, blink, transformation coefficients, asteroid astrometry, plugin step,
first-run welcome — English only there, the owner's rule) has a tooltip, translated.
`tests/test_tooltips.py::test_every_dialog_control_has_a_tooltip` keeps it so. Facts checked against the code
(e.g. the astrometry fits a straight motion, `photometry/moving.py`).

**T5 (done).** `calibration/masters.py::_layout`: the data section is the first *readable* of TRIMSEC, DATASEC
(LCO writes TRIMSEC = 'UNKNOWN'; before, DATASEC was then never looked at and nothing was trimmed), and
`_without_overscan()` cuts a BIASSEC strip off the side it is on when the data section covers it (FLOYDS:
DATASEC [1:2079,1:512], BIASSEC [2049:2079,1:512] → 512 x 2048 now). Test in `test_section_overscan_and_trim`.

**T6 (done).** New `spectroscopy/reidentify.py` (read before writing: IRAF `noao/onedspec/identify/iddb.x`,
`ecidentify/ecdb.x`, `identify/idshift.x`; PypeIt's shift-and-stretch reidentification idea).
- `read_database`: IRAF identify / ecidentify text databases (user wavelength, or the fit when INDEF; weight-0
  lines left out; IRAF's "features N" may exceed the lines written — read until the next keyword).
- **Key finding:** LCO's FLOYDS reference arcs (`floyds_pipeline/src/floyds/archive/<tel>/en06/arc/{red,blu}/<slit>/`)
  are *wavelength-resampled* 1-D spectra (red: CRVAL1 4850, CDELT1 2.956) and their databases' pixels are on that
  grid — that is why mapping them onto raw pixels "by a shift and scale" failed before. They are atlases.
  `from_reference` cross-correlates the night's arc with the reference over 400 dispersions (1/3 to 3x the
  reference step) and every shift, both axis directions (FFT, 0.3 s), then carries each database line to the
  nearest arc peak and refits (degree 1→3, tolerance 8→1.5 px). `shift_features`: databases on raw pixels (IRAF
  id_shift1: mode of peak − feature differences; the window is as wide as the number of lines).
- UI: Reduce tab **Lines from a reference arc / IRAF database…** (either file may be chosen; the other is found:
  `database/id<name>` ↔ `<name>.fits`), Echelle tab **Lines from an IRAF ecidentify database…** (needs the lowest
  order number; orders matched by absolute number). Both fill the table through `edit()` (Ctrl+Z), say how many
  lines were found and how well they agree, and warn when few agree. The user still checks and presses Solve.
- `reduce_step` / echelle: the user's identified wavelengths are added to the chosen line list (Hg lines of an HgAr
  lamp are in no list). `wavecal.solve`: the final fit uses as many terms as the lines carry (`len // 4`, at most
  the order): before, a cubic through 3-4 lines gave "rms 0.000".
- **Real FLOYDS result** (OGG 2026-10-27, BD+28 4211, red order, `ctiohear` + database lines): 13/13 database lines
  found (correlation 0.78), solution 17 lines, rms 0.143 Å (≈ 0.04 px). Independent check on the star: Hα minimum
  at 6563.0 Å (lab 6562.8), telluric O2 A band minimum at 7605.8 Å (band 7594–7621). Blue order: the HgAr lamp has
  only 4 lines there (database 4), 3 found, linear solution rms 1.9 Å — not enough lines for a good blue solution;
  the status says so. Tests: `tests/test_reidentify.py` (8). Guide 08 updated in four languages.
- Turkish terminology fixed on the way: echelle "order" is "mertebe" (as in the guide), not "düzen".

**T7 (done).** Read: MKCLASS paper (Gray & Corbally 2014, AJ 147, 80), its documentation and v1.07 C source
(`https://www.appstate.edu/~grayro/mkclass/`: mkclassv107.tar.gz, mklib.tar.gz, mkclassdoc.pdf). MKCLASS has no
licence (and Numerical Recipes code inside), so **nothing of it is copied or bundled**; building and running it
here was refused by the session's safety check (code from outside), so it was validated against published MK
types instead. New `spectroscopy/mkstandards.py`: the libnor36 MK standards (174 usable spectra, O6–M5, all
luminosity classes, 3800–5600 Å, 3.6 Å) are downloaded once from the authors' page (the server refuses Python's
default client name; the request says "astronomy-workbench (MK standards download)" — an honest name, not a
browser imitation), only `libnor36/t*l*p00.rbn` kept. Method = MKCLASS's matching step: smooth to 3.6 Å, standards
interpolated in temperature (running numbers) within each luminosity class, × quadratic response, ranked by rms.
- Benchmarks: leave-one-out on the standards with S/N 50 and a random response tilt: 86 % within one subclass,
  100 % within two, luminosity class 90 % exact (with a 61 Å local-continuum comparison instead: only 34 %).
  Pickles stars (inhomogeneous types, as Gray warns) 62 % within one subclass. TOFES: Sun G0 V (G2 V), Vega A0 V
  (A0 Va), Arcturus K1 III (K1.5 III) — the old Pickles ranking gave G0 III / A2 V / G8 V.
- `spectroscopy.classify` returns `mk` (ranked, with scores) and `mk_note` (why not: offline, outside 3800–5600 Å)
  besides the Pickles ranking that still chooses the RV template (it covers the red). Velocity tab shows both;
  the MK line says it is a suggestion. Guide 08 (four languages), THIRD_PARTY.md, tests `tests/test_mkstandards.py`.
- MKCLASS's rule-based refinement, part done (agent session 019Lu3, from Gray & Corbally 2014 sections 3.4 and the
  MKCLASS documentation, `https://www.appstate.edu/~grayro/mkclass/mkclass.pdf`, `mkclassdoc.pdf`; no code copied):
  (1) the quality word MKCLASS gives (excellent / vgood / good / fair / poor) from the match score, thresholds from
  the library itself (every third standard left out with noise: score ≈ sqrt(0.012² + (1/SNR)²)); (2) for B9–F5 stars
  the separate types from the Ca II K line, the hydrogen lines and the metal lines (each region compared alone with
  the standards, within ±6 running numbers of the overall type, as a classifier brackets), with the hints "Am" (metals
  ≥ 3 later than hydrogen, K earlier than metals) and "metal-weak" (K and metals ≥ 3 earlier). Validated: 0 of 23
  normal A–F standards (left out, S/N 50) get a hint; synthetic Am (kA1 hA2 mF0) and metal-weak (kA0 hA5 mA0) stars are
  recognised. (3) Lines of peculiar stars, each measured in the star and in its best standard over the same continuum:
  Sr II 4077 and Si II 4128-30 for B9–F5 (Ap), Ba II 4554 for G5–K5 giants (barium stars); flagged above 0.35 Å
  excess (normal standards: scatter 0.07–0.10 Å, max 0.29 Å). Validated: 0 of 174 standards flagged, +0.5 Å lines found.
  Tests in `tests/test_mkstandards.py`.
  (4) Luminosity of G5–M stars from the gravity-sensitive lines (Gray & Corbally 2009: Sr II 4077, 4216, Ca I 4226,
  the 4172–79 blend, Y II 4376 / Fe I 4383, Mg b, MgH 4780) at the fitted temperature type: late standards left out
  (S/N 50 and 20) right in 47 of 56 against 45 from the whole-spectrum match (mixing both scores did worse).
  (5) CN / CH (owner asked for a better method than equivalent widths, whose scatter on normal standards was 3–4 Å):
  the star divided by its best standard — fitted with 4140–4340 Å left out, so a strong band does not pull the type —
  band against continuum over the Lick windows CN1 and G4300. Normal giants: CN 0.985 ± 0.032 (never < 0.917), G band
  0.998 ± 0.014 (never < 0.971); limits 0.87 and 0.945. 0 of 174 standards flagged; G band 10 % deeper found in
  25 of 35 G0–K7 IV–I stars, CN 20 % deeper in 17 of 35 (the rest: the deep band makes the star look like a dwarf
  or too faint in the blue). Hints, never applied.
- Follow-up done (agent session 019Lu3): the Velocity tab draws the star over the best MK standard after "Spectral
  type…" (the user judges the suggestion by eye, as MK classification is done); the standard is drawn only where it
  has flux. The MK type no longer fails when the Pickles library cannot be downloaded (it did in this container,
  SSL error from ssb.stsci.edu): the page shows the MK type and says to choose a template. Test:
  `test_mk_suggestion_is_drawn_and_survives_without_the_template_library`.
