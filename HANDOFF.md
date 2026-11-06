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

Agent session 01RxUU stopped on 2026-11-04 because the owner's weekly quota ended. State at that moment:

- `main` = `0108d6e`, everything on it passed `tools/precommit.sh` (580 passed, 3 skipped) and is pushed.
  CI: run for `d180798` green; later runs (`7cd4187` … `0108d6e`) were not yet checked — check them first
  (GitHub MCP `actions_list` → `list_workflow_runs`, branch main). No release was made (only after asking the owner).
- **Unfinished task T11 (paper-quality output) is on branch `wip-t11-results-export` (commit `2d57cb3`, pushed,
  one commit on top of `0108d6e`; NOT merged, NOT passing precommit yet because its new strings are untranslated).**
  To continue: `git fetch origin wip-t11-results-export && git checkout -b t11 origin/wip-t11-results-export`, finish
  the list below, run precommit, then fast-forward `main` to it (`git checkout main && git merge --ff-only t11`) and
  push `main`. Delete the wip branch after.
  - DONE in that commit:
    1. `ui/export.py`: `rounded(value, error)` (error to 2 significant digits, value to the same decimal place),
       `save_results(path, rows, caption)` (rows = (parameter, value, error|None, unit); `.tex` → a LaTeX `table`
       with caption + booktabs tabular, values as `$v \pm e$`; otherwise CSV with a `# caption` first line), and
       `results_button(parent, rows_and_caption)` (a QPushButton "Export results (CSV / LaTeX)…"; its texts use
       `QCoreApplication.translate("Export", …)`).
    2. `ui/spectro_page.py` (VelocityTab): `show_orbit` now draws velocities + model curves + γ line on top and an
       **O−C (km/s) residual panel** below (2 rows, shared x, height ratio 3:1, hspace 0; secondary in orange), keeps
       `self.orbit_result`; new `orbit_table()` → rows (P, T_peri, e, ω, K1, γ, and K2, q, M1/M2 sin³i, a sin i, rms
       for SB2; f(m), a1 sin i, rms for SB1) + caption ("Keplerian least-squares … errors from the covariance
       matrix (e and ω from its draws)" — true, see `spectroscopy/orbit.py` lines 84-110); results button under
       "Fit orbit". Checked visually: `/tmp/claude-0/real/t11_orbit.png` (looked right: two orbits, residuals).
    3. `ui/workspaces.py` (OCPage): `self.fit_result`, `fit_table()` for linear / quadratic (T0, P, Q, dP/dt),
       light-travel time (T0, P, A in min, P3 in yr, T3, e3, ω3, f(m3)) and apsidal motion (T0, Ps, e, ω0, dω/dE,
       U), + χ²ᵣ; caption says weighted least squares, errors scaled by √χ²ᵣ when > 1 (true: `timeseries/ephemeris.py`,
       `oc_models.py::_covariance`); results button under "Fit and draw O-C".
    4. `tests/test_sb2.py::test_velocity_tab_shows_sb2` checks the residual panel and a PDF export (passes).
  - LEFT TO DO for T11 (in this order):
    a. ModelsPage (`ui/models_page.py`, `show_fit` stores `self.result = r`): add `fit_table()` from `r["params"]` /
       `r["errors"]` (only the free ones have errors; names in `models/fit.py::NAMES`: period, t0, r_sum, k, incl, j,
       ecosw, esinw, l3), `r["derived"]` / `r["derived_err"]` (r1, r2, e, omega, light_ratio), `r["absolute"]`
       (m1, m2, r1, r2, a, logg1, logg2 with *_err) and `r["transit"]` (tc, tc_err, depth, t14); caption: "two
       limb-darkened spheres on a Keplerian orbit (EBOP/JKTEBOP approximation); errors from the covariance, or from
       MCMC when ticked" (check `models/fit.py` for which); add `results_button(self, self.fit_table)` into the
       buttons grid (two per row).
    b. Run `python tools/i18n.py update`, translate the new strings (list them with the snippet in "How the
       translations were done" below), `python tools/i18n.py`.
    c. Tests: `rounded` (e.g. (1.234567, 0.000123) → ('1.23457', '0.00012'); (12.3, None) → ('12.3', '')),
       `save_results` both formats, `fit_table` of OCPage after a linear fit, ModelsPage table after `show_fit`.
    d. Period page light curve (`workspaces.py` ~line 3057 `ax.set_xlabel(self.tr("Time"))`): label with the time
       scale and offset as the Photometry plot does (`f"{lc['time_scale']} − {t_ref:.0f}"`), plot errors if known.
    e. Frequency page (`ui/frequency_page.py` ~166): amplitude axis with its unit (mag or relative flux).
    f. Then precommit, merge to main, update this board (T11 DONE) and push.

- **Owner's newest wish (not done yet, task T13 below):** for technical terms keep the English word next to the
  Turkish one where Turkish astronomers also say it in English, e.g. "order/mertebe" (owner: "türkçede de order
  diyoruz … order/mertebe şeklinde olsun"). Apply to the Turkish translations (`src/astrowb/resources/i18n/app_tr.ts`)
  and the Turkish guide (`resources/guide/tr`): echelle order → "order/mertebe"; consider also blaze, flat, bias,
  dark, light, arc (already kept in English), FWHM, seeing ("seeing/görüş"), airmass ("airmass/hava kütlesi"),
  detrend. Do it consistently (grep the .ts translations), then `python tools/i18n.py`.

### Tools and files the last agent used (all in the ephemeral container; recreate if needed)

- Scratchpad `the session scratchpad (`/tmp/claude-0/<project>/<session>/scratchpad/`)`: `tips/apply.py` (inserts
  `x.setToolTip(self.tr("…"))` after an anchor line; input blocks: `file | anchor | target` then EN, TR, DE, ES
  lines; writes a TSV), `fill3.py <tsv>` (fills unfinished tr/de/es entries in the three .ts files from lines
  `English<TAB>Türkçe<TAB>Deutsch<TAB>Español`; the English must equal the source text exactly), `wt/` a git
  worktree used to run the full precommit on a commit while working on the next (`git worktree add --detach wt
  <commit>`; run with `PYTHONPATH=wt/src`, since the venv's package is an editable install of the main checkout).
- How the translations were done: `. .venv/bin/activate; python tools/i18n.py update`; list unfinished entries with
  `python -c "import re;s=open('src/astrowb/resources/i18n/app_tr.ts',encoding='utf-8').read();[print(m.group(1)) for m in re.finditer(r'<source>([^<]*)</source>\s*(?:<comment>[^<]*</comment>\s*)?<translation type=\"unfinished\">',s)]"`;
  write the TSV, `python fill3.py x.tsv`, then `python tools/i18n.py` (must say "… finished and 0 unfinished").
  Turkish terms in use: mertebe (order), kalibre, ark, flat, bias, dark, light, açıklık (aperture), mukayese
  yıldızı (comparison), kontrol yıldızı (check), periyot (Period search names), sönükleşme…
- `/tmp/claude-0/real/`: `harness.py` (drives the real main window: every dialog/exception collected, `wait()` for
  tasks, real clicks), `audit_ui.py` (controls without tooltip per page + every checkbox default), `audit_dialogs.py`
  (same for the ten dialogs), `t6/arcs.py`, `t6/proto.py`, `t6/check.py`, `t6/gui.py` (FLOYDS reidentify session),
  `t7_proto.py`, `t7_bench.py`, `t7_loo.py`, `t7_tofes.py` (MK classification prototypes and benchmarks),
  `t11_orbit.py` (renders the RV orbit publication figure).
- Run any Qt script with `QT_QPA_PLATFORM=offscreen`; driving scripts need `if __name__ == "__main__":` (spawn).

### Data and sources downloaded in this round (all outside the repository; never commit them)

| What | From | Used for / result |
|---|---|---|
| LCO FLOYDS pipeline (reference arcs + IRAF databases per telescope/arm/slit) | `git clone --depth 1 https://github.com/LCOGT/floyds_pipeline` → `src/floyds/archive/ftn/en06/arc/{red,blu}/<slit>/` (`ftn_red_2.0.fits` + `database/idftn_red_2.0`, `ftn_blue_2.0.fits` + `database/idftn_blue_2.0`) | T6. Reference arcs are wavelength-resampled 1-D spectra (red CRVAL1 4850, CDELT1 2.956; blue 3300, 1.687) |
| IRAF source (sparse) | `/tmp/claude-0/ref/iraf/iraf` (git clone --sparse https://github.com/iraf-community/iraf; `git sparse-checkout add noao/onedspec/ecidentify noao/onedspec/identify noao/twodspec/apextract`) | read `identify/iddb.x`, `ecidentify/ecdb.x`, `identify/idshift.x` (database formats, id_shift1) |
| FLOYDS raw frames (OGG 2026-10-27) | LCO archive API (see the table of the third campaign) in `/tmp/claude-0/realdata/floyds/` | T5 trimming, T6 end-to-end (red: 13/13 lines, rms 0.143 Å; Hα 6563.0 Å; O2 A band 7605.8 Å) |
| MKCLASS v1.07 source, documentation, paper | `https://www.appstate.edu/~grayro/mkclass/` : `mkclassv107.tar.gz`, `mklib.tar.gz` (libraries libnor36, libr18, libr18_225/27/30, libr36), `mkclassdoc.pdf`, `mkclass.pdf` (Gray & Corbally 2014, AJ 147, 80) → `/tmp/claude-0/src_ref/mkclass/` | T7. No licence in the source (+ Numerical Recipes code): nothing copied/bundled. Building/running it was refused by the session's safety check. The server answers 403 to Python's default User-Agent; the application sends "astronomy-workbench (MK standards download)" |
| Pickles library (131 FITS) | `https://ssb.stsci.edu/cdbs/grid/pickles/dat_uvk/pickles_uk_{1..131}.fits` → `/tmp/claude-0/realdata/pickles/` (also holds `mk_libnor36/` after a test run) | T7 benchmark (Pickles types are inhomogeneous: 62 % within one subclass) |
| NutMaat 0.1.1 wheel (Python MK classifier, 2025, arXiv 2501.17698) | `pip download --no-deps nutmaat` → `/tmp/claude-0/src_ref/nutmaat/` | downloaded, NOT yet read — worth reading for MKCLASS's rule-based refinement (T7 follow-up) |
| TOFES merged spectra (Sun, Vega, Arcturus) | made in the third campaign: `/tmp/claude-0/realdata/tofes_out/*_1d.fits` | T7: Sun G0 V, Vega A0 V, Arcturus K1 III |

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
| U6 | Heavy use test, page by page, as an astronomer (every button, tooltip, text, dialog, menu, language, theme), with timings: U6a Start, U6b Plan, U6c Observe, U6d Calibrate, U6e Images, U6f Photometry, U6g Light curves & O−C, U6h Spectroscopy, U6i Orbits & models, U6j Remote sensing, U6k Automation, U6l Project, U6m Guide, U6n menus / settings / dialogs | CLAIMED (session 019Lu3, 2026-11-05): automatic sweep DONE in 4 languages; real-data use per page in progress |
| U7 | Every feature on new real data from the internet (list in the notes; record sources) | open |
| U8 | Raw vs published processed data: U8a LCO raw (e00) vs BANZAI-reduced (e91) frames and photometry; U8b ESO raw echelle (HARPS / FEROS) vs ESO's reduced spectra; U8c TESS FFI photometry vs the SPOC light curve; U8d IRAF installed here: the same raw long-slit and photometry reduced in IRAF vs here; U8e times of minimum vs published | CLAIMED (session 019Lu3, 2026-11-06): U8a, U8c, U8d, U8e DONE; U8b (ESO echelle raw vs reduced) open |
| U9 | Speed: every operation timed (speed log below), slow ones fixed and measured again | IN PROGRESS (speed log below; period search fixed) |
| U10 | Re-run the tests touched by every fix; CI green | open |
| U11 | Basic / Expert interface mode (chosen on the Start page, changeable later; settings stay where they are, only folded) — postponed by the owner, do not forget | postponed |

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
**Environment note (agent container only):** the container's CA bundle lacks STScI's root (emSign); Python
scripts here use `scratchpad/ca-all.pem` (container bundle + certifi) via `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`.
Users are not affected (certifi has it).

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
| Calibrate: scan 91 raw LCO frames | 30 bias, 20 darks, 40 lights, 1 master flat | 3.3 s | fine |
| Calibrate: masters + 40 lights (2400 x 2400, compressed) | same | before 110 s, now 18.4 s (IRAF ccdred 11 s) | the full-chip masters no light needed are skipped |

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

### How to do the remaining tasks (suggestions of the last agent)

- **T4 user-control review:** go page by page with `/tmp/claude-0/real/harness.py` (or a new script) and list each
  automatic choice: suggested comparison stars (Photometry), automatic apertures ("Choose the radii from the star
  profiles"), outlier clipping (Period search), arc line auto-matching (Reduce / Echelle: the line list after the
  user's identifications), order tracing on the flat, template choice (Pickles best → RV template), BJD site from
  the header (velocities), camera clock offset, dark scaling. For each: is it shown, explained (tooltip/status), and
  can the user override it? Fix the gaps; write the list here.
- **T8 error messages:** `tests/test_messages.py::test_every_engine_error_has_a_template` already forces a
  template for every engine `raise`. Remaining: messages raised in `ui/` code (QMessageBox texts, status texts)
  — check that each says what happened and what to do; check `translate()` is applied to engine texts shown in
  the UI (grep `str(e)` in `src/astrowb/ui/*.py`; several places show `str(e)` without `translate`).
- **T9 real ground photometry:** needs a public multi-frame night (e.g. LCO archive public imaging of a known
  eclipsing binary or exoplanet transit: `https://archive-api.lco.global/frames/?RLEVEL=91&public=true&OBJECT=…`;
  check the BANZAI-reduced e91 frames). Run calibrate (or use e91), photometry, minimum (KvW), AAVSO export;
  compare the minimum with the literature ephemeris. CDS (VizieR) and AAVSO were blocked from the container.
- **T10 simple long-slit / archive spectra:** ESO archive 1-D (ADP) spectra or LAMOST DR spectra through RV,
  line measurement and the new MK type; specreduce-data has raw long-slit sets.
- **T7 follow-up (optional):** read NutMaat (wheel above) and the MKCLASS paper's rules (Ca II K, hydrogen,
  G band, Mg b luminosity criteria) to add peculiarity hints; draw the star over the best MK standard (the step
  returns `mk_model`).
