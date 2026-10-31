# Validation: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done".

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

How we know the program is right, and how we keep knowing it: the data sets, the reference programs run beside
ours, the tolerances, the end-to-end science cases, the statistics of our error bars, the tests that use the
program as a user does, and the report a professor can read.

**Goal:** for every number the program reports, there is a named comparison with an independent source and a test
that fails when the agreement is lost. "Validated" is never a claim in a commit message; it is a row in a table
that CI regenerates.

## Principles (binding)

1. **Three kinds of evidence, all required** for a science feature: (a) synthetic data with known truth; (b) real
   public data compared with a published value; (c) the same data through an established program.
2. **Reference programs are run beside ours, never inside:** IRAF, PHOEBE, the Wilson–Devinney program, ellc,
   JKTEBOP, batman, EXOFASTv2's published outputs, the reference TLS package, lightkurve, Astropy / ccdproc /
   photutils (as independent scripts), GDAL, astrometry.net — each in its own environment
   (`tools/reference_env.sh`), their reduced outputs committed as small tables with the script that made them.
3. **A tolerance is decided before the comparison** and written in the step; a failure is investigated, not
   widened away. Widening a tolerance needs a written reason under the step and the architect's or owner's yes.
4. **Error bars are tested by coverage:** over many simulated data sets the stated 68 % intervals must contain the
   truth 68 % of the time (within sampling error).
5. **Agreement between reference programs is measured too:** where PHOEBE and WD differ by 3 × 10⁻⁴, we cannot
   demand 1 × 10⁻⁵ of ourselves against either — the table shows all pairs.
6. **Real data are never committed** (rule R11); only links, checksums and reduced reference tables.

## What we already have (do not redo)

- `tests/validation/test_iraf_phot.py` with the IRAF table of the HAT-P-32 night; the CI job `validation` that
  downloads that night; `data/` with `SOURCE.md` notes for sixteen sets; the results table of the second full test
  round (`docs/history/HANDOFF-2026-11.md`: IRAF ccdred identical; BANZAI 0.92 ADU; `phot` 0.06 %; SPOC 0.02 %;
  HARPS DRS 22 m/s; ORB6; JPL Horizons 0.01°; and more) — those comparisons were made by scripts in a container
  that no longer exists: VAL-4 turns each into a permanent test.

## To ask the owner

- Which of the owner's own solved cases (an AstroImageJ light curve, a PyWD solution, an IRAF-reduced spectrum, a
  published O−C analysis of the group) may be used as private validation cases in `data/owner/` (never committed,
  never copied; only the comparison numbers are written into the plans).

## For the owner to try

- Generated: `docs/validation/for-the-owner.md` collects every "For the owner to try" entry of all plan files with
  its state (VAL-6).

## Steps

Order of work: VAL-1, 2, 3 in stage S1 (with the foundation); VAL-4, 7, 8 as the areas reach them; VAL-5, 6, 9
before each release; VAL-10 for 1.0.

### VAL-1. The data registry and one command to fetch  (P1)
**partial** — done (2026-11-12): `data/registry.toml` (14 sets: id, title, area, source — LCO archive by file name, a URL, a tar / zip archive, or manual for ESO and NIST — and the exact files of each SOURCE.md; SHA-256 recorded for the sets fetched here: Eros, SA 98, FLOYDS, AI Dra, Kurucz); `tools/fetch_data.py <id> | --area A | --all [--into DIR] [--record]` (into `data/<id>/` or `$ASTROWB_DATA`; a verified file is never fetched again, a changed one is; what cannot be fetched is listed with why); `tests/test_data_registry.py` keeps the registry and the notes in step and checks the fetch logic. Found: one FLOYDS file (`…-0001-e00_1d.fits`) is not in the LCO archive under that name; STScI's server fails certificate checks from this network (Pickles). Left: checksums of the large sets (Qatar-1, Palomar, TOFES), CI caching and the per-area validation matrix.
- **Ours now:** `data/` with a `SOURCE.md` per set and `data/README.md` (download commands by hand); CI's validation job downloads the HAT-P-32 night.
- **Build:** `data/registry.toml`: for each set: id, title, areas, source URLs (with mirrors), licence and
  citation, size, the exact files with SHA-256, how it is used (tests' names), and whether CI fetches it;
  `tools/fetch_data.py <id>|--area photometry|--all [--into DIR]` downloads with resume into `data/<…>/` (or a
  shared cache folder named by `ASTROWB_DATA`), verifies checksums, never re-downloads a verified file, and prints
  what is missing when a source is unreachable from this network (with the mirror to try); the `SOURCE.md` files
  stay as the human notes and are checked against the registry by a test; CI caches the fetched sets between runs
  and runs the validation job per area in a matrix (weekly for the large ones, on every push for those under 200
  MB in total).
- **Accept:** a fresh container runs `tools/fetch_data.py --area photometry` and then `pytest -m validation -k
  photometry` green without any other instruction; a corrupted file is detected and re-fetched.
- **Files:** `data/registry.toml`, `tools/fetch_data.py`, `tests/test_data_registry.py`, CI.

### VAL-2. Reference environments  (P1)
**open**
- **Build:** `tools/reference_env.sh <program>`: creates an isolated environment outside the repository's own
  (`~/.cache/astrowb-reference/<program>`): IRAF (`apt-get install iraf iraf-noao`), PHOEBE 2, ellc, batman, the
  TLS reference package, lightkurve, JKTEBOP and the Wilson–Devinney program (built from their authors' public
  sources with the container's Fortran compiler), GDAL tools, astrometry.net (with a small index for the test
  fields), EXOFASTv2 (not run: IDL; its published example outputs are used), MOOG / Find_Orb (only for the P3
  adapters); `tests/validation/scripts/<program>/*.py|.cl|.sh` regenerate each reference table and write a
  manifest (program version, date, command line, input checksums) next to it; a test fails when a reference table
  has no manifest or its script is missing; **nothing of these programs is imported by our package or its tests**
  (a test greps the imports).
- **Accept:** each reference table in the repository can be regenerated by one documented command in a fresh
  container and reproduces the committed numbers (within the programs' own run-to-run variation).
- **Files:** `tools/reference_env.sh`, `tests/validation/scripts/`, `tests/test_reference_manifests.py`.

### VAL-3. The tolerance tables and the generated report  (P1)
**partial** — done (2026-11-12): the `measured` fixture (`tests/validation/conftest.py`) writes each test's rows (area, quantity, compared with, tolerance, measured, verdict, data, step, test, versions) to `validation-results/`; `tools/validation_report.py` builds the report beside this table, a planned row whose step no test names is "not yet tested"; the CI validation job uploads it as `validation-report`. Rows written now: IRAF `phot` centres, fluxes and errors, the HAT-P-32 b mid-time. Left: rows for every other validation test as they come, the guide's chapter "How results are checked", the report attached to a release.
- **Build:** every validation test writes its measured differences to `validation-results/<test>.json` (quantity,
  reference, tolerance, measured, data set, versions); `tools/validation_report.py` builds `docs/validation/
  report.md` (one table per area: quantity, compared with, tolerance, measured, verdict, test id, data set) and
  the guide's chapter "How results are checked" in four languages (the prose translated once, the tables
  generated); CI uploads the report as an artifact on every validation run and commits nothing; the release
  procedure (PLAN.md R12) attaches the report of the release commit. The initial content of the tables is the
  list below — each row must point to a test when its step is done.

| Area | Quantity | Compared with | Tolerance | Step |
| --- | --- | --- | --- | --- |
| Calibration | calibrated pixel values | IRAF `ccdproc` | identical to float precision | CAL-21 |
| Calibration | combine with each rejection method | IRAF `imcombine` | 1e-4 ADU | CAL-5 |
| Calibration | variance plane | empirical variance of repeats | 3 % | CAL-13 |
| Photometry | aperture flux, error, centre | IRAF `phot` | 0.1 %, 10 %, 0.05 px | photometry item 1 (done), PHO-41 |
| Photometry | PSF fluxes in a crowded field | IRAF `daophot.allstar` | 2 % (S/N > 50) | PHO-18 |
| Photometry | BJD_TDB | Astropy independent script, Eastman's values | 1 ms | ARC-15 |
| Photometry | transit mid-time, depth | literature / AstroImageJ on the same curve | 1σ, 30 s | PHO-26 |
| Photometry | pixel-file light curve | SPOC SAP | 0.02 % rms | PHO-32 |
| O−C | LTTE, apsidal, parabola parameters | published solutions | published errors | OC-5, OC-6, OC-7 |
| O−C | interval coverage | simulation | 62–74 % for 68 % | OC-8 |
| Period | each periodogram | Astropy, the reference TLS package, published tables | per PER-3 | PER-3 |
| Period | false-alarm levels | simulation | factor 2 at 1 % | PER-4 |
| Period | frequencies of a δ Scuti campaign | published / Period04 | published errors, 1e-6 c/d | PER-6 |
| Spectroscopy | extraction, wavelengths | IRAF `apall` / `identify`; ESO DRS | 1 %, 0.1 px; 25 m/s rms | SPE-24 |
| Spectroscopy | radial velocities | standards, DRS | 5 m/s scatter (HARPS), 0.3 km/s (R ≈ 30 000) | SPE-14 |
| Spectroscopy | flux calibration | PESSTO / a third standard | 5 % | SPE-10 |
| Spectroscopy | Teff, log g, [Fe/H] | Gaia benchmark stars | 150 K, 0.3, 0.15 dex | SPE-17 |
| Models | Roche light curves | PHOEBE 2, WD, ellc | 1e-4 (detached), 3e-4 (contact) | MOD-9 |
| Models | solutions of benchmark binaries | published | published errors | MOD-21 |
| Exoplanets | transit model | brute-force integration, batman | 1e-8 / its stated error | EXO-1 |
| Exoplanets | global fit | EXOFASTv2 published example | 1σ, widths ± 25 % | EXO-7 |
| Exoplanets | host-star M, R | benchmark stars | 7 %, 4 % | EXO-6 |
| Astrometry | positions of Eros | JPL Horizons | 0.15″ rms | AST-4 |
| Astrometry | plate solutions | astrometry.net | 0.3 px at corners | AST-1 |
| Planning | almanac, events | JPL Horizons; stored prediction pages | 1 min; 1–2 min | PLN-14 |
| Observing | scenarios end safe | — | all | OBS-18 |
| Remote sensing | geometry, radiometry | GDAL, independent scripts | rounding; 1e-6 | RS-14 |

- **Accept:** the report builds from a validation run; a row without a test is listed as "not yet tested" — the
  1.0 release needs zero such rows for P1 steps.
- **Files:** `tools/validation_report.py`, `tests/validation/conftest.py` (the JSON writer fixture), guide 13.

### VAL-4. Gold paths: from raw data to a published number  (P1)
**open**
- **Why:** unit comparisons can all pass while the chain is wrong (a time-stamp convention, a unit, a flipped
  axis). The second test round of 2026-11-06 proved the chain by hand; these make it permanent.
- **Build:** recipes (AUT) + tests, each run from the command line as a user would, asserting the final number:
  1. raw LCO frames of the Qatar-1 night → calibrated → light curve → transit fit → mid-time against the ExoClock
     ephemeris (within 1σ and 1 min);
  2. HAT-P-32 raw frames → light curve identical to the IRAF-validated table → transit time;
  3. the practice eclipsing-binary night → time of minimum within its error of the truth → O−C with a literature
     list → the injected LTTE recovered;
  4. a TESS pixel file → light curve → period → folded curve → minima → O−C (AI Dra: P against the literature);
  5. raw EFOSC2 long slit → extracted, wavelength- and flux-calibrated spectrum against PESSTO's;
  6. raw HARPS frames → order extraction → wavelengths against the DRS → velocities of τ Ceti;
  7. FEROS spectra of AI Phe → SB2 velocities → orbit; with the TESS light curve → Roche solution → masses and
     radii against Maxted et al. 2020;
  8. EXOFASTv2's HAT-P-3 example files → global fit → the published table;
  9. Eros frames → solved → measured → ADES; positions against Horizons;
  10. a Sentinel-2 tile → NDVI → classes; statistics against the reference.
- **Accept:** each path is one command (`astrowb-cli recipe gold/<n>.toml`) and one test; the weekly CI job runs
  them all; their final numbers are the first rows of the generated report.
- **Depends on:** the areas' steps each path uses (a path is added when its steps are done), ARC-12, VAL-1.
- **Files:** `resources/recipes/gold/*.toml`, `tests/validation/test_gold_paths.py`, `.github/workflows/validation-weekly.yml`

### VAL-5. The science changelog  (P1)
**open**
- **Build:** at every release the gold-path numbers and the tolerance tables' "measured" columns are stored in
  `docs/validation/history/<version>.json`; `tools/validation_report.py --diff A B` lists every number that moved
  by more than a third of its tolerance; the release notes get a "Science changes" section from it (in Turkish for
  the owner and in English): what changed, by how much, why. A release with an unexplained movement is not made.
- **Accept:** a deliberate change of the sky estimator moves the photometry rows and appears in the diff; the
  release procedure in PLAN.md R12 names this check.
- **Files:** `tools/validation_report.py` (`--diff`), `docs/validation/history/`, `PLAN.md` R12 (procedure line)

### VAL-6. What only the owner can check  (P1)
**open**
- **Build:** `tools/owner_checklist.py` gathers the "To ask the owner" and "For the owner to try" entries of every
  plan file into `docs/validation/for-the-owner.md` (Turkish headings and one-line Turkish summaries written by the
  agent who adds an entry; the state: waiting / done with the date and what was found); private comparison cases
  run from `data/owner/` by tests that are skipped when the folder is empty and that print only differences, never
  data.
- **Accept:** the file is regenerated by precommit and lists every entry of the plan files; a private case in
  `data/owner/` runs locally and is skipped in CI.
- **Files:** `tools/owner_checklist.py`, `docs/validation/for-the-owner.md` (generated), `tests/validation/test_owner_cases.py`

### VAL-7. Coverage of the error bars  (P1)
**open**
- **Build:** `tests/coverage/` (marker `slow`, weekly in CI): one harness that, for a fitting tool and a simulator
  of its data, runs N realisations and reports the fraction of truths inside the stated 68 % and 95 % intervals,
  the bias in units of the stated error, and the ratio of stated to actual scatter; applied to: aperture
  photometry errors, every minimum-timing method (OC-2), ephemeris and O−C models (OC-5 … OC-8), period and
  frequency errors (PER-4, PER-6), radial velocities (SPE-14) and orbits (SPE-15), line measurements (SPE-13),
  transit fits (PHO-26, EXO-7), binary solutions (MOD-14), astrometric positions (AST-3), the detector
  measurements (CAL-9). Results go to the report (VAL-3).
- **Accept:** every listed tool has a coverage row within its step's stated range.
- **Files:** `tests/coverage/harness.py`, `tests/coverage/test_*_coverage.py`, CI weekly job

### VAL-8. Using the program as a user, by script  (P1)
**partial** — done (2026-11-12): `tests/ui/harness.py` starts the real main window in a language, finds controls by
the guided tasks' names (bringing their tab or stage forward), clicks (check boxes on their box), types numbers as the
language writes them, clicks on images through the viewport, answers file dialogs, triggers menu commands by their
English text, waits for the tasks, and fails on message boxes, uncaught exceptions, labels / buttons / tooltips left
in English, clicks slower than 2 s; a screenshot after every action. Walks in English and Turkish: the practice night
(raw frames → time of minimum), the practice transit (suggested comparisons → ETD file), the long slit (arc lines
clicked on the plot, Hβ checked), frequencies, O−C third body, SB2 orbit, Images (open, bin, Undo, save). Its finds:
the plot toolbar's own matplotlib buttons spoke English in every language; Undo of an image operation in the Images
window did nothing (the page looked for the open file in its own window). Left: walks for Plan, Observe, Remote
sensing, Models, Automation, one real set per walk, German and Spanish, the gallery tool on the harness.
- **Build:** `tests/ui/harness.py` (the lost container script rebuilt and kept): start the real application
  offscreen, find controls by their accessible names / object names, click, type, drag on images and plots, wait
  for tasks, collect every dialog, banner and uncaught exception, take screenshots at each step, measure the time
  of each action; `tests/ui/walks/<area>.py`: the main workflow of each window on its practice data and on one real
  set, in four languages; failures show the last screenshot; the gallery tool (UI-15) reuses the harness.
- **Accept:** every area has a walk; a walk fails on any exception, any raw error text (a message without a code),
  any untranslated string, any action slower than its budget.
- **Files:** `tests/ui/harness.py`, `tests/ui/walks/*.py`, `tools/ui_gallery.py`

### VAL-9. The same numbers on every system  (P2)
**open**
- **Build:** the light gold paths (3 and a reduced 1) run in the CI test matrix on Linux x86 / ARM, Windows and
  macOS (Intel and Apple); final numbers must agree across systems within 1e-9 relative (float32 GPU paths within
  their documented tolerance); a difference names the first step where intermediate checksums diverge
  (provenance hashes of ARC-11 help).
- **Accept:** the matrix job is green; an injected platform-dependent rounding (a float32 cast on one system) is
  caught and located.
- **Files:** `.github/workflows/ci.yml` (matrix job), `tests/validation/test_cross_platform.py`

### VAL-10. The validation report for version 1.0  (P1 for 1.0)
**open**
- **Build:** a PDF (and the same as a guide chapter): purpose and method of the validation; the data sets with
  citations; one section per area with its tables, a figure of the main comparison, the known limits and the cases
  where we differ from a reference program and why; the coverage results; the gold paths; the list of algorithms
  with their references (from `core/citations`); in English, with a Turkish summary for the owner. Built by
  `tools/validation_report.py --pdf` from the results of the release commit.
- **Accept:** the PDF builds in CI; every P1 step of every area has a row; no row is "not yet tested".
- **Files:** `tools/validation_report.py` (`--pdf`), `docs/validation/report-template.md`, guide 13

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(nothing yet)
