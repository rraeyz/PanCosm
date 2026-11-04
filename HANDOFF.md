# Handoff: full test & fix campaign (state on 2026-11-04)

Notes for whoever continues the work. The owner speaks Turkish: answer in Turkish; code, comments
and commits in English. Delete this file once the work is finished.

## The owner's request

- Test the application from top to bottom: every feature, every button, every menu, with real data.
- It must work with **any** data, not only the owner's (MaxIm DL files from the TUG T100 telescope):
  phone pictures (JPEG/PNG/TIFF), DSLR raw, cubes, compressed FITS, odd headers, other observatories.
- Problems that only show up on one distribution (Arch / CachyOS) must be fixed too. The owner also tests on Windows.
- Push straight to `main`. A new release only after CI is fully green, and only after asking the owner.
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
| T1 | Minimum tab: both methods visible as a clear choice, Kwee–van Woerden (eclipsing binaries) the default | CLAIMED by agent session 01RxUU (2026-11-04) |
| T2 | Undo / redo for the remaining editors: Spectrum tools (into Ctrl+Z), Plan targets, Observe exposure rows, Models parameters | TODO |
| T3 | Tooltips in the dialogs (exposure calculator, AAVSO, BeSS, observatory set-up, levels, blink, coefficients, moving objects, plugins) with a test | TODO |
| T4 | User-control review, page by page: every automatic choice visible, explained, overridable | TODO |
| T5 | FLOYDS-type headers: TRIMSEC 'UNKNOWN', DATASEC that includes the BIASSEC columns | TODO |
| T6 | "Load identifications from an IRAF database" (Reduce and Echelle tabs) + reidentify-style shift search; FLOYDS wavelengths end to end | TODO |
| T7 | Spectral classification checked against MKCLASS (Gray & Corbally) / iSpec; shown as a ranked suggestion with scores | TODO |
| T8 | Error messages (old task 38): every message says what happened and what to do, in all four languages | TODO |
| T9 | Real ground photometry time series through the whole Photometry page, AAVSO export, standard magnitudes | TODO |
| T10 | Real long-slit data of a simple spectrograph; reduced archive spectra (ESO / LAMOST) through RV and line tools | TODO |
| T11 | Paper-quality output: every result exported as a figure (vector, error bars, labelled axes, units) and a table with uncertainties (CSV and LaTeX); a reviewer can reproduce it | TODO |
| T12 | CI green for the latest commits; a release only after asking the owner | ongoing |

### Notes per task

(Each agent adds its notes here under the task number.)

## Earlier "next steps" list (kept for its details; superseded by the task board)


1. **Long slit, curved traces (FLOYDS) — DONE (commit after `331d620`):** read first: IRAF apextract `aptrace.x`
   (`git clone --sparse https://github.com/iraf-community/iraf`, `noao/twodspec/apextract`: steps of `step`
   columns summing `nsum`, each centre found from the previous one with `center1d`, lost after `nlost` steps, then
   an interactive Legendre fit) and specreduce 1.9 `FitTrace` (fixed window around one guess, so it does not follow
   a bend either). `longslit.trace` now does what aptrace does; the Reduce tab has **Spectrum at row** (0 = the
   brightest) so the user chooses which spectrum, and the traced line with the aperture is drawn on the frame under
   the plots, so the user checks it (as aptrace shows its fit). Both FLOYDS orders are followed (within 1 px of the
   ridge over the illuminated part); the extracted blue order of BD+28 4211 shows its Balmer lines.
   Still open for FLOYDS: TRIMSEC 'UNKNOWN' and a DATASEC that includes the BIASSEC columns (trim the overscan strip
   off the data section); wavelengths. **The LCO FLOYDS pipeline** (`git clone https://github.com/LCOGT/floyds_pipeline`,
   `src/floyds/archive/<tel>/en06/arc/{red,blu}/<slit>/`) keeps, per telescope, arm and slit width, a reference arc
   spectrum and an IRAF `identify` database (`database/idftn_red_2.0`: pixel, fitted and user wavelength, line name;
   Hg 5460.75 and Ar I lines) — exactly the instrument "atlas" the owner remembers. Their pixels are on their
   rectified, trimmed frame, so they do not map onto ours by a shift and scale (tried). Idea to discuss with the
   owner: **"Load identifications from an IRAF database"** in the Reduce / Echelle tabs, filling the editable table
   of identified lines (the user checks and corrects them; a shift search like IRAF reidentify as an option).
2. **Spectral classification:** read MKCLASS (rules on line ratios at a known resolution) and iSpec; decide with
   the owner whether to show it only as a ranked suggestion with scores (keep the user's choice of template).
3. **User control review, page by page** (owner: nothing silently automatic): list every automatic choice
   (suggested comparison stars, automatic apertures, outlier clipping, line auto-identification, order tracing,
   template choice, BJD site from the header) and make sure each is visible, explained and can be overridden.
4. Long-slit real data with a simple spectrograph (LHIRES / Alpy-like amateur data, or another public archive);
   ESO / LAMOST reduced spectra for the RV and line tools.
5. Photometry with real ground data and many frames (the two Zenodo nights have only 1-2 science frames): a
   public time series (e.g. LCO or an AAVSO-style night) through the whole Photometry page, the AAVSO export and the
   standard magnitudes (needs CDS, blocked here).
6. CI: confirm green for the latest commits. Release only after asking the owner.
7. Undo / redo for the remaining editors (Spectrum tools into the same Ctrl+Z; Plan / Observe / Models tables).
