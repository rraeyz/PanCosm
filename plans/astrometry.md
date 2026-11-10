# Astrometry and moving objects: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.11).

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

Where things are on the sky: plate solving of any frame (with hints, blind, offline), precise positions against
Gaia, asteroids and comets (finding them, measuring them, reporting them), double stars, and proper motions.

**Goal:** Astrometrica's reduction and reports, Tycho Tracker's synthetic tracking on the GPU, ASTAP-class solving
without installing anything — inside the same program that calibrated the frames and will measure the light curve.

## What the reference programs do

Read: Astrometrica's documentation (reference-star matching, plate constants: linear / quadratic / cubic fits,
residuals, object centroids by PSF fit, magnitudes from the catalogue zero point, known-object overlay from MPCORB,
"track and stack", blink, MPC report); Tycho Tracker's documentation and talks (synthetic tracking: stacking along
thousands of motion vectors on the GPU, detection and tracklet building, known-object matching, light curves,
ADES reports); Lang et al. 2010 (astrometry.net: geometric hashing of star quads, verification by Bayesian odds);
ASTAP's documentation (quad hashing with its own star databases, SIP, photometric calibration); Shao et al. 2014 and
Zhai et al. 2014 (synthetic tracking); Heinze et al. 2015 (digital tracking, statistics of false detections);
Bertin 2006 (SCAMP: distortion fits); the MPC's ADES documentation (PSV and XML, the required fields, catalogue and
band codes) and guide to minor-body astrometry; Veres et al. 2017 (astrometric error models); the WDS notes and the
JDSO author guide for double-star measures; Lindegren et al. 2021 (Gaia EDR3 astrometry, epoch propagation).

| Topic | Astrometrica | Tycho Tracker | ASTAP / astrometry.net | Ours now |
| --- | --- | --- | --- | --- |
| Solving | needs approximate centre and scale; catalogue from the internet | needs a solved or solvable frame | blind, offline with index / star databases | external ASTAP or astrometry.net if installed; built-in Gaia triangle match needing pointing and scale from the header |
| Plate model | linear, quadratic, cubic; residual report | from the solver | TAN + SIP | TAN fitted to matched stars; SIP refinement on Gaia |
| Moving objects | blink, known-object overlay, manual measurement, track and stack | automatic search over motion vectors (GPU), tracklets, known-object matching | — | two-click linear track with re-centring; SkyBoT overlay; residuals against a straight line |
| Magnitudes | catalogue zero point in a band | the same, light curves | catalogue calibration | none in the report |
| Reports | MPC 80-column and ADES | ADES | — | ADES PSV |
| Double stars | — | — | — | visual-orbit fit only (`models/visual.py`) |

## What we already have (do not redo)

- `astrometry.py` (external solvers; WCS copied into our header), `photometry/field.py` (`solve`, `identify`),
  `gaia.py` (`stars`, `at_epoch`, `refine_wcs` with SIP), `calibration/starmatch.py`, `photometry/moving.py`
  (`track`, `residuals`, `ades_psv`), `ui/moving_dialog.py`, `overlays.minor_planets` (SkyBoT),
  `devices/pointing.py` (centre a target, polar-alignment error). Eros on LCO frames measured
  (`data/astrometry/eros-lco`).

## Decisions

- One solving entry point `astrometry.solve(frame, hints)` used by every window; it tries, in order: the header's
  WCS if it verifies, the Gaia match with hints, the built-in blind solver with the offline index when installed,
  an external solver when installed — and says which succeeded.
- Positions are ICRS at the epoch of observation with Gaia DR3 proper motions and parallaxes applied to the
  reference stars; reports state the catalogue (ADES code for Gaia DR3) and the time as mid-exposure UTC.
- The program never submits observations by itself: it writes validated files and opens the submission page.

## To ask the owner

- The owner's MPC observatory code, if any (for the report header profile).

## For the owner to try

- After AST-W and AST-3: open the Eros frames, solve, measure, and look at the residual table.
- After AST-5 on the RTX 4050: run the synthetic-tracking search on a night of your own wide frames; send the GPU
  timing shown at the end.

## Data used

- `data/astrometry/eros-lco`. To add: a main-belt field with several faint known asteroids over ≥ 20 frames (for
  AST-5: positions checked against JPL Horizons); frames from five different telescopes / scales for solver tests;
  a wide pair of double stars with WDS measures; a multi-epoch set of a high-proper-motion star.

## Steps

Order of work: AST-W, then P1: 1, 3, 4, 6; P2: 2, 5, 7, 8; P3: 9, 10, 11.

### AST-W. The Astrometry window  (P1)
**open**
- `plans/interface.md` UI-16.11: stages Images, Solve, Find, Measure, Report; the same tools reachable from the
  Images window's Astrometry menu.
- **Extra accept:** the Eros set: open → solved by itself → known objects labelled → Eros measured on all frames →
  ADES file: **five clicks**.
- **Depends on:** ARC-4, ARC-5, ARC-7, ARC-8, UI-1 … UI-4.
- **Files:** `ui/astrometry/{window,controller,state,menus}.py`, `ui/astrometry/panels/{images,solve,find,measure,report}.py`, `tests/ui/walks/astrometry.py`, guide 05 (new chapter section) in four languages

### AST-1. Solving with hints: robust for any telescope  (P1)
**open**
- **Read first:** Groth 1986 and Valdes et al. 1995 (triangle matching: have); Lang et al. 2010 §2–3 (quads,
  verification by counting predicted against found stars); Calabretta & Greisen 2002 (TAN), Shupe et al. 2005
  (SIP); Astropy `fit_wcs_from_points`.
- **Ours now:** `field.solve`: needs pointing (header) and scale (FOCALLEN + XPIXSZ or a scale keyword); 40 bright
  stars; similarity transform; ≥ 8 matched stars; RMS ≤ 2 px.
- **Build:**
  1. Hints from everywhere: header pointing in any convention (CAL-2's table), the object name resolved, the
     equipment profile's scale, the user's typed field centre, the previous frame's solution (a series solves by
     continuity in milliseconds).
  2. Unknown scale: a ladder of trial scales (from 0.2 to 30 ″/px in steps of 15 %) with the matching statistic
     deciding; unknown rotation and parity always allowed; pointing error up to 2° (catalogue radius grows in
     steps); crowded and sparse fields (adaptive number of stars; magnitude-ordered subsets).
  3. Verification as astrometry.net: after a candidate transform, predicted catalogue stars against detected ones
     → a log-odds score; a solution is accepted only above a threshold (false-positive rate < 1e-6 by test).
  4. Model choice: TAN → TAN-SIP order 2–4 by BIC of the residuals with outlier rejection; residual table and
     vector plot; RMS in arcsec; the number of stars; scale, rotation (north angle), parity, field size written in
     words.
  5. Failure messages that help: `astrometry.too_few_stars` (n found; advice: longer exposure / stretch check),
     `astrometry.no_match` (which hints were used, what to try: type the centre, check the scale = …).
  6. Batch: many files with continuity and a results table.
- **Accept:** a test set of 60 frames from ten instruments (0.3–12 ″/px, fields 5′–5°, both parities, various
  header conventions; recorded Gaia responses): ≥ 95 % solved with header hints in < 3 s each; 0 false solutions on
  200 frames of pure noise / shuffled star lists; solutions agree with astrometry.net's (stored) within 0.3 px at
  the corners; RMS against Gaia ≤ 0.2 px for well-sampled frames.
- **Files:** `astrometry/{solve,verify,model}.py` (the package replaces `astrometry.py`, old names re-exported),
  `photometry/field.py` (calls it), tests.

### AST-2. Blind and offline solving  (P2)
**open**
- **Read first:** Lang et al. 2010 (index construction: healpix grid, quads at several scales, the 4-D hash code
  of a quad invariant to translation, rotation, scale; kd-tree lookup); ASTAP's description of its quad method and
  database tiers; Gaia DR3 data model.
- **Build:** `tools/build_star_index.py` (run by us, output published as data packs, ARC-20): from Gaia DR3
  (positions at J2016, proper motions, G, BP − RP), tiers by magnitude (to G = 11: ~1 M stars, bundled size check;
  to 14; to 16 as optional larger packs), stored in HEALPix tiles with a quad index per scale band; `astrometry/
  blind.py`: detect stars → form quads from the brightest → hash lookup → candidate transforms → verification
  (AST-1.3) → refinement; works with no header at all in < 20 s for fields ≥ 15′ with the G ≤ 14 pack; the same
  packs serve offline catalogue overlays and comparison stars (`services/gaia` falls back to the pack when
  offline).
- **Accept:** the 60-frame set with all header hints removed: ≥ 90 % solved (fields ≥ 15′) in a median < 8 s; no
  false solution on the noise set; the index tier sizes written in the data manager with their coverage.
- **Files:** `tools/build_star_index.py`, `astrometry/{blind,index}.py`, `services/gaia.py` (offline fall-back), `core/datapacks.py` entries, `tests/test_astrometry_blind.py`

### AST-3. Astrometric reduction of a frame  (P1)
**open**
- **Read first:** the MPC "Guide to Minor Body Astrometry" (what a good measurement needs: timing, reference
  stars, saturation, S/N); Veres et al. 2017; Lindegren et al. 2021 §3 (epoch propagation); Stone 1996 (centroid
  methods and their errors); Anderson & King 2000 (pixel-phase error).
- **Build:** `astrometry/reduce.py`: detect stars; match to Gaia DR3 at the frame's mid-exposure epoch (proper
  motion and parallax applied; `services/gaia` or the offline pack); reject saturated, blended and high-RUWE /
  duplicated-source stars from the reference set; fit the plate model (AST-1.4) with weights by centroid error;
  per-star residuals; the solution's uncertainty at any position (covariance of the fit propagated); an object's
  position: centroid by PSF (Moffat / Gaussian) fit or moments with its error (photon noise + background + the
  pixel-phase floor) ⊕ the solution's error at that place → RA, Dec with σ_RA, σ_Dec (arcsec) as ADES wants;
  differential chromatic refraction estimate for low altitudes (reported when > 0.05″); timing: mid-exposure UTC
  from `timing.mid_time` with the camera profile's time-stamp convention and an accuracy statement (the profile's
  clock offset and its uncertainty, OBS time-sync check).
- **Accept:** synthetic frames with a known distortion and star positions: recovered positions unbiased with
  errors within 0.8–1.3 × the scatter (S/N 5–200); Gaia stars left out of the fit are recovered within their
  predicted errors on real frames (cross-validation RMS reported: ≤ 0.1″ on the LCO frames).
- **Files:** `astrometry/{reduce,centroid}.py`, step `astrometry.reduce`, `tests/test_astrometry_reduce.py`

### AST-4. Known moving objects: overlay, measure, magnitudes  (P1)
**open**
- **Read first:** the SkyBoT service documentation (cone search at an epoch, observer location); JPL's small-body
  identification and Horizons APIs; the MPC's MPCORB format (for offline use); the MPC band and catalogue codes.
- **Ours now:** SkyBoT overlay; two-click track; linear-motion residuals.
- **Build:** all known objects in the field for each frame's time and the site (SkyBoT → JPL identification →
  local MPCORB propagated by a two-body + planetary-perturbation-free Kepler step as a last resort, with its lower
  accuracy stated), with predicted positions, rates, magnitudes; arrows of motion over the series; click an object
  → measured on every frame around its prediction (centroid as AST-3; frames where it is blended with a star or
  off the frame are flagged, not measured); for unknown objects: the two-click track (have) or tracklets from
  AST-5; residuals against the ephemeris (O − C in RA cos Dec and Dec per frame, mean and scatter) and against a
  great-circle motion fit; magnitudes from the frame zero point (IMG-5.4) in G or the frame's band with the MPC
  band code; trailed objects: a trail-fitting centroid (a line segment convolved with the PSF) when the motion
  during the exposure exceeds 1.5 FWHM, positions referred to mid-exposure.
- **Accept:** Eros on the LCO frames: O − C against JPL Horizons RMS ≤ 0.15″ with no systematic offset above 0.1″
  (our timing and reduction are right); a synthetic trailed object (trail 6 FWHM): mid-point within 0.1 px.
- **Files:** `astrometry/{known,measure,trail}.py`, `services/{skybot,horizons,mpc}.py`, `photometry/moving.py` (kept, calls the new code), UI measure panel, `tests/test_moving_objects.py`, `tests/validation/test_eros_horizons.py`

### AST-5. Finding what is not known: track-and-stack and synthetic tracking  (P2)
**open**
- **Read first:** Shao et al. 2014 (ApJ 782, 1); Zhai et al. 2014 (ApJ 792, 60); Heinze et al. 2015 (AJ 150, 125:
  the significance threshold against the number of trial vectors; matched filtering); Yanagisawa et al. 2005 (the
  median-stack variant that rejects stars); descriptions of Tycho Tracker's pipeline.
- **Build:**
  1. `astrometry/shiftstack.py` — **track and stack**: for a given motion (rate, position angle; from an ephemeris
     or typed), frames registered on the stars, shifted along the motion, combined (mean with rejection, or median)
     → the object as a point, stars as trails; measured on the stack with the effective mid-time and the motion
     removed.
  2. **Synthetic tracking**: preparation: register all frames on the stars; remove the static sky (subtract the
     star-aligned median image, mask residuals of bright stars and bad pixels); normalise by the noise map. Search:
     for every trial vector on a grid (rates 0 … v_max, all angles; grid step so that the smear over the series is
     < 1 px), shift-and-add the residual frames (GPU kernel through `compute`; CPU twin threaded) and record, per
     output pixel, the best S/N and its vector (a running maximum, so memory stays one image); detection: peaks
     above a threshold set from the number of trials (false-alarm rate chosen by the user, default one false
     candidate per run) ; refinement of each candidate's vector and position by a local fit; confirmation tests:
     the object is present in two independent halves of the frames with consistent motion; not on a masked star
     residual; PSF-like.
  3. Candidates table with thumbnails (the stack along the candidate's motion; a blink of sub-stacks), predicted
     positions per frame, known-object match (AST-4) → "known: (433) Eros" or "no known object within 30″", measure
     (per sub-stack positions for the report).
  4. The search space and time estimate are shown before the run (frames × pixels × vectors → seconds on this
     machine's CPU / GPU).
- **Accept:** synthetic movers injected into a real 30-frame series at S/N 2.0–3.0 per frame and rates 0.1–3
  ″/min: ≥ 90 % recovered above S/N 7 in the stack, ≤ 1 false candidate per run; in the real main-belt set every
  known asteroid brighter than the stack's 7σ limit is found and matched; GPU = CPU within 1e-4; 30 frames of 4k² ×
  2000 vectors: < 10 min on 4 CPU cores, < 1 min on the owner's GPU (measured there, written here).
- **Files:** `astrometry/shiftstack.py`, `compute/shiftstack.py`, UI find panel, tests, guide.

### AST-6. Reports  (P1)
**open**
- **Read first:** the ADES description (2017 and the current revision: PSV and XML forms, mandatory header
  records, observation fields, precision of time and position fields, uncertainties) and the MPC's public XML
  schema / validation tools; the MPC's observatory-code and program-code rules; the COBS / ICQ comet format.
- **Ours now:** `moving.ades_psv`.
- **Build:** `astrometry/reports/ades.py`: PSV and XML writers from the measurement table (AST-3 / AST-4: positions
  with uncertainties, magnitudes with band, catalogue codes, time precision from the exposure, notes for trailed /
  stacked observations, `trkSub` for unknown objects, permanent / provisional designations parsed and packed
  correctly); header from the observer / site / equipment profiles; a validator against the schema rules (our own
  reading of the XSD into checks; the official validator run in the validation suite if obtainable); the old
  80-column format as an export for other tools; comet magnitudes file (COBS); a preview pane and "Open the MPC
  submission page" (never automatic submission).
- **Accept:** files for Eros and for a synthetic unknown object pass the validator; designations of the MPC's
  examples (numbered, provisional, comets, survey designations) pack and unpack correctly (a table-driven test).
- **Files:** `astrometry/reports/{ades,mpc80,cobs,designations}.py`, `photometry/moving.py` (`ades_psv` re-exported), UI report panel, `tests/test_ades.py`
- **Notes from the sources (architect, 2026-11-10):** the MPC's current default is **ADES 2022** (backward compatible
  with 2017); a PSV file starts with the line `# version=2022`; the allowed values of `astCat` (Gaia DR3 = `Gaia3`),
  bands, `mode`, `stn` and notes are listed at docs.minorplanetcenter.net/mpc-ops-docs/observations/valid-ades-values/
  — a value not on the list makes the MPC reject the whole batch, so the writer takes its vocabularies from a
  table copied from that page (with the date) and the validator checks against it; `rmsRA`, `rmsDec` are the random
  1σ uncertainties in arcsec and sit after `dec` and before `astCat` in XML; the MPC offers web validators for
  both forms (the guide tells the user to run one before sending).

### AST-7. Catalogue positions for anything: the measure tool  (P2)
**open**
- **Build:** in Images and here: click any object on a solved frame → RA / Dec with errors (AST-3) and catalogue
  identity; a table of measured positions over many frames (variable stars' positions, supernova offsets from the
  host nucleus in arcsec east / north, comet nuclei); offsets and separations between two objects with errors.
- **Accept:** offsets between two Gaia stars measured on ten frames equal the catalogue separation within the
  predicted error.
- **Files:** `astrometry/measure.py`, `ui/image/tools.py` (the position tool), `tests/test_astrometry_measure.py`

### AST-8. Double stars  (P2)
**open**
- **Read first:** the WDS format notes and "requested precision" guidance; the JDSO author guide (the table of a
  measures paper: WDS designation, discoverer code, date as Besselian year, θ, ρ, their errors, number of nights);
  Argyle, *Observing and Measuring Visual Double Stars* (calibration by drift and by reference pairs; lucky
  imaging); Losse's REDUC documentation (as description).
- **Build:** measure a pair on one or many frames: two-component PSF fit for close pairs (separation ≥ 0.7 FWHM),
  centroids for wide ones; scale and orientation from the plate solution, or from a star drift (mount stopped) or a
  calibration pair when the field is too small to solve; θ referred to the epoch's equinox with the precession
  correction to the WDS convention stated; per-frame values, means and standard errors, Δm; the WDS entry by
  coordinates (`services`: WDS, ORB6, INT4): last measure, and for pairs with an orbit the ephemeris (θ, ρ) for the
  date and our O − C; the report table in JDSO layout; hand-over of measures to MOD-20.
- **Accept:** synthetic pairs (ρ = 0.8–20 px, Δm 0–3): θ within 0.3° and ρ within 1 % at S/N 100; a real wide
  pair's measure within the scatter of its recent WDS measures.
- **Files:** `astrometry/doubles.py`, `services/wds.py`, `astrometry/reports/jdso.py`, UI (Measure stage, double-star mode), `tests/test_double_stars.py`

### AST-9. Proper motion and parallax from your own frames  (P3)
**open**
- **Build:** positions of a star over months / years (AST-7) fitted with proper motion and the parallax factors
  for the site and dates (Astropy), relative to the frame's reference stars (their own Gaia motions removed) → μ,
  π with errors and the classic plot (the wobbling track); for teaching and for high-proper-motion stars.
- **Accept:** synthetic epochs of a star with μ = 10″/yr, π = 0.5″ at 0.05″ per-epoch precision: recovered within
  1σ.
- **Files:** `astrometry/motion.py`, UI tool, `tests/test_proper_motion.py`

### AST-10. Orbits through external tools  (P3)
**open**
- **Build:** an adapter to a user-installed Find_Orb (never bundled): send the ADES file, read back the orbit and
  residuals; without it: only the great-circle and rate fits of AST-4 and a statement of what orbit determination
  needs.
- **Accept:** with Find_Orb present in the test container (outside the bundle) the Eros observations give
  residuals as AST-4's O − C; without it the interface explains.
- **Files:** `astrometry/external_orbit.py` (adapter through AUT-9's external-program step), tests with a fake executable

### AST-11. The camera's distortion map  (P3)
**open**
- **Build:** residuals of many solved frames stacked into a distortion map per equipment profile (and filter),
  stored and applied as a prior to later solutions (fewer free terms per frame → better astrometry in sparse
  fields).
- **Accept:** cross-validation RMS on sparse fields improves when the stored map is used (asserted on synthetic
  data).
- **Files:** `astrometry/distortion.py`, `core/profiles.py` (map stored per equipment), tests

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
