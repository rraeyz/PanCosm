# Times of minimum and O−C: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.5).

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

Two things that belong together: **measuring times of minimum (and maximum)** from light curves — one night, or
years of survey and space data — and **analysing them**: ephemerides, O−C diagrams, period changes, third bodies,
apsidal motion, magnetic cycles, with errors a referee accepts and tables ready for a paper.

**Goal:** more complete than OCFit, Peranso's extremum tools, the Czech and Krakow O−C services and the private
codes behind most O−C papers — and the only tool where a minimum measured tonight is on the star's O−C diagram,
with the literature minima, one click later.

## What the reference programs and the literature do

Read (never copied): OCFit (Gajdoš & Parimucha 2019, OEJV 197, 71: classes `FitLinear`, `FitQuad`, `OCFit` with
models LiTE3, LiTE34 (two bodies), LiTE3Quad, AgolInPlanet / AgolExPlanet (TTV), Apsidal; genetic algorithm then
MCMC; no start values needed); Peranso (extremum: Kwee–van Woerden, polynomial; O−C sheet); AVE (Barberá: KvW,
"sliding integrations", bisector chords); Nelson's Minima and O−C spreadsheets; the O−C Gateway / VarAstro (Paschke
& Brát 2006, OEJV 23; database of minima with per-star downloads); Kreiner's Atlas of O−C diagrams (Kreiner 2004,
AcA 54, 207) and TIDAK (Krakow); the BAV Lichtenknecker Database; B.R.N.O.; Zasche et al.'s method papers; the
Kepler / TESS eclipse-timing papers.

| Topic | Method and source | Ours now |
| --- | --- | --- |
| One eclipse, dense data | Kwee & van Woerden 1956 (BAN 12, 327); its error is too small for noisy data (Mikulášek et al. 2014, CoSka 43, 382; Deeg 2021, Galaxies 9, 1: revised error) | `minima.kwee_van_woerden` with bootstrap error (the larger of the two) |
| | polynomial through the bottom | `polynomial_minimum` |
| | phenomenological eclipse model of Mikulášek 2015 (A&A 584, A8): depth, width, kurtosis-like shape parameters, fitted with the time | none |
| | symmetric functions: Gaussian, Lorentzian, their sum (as AVE and many national groups) | none |
| | bisector of chords at several depths ("tracing paper"), with the bisector's slope as a symmetry check | none |
| | trapezoid for flat-bottomed transits and total eclipses | `trapezoid_fit` (with detrending terms) |
| | the full light-curve model shifted in time | PHO-26 (exact transit / sphere model) |
| Sparse survey data | template method: a phase-curve template (from the star's own folded data or a model) fitted to chunks of data in time; one minimum per chunk (Zasche et al. 2014, A&A 572, A71 "AFP") | none |
| Long continuous series | every eclipse timed in its window with a template; odd / even kept apart (Gies et al. 2012; Rappaport et al. 2013; Conroy et al. 2014; Borkovits et al. 2016) | `each_minimum` (window per eclipse, chosen timer) |
| Maxima of pulsators | polynomial / Fourier-template maximum per cycle | `fourier.times_of_maximum` |
| Ephemeris | weighted linear and quadratic least squares; errors scaled by √χ²ᵣ | `ephemeris.fit` |
| Mass transfer, mass loss | dP/dt from the quadratic term; conservative transfer rate Ṁ = M₁M₂ / [3 (M₁ − M₂)] · Ṗ/P; non-conservative forms (Tout & Hall 1991) | Q and dP/dt only |
| Third body | light-travel-time effect (Irwin 1952, ApJ 116, 211; 1959): A, P₃, e₃, ω₃, T₃; mass function; minimum mass; two bodies; with a parabola | `oc_models.fit_ltte` (one body, linear ephemeris, grid in P₃, emcee) |
| Apsidal motion | Giménez & García-Pelayo 1983 (Ap&SS 92, 203) to e⁵ with inclination; Giménez & Bastero 1995; Lacy 1992 (exact, numerical); sidereal vs anomalistic period; internal-structure constant k₂; relativistic term (Giménez 1985) | `fit_apsidal` first order in e, i = 90° |
| Magnetic cycles | Applegate 1992 (ApJ 385, 621); energy test (Völschow et al. 2016, A&A 587, A34) | none |
| Abrupt period changes | segmented linear ephemerides with jump epochs | none |
| Dynamical triples | perturbations on the P₁²/P₂ time scale besides LTTE (Borkovits et al. 2015, 2016) | none |
| Weights without errors | by method, e.g. visual 1, photographic 3, photoelectric / CCD 10 (as in Zasche's and Kreiner's analyses) | a default error for all |
| Time standards | old minima are HJD (UTC, sometimes unknown); modern BJD_TDB (Eastman et al. 2010) | times taken as given |
| Sources of minima | O−C Gateway / VarAstro, Kreiner's atlas, TIDAK, BAV LkDB, B.R.N.O., AAVSO EB section (Nelson's O−C files), IBVS, OEJV, BAVM, JAAVSO, Kepler EB catalogue ETVs | typed or pasted text, file; VSX ephemeris look-up |

## What we already have (do not redo)

- `timeseries/minima.py`, `ephemeris.py`, `oc_models.py` (above), step `timeseries.oc_fit`, minimum step in
  `photometry/steps.py`; the O−C window (`ui/oc_page.py`) with menus Ephemeris, Models, File → Export; minima timed
  in Photometry arrive by themselves; MCMC runs without freezing; checked on KIC 6525196 (801 Kepler minima; P₃ =
  418.3 d against ~418 d) and AI Dra (42 TESS minima).

## Decisions

- Internally every time of minimum is BJD_TDB with a known conversion history; the table shows the original value
  and standard beside it.
- A minimum is a record (OC-1), not a line of text; the text box is replaced by a table.
- Model fits always report: parameters with errors, χ², reduced χ², BIC, the number of minima by kind and method,
  the weights used, and the time standard.

## To ask the owner

- Which databases of minima the owner's group uses most (to order OC-4's importers) and a typical star with a rich
  O−C history for the guide's exercise.

## For the owner to try

- After OC-W and OC-4: type a star's name, fetch its minima, add tonight's, fit; compare with your own O−C plot of
  that star.

## Data used

- KIC 6525196 (Kepler, 801 minima; LTTE), AI Dra TESS sector 24 (42 minima) — from the history.
- To add (each with `SOURCE.md`): literature minima of a classical LTTE system and of an apsidal-motion system with
  published solutions (to reproduce the published parameters); a W UMa star with a parabolic O−C and published
  dP/dt; a TESS two-year series of a short-period binary for ETV.

## Steps

Order of work: OC-W, then P1: 1, 2, 3, 5, 6, 7, 8, 12; P2: 4, 9, 10, 11, 13, 14; P3: 15, 16.

### OC-W. The O−C window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.5: stages Minima, Ephemeris, Models, Uncertainty, Report; O−C diagram with residuals;
  result tabs Minima table, Parameters, Correlations.
- **Extra accept:** star name → minima fetched (OC-4, or a file for now) → ephemeris fitted → LTTE fitted → table
  exported in **six clicks**; symbols distinguish primary / secondary and the method; a click on a point selects its
  table row and the reverse; points can be left out and brought back (undo).
- **Depends on:** ARC-4.6, ARC-5, ARC-6, ARC-8, UI-1 … UI-4, OC-1.
- **Files:** `ui/oc/{window,controller,state,menus}.py`, `ui/oc/panels/{minima,ephemeris,models,uncertainty,report,parameters}.py`, `tests/ui/walks/oc.py`, guide 07

### OC-1. A minimum is a record  (P1)
**open**
- **Ours now:** `ephemeris.Minimum(time, error, kind, source)`; `parse_minima(text)`.
- **Build:**
  1. `timeseries/minima_table.py`: columns `time_original`, `standard_original` (HJD_UTC | HJD_TT | HJD unknown |
     BJD_TDB | BJD_UTC | JD_UTC | JD geocentric), `bjd_tdb`, `error`, `error_assumed` (bool), `kind` (I | II),
     `method` (ccd | pe | pg | vis | dslr | space | unknown), `filter`, `timing` (kvw | poly | model | template |
     other), `observer`, `source` (reference text or bibcode), `weight`, `use`, `note`; a stable id per row.
  2. Conversion of every time to BJD_TDB with the star's coordinates (ARC-15); "HJD unknown" is treated as HJD_UTC and
     the possible error (TT − UTC, up to 69 s) is added in quadrature to the row's error and said in a banner.
  3. Readers that detect the layout: our own ECSV / CSV; free text with columns in any order (a column-mapping
     dialog when the detection is unsure: preview of the first rows, pick what each column is); the layouts of the
     services in OC-4; clipboard paste of a table from a paper (PDF copy: handles `2 4xx xxx.xxxx`, `xxxxx.xxxx` with
     an implied 2 400 000, `±` errors, `(3)` errors in units of the last digit, `p` / `s` / `pri` / `sec` / `I` /
     `II`, footnote marks).
  4. Default errors by method when none is given (editable in the Minima stage): visual 0.004 d, photographic
     0.003 d, photoelectric 0.0010 d, CCD 0.0005 d, space 0.0001 d; rows using a default have `error_assumed`.
  5. Duplicates (same eclipse reported twice, within 0.002 d and the same kind) are marked and one is unticked with
     the reason; half-integer / integer epoch conflicts with the declared kind are marked (a primary that falls at
     phase 0.5 of the reference ephemeris).
  6. Writers: ECSV; CSV; LaTeX table (BJD_TDB, error, epoch, O−C, kind, method, reference) for a paper; the plain
     layouts of OEJV / IBVS-style lists and of the BAV and B.R.N.O. submission forms (read their current
     instructions; write the exact column list under this step).
- **Accept:** each of ten stored example texts (papers' tables in the common styles, each service's export) parses
  to the expected records; HJD_UTC → BJD_TDB equals the Astropy computation within 0.1 s for 1900–2030; round trip
  through ECSV is exact; a pasted table with `(3)` errors and implied 2 400 000 reads right.
- **Files:** `timeseries/minima_table.py`, `timeseries/ephemeris.py`, UI minima panel, tests.

### OC-2. Timing one eclipse: every method, honest errors, a verdict on symmetry  (P1)
**partial** — done (2026-11-12): `timeseries/timing_methods.py`: `time_minimum(t, y, err, method)` → TimingResult
(time, the largest of the analytic, bootstrap and prayer-bead errors, all three, branch coverage, depth S/N, notes)
for kvw, mikulasek (Mikulášek 2015), polynomial (order 2–8 by BIC, Newton on the derivative, error propagated to
the root), gaussian, lorentzian, bisector (7 levels), trapezoid; methods without a model of their own resample
about the better of a Gaussian and a Mikulášek fit (the mirror-symmetric curve, smoothed, when neither fits);
`compare_methods`: every method, their error-weighted χ²ᵣ ("disagree" above 9: a shape that does not suit reports a
large error and weighs little) and the bisector's tilt from 20 % to 80 % of the depth with its error ("asymmetric"
beyond 3 σ); `timeseries.minimum` takes every method (recipes, command line). Tests: at S/N 50 with one branch covered
to 60 %, 60 realisations, each suited method unbiased within 0.3 × its error and its error 0.7–1.7 × the scatter.
**Found:** Mikulášek's model is biased by 0.5–0.8 σ with one branch covered to 60 % (its shape against a Gaussian
or a trapezoid, with a free baseline slope): KvW stays the default; the bisector's error is 4 × too large on a flat
bottom; the bisector's tilt from a 2 % spot asymmetry (8 s at depth 0.3) is below its error at S/N 100 with 160
points (10 s) — the acceptance's 2 % holds only for denser or better data (5 % at S/N 600 with 400 points is found).
Left: Deeg's revised KvW error, the automatic window and the trend fitted with the model, the timing panel and its
"Compare methods" table in the windows, the 500-realisation acceptance with the W UMa shape, the speed check.
- **Ours now:** `minima.kwee_van_woerden` (with bootstrap error), `polynomial_minimum`, `trapezoid_fit` (with covariates), `each_minimum`.
- **Read first:** Kwee & van Woerden 1956; Mikulášek et al. 2014 (KvW: to use or not to use); Deeg 2021; Mikulášek
  2015 §2–3 (the model functions and their use for timing); the AVE manual's description of its methods.
- **Build:**
  1. `timeseries/timing_methods.py` (one interface: `time_minimum(t, y, err, method, **options) → TimingResult(t_min,
     error, error_kind, quality, model_curve, notes)`): `kvw` (have; add Deeg's revised error as the analytic
     error), `polynomial` (order 2–8 chosen by BIC, error from the fit covariance and bootstrap), `gaussian`,
     `lorentzian`, `gauss+lorentz`, `mikulasek` (the 2015 model with depth, width, shape exponent and a linear
     trend; the default for V-shaped and for flat-bottomed eclipses alike), `bisector` (chords at 6–10 depths; the
     mean and the slope of the bisector), `trapezoid` (have), `model` (PHO-26), `template` (OC-3).
  2. A common pre-step: choose the window (automatic: from the half-depth width × 1.5 around the deepest smoothed
     point, shown as a draggable range), remove a linear or quadratic trend fitted outside the eclipse **together**
     with the model where the method allows.
  3. Errors: analytic, bootstrap of residuals (default 500 samples), and the "prayer-bead" (residual shift) estimate
     for correlated noise; the reported error is the largest, and the Inspector shows all three.
  4. "Compare methods": runs all applicable methods and shows a table and the spread; when the spread exceeds 3 ×
     the reported error a banner says the eclipse is asymmetric or badly covered (with the bisector slope and the
     coverage of each branch in per cent).
  5. Quality flags: branch coverage (< 30 % on one side → "one branch only: time unreliable"), points in eclipse,
     depth / noise, a gap at the bottom.
  6. Used by: Photometry's Timing stage, the Light curves window (Minima job), `each_minimum`, recipes.
- **Accept:**
  1. Synthetic eclipses (detached V-shaped, total flat-bottomed, W UMa-like, transit) × S/N 20 / 50 / 200 × full
     and 60 % one-sided coverage, 500 realisations each: for every method the bias is < 0.3 × its reported error and
     the reported error is within 0.8–1.3 × the actual scatter (the existing "honest errors" test extended to all
     methods).
  2. The asymmetry banner fires on an eclipse with a spot-induced asymmetry of 2 % and not on symmetric ones.
  3. One minimum with bootstrap < 0.3 s; "Compare methods" < 2 s.
- **Files:** `timeseries/timing_methods.py`, `minima.py`, steps, UI timing panel, tests, guide 07 and 13.

### OC-3. Many minima from long or sparse series  (P1)
**open**
- **Reference:** Zasche et al. 2014 (template fitted to data chunks); Gies et al. 2012 and Conroy et al. 2014
  (Kepler eclipse timing with a template per star); Borkovits et al. 2016 (odd / even averaging to suppress spots).
- **Ours now:** `minima.each_minimum(t, y, t0, period, timer, window)`.
- **Build:**
  1. `timeseries/etv.py`: `template_from_fold(t, y, period, t0)` (the folded curve smoothed: binned median with a
     penalised spline, primary and secondary separately, each with its own half-width); `time_by_template(chunk)`:
     shift (and optionally depth scale and a local polynomial baseline) fitted by least squares, error from χ²
     curvature and bootstrap.
  2. Dense continuous data (TESS, Kepler): one minimum per eclipse window; cadence integration of the template for
     30-minute data; eclipses with gaps or flagged cadences are skipped with the reason; the template is rebuilt
     once after a first pass with the first-pass times (iteration converges the period).
  3. Sparse data (ASAS-SN, ZTF, SuperWASP, Hipparcos, NSVS): chunks of N nights / M points chosen so that each
     chunk has ≥ 10 points in each eclipse; one primary and one secondary time per chunk at the chunk's mean epoch.
  4. Light curves window job "Minima of the whole series": choose data sets, period and T0 (from PER or VSX), run;
     results table with a thumbnail of each fit (click to inspect, untick bad ones); "Send to O−C".
  5. Native / vectorised speed: all eclipses of a sector in one batch.
- **Accept:** KIC 6525196: the LTTE solution from our own timings equals the stored one (P₃ within its error) and
  the scatter of the residuals is not larger than with the current code; 801 minima in < 20 s (was 125 s);
  synthetic ASAS-like sparse series (300 points over 8 years, LTTE of amplitude 0.01 d injected): the amplitude and
  P₃ recovered within 2σ; TESS two-year series of the set to add gives the published ETV amplitude.
- **Files:** `timeseries/etv.py`, `minima.py`, steps, UI (Light curves window job), tests.
- **Depends on:** OC-2.

### OC-4. Literature minima from the services  (P2)
**open**
- **Read first:** each service's current way to get one star's minima (VarAstro portal — successor of the O−C
  Gateway — "Minimas" pages and exports; Kreiner's atlas pages; TIDAK; BAV LkDB download; AAVSO's O−C files by B.
  Nelson; the Villanova Kepler EB catalogue ETV files) and its terms of use; write under this step what is
  reachable by program, in which format, and how each asks to be cited.
- **Build:** `services/minima_*.py` (ARC-14): one module per service that can be queried by program; for the others
  an importer of the file the user downloads by hand (the Minima stage's "From databases…" dialog lists every
  service with either "Fetch" or "Open the page / import the file" and the citation line); merged into the table
  with source, duplicates marked (OC-1.5); cached; the project records what was fetched and when.
- **Accept:** for three well-observed stars the merged table has no duplicate ticked twice and every row carries its
  source; recorded responses make the tests run offline; the report (OC-12) lists the services to cite.
- **Files:** `services/minima_*.py`, UI dialog, tests.

### OC-5. Ephemeris: linear, quadratic, higher order, segmented; significance  (P1)
**open**
- **Ours now:** `ephemeris.fit` (linear / quadratic, weighted, centred epochs).
- **Build:**
  1. Weights: from errors; or by method (a table of relative weights the user can edit; default 1 / 3 / 10 for
     visual / photographic / electronic) — the choice is shown and written in the report; robust option (Huber loss,
     and iterative 3σ rejection with the rejected rows unticked visibly).
  2. Models: linear; quadratic with dP/dt in d/yr and s/century and P/Ṗ in years; cubic; **segmented linear** with K
     break epochs (K = 1…4; breaks fitted on a grid; each segment's period with error; ΔP/P of each jump) for abrupt
     period changes.
  3. Model comparison: χ², reduced χ², BIC, AIC for each; an F-test for the quadratic against the linear
     ephemeris with its probability; a one-line verdict ("the parabola is preferred: ΔBIC = −41").
  4. Epoch handling: epoch numbers from the reference ephemeris with a warning when the cycle count is ambiguous
     (O−C beyond ± 0.25 P at long gaps); secondary minima at half-integer epochs, with an optional fitted offset
     of the secondary from 0.5 (eccentric orbits) reported as e cos ω ≈ (π/2)(φ₂ − 0.5).
  5. Mass-transfer estimates when masses are known (typed or from MOD): conservative rate and its direction, the
     non-conservative forms as options; time scales.
  6. "Update the ephemeris": the new T0 (chosen near the middle or at the latest minimum) and P with errors, in the
     form observers use (`Min I = BJD_TDB 24xxxxx.xxxxx(x) + 0.xxxxxxxx(x) E`), sent to Planning on request.
- **Accept:** synthetic minima with a known dP/dt (W UMa-like) and with a period jump: parameters within 1σ in 95 %
  of 200 realisations; the F-test rejects a parabola on linear data at the 1 % level in ≤ 2 % of realisations; the
  published dP/dt of the W UMa set is reproduced within its error.
- **Files:** `timeseries/ephemeris.py`, UI ephemeris panel, tests.

### OC-6. Light-travel-time effect: complete  (P1)
**open**
- **Read first:** Irwin 1952 and 1959; Mayer 1990 (BAICz 41, 231: practical formulas, mass function); OCFit's model
  list (which combinations exist); Zasche & Wolf 2007 (combination with astrometry).
- **Ours now:** `oc_models.fit_ltte` (one body + linear ephemeris; P₃ grid; eccentric starts; emcee).
- **Build:**
  1. Models: LTTE; LTTE + quadratic; two LTTE orbits (third and fourth body); two LTTE + quadratic. Parameters per
     orbit: P₃, T₃, e₃, ω₃, A = a₁₂ sin i₃ / c (days), with e sampled as √e cos ω, √e sin ω.
  2. Global search before the local fit: differential evolution (SciPy) over P₃ ∈ [0.5 × the data span / N_min, 3 ×
     span], with the linear parameters solved analytically inside — no start values needed (as OCFit's genetic
     step); then Levenberg–Marquardt; then MCMC (EXO-5's sampler with the convergence test, shared).
  3. A periodogram of the O−C residuals after the polynomial (GLS, PER engine) with false-alarm levels, shown as a
     tab, to justify a periodic term before fitting it.
  4. Derived with errors (from the posterior): a₁₂ sin i₃ (AU), mass function f(m₃), minimum third mass and the mass
     for i₃ = 60° and 30° given M₁ + M₂ (typed or from MOD), a₃, the semi-amplitude of the systemic-velocity
     variation, the angular separation at a given distance (Gaia parallax fetched) and the expected magnitude
     difference of a main-sequence third star of that mass (a rough check against third light in MOD — said to be
     rough); orbit coverage (number of cycles observed) with a warning below 1.5 cycles; stability of the hierarchy
     (period ratio; Mardling & Aarseth 2001 criterion when masses are known).
  5. The diagram draws the model, the polynomial part and the LTTE part separately on request, with the 1σ band
     from the posterior, and extends them into the future (prediction with its band) — and to Planning ("next
     minimum of the LTTE orbit's extremes").
- **Accept:** synthetic LTTE (e₃ = 0.4, 2.3 cycles covered, CCD-like errors) and LTTE + parabola: all parameters
  within 1.5σ in 90 % of 100 realisations without start values; the classical LTTE system's published P₃, A, e₃
  reproduced within the published errors; two-body synthetic case recovered; global + local fit of 300 minima
  < 10 s; MCMC 20 000 steps < 30 s.
- **Files:** `timeseries/oc_models.py`, UI models panel, tests, guide 07.

### OC-7. Apsidal motion: complete  (P1)
**open**
- **Read first:** Giménez & García-Pelayo 1983 (equations 15–21: the series to e⁵ with the inclination terms);
  Giménez & Bastero 1995 (Ap&SS 226, 99: weighted fitting, use of both minima); Lacy 1992 (AJ 104, 2213: the exact
  method: times of conjunction from Kepler's equation); Giménez 1985 (ApJ 297, 405: relativistic term); Claret &
  Giménez 2010 and Claret 2019 (theoretical k₂).
- **Ours now:** `fit_apsidal`: first order in e, i = 90°.
- **Build:**
  1. The exact numerical model (Lacy): for given Pₛ, T0, e, ω₀, ω̇ and i, the times of primary and secondary
     conjunction of each epoch by solving for the true anomaly of minimum projected separation; this is the default.
     The Giménez series kept as a fast twin and a check (test: they agree to 1e-6 d for e < 0.3).
  2. Fit of T0, Pₛ, e, ω₀, ω̇ (deg / cycle) with i fixed (typed or from MOD); grid over e and ω̇ for the global
     minimum (the well-known e–ω̇ degeneracy is shown as a χ² map), then LM and MCMC; a prior on e from the light
     curve (MOD: e cos ω from the secondary's phase, e sin ω from the durations) can be added.
  3. Derived: anomalistic period Pₐ = Pₛ / (1 − ω̇/360°), apsidal period U (years) with error, ω̇ in deg/yr; with
     masses and radii (typed or MOD): the relativistic term ω̇_rel and its share, the classical term, the observed
     mean internal-structure constant log k̄₂,obs, to compare with tabulated models (the user types the theoretical
     value; a note says where such tables are published).
  4. Combined model apsidal motion + LTTE (hierarchical triples with eccentric inner orbits).
  5. Diagram: primary and secondary branches drawn separately with the model curves.
- **Accept:** synthetic eccentric system (e = 0.25, U = 80 yr, i = 85°) from exact conjunction times: parameters
  within 1.5σ; the published apsidal-motion system's ω̇ and e reproduced within the published errors; exact model
  for 500 minima < 5 ms per evaluation (native Kepler solver).
- **Files:** `timeseries/oc_models.py`, UI, tests.

### OC-8. Uncertainties and correlations  (P1)
**open**
- **Build:** for every model: errors from the covariance (scaled), bootstrap of residuals, and MCMC (the shared
  sampler, EXO-5: affine-invariant ensemble or differential-evolution MCMC, Gelman–Rubin R̂ < 1.01 and ≥ 1000
  effective samples before it stops, or a warning with the reached values); priors per parameter (uniform bounds,
  Gaussian); a corner plot and a correlation table; an "error inflation" option that adds a jitter term in
  quadrature fitted with the model (when minima errors are underestimated) and reports it; the chain is saved with
  the session (compressed) so that plots reopen without resampling.
- **Accept:** on synthetic data the 68 % intervals contain the truth in 62–74 % of 300 realisations for each
  parameter of the LTTE and the apsidal model; a non-converged run says so and does not print intervals as final.
- **Files:** `timeseries/oc_uncertainty.py`, `core/inference/` (EXO-5), `timeseries/oc_models.py` (old `_posterior` removed after migration), `tests/coverage/test_oc_coverage.py`

### OC-9. Magnetic cycles (Applegate) as a tested alternative  (P2)
**open**
- **Read first:** Applegate 1992; Lanza 2006 (MNRAS 369, 1773); Völschow et al. 2016 (the two-zone energy
  criterion and its fitting formulas).
- **Build:** for a cyclic term of period P_mod and amplitude A: ΔP/P = 2π A / P_mod; with the active star's mass,
  radius, temperature and luminosity (typed or MOD): the required change of the quadrupole moment, the angular
  momentum transfer, the energy ΔE and the ratio ΔE / (L P_mod) by Applegate's formulas and by Völschow's
  criterion; a verdict "energetically feasible / not feasible" with the numbers; cyclic but not strictly periodic
  modulations can be modelled with a damped / quasi-periodic sinusoid as an alternative to LTTE and compared by BIC.
- **Accept:** the worked examples of Völschow et al. (their table values for well-known systems) are reproduced
  within 5 %.
- **Files:** `timeseries/applegate.py`, `ui/oc/panels/models.py`, `tests/test_applegate.py`

### OC-10. Short-period triples: dynamical delays  (P3)
**open**
- **Read first:** Borkovits et al. 2015 (MNRAS 448, 946) and 2016 (MNRAS 455, 4136): the analytic dynamical term
  for hierarchical triples, its amplitude ∝ P₁²/P₂.
- **Build:** the quadrupole-order dynamical delay added to LTTE for P₂ / P₁ < ~100 with the mutual inclination as a
  parameter; a warning in OC-6 when the fitted P₃ makes the dynamical term comparable to LTTE (estimated
  amplitude ratio shown).
- **Accept:** the term reproduces the published curve of a known compact triple from its published parameters
  within the plot's accuracy; the warning fires for P₃ / P₁ = 30 and not for 3000.
- **Files:** `timeseries/oc_dynamical.py`, `tests/test_oc_dynamical.py`

### OC-11. Cyclic and general terms; periodogram of residuals  (P2)
**open**
- **Build:** sinusoid(s) + polynomial as a quick model (for first looks and for pulsators' O−C); the residual
  periodogram tab (OC-6.3) for every model; "Fit the highest peak as LTTE" one click; O−C of maxima for pulsating
  stars with the same tools (period change rates of RR Lyrae / δ Scuti / Cepheids in d/Myr; the Blazhko-like
  modulation via the periodogram).
- **Accept:** a synthetic RR Lyrae O−C with dP/dt = 0.3 d/Myr is recovered within 1σ; the guide shows the case.
- **Files:** `timeseries/oc_models.py` (cyclic terms), `timeseries/methods/gls.py` (residual periodogram), `tests/test_oc_cyclic.py`

### OC-12. Report: tables and figures for a paper, and for observers  (P1)
**open**
- **Ours now:** `ui/oc_page.py` → Export results (CSV / LaTeX through `ui/export.save_results`), the O−C plot's publication figure.
- **Build:** the minima table (OC-1.6 writers); the parameters table with errors in the journal style (value(err)
  and ± forms), for every fitted model side by side; the O−C figure through `ui/plot/publish` (two-panel: O−C with
  model, residuals; top axis in years; symbols by kind and method with a legend); the new ephemeris line; the
  methods text (ARC-11: which timing method, weights, time standard, models, sampler settings, references to cite,
  services used); "new minima of this work" as a separate table ready for IBVS / OEJV / BAVM-style lists and the
  B.R.N.O. / BAV submission layouts; predictions of the next minima for the coming month at the site (to Planning).
- **Accept:** the LaTeX tables compile in AASTeX and A&A classes (stored expected text); the figure passes the
  publication checks of ARC-6; every number in the table equals the session's value at the printed precision.
- **Files:** `timeseries/oc_report.py`, `timeseries/minima_table.py` (writers), `resources/methods/oc_*.txt`, `tests/test_oc_report.py`

### OC-13. Exoplanet transit timing in the same window  (P2)
**open**
- **Build:** a "Transits" mode: mid-times (from PHO-26, EXO, ExoClock / ETD / literature lists) against a linear
  ephemeris; fit of a refined ephemeris with the covariance between T0 and P and the propagated uncertainty of
  future transits (the "ephemeris drift" plot); tests for a quadratic term (orbital decay: dP/dt in ms/yr with the
  tidal quality factor estimate) and periodic TTVs (periodogram with false-alarm level; sinusoid fit); export in the
  ExoClock / literature table style. Shares all machinery of OC-5, OC-8, OC-11.
- **Accept:** the published decay rate of WASP-12 b is reproduced from the published mid-times list within its
  error; a linear-only system gives no significant term.
- **Files:** `timeseries/transit_timing.py`, `ui/oc/panels/` (Transits mode), `tests/test_transit_timing.py`

### OC-14. From the literature's ephemerides to tonight  (P2)
**open**
- **Ours now:** `planning/ephemerides.vsx` (VSX ephemeris look-up) used by the O−C window's Look up button.
- **Build:** the Minima stage's "Star" field resolves the star (services), shows the VSX / GCVS / Kreiner ephemeris
  and type, the Gaia distance, known multiplicity notes (WDS / literature flags when in SIMBAD), and how many minima
  each service has; "What changed since the catalogue ephemeris?" shows the O−C of the newest minima against it —
  the quickest answer to "is the ephemeris still good for planning?".
- **Accept:** for three stars the panel fills from recorded responses; offline it shows what the cache has.
- **Files:** `timeseries/star_context.py`, `services/{vsx,gcvs,simbad,gaia}.py`, `ui/oc/panels/minima.py`, tests with recorded responses

### OC-15. Joint analysis with the light and velocity curves  (P3)
**open**
- **Build:** links to MOD: e and ω from apsidal analysis as priors for the light-curve model and the reverse; LTTE
  orbit + third light + systemic-velocity drift checked for consistency in one summary table; a combined fit is out
  of scope until MOD supports timing as a data set (MOD-17).
- **Accept:** the summary table for a synthetic triple shows consistent third-body evidence from the three sides.
- **Files:** `timeseries/oc_consistency.py`, `models/` (links), tests

### OC-16. Speed and scale  (P3)
**open**
- **Build:** 10 000 minima (Kepler short-period binaries) plot and fit interactively: vectorised models, native
  Kepler solver, decimated drawing through `PlotView`; MCMC on 10 000 minima < 60 s.
- **Accept:** the budgets written here are met on the reference machine.
- **Files:** `tools/speed.py` cases, `timeseries/oc_models.py`, `native/` (Kepler solver use)

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`; O−C window as interface I6d (4))
