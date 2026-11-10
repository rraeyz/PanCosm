# Architecture, quality, performance, packaging: plan

Read `PLAN.md` first, all of it. This file is the foundation every other plan file builds on.

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, this file's "Conventions" and "Definition of done", your area file, and `plans/interface.md` before
   you touch anything the user sees.
2. Claim the step in its file and push before starting (English or Turkish); one step at a time; push at least
   hourly; mark it done with the commit.
3. First search the code: reuse or improve what exists, never write it twice. Question the step: if a bullet is
   wrong, do what is right, write why under the step and tell the owner (no approval needed).
4. Research first (papers, reference programs' source); learn, never copy; nothing GPL bundled.
5. Synthetic test with known truth **and** real data against a reference; the reference numbers become a test.
6. Use the program as a user (real clicks, screenshots in four languages, looked at) before calling it done.
7. Only kit components in the interface; workflow first; one primary action; tooltips; undo; nothing locked.
8. Errors by code, saying what happened and what to do, translated into Turkish (German and Spanish wait for ARC-25,
   PLAN.md R0). Guide updated in English and Turkish.
9. Measure time and memory; meet the budget; CPU and GPU paths give the same result.
10. Commits in the owner's name only, no "Claude" anywhere; everything to `main`; never delete without the owner.

## Scope and goal

Everything that is not one area's science: the structure of the code, the shared layers (state, plots, images,
tables, errors, services, profiles), native and GPU kernels, the scripting surface, provenance, tests, speed,
packaging and documentation. The goal: an agent working on any area finds one obvious way to do each common thing,
and a user finds every window behaving the same.

## Conventions (binding for all code)

### Layout of the package (target; reached by ARC-4)

```
src/astrowb/
  core/            state.py (session state, undo), errors.py (AppError codes), units.py, provenance.py, profiles.py
  engine/          steps, tasks, project, plugins, automation (as today)
  services/        catalogues and archives: one module per service + cache.py, mirrors.py, offline.py
  compute/         GPU kernels (wgpu) with NumPy twins
  _native          compiled Rust module (built from /native); every function has a NumPy twin in its area
  calibration/ photometry/ timeseries/ spectroscopy/ models/ exoplanets/ planning/ devices/ astrometry/
  images/ (today io/ + overlays + display) remotesensing/
  api/             the stable scripting surface (ARC-12): thin functions over the steps
  ui/
    kit/           the component kit (plans/interface.md UI-3): no area code may bypass it
    plot/          FigureSpec, PlotView (pyqtgraph), publish (Matplotlib)        (ARC-6)
    image/         ImageView with tiles, overlays, tools                          (ARC-7)
    shell/         application start, start window, menus, tasks, settings, help
    <area>/        window.py, controller.py, state.py, panels/*.py, dialogs/*.py  (one package per area window)
  resources/       brand, i18n, guide, icons, linelists, automations, data tables
native/            Rust crate (Cargo.toml, src/*.rs), built by maturin
tests/             test_<area>_*.py; tests/validation/ (real-data reference tests); tests/ui/ (window walks)
tools/             precommit, i18n, screenshots, speed, licence and brand checks, module sizes
```

### Code rules
- **Engine code** (everything outside `ui/`): no Qt import; pure functions on arrays and plain values; a step
  wrapper in `<area>/steps.py`; reachable from `astrowb.api`.
- **Sizes:** no interface module above 700 lines, no engine module above 900, no function above 80 lines
  (`tools/module_sizes.py`, checked in precommit; today's large files are on a shrinking allow-list, ARC-4).
- **Arrays:** images are `[y, x]`, row 0 at the bottom as FITS; pixel centres on integers, 0-based in code, 1-based
  only in what the user reads when FITS convention is expected (the label says so). Spectra: wavelength ascending.
- **Units and standards in names and docstrings:** `t_bjd_tdb`, `wave_air_angstrom`, `v_bary_kms`, `flux_adu`,
  `flux_e`. A function never guesses a unit.
- **Times** float64 days; never float32; GPU kernels receive times relative to a float64 reference.
- **Randomness:** `np.random.default_rng(seed)`; the seed is a parameter and is recorded.
- **Errors:** raise `core.errors.AppError(code, **values)` for everything a user can meet (ARC-13); plain
  exceptions only for programming errors.
- **Steps:** identifiers `area.name` are permanent. Parameters have defaults; new parameters are optional. Outputs
  are plain JSON-able values or paths. A step reports progress through `ctx.progress(fraction, code)` and checks
  `ctx.check()` at least once per second of work.
- **Files written:** FITS with full provenance cards; tables as ECSV (Astropy) and CSV; figures through
  `ui/plot/publish`. Never overwrite an input. Atomic writes (temporary name, then rename).
- **Settings keys, session fields, file formats:** additive changes only, with a migration and a test.
- **Imports:** heavy libraries inside functions where start-up time matters (the start window must show in under
  one second); `tests/test_startup.py` guards the import list.
- **Style:** ruff (line length 120), type hints on public functions, no commented-out code, comments say why.

### Interface rules (short; the full set is in `plans/interface.md`)
- A window = `ui/<area>/window.py` (assembly only) + `controller.py` (signals → steps → state) + `state.py`
  (dataclasses) + panels that read the state and send intents to the controller. Panels never call steps.
- Every string through `self.tr`; contexts are class names; no translation by variable context.
- Long work never on the GUI thread: steps through `run_step`, light work through `QThreadPool` helpers in
  `ui/shell/work.py`.

## Use what exists: libraries and their pieces (binding: look here before writing your own)

Checked on 2026-11-10 against the installed versions (Astropy 8.0, photutils 3.1, SciPy 1.18, specreduce 1.9,
ccdproc 2.5). A step that needs one of these uses it, or writes under the step why it cannot (accuracy, speed,
a missing case) and keeps the library call as the reference twin in its test.

| Need | Already bundled | Used by |
| --- | --- | --- |
| Empirical PSF, PSF and grouped photometry, flags | `photutils.psf`: `EPSFBuilder`, `ImagePSF`, `MoffatPSF`, `GaussianPSF`, `PSFPhotometry`, `IterativePSFPhotometry`, `SourceGrouper`, `PSF_FLAGS`, `fit_fwhm`, `fit_2dgaussian` | PHO-18, PHO-29, IMG-3, AST-3, AST-8 |
| Radial profile, curve of growth (also elliptical) | `photutils.profiles`: `RadialProfile`, `CurveOfGrowth`, `EllipticalCurveOfGrowth` | IMG-3, PHO-28, PHO-22 |
| Aperture shapes with exact overlap; statistics in an aperture | `photutils.aperture`: `CircularAperture`, `EllipticalAperture`, `RectangularAperture`, `PolygonAperture`, annuli, `ApertureStats` | PHO-22, IMG-3, IMG-6 |
| Background maps; the DAOPHOT "MMM" mode estimator | `photutils.background`: `Background2D`, `MMMBackground`, `LocalBackground`, biweight estimators | IMG-5, IMG-7, PHO-45 |
| Detection, deblending, source catalogue | `photutils.segmentation`: `SourceFinder`, `deblend_sources`, `SourceCatalog` | IMG-5, IMG-4, PHO-30 |
| Isophotes | `photutils.isophote`: `Ellipse`, `build_ellipse_model` | PHO-39 |
| Lomb–Scargle (fast, floating mean, multi-term), multi-band, box least squares, false-alarm levels | `astropy.timeseries`: `LombScargle`, `LombScargleMultiband`, `BoxLeastSquares` | PER-3, PER-4, PER-13 |
| Robust statistics: sigma clipping, biweight location / scale, Bayesian blocks, bootstrap | `astropy.stats` | PER-2, CAL-5, IMG-3 |
| Times, barycentric and heliocentric corrections, velocity corrections | `astropy.time`, `Time.light_travel_time`, `SkyCoord.radial_velocity_correction` | ARC-15, SPE-14 |
| Data with variance and mask; cut-outs; block reduce | `astropy.nddata`: `NDData`, `VarianceUncertainty`, `Cutout2D`, `block_reduce` | CAL-13, IMG-14 |
| WCS fitting with SIP; WCS axes for figures | `astropy.wcs` (`fit_wcs_from_points`), `astropy.visualization.wcsaxes` | AST-1, AST-3, IMG-16 |
| Stretches and intervals, Lupton RGB | `astropy.visualization`: `ZScaleInterval`, `AsinhStretch`, `make_lupton_rgb` | IMG-2, IMG-7 |
| Tables to ECSV, VOTable, LaTeX (AASTeX), HTML | `astropy.table.Table.write` (`ascii.ecsv`, `votable`, `ascii.aastex`, `ascii.latex`) | ARC-8 |
| SAMP hub and client | `astropy.samp` | IMG-12, SPE-12 |
| Nominal solar and physical constants (IAU 2015) | `astropy.constants` | MOD-15, EXO-4 |
| Catalogue and archive protocols | `astroquery` (SIMBAD, VizieR, Gaia TAP, MAST incl. TESScut, Exoplanet Archive, Horizons, MPC, IRSA, ESO) — always behind `services/` (ARC-14) | every area |
| Global and local optimisers; splines; signal tools | `scipy.optimize` (`differential_evolution`, `least_squares`), `scipy.interpolate`, `scipy.signal`, `scipy.ndimage` | MOD-12, OC-6, PER-2, IMG-7 |
| Ensemble MCMC | `emcee` (kept as the alternative sampler) | EXO-5 |
| Cosmic rays (L.A.Cosmic) | `astroscrappy` | CAL-12 |
| TIFF / GeoTIFF, projections, HDF5, raw decoding | `tifffile`, `pyproj`, `h5py`, `rawpy` | RS, IMG-1 |

For reading and for reference twins in tests only (development dependencies, not bundled today): **specreduce**
(BSD; modules `tracing`, `background`, `extract` (boxcar, Horne), `tilt_solution`, `tilt_correction`,
`line_matching`, `wavecal1d`, `fluxcal`) — read before SPE-3 … SPE-7 and SPE-10; **ccdproc** (BSD) — the twin for
CAL-5 and CAL-13.

Candidate new dependencies (decide in the step named; conditions of R9: permissive licence, wheels for all five
targets, maintained, small; write the verdict in this table):

| Package | Licence | For | Verdict today |
| --- | --- | --- | --- |
| pyqtgraph ≥ 0.14 | MIT | interactive plots | adopt after ARC-6's gate |
| PyO3 / maturin (build time) | MIT / Apache | native kernels | adopt (ARC-9) |
| dynesty | MIT | nested sampling | adopt in EXO-5.5 |
| celerite2 | MIT | Gaussian-process noise | adopt in EXO-13 if wheels exist on all targets |
| reproject | BSD | WCS resampling, mosaics | decide in CAL-15 |
| regions (astropy-regions) | BSD | DS9 region language | decide in IMG-6 (size, wheels) |
| dust_extinction | BSD | reddening laws | decide in SPE-12 (or 40 lines of our own from the papers) |
| synphot | BSD | synthetic photometry | reference twin for SPE-18; own code preferred (small) |
| specutils | BSD | spectrum readers | reference twin for SPE-12 readers; not bundled (pulls gwcs / asdf) |
| rasterio (GDAL) | BSD / MIT | raster warping, formats | decide in RS-3 |
| pywin32 or comtypes | PSF-like / MIT | ASCOM COM on Windows | decide in OBS-1 |
| barycorrpy | MIT | reference for barycentric corrections | test reference only (SPE-14) |
| lightkurve | MIT | reference for mission data handling | test reference only |
| batman, PyTransit, ellc, PHOEBE, PyReduce, TLS reference package, JKTEBOP, IRAF, LDTk | GPL | — | **never bundled**; run beside ours for validation (VAL-2) |

## Definition of done (the checklist; copy it under the step and tick it)

```
[ ] searched the code first; "Found in the code" written; reused / improved existing code, nothing duplicated
[ ] every Build bullet exists (or "Changed from the plan" written and told to the owner); every Accept line shown (numbers written under the step)
[ ] synthetic test with known truth            [ ] real-data check vs reference; reduced reference committed as a test
[ ] engine has no Qt; step registered; in astrowb.api; runs from the command line
[ ] interface uses the kit only; tooltips; undo/redo; empty state; error state; keyboard reachable
[ ] used as a user: QTest walk on real data; screenshots en/tr × dark/light at 1366×768 looked at
[ ] Turkish translations 0 unfinished (German, Spanish: ARC-25); error codes with what-happened + what-to-do; glossary terms respected
[ ] guide updated in English and Turkish; plans/interface.md "Where everything is" and plans/parity.md marks updated
[ ] time and peak memory measured on the named data; budget met; GPU twin tested equal (if any)
[ ] old projects / sessions / settings open (compatibility test extended)
[ ] precommit green; CI green on all systems; THIRD_PARTY.md updated for anything consulted or added
```

## Performance budgets (measured on the reference machine: 4 cores, 16 GB, no GPU; the owner's machine: RTX 4050)

| Operation | Budget |
| --- | --- |
| Start window visible | < 1.0 s from source, < 2.5 s installed |
| Open an area window | < 0.4 s (first time < 1.0 s) |
| Any click that only changes the view (zoom, pan, toggle, select) | < 100 ms; plots ≥ 30 fps while dragging with 10^6 points |
| Show a 4096 × 4096 frame (from disk, uncompressed) | < 0.3 s; next frame of a series < 0.1 s (read ahead) |
| Calibrate 100 frames of 4096 × 4096 | < 60 s CPU; GPU combine ≥ 3× faster on masters of ≥ 30 frames |
| Light curve, 1000 frames 4096 × 4096, 10 stars | < 5 min, < 2 GB |
| Period search, 10^5 points × 10^5 frequencies (LS / PDM / BLS) | < 10 s CPU, < 2 s GPU |
| Roche-model light curve, 500 phases, fine grid | < 20 ms (native), so that a 50 000-step MCMC takes minutes |
| Exact transit model, 10^5 points with supersampling 5 | < 30 ms (native) |
| Échelle extraction, 70 orders × 4096 px, optimal | < 15 s |
| Memory of the interface process with six windows open | < 500 MB without data |

A step that cannot meet a budget says so under the step with the profile; it is not done until the architect
answers.

## Network notes for agents (state 2026-11)

- From the agents' containers CDS Strasbourg (vizier, simbad, cdsarc, hips2fits) cuts connections; the Harvard
  mirrors `vizier.cfa.harvard.edu` and `simbad.harvard.edu` work (the Harvard VizieR returns nothing for Gaia and
  APASS: use the ESA Gaia archive and the IDIA VizieR). MAST, ESO, LCO, the Gaia archive, the Exoplanet Archive, JPL
  Horizons, Zenodo, NED, HEASARC, PyPI, crates.io and static.rust-lang.org work. aavso.org and GitHub release
  downloads answer 403; `git clone` of public repositories works.
- The user's network is not the agent's: every service call goes through `services/` with mirrors and a clear
  offline message; tests never need the network (recorded responses in `tests/data/services/`).

## To ask the owner

- Code signing (PLAN.md §8). Until decided, installers stay unsigned and the guide says how to open them.
- Hosting of optional data packs (ARC-20).

## For the owner to try

- After ARC-1: nothing to do; the next release simply no longer breaks with age.
- After ARC-10: Help → "Check the GPU" on the RTX 4050 machine and send the report file it writes.

## Steps

Order of work: stage S0: ARC-1 (together with OBS-0 of `plans/observing.md`), 2, 3; stage S1: ARC-4, 13, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 18, 23 (ARC-4's
sub-steps first for the window whose other layers are being migrated; ARC-13 early so that new code raises codes
from the start); P2 with the areas: ARC-17, 19, 20, 21, 22; P3: ARC-24.

### ARC-1. Earth-orientation and leap-second tables can never stop the program  (P1, first of all)
**agent3 done (2026-11-10, commit b599387 + this commit)**
- **Why:** `timing.py` sets `iers.conf.auto_download = False`. With Astropy ≥ 6 an alt-az transformation for a date
  after the bundled IERS-A table raises `ValueError: interpolating from IERS_Auto using predictive values that are
  more than 30.0 days old` once the bundle is older than `auto_max_age` (30 days). Reproduced on 2026-11-09 with
  `astropy-iers-data 0.2026.10.19`: `tests/test_alpaca.py::test_observatory_over_alpaca` fails. Every installed copy
  older than about a month fails in Planning, airmass, Observing safety (which then fails closed: no slews).
- **Reference:** Astropy documentation "IERS data access" (`astropy.utils.iers`): `auto_max_age = None` disables the
  check; predictions of UT1−UTC a year ahead are good to ~0.1 s (1.5″ in hour angle), irrelevant for airmass and
  far below a pointing error. BJD_TDB does not use UT1. **Safety consequence found 2026-11-10:**
  `devices/observatory.Observatory.check()` calls `check_sun` (an alt-az transformation); with a stale table it
  raises `ValueError`, the supervisor's loop catches it as "supervisor error" and **makes nothing safe**: weather
  and sunrise are then ignored for an unparked telescope (OBS-0 closes this hole on the supervisor's side). Leap seconds: `iers.LeapSeconds.auto_open()` and its expiry.
- **Ours now:** `timing.py` lines 19–22; `selfcheck.iers()` only counts rows.
- **Build:**
  1. `core/earth_orientation.py`: `configure()` sets `auto_download = False`, `auto_max_age = None`,
     `iers_degraded_accuracy = "warn"`; called once at import of `timing` and at the start of every worker process.
  2. `status()` → dict(table_date, age_days, covers_until, leap_seconds_expire, source = bundled | downloaded).
  3. `refresh(fetch=…)`: downloads IERS-A (`finals2000A.all`) and the leap-second list from the IERS / USNO
     mirrors Astropy lists, verifies they parse, stores them in the user data folder atomically, and installs them
     with `iers.earth_orientation_table.set(...)`; at start-up a stored table newer than the bundled one is used.
     Never blocks: runs as a background task with a 20 s time-out; failure leaves the old table.
  4. Setting `time.auto_refresh` (default on, shown in the first-run welcome and in Settings with the sentence "Once a
     week, when online, download the Earth-rotation table from the IERS (3 MB). Nothing about you is sent."). Off =
     only on request (Settings → "Update now").
  5. Start window status chip (UI-5): green "Time tables up to date", amber "Time tables are N days old — Update",
     with the consequence in the tooltip (altitudes may be off by up to X″; times are not affected).
  6. Error code `time.table_unreadable` if a stored table is corrupt: the file is set aside and the bundle is used.
  7. Tests: (a) with the bundled table made 800 days old (monkeypatch `Time.now` and the table's `predictive_mjd`)
     every function of `timing`, `planning.visibility`, `devices.safety` works and warns once; (b) BJD_TDB is
     bit-identical with a fresh and an old table; (c) `refresh` with a recorded response installs the table; with a
     broken response it leaves the old one; (d) the packaged smoke test computes an altitude for build date + 3
     years.
- **Accept:** the whole suite passes with `astropy-iers-data` pinned to a release two years old; no test needs the
  network; the status chip shows the right state in four languages.
- **Files:** `core/earth_orientation.py` (new), `timing.py`, `engine/tasks.py` (worker start), `selfcheck.py`,
  `__main__.py` (smoke test), `ui/welcome.py`, settings, `tests/test_earth_orientation.py`, guide 12.
- **Found in the code:** `timing.py` set `auto_download = False` and `iers_degraded_accuracy = "warn"` but not
  `auto_max_age`; `selfcheck.iers` only counted rows; every alt-az user (planning, safety, observatory, focus,
  server) reaches Astropy through `timing` (directly or via `devices/safety.py`), so one central setting suffices.
- **Result:** `core/earth_orientation.py` (`configure`, `use_stored`, `status`, `describe`, `due`, `refresh`);
  `timing.py` calls `configure()`; step `app.update_time_tables` downloads IERS-A and the leap-second list
  (primary URL, then mirror), checks they parse, stores them atomically in `<config>/earth-orientation/` and uses
  them in this and later processes; Settings menu: "Keep the Earth-rotation tables up to date (weekly)" (setting
  `time.auto_refresh`, default on) and "Update the Earth-rotation tables now"; weekly quiet update 8 s after start
  when due; first-run welcome has the tick; Help → Check the installation shows the table's date, age and how far
  its predictions reach; the smoke test computes an altitude three years ahead. Guide 12 (en, tr).
  Tests: `tests/test_earth_orientation.py` — alt-az, airmass and the safety rule with the clock 3 years past the
  table (fails on the old code with Astropy's `ValueError`, passes now), BJD identical with an old table, refresh
  from the mirror and refusal of a broken download (old table kept).
- **Changed from the plan:** (1) the start-window status chip (Build 5) is left to UI-5, which rebuilds the start
  window — the age is shown in Help → Check the installation meanwhile; (2) the leap-second file is set through
  `iers.conf.system_leap_second_file` instead of a separate status entry; (3) "covers until" in the status is the
  end of the table's predictions, not a computed accuracy.

### ARC-2. Green baseline and test tiers  (P1)
**agent3 done (2026-11-10, this commit)**
- **Why:** on a fresh checkout `pytest` fails in 5 tests because the compiled translations (`*.qm`, git-ignored) do
  not exist until `python tools/i18n.py` runs; the suite takes 11 minutes, one test 78 s; agents skip it and push
  untested work (it happened: photometry 9b broke the IRAF validation in CI).
- **Build:**
  1. `tests/conftest.py`: a session fixture compiles the translations when a `.qm` is missing or older than its
     `.ts`.
  2. Markers registered in `pyproject.toml`: `slow` (> 5 s), `gui`, `validation` (needs `ASTROWB_VALIDATION_DATA`),
     `gpu`, `hardware` (INDI simulators), `network` (never in CI's default run). `pytest -m "not slow"` is the quick
     loop.
  3. `pytest-xdist` (MIT) in the dev extra; `tools/precommit.sh` runs `pytest -n auto`; tests that need exclusive
     resources (ports, the settings folder) use `tmp_path` and free ports — fix every test that fails in parallel.
  4. Targets: quick loop < 3 min on 4 cores; whole suite < 6 min; no single test > 30 s without the `slow` marker
     (`test_minimum_times_are_unbiased_with_honest_errors` 78 s: keep its statistics, cut its cost by vectorising or
     by a smaller default sample with the full sample under `slow`).
  5. `tools/precommit.sh` prints the ten slowest tests and fails on warnings that are ours
     (`TimeDeltaMissingUnitWarning` in the sample night: fix the call).
  6. Coverage (coverage.py) measured in CI on Linux, reported per package in the job summary; no threshold yet.
  7. `tools/run_validation.sh`: downloads (or finds) the sets listed in `data/` and runs `pytest -m validation`
     locally, so the lesson of photometry 9b ("validation data must be set for the local full check") is one
     command.
- **Accept:** fresh clone → `pip install -e ".[gui,dev]"` → `pytest` green without any other command; `-n auto`
  green three times in a row; times above met; CI uses the same script as the agents.
- **Files:** `tests/conftest.py`, `pyproject.toml`, `tools/precommit.sh`, `tools/run_validation.sh`, the slow tests,
  `.github/workflows/ci.yml`.
- **Result:** `tests/conftest.py` compiles the translations when a `.qm` is missing or older than its `.ts`;
  markers `slow`, `validation`, `gpu`, `hardware`, `network` registered; the 78 s statistics test split into a
  16-night `slow` test and a 4-night quick one; `test_every_button…`, `test_text_size`, the layout test, the EB MCMC
  test and the practice-night run marked `slow`; `pytest-xdist` and `pytest-cov` in the dev extra; precommit and CI run
  `-n auto --durations=10`; CI's Linux job writes coverage per module into the job summary; `tools/run_validation.sh`
  fetches the HAT-P-32 night once and runs `tests/validation`; the practice-night generator's unit-less time sum
  fixed, and that warning is now an error in the tests. Measured here (4 cores): whole suite serial 10 min 41 s, 818
  passed; quick loop `-n auto -m "not slow"` 4 min 42 s, 806 passed, nothing broken by parallel running.
- **Changed from the plan:** the quick-loop target "< 3 min" is not met on this 4-core container (4 min 42 s); the
  remaining time is spread over many 2–6 s UI tests, which ARC-4 and the UI rebuild will change anyway — revisit
  after UI-4. Python 3.13 in the matrix is left to ARC-3.

### ARC-3. Reproducible environment and early warning for dependency changes  (P1)
**agent3 done (2026-11-10)**
- **Result:** `uv.lock` exported to `requirements/{dev,build}.txt`, used by CI and the installers; upper major bounds;
  weekly `latest-deps` run; licence table generated. Linux ARM gets its own pin (PySide6 6.8.0.2): later PySide6
  wheels for ARM need a newer glibc than Ubuntu 22.04's, found by the first locked packaging run.
- **Why:** ARC-1 was caused by a behaviour change in a dependency and found by accident. Installers are built from
  whatever is newest on the build day.
- **Build:**
  1. `uv.lock` committed; CI and the packaging jobs install from the lock (`uv sync --frozen`); a documented command
     updates it (`uv lock --upgrade`), run on purpose, with the suite and the validation run before the commit.
  2. Lower bounds in `pyproject.toml` stay; add the tested upper major bounds for numpy, astropy, photutils, scipy,
     PySide6.
  3. A scheduled CI job (weekly) installs the newest versions without the lock and runs the suite; a failure opens
     nothing by itself but shows red in Actions with the diff of versions in the summary.
  4. Python: 3.12 is the build version; the test matrix adds 3.13 on Linux.
  5. `tools/check_licenses.py` runs against the locked set and prints the table of licences into
     `THIRD_PARTY.md` (generated section).
- **Accept:** two packaging runs a week apart produce installers with identical dependency versions; the weekly job
  exists and is green or explains itself.
- **Files:** `uv.lock`, `pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/latest-deps.yml`,
  `tools/check_licenses.py`, `CONTRIBUTING.md`.

### ARC-4. Split the interface into packages  (P1)
**open** — eight sub-steps, each claimed and done on its own, each a pure move: behaviour, texts, object names,
settings keys and translations contexts unchanged (class names stay the same so that translations keep matching);
the suite is green after each.
- **Why:** PLAN.md §2 item 3.
- **Method (the same for every sub-step):**
  1. Read the whole file; write under the sub-step the list of classes and of method groups (by the panel or dialog
     they serve).
  2. Create `ui/<area>/` with `__init__.py` re-exporting the public classes under their old import paths
     (`ui/photometry_page.py` becomes a three-line shim importing from `ui/photometry/`; shims are removed only in
     ARC-4.8).
  3. Move one panel at a time into `panels/<name>.py` as its own `QWidget` class; what it needs from the page comes
     through its constructor or signals — no reaching into `self.parent()`.
  4. Step calls and their `on_done` handlers move to `controller.py`; the widgets keep only display code.
  5. After every moved panel: run the area's tests. Commit moves separately from any fix found on the way (fixes
     get their own commits and tests).
  6. `tools/module_sizes.py` + `tests/test_module_sizes.py`: every `ui/` module ≤ 700 lines except those on the
     allow-list in the tool; a sub-step removes its file from the allow-list.
- **Sub-steps:**
  - **ARC-4.1** `tools/module_sizes.py`, the test, the allow-list of today's files. **agent3 done (2026-11-10, this
    commit)** — limits ui 700 / other 900 lines per module, 80 per function; allow-list
    `tools/module_sizes_allow.json` (a ratchet: listed items may shrink, not grow): 5 modules
    (photometry_page 3190, main_window 2893, spectro_page 2429, observe_page 861, spectrum_tools 810) and 39
    functions — the largest `PhotometryPage.__init__` with 953 lines, `CalibratePage.__init__` 372,
    `photometry/lightcurve.light_curve` 228. Run in precommit and by `tests/test_module_sizes.py`.
    Changed from the plan: functions are on the allow-list too (the plan's code rule limits them as well).
  - **ARC-4.2** Photometry (`photometry_page.py`, 3190 lines) → `ui/photometry/`: `window.py`, `controller.py`,
    `panels/{images,stars,apertures,measure,plot,stars_table,minimum,measurements,export,multiplot,detrend}.py`,
    `dialogs/{aavso,star_list,coefficients}.py`. **merged into UI-16.1 (Photometry) (agent3, 2026-11-10; see the note below)**
  - **ARC-4.3** Spectroscopy (`spectro_page.py` 2429, `spectrum_tools.py` 810) → `ui/spectroscopy/` with one module
    per job (long slit, échelle, telluric, velocity, cube, tools) and shared `panels/{profile,identify,fit}.py`.
    **merged into UI-16.3 (Spectroscopy) (agent3, 2026-11-10; see the note below)**
  - **ARC-4.4** `main_window.py` (2859) → `ui/shell/`: `app.py` (start-up), `main_window.py` (the start window only),
    `menus.py`, `area_registry.py` (the table of areas: key, title, icon, factory, opener — one source for the
    start window, Window menus and Ctrl+K), `tasks_panel.py`, `settings_menu.py`, `help.py`, and each area's
    `_xxx_menus` moved into that area's package as `menus.py`. **open**
  - **ARC-4.5** Calibration, Images, Observing, Planning pages → their packages. **merged into UI-16.2, 16.8, 16.9, 16.10 (agent3, 2026-11-10; see the note below)**
  - **ARC-4.6** Light curves (period, frequency, variable search), O−C, Models, Automation, Remote sensing →
    their packages. **merged into UI-16.4 … 16.7, 16.12, 16.13 (agent3, 2026-11-10; see the note below)**
  - **ARC-4.7** `widgets.py`, `table_view.py`, `export.py`, `icons.py`, `workspaces.py`, `area_window.py` → `ui/kit/`
    and `ui/plot/` as the first content of the kit (their public names re-exported). **agent3 done (2026-11-10, this commit)** — moved with `git mv`: `ui/widgets.py` →
    `ui/kit/widgets.py`, `ui/table_view.py` → `ui/kit/table_view.py`, `ui/icons.py` → `ui/kit/icons.py`,
    `ui/area_window.py` → `ui/kit/window.py`, `ui/export.py` → `ui/plot/export.py`; every import in `src/`,
    `tests/` and `tools/` updated (no shims: nothing outside the repository imports them; `ui/workspaces.py`
    keeps its old re-exports). Changed from the plan: no compatibility shims at the old paths — they would only
    have to be removed again in ARC-4.8.
  - **ARC-4.8** Remove the shims; update imports in tests and tools; delete the allow-list. **open**
- **Changed from the plan (agent3, 2026-11-10, told to the owner):** a pure move of the old pages (ARC-4.2, 4.3,
  4.5, 4.6) would be done twice: every one of those windows is rebuilt on the new anatomy in its UI-16 sub-step. So
  each UI-16 sub-step creates its `ui/<area>/` package and moves the old page's code into it as it rebuilds the
  window (engine calls into `controller.py`, panels into `panels/`); the old file shrinks with each move and is
  removed when empty. The size ratchet (ARC-4.1) keeps the old files from growing meanwhile. ARC-4.4 (the shell out
  of `main_window.py`) and ARC-4.7 (the kit's location) stay as written: the kit and the start window need them
  first.
- **Accept:** no `ui/` module above 700 lines; the suite and the four-language layout tests green; start-up time not
  worse (measure before and after); `git log --follow` works on the moved files (moves done with `git mv` where a
  file moves whole).
- **Files:** all of `src/astrowb/ui/`, `tools/module_sizes.py`, tests' imports.
- **Depends on:** ARC-2.

### ARC-5. Typed session state, undo and autosave from one mechanism  (P1)
**agent3 done (core: items 2, 3, 4 in parts, 7) — items 4–6 continue with each area's move (ARC-5.1 …)**
- **Result:** `core/state.py` `Store` (set / delete / batch / undo / redo, typing merged within 0.7 s, listeners,
  `to_json` / `from_json` with migrations, refusal of another area or a newer schema); `ui/kit/binding.py` `bind()`
  for spin boxes, buttons, combo boxes, line and text edits, `Autosave` into the project's new `sessions` table;
  tests: property test (300 random sequences), merging, batches, list items, bound controls both ways.
- **Found in the code:** File → Save / Open session already exist in `ui/kit/window.py` (item 5): the migrated
  windows pass the store's `to_json` / `from_json` to it instead of new menu entries.
- **Changed from the plan:** item 1 (a dataclass `AreaState`) is replaced by one plain JSON tree addressed by paths:
  every binding, undo step and migration works on paths anyway, and a dataclass per area would be a second copy of the
  same shape. Large arrays as files in the project come with the first area that needs them (spectroscopy).
- **Why:** each page hand-writes `undo_state()` / `set_undo_state()`; sessions restore part of a window; "continue
  where you left off" (owner) needs the whole state; scripting (ARC-12) needs to turn a session into a recipe.
- **Reference:** Qt's undo framework (`QUndoStack`, commands with `mergeWith`); Siril and PixInsight keep a
  processing history per image; AstroImageJ saves "all" (table, plot configuration, apertures) as files.
- **Ours now:** `ui/undo.py` (`Undoable`, `_Snapshot` of a whole state, `track_typing`), `AreaWindow` sessions (I2.3).
- **Build:**
  1. `core/state.py`: `class AreaState` (dataclass base): `schema: int`, `to_json()`, `from_json()` with a registry of
     migrations `(area, from_schema) → function`; fields are plain values, lists, dicts, nested dataclasses, numpy
     arrays stored as lists only when small (< 10 000 numbers), large arrays as references to files in the project.
  2. `core/state.py`: `class Store(QObject-free)`: holds the state, `apply(change)` with `change = Set(path, value)`
     or `Batch(text, [changes])`; emits `changed(paths)` through a plain callback list (Qt wiring lives in
     `ui/kit/binding.py`); an undo stack of inverse changes with text for the Edit menu; consecutive `Set` on the same
     path within 0.7 s merge (typing, dragging).
  3. `ui/kit/binding.py`: helpers that bind a kit control to a state path both ways (`bind_number(field, store,
     "apertures.r_ap")`), so a panel never writes its own undo code.
  4. Autosave: the store's JSON goes to the project (`sessions` table: area, name, json, saved) 2 s after the last
     change and on close; on opening the window the last session of the project is restored and a banner says so
     with "Start fresh" (UI-3 InfoBanner). Without a project: the user data folder.
  5. File → "Save session as…", "Open session…" (`.session.json`, self-contained: relative paths when inside the
     project folder).
  6. Migration of the areas: one sub-step per area window (ARC-5.1 Photometry … ARC-5.11), each replacing that
     window's `Undoable` code and old session code by the store; the old session files still open through a migration.
     `ui/undo.py` stays until the last area has moved.
  7. Tests: property test (random sequences of changes then undo-all returns to the initial JSON); merge of typing;
     migration from every older schema kept as fixture files in `tests/data/sessions/`.
- **Accept:** in every migrated window Ctrl+Z / Ctrl+Y cover every control (a test walks all bound controls,
  changes each, undoes, compares the state); closing and reopening the program restores the window exactly (state
  JSON equal); a session saved by version 0.3.4 opens.
- **Files:** `core/state.py`, `ui/kit/binding.py`, each `ui/<area>/state.py` and `controller.py`, `engine/project.py`
  (table `sessions`, additive), tests.
- **Depends on:** ARC-4 for the area being migrated.

### ARC-6. Plot layer: fast interactive plots, publication export from the same description  (P1)
**agent3 claimed (2026-11-10 21:30 UTC) — do not touch**
- **Progress (agent3):** items 0, 1, 2, 3, 5, 7 done — `ui/plot/spec.py` (spec, Okabe–Ito colours, time offsets,
  decimation), `ui/plot/view.py` (`PlotView`: every interaction of item 2, driven by QTests in
  `tests/test_plot_view.py`), `ui/plot/publish.py` (AAS / A&A / MNRAS / screen styles, fonts embedded, ECSV data and
  a redraw script); pyqtgraph 0.14 locked. Item 4 done (`set_time_mode`: BJD, UT hours, phase). Pending: item 6 (toolbar, with UI-10) and the
  window migrations (item 8). Axis settings, export and copy come from pyqtgraph's own context menu for now.
- **Why:** PLAN.md §2 item 6; AstroImageJ's Multi-Plot and Period04 are interactive on every point; ours redraws a
  Matplotlib canvas.
- **Reference:** pyqtgraph (MIT; `PlotItem`, `ScatterPlotItem`, downsampling, `LinearRegionItem`, linked views);
  Matplotlib for print; AAS journals' figure rules (vector, fonts embedded, colour-blind safe); AstroImageJ
  Multi-Plot (click to remove a point, drag to set regions, legend toggles).
- **Ours now:** `ui/widgets.PlotCanvas` (Matplotlib `FigureCanvasQTAgg` with a toolbar, publication figure, export
  data, open in a new window); `ui/export.publication_copy`.
- **Build:**
  1. `ui/plot/spec.py`: `FigureSpec(panels=[PanelSpec], shared_x=True, title)`, `PanelSpec(x: AxisSpec, y: AxisSpec,
     series=[SeriesSpec], height_ratio)`, `AxisSpec(label, unit, scale=linear|log, invert, time=None|bjd|phase|ut,
     offset)`, `SeriesSpec(name, x, y, yerr=None, xerr=None, kind=points|line|steps|errorbars|band|vline|hline|image|
     histogram, colour, symbol, size, width, alpha, z, pickable, ids)`. Pure data, no Qt, JSON-able (arrays by
     reference).
  2. `ui/plot/view.py`: `PlotView(QWidget)` renders a spec with pyqtgraph. Interactions, all with the mouse and the
     keyboard, the same in every window: wheel = zoom at the cursor (Ctrl = x only, Shift = y only); drag = pan;
     right-drag or `Z` + drag = box zoom; `A` or double-click = show all; `R` + drag = select a range on x (emits
     `range_selected(x0, x1)`); click on a pickable point = `point_clicked(series, id)`; `L` + drag = lasso
     (`points_selected`); legend entries toggle their series; crosshair with read-out in the window's status bar
     (x, y in the axis units, the nearest point's id); linked x between stacked panels; a context menu (export,
     copy image, copy data, axis settings: limits typed, log, invert, grid).
  3. Large data: peak-preserving decimation above 50 000 points per series in view (min and max per pixel column),
     exact when zoomed in; errors bars drawn only below 5 000 points in view.
  4. Time axes: `AxisSpec.time`; the axis shows `BJD_TDB − 2460000` style offsets chosen automatically and written in
     the label; a toggle to UT hours of the night and, when a period is known, to phase.
  5. `ui/plot/publish.py`: `publish(spec, path, style)` renders the same spec with Matplotlib: styles `aas`, `aanda`,
     `mnras`, `screen`; widths single 3.5 in / double 7.1 in; fonts STIX; line widths and marker sizes per style;
     Okabe–Ito colours; output PDF / EPS / SVG / PNG 300 and 600 dpi; metadata (title, the application's name from
     the brand, version, date). `data_behind(spec, path)` writes the plotted numbers as ECSV with units; `script(spec,
     path)` writes a stand-alone Python script that redraws the figure from that ECSV.
  6. The toolbar of a plot is a kit component (UI-10): show all, box zoom, select range, pick, export…, publication
     figure…, open in a window.
  0. **Decision gate before anything else in this step (a two-hour spike, results written under the step):** with
     pyqtgraph ≥ 0.14 (its OpenGL path was rewritten on programmable shaders, OpenGL 3.1+; PySide6 ≥ 6.10 needed on
     macOS) measure on the reference machine and under the software renderer of CI: scatter and line plots of
     10^5, 10^6 and 10^7 points, pan / zoom frame times, with and without OpenGL, with our decimation. If 10^6
     points cannot reach 30 fps even with decimation, stop and write the numbers under "Questions for the
     architect" (the fall-back is our own `QPainter` renderer on decimated data behind the same `PlotView` API).
     **Gate result (agent3, 2026-11-10; Qt software raster, no OpenGL, 4 cores, 1200 × 700 px, median of 30 pans):**
     | points | line, pyqtgraph peak downsampling | line, ours | scatter, pyqtgraph | scatter, ours |
     |---|---|---|---|---|
     | 10^5 | 18 ms first, 112 fps | 11 ms, 199 fps | 203 ms, 49 fps | 10 ms, 158 fps |
     | 10^6 | 82 ms, 119 fps | 12 ms, 189 fps | 1.8 s, 5 fps | 17 ms, 149 fps |
     | 10^7 | 229 ms, 75 fps | 22 ms, 112 fps | (too slow) | 28 ms, 97 fps |
     Passed without OpenGL: pyqtgraph stays, OpenGL is not needed (fewer driver problems on old laptops). Our own
     decimation is required for scatter plots (pyqtgraph draws every symbol). **Changed from the plan:** scatter
     series are decimated to one point per occupied pixel cell (min / max per column would draw only the envelope
     of a noisy light curve); lines keep min / max per column.
  7. Dependency: `pyqtgraph >= 0.14` (MIT) in the gui extra; PyInstaller hook checked on all five targets;
     `THIRD_PARTY.md`.
  8. Migration, one sub-step per window (ARC-6.1 Photometry plot and multi-plot; .2 Light curves, period,
     frequency; .3 O−C; .4 Spectroscopy (spectrum, arc, fit, residuals, CCF); .5 Models; .6 Planning; .7 Images
     tools (profiles, histogram); .8 the rest). Corner plots and other statistical figures stay Matplotlib inside
     a `ui/plot/static.py` wrapper with the same toolbar.
- **Accept:**
  1. 10^6 points (TESS two-minute data, three sectors): first draw < 300 ms, pan and zoom ≥ 30 fps on the reference
     machine (measured with a script that drives 200 mouse-move events and reports the frame time).
  2. For ten spec fixtures the publication PDF contains the same series, limits and labels as the interactive view
     (a test compares the limits and the number of drawn points).
  3. Every interaction above is driven by a QTest in `tests/ui/test_plot_view.py`.
  4. The published PDF of a light curve passes the AAS checker rules we can test: fonts embedded, no bitmap for
     < 20 000 points, single-column width 3.5 in.
- **Files:** `ui/plot/{spec,view,publish,static,toolbar}.py`, each window's panels, `pyproject.toml`, packaging hooks,
  tests.
- **Depends on:** ARC-4.7.

### ARC-7. Image layer: one viewer for every window  (P1)
**agent3 claimed (2026-11-10 21:45 UTC) — do not touch**
- **Progress (agent3):** speed part of the Accept met without item 1's tile pyramid. Measured first (Qt software
  raster, 4 cores, 1400 × 900 view): the old viewer already panned and zoomed in 2–7 ms a frame (Qt scales one
  pixmap); only the first view (9576 × 6388: 1.1 s) and a level change (0.7 s) were slow, both from converting
  every pixel. Now: the conversion runs in row blocks on every core (574 → 158 ms), and frames above 8 MP show a
  screen-sized preview at once and their full resolution from a background thread. Result: first view 0.41 s (of
  which 0.3 s is the one-time Astropy import), level change visible in 72 ms, 16 384² mosaic 0.11 s, pan / zoom
  1.5–2 ms. **Changed from the plan:** no tile pyramid (item 1) — it would add a cache, a thread pool and tile
  seams for no measured gain; revisit only if a frame larger than memory has to be shown. Item 2 done in the
  viewer: View → Orientation (North up / East left from the WCS — key N, turn 90°, mirror, original), compass and
  scale bar (`ui/image/orient.py`, tests for four angles × both parities). The `DisplaySpec` object is left out:
  the viewer's interval / stretch / limits / colour map / orientation attributes are that state, and ARC-5's store
  holds them when the Images window moves. Items 3–9 continue.
- **Why:** `ui/viewer.py` renders the whole image to one pixmap on every change of levels; 9k × 9k CMOS frames and
  mosaics are slow; overlays, tools and read-outs are wired differently in Images, Photometry and Spectroscopy.
- **Reference:** DS9 (frames, lock by WCS / image, regions, magnifier, panner, pixel table, scales zscale / minmax /
  percent, linear / log / sqrt / asinh / histogram equalisation); AstroImageJ's image window (RA / Dec at the cursor,
  aperture overlay toggles, frame slider, auto contrast, invert, N-up / E-left flips of the display only); MaxIm DL's
  Information window; Ginga (tiling, modes).
- **Ours now:** `ImageViewer(QGraphicsView)`: pan, zoom, stretch, markers, overlays by name, area and line tools,
  hover read-out; `display.py` (limits on a subsample, 16-bit LUT).
- **Build:**
  1. `ui/image/view.py`: `ImageView`: a tile pyramid (tiles 512 × 512, levels by factors of 2, built lazily in a
     thread pool from the float data through the LUT; a cache with a memory cap, default 512 MB); the visible tiles
     of the right level are drawn; changing levels re-renders only visible tiles first.
  2. Display state `DisplaySpec(interval, stretch, limits, colour_map, invert, flip_x, flip_y, rotate_90)` — display
     only, the data never change; "North up, East left" one click when a WCS exists; a compass and a scale bar
     overlay (arcsec / arcmin from the WCS).
  3. Layers: `view.layer(name)` returns a group; items are plain specs (`Circle`, `Annulus`, `Ellipse`, `Box`,
     `Polyline`, `Text`, `Cross`, with colour, width, label, id, pickable) so engine code can produce overlays without
     Qt; visibility and opacity per layer from a Layers popover; fixed screen-size option for markers.
  4. Tools (one active, the same keys everywhere): pan (space-drag always pans), pick / mark (click), region (box,
     circle, ellipse, polygon), ruler (distance, position angle; in arcsec with a WCS), profile line with width, and
     the `imexamine`-style keys under the cursor: `a` aperture summary, `r` radial profile with Moffat / Gaussian
     fit, `e` contour, `s` surface, `l` / `c` line / column cut, `h` histogram, `m` statistics in a box — each opens
     or updates the Inspect panel (IMG-3).
  5. Read-out in the status bar: x, y (FITS 1-based), value, RA / Dec (sexagesimal and degrees), and with a
     photometric zero point the magnitude in the default aperture.
  6. Navigator (thumbnail with the view rectangle) and magnifier (pixel grid at 8×–32× with values printed when the
     pixels are larger than 40 screen pixels).
  7. Sequences: `set_sequence(paths)`, slider, previous / next, play (blink) at a chosen rate; the next and previous
     frames are read ahead; display limits fixed for the sequence or per frame (toggle).
  8. Linked views: several `ImageView`s lock pan / zoom by pixel or by WCS (for compare, RGB, before / after).
  9. The old `ImageViewer` API stays as a thin adapter until every window has moved (sub-steps ARC-7.1 Images,
     .2 Photometry, .3 Spectroscopy 2-D, .4 Remote sensing, .5 Observing preview, .6 Astrometry).
- **Accept:** a 9576 × 6388 16-bit frame: first view < 0.5 s, pan / zoom ≥ 30 fps, change of levels visible in
  < 100 ms; memory under the cap; 16 384 × 16 384 synthetic mosaic usable; every tool and key driven by a QTest; the
  read-out matches `astropy.wcs` to 0.01 px on the Qatar-1 frames.
- **Files:** `ui/image/{view,tiles,layers,tools,readout,navigator}.py`, `display.py`, the windows' panels, tests.
- **Depends on:** ARC-4.7.

### ARC-8. Table layer: one table for every window  (P1)
**agent3 claimed (2026-11-10 22:00 UTC) — do not touch**
- **Progress (agent3):** items 1 and 2 done. `core/table.py`: `select()` (column names, arithmetic, chained
  comparisons, and / or / not, abs / isnan / log10 / sqrt — parsed with `ast`, nothing else can run), `write()`
  to CSV, ECSV, VOTable, HTML (Astropy's writers), AASTeX deluxetable and Markdown with "value ± error" rounded by
  the error. `ui/kit/table.py`: `TableView` over the table without copying it — 10^6 × 40 opens in < 0.5 s and
  sorts in < 1 s (tested); NaN last both ways, filter errors shown on the line, marks with reasons, column
  chooser, copy, Export…. Floats show 15 significant digits (a BJD keeps its microdays). Item 3 done: `ui/kit/link.py` `link(table, plot, series)` (table selection ringed in the plot, clicked or lassoed points select their rows; tested). **Changed from the plan:**
  no own `Columns` class — Astropy's `Table` already holds named columns with unit, description and format and
  reads / writes every format; `rounded()` moved from `ui/plot/export.py` to `core/table.py`. Pending: item 4
  (editing), item 5 (moving the old tables).
- **Why:** the measurements table, minima lists, line lists, frame lists and results tables are separate
  `QTableWidget`s with separate export code; a million TESS cadences cannot be shown.
- **Reference:** AstroImageJ's Measurements window (filter, column chooser, sort), TOPCAT (columns with units and
  descriptions, row subsets linked to plots, many export formats).
- **Ours now:** `ui/table_view.DataTable`, `ui/export.export_table` / `save_results`, `photometry/measurements.filter_rows`.
- **Build:**
  1. `core/table.py`: `Columns` = ordered named numpy arrays with unit, description, format hint and an optional
     error column; conversions to and from Astropy `Table`; writers: CSV, ECSV, VOTable, LaTeX (`aastex` deluxetable
     and A&A), Markdown, HTML; values rounded by their errors (two significant digits of the error) in LaTeX.
  2. `ui/kit/table.py`: `TableView` on a `QAbstractTableModel` over `Columns` (virtual: 10^6 rows scroll smoothly);
     sort by a click; a filter line with the expression language of `filter_rows` (columns by name, `and`, `or`,
     comparisons, `abs`, `isnan`), errors explained by code; a column chooser with search; frozen first column;
     cell colours from flag columns with the reason in the tooltip; copy (cells with headers, tab-separated);
     Export… with every writer.
  3. Selection model shared with a `PlotView` (`ui/kit/link.py`): selecting rows highlights points and the reverse;
     "Leave out the selected rows" is an intent to the controller (undoable).
  4. Editable columns where the area allows (typed with validation by the column's kind; undo through ARC-5).
  5. Migration: measurements, frames, stars, minima, lines, orders, results, sequence, targets tables (one sub-step
     per window, with the window's ARC-5 migration).
- **Accept:** 10^6 rows × 40 columns: open < 0.5 s, sort < 1 s, scroll without stutter; each writer round-trips
  through Astropy readers in a test; the LaTeX output compiles in a minimal AASTeX document (checked with a stored
  expected text); selection linking driven by a QTest.
- **Files:** `core/table.py`, `ui/kit/{table,link}.py`, windows' panels, tests.

### ARC-9. Native kernels (Rust) with NumPy twins  (P1)
**agent3 claimed (2026-11-10 22:15 UTC) — do not touch** (done when the installers of all five targets carry it)
- **Progress (agent3):** items 1, 3–7 done; item 2 changed. `native/` (pyo3 0.30 abi3, numpy, rayon; Rust pinned
  1.97.0; `Cargo.lock` committed), `tools/build_native.py`, `src/astrowb/native.py` (`available`, `use`,
  `describe`, `ASTROWB_NATIVE=off`), `kepler_e` behind `spectroscopy/orbit.eccentric_anomaly` with its twin kept,
  `tests/test_native.py` (twin equality at e = 0 … 0.99 to 1e-12, empty / NaN / inf / threaded path, the twin
  with the module switched off), Help → "Check the installation" line "compiled routines" (required in an
  installed copy, optional in a checkout), `native/README.md`. CI builds it in the test and package jobs.
- **Measured:** 10^6 anomalies, e = 0.3: 33 ms on 4 threads (118 ms on one) against 235 ms for the NumPy twin:
  7× (11× at e = 0.99). **Changed from the plan:** the Accept's "≥ 10×" assumed a Python loop; the twin is a
  vectorised NumPy loop with SIMD sine and cosine, so one core gains only 2×. Not chased further (it is not a
  bottleneck); the kernels that matter (Roche, PDM, PSF) replace real Python loops. Item 2: no maturin wheels —
  the module ships only inside the installers and source trees, so `cargo build` and a copy next to the package
  (`tools/build_native.py`, a hatch artifact for the non-editable install) do the job on each runner's own
  system. `cargo deny` not added: the licences are listed in THIRD_PARTY.md from `cargo metadata` (all MIT /
  Apache-2.0 / BSD-2-Clause); a new crate is checked by hand (README rule 5).
- **Why:** AD-2. The Roche model (MOD), exact transits with supersampling (EXO), fold statistics over 10^5
  frequencies (PER), PSF fits (PHO) and curved-slit extraction (SPE) are loops NumPy cannot vectorise well.
- **Reference:** PHOEBE (C++ `libphoebe`), ellc (Fortran), batman (C with OpenMP), Astropy BLS (C), photutils
  (Cython): every serious code has compiled kernels. PyO3 user guide; maturin; the `numpy` crate (zero-copy
  `PyReadonlyArray`), `rayon` for threads.
- **Build:**
  1. `native/Cargo.toml` (crate `astrowb_native`, `crate-type = ["cdylib"]`, `pyo3` with `abi3-py311`, `numpy`,
     `rayon`, `ndarray`; licences MIT / Apache-2.0 only, checked by `cargo deny` in CI); Python module name
     `astrowb._native`.
  2. Build: `pyproject.toml` keeps hatchling for the pure package; the native module is built by `maturin build
     --release` in a CI job for the five targets (manylinux2014 x86_64 and aarch64, Windows x64, macOS arm64 and
     x86_64) and copied into the installers by the PyInstaller spec; developers run `tools/build_native.sh`
     (`maturin develop --release`). The tool chain is pinned (`rust-toolchain.toml`).
  3. `astrowb/native.py`: `available()`, `version()`, and `use(name)` returning the compiled function or `None`;
     every caller has the form `fast = native.use("fold_pdm"); return fast(...) if fast else _numpy_twin(...)`.
     A setting `compute.native = auto | off` (off for debugging); `selfcheck` reports whether the module loaded.
  4. First kernel, to prove the chain end to end: `kepler_e(m, e)` (eccentric anomaly, vectorised, Newton with
     Danby's start, tolerance 1e-14) replacing the loop in `spectroscopy/orbit.py`; its twin stays.
  5. Conventions for every kernel: inputs are float64 contiguous arrays; no allocation in inner loops; the GIL is
     released (`py.allow_threads`); threads through rayon with the number of threads from `engine.parallel.workers()`;
     results deterministic for a fixed thread count; errors returned as `AppError` codes, never panics (a
     `catch_unwind` guard at the boundary).
  6. Tests: `tests/test_native.py` compares each kernel with its twin on random inputs (relative 1e-12 unless the
     kernel documents another tolerance) and on edge cases (empty, NaN, single value); the suite passes with
     `compute.native = off`; CI runs both.
  7. Documentation: `native/README.md`: how to add a kernel (signature, twin, test, benchmark entry).
- **Accept:** installers of all five targets contain the module and `--smoke-test` calls `kepler_e`; with the module
  removed the program runs (twin) and Help → "Check the installation" says "compiled routines: not available
  (slower)"; `kepler_e` ≥ 10× the NumPy loop on 10^6 anomalies.
- **Files:** `native/`, `src/astrowb/native.py`, `packaging/`, `.github/workflows/ci.yml`, `tools/build_native.sh`,
  `tests/test_native.py`, `THIRD_PARTY.md`.

### ARC-10. GPU kernels: the list, the rules, the check on real hardware  (P1)
**open**
- **Ours now:** `compute/` with wgpu: clipped-mean combine, stack combine, BLS, PDM, Richardson–Lucy, k-means
  nearest; `--benchmark` and `tools/gpu_check.py`; software adapters refused in auto mode. Never measured on a real
  GPU.
- **Build:**
  1. Help → "Check the GPU…" runs `compute.check.benchmark()` in a task and shows a table (job, CPU time, GPU time,
     equal?) and writes `gpu-report.json` (adapter, driver, limits, results) that the problem report includes.
  2. The owner runs it on the RTX 4050; the result is written under this step and into the guide's speed table;
     every kernel slower on that GPU than on its CPU twin is fixed or removed from "auto" (kept under "GPU" for
     larger machines) with the measured crossover size stored in `compute/thresholds.json`.
  3. Rules written into `compute/README.md`: float32 only for values, never for times or coordinates; inputs larger
     than the adapter's limits are chunked; any failure falls back to the CPU and is reported once per session in the
     Tasks list; results equal to the CPU twin within the tolerance documented per kernel.
  4. New kernels are planned in their areas and listed here when done: TLS and fold statistics (PER), Lomb–Scargle
     by NFFT-like binning (PER), synthetic tracking shift-and-stack (AST), difference-image convolution (PHO),
     aperture sums on many stars × frames (PHO), cross-correlation over many orders (SPE), Roche-model grid search
     (MOD) only if the native CPU kernel is not enough.
- **Accept:** the report exists for the owner's machine; `auto` never picks a slower path at the measured sizes;
  every kernel has an equality test that runs in CI under the software Vulkan driver (lavapipe) on Linux.
- **Files:** `compute/check.py`, `compute/thresholds.json`, `compute/README.md`, `ui/shell/help.py`, CI.

### ARC-11. Provenance: every product knows how it was made  (P1)
**open**
- **Why:** AD-12. A referee asks "how were the frames calibrated, which stars, which radii, which version?"; today
  the project records runs but the products do not carry it and nothing writes it for a paper.
- **Reference:** IRAF writes `HISTORY` and processing keywords (`CCDPROC`, `ZEROCOR`, `FLATCOR`); ESO pipelines
  write `HIERARCH ESO PRO REC` records; MaxIm DL `CALSTAT`; AAS "Software" citations.
- **Ours now:** `engine/project.py` table `runs` (step, params, inputs, outputs, status, times); `HISTORY` lines in
  some writers; `ui/project_page.py` shows the history and can run again.
- **Build:**
  1. `core/provenance.py`: `record(step_id, params, inputs, versions)` → a compact dict with the checksums (BLAKE2,
     first and last MB + size for large files) of the inputs; `to_fits(header, record)` writes `HISTORY` lines and
     the keywords `SWCREATE`, `SWVERS`, `PROCSTEP`, `PROCHASH`; `to_ecsv(meta, record)`; `read(path)` gets it back.
  2. Every writer of a product (calibrated frames, masters, stacks, spectra, light curves, tables, figures' data)
     calls it; a test lists the writers and fails for one without provenance.
  3. `core/citations.py`: a table `method → BibTeX key, short text` for every algorithm in the program (kept next to
     the code that uses it by a decorator `@cites("kwee1956", "mikulasek2014")`); `resources/citations.bib`.
  4. Project window: "Methods text…" builds the paragraphs for the selected products ("The frames were corrected
     for bias, dark and flat field with … version …; aperture photometry … radii of …; times were converted to
     BJD_TDB following Eastman et al. (2010) …") in English, with the BibTeX file; the text comes from templates per
     step in `resources/methods/` filled with the recorded parameters.
  5. "Reproduce…" on a product: runs its chain again into a new folder and compares (bit-identical or the largest
     difference).
- **Accept:** for the practice night the methods text names every step with its real parameters and compiles with
  the `.bib`; "Reproduce" gives identical files; a FITS product read in DS9 shows the history cards.
- **Files:** `core/{provenance,citations}.py`, writers in every area, `resources/citations.bib`,
  `resources/methods/*.txt`, `ui/shell/project/…`, tests.

### ARC-12. Scripting surface: Python API and command line  (P1)
**open**
- **Ours now:** `__main__.py` (argparse: files, `--smoke-test`, `--benchmark`, `--check-online`, `--observatory`), `engine/automation.py` (run chains), project re-run in the Project page.
- **Why:** AD-11; `astrowb-cli` only opens files, runs the smoke test, the benchmark and the observatory.
- **Reference:** IRAF CL scripts and parameter files; `siril-cli -s script`; AstroImageJ macros; PypeIt's
  `pypeit_setup` / `run_pypeit` with a reduction file; `lightkurve`'s object API.
- **Build:**
  1. `astrowb/api/__init__.py`: one function per step with real signatures and docstrings generated from the step
     registry plus hand-written high-level helpers (`calibrate_night(folder, out)`, `light_curve(files, target, …)`,
     `period_search(lc, method=…)`); returns plain values / small result objects with `.to_table()`, `.plot()`,
     `.save()`. Stable: covered by `tests/test_api_stability.py` (a stored list of names and parameters; removals
     fail).
  2. Command line: `astrowb-cli steps` (list with one-line help), `astrowb-cli help <step>` (inputs, parameters,
     defaults), `astrowb-cli run <step> key=value … [--project P] [--json]`, `astrowb-cli recipe <file.json|.toml>
     [--set key=value]`, `astrowb-cli session <file.session.json> --run` (re-run a saved session without the
     window). Exit codes: 0 ok, 2 usage, 3 an `AppError` (printed with its code and advice), 4 a crash (trace to
     `error.log`). Progress on stderr; `--quiet`.
  3. Recipes: `core/recipe.py` — a list of step calls with links between outputs and inputs (the automation format
     of `engine/automation.py`, extended, not replaced); every area window gets File → "Save as recipe…" (from its
     session state, ARC-5) and Edit → "Copy as Python" (the `astrowb.api` calls of the last action or of the whole
     session).
  4. Documentation generated from the registry: `docs/api/*.md` and the guide's "Scripting" page (four languages for
     the prose; the reference tables stay English).
- **Accept:** the practice night runs from one recipe on the command line and gives the same tables as the windows
  (bit-identical CSV); "Copy as Python" pasted into a file runs; `astrowb-cli run photometry.light_curve --help`
  shows every parameter with its unit and default.
- **Files:** `api/`, `core/recipe.py`, `__main__.py` (subcommands), `engine/automation.py`, docs, tests.
- **Depends on:** ARC-5 for the session part.

### ARC-13. Errors by code  (P1)
**open — reduced (agent3, 2026-11-10, see "Changed from the plan")**
- **Why:** AD-7. `ui/messages.py` matches English engine messages against 400 templates with regular expressions.
- **Build:**
  1. `core/errors.py`: `class AppError(Exception)` with `code` (dotted, e.g. `photometry.star_off_frame`), `values`
     (dict), `advice_code` optional; `str()` gives the English text from the catalogue so logs stay readable.
     `class AppWarning` likewise for non-fatal notes collected in a step's output (`ctx.warn(code, **values)`).
  2. `resources/messages/en.toml`: `code = { what = "…{name}…", do = "…" }`; the catalogue is the source for
     translation (`tools/i18n.py` extracts it into the `.ts` files under the context `Messages`).
  3. `ui/kit/errors.py`: `show(error, parent)` → an InfoBanner or a dialog with what happened, what to do, a
     "Details" fold (code, values, traceback), "Copy", "Report a problem".
  4. Migration area by area (sub-steps ARC-13.1 devices, .2 calibration, .3 photometry, .4 timeseries, .5
     spectroscopy, .6 models, .7 the rest): each `raise ValueError("…")` a user can meet becomes an `AppError`;
     its old template is removed from `messages.py`; `tests/test_messages.py` is replaced by: every code raised in the
     source exists in the catalogue (static scan), has `what` and `do`, and is translated in three languages.
  5. Third-party exceptions that reach the user (Astropy, photutils, OS errors) are wrapped at the step boundary
     into codes by a mapping table (`core/errors.wrap`), with the original text under Details.
- **Accept:** `ui/messages.py` is gone; a test raises every code and renders it in four languages without a missing
  placeholder; changing the English wording of a message changes no behaviour.
- **Files:** `core/errors.py`, `resources/messages/`, `ui/kit/errors.py`, all `raise` sites, `tools/i18n.py`, tests.
- **Changed from the plan (agent3, 2026-11-10, told to the owner):** the step's reason — "a changed word in an
  engine message silently loses its translation" — is already guarded: `tests/test_messages.py::
  test_every_engine_error_has_a_template` walks every `raise` with a message in the engine (242 today) and fails when
  one has no template, so a reworded message cannot pass the tests. Rewriting all 242 raise sites into codes would be
  churn with no gain for the user. What the user does miss is the **what to do** part and one consistent error
  window. The step is therefore reduced to:
  1. `ui/messages.py` gets an `ADVICE` table: template → one or two lines of what to do (written for the 60 most
     frequent errors first — the ones the tests' message list and the guide's troubleshooting chapter name — then
     the rest area by area as each window is rebuilt); `translate()` keeps working as it is; `advice(text)` returns
     the translated advice or nothing.
  2. `ui/kit/errors.py` (with UI-3): `show(error_text, parent)` → an `InfoBanner` (in the view concerned) or a dialog
     with what happened (translated), what to do (advice), a Details fold (the original English text and the
     traceback), Copy and Report a problem. Every `on_fail` of the windows goes through it as each window is
     rebuilt (UI-16).
  3. New engine code may raise `core.errors.AppError(template, **values)` (a `ValueError` whose message is the
     filled template), so that template and code cannot drift; existing raises are converted only when touched.
  4. A test: every template in `ADVICE` exists in `TEMPLATES`; every advice is translated into Turkish.
- **Accept (reduced):** the 60 first advices exist in English and Turkish; the error window shows them; the
  existing template test stays green.

### ARC-14. Services layer: catalogues and archives in one place  (P1)
**open**
- **Ours now:** `mirrors.py` (CDS → Harvard / IDIA fall-back, remembered server), `gaia.py` (VizieR or ESA archive, cache), separate queries in `overlays.py`, `photometry/catalog.py`, `planning/ephemerides.py`, `timeseries/{archive,surveys}.py`, `spectroscopy/{templates,mkstandards,atmosphere}.py`.
- **Why:** AD-9. Queries live in `gaia.py`, `mirrors.py`, `overlays.py`, `photometry/catalog.py`,
  `planning/ephemerides.py`, `timeseries/{archive,surveys}.py`, `spectroscopy/{templates,mkstandards,atmosphere}.py`,
  each with its own time-outs and caches.
- **Build:**
  1. `services/base.py`: `Service` with `name`, `mirrors`, `timeout`, `rate limit`, `licence / how to cite`,
     `fetch(request) → bytes` through one HTTP helper (certifi, retries with back-off, a per-session memory of the
     mirror that answered); `services/cache.py`: an on-disk cache keyed by the request (SQLite index + files, size
     cap 2 GB by default, "Clear cache" in Settings), with an age per service (catalogues: forever; ephemerides:
     7 days; light-curve archives: 1 day).
  2. Offline mode: Settings → "Work offline" and automatic detection; a query then answers from the cache or raises
     `services.offline` naming what is needed; every window that can use cached data says "from cache, fetched on
     <date>".
  3. Modules: `gaia` (DR3 cone, proper motion to epoch, GSPC synthetic photometry; written release-aware: the
     table names and columns of a data release live in one table, because **Gaia DR4** — all epoch photometry in
     G / BP / RP, epoch radial velocities and spectra for all sources — has an announced release date (ESA,
     2026-05-07 news; check cosmos.esa.int/web/gaia/dr4) and must be adoptable by adding its entry: epoch photometry
     then becomes a light-curve source in PER-1 and epoch velocities a source in SPE-15), `simbad`, `vizier` (generic
     table cone), `vsx`, `gcvs`, `apass`, `refcat2`, `panstarrs`, `skymapper`, `ucac4`, `tycho2`, `landolt` /
     `stetson` standards, `aavso_vsp` (sequences), `aavso_webobs`, `exoplanet_archive`, `exoclock`, `etd / varastro`,
     `mast` (TESS / Kepler light curves, pixel files, TESScut), `ztf`, `asassn`, `atlas`, `gaia_epoch_photometry`,
     `horizons`, `mpc` (orbits, observatory codes), `skybot`, `hips2fits` / DSS, `eso_archive`, `lco_archive`,
     `phoenix` / spectral libraries, `nist_asd` (lines), `iers` (ARC-1). Each returns `core.table.Columns` with units.
  4. The project records every fetch (service, request, date, rows) so that the methods text can cite the
     catalogues (ARC-11).
  5. Help → "Check the installation and internet services" reads this registry.
  6. Tests use recorded responses (`tests/data/services/<service>/…`), refreshed by `tools/record_services.py` when
     run with network.
- **Accept:** `grep -R "astroquery\|urllib\|requests" src/astrowb` finds the network only under `services/`; the
  practice workflows run offline after one online run; every service appears in the installation check.
- **Files:** `services/*`, the callers listed above (moved, their public functions kept), tests.

### ARC-15. Time, coordinates and units: one policy, one converter tool  (P1)
**open**
- **Reference:** Eastman, Siverd & Gaudi 2010 (PASP 122, 935) for BJD_TDB / HJD / JD_UTC differences and the
  online converters; AstroImageJ's Coordinate Converter window (object → coordinates, site, time in every standard,
  airmass, altitude, hour angle, Moon); IAU SOFA / ERFA.
- **Ours now:** `timing.py` (mid-exposure, BJD_TDB, HJD, airmass, header conventions).
- **Build:**
  1. `core/units.py`: named conversions used everywhere — `jd_utc ↔ bjd_tdb ↔ hjd_utc ↔ bjd_utc ↔ hjd_tdb` for a
     position and site (through Astropy; documented accuracy), `air ↔ vacuum` wavelength (Ciddor 1996 and Morton
     2000, the one used stated in outputs), `flux ↔ magnitude` with errors, velocity frames (observed, barycentric,
     heliocentric, LSR).
  2. A `TimeStandard` enum carried by every table column of times (unit string `d (BJD_TDB)`); joining two series
     with different standards converts or refuses with `time.mixed_standards` — never silently.
  3. Tools → "Time and coordinate converter…" (in every window's Tools menu): object by name or coordinates, site
     from the profiles, a date / time in any standard → all the others, plus altitude, azimuth, hour angle,
     airmass, parallactic angle, Moon distance and phase, barycentric velocity correction; batch mode: paste a
     column of times, get the converted column.
  4. Reading published minima: HJD (UTC or TT unknown) is the rule in old literature; the converter and O−C offer
     "HJD, time scale unknown: assume UTC" with the size of the possible error (up to ~69 s since 2017) shown.
  5. **Header times read without guessing** (found 2026-11-10 in `timing.start_time` / `mid_time`): (a) `TIMESYS`
     is honoured (UTC default; TT, TAI, TDB, GPS converted; an unknown value is an error naming it) — today every
     header time is taken as UTC; (b) the mid-exposure time is taken, in this order, from `DATE-AVG` / `MJD-AVG`
     (FITS standard), `JD-MID` and the known mid-time keywords of capture programs (CAL-2's table), then from the
     mean of `DATE-OBS` and `DATE-END` when both exist and agree with the exposure time within 20 % (this covers
     dead time, co-adds and stacks, where start + EXPTIME / 2 is wrong), then start + EXPTIME / 2; which rule was
     used is recorded per frame and shown in the Frames table; (c) stacked or co-added frames (`NCOMBINE`,
     `STACKCNT`, our own stacks) take the flux-weighted mean mid-time their writer stored, never start + EXPTIME /
     2 of the sum; (d) a series whose time stamps repeat, run backwards or step unevenly beyond 3 × the median
     cadence is flagged in the Frames stage.
  6. **One airmass function** `core/units.airmass(altitude, formula = "young1994")` used by Photometry, Planning and
     Observing (today `timing.airmass` is the plane-parallel sec z from a geometric altitude, and Planning uses sec z
     with Pickering's formula below 30°): Young 1994 (Appl. Opt. 33, 1108) as default, sec z, Hardie 1962, Kasten &
     Young 1989 and Pickering 2002 as choices; the formula's name is written beside every airmass column. Sec z is
     3 % too large at altitude 10° and grows without limit towards the horizon.
- **Accept:** a header with `TIMESYS = 'TT'` gives times 69.184 s earlier in UTC than the same header without it
  (2017 onwards); a co-added frame with `DATE-OBS`, `DATE-END` and dead time gets the mid-point of the two; the
  airmass formulas equal their papers' tabulated values and each other within 0.1 % above altitude 30°;
  conversions agree with Eastman's on-line applets' published test values and with `astropy` to 1 ms;
  the tool's batch mode converts 10^5 times in < 1 s; mixing standards in a join raises the code.
- **Files:** `core/units.py`, `timing.py`, `ui/shell/tools/converter.py`, tests, guide 13.

### ARC-16. Profiles: site, equipment, observer  (P1)
**open**
- **Ours now:** the Planning window's site (and `planning/sites.py`), gain / read noise typed in Photometry, observatory set-up JSON (`devices/setup.py`); settings in `settings.py`.
- **Why:** AD-10.
- **Reference:** N.I.N.A. profiles (equipment, astrometry, image file pattern, focal length, pixel size);
  MaxIm DL site and optics settings; AAVSO report headers (observer code, telescope, camera); MPC observatory codes.
- **Build:**
  1. `core/profiles.py`: `Site` (name, latitude, longitude east-positive, height, time zone, MPC code, horizon
     profile as azimuth–altitude pairs, typical seeing and sky brightness per filter, extinction coefficients per
     filter with date), `Optics` (aperture, focal length, reducer, central obstruction), `Camera` (sensor name,
     pixel size, format, binning modes, gain per mode in e⁻/ADU, read noise, dark current at temperature, full well,
     saturation and linearity limits in ADU, shutter type and delay, colour mosaic pattern, time-stamp convention:
     start / middle / end, clock offset), `FilterSet` (names as written in headers ↔ standard bands, zero points,
     focus offsets), `Spectrograph` (kind, dispersion axis, slit, grating, resolving power, lamp list),
     `Observer` (name, AAVSO code, MPC contact, affiliation). Stored as JSON in the user data folder and copied into
     a project on first use (a project is self-contained).
  2. Settings → Profiles (UI-13): lists, add / duplicate / edit / import / export; "Fill from a FITS header" reads
     what a header gives; the equipment pixel scale is computed and compared with a plate solution when one exists
     ("the header says 0.62″/px, the solution 0.57″/px: use the solution?").
  3. Every window takes its defaults from the active profiles and shows which profile it used; a value typed in a
     window overrides for that session only and offers "Save to the profile".
  4. Camera numbers measured by the detector tools (CAL-9) are offered to the profile.
- **Accept:** entering a site and equipment once is enough for Planning (visibility, exposure calculator),
  Photometry (gain, saturation, time stamp), Observing (headers written) and the AAVSO / MPC reports; old settings
  (the Plan page's site, the Photometry page's gain) migrate into a profile named "Default".
- **Files:** `core/profiles.py`, `ui/shell/settings/profiles.py`, the windows' controllers, migration, tests.

### ARC-17. Diagnostics: logs, traces, the problem report  (P2)
**open**
- **Ours now:** `error.log` from `__main__._show_unexpected_errors`, `ui/report.py` (problem-report zip), task errors with tracebacks under Details.
- **Build:** a rotating structured log (`app.log`: time, level, area, code, message) besides `error.log`; a task
  timeline (start, end, CPU seconds, peak memory of the worker, GPU used) kept per session and shown in Tasks →
  "Details"; "Why was this slow?" lists the phases a step reported (`ctx.phase("reading")`); the problem report
  (existing) adds the last 500 log lines, the profiles without personal names, `gpu-report.json`, the session
  state of the window in front (paths anonymised unless the user ticks otherwise).
- **Accept:** a deliberately slow step shows its phases; the report of a provoked error is enough to reproduce it
  from `data/` (checked by an agent following only the report).
- **Files:** `core/log.py`, `engine/tasks.py`, `ui/report.py`, tests.

### ARC-18. Translation quality  (P1)
**open**
- **Why:** four languages are a promise; machine-filled strings drift ("mukayese" had to be replaced in 28 places).
- **Build:**
  1. `resources/i18n/glossary.toml`: the astronomy terms and their fixed translation per language (comparison star
     = karşılaştırma yıldızı = Vergleichsstern = estrella de comparación; check star = kontrol yıldızı; light curve
     = ışık eğrisi; time of minimum = minimum zamanı; airmass = hava kütlesi; aperture = açıklık; sky annulus = gök
     halkası; plate solve = astrometrik çözüm; radial velocity = dikine hız; limb darkening = kenar kararması;
     eclipsing binary = örten çift; … at least 150 entries, written by reading Turkish, German and Spanish
     astronomy texts: TÜBİTAK / TUG pages and Turkish university lecture notes, the Sternfreunde / BAV glossary, the
     SEA / AAVSO Spanish manuals). The owner reviews the Turkish column once.
  2. `tools/translation_review.py` (exists) extended: fails when a source string contains a glossary term and its
     translation does not contain the fixed term; lists strings longer than 1.6× the English (risk of cuts);
     lists identical translations for different sources.
  3. Pseudo-locale test: every string lengthened by 40 % and accented; the layout tests run with it to find cuts
     before a translator does.
  4. Plural forms and number formats: numbers through `QLocale` only in labels, never in exported files (files use
     `.` decimals always).
- **Accept:** review tool green; the pseudo-locale layout test green at 1366 × 768; no decimal comma in any file
  written under a German locale (test).
- **Files:** `resources/i18n/glossary.toml`, `tools/translation_review.py`, `tests/test_layout_fits.py`,
  `tests/test_locale_files.py`.

### ARC-19. Screens, scaling, accessibility  (P2)
**open**
- **Build:** tests at device pixel ratios 1, 1.25, 1.5, 2 (Qt `QT_SCALE_FACTOR`) and with the Windows default font
  metrics (`Segoe UI` 9 pt emulated by a fixed font with its widths); minimum hit target 28 px; every control
  reachable by Tab in reading order (a test walks the focus chain of every window); accessible names on icon-only
  buttons; contrast of text ≥ 4.5 : 1 in both themes (a test computes it from the tokens); a colour-blind-safe
  default palette for plots and roles (target / comparison / check distinguished also by shape and label).
- **Accept:** the tests exist and pass; the owner's Windows machine shows no cut text at 125 % (owner to try).
- **Files:** `tests/ui/test_scaling.py`, `tests/ui/test_focus_chain.py`, `ui/kit/theme.py`.

### ARC-20. Packaging, optional data packs, updates  (P2)
**open**
- **Ours now:** PyInstaller bundles; Inno Setup, dmg, AppImage; distro containers; "Check for updates" on request.
- **Build:**
  1. Data manager (Settings → Data): optional packs with size, licence, source and "used by": synthetic spectra
     (PHOENIX subset), MK standards, Pickles library, limb- and gravity-darkening tables (Claret), model-atmosphere
     passband intensities (MOD-6), isochrone and bolometric-correction tables (EXO-6), offline catalogue index
     for plate solving (AST-2), telluric templates (SPE), spectrophotometric standards (SPE), sample data per area.
     Download with resume and checksum, stored in the user data folder or a folder the user chooses (a shared disk
     at an observatory); works offline from a copied folder.
  2. Installer size budget: < 350 MB; start-up budget kept (lazy imports test).
  3. Linux: besides AppImage, a Flatpak manifest and an Arch `PKGBUILD` (CachyOS is the owner's system); Windows:
     a portable zip besides the installer; `winget` manifest prepared (publishing is the owner's decision).
  4. Update check stays on request; when a newer release exists: what changed (the Turkish / English notes of the
     release) and the download link; no silent self-update.
  5. Signing: scripts ready for a certificate; unsigned until the owner decides.
- **Accept:** each pack installs, verifies, is found by its user and can be removed; the installers pass the smoke
  test on every CI system; the Arch package builds in the `archlinux` container job.
- **Files:** `core/datapacks.py`, `ui/shell/settings/data.py`, `packaging/`, CI.

### ARC-21. Guide, tutorials and sample data for every area  (P2)
**open**
- **Build:** one practice set per area, small, generated or public with licence, downloaded by the data manager:
  eclipsing-binary night (exists, synthetic), a real transit night (Qatar-1, 24 frames), a long-slit set (EFOSC2),
  an échelle set (TOFES), a radial-velocity series of a double-lined binary, a list of minima (a real star with an
  LTTE), a TESS light curve of a pulsator, light and velocity curves of a detached and of a contact binary, an
  asteroid field (Eros). Each guide chapter gets a "Try it" exercise with the expected result (a number to find);
  the tour offers "Open the practice data" in each window's empty state (UI-6). Screenshots regenerated by
  `tools/guide_screenshots.py` for every release (four languages). A PDF of the guide per language built in CI.
- **Accept:** a test runs every exercise by script and finds the expected number; the guide has no screenshot older
  than the last interface change (the tool stamps them with the commit).
- **Files:** `resources/guide/*`, `sampledata.py`, `tools/guide_screenshots.py`, CI.

### ARC-22. Security and privacy  (P2)
**open**
- **Build:** a written statement in Help → About and the guide: no telemetry; network only for the services the user
  starts (and ARC-1's weekly table if left on); plugins and recipes run with the user's rights — the Plugins dialog
  shows the file path and a warning before the first run of a new or changed plugin (hash remembered); the
  observatory API keeps token + TLS pinning (exists) and gets rate limiting and a lock-out after repeated wrong
  tokens; `pip-audit` on the locked dependencies in the weekly CI job.
- **Accept:** tests for the plugin prompt and the API lock-out; the audit job runs.
- **Files:** `engine/plugins.py`, `ui/plugin_dialog.py`, `devices/server.py`, CI.

### ARC-23. Speed harness  (P1)
**open**
- **Ours now:** `tools/speed.py`.
- **Build:** `tools/speed.py` becomes a benchmark suite with named cases bound to the budgets above (data generated
  or from `data/`), results written to `speed/<date>-<commit>.json` (machine described); `tools/speed.py compare A B`
  prints the differences; CI runs the generated-data cases on Linux and fails when a case is more than 1.5× slower
  than the stored baseline for that runner class (baseline updated on purpose); peak memory measured with
  `tracemalloc` + the worker's RSS.
- **Accept:** every budget row has a case; a deliberately slowed function turns CI red.
- **Files:** `tools/speed.py`, `speed/baseline-ci.json`, CI.

### ARC-24. Repository hygiene  (P3)
**open**
- **Build:** `README.md` and `docs/` checked against the new structure; `CONTRIBUTING.md` points to PLAN.md and this
  file; `docs/PLUGINS.md` regenerated from the API docs (ARC-12); the 880 MB of observations in the history stay
  (rewriting needs a force-push the owner's settings forbid) — `data/README.md` keeps the blob-filter advice.
- **Accept:** a newcomer following README + CONTRIBUTING reaches a green test run in one try (tested in a clean
  container).
- **Files:** `README.md`, `CONTRIBUTING.md`, `docs/`, `data/README.md`

### ARC-25. German and Spanish: the one translation pass before 1.0  (P1 for 1.0)
**open** — not before the windows of stage S2 are rebuilt (the texts change until then); decided by the owner on
2026-11-10 (PLAN.md R0).
- **Why:** translating texts that will be replaced is wasted work; one pass at the end, with the glossary, is cheaper
  and more consistent.
- **Ours now:** German and Spanish `.ts` files complete up to 2026-11-10 (texts after that are unfinished there);
  guide in four languages up to that date; `tools/fill_translations.py`, `tools/translation_review.py`.
- **Build:**
  1. ARC-18's glossary with German and Spanish columns complete first.
  2. Every unfinished German and Spanish string translated with the glossary; every string that changed in English
     since its translation (Qt marks them obsolete / unfinished) reviewed.
  3. The guide's German and Spanish chapters brought to the same sections and content as English (the test of
     `tests/test_ui.py::test_guide_categories_translations_and_search` back to requiring all four languages).
  4. The tests' language lists back to `tr`, `de`, `es` (`ui/i18n.py` `COMPLETE`); screenshots of every window in
     German and Spanish looked at; UI-18's review in both languages.
- **Accept:** 0 unfinished in all three `.ts` files; guide test strict for four languages; gallery test green in
  German and Spanish.
- **Files:** `resources/i18n/app_{de,es}.ts`, `resources/guide/{de,es}/`, `ui/i18n.py`, `tests/test_ui.py`.

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(nothing yet)
