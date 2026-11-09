# Calibration: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.2).

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

From raw frames to calibrated frames a measurement can trust: recognising and grouping frames, master bias / dark /
flat, overscan, linearity, defects, cosmic rays, fringes, illumination, error and mask planes, registration and
stacking, the detector's own numbers, and a report that says how good the calibration is. One engine serves the
Calibration window and the optional calibration stage of Photometry and Spectroscopy (PLAN.md §8).

**Goal:** every capability of IRAF `ccdred`, ccdproc, MaxIm DL's calibration, Siril's preprocessing and
AstroImageJ's Data Processor; plus what none of them gives: a plan the user can read and change before anything
runs, a quality report of the masters, and error / mask planes that reach the light curve and the spectrum.

## What the reference programs do

Read (never copied): IRAF `noao/imred/ccdred` (`ccdproc`, `zerocombine`, `darkcombine`, `flatcombine`, `combine`,
`mkfringecor`, `mkillumcor`, `mkillumflat`, `mkskycor`, `mkskyflat`, `ccdmask`, `ccdgroups`, `ccdhedit`,
`setinstrument` with its header translation files) and `images/immatch/imcombine`; ccdproc (Astropy, BSD:
`Combiner`, `subtract_overscan`, `trim_image`, `create_deviation`, `gain_correct`, `cosmicray_lacosmic`, `ccdmask`,
`ImageFileCollection`); Siril (`src/core/preprocess.c`, `src/stacking/`: rejection and normalisation,
`cosmetic correction`); AstroImageJ `Data_Processor.java`; MaxIm DL manual ("Set Calibration", calibration groups,
dark scaling None / Auto-Scale / Auto-Optimize, combine types); the Astropy CCD Data Reduction Guide (Craig & Chambers);
Howell, *Handbook of CCD Astronomy*; Janesick, *Photon Transfer*.

| Topic | IRAF ccdred | ccdproc | MaxIm DL | Siril | AstroImageJ DP | Ours now |
| --- | --- | --- | --- | --- | --- | --- |
| Frame types | `ccdtype` through an instrument translation file | header keyword filter (`ImageFileCollection`) | calibration groups auto-generated from headers | by file sequences the user builds | file-name patterns | header keywords of many capture programs, file name, 0 s = bias; arcs kept apart |
| Overscan / trim | `biassec`, `trimsec`, fit function and order, interactive | `subtract_overscan`, `trim_image` | — | — | — | BIASSEC / TRIMSEC / DATASEC, row-wise fit, ESO prescan; single amplifier only |
| Combine | average / median; reject none, minmax, **ccdclip**, **crreject**, sigclip, **avsigclip**, **pclip**; scale by mode / median / mean / exposure; zero offsets; weights; `nkeep`, `mclip`, `grow` | average / median / sum; minmax, sigma clipping, clip extrema; scaling function | average, median, sigma clip, SD mask | mean with percentile, sigma, MAD, median-sigma, winsorized, **linear-fit**, **GESD** rejection; additive / multiplicative normalisation with scale; weights by noise, FWHM, star count | average / median | clipped mean (median + MAD) for masters; stack: sigma, MAD, winsorized, min-max, percentile; mean / median / sum; noise weights; GPU |
| Dark | scaled by exposure | scaled by exposure | none / auto-scale (exposure) / auto-optimise (least variance) | dark optimisation (least noise), hot-pixel cosmetic correction | scaled by exposure | exposure scaling, optimisation (least variance), nearest temperature within a tolerance |
| Flat | per filter; `mkskyflat`, `mkillumflat` for illumination; `minreplace` | per filter | per filter and rotator angle | per filter; flat-dark | per filter | per filter, nearest in time; dead pixels below 5 % → NaN |
| Fringes | `mkfringecor`, `fringecor` scaled | — | — | — | — | none |
| Defects | `fixpix` with a bad-pixel file, `ccdmask` | `ccdmask`, mask planes | bad-pixel maps, bloom removal | cosmetic correction from the dark | outlier removal | defect map from dark (hot) and flat (dead), repaired by neighbours |
| Cosmic rays | `cosmicrays`, `crmedian`, `lacos_im` | L.A.Cosmic (astroscrappy), median | — | — | threshold outlier removal | L.A.Cosmic (astroscrappy) on request |
| Errors and masks | optional variance in `apall` only | `CCDData` uncertainty and mask carried by every operation | — | — | — | none carried |
| Linearity | — | — | — | — | polynomial correction | polynomial correction when coefficients are given |
| Detector numbers | `findgain` (gain and read noise from two flats and two biases) | — | — | — | — | none |
| Colour sensors | — | — | calibrate Bayer planes | CFA-aware, X-Trans fix, equalise CFA | photometric debayer | superpixel split, CFA repair, DSLR raw |
| Report | log file | — | — | — | log | list of problems and missing frames |

## What we already have (do not redo)

- `calibration/frames.py` (classification), `matching.py` (plan with reasons), `masters.py` (formulas above,
  overscan fit, linearity, dark optimisation, defect map, block-wise reading, GPU combine), `steps.py`
  (`calibration.scan`, `calibration.run`, `stacking.stack`, `stacking.drizzle`), `stacking.py` (FFT and star-pattern
  alignment, rejections, normalisation, weights, coverage), `starmatch.py`, `drizzle.py`, `io/bayer.py`.
- Validated: identical to IRAF `ccdred` on LCO frames (0.000 ADU), 0.92 ADU per pixel from LCO's BANZAI; Palomar LFC
  and thermo-electric MaxIm nights of the Astropy guide reduce.
- Window: `ui/calibrate_page.py` in its area window with menus Frames, Masters, Process, Send.

## Decisions

- Calibrated frames are written as multi-extension FITS: `SCI` (float32), `VAR` (float32, variance in ADU²), `DQ`
  (uint8 flags) — CAL-13. A setting writes plain single-image FITS for other programs (the planes are then dropped
  and the header says so).
- Raw files are never changed. Outputs go to a folder the user sees before the run, with an estimate of the size.
- The plan (which master for which light, and why) is always shown before running and can be edited.
- CMOS guidance is built in: darks are matched by exposure, gain, offset and temperature and not scaled unless the
  user asks; flat-darks are used for flats when present.

## To ask the owner

- Which capture programs and cameras the owner's group uses besides MaxIm DL at TUG (to fill CAL-2's header table
  from real files).

## For the owner to try

- After CAL-W: calibrate one of your nights in the new window; look at the Plan tab before pressing Calibrate and
  say whether its reasons are clear.
- After CAL-9: run "Measure the camera" on two flats and two biases of your camera and compare with the maker's
  sheet.

## Data used

- `data/calibration/palomar-lfc` (overscan, darks in a sub-folder, two filters); the thermo-electric MaxIm night
  (Zenodo 3245296); LCO raw frames with BANZAI products (`data/photometry/qatar1-lco` notes).
- To add: a night with I- or z-band fringing and its fringe frame (CAL-10); a multi-amplifier, multi-extension
  mosaic night (CAL-4); a CMOS night with amp glow, flat-darks and no bias (CAL-3); a flat exposure series for
  linearity and the photon-transfer curve (CAL-9); a DSLR raw night.

## Steps

Order of work: CAL-W, then P1: 1, 2, 3, 13, 8, 5, 6, 12, 4, 14, 23; P2: 7, 9, 10, 11, 15, 16, 17, 19, 21, 22;
P3: 18, 20.

### CAL-W. The Calibration window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.2: stages Frames, Check, Masters, Calibrate, Review, Continue; groups tree with a
  preview; result tabs Plan, Problems, Report, Log.
- **Extra accept:** on the practice night: drop the folder → the plan is shown → one click calibrates → Review
  shows before / after — **three clicks**; every grey paragraph of the old page is gone from the panel and found in
  the Help panel.
- **Depends on:** ARC-4.5, ARC-5, ARC-7, ARC-8, UI-1 … UI-4.
- **Files:** `ui/calibration/{window,controller,state,menus}.py`, `ui/calibration/panels/{frames,check,masters,calibrate,review,continue_,plan,report}.py`, `tests/ui/walks/calibration.py`, guide 04

### CAL-1. Frames stage: groups, previews, any folder layout  (P1)
**open**
- **Reference:** MaxIm DL's calibration groups (type, filter, exposure, binning, temperature, count, auto-generated);
  ccdproc `ImageFileCollection.summary`; IRAF `ccdlist`, `ccdgroups`.
- **Ours now:** `calibration.scan` returns frames and problems; a flat table of files.
- **Build:**
  1. `calibration/groups.py`: frames grouped by (type, filter, exposure, binning, read-out settings, temperature
     rounded to the tolerance, sub-frame, camera, night); night = local noon-to-noon date from the site profile or
     the header longitude; each group has count, time span, median level and noise from a fast read of the central
     512 × 512 (thread pool, cached by path + mtime).
  2. Any layout works: one folder, type sub-folders (`Bias/`, `Dark_60s/`, `Flat_V/`, `Light/`), date sub-folders,
     several nights at once; pictures (JPEG / PNG / TIFF / raw) follow the existing rules; compressed FITS (`.fz`,
     `.gz`, `.Z`) as today.
  3. Groups tree (kit `TableView` in tree mode): tick boxes for use; a click previews the group's first frame, a
     click on a file its own frame, with median, noise, minimum, maximum, saturated fraction and a histogram;
     outliers inside a group (level or noise beyond 5 robust σ of the group, flats outside 20–80 % of saturation,
     lights mis-typed as flats) get an amber mark with the reason and "Leave out" / "Change type".
  4. Changing a frame's or a group's type, filter or exposure is an edit of the session (undoable), never of the
     file; "Write these corrections into copies…" is offered (CAL-23).
  5. Scan speed: headers only first (the table appears), statistics after, 16 threads for I/O.
- **Accept:** the four layouts above of the same night give the same groups (test builds them from the practice
  night); 2000 files appear in the table in < 3 s and their statistics within 30 s; a flat that is 95 % saturated
  is marked with its reason; a mixed two-night folder gives two nights of groups.
- **Files:** `calibration/groups.py`, `calibration/steps.py`, UI frames panel, tests.

### CAL-2. Header conventions as data, and the user's own rules  (P1)
**open**
- **Reference:** IRAF `setinstrument` translation files (`subsets`, `imagetyp` mapping per instrument); ccdproc
  keyword filters; N.I.N.A., SharpCap, KStars / Ekos, MaxIm DL, SGP, Voyager, APT, ASIAIR, CCDCiel, Prism, TheSkyX
  header habits; ESO, LCO, NOT, TUG observatory conventions.
- **Ours now:** keyword lists inside `frames.py` and `hdr.py`.
- **Build:**
  1. `resources/headers/conventions.toml`: for each concept (type, filter, exposure, temperature, set point,
     binning, gain, offset, read-out mode, date / time, object, coordinates, site, pier side, rotator angle, focus
     position, airmass, sub-frame, Bayer pattern, amplifier sections) the keywords in order of trust and the value
     maps (`"Dark Frame" → dark`, `"zero" → bias`, `"comp" → arc`, `"skyflat" → flat` …), per writing program where
     they differ (`SWCREATE` / `PROGRAM` / `CREATOR` / `ORIGIN` detected first).
  2. `calibration/frames.py` reads the table instead of in-code lists; a test replays a stored header of every
     program listed (collected from public sample files, each noted in `data/reference/headers/SOURCE.md`).
  3. Settings → Files → "Header rules": the user adds a rule for their instrument ("keyword `OBSTYPE` value `SKY` is
     a flat"; "filter names `Clear, L, Lum` are the same filter"); rules are stored in the equipment profile
     (ARC-16) and exported / imported.
  4. "Why is this frame a …?" in the Inspector: the keyword and rule that decided.
- **Accept:** every stored header classifies as its `SOURCE.md` says; a user rule changes the classification and
  survives a restart; removing the rule restores it (undo).
- **Files:** `resources/headers/conventions.toml`, `calibration/frames.py`, `hdr.py`, settings panel, tests.

### CAL-3. CMOS-correct matching: flat-darks, no forced bias, no blind dark scaling  (P1)
**open**
- **Why:** most new amateur and many observatory cameras are CMOS: bias frames are unstable at the shortest
  exposure, amplifier glow does not scale with time, gain and offset change the pattern.
- **Reference:** Siril's and PixInsight's guidance for CMOS (darks at the lights' exposure, gain, offset and
  temperature; "dark flats" at the flats' exposure instead of bias); MaxIm DL group properties; camera makers'
  notes on amp glow (Sony IMX sensors).
- **Ours now:** matching by size, binning, read-out settings; temperature tolerance; dark scaling when exposures
  differ; flats take bias and scaled dark.
- **Build:**
  1. Sensor kind per camera profile (CCD / CMOS / unknown; guessed from `INSTRUME` and the sensor table
     `resources/cameras.toml` with common models) drives defaults: CMOS → `dark_scaling = off`, flats calibrated
     with flat-darks (darks of the flats' exposure ± 10 %) when present, else with bias, else with a constant
     offset from the header `OFFSET` / pedestal with a warning.
  2. Matching score made explicit and shown: each candidate master gets penalties for exposure ratio, temperature
     difference, gain / offset mismatch, age in days, and the plan shows the chosen one with its penalties and the
     runner-up.
  3. Amp-glow check: the master dark's corners against its centre; when glow is seen and the plan would scale a
     dark, the plan warns ("this dark has amplifier glow: scaling it from 300 s to 60 s leaves the glow wrong; take
     60 s darks or accept the residual") — the user decides.
  4. A night without bias runs without complaint when darks match the lights' exposure (raw-dark path) and flats
     have flat-darks.
- **Accept:** synthetic CMOS night (glow that grows non-linearly with time): the default plan uses matched darks
  and flat-darks and leaves < 0.2σ residual; forcing scaling leaves the predicted residual and the warning was
  shown; the CCD validations stay identical to IRAF.
- **Files:** `calibration/matching.py`, `masters.py`, `resources/cameras.toml`, UI plan tab, messages, tests.

### CAL-4. Several amplifiers and multi-extension mosaics  (P1)
**open**
- **Reference:** IRAF `mscred` (`ccdproc` per extension, `AMPSEC`, `DETSEC`, `CCDSEC`, crosstalk), ccdproc examples
  for multi-amp frames, ESO and LCO multi-amp headers, Palomar LFC (six chips).
- **Ours now:** one BIASSEC / TRIMSEC per frame; the first image HDU is used.
- **Build:** per-amplifier sections from `BIASSECn` / `DATASECn` / `AMPSECn` / `DETSECn` or `BIASSEC` per extension;
  overscan fitted per amplifier; gains per amplifier (`GAINn`) normalised so that the joined frame is in one unit;
  extensions processed independently with the same plan and written back as a MEF with the same structure, or
  joined into one image by `DETSEC` on request (gaps as NaN with the DQ no-data bit); every later tool (Photometry,
  Images) opens a chosen extension or the joined frame.
- **Accept:** a synthetic two-amplifier frame with different bias levels and gains calibrates to a seamless sky
  (step at the boundary < 0.1σ); the six-chip Palomar LFC set calibrates chip by chip with results equal to ccdproc
  run per extension (reference stored); memory stays block-wise.
- **Files:** `calibration/masters.py` (`_layout`), `io/fits.py`, tests.

### CAL-5. Combine and rejection: every method of the reference programs  (P1)
**open**
- **Reference:** IRAF `imcombine` help (the definitive description; its parameter file: `combine = average |
  median | lmedian | sum | quadrature | nmodel`, `reject = none | minmax | ccdclip | crreject | sigclip | avsigclip |
  pclip`, `nkeep 1`, `mclip yes`, `grow 0`, `sigscale 0.1`): `minmax` (nlow, nhigh), `ccdclip` (σ from the
  noise model: read noise, gain, sensitivity noise), `crreject` (ccdclip rejecting only high), `sigclip`,
  `avsigclip` (σ ∝ √signal with the proportionality estimated per line — for few frames), `pclip` (percentile),
  `nkeep`, `mclip` (median vs mean as centre), `grow`; scaling and zero offsets by mode / median / mean / exposure;
  weights. Siril: winsorized σ, linear-fit clipping (a line through the sorted pixel stack; robust to gradients
  between frames), generalised ESD test (Rosner 1983) for large stacks. ccdproc `Combiner`.
- **Ours now:** masters: clipped mean about the median with MAD scale; stacks: sigma (IRAF sigclip), MAD,
  winsorized, min-max, percentile; normalisation none / additive / multiplicative; noise weights.
- **Build:**
  1. `calibration/combine.py` (one module for masters and stacks): rejections `none`, `minmax`, `sigclip`,
     `avsigclip`, `ccdclip`, `crreject`, `pclip`, `mad`, `winsorized`, `linear_fit`, `gesd`; `nkeep`, `mclip`,
     `grow` radius (reject neighbours of a rejected pixel in the same frame); centre mean / median; combination
     mean / median / sum; scale and zero by none / mode / median / mean / exposure / a header keyword; weights none
     / exposure / 1/noise² / a header keyword; the statistics region (whole frame or a section).
  2. Defaults that are right without thought: bias → `avsigclip` (< 10 frames) or `sigclip`; darks → `sigclip`
     high-only 3σ (cosmic rays), `ccdclip` when gain and read noise are known; flats → scale by mode (median),
     `sigclip` 3σ both sides (stars in twilight flats), `minmax` for < 5 frames; science stacks → `winsorized`
     (< 15 frames), `linear_fit` (15–50), `gesd` (> 50), as Siril advises.
  3. Outputs besides the combined image: the number of frames kept per pixel, and low / high rejection maps on
     request (as Siril).
  4. GPU twins (`compute/stack.py`) for the new methods where they are per-pixel (`avsigclip`, `ccdclip`,
     `linear_fit`); `gesd` CPU only unless measured worthwhile.
  5. Masters stage: one "Method" choice per master type with the default named "Automatic (sigclip: 20 frames)";
     the options are folded.
- **Accept:** for each method a test against a direct, slow NumPy statement of the IRAF / Siril definition;
  `sigclip`, `avsigclip`, `ccdclip`, `minmax` equal IRAF `imcombine` on 10 real bias and 10 dark frames within 1e-4
  ADU (reference images' statistics and 1000 sampled pixels stored); GPU equals CPU within 1e-5 relative; a cosmic
  ray in one of five darks is removed by the default.
- **Files:** `calibration/combine.py`, `masters.py`, `stacking.py`, `compute/stack.py`, tests.

### CAL-6. The quality report of the masters and of the calibration  (P1)
**partial** — done (2026-11-14), item 1 and its place in the run: `calibration/quality.py` (`level_noise` with the
excess over σ/√N, `banding`, `hot_pixels`, `dark_current`, `flat_levels`, `dust` (binned for large flats: a 4k
flat in 1.6 s), `flat_noise`, `report` per kind with ok / amber); `calibration.run` returns each master's report
("quality"), and the Calibration window lists every amber check in its problems box. Tests
(tests/test_cal_quality.py): banding 2 ADU, 500 hot pixels, 0.1 e⁻/s, a flat at 95 % of full well and a 3 % mote
each reported within 10–15 %; a clean bias all green; a run on frames with a 6 % mote says so. Left: items 2–5 (the
residual tests, the library comparison, the lights' before / after, the report tab with pictures and PDF, QC
header keywords), the input flats' levels in the run, the real LCO masters.
- **Ours now:** the Problems list after a run (groups that failed, missing frames); no statistics of the masters.
- **Why:** no reference program tells the user whether the calibration is good. A bad flat ruins a night silently.
- **Reference:** LCO BANZAI and ESO pipeline QC parameters (bias level and noise, structure, flat levels, number
  of saturated pixels); CCD Inspector's flat-field views; Howell ch. 4.
- **Build:**
  1. `calibration/quality.py`, per master: level, noise of the master against the expected `σ_single / √N`, and
     the excess (pattern noise); row / column structure (medians along both axes, RMS of each; banding flag);
     a low-resolution image of the master (for a "surface" picture); count of hot, cold and unstable pixels (pixels
     whose scatter across the input frames is > 5 × the median scatter); for darks: dark current in e⁻/px/s (with
     the gain) and its doubling temperature when darks at several temperatures exist; for flats: vignetting profile
     (radial median), strongest dust motes (location, depth), illumination tilt, the level of each input flat (range
     20–80 % of full well advised), the flat's own noise against photon noise ("this master flat adds 0.12 % noise
     per pixel; stars measured over 80 pixels gain 0.013 %").
  2. Residual test: one input flat calibrated with the master made from the others → RMS of the result's large-scale
     structure (should be < 0.3 %); one dark calibrated with the master from the others → hot-pixel residual.
  3. Comparison with the library (CAL-7): change of bias level, dark current, flat pattern (correlation of the
     normalised flats; dust that moved) since the last masters of the same set-up.
  4. After the run: for every group of lights the sky level and noise before and after, the count of repaired
     pixels, cosmic rays found, frames left out and why.
  5. Report tab: a table per master with green / amber marks and one-line explanations; pictures of each master;
     "Save the report (PDF / HTML)" for the night's log; values also in the masters' headers (`QC*` keywords).
- **Accept:** synthetic masters with a known defect of each kind (banding 2 ADU, a flat taken at 95 % full well,
  dust mote of 3 %, 500 hot pixels, dark current of 0.1 e⁻/s) are each reported with the right number within 10 %;
  the real LCO masters produce a report with no red mark; report of 30 masters < 5 s.
- **Files:** `calibration/quality.py`, steps (outputs), UI report tab, `ui/plot/publish` use, tests, guide 04.

### CAL-7. A library of masters across nights  (P2)
**open**
- **Reference:** MaxIm DL keeps calibration groups between sessions; N.I.N.A.'s flat and dark libraries; observatory
  pipelines select masters by date validity.
- **Build:** `calibration/library.py`: a folder (Settings → Files) with masters filed by camera / binning / gain /
  offset / temperature / exposure / filter / date, an index (SQLite) with their QC values; after every run "Add
  these masters to the library" (default on); the plan uses library masters when the night has none or too few
  (marked "from the library, 12 days old") within validity rules per type (bias 90 days, dark 90 days, flat 7 days
  or until the camera was rotated — `ROTATANG` / a profile note; all editable); a Library dialog to browse, compare
  two masters (ratio image, difference statistics), retire or delete.
- **Accept:** a night with lights only calibrates from the library with the reasons shown; a flat older than its
  validity is offered with an amber mark, not used silently; two masters' comparison of a moved dust mote shows it.
- **Files:** `calibration/library.py`, `calibration/matching.py`, `ui/calibration/dialogs/library.py`, `tests/test_master_library.py`

### CAL-8. Bad-pixel masks as files, cosmetic correction choices  (P1)
**open**
- **Reference:** IRAF `fixpix` and its bad-pixel file formats (text regions; mask images `.pl`), `ccdmask` (from a
  flat ratio); ccdproc `ccdmask` (after IRAF); Siril cosmetic correction (hot / cold sigma from the dark, or a list
  file); MaxIm DL bad-pixel maps and column repair.
- **Ours now:** `masters.defect_map` (hot from dark, dead from flat), `repair` by neighbour medians.
- **Build:** `calibration/badpix.py`: mask sources combined by OR: from the master dark (hot: > median + n σ;
  unstable), from the flat (dead / low: < x of the median; `ccdmask` method on the ratio of two flats of different
  level for non-linear pixels), from a user file (FITS mask image of the same geometry, IRAF text regions `x1 x2 y1
  y2`, Siril list, DS9 region file), bad columns and rows detected as runs; saved as a FITS mask with provenance
  and added to the library per camera and binning; repair modes: none (flag only — the right choice for photometry,
  which then flags apertures: PHO-36), interpolate along rows for columns, median of good neighbours, for CFA
  frames the same-colour neighbours; the DQ plane records flagged and repaired pixels separately.
- **Accept:** a synthetic frame with a bad column, 300 hot pixels and a dead cluster: all masked from dark + flat;
  each file format reads and writes back identically; repaired values within 1σ of the truth on a smooth sky;
  unrepaired mode leaves data untouched and flags set.
- **Files:** `calibration/badpix.py`, `masters.py`, steps, UI masters panel, tests.

### CAL-9. Measure the camera: gain, read noise, linearity, full well, dark current, shutter  (P2)
**open**
- **Reference:** IRAF `findgain` (Janesick's two-flats-two-biases method: `g = [(F̄1 + F̄2) − (B̄1 + B̄2)] /
  [σ²(F1 − F2) − σ²(B1 − B2)]`, `RN = g σ(B1 − B2) / √2`); the photon-transfer curve (variance against mean over a
  series of flat pairs; Janesick 2007); linearity from an exposure series with a monitor of lamp stability;
  SharpCap "Sensor Analysis"; shutter-timing correction maps for iris shutters (short flats against long flats);
  AstroImageJ's linearity polynomial.
- **Build:** Tools → "Measure the camera…" (also in Calibration's Tools menu) with tasks: (a) gain and read noise
  from two flats + two biases (in boxes of 100 × 100 px over the frame, median and scatter of the estimates,
  per amplifier); (b) photon-transfer curve from flat pairs at many levels → gain from the slope, full well and the
  onset of non-linearity where the curve bends, fixed-pattern noise; (c) linearity: mean signal against exposure
  time, with the lamp drift removed by repeated reference exposures; polynomial of the correction (the form
  `masters.linearity` uses), the level where the deviation exceeds 1 %, residual plot; (d) dark current against
  temperature from dark sets; (e) shutter map from short / long flats and the effective exposure offset. Each task
  explains which frames to take (and can send a sequence to Observing), shows the plot (`PlotView`), and offers
  "Save to the camera profile" (ARC-16: gain, read noise, linearity limit and coefficients, saturation).
- **Accept:** synthetic camera (gain 1.8 e⁻/ADU, read noise 6.5 e⁻, 2 % non-linearity at 50 000 ADU, full well
  61 000 ADU, shutter offset 12 ms): each recovered within 3 % (gain, read noise), 0.3 % (linearity at 50 000 ADU),
  2 ms (shutter); on a real flat series (data to add) gain agrees with the header's value within 5 %.
- **Files:** `calibration/detector.py`, steps `calibration.detector_*`, UI tool, tests, guide 04.

### CAL-10. Fringe correction  (P2)
**open**
- **Reference:** IRAF `mkfringecor` (object-masked combination of sky frames, sky level subtracted) and `ccdproc
  fringecor` with a scale; Snodgrass & Carry 2013 (The Messenger 152, 14: the fringe amplitude measured from
  control pairs of bright and dark fringe positions); thinned CCDs in I, z, narrow bands.
- **Build:** `calibration/fringe.py`: `make_fringe_frame(lights)` from ≥ 5 dithered science or sky frames of one
  filter: calibrate, mask objects (segmentation above 2σ, dilated), scale to a common sky, median-combine, subtract
  the smooth background (large median filter) → the fringe pattern in units of sky; `fit_amplitude(light, fringe)`
  by least squares on unmasked pixels or by control pairs; `calibrated −= amplitude × fringe`; the plan adds a
  fringe column for filters where a pattern is detected in the combined sky (power at the fringe scale above a
  threshold) or where the user asks; library storage per filter and camera.
- **Accept:** synthetic fringes of 3 % of sky on dithered star fields: residual < 0.3 % after correction and star
  fluxes unbiased (< 0.2 %); on the real I-band set the fringe RMS falls by ≥ 5 × (number stored).
- **Files:** `calibration/fringe.py`, plan and steps, UI, tests.

### CAL-11. Illumination correction and flats from the night sky  (P2)
**open**
- **Reference:** IRAF `mkskyflat`, `mkillumflat`, `mkskycor`, `mkillumcor` (large-scale difference between dome /
  twilight flats and the dark-sky response); super-sky flats from dithered science frames; twilight flats with
  changing level and stars (scale by mode, reject high).
- **Build:** `calibration/skyflat.py`: super-sky flat from N dithered, object-masked, normalised lights (needs
  dithers larger than the objects; the tool checks the dither pattern from the offsets and refuses with advice
  when stars would print through); illumination correction = smoothed (super-sky / flat), applied to the flat;
  twilight-flat processing with star rejection across dithered sky flats; a check picture of the corrected flat
  field's large-scale residual.
- **Accept:** synthetic night whose dome flat has a 3 % illumination gradient the sky does not have: the corrected
  photometry of a star dithered across the field is constant within 0.3 % (was 3 %).
- **Files:** `calibration/skyflat.py`, `calibration/matching.py` (plan column), steps, `tests/test_skyflat.py`

### CAL-12. Cosmic rays and trails: preview, masks, the right parameters  (P1)
**partial** — done (2026-11-14): the cosmic-ray cleaning is astroscrappy's result 2–2.5× faster
(`calibration/cosmics.py`, UF-12); `calibration/trails.py` finds trails (`find`: stars cut out and pixels held
within ±3σ, binned 4 × 4, projected on every direction with the angle refined to 0.05°; a second look at the map
of bright pixels for bright trails; `band`: the trail's mask). Tests (tests/test_trails.py): a 2σ-per-pixel trail
across a 2k frame found within 0.3° at two angles, a bright one too, none on a frame of 400 stars. Left: the
presets and the preview, the DQ bits, running the trail search on the lights (2–3 s per 2k frame: an option) and
listing them in the Problems, the real frame with a trail.
- **Reference:** van Dokkum 2001 (PASP 113, 1420: L.A.Cosmic; `sigclip`, `sigfrac`, `objlim`, iterations; separate
  recipes for imaging and spectra); astroscrappy (BSD; in use); satellite trails: Hough / Radon detection (Nir,
  Zackay & Ofek 2018, AJ 156, 229; the ACS `satdet` approach; ASTRiDE, Kim 2016).
- **Ours now:** `_remove_cosmic_rays` with astroscrappy on request.
- **Build:** parameters exposed with presets (imaging: sigclip 4.5, objlim 5; under-sampled stars: objlim 10–20 and
  a warning that star cores may be touched; spectra: sigclip 5, sigfrac 0.3, with the dispersion-direction
  variant); gain and read noise from the profile / header (wrong values are the main cause of bad results — the
  step refuses to guess silently); a **preview on one frame** before the run (blink: original / cleaned / mask) in
  the Calibrate stage; the mask goes to the DQ plane (cosmic-ray bit; repaired or not); trail detection:
  `calibration/trails.py` (edge map → Radon / Hough peaks → a band mask of the fitted width), DQ trail bit, a list of
  frames with trails in the Problems tab; trails are **not** repaired, only flagged (PHO-36 then flags points).
- **Accept:** synthetic frames with 200 cosmic rays and stars of FWHM 2 px: ≥ 95 % found, no star core flagged at
  the imaging preset; a faint (2σ per pixel) trail across a 2k frame is found with its angle within 0.3°; a real
  frame with a trail (data to add) is flagged.
- **Files:** `calibration/cosmic.py`, `calibration/trails.py`, steps, UI, tests.

### CAL-13. Variance and mask planes  (P1)
**open**
- **Why:** AD-8.
- **Reference:** Astropy `CCDData` (data, `StdDevUncertainty` / `VarianceUncertainty`, mask, flags), ccdproc's
  propagation through `subtract_bias`, `subtract_dark`, `flat_correct`; ESO pipelines' ERR and DQ extensions; HST
  DQ flags.
- **Build:**
  1. `core/planes.py`: `Frame(sci, var, dq, header)`; DQ bits: 1 bad pixel, 2 saturated, 4 non-linear, 8 cosmic
     ray, 16 trail, 32 no data (outside the detector, gap, off the edge after registration), 64 repaired
     (interpolated value), 128 user mask. Readers return a `Frame` for our MEF files and for plain FITS (var and dq
     then `None` / built on request from the gain and read noise).
  2. Propagation in `masters.calibrate`: `var_raw = max(sci_raw − bias, 0) / g + (RN / g)²` (ADU²) + overscan-fit
     error; minus bias: `+ var_bias`; minus dark × k: `+ k² var_dark`; divided by flat: `var / flat² + sci²
     var_flat / flat⁴`; masters carry their own variance from the combine (`σ² / N_kept` per pixel). Saturation and
     linearity limits (profile / header) set bits on the raw frame before anything else.
  3. Registration and stacking carry variance (resampling correlates pixels: the variance plane is resampled with
     the squared kernel weights and the header notes the correlation factor) and OR the DQ of contributing pixels;
     stacks weight by inverse variance when asked.
  4. Output format as decided above (float32, RICE-compressed MEF optional); `io/fits.read_image` unchanged for
     callers that want only the image.
  5. A check tool: the variance plane against the empirical variance of a stack of repeated frames.
- **Accept:** for 30 synthetic repeated lights the per-pixel empirical variance equals the mean variance plane
  within 3 % over the sky and over a bright star; flags of a saturated star, a hot pixel and a cosmic ray survive
  calibration and a 0.4 px shift; reading a 0.3.4 calibrated file still works everywhere.
- **Files:** `core/planes.py`, `calibration/masters.py`, `stacking.py`, `io/fits.py`, tests.

### CAL-14. What is written, where, and how much disk it needs  (P1)
**open**
- **Ours now:** `masters.save`, calibrated files written next to a chosen output folder as float32 FITS with HISTORY lines.
- **Build:** output naming pattern (Settings → Files; default `<output>/<night>/<type>/<original name>_cal.fits`
  with tokens for object, filter, date, sequence number); data type choices: float32 (default), float32 RICE /
  fpack tile compression (lossless for integers, quantised q = 16 for floats — the choice explained), 16-bit scaled
  integers for other programs (with BZERO / BSCALE chosen from the data range and a warning about the loss); before
  a run: the estimated size and the free space; headers: every calibration fact as keywords (`CALSTAT = 'BDF'` as
  MaxIm DL writes, `ZEROCOR`, `DARKCOR`, `FLATCOR`, `FRINGCOR`, `ILLUMCOR`, `LINCOR`, `OVERSCAN`, `TRIM`, `CRCOR`
  with the master's file name and checksum each, as IRAF does) plus provenance (ARC-11); atomic writes; a run can be
  resumed (frames already written with the same provenance hash are skipped).
- **Accept:** a calibrated file opens in DS9, AstroImageJ and IRAF (`imstat` equal); an interrupted run resumed
  writes only the missing frames; the estimate is within 10 % of the real size.
- **Files:** `calibration/output.py`, `calibration/masters.py` (`save`), `calibration/steps.py`, `ui/shell/settings/files.py`, `tests/test_calibration_output.py`

### CAL-15. Registration: more than shifts  (P2)
**open**
- **Reference:** IRAF `imalign` / `geomap` / `geotran` (polynomial transforms), Siril registration (global star
  alignment with homography, 1–2–3 star, image pattern, comet), AstroImageJ Stack Aligner (apertures or WCS),
  `astroalign` (MIT; triangle matching — the method we already have), `reproject` (BSD) for WCS resampling; kernels
  bilinear / bicubic / Lanczos-3 with clamping against ringing; flux conservation (Jacobian).
- **Ours now:** FFT shifts accumulated; star-pattern similarity (rotation, scale, shift); bilinear.
- **Build:** transforms: shift, similarity (have), affine, homography, low-order polynomial distortion — chosen by
  the residuals (reported per frame in px RMS); by WCS when frames are solved (`reproject` interp and exact
  flux-conserving modes, optional dependency checked for licence and wheels); align on a moving object (track from
  AST / Horizons); kernels nearest / bilinear / bicubic / Lanczos-3 (clamped); surface-brightness or flux
  conservation; edges and gaps flagged in DQ; the registration table (shifts, rotation, scale, residual, matched
  stars) saved with the session and reused by Photometry (no second registration).
- **Accept:** synthetic frames with rotation 0.7°, scale 1.002 and barrel distortion: star positions after
  registration within 0.05 px RMS; total flux of stars conserved within 0.2 % (Lanczos) and 0.05 % (exact); a
  meridian-flipped half night aligns.
- **Files:** `calibration/registration.py` (from `stacking.py` and `starmatch.py`), `calibration/resample.py`, `tests/test_registration.py`

### CAL-16. Stacking: parity with Siril and MaxIm DL  (P2)
**open**
- **Ours now:** `calibration/stacking.py` (rejections, normalisation, weights, coverage), `calibration/drizzle.py`, `compute/stack.py`.
- **Build:** on CAL-5 and CAL-15: frame selection by quality (FWHM, roundness, background, star count: best x % or
  thresholds, with the table of values); normalisation options; weights by noise / FWHM / star count; rejection
  maps; drizzle (have) with CFA drizzle; mosaics of adjacent fields by WCS with background matching (`reproject`);
  comet-and-stars two-pass stacks; a preview of the stack growing (live stacking for the Observing window, OBS);
  output with VAR and DQ and the coverage map.
- **Accept:** 50 frames of the Qatar-1 field: stack noise falls as 1/√N within 5 %; a satellite trail in one frame
  leaves no trace above 0.5σ with the default rejection; a 2 × 2 mosaic of synthetic fields joins with seams below
  0.3σ.
- **Files:** `calibration/stacking.py`, `calibration/mosaic.py`, `calibration/drizzle.py`, steps `stacking.*`, `tests/test_stacking.py`

### CAL-17. Colour sensors  (P2)
**open**
- **Ours now:** `io/bayer.py`: superpixel split, CFA-aware repair, DSLR raw through rawpy.
- **Build:** per-channel statistics and flats (colour flats normalised per channel: "equalise CFA" as Siril);
  X-Trans handling (6 × 6 pattern) for classification and repair; debayering for pictures only (bilinear, and a
  gradient-corrected method written from Malvar, He & Cutler 2004), clearly separated from the photometric
  superpixel path; DSLR specifics: ISO in matching, black level and white level from the raw metadata into the
  saturation / linearity limits, sensor temperature from EXIF when present; CFA drizzle.
- **Accept:** a synthetic Bayer night: superpixel photometry of the green channel equals the mono truth within
  noise; equalised flats remove a colour cast of the flat panel; an X-Trans raw classifies and calibrates.
- **Files:** `io/bayer.py`, `calibration/cfa.py`, `images/debayer.py`, `tests/test_bayer.py`

### CAL-18. Spectroscopic calibration hooks  (P3; the science is in `plans/spectroscopy.md`)
**open**
- **Build:** the plan's "data kind = spectra" defaults: arcs bias / dark only; flats normalised along the
  dispersion (SPE does it) instead of divided as they are; cosmic-ray preset for spectra; no dark scaling for long
  exposures unless optimised; lamp frames grouped by lamp name; twilight / dome flats distinguished from lamp
  flats.
- **Accept:** the EFOSC2 and TOFES nights group correctly and hand the right frames to SPE.
- **Files:** `calibration/matching.py` (data kind = spectra), `calibration/frames.py`, `tests/test_calibration_spectra.py`

### CAL-19. Many nights at once  (P2)
**open**
- **Build:** a queue of nights (the groups tree with nights at the top level): one plan per night, library masters
  where a night lacks them, one run in the background with a summary table per night (frames, masters used,
  problems, QC marks), resumable (CAL-14); recipe export (ARC-12).
- **Accept:** three nights in one folder tree calibrate in one run with per-night outputs and one report.
- **Files:** `calibration/steps.py` (`calibration.nights`), `calibration/groups.py`, UI frames panel (nights level), `tests/test_calibration_nights.py`

### CAL-20. Speed  (P3)
**open**
- **Build:** benchmark cases (100 frames 4k²; 30-frame masters 6k × 4k); profile; I/O read-ahead and write-behind
  threads; native CPU kernels for combine (ARC-9) if NumPy partition-based code is the hot spot; GPU thresholds from
  ARC-10; peak memory cap respected (block size from available memory).
- **Accept:** architecture budgets met; results bit-identical to before for the default methods.
- **Files:** `tools/speed.py` cases, `calibration/{masters,combine}.py`, `native/src/combine.rs` (only if profiling asks)

### CAL-21. Validation set for calibration  (P2)
**open**
- **Build:** tests under `tests/validation/` with stored reference statistics: IRAF `ccdproc` + `imcombine` runs for
  CAL-5's methods; ccdproc library run for variance propagation (CAL-13) on the same frames; BANZAI comparison
  (have, as a test); fringe (CAL-10) and mosaic (CAL-4) sets. The IRAF scripts used are kept in
  `tests/validation/scripts/` so that any agent can regenerate the references.
- **Accept:** `pytest -m validation` covers every calibration capability with a real set.
- **Files:** `tests/validation/test_calibration_*.py`, `tests/validation/scripts/iraf/ccdred_*.cl`, `tests/validation/scripts/ccdproc/*.py`, `tests/validation/data/calibration/`

### CAL-22. Calibrate frames as they arrive  (P2)
**open**
- **Reference:** AstroImageJ Data Processor polling; MaxIm DL auto-calibrate on acquire.
- **Build:** "Follow a folder" in the Calibrate stage with the night's masters (or the library's): each new light is
  calibrated on arrival and handed to whoever follows (Photometry PHO-19, live stack, Images); the Observing window
  can switch it on for its sequence.
- **Accept:** a replayed night gives the same calibrated files as the batch run (bit-identical).
- **Files:** `calibration/live.py`, `photometry/live.py` (`load_masters` moved here), `calibration/steps.py`, UI calibrate panel, `tests/test_calibration_live.py`

### CAL-23. Header tools  (P1)
**open**
- **Ours now:** header editing of one file in the Images window (`io/fits.save_as` with set / delete cards); nothing for many files.
- **Reference:** IRAF `ccdhedit`, `hedit`, `asthedit`, `setairmass`, `setjd`; AstroImageJ DP "FITS header updates"
  (target coordinates, observatory, airmass, JD, HJD, BJD written to the header); MaxIm DL batch header edit.
- **Build:** Tools → "Edit headers of many files…": set / rename / delete keywords by rule over a selection, with a
  preview table (old → new) and writing **copies** by default (in place only after an explicit confirmation naming
  the count of files); computed keywords: mid-exposure `DATE-AVG`, `JD_UTC`, `HJD_UTC`, `BJD_TDB`, `AIRMASS`,
  `ALT`, `AZ`, `HA`, `MOONSEP` from the site and target (name resolved or coordinates); time fixes: clock offset,
  UTC offset mistakes, exposure-start vs end conventions; plate-solve many files and write the WCS (AST); each run is
  a project step with provenance; undo restores the previous copies list.
- **Accept:** a set of 48 frames with OBJECT wrong and no coordinates gets the right OBJECT, RA / Dec and BJD_TDB
  (equal to `timing` values within 1 ms); originals untouched; the Photometry window then needs no typed
  coordinates.
- **Files:** `calibration/headers.py`, step `calibration.headers`, UI tool, tests.

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history of the calibration engine before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
