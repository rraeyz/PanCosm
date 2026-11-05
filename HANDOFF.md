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
| T4 | User-control review, page by page: every automatic choice visible, explained, overridable | TODO |
| T5 | FLOYDS-type headers: TRIMSEC 'UNKNOWN', DATASEC that includes the BIASSEC columns | DONE (see notes) |
| T6 | "Load identifications from an IRAF database" (Reduce and Echelle tabs) + reidentify-style shift search; FLOYDS wavelengths end to end | DONE (see notes) |
| T7 | Spectral classification checked against MKCLASS (Gray & Corbally) / iSpec; shown as a ranked suggestion with scores | DONE (see notes) |
| T8 | Error messages (old task 38): every message says what happened and what to do, in all four languages | DONE (see notes) |
| T9 | Real ground photometry time series through the whole Photometry page, AAVSO export, standard magnitudes | CLAIMED by agent session 019Lu3, 2026-11-05 |
| T10 | Real long-slit data of a simple spectrograph; reduced archive spectra (ESO / LAMOST) through RV and line tools | TODO |
| T11 | Paper-quality output: every result exported as a figure (vector, error bars, labelled axes, units) and a table with uncertainties (CSV and LaTeX); a reviewer can reproduce it | DONE (see notes) |
| T12 | CI green for the latest commits; a release only after asking the owner | ongoing |
| T13 | Turkish terms as "English/Türkçe" where both are used (order/mertebe, seeing/görüş, airmass/hava kütlesi…), translations and guide | DONE (see notes) |

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
error bars on the Period page (it keeps no errors); the guide does not mention the export button yet.

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
- Not done: MKCLASS's rule-based refinement (line-ratio criteria, peculiarity flags such as Am/Ap/Ba); a plot of the
  star over the best standard (the step already returns `mk_model` for it).

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
