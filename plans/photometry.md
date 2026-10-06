# Photometry and light curves: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.1).

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, this file's "Conventions" and "Definition of done", your area file, and `plans/interface.md` before
   you touch anything the user sees.
2. Claim the step in its file and push before starting; one step at a time; push at least hourly; mark it done with
   the commit, or `partly done` with what is missing.
3. Build every bullet, show every Accept line. No silent scope cuts: doubts go under "Questions for the architect".
4. Research first (papers, reference programs' source); learn, never copy; nothing GPL bundled.
5. Synthetic test with known truth **and** real data against a reference; the reference numbers become a test.
6. Use the program as a user (real clicks, screenshots in four languages, looked at) before calling it done.
7. Only kit components in the interface; workflow first; one primary action; tooltips; undo; nothing locked.
8. Errors by code, saying what happened and what to do, translated (tr, de, es: 0 unfinished). Guide updated.
9. Measure time and memory; meet the budget; CPU and GPU paths give the same result.
10. Commits in the owner's name only, no "Claude" anywhere; everything to `main`; never delete without the owner.

## Scope and goal

From a set of images to a light curve a referee accepts, and to the reports the community takes: aperture, PSF and
difference-image photometry; comparison stars and ensembles; errors; detrending; times of minimum and transit fits
in place; catalogue magnitudes; whole-field time series; space-mission pixels; moving objects.

**Goal:** everything AstroImageJ, HOPS, EXOTIC, Muniwin, MaxIm DL's photometry tool, Siril's light curves and IRAF
`apphot` / `daophot` / `photcal` can do, in one window whose stages lead from the images to the report — with
catalogue help, honest errors and undo, which none of them has together.

## What the reference programs do (read 2026-11-07 … 2026-11-09)

Sources read, never copied (AstroImageJ, Siril, C-Munipack and PyReduce are GPL): AstroImageJ `astroj/Photometer.java`,
`Centroid.java`, `Astronomy/MultiAperture_.java`, `MultiPlot_.java` (19 400 lines: the fit panel, detrending,
NEB reports, AAVSO report), `Seeing_Profile.java`, `FitOptimization.java`, `multiplot/MeridianFlip.java`,
`MandelAgolTransitModel.java`, `Periodogram_.java`, `Data_Processor.java`; Siril `src/algos/photometry.c`,
`comparison_stars.c`; IRAF `noao/digiphot/apphot`, `daophot`, `photcal`; MaxIm DL and C-Munipack manuals;
lightkurve; HOPS and EXOTIC documentation.

| Topic | AstroImageJ | Siril | IRAF | MaxIm DL / Muniwin | HOPS / EXOTIC |
| --- | --- | --- | --- | --- | --- |
| Aperture sum | exact pixel–circle overlap; circular, **elliptical** (5.5.1), free-form pixel apertures | linear edge weight | linear edge weight; several apertures in one pass | circular | circular; EXOTIC scans aperture and annulus sizes |
| Sky | annulus mean; 2σ iterative star removal; optional plane; mask kept for the next frame | Hampel robust mean | `fitskypars.salgorithm`: **mode** is the default in the current source (`apphot` and `daophot` `fitskypars.par`; older `apphot` releases shipped centroid); also median, centroid of the histogram, gauss, crosscor, ofilter, mean, constant, file; rejection (`sloreject` / `shireject` 3σ, `snreject` 50), histogram `khist` 3σ and `binsize` 0.1σ, `rgrow` | median-mean | median |
| Error | source + sky Poisson, dark, read noise, quantisation (Merline & Howell 1995) | measured sky σ | measured sky σ + epadu, readnoise | from reference-star scatter when ≥ 3 | photon + scatter |
| Centre | Howell marginal sums; per-aperture on / off | PSF fit | centroid / gauss / ofilter / none; `maxshift`; `minsnratio` | centroid | Gaussian or Moffat fit |
| Radii | radial profile: 1 % of peak, sky 2× and 4×; variable aperture = factor × FWHM per frame | from FWHM | typed; `mkapfile` growth curves | typed, snap | scanned |
| Comparison stars | by clicks; "auto comp" without catalogue; RA / Dec apertures file; ensemble toggles; **optimise the set** | from catalogue: ΔV 3, Δ(B−V) 0.5, error 0.03, not variable | — | tag reference and check stars with magnitudes | catalogue-assisted (EXOTIC: AAVSO comparison stars) |
| Detrending | linear terms in the fit χ², BIC, exhaustive search, meridian flip step, Kepler spline | — | — | — | airmass polynomial; EXOTIC: airmass exponential in the fit |
| Transit fit | Mandel & Agol 2002 quadratic law; parameters baseline, (Rp/R*)², a/R*, Tc, inclination, u1, u2; priors with widths; locks; outputs depth, T14, T23, τ, b, ρ*, Rp; χ², BIC, RMS; odd / even at 2 × P | — | — | — | pylightcurve model, MCMC (HOPS); nested sampling with priors from the NASA Exoplanet Archive (EXOTIC) |
| Reports | AAVSO variable-star report; AAVSO exoplanet; **NEB check** folder for TESS follow-up; "save all" (table, plot, configuration, apertures, field image) | ETD, AAVSO | text tables | AAVSO, CSV | ExoClock upload files; AAVSO Exoplanet Database file |
| PSF / crowded | "create mean PSF" only | PSF fit of each star | **daophot**: empirical PSF with look-up table, `nstar`, `allstar`, `substar`, `addstar` | — | PSF option (HOPS) |
| Absolute photometry | — | photometric colour calibration (for pictures) | **photcal**: `mknobsfile`, `fitparams`, `evalfit`, `invertfit`: zero point, extinction, colour terms from standards | zero point from reference stars | — |
| Real time | Data Processor polls a folder, calibrates, measures, updates the plot | — | — | — | — |
| Period search on the curve | BLS and TLS on the GPU | — | — | — | — |

Community formats and rules read: AAVSO Extended File Format; AAVSO Exoplanet Database file (`#TYPE=EXOPLANET`,
`#DATE_TYPE=BJD_TDB`, measurement and up to four detrend columns; guide at app.aavso.org/exosite/doc); ExoClock upload
(BJD_TDB / flux / error text plus the observation form); ETD / VarAstro text; TFOP SG1 observation guidelines
(NEB check, the required plots and tables); ALCDEF 2.x for asteroid light curves; MPC ADES.

## What we already have (do not redo; details and commits in `docs/history/photometry-plan-2026-11-09.md`)

| # | Feature | Where |
| --- | --- | --- |
| 0 | Photometry window (first layout): steps, image, results dock | `ui/photometry_page.py` (→ UI-16.1) |
| 1 | Validation against IRAF `phot` on two nights (fluxes within 0.015 %); "radii as AstroImageJ" rule; grouped median for integer data | `tests/validation/test_iraf_phot.py`, `aperture.aij_radii`, `_grouped_median` |
| 2 | Noise model with the camera's numbers (gain, read noise, dark, quantisation) | `aperture.camera_pixel_noise` |
| 3 | Sky estimates: median, mode, clipped mean, plane | `aperture.sky_estimate` |
| 4 | Saturation and linearity limit flagged per point, leave-out button | page + measurements table |
| 5 | Target not centred (follows the field); donut stars; `max_move` | `lightcurve.light_curve(fixed=)`, `_wide_centroid` |
| 6 | Measurements table with AstroImageJ's column names, filter, columns, CSV | `photometry/measurements.py` |
| 7 | Star list saved and opened on another night through the plate solution | `photometry/starlist.py` |
| 8 | Multi-plot: series, normalisation range, binning, colours, template, leave each comparison star out | `photometry/multiplot.py` |
| 9 | Detrending chosen by BIC, meridian-flip step, spline trend, outliers | `differential.detrend_bic`, `spline_detrend` |
| 9a | Best comparison set (never looks at the target) | `differential.best_comparison_sets` |
| 9b | Speed: 1000 × 4k² frames ≈ 4 min estimated; field offset without the slow path | `lightcurve._field_offset` |
| 10 | Several apertures at once, radius chosen afterwards, relative aperture correction | `lightcurve.with_aperture`, `aperture_correction` |
| 11 | Several filters in one run, colour-index curve | `photometry/multifilter.py` |
| 12 | Several nights joined on one zero point | `photometry/nights.py` |
| 13 | Frames missing a comparison star kept (Honeycutt-style share) | `differential.ensemble` |
| 14 | HJD_UTC column; header time as start / middle / end; shutter delay | `timing.mid_time`, `timing.hjd` |
| 15 | ETD / VarAstro text export; CSV readable by Models | `export.etd_text` |
| 16 | Trapezoid transit fitted together with detrending terms (BIC) | `minima.trapezoid_fit(covariates=)` |
| — | Field identification without a solver (Gaia), VSX variables, OBJECT check; comparison suggestions from Gaia; catalogue magnitudes (APASS DR9, Gaia → V R I by Riello 2021); extinction and transformation coefficients; AAVSO Extended export; PSF photometry with grouped Gaussians; variable-star search; live light curve; frame quality; polarimetry; TESS / Kepler pixel files as frame series; asteroid astrometry | `photometry/{field,catalog,coefficients,export,fieldstars,live,quality,polarimetry,moving}.py`, `io/tpf.py` |

Left out by the previous agent under "rule 12" and now planned: centring algorithm choice (PHO-44), IRAF's
histogram-centroid sky and a star mask in the ring (PHO-45), residuals under a fit and detrending per series
(PHO-26, PHO-46), scintillation for a radius chosen afterwards (PHO-34), raw errors lost in the exported CSV
(PHO-48).

## Decisions

- Default method stays aperture photometry with an ensemble; PSF and difference imaging are choices of the Measure
  stage, suggested by the program when the field is crowded (PHO-18.5).
- Roles and colours: target bluish green `T1`, comparison vermilion `C1…`, check sky blue `K1…` (interface tokens).
  The measurements table keeps AstroImageJ's names (`T1`, `C2`, …) in its columns for side-by-side comparison.
- Times: BJD_TDB is the default column wherever the position is known; HJD_UTC and JD_UTC are written beside it.

## To ask the owner

- An AstroImageJ Measurements table of one of your nights with the radii written down (PHO-41).
- Your AAVSO observer code and, if you have them, ExoClock and TFOP accounts for the upload checks (PHO-27).

## For the owner to try

- After UI-16.1: measure the NY Vir night in the new window; send a screenshot of any stage where it was unclear what
  to do.
- After PHO-17 and PHO-25: let the program suggest comparison stars for NY Vir and say whether you agree with the
  reasons it gives for the stars it left out.

## Data used

- `data/photometry/qatar1-lco`: Qatar-1 transit, LCO 0.4 m, 24 of 265 calibrated frames here (whole night for
  timing).
- HAT-P-32, MicroObservatory, 142 raw frames (CI downloads it; IRAF reference table in `tests/validation/data`).
- `data/photometry/ai-dra-tess`: TESS cut-out of AI Dra (pixel-file photometry, 42 minima).
- `data/photometry/sa98-landolt-lco`: Landolt SA 98 in B and V (transformation coefficients).
- `data/astrometry/eros-lco`: 433 Eros (moving object).
- To add (each with `SOURCE.md`): a crowded field with a published light curve (PHO-18, PHO-29); a TFOP-style
  follow-up night of a TESS candidate with its public AstroImageJ products from ExoFOP (PHO-23, PHO-27); an asteroid
  night with an ALCDEF record (PHO-21); a standard-star night at several airmasses (PHO-28).

## Steps

Order of work: PHO-W, then P1: 17, 25, 36, 48, 26, 27, 23, 18, 19, 33, 34, 41; then P2: 20, 21, 22, 24, 28, 29, 30,
31, 32, 35, 37, 42, 43, 45; then P3: 38, 39, 40, 44, 46.

### PHO-W. The Photometry window on the new anatomy  (P1)
**open**
- This is `plans/interface.md` UI-16.1; claim it there and here. Stages: Images, Field, Stars, Apertures, Measure,
  Light curve, Timing and fit, Report; results dock: Light curve, Multi-plot, Measurements, Stars, Frames, Checks.
- **Extra accept for this window:** the owner's NY Vir flow (choose the images → the field is identified → the
  target is found from the header or by name → comparison stars suggested → radii chosen → measured → minimum timed
  → sent to O−C) takes **seven clicks or fewer** on the practice night, counted by the QTest; every automatic choice
  on the way is listed in the stage with its reason.
- **Depends on:** ARC-4.2, ARC-5, ARC-6, ARC-7, ARC-8, UI-1 … UI-4.
- **Files:** `ui/photometry/{window,controller,state,menus}.py`, `ui/photometry/panels/{images,field,stars,apertures,measure,lightcurve,timing,report,frames,checks}.py`, `tests/ui/walks/photometry.py`, guide 06

### PHO-17. Comparison-star rules the user can set, with the reason for every star left out  (P1)
**open** (agent2's claim of 2026-11-09 is released; nothing was pushed for it)
- **Why:** the choice of comparison stars decides the light curve; today the rules are fixed in code and a star left
  out is left out silently.
- **Reference:** Siril `findcompstars` (`src/algos/comparison_stars.c`): ΔV ≤ 3 mag, Δ(B−V) ≤ 0.5, catalogue error ≤
  0.03 mag, catalogue APASS or NOMAD, whole image or a centred circle, variables removed with GCVS / VSX / Gaia.
  AstroImageJ "auto comparison stars" without a catalogue: peak between mean + 1σ and 0.9 × maximum, brightness
  50–150 % of T1, no neighbour within 2 r_ap, ranked by brightness closeness and nearness, at most 12. AAVSO CCD
  Photometry Guide (chapter on comparison stars): similar colour, similar brightness (not much fainter than the
  target), close on the sky, not variable, not at the edge. Gaia DR3 variability proxies: `phot_variable_flag`, and
  the excess of the G-band flux scatter over the expected one at that magnitude (amplitude proxy
  √N_obs / flux_over_error; Eyer et al. 2023, Mowlavi et al. 2021).
- **Ours now:** `photometry/field.comparison_stars` (|ΔG| ≤ 2.5; colour within 0.5 preferred; Gaia flag; VSX within
  3 px; no Gaia neighbour brighter than G + 5 inside `r_out`; peak < 0.8 × saturation; `margin` 60 px);
  `aperture.suggest_comparisons` (pixel rules without a solution); step `photometry.suggest`.
- **Read first:** the Siril file above; AstroImageJ `MultiAperture_.java` (the auto-comparison part); the AAVSO guide
  chapter; Gaia DR3 documentation of `phot_g_mean_flux_over_error` and `phot_g_n_obs`.
- **Build:**
  1. `photometry/comprules.py`: `@dataclass ComparisonRules` with defaults: `brighter_by_max = 1.5` mag,
     `fainter_by_max = 1.0` mag (a star much fainter than the target only adds noise; both limits in the band of
     the frames when known, else Gaia G), `colour_tolerance = 0.5` (in B−V when known, else BP−RP scaled by 0.77),
     `colour_required = False` (when True, stars outside are rejected, not just ranked lower), `max_distance_arcmin =
     None` (whole frame), `catalogue_error_max = 0.03` mag, `exclude_variables = True` (VSX, GCVS, Gaia flag),
     `exclude_gaia_noisy = True` (scatter excess > 3 × the median at that magnitude), `neighbour_rule`: no star
     within `r_out` brighter than `own magnitude + 5`, and none within `r_ap + 1 FWHM` at all, `peak_max = 0.8 ×
     min(saturation, linearity limit)` **on every frame of a sample of 10 frames spread over the night**, not only
     the first, `edge_margin_px` = larger of 3 × `r_out` and the largest drift of the night + `r_out`,
     `min_snr = 100` on the first frame, `count = 8`, `prefer_aavso_sequence = True` (PHO-25).
  2. `comprules.judge(field, target, frames_sample, rules)` → a table of **every** catalogue star brighter than
     target + 3 mag with columns: id, x, y, magnitude, colour, distance, peak, S/N, and `verdict` = `chosen` or one
     reason code out of `too_bright`, `too_faint`, `colour`, `variable_vsx`, `variable_gcvs`, `variable_gaia`,
     `noisy_gaia`, `neighbour`, `saturated`, `non_linear`, `edge`, `low_snr`, `bad_pixel` (PHO-36),
     `catalogue_error`, `too_far`, `not_needed` (passed but beyond `count`). Ranking of the passed stars: colour
     closeness and brightness closeness with equal weight after scaling by their tolerances, then nearness.
  3. `photometry.suggest` step takes `rules` (dict) and returns the table; the old parameters keep working.
  4. Stars stage: "Suggest comparison stars" marks the chosen ones as *suggested* (dotted rings) until the user
     accepts (one click "Use these") or edits; a folded section **Comparison-star rules** with the fields above
     (`FormRow`s with units and resets); a result tab or popover **Why these stars?** showing the table, sortable,
     with a click on a row showing the star in the image; a rejected star can be forced in ("Use anyway") and the
     table then says `chosen by the user`.
  5. Without a plate solution: the pixel rules (`aperture.suggest_comparisons`) with the same table and the reasons
     that can be known (brightness, neighbours, edge, peak); a banner says that colour and variability could not be
     checked and offers "Identify the field".
  6. GCVS through `services/gcvs` (VizieR B/gcvs) besides VSX; both cached.
  7. Error codes: `photometry.no_comparison_star` (what: no star passed; do: the three rules that removed most
     stars, with a button that relaxes each).
  8. Guide 06 "Choosing comparison stars" rewritten around the rules, four languages.
- **Accept:**
  1. Synthetic field with one star of each rejection kind: each gets exactly its reason code.
  2. NY Vir field (the owner's night when present in `data/owner/`, otherwise its Gaia field at the frame's scale):
     the table equals Siril's rules applied by hand to the same catalogue rows (a stored expected table).
  3. Qatar-1 night: the eight chosen stars give a point-to-point scatter of the target not worse than the set chosen
     by hand in the validation (0.44 %).
  4. A night where a suggested star saturates only late in the night: it is rejected as `saturated` (sample of
     frames), which the old code missed (test with synthetic frames).
  5. Suggest on a 4k × 4k frame with 5000 Gaia stars: < 1.5 s.
- **Files:** `photometry/comprules.py` (new), `photometry/field.py`, `photometry/steps.py`, `services/gcvs.py`,
  `ui/photometry/panels/stars.py`, messages, tests, guide.
- **Depends on:** PHO-W for the interface part (the engine part can be done first).
- **Notes from the sources (architect, 2026-11-10):** Siril `src/algos/comparison_stars.c`: a star passes when
  ΔV ≤ `delta_Vmag`, |Δ(B−V)| ≤ `delta_BV`, and — only for APASS — 0 < `e_mag` ≤ `max_emag`; the default numbers
  (3, 0.5, 0.03) are those of the `findcompstars` command's documentation, not constants of this file. AstroImageJ
  `MultiAperture_.java` (fields near line 304): `minPeakValue 2000`, `upperBrightness 150` %, `lowerBrightness 50` %,
  `brightness2DistanceWeight 50`, `maxSuggestedStars 12`; `Seeing_Profile.java`: radii 1.7 / 3.4 / 6.8 FWHM.

### PHO-18. Crowded fields: PSF photometry with an empirical PSF, and neighbour removal  (P1)
**open**
- **Why:** aperture photometry of a target with a neighbour inside the aperture or the ring gives a wrong depth; our
  PSF path is a circular Gaussian only.
- **Reference:** DAOPHOT (Stetson 1987, PASP 99, 191): analytic function plus an empirical look-up table of
  residuals from PSF stars; `nstar` (simultaneous fit of a group), `allstar` (iterative fit and subtraction),
  `substar`. Anderson & King 2000 (PASP 112, 1360): effective PSF (ePSF) built iteratively from many stars with
  oversampling. photutils (BSD): `EPSFBuilder`, `PSFPhotometry`, `IterativePSFPhotometry`, `SourceGrouper`,
  `MoffatPSF`, `GaussianPSF` — may be used as a library. Siril fits Gaussian or Moffat per star. HOPS offers PSF
  photometry for defocused and crowded cases.
- **Ours now:** `photometry/fieldstars.psf_measure` (circular Gaussian of the frame's FWHM; stars closer than 2.5
  FWHM fitted together).
- **Read first:** Stetson 1987 §3–4; Anderson & King 2000 §3; photutils PSF documentation and the source of
  `EPSFBuilder`; IRAF `daophot` help pages of `psf`, `nstar`, `allstar`.
- **Build:**
  1. `photometry/psf.py`: `select_psf_stars(data, catalogue, n=25)` (bright, unsaturated, isolated by the neighbour
     rule of PHO-17, away from edges and bad pixels, spread over the frame); `build_epsf(data, stars, oversampling=2,
     size=…)` wrapping `EPSFBuilder` with sigma-clipped recentring; analytic alternatives `moffat` and `gaussian`
     (elliptical, with angle) fitted to the same stars; `psf_quality` (residual RMS of the PSF stars after
     subtracting the model, in per cent of the peak).
  2. PSF model per frame by default (seeing changes); option "one PSF shape per night scaled by each frame's FWHM"
     for sparse fields with too few PSF stars (< 6).
  3. `psf.measure(data, variance, positions, psf, groups, fit_positions=False|True, sky=local)`: forced photometry at
     the positions predicted from the reference frame and the field offset (the same prediction as the aperture
     path), positions fitted only within ± `max_move`; grouped fit (`SourceGrouper`, separation 2.5 FWHM) including
     **every catalogue neighbour** inside the group radius even if the user did not mark it (positions from Gaia at
     the epoch when the field is solved); returns flux, error from the fit covariance scaled by reduced χ², χ² per
     star, a "sharpness" and whether the fit hit a limit.
  4. `psf.subtract_neighbours(data, …)` → an image with all neighbours of the measured stars removed; the aperture
     path can then run on it (method "aperture after removing neighbours": the target's own flux is still an
     aperture sum, which is more robust for trailed or defocused stars).
  5. `light_curve(..., method = "aperture" | "psf" | "aperture_clean")` carried through the step, the live path
     (PHO-19) and the measurements table (new columns `PSF_chi2_<star>`, `PSF_flag_<star>`).
  6. Measure stage: Method `Segmented` (Aperture · PSF · Aperture after removing neighbours); a banner **suggests**
     the third when a catalogue neighbour brighter than target + 4 mag lies within `r_out` of any measured star, and
     says which; a "PSF" result tab shows the ePSF picture, the PSF stars (click to exclude one), the quality
     number, and for the current frame the residual image (original minus all fitted stars).
  7. Native kernel `psf_fit_group` (ARC-9) only if profiling shows the grouped fits dominate; write the measured
     profile under this step first.
  8. Error codes: `photometry.psf_too_few_stars`, `photometry.psf_bad_fit` (per frame: left out with the reason).
- **Accept:**
  1. Synthetic pair 1.5 FWHM apart, flux ratio 1 : 3, S/N 200: each flux within 1 % (PSF) and within 1.5 %
     (aperture after removal); aperture alone is off by more than 10 % (the test asserts that too).
  2. Synthetic eclipse of the fainter star of that pair: the depth is recovered within its error by both new
     methods.
  3. Real crowded field (the set added to `data/photometry/`): fluxes agree with IRAF `daophot.allstar` run on the
     same frame with the same PSF stars within 2 % for stars with S/N > 50 (reference table committed); the target's
     published depth is recovered.
  4. Qatar-1 (uncrowded): PSF and aperture light curves agree within their errors (no bias introduced).
  5. 265 frames × 12 stars with the ePSF: < 3 × the aperture time.
- **Files:** `photometry/psf.py` (new), `photometry/{lightcurve,fieldstars,steps,measurements}.py`, UI panels,
  messages, tests, guide 06.

### PHO-19. Real-time photometry is the same code as the night run  (P1)
**open**
- **Reference:** AstroImageJ Data Processor (`Data_Processor.java`): polls a folder, calibrates each new file, runs
  Multi-Aperture with the stored apertures, updates the table and the plot.
- **Ours now:** `photometry/live.LiveLightCurve`: its own incremental copy of the per-frame method; does not know the
  sky methods, noise model, missing-comparison handling, star lists or PSF path added since.
- **Build:**
  1. Refactor so that `lightcurve._measure_frame` is the single per-frame function; `LiveLightCurve.add(path)` calls
     it with the same options object (`MeasureOptions` dataclass shared by the step, the live path and recipes).
  2. Live state is the same light-curve dict growing by one row; every result view of the window (plot,
     measurements, checks) updates from it; lost and partial frames appear at once with their reasons.
  3. Photometry Images stage: "Follow a folder" (`PathField` kind folder + a toggle): files older than `min_age_s`
     and complete (size stable for 2 s, FITS readable) are taken; calibration with chosen masters first when the
     frames are raw.
  4. From Observing: a running sequence can open the Photometry window in follow mode on its target (OBS).
  5. A stalled night (no new file for 3 × the cadence) shows a banner, not an error.
- **Accept:** the Qatar-1 night replayed file by file (a test copies files into a folder with delays) gives
  **bit-identical** `rel_flux`, errors and times to the batch run with the same options, for the aperture and the
  PSF method; per new 4k frame < 0.5 s.
- **Files:** `photometry/{live,lightcurve}.py`, `photometry/options.py` (new), UI images panel, tests.

### PHO-20. The same run without the window  (P2)
**open**
- **Build:** through ARC-12: File → "Save as recipe…" writes images pattern, star list (RA / Dec), radii, every
  option, exports; `astrowb-cli recipe night.toml --set images=/path/*.fits` runs it; `astrowb.api.light_curve(...)`
  documented with an example notebook-style script in the guide.
- **Accept:** GUI run and command-line run of the practice night and of Qatar-1 give identical measurement tables
  (byte-identical ECSV apart from the creation time).
- **Depends on:** ARC-12, PHO-48.
- **Files:** `core/recipe.py`, `ui/photometry/controller.py` (export), `api/photometry.py`, `tests/test_photometry_recipe.py`, guide 06

### PHO-21. Light curves of moving objects  (P2)
**open**
- **Reference:** MPO Canopus (comparison-star selector with catalogue magnitudes, sessions joined across nights,
  reduction to unit distances and a phase angle, export to ALCDEF); Tycho Tracker's light-curve module; MaxIm DL
  (tag the object on the first and last frame). ALCDEF standard document (alcdef.org); H–G system (Bowell et al.
  1989); light-time correction.
- **Ours now:** `photometry/moving.track` (astrometry of a moving object between two clicks), MPC ADES report.
- **Build:**
  1. `photometry/moving_lc.py`: the object's position on each frame from (a) JPL Horizons / MPC ephemeris for the
     site and mid-exposure times (`services/horizons`), refined by a centroid, or (b) the two-click linear track;
     the aperture follows it.
  2. Comparison stars: fixed pixel stars do not work when the field drifts with the object; instead a **catalogue
     ensemble per frame**: all usable field stars with catalogue magnitudes (PHO-25) give the frame's zero point
     (clipped mean; colour term optional), so the object's magnitude is on the standard system on every frame and
     nights join by themselves.
  3. Frames where the object is within `r_out` of a catalogue star brighter than object + 4 mag are flagged
     `blended` and left out by default (listed).
  4. Reduced magnitude `H(α) = m − 5 log10(r Δ)` with r, Δ, phase angle α and light-time from Horizons per frame;
     time corrected for light-time (column `JD_LTC`); optional H–G removal of the phase trend over several nights.
  5. Export ALCDEF 2.x (metadata block from the observer and equipment profiles; one `DATA=` line per point);
     the curve goes to Light curves and period (PER: Fourier fit of rotation, FALC).
  6. Stars stage in "Moving object" mode: object by designation; the predicted track drawn over the image.
- **Accept:** a synthetic object of constant brightness moving 300 px through a real star field gives a flat curve
  (RMS within 1.2 × the predicted error) with blended frames flagged; the real asteroid night gives the published
  rotation period within its error in PER and an ALCDEF file that passes the ALCDEF validator rules (checked by our
  own parser of the standard).
- **Files:** `photometry/moving_lc.py`, `photometry/export.py` (ALCDEF), `services/horizons.py`, UI, tests, guide.
- **Depends on:** PHO-25.
- **Notes from the sources (architect, 2026-11-10):** the current ALCDEF standard is **2.3.0** (March 2024,
  alcdef.org/docs/ALCDEF_Standard.pdf): since 2.2 a light-curve block may not hold a single observation and
  keywords required by NASA's Planetary Data System were added; 2.3.0 removed `ALLOWSHARING`. Write the exporter
  against 2.3.0 and read the keyword tables in the PDF. AstroImageJ 5.5.0 (April 2025) added moving-target tracking
  to Multi-Aperture: read its release page (astroimagej.com/releases/55000/) and that part of `MultiAperture_.java`
  for how the aperture is carried between the first and last frame.

### PHO-22. Aperture shapes  (P2)
**open**
- **Reference:** AstroImageJ `ShapedApertureRoi` (ellipse; 5.5.1 added it to Multi-Aperture for non-circular PSFs),
  `FreeformPixelApertureRoi` (painted pixels, for TESS-like stamps and blends); lightkurve aperture masks.
- **Build:** `aperture.measure(shape = circle | ellipse | pixels)`: ellipse with axis ratio and angle from the
  star's second moments on a median of 10 frames (or typed), elliptical annulus with the same shape; exact
  pixel–ellipse overlap (photutils `EllipticalAperture`, `EllipticalAnnulus`); painted masks (click-drag on the image
  in the Apertures stage, one mask per star, stored in the star list); for long trails a "racetrack" (two half
  circles joined by a rectangle) of given length and angle. Table columns `Ap_shape`, `Ap_a`, `Ap_b`, `Ap_angle`.
- **Accept:** a 3 : 1 trailed star gives the flux of its untrailed copy within 1 % with the ellipse and within 0.5 %
  with the racetrack, at lower noise than the circle that contains the trail (asserted); painted mask on a TESS stamp
  equals lightkurve's `to_lightcurve(aperture_mask=…)` within 1e-6 relative.
- **Files:** `photometry/aperture.py`, `starlist.py` (schema +1 with migration), UI apertures panel, tests.
- **Notes from the sources (architect, 2026-11-10):** elliptical apertures arrived in AstroImageJ 5.5.0 / 5.5.1 (2025)
  as an option of Multi-Aperture "for non-circular PSFs, as with poor tracking or guiding"; multi-threaded
  photometry came with the same release.

### PHO-23. Nearby-eclipsing-binary check  (P1)
**open**
- **Why:** TESS pixels are 21″; ground follow-up must show which star has the dip. AstroImageJ's NEB reports are the
  community standard for TFOP.
- **Reference:** AstroImageJ's NEB analysis ("Create NEB search reports and plots": the menu item is in
  `MultiPlot_.java` and `AstroStackWindow.java`, the logic is the macro
  `Astronomy_/src/main/resources/Astronomy/NEBSearchMacro.txt`, 3300 lines with a change log on top); TFOP SG1
  Observation Guidelines (the NEB check: all Gaia stars within 2.5′ that are bright enough to cause the TESS depth;
  the per-star required depth; dispositions "Cleared", "Cleared-too faint", "Likely cleared", "Not cleared-flux too
  low", "Potential NEB"; the dmag-vs-RMS plot); the TESS magnitude from Gaia (Stassun et al. 2019, TIC-8 relation).
- **Read first:** the AstroImageJ NEB code path end to end and write its thresholds here; the current SG1 guidelines
  PDF (ExoFOP-TESS); Stassun et al. 2019 §2.3.
- **Build:**
  1. `photometry/neb.py`: `candidates(field, target, radius_arcmin=2.5, tess_depth_ppt)` → Gaia stars with ΔT
     (TESS-band magnitude difference to the target) for which the required eclipse depth `d_i = d_T × 10^(0.4 ΔT_i)`
     is ≤ 100 %; others are "too faint to matter".
  2. Every candidate is measured on every frame with the night's apertures (PSF or neighbour-removed apertures by
     default here, PHO-18), detrended like the target; for each: RMS of its curve binned to the ingress duration,
     predicted depth `d_i`, ratio `d_i / RMS`, a fitted box at the predicted transit window (depth, error), and the
     disposition by the SG1 rules as read in the sources (thresholds written under this step).
  3. Outputs in a folder: the table (CSV), one light-curve plot per candidate with the predicted depth drawn, the
     Δmag-vs-RMS summary plot, the field image with every candidate labelled and coloured by disposition.
  4. Timing and fit stage: "Check nearby stars (NEB)…" asks for the TESS depth and ephemeris (fetched from ExoFOP /
     the Exoplanet Archive by TOI / TIC name through `services`), runs as a task; results tab **Nearby stars**.
- **Accept:** synthetic field where a neighbour 12″ away, 3 mag fainter, carries a 20 % eclipse: named "Potential
  NEB", the target cleared; a field with no eclipse: all cleared or "too faint"; on the public TFOP night the
  dispositions equal the ones in the public AstroImageJ NEB table for that night (stored reference).
- **Files:** `photometry/neb.py`, step `photometry.neb`, `services/exofop.py`, UI, tests, guide 06.
- **Depends on:** PHO-18 (methods), PHO-25 (magnitudes).
- **Notes from the sources (architect, 2026-11-10; `NEBSearchMacro.txt` read):**
  - Stars within a search radius (default 2.5′) of the target are measured in the same Multi-Aperture run (as `T`
    stars); the macro works on the measurements table.
  - Each star's Δmag to the target is taken from the **measured** weighted-mean `Source-Sky` ratio in the observed
    band (an earlier TESS-band correction was removed); for every star except the target a buffer of −0.5 mag is
    added (`dmagBuffer`), i.e. the star is treated as half a magnitude brighter than measured, to be safe.
  - Required depth: `NEBdepth [ppt] = target depth [ppt] / 10^(−(Δmag − 0.5) / 2.5)`.
  - RMS: of the star's normalised relative flux, after points further than `rmsLimit` × RMS from 1 are dropped and
    the curve is normalised again.
  - Dispositions, tested in this order: "Not cleared — flux too low" when the weighted-mean `Source-Sky` per aperture
    pixel is < 2 counts; "Cleared — too faint" when NEBdepth ≥ 1000 ppt; "Cleared" when NEBdepth / RMS ≥ 5; "Likely
    cleared" when 3 ≤ NEBdepth / RMS < 5; otherwise "Not cleared". With several aperture sizes the best disposition
    per star is kept (priority: cleared > likely cleared > too faint > not cleared > flux too low).
  - Plots: one per star (relative flux with a box of the required depth between the predicted ingress and egress),
    and Δmag against RMS with the "cleared" and "likely cleared" boundary lines; a star's label turns red when its
    nearest neighbour is within 3 aperture radii; neighbours within 10″ are named in the plot's subtitle.
  - Output folder `<measurements file>_<aperture>px_NEBcheck/`.
  - Consequence for Build 1–2: candidates are **selected** from the catalogue (Gaia, with the TESS-band Δmag as
    information), but the required depth uses the measured Δmag with the buffer, as above; both Δmag values are
    columns of our table.

### PHO-24. Measuring between two stars on the image  (P2)
**open**
- **Reference:** AstroImageJ Measure (separation, position angle, Δmag, flux ratio written to a table); MaxIm DL
  Information window (astrometric mode).
- **Build:** the ruler tool of `ImageView` (ARC-7), when both ends are on stars (centroid within 3 px): separation in
  px and arcsec, position angle (N through E, from the WCS), flux ratio and Δmag from apertures of the current radii
  with errors; shown in the Inspector, "Add to table" appends to a measurements table (CSV / ECSV export). Also in
  the Images and Astrometry windows (double-star measures feed AST).
- **Accept:** two synthetic stars with ratio 0.25 at 37.5 px, PA 123°: ratio within 0.5 %, separation within 0.02
  px, PA within 0.05°.
- **Files:** `images/inspect.py` (`pair_measure`), `ui/image/tools.py` (ruler), `tests/test_pair_measure.py`

### PHO-25. Catalogue magnitudes: more catalogues, AAVSO sequences, one model  (P1)
**open**
- **Why:** differential magnitudes need comparison magnitudes; APASS DR9 stops near V = 16 and has known zero-point
  errors; Gaia → V polynomials scatter by 0.03 mag; AAVSO reports should use the AAVSO sequence of the field.
- **Reference:** Gaia Synthetic Photometry Catalogue (Gaia Collaboration, Montegriffo et al. 2023, A&A 674, A33):
  standardised U B V R I, u g r i z, y for ~2 × 10^8 stars to G = 17.65, archive table
  `gaiadr3.synthetic_photometry_gspc` (quality flags per band); ATLAS-REFCAT2 (Tonry et al. 2018; g r i z to 19
  mag, all sky; MAST / VizieR J/ApJ/867/105); APASS DR10 (AAVSO); Pan-STARRS1 DR2 (MAST catalogues API);
  SkyMapper DR4 (southern); SDSS DR17; 2MASS; Tycho-2; UCAC4 (carries APASS B V g r i); Landolt 1992 / 2009 / 2013
  and Stetson's standard fields (CADC); AAVSO VSP API (`…/vsp/api/chart/?star=…&fov=…&maglimit=…&format=json`: chart
  id, comparison stars with AUID, label, RA, Dec, per-band magnitude and error). Transformations: PS1 → SDSS (Tonry
  et al. 2012), SDSS → Johnson–Cousins (Jordi et al. 2006), Gaia → others (Riello et al. 2021).
- **Ours now:** `photometry/catalog.py` (APASS DR9, Gaia with Riello polynomials), `coefficients.catalogue_magnitudes`.
- **Build:**
  1. `services/` modules for each source above (ARC-14), cached; each returns id, RA, Dec at epoch, per-band
     magnitude, error, quality flag, source name.
  2. `photometry/refmags.py`: `reference_magnitudes(positions, band, order=…)` picks per star the best source for
     the band by a documented order (default for B V R I: AAVSO sequence → GSPC (flag good) → APASS DR10 → transformed
     RefCat2 / PS1 / SkyMapper → Gaia polynomial; for g r i z: RefCat2 → PS1 / SkyMapper / SDSS → GSPC), returns the
     magnitude, its error (catalogue error ⊕ transformation scatter) and the source; never mixes sources silently:
     the Stars table has a "Source" column and a banner when the comparison stars come from different sources.
  3. Stars stage: "Magnitudes from…" (Automatic · a chosen catalogue · AAVSO sequence · typed); "Show AAVSO
     sequence" overlays the VSP stars with their labels; choosing them fills `CNAME` / `CMAG` / `CHART` for the AAVSO
     report (the chart id is stored).
  4. Field stage overlay toggles: Gaia, variables (VSX / GCVS), AAVSO sequence, standards.
  5. Offline: all of this works from the cache after one online look-up of the field (ARC-14).
  6. Validation of the sources against each other on Landolt SA 98: the table of mean difference and scatter per
     source and band is written to the guide's methods chapter and checked by a test with recorded responses.
- **Accept:** for SA 98 (recorded responses) GSPC V differs from Landolt by < 0.02 mag mean, < 0.03 scatter (as
  the GSPC paper states) and our pipeline reproduces that; Qatar-1's standard V from GSPC comparison stars is within
  0.03 of APASS; with the network off after one run everything still resolves; the AAVSO report of a field with a VSP
  sequence carries the chart id and the labels.
- **Files:** `services/{gaia,refcat2,apass,panstarrs,skymapper,sdss,twomass,tycho2,ucac4,standards,aavso_vsp}.py`,
  `photometry/refmags.py`, `photometry/catalog.py`, UI stars and field panels, tests, guide 06 and 13.
- **Depends on:** ARC-14.

### PHO-26. Exact transit and eclipse model fitted in the Photometry window  (P1)
**open**
- **Why:** AstroImageJ's most used feature after the light curve: fit the transit with detrending and priors and read
  depth, duration and mid-time at once. Ours fits a trapezoid; the exact model is one window away.
- **Reference:** AstroImageJ fit panel (see the table above): parameters and their priors, locks, "auto-update
  priors", fit statistics, the residual curve under the fit, odd / even view at 2 × P, host-star panel (any of
  Teff, B−V, J−K, R*, M*, ρ* gives the others by tabulated main-sequence relations, then Rp). Mandel & Agol 2002;
  Agol, Luger & Foreman-Mackey 2020 (analytic quadratic model with derivatives); Kipping 2013 (q1, q2 limb-darkening
  sampling); Seager & Mallén-Ornelas 2003 (ρ* from a/R* and P; durations); Winn 2010 (T14, T23, b); Claret limb
  darkening tables (EXO-3).
- **Ours now:** `minima.trapezoid_fit(covariates=)`; `models/eb.py` spheres through the Models window.
- **Build:**
  1. The engine is EXO-1 (exact quadratic-law transit with exposure integration) and EXO-3 (limb darkening from
     tables): this step is the Photometry window's use of them. `photometry/transitfit.py`: model =
     `baseline × transit(t; Tc, P, Rp/R*, a/R*, i or b, u1, u2) × exp(Σ c_k z_k)` with the detrending terms chosen in
     the Light curve stage, an optional meridian-flip step, fitted by least squares (Levenberg–Marquardt with bounds)
     then, on request, MCMC (EXO-5 sampler with convergence test).
  2. Parameters table in the Timing and fit stage (kit `TableView`, editable): for each of baseline, Rp/R*, a/R*,
     Tc, inclination (or impact parameter — a toggle), u1, u2, and each detrend coefficient: start value, "fit" ☑,
     prior centre and width ("use" ☑), lower / upper limit; "Fill from the archive" (period, expected Tc for the
     night, depth, a/R*, inclination from the NASA Exoplanet Archive / ExoClock by planet name; P is fixed by
     default for a single transit); "Limb darkening from tables" (needs Teff, log g, [Fe/H] and the filter; values
     fixed by default as AstroImageJ users do, or Gaussian priors).
  3. Derived, with errors: depth (ppt and mmag), T14, T23, τ (ingress), b, ρ* (g cm⁻³) from a/R* and P, Rp in
     Jupiter and Earth radii when R* is given (host-star panel: Teff / R* / M* typed or fetched), and the O−C against
     the catalogue ephemeris with its error (propagated ephemeris error included).
  4. Statistics: χ², reduced χ², BIC, dof, RMS (ppt and mmag), the red-noise factor β (PHO-34).
  5. Plot: data, model, the detrended curve, residuals under it (always), predicted ingress / egress lines from the
     ephemeris, the fitted Tc with its error band; "Odd / even" view when several transits are in the data.
  6. The same panel fits an **eclipse of a binary** for timing with the sphere model (depth, duration, Tmin), and
     offers "Open in Models" for a full solution.
  7. "Send the mid-time" to O−C / the Exoplanets window's timing list; the fit is stored in the session and exported
     in the reports (PHO-27).
- **Accept:**
  1. Synthetic transit (known truth, white noise + airmass trend): every parameter within 1.5σ in 95 of 100 noise
     realisations; BIC prefers the true detrending set.
  2. Qatar-1 whole night: Tc within 1σ of the value in the literature for that epoch and within 30 s of the
     AstroImageJ fit of the same light curve with the same priors (reference numbers stored); depth and duration
     within 1σ of the Exoplanet Archive values.
  3. Fit of 265 points with 3 detrend terms: < 0.3 s least squares; MCMC 20 000 steps < 20 s (native kernel).
  4. QTest: fill from the archive → fit → send to O−C, in four languages.
- **Files:** `photometry/transitfit.py`, step `photometry.transit_fit`, UI panel, tests, guide 06.
- **Depends on:** EXO-1, EXO-3, EXO-5 (engines), PHO-W.

### PHO-27. Reports the community accepts  (P1)
**open**
- **Reference:** AAVSO Extended File Format (exists); AAVSO Exoplanet Database (WebObs users guide,
  app.aavso.org/exosite/doc: header `#TYPE=EXOPLANET`, `#OBSCODE`, `#SOFTWARE`, `#DELIM`, `#DATE_TYPE=BJD_TDB`,
  `#OBSTYPE`, `#STAR_NAME`, `#EXOPLANET_NAME`, `#BINNING`, `#EXPOSURE_TIME`, `#FILTER`, `#DETREND_PARAMETERS`,
  `#MEASUREMENT_TYPE`, priors and results blocks; data: date, measurement, error, up to four detrend columns — read
  the current guide and write the exact list under this step); ExoClock (text file BJD_TDB / flux / error and the
  observation form's fields); ETD / VarAstro (exists); TFOP SG1 submission to ExoFOP (file naming
  `TIC<id>-<pp>_<yyyymmdd>_<observatory>_<filter>_…`, the required set: light-curve plot, field image with
  apertures, measurement table, plot configuration, notes text, NEB files); AstroImageJ "Save all".
- **Ours now:** `export.aavso_extended`, `export.etd_text`, `models/transit_report.py` (ETD, ExoClock, summary).
- **Read first:** each format's current specification (linked above), one real accepted file of each kind (public
  on the sites), AstroImageJ's writers for the AAVSO exoplanet and TFOP outputs.
- **Build:**
  1. `photometry/reports/` with one module per format and a common `ReportContext` (light curve, fit, profiles of
     site / equipment / observer, target identifiers); each writer has a validator that re-reads its own file against
     the format rules.
  2. AAVSO Exoplanet Database file (header + data with the chosen detrend columns, `MEASUREMENT_TYPE` flux or
     magnitude); ExoClock files plus a text of the form's values to paste; AAVSO Extended with `TRANS=YES` when
     PHO-35 is used; ETD / VarAstro; BAA / BAV style tables of minima go to OC.
  3. TFOP package: named by the SG1 convention; contains light-curve plot (PNG and PDF) with the fit and the
     predicted ingress / egress, the field image with apertures and a 2.5′ circle, the seeing-profile plot, the
     measurements table, the NEB folder (PHO-23), the notes text filled from the fit (aperture radius in px and
     arcsec, pixel scale, FWHM, detrending used, depth, Tc, duration, whether the event was on target, on time).
  4. "Observation summary" one-page PDF for any night (target, site, equipment, conditions, light curve, comparison
     stars table with magnitudes and sources, timing result) through `ui/plot/publish`.
  5. "Save all" (as AstroImageJ): light curve (ECSV, PHO-48), measurements table, star list, session, plots, field
     image, methods text (ARC-11) into one folder.
  6. Report stage: a card per report with what it is for, what is still missing for it ("AAVSO needs your observer
     code" → opens the profile), and a preview of the file.
- **Accept:** each file passes its validator and matches a stored accepted example in structure (keys, order,
  delimiters); the AAVSO exoplanet file made from the Qatar-1 night is accepted by a format check built from the
  users guide; the TFOP package for the public TFOP night has the same file set and names as the public one.
- **Files:** `photometry/reports/*.py`, `models/transit_report.py` (moved in), UI report panel, tests, guide 06.
- **Depends on:** PHO-26 (fit values), PHO-23, ARC-16 (profiles).

### PHO-28. All-sky photometry: the night's solution from standard stars  (P2)
**open**
- **Reference:** IRAF `photcal` (`mknobsfile`, `mkconfig`, `fitparams`, `evalfit`, `invertfit`; Davis & Gigoux
  1993): transformation equations per filter fitted to standards observed over a range of airmass, e.g.
  `m_V = V + v1 + v2 X + v3 (B−V) + v4 X (B−V)`; Harris, Fitzgerald & Reed 1981 (the classical method); Landolt and
  Stetson standards; AAVSO transformation campaign conventions (`Tv_bv`, `Tbv`, …) — ours has those in
  `coefficients.py`.
- **Ours now:** `coefficients.extinction` (k from comparison stars of one field), `transformation` (two filters, one
  field), dialog `coefficients_dialog.py`.
- **Build:** `photometry/allsky.py`: instrumental magnitudes of standards from many frames (several fields,
  airmasses, filters) with aperture correction to a large radius (growth curve, from the several-apertures data of done item 10); a general
  least-squares fit of zero point, first-order extinction, colour term and optionally second-order extinction and a
  time drift of the zero point per filter, with sigma clipping and the covariance; residual plots against airmass,
  colour, time and position; `apply()` to programme stars (iterating on the colour) giving standard magnitudes with
  errors including the fit's; a "night quality" verdict (photometric or not: scatter of the standards' residuals and
  the zero-point drift). Window: a tool reachable from Tools → "All-sky calibration…" with stages Standards (frames
  and automatic identification of Landolt / Stetson stars through PHO-25), Fit, Apply.
- **Accept:** synthetic night with known k′ = 0.25, colour term 0.08, zero point 21.3: recovered within 1σ; the
  SA 98 + second standard field night (data to add) gives residual scatter < 0.02 mag and coefficients equal to
  IRAF `fitparams` on the same instrumental magnitudes within 1σ (reference stored).
- **Files:** `photometry/allsky.py`, `coefficients.py`, UI tool, tests, guide 06.

### PHO-29. Difference-image photometry  (P2)
**open**
- **Why:** very crowded fields (Galactic plane, clusters, novae, microlensing) where even PSF fitting fails.
- **Reference:** Alard & Lupton 1998 (ApJ 503, 325) and Alard 2000 (kernel as Gaussians × polynomials, spatially
  varying); Bramich 2008 (MNRAS 386, L77: discrete pixel kernel, "delta basis"), Bramich et al. 2013 (extended);
  Becker's HOTPANTS and Albrow's pyDIA as descriptions of practice (read, not copied).
- **Build:** `photometry/dia.py`: reference image (best-seeing 5–10 frames aligned and combined, CAL stack);
  per frame: registration to the reference (sub-pixel, flux-conserving), kernel solution on stamps around bright
  isolated stars (delta-basis kernel of size from the seeing ratio, regularised; differential background as a
  low-order polynomial), convolution of the reference to the frame (GPU kernel through `compute`, CPU twin),
  difference image; photometry on the difference image at the fixed positions with the reference PSF convolved by
  the kernel (optimal weighting), flux scale from the kernel sum; total flux = reference flux (PSF photometry on the
  reference) + difference flux; errors from the pixel variances. Measure-stage method "Difference imaging"; result
  tab shows the reference, the current difference image and the kernel.
- **Accept:** synthetic crowded field (5000 stars, variable seeing, a star varying by 5 %): the variation is
  recovered within the error and constant stars are flat to the photon limit × 1.3; on the real crowded set the
  scatter of constant stars is lower than with PSF photometry for stars with a neighbour within 2 FWHM (asserted);
  GPU and CPU difference images equal within 1e-5 relative; 100 frames of 2k × 2k: < 2 min CPU.
- **Files:** `photometry/dia.py`, `compute/convolve.py`, steps, UI, tests, guide.
- **Depends on:** PHO-18.

### PHO-30. Whole-field time series and the search for variables  (P2)
**open**
- **Reference:** Muniwin "find variables" (magnitude–deviation diagram); Honeycutt 1992 full inhomogeneous ensemble
  solution; Welch & Stetson 1993 / Stetson 1996 indices J, K, L; von Neumann ratio; Sokolovsky et al. 2017 (MNRAS
  464, 274: comparison of 18 variability indices; best: IQR, 1/η, MAD, weighted σ); VaST software (description).
- **Ours now:** `fieldstars.field_photometry`, `variability` (one index), page `varfind_page.py`.
- **Build:** all detected or catalogue stars measured on all frames (aperture or PSF); the Honeycutt ensemble
  solved for frame zero points and star means iteratively with weights and with variables excluded; indices: weighted
  σ, MAD, IQR, 1/η (von Neumann), Stetson J and K, reduced χ², each against the magnitude with a running median and
  robust spread — a star is a candidate when it is beyond n σ in at least two indices; a quick period search of each
  candidate (PER engines, GPU batch) with the best period and its false-alarm probability; cross-match with VSX,
  GCVS and Gaia variables (known / new); result: a table (TableView) linked to the image and to a small-multiples
  page of light curves and folded curves; export of candidates (CSV, a VSX-submission helper sheet); "Open in
  Photometry as target" for any star.
- **Accept:** synthetic field with 2000 constant stars and 10 variables of amplitude 2–5 × their noise: ≥ 9 found,
  ≤ 5 false candidates; on the real crowded set the known VSX variables in the field brighter than the limit are
  recovered (list stored); 2000 stars × 300 frames < 3 min.
- **Files:** `photometry/fieldstars.py`, `photometry/varindex.py`, UI (Light curves window, Variable search job),
  tests.

### PHO-31. Removing systematics common to many stars  (P2)
**open**
- **Reference:** SysRem (Tamuz, Mazeh & Zucker 2005, MNRAS 356, 1466); TFA (Kovács, Bakos & Noyes 2005, MNRAS 356,
  557); cotrending basis vectors of Kepler / TESS (Smith et al. 2012); lightkurve `CBVCorrector`,
  `RegressionCorrector`, `PLDCorrector`.
- **Build:** `photometry/systematics.py`: `sysrem(mag, err, n_terms)` (iterative rank-one effects with errors),
  `tfa(target, templates, n)` with reconstruction mode for a known period, PCA basis from the field's stars with a
  BIC-chosen number of terms; applied to whole-field series (PHO-30) and offered in the Light curve stage as
  "Remove trends shared with the field stars" when ≥ 30 field stars are measured; the amplitude suppression of a
  signal is estimated by injection and shown ("a 1 % transit would be reduced to 0.93 %").
- **Accept:** synthetic field with an injected airmass-and-colour systematic: scatter of constant stars falls to the
  white-noise level within 10 %; an injected transit keeps ≥ 90 % of its depth with the default settings.
- **Files:** `photometry/systematics.py`, UI, tests.

### PHO-32. Space-mission pixel tools  (P2)
**open**
- **Reference:** lightkurve (MIT; may be read freely and its algorithms reimplemented or the ideas used):
  `TargetPixelFile.interact`, custom and threshold aperture masks, `estimate_background`, `PLDCorrector`, `flatten`
  (Savitzky–Golay), `remove_outliers`, `stitch`; `tpfplotter` (Gaia stars over the stamp, contamination); TESScut;
  SPOC flags and crowding metrics (CROWDSAP, FLFRCSAP); `eleanor`, TESS-SIP as descriptions.
- **Ours now:** `io/tpf.py` (frames written per cadence, `cube`), `aperture.measure_cube`, missions' light curves from
  MAST (`timeseries/archive.py`).
- **Build:** Images stage accepts a TIC / KIC / EPIC / name: lists the available pixel files and FFIs per sector
  (`services/mast`), downloads the pixel file or a TESScut cut-out of chosen size; Apertures stage in "pixel mask"
  mode: the stamp with Gaia stars drawn to scale by magnitude (contamination estimate from Gaia fluxes and the
  pixel response as a Gaussian of the mission's FWHM), mask editor (click pixels; "pipeline mask", "threshold n σ",
  "all pixels of the target's flux > x"); background from the faintest pixels' median per cadence (FFI cut-outs
  have no background removed); scattered-light flagging by the background's time derivative; detrending by PLD
  (first order, with PCA of the pixel basis) and by regression against centroids and background, both with the
  transit / eclipse windows masked; quality bitmask choice (default, hard, none); sectors stitched with per-sector
  normalisation; comparison with the pipeline SAP / PDCSAP in a plot; centroid shift test in and out of transit
  (in-transit minus out-of-transit centroid, with error) for false-positive vetting.
- **Accept:** for WASP-12 sector 20 and AI Dra sector 24: our mask-editor light curve with the pipeline mask equals
  SAP within 0.02 %; PLD lowers the 1-hour CDPP relative to SAP (asserted); the centroid test on a synthetic blend
  detects a 0.2 px shift at 5σ; a 15 × 15 stamp with 18 000 cadences: mask change → new light curve < 0.3 s.
- **Files:** `photometry/pixels.py`, `io/tpf.py`, `services/mast.py`, UI, tests, guide 06 and 07.
- **Notes from the sources (architect, 2026-11-10):** AstroImageJ 5 opens TESScut files, TESS postage-stamp sequences,
  and TICA and SPOC full-frame images directly; lightkurve's quality bitmasks are named `default`, `hard` and
  `hardest` (`lightkurve/utils.py`). Our reader must accept the same four kinds of files (TICA FFIs have their own
  header conventions and time system: read the TICA product description before writing the reader).

### PHO-33. Night diagnostics ("Checks" tab)  (P1)
**open**
- **Why:** users must see at a glance whether a dip is real or a cloud; AstroImageJ users plot airmass, sky, FWHM,
  X / Y by hand.
- **Build:** a results tab with small stacked `PlotView` panels on the light curve's time axis: total comparison
  counts (transparency), sky per pixel, FWHM, ellipticity, X and Y drift of the field, airmass, peak of the target
  relative to the linearity limit, number of comparison stars used, the comparison − check curve; automatic flags:
  cloud (ensemble counts down by more than `x` % from a running upper envelope), bad seeing, drift jump (meridian
  flip, guiding loss), near-saturation; each flag marks the frames in every plot and in the Frames table; "Leave out
  flagged frames" per flag kind (undoable); a one-line verdict in the Light curve stage ("3 frames behind cloud, 1
  with a satellite trail; 0 saturated").
- **Accept:** synthetic night with a cloud passing (ensemble −40 % for 6 frames), a focus drift and a flip: each is
  flagged on exactly its frames; the Qatar-1 night shows no cloud flag; rendering with 1000 frames < 150 ms.
- **Files:** `photometry/quality.py`, UI checks panel, tests.

### PHO-34. Errors that match the scatter; red noise  (P1)
**open**
- **Reference:** Pont, Zucker & Queloz 2006 (MNRAS 373, 231: red noise); Winn et al. 2008 (ApJ 683, 1076: the
  time-averaging β factor); Carter & Winn 2009 (wavelets); Young 1967 / Osborn et al. 2015 (MNRAS 452, 1707:
  scintillation with a site-dependent coefficient).
- **Build:** after every measurement: the ratio of the observed scatter (comparison − check, and the target's
  out-of-event residuals) to the predicted error; when above 1.2 a banner offers "Scale the errors by 1.37" (stored
  as a factor, never overwriting the formal errors; columns `rel_flux_err` and `rel_flux_err_scaled`); β from the
  RMS of binned residuals against bin size (plot "RMS vs bin size" with the white-noise line), reported in fits
  (PHO-26) and used to inflate parameter errors when the user ticks "account for red noise"; scintillation: Osborn's
  formula with the correction factor per site from the profile, added to the error of **every** aperture radius
  (fixes the gap of item 10); a noise budget per star (photon, sky, read, dark, scintillation, as a stacked bar) in
  the Inspector.
- **Accept:** synthetic white noise: ratio 1.00 ± 0.05, β = 1.0 ± 0.1; synthetic red noise of known amplitude: β
  within 15 % of the expected value; the scaled errors make reduced χ² of the Qatar-1 fit 1.0 ± 0.1.
- **Files:** `photometry/errors.py`, `aperture.scintillation`, UI, tests, guide 13.

### PHO-35. Transformed magnitudes on every frame  (P2)
**open**
- **Reference:** AAVSO Guide to CCD Photometry (transformation); AAVSO Extended format `TRANS=YES`; VPhot; our
  `coefficients.transformation`.
- **Build:** with coefficients from the profile (per filter set, dated) or from PHO-28: standard magnitude of the
  target per frame `V = v_inst + ZP_frame + T_v_bv × (B−V)_target`, the target's colour from the two-filter curve of
  the night interpolated in time (done item 11) or a typed colour; second-order extinction term optional; the AAVSO report
  marks `TRANS=YES` and notes the coefficients; error propagation includes coefficient errors.
- **Accept:** synthetic B / V night with colour terms 0.05 and 0.10: recovered standard magnitudes within 0.005 of
  truth, against 0.03 untransformed.
- **Files:** `photometry/transform.py`, `photometry/coefficients.py`, `photometry/export.py` (`TRANS=YES`), `tests/test_transform.py`

### PHO-36. Bad pixels, cosmic rays and trails inside an aperture are flagged  (P1)
**open**
- **Why:** AD-8. A hot pixel or a satellite trail in the aperture makes an outlier that today is found only by eye.
- **Build:** `aperture.measure` takes the frame's mask plane (CAL-13: bits for bad pixel, saturated, cosmic ray
  repaired, satellite trail, no data) and variance plane; a flagged pixel in the aperture sets a per-star, per-frame
  flag (`Flags_<star>` column with letters B, S, C, T, E for edge) and, for repaired pixels, the measurement is kept
  but marked; a flagged pixel in the sky ring is simply not used; the error uses the variance plane when present
  (the measured-σ formula stays the fall-back and the cross-check). Flags colour the points (interface roles) and
  feed "Leave out flagged points". Frames without planes behave as today.
- **Accept:** synthetic night with a hot pixel inside the target's aperture on drifted frames 10–14 and a trail
  across frame 20: exactly those points carry B and T; variance-plane errors equal the formula within 3 % on clean
  frames.
- **Depends on:** CAL-8, CAL-12, CAL-13.
- **Files:** `photometry/aperture.py`, `photometry/lightcurve.py`, `photometry/measurements.py` (`Flags_<star>`), `core/planes.py`, `tests/test_photometry_flags.py`

### PHO-37. Speed at scale  (P2)
**open**
- **Build:** benchmark cases in `tools/speed.py`: 1000 × 4k² frames, 10 stars (aperture); 300 × 4k², 2000 stars
  (PHO-30); pixel file 18 000 cadences. Native kernel `aperture_sums(data, xy, radii)` (exact circle–pixel overlap
  for many stars and radii in one pass, threaded) if the profile shows the sums dominate; a GPU twin only for the
  2000-star case. Reading stays the floor: measure and report the split (read, register, centre, sum, sky).
- **Accept:** budgets of `plans/architecture.md` met; results identical to the NumPy path within 1e-10 relative.
- **Files:** `tools/speed.py`, `native/src/aperture.rs`, `photometry/aperture.py`, `compute/aperture.py` (only for the many-star case)

### PHO-38. High-speed and video photometry, occultations  (P3)
**open**
- **Reference:** Tangra, PyOTE / PyMovie (IOTA), Limovie: SER / AVI / ADV / FITS-cube input, time stamps from GPS
  inserters, drop detection in a noisy light curve with a square-well model and confidence from Monte Carlo.
- **Build:** readers for SER (documented header; UTC time stamps per frame) and FITS cubes with time keywords
  (`io/video.py`); the photometry runs on frame streams without writing a FITS per frame; an "Occultation" timing
  tool: square-well fit of disappearance and reappearance with errors by bootstrap, duration, magnitude drop;
  report in the IOTA text layout. AVI / ADV only if a permissively licensed decoder is already bundled (else listed
  as not supported, with the conversion advice).
- **Accept:** a synthetic 25 fps series with a 2.4 s occultation at S/N 3 per frame: D and R times within 0.05 s.
- **Files:** `io/video.py`, `photometry/occultation.py`, `photometry/reports/iota.py`, `tests/test_occultation.py`

### PHO-39. Extended objects: comets and surface photometry  (P3)
**open**
- **Reference:** A'Hearn et al. 1984 (Afρ); photutils `isophote` (ellipse fitting after Jedrzejewski 1987; IRAF
  `stsdas.ellipse`); surface brightness in mag arcsec⁻².
- **Build:** comet mode in moving-object photometry: apertures of fixed physical radius (km at the comet, from Δ),
  Afρ with the solar magnitude in the band, background from a far annulus; isophote fitting tool in Images →
  Analyse (profile of surface brightness, ellipticity, position angle against semi-major axis, with a model image
  and residual); sky brightness of a frame in mag arcsec⁻² from the zero point.
- **Accept:** a synthetic 1/ρ coma gives Afρ independent of the aperture within 2 %; a synthetic Sérsic galaxy's
  profile parameters within 3 %.
- **Files:** `photometry/comet.py`, `images/isophote.py`, `tests/test_extended.py`

### PHO-40. Polarimetry completed  (P3)
**open**
- **Ours now:** `photometry/polarimetry.py` (dual- and single-beam Stokes q, u, P, θ) and a step.
- **Build:** instrumental polarisation and zero angle from standard stars (polarised and unpolarised lists bundled
  with references); bias correction of P (Wardle & Kronberg 1974; Plaszczynski et al. 2014 MAS estimator); time
  series of q, u, P, θ; a q–u plot; error propagation checked by Monte Carlo.
- **Accept:** synthetic standards with 0.3 % instrumental polarisation and a 12° zero-angle offset: recovered within
  1σ; debiased P unbiased at P/σ = 2 within 10 %.
- **Files:** `photometry/polarimetry.py`, `resources/data/polarimetric_standards.ecsv` (with references), `tests/test_polarimetry.py`

### PHO-41. Validation against the owner's AstroImageJ table  (P1, waits for the owner)
**open — waiting for data**
- **Build:** when the owner sends a Measurements table of a night with its radii: measure the same frames with
  "radii as AstroImageJ" and the same stars; compare per frame `rel_flux_T1`, its error, `Source-Sky`, `Sky/Pixel`,
  `X(FITS)`, `Y(FITS)`, `BJD_TDB`; write the differences here; store a reduced table (public data only if the night
  can be made public, otherwise the comparison numbers alone) as a validation test.
- **Accept:** median |ours / AstroImageJ − 1| < 0.1 % per frame; errors within 10 %; BJD within 1 s; any larger
  difference explained.
- **Files:** `tests/validation/test_aij_owner.py`, `tests/validation/data/` (reduced table only if public)

### PHO-42. Faint targets: measuring on running stacks  (P2)
**open**
- **Build:** "Combine frames before measuring": groups of N consecutive frames (or of T minutes) aligned on the
  stars and averaged with rejection (CAL stacking engine, in memory), measured as one frame with mid-time = the
  flux-weighted mean of the group's mid-times and exposure = the sum; moving-object variant aligned on the track.
- **Accept:** a synthetic target at S/N 3 per frame gives a curve at S/N ≈ 3 √N (within 10 %) with unbiased times.
- **Files:** `photometry/stacked.py`, `calibration/stacking.py` (in-memory combine), `tests/test_photometry_stacked.py`

### PHO-43. Advice for the next night  (P2)
**open**
- **Why:** beyond every reference program: the program has the numbers to say how to observe better.
- **Build:** after a measurement, a "For next time" card: exposure time that would bring the target's peak to 60 %
  of the linearity limit; whether to defocus (peak / total and the pixel-to-pixel term); the noise budget's largest
  term and what reduces it; comparison stars lost at the edge → the pointing offset that keeps them all; cadence
  against the event's ingress duration; flats' contribution if the stars drifted by more than n px.
- **Accept:** on a synthetic night that saturates late, the advice gives the exposure that would not have; texts in
  four languages, each with its reasoning in one line.
- **Files:** `photometry/advice.py`, `ui/photometry/panels/lightcurve.py` (card), `tests/test_advice.py`

### PHO-44. Centring algorithm choice  (P3)
**open**
- **Reference:** IRAF `centerpars.calgorithm` = centroid | gauss | ofilter | none with `cbox`, `cthreshold`,
  `minsnratio`, `cmaxiter`, `maxshift`; AstroImageJ Howell centroid.
- **Build:** `recenter(method = auto (today's) | moments | gauss | none)` exposed under More options with `box` and
  `max_move`; `Centring_Method` in the provenance.
- **Accept:** each method within 0.05 px on synthetic Gaussian stars at S/N 50; identical default results to today.
- **Files:** `photometry/aperture.py` (`recenter`), `photometry/options.py`, `tests/test_centring.py`

### PHO-45. Sky ring: catalogue star mask and IRAF's histogram centroid  (P2)
**open**
- **Build:** stars known from the catalogue (Gaia to G + 7 of the target) are masked in every sky ring by position
  (radius 1.5 FWHM scaled with brightness) before any statistic — better than rejection alone because faint wings
  are removed too; `sky_method = "centroid"` (IRAF's `salgorithm = centroid`: histogram of the ring within ± 3σ in bins of 0.1σ,
  centroid of the histogram, iterated with rejection and `rgrow`); the rejected-pixel count per star and frame in the
  measurements table.
- **Accept:** synthetic ring with a V + 5 star inside: the masked sky is unbiased within 0.1σ where the median is
  biased by > 0.5σ (asserted); "centroid" equals IRAF `phot salgorithm=centroid` on the HAT-P-32 frames within
  0.2 ADU (reference stored).
- **Files:** `photometry/aperture.py` (`sky_estimate`, ring mask), `photometry/skymask.py`, `tests/test_sky_mask.py`, `tests/validation/test_iraf_phot.py`
- **Notes from the sources (architect, 2026-11-10):** `noao/digiphot/apphot/fitskypars.par` of the iraf-community
  tree has `salgorithm = "mode"`, `smaxiter 10`, `snreject 50`, `sloreject = shireject = 3`, `khist 3`, `binsize 0.1`,
  `rgrow 0`; `centerpars.par`: `calgorithm centroid`, `cbox 5`, `cthreshold 0`, `minsnratio 1`, `cmaxiter 10`, `maxshift
  1`. The validation of item 1 ran IRAF with `salgorithm=median`; when this step adds "centroid", also add a reference
  run with IRAF's own default (`mode`) so that all three are covered. Check the par file of the installed version
  (`apt` IRAF 2.17) before writing the test: defaults differ between releases.

### PHO-46. Detrending of every plotted series  (P3)
**open**
- **Build:** multi-plot rows get their own detrend choice (none / the target's set / own set), as AstroImageJ's
  Y-data rows, for check stars and further targets.
- **Accept:** a check star's curve detrended with airmass alone while the target uses airmass + FWHM, saved in and
  restored from the template.
- **Files:** `photometry/multiplot.py`, `ui/photometry/panels/multiplot.py`, `tests/test_multiplot.py`

### PHO-48. The light-curve file: nothing lost on the way out and back  (P1)
**open**
- **Why:** the exported CSV keeps relative errors only, so a night read back shares its error between target and
  comparison stars (item 12); other windows and other programs need the full table with units and provenance.
- **Build:** `photometry/lcfile.py`: ECSV (`.lc.ecsv`) with every column of the measurements table plus the derived
  series (rel_flux, detrended, model), units and time standard in the column metadata, the star list, the options,
  the profiles used and the provenance record (ARC-11) in the header; `read()` restores a light-curve dict
  identical to the measured one (round-trip test of every key); the old CSV stays as "simple CSV" export; every
  consumer (join nights, Light curves, Models, Exoplanets, O−C minimum timing, recipes) reads the new file; the
  format has a version and a migration reader for the old CSV.
- **Accept:** measure → save → read → join nights gives results identical to joining the in-memory curves; Astropy's
  `Table.read` opens the file with units; lightkurve can read it through its generic reader (time, flux, flux_err
  columns present under those names as aliases).
- **Files:** `photometry/lcfile.py`, `photometry/nights.py`, readers in other areas, tests.

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

Items 0–16 before 2026-11-09 (agent2): see the table "What we already have" and
`docs/history/photometry-plan-2026-11-09.md` for the notes and commits of each.
