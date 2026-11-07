# Photometry and light curves: plan

## Most important rules (this block heads every plan file)

> Came straight to an area file? Stop and read `PLAN.md` first, all of it. Then come back.

1. **Never stop.** Work until the work is finished or your quota ends, unless the owner interrupts.
   - Set yourself reminders so that a pause, a sleep or a lost session does not end the work: a scheduled wake-up
     every 30–60 minutes, or what suits the work. You choose the interval.
2. **Claim every step.**
   - Before starting: write `**agentN claimed (date) — do not touch**` and push.
   - When finished: push the work, then write `**agentN done (date, commit)**`.
   - Claim the next step before starting it (PLAN.md R2).
3. **Research first.** The scientific basis, the reference programs' source code (learn, never copy), the
   internet, real data.
4. **Test as a real user, not only in code.**
   - Install the program on your machine, open it and use it as someone who knows less than you would.
   - Look for:
     - a button that works but is in the wrong place, or has no explanation;
     - a control that should not be there;
     - something missing;
     - a step a newcomer would not find.
   - Every problem found becomes a task (rule 5).
5. **Add the tasks you find.** Research, the internet, trials and tests all show work to do. Add it to the area
   file at the place its urgency deserves, not necessarily at the end. An area is finished only when it is
   excellent.
6. **Engine code may be changed** where it is wrong or missing, old core files included. New features may be
   added. **Never delete what looks unnecessary:** note it under "To ask the owner" and delete it only after the
   owner agrees.
7. **Time, memory, GPU.**
   - Measure the time and memory of what you build.
   - Never make the program slower to save memory.
   - Where the work suits a GPU, write a GPU path with a CPU fallback (the `compute` module: auto / cpu / gpu).
8. **Everything goes to `main`.** No branches and no pull requests for the owner to deal with.
9. **The workflow comes first.** No wall of buttons. The right default. Rarely used options folded.

Written 2026-11-07 at the owner's request: scan AstroImageJ, Siril, MaxIm DL, IRAF and the
others, and write down everything that has to be done. **Nothing here is started without the owner's word.**

The rules that matter most here:

- **Before each item, read how the reference programs do it in their source.** The table "How they do it in their
  code" below is the start; read the files again for the detail of the item and add what you learn under the item.
  The sources are AstroImageJ `astroj/Photometer.java`, `Centroid.java`, `Astronomy/MultiAperture_.java`,
  `MultiPlot_.java`, `Seeing_Profile.java`, `FitOptimization.java`; Siril `src/algos/photometry.c`; IRAF
  `noao/digiphot/apphot` and `daophot`; C-Munipack.
- **Learn, never copy.** They are GPL (PLAN.md R1).
- **Check on real data**, against a reference made with the same settings:
  - IRAF `phot` can be installed here (`apt-get install iraf iraf-noao`);
  - AstroImageJ tables come from the owner.
  - Public nights: Qatar-1 from the LCO archive, TESS cut-outs, the owner's NY Vir night (scratchpad only, never
    committed).
- **The workflow first.** The owner's first real night (NY Vir) failed on a page full of buttons. A new feature
  goes into a step or a panel where it is needed, folded when rarely used, with the right default.
- **Never a silent wrong result.** A star not found leaves the frame out, and the frame is named with the reason.
- **Claim each item before starting it, and mark it done after the push** (PLAN.md R2). Enter every feature the
  user sees in `plans/interface.md`.

## How to read an item

Each item says: what the reference programs do, what ours does now, what to build, and how to check it is right
(acceptance). Items in P1 decide whether the owner can trust a light curve; P2 makes the tool complete for eclipsing
binary and variable-star work; P3 is workflow comfort.

## Sources

- AstroImageJ: Collins et al. 2017, AJ 153, 77 ([arXiv:1701.04817](https://arxiv.org/abs/1701.04817)), with
  appendix A (settings) and B (noise model).
- Siril: [light curves](https://siril.readthedocs.io/en/latest/photometry/lightcurves.html),
  [quick photometry](https://siril.readthedocs.io/en/stable/photometry/quickphotometry.html).
- MaxIm DL: [photometry](https://cdn.diffractionlimited.com/help/maximdl/Photometry.htm),
  [photometry calculations](https://cdn.diffractionlimited.com/help/maximdl/Photometry_Calculations.htm).
- C-Munipack / Muniwin: [project](https://sourceforge.net/projects/c-munipack/),
  [manual 1.1](https://www.as.up.krakow.pl/rzeczy/cmpack-1.1-doc-en.pdf).
- IRAF apphot / daophot / photcal: the `phot` task with `centerpars`, `fitskypars`, `photpars`, `datapars`;
  `mkapfile`; `fitparams` / `invertfit` (Davis 1987, Massey & Davis 1992).
- Honeycutt 1992, PASP 104, 435 (inhomogeneous ensemble photometry).
- Licences: only ideas and published methods are taken. No code is copied from GPL programs (AstroImageJ, Siril,
  C-Munipack), and nothing from MKCLASS.

## How they do it in their code (read 2026-11-07)

Sources read, not copied (AstroImageJ and Siril are GPL; their code must not be pasted into ours): AstroImageJ
`astroj/Photometer.java`, `astroj/Centroid.java`, `Astronomy/MultiAperture_.java`, `Astronomy/Seeing_Profile.java`,
`Astronomy/FitOptimization.java`, `Astronomy/MultiPlot_.java`, `multiplot/MeridianFlip.java`
(github.com/AstroImageJ/astroimagej); Siril `src/algos/photometry.c`, `robustmean` in
`src/algos/statistics_float.c` (gitlab.com/free-astro/siril); IRAF `noao/digiphot/apphot/phot/apmeasure.x`,
`apcomags.x`, `fitsky/apmode.x` (github.com/iraf-community/iraf). MaxIm DL is closed source: only its manual.
C-Munipack: only its manual (the code is on SourceForge SVN, not read).

| Step | AstroImageJ | Siril | IRAF apphot | Ours now |
| --- | --- | --- | --- | --- |
| Pixels in the aperture | exact area of each pixel inside the circle (polygon intersection) | weight r_ap − r + 0.5, cut to 0–1 (a linear edge) | weight r_ap − r, cut to 0–1; several apertures in one pass | exact area (photutils) |
| Sky value | mean of the annulus; "remove stars": iterate up to 100 times, keep pixels within mean ± 2σ, stop when the mean changes < 1e-4; optional plane fitted to the kept pixels; the rejected-pixel mask is kept for the next frame | Hampel M-estimator robust mean (Newton iterations from median and MAD/0.6745), pixels outside [minval, maxval] dropped | `salgorithm`: mode = 3 median − 2 mean with iterative low / high sigma clipping (also median, centroid of the histogram, …) | sigma-clipped (3σ, 10 iterations) median |
| Error of the flux | √(F·g + N_ap(1 + N_ap/N_sky)(sky·g + dark + RON² + 0.289²·g²)) / g — the sky noise is modelled from the sky level, read noise and dark current (Merline & Howell 1995) | area_sq·σ²_sky + F/gain + area²·σ²_sky/N_sky (σ_sky measured) | area·σ² + F/epadu + area²·σ²/N_sky (σ measured) — the same as Siril | F/gain + N_ap(1 + N_ap/N_sky)·σ² (σ measured) — the same as IRAF |
| Centre | iterative moments in a circle (Howell's marginal-sum method by default; up to 100 iterations, stop when the move < 0.01 px), the sky taken off first (or a plane); can be turned off per aperture | PSF fit of each star on each frame (Gaussian or Moffat) | `calgorithm`: centroid / gauss / ofilter / none | 1-D Gaussians on the marginal sums |
| Radii from the star | radial profile in 1-px bins, normalised by the peak; FWHM where it crosses 0.5; r_ap where it falls below 1 % (`autoModeFluxCutOff` 0.010), r_in = 2 r_ap, r_out = 4 r_ap; fallback 1.7 / 3.4 / 6.8 FWHM | r_ap = factor × FWHM / 2; r_in, r_out = 4.2 and 6.3 FWHM ("autoring") | fixed values typed in (the curve of growth is a separate task) | profile, then a scan of 1–3 FWHM for the steadiest curve; r_in ≥ 4.5 FWHM |
| Ensemble | T: F_T / Σ comps; each C_k: F_C / Σ the other comps; errors added in quadrature | target − (−2.5 log Σ flux / n); a frame is dropped unless every reference is valid | not part of phot (done afterwards) | the same as AstroImageJ; a frame is dropped when a comparison star is lost (as Siril) |
| Saturation | peak per aperture compared with a saturation and a linearity level; the cell is coloured in the measurements table | any aperture pixel outside [minval, maxval] makes the star invalid on that frame | `datamax`: the measurement is flagged | peak measured, a level read from the header; not shown per point |
| Choosing comparison stars | "Optimise": exhaustive search, or toggle one star at a time, for the lowest RMS of the fit | from a catalogue by ΔV, Δ(B−V), catalogue error, not variable | — | from Gaia by rules; scatter of each against the others |
| Detrending | linear terms in the χ² of the fit; BIC = χ² + k ln n; exhaustive search of covariate sets for the lowest BIC (threshold ΔBIC); meridian flip as a step from a time or a column | — | — | linear least squares in chosen covariates, no BIC |

Three things this changes in the list below:
- Our error formula is IRAF's and Siril's; AstroImageJ differs because it models the sky noise from the camera
  numbers. Item 2 is therefore "add the camera model as an option", not "fix a wrong formula".
- AstroImageJ's automatic radii are much larger than ours (to 1 % of the peak, sky from 2× to 4× that). Our scan
  picks by scatter; the validation (item 1) must use the same radii in both programs, or the comparison means nothing.
- AstroImageJ keeps the background-star mask from one frame to the next; this is cheap and worth copying as an idea
  in item 3.

## What we already have (do not redo)

| Area | Ours now | Like |
| --- | --- | --- |
| Registration | Every frame against the first one (phase correlation), star-pattern match as fallback (rotation, flip) | AIJ / Muniwin matching |
| Per-frame checks | Star found with S/N ≥ 3, else the frame is listed as lost and why | — (ours is stricter) |
| Apertures | Exact partial-pixel circles; radii from the star profile, then a scan of 1–3 FWHM that keeps the steadiest light curve; optional radii scaled by each frame's FWHM | AIJ variable aperture, EXOTIC aperture grid |
| Sky | Sigma-clipped median in the annulus | Siril (deviant pixels out), MaxIm (median-mean) |
| Error | F/gain + sky scatter (Merline & Howell 1995); scintillation (Young) | IRAF phot, AIJ (partly) |
| Field | Built-in Gaia plate solve, VSX variables, OBJECT check, target from the files | AIJ (astrometry.net), Siril (plate solve) |
| Comparison stars | From Gaia: magnitude and colour, not variable, isolated, unsaturated; tick a star off and the curve follows; each star's scatter against the others | Siril findcompstars, AIJ comp checkboxes |
| Ensemble | Sum or scatter-weighted ensemble; check stars and extra targets | AIJ, Muniwin, MaxIm |
| Detrending | Linear in airmass, sky, x, y, FWHM, time | AIJ Multi-Plot detrend |
| Time | Mid-exposure, BJD_TDB from the target's coordinate, airmass | AIJ coordinate converter |
| Magnitudes | Catalogue magnitudes (APASS, Gaia → V R I), extinction k, transformation coefficients | IRAF photcal, VPhot |
| Outputs | CSV light curve, AAVSO extended format, minimum times (KvW) to O−C | Siril, Muniwin, AIJ |
| Other | PSF photometry (Gaussian, grouped), live photometry during the night, frame quality, variable-star search, polarimetry | daophot, AIJ real-time |

## To ask the owner
(nothing yet)

## P0 — the photometry window

The page is one column of four folding steps beside the image. Items 6 (measurements table), 7 (star lists), 8
(multi-plot) and 9 (detrending with BIC) will not fit in that column: AstroImageJ uses separate windows for them
(image with apertures, Multi-Aperture settings, Measurements table, Multi-Plot main, Multi-Plot Y-data, fit panel).

### 0. Photometry in a window of its own
**open** — needs the area window frame first (`plans/interface.md` I2); this item is the same as interface I5.
- **Build:** "Photometry" opens its own main window (it can also stay a page). Inside: the image in the middle; the
  steps on the left; at the bottom or right, tabs that can be pulled out as windows of their own — Measurements
  table, Plot (multi-plot), Stars (target, comparison, check, with their scatter), Detrend and fit. The program
  already has dockable panels (`MainWindow.dock_page`), so this reuses them; window layout is remembered.
- **Accept:** on a 1366 × 768 screen the image, the plot and the table are visible at once; every panel can be
  pulled out to a second monitor and comes back where it was next time.
- **Why first:** items 6–9 each need room; built into the present column they would make it longer and harder,
  which is the complaint.

## P1 — trust in the light curve

### 1. Same frames, same answer as AstroImageJ (validation)
**open**
- **Reference:** the owner compares against AIJ by eye; no number says we agree.
- **Ours:** checked only on synthetic frames and Qatar-1 scatter.
- **Build:** a validation script that measures one public night (Qatar-1 LCO and one eclipsing binary night) with
  fixed target, comparisons and radii, and compares per-frame rel_flux and its error with an AIJ Measurements table
  exported for the same settings. A reduced reference table (time, rel_flux, error; public data only) goes into
  `tests/validation`, so CI catches any drift.
- **Also build:** an "AstroImageJ radii" choice (aperture where the profile falls to 1 % of the peak, sky ring from 2×
  to 4× that; see the code table), so the same radii can be used in both programs.
- **Reference here:** IRAF `phot` installed in the container, with the same centres, radii and sky algorithm; the
  AstroImageJ table from the owner when one is sent.
- **Accept:** median |ours/reference − 1| < 0.1 % per frame and errors within 10 %; any larger difference explained
  in the test.

### 2. Noise model with the camera's numbers
**open**
- **Reference:** AIJ appendix B (source and sky Poisson noise, dark current, read noise, quantisation); IRAF
  `datapars` (epadu, readnoise).
- **Ours:** F/gain plus the scatter of the sky ring — the same formula as IRAF and Siril (see the code table); read
  noise and dark current enter only through that measured scatter, and S/N per star is not shown.
- **Build:** GAIN, RDNOISE / READNOIS, DARKCUR (or values typed once per camera) in the error, as AstroImageJ does
  (with its quantisation term 0.289² g²), as an option beside the measured sky scatter; S/N of every star on every
  frame in the table.
- **Accept:** on simulated frames with known gain, read noise and dark current, the predicted error matches the
  scatter of 1000 noise realisations within 5 %.

### 3. Sky estimate choices
**open**
- **Reference:** IRAF `fitskypars.salgorithm` (mode, median, centroid…); MaxIm median-mean; AIJ iterative 2σ
  rejection of stars in the annulus and an optional plane fit; Siril rejects deviant pixels.
- **Ours:** sigma-clipped median only; no plane fit; a bright star in the annulus is clipped but not masked.
- **Build:** a choice of median (now) / mode (3 median − 2 mean with iterative clipping, IRAF) / clipped mean with
  ±2σ iterations (AstroImageJ) / plane fit (gradients from the Moon or twilight). The rejected pixels of the first
  frame kept as a mask for the next frames (AstroImageJ's idea), so a star in the ring is masked even when faint.
- **Accept:** on a synthetic frame with a sky gradient and a star in the annulus, the plane fit gives the true sky
  within 0.1 σ, and the median is biased as expected.

### 4. Saturation and non-linearity flagged per point
**open**
- **Reference:** IRAF `datamax` flags each measurement; AIJ warns about saturated or non-linear stars.
- **Ours:** the peak pixel is measured and a saturation level is read from the header; this is not shown per point,
  and there is no linearity limit.
- **Build:** a linearity limit (header or typed in) next to saturation; each point whose target or comparison star
  passes it is marked in the plot and the table, with an option to leave such points out.
- **Accept:** a synthetic night where the target saturates in 5 frames marks exactly those 5.

### 5. Centring per star
**open**
- **Reference:** AIJ turns centring off per aperture (an un-centred aperture follows the mean shift of the others);
  IRAF `calgorithm` = none / centroid / gauss / ofilter.
- **Ours:** every star is always re-centred with a 1D Gaussian centroid. A faint target next to a bright star can be
  pulled to the bright star.
- **Build:** per star, "do not centre: follow the field" (the shift from the other stars), and a choice of centroid /
  Gaussian. The table shows how far each star was moved on each frame.
- **Accept:** a faint star 6 px from a bright one stays on the faint star when centring is off.

### 6. Measurements table (one row per frame, every number)
**open**
- **Reference:** the AIJ Measurements table: JD, BJD, airmass, and for every star x, y, source counts, sky per pixel,
  peak, FWHM, S/N, rel_flux and its error.
- **Ours:** the frame list and a CSV with time, rel_flux, comparison fluxes, airmass, FWHM, Δm.
- **Build:** a full table on the page (sortable, copyable) and the same columns in the CSV; columns named as AIJ
  names them where they mean the same, so that tables can be compared side by side.
- **Accept:** every column AIJ writes for one star has a column here or a stated reason why not.

### 7. Star list saved and used again on another night
**open**
- **Reference:** AIJ saves apertures (in RA/Dec when the frame has WCS); Siril saves a comparison-star CSV; MaxIm
  labels reference stars so a run can be repeated.
- **Ours:** the stars are marked again on every night.
- **Build:** save target, comparison and check stars and the radii in RA/Dec to a small file (and in the project);
  loading it on another night puts the stars back through that night's plate solution.
- **Accept:** a list saved on night 1 of a public data set lands within 1 px of the same stars on night 2.

### 8. Multi-plot
**open**
- **Reference:** AIJ Multi-Plot: many series on a shared time axis (target, comparison stars, check star, airmass,
  sky, FWHM, x / y), normalisation region, binning, residuals, shift-click to drop or restore a point, "cycle the
  comparison stars less one".
- **Ours:** the light curve, per-star plots, a hand-made frame exclusion list, and each comparison star's scatter.
- **Build:** one plot with selectable series stacked with offsets; binning by N points or by minutes; a normalisation
  range; click a point to drop it or bring it back (undoable); "leave each comparison star out in turn" with the
  scatter of every variant.
- **Accept:** each AIJ plot used in the owner's NY Vir check can be made here.

### 9. Choosing the detrending with numbers
**open**
- **Reference:** AIJ shows χ², reduced χ² and BIC; a parameter is kept when BIC drops by more than 2; a meridian-flip
  term removes the jump at the flip.
- **Ours:** detrending against chosen covariates, with no BIC and no meridian-flip term.
- **Build:** BIC and ΔBIC for each covariate set (also out-of-eclipse only); a step term at the meridian flip (time
  from the header pier side or typed in).
- **Accept:** on a synthetic curve with an airmass trend and a flip jump, the true model has the lowest BIC.

## P2 — complete for eclipsing binaries and variable stars

### 10. Several apertures at once and aperture correction
**open**
- **Reference:** IRAF `phot` measures a list of apertures in one pass; `mkapfile` builds a curve of growth and the
  aperture correction.
- **Ours:** the scan tries several radii but keeps one; there is no aperture correction.
- **Build:** keep the curves for every scanned radius (pick one later without measuring again); a curve of growth
  and aperture correction for catalogue magnitudes.
- **Accept:** switching radius after the measurement gives the same curve as measuring with that radius.

### 11. Several filters in one night
**open**
- **Reference:** IRAF photcal transformation equations; common practice in B and V monitoring.
- **Ours:** the images are grouped by filter, but each filter is measured on its own; the transformation exists only
  as separate steps.
- **Build:** one run over a mixed B / V / R sequence giving a curve per filter, the colour-index curve (B−V against
  time), and transformed magnitudes when coefficients exist.
- **Accept:** a synthetic two-filter night gives the injected colour change.

### 12. Several nights together
**open**
- **Reference:** Muniwin and AIJ work per night; observers join the nights afterwards.
- **Ours:** one night at a time (survey curves can be joined, nightly ones cannot).
- **Build:** join nights measured with the same star list; offsets per night from the common comparison stars; the
  minima of every night go to O−C at once.
- **Accept:** two nights of one star with a 0.05 mag offset injected are joined without the step.

### 13. Frames where a comparison star is missing
**open**
- **Reference:** Honeycutt 1992 inhomogeneous ensemble photometry (each frame uses the stars it has); Muniwin's
  artificial comparison star.
- **Ours:** a frame without one comparison star is left out of the light curve.
- **Build:** an ensemble zero point per frame from the stars that frame does have (Honeycutt), with the frame marked.
- **Accept:** a night where one comparison star leaves the field half-way keeps every frame, with no jump.

### 14. Time systems
**open**
- **Reference:** AIJ writes HJD_UTC and BJD_TDB; much eclipsing-binary O−C literature is in HJD.
- **Ours:** BJD_TDB (or JD_UTC without coordinates).
- **Build:** HJD_UTC as an extra column; the header time read as start, middle or end (choice); a shutter-delay
  correction per camera.
- **Accept:** HJD matches astropy's light-travel-time computation within 1 s for a test star.

### 15. Export formats
**open**
- **Reference:** Siril writes ETD (Exoplanet Transit Database) format and AAVSO extended; AIJ writes its
  measurements table and MPC magnitudes.
- **Ours:** CSV and AAVSO extended.
- **Build:** ETD format; the AIJ-style measurements table (item 6); a light-curve file the Models page reads
  directly.
- **Accept:** the ETD file is accepted by the ETD upload check (or matches its published column layout).

### 16. Eclipse and transit fit on the light-curve page
**open**
- **Reference:** AIJ fits a transit model with the detrending in the same χ² and reports BIC.
- **Ours:** minimum timing (KvW and others) on the Photometry page; transit and eclipsing-binary models live on the
  Models page.
- **Build:** a fit of the eclipse or transit with the detrending together, run from the light curve without changing
  pages; the result's time of minimum goes to O−C.
- **Accept:** a synthetic transit with an airmass trend: depth and mid-time recovered within 1σ.

### 17. Comparison-star criteria the user can set
**open**
- **Reference:** Siril findcompstars: ΔV (default 3), Δ(B−V) (default 0.5), largest catalogue error (0.03 mag),
  catalogue APASS or NOMAD, centred circle or whole image, variable catalogues GCVS / VSX / Gaia.
- **Ours:** fixed |ΔG| ≤ 2.5 and colour within 0.5 (a preference), Gaia flag and VSX, no catalogue-error limit.
- **Build:** these criteria in a folded "Comparison-star rules" section; GCVS and a catalogue-error limit added;
  why each nearby star was rejected shown on request.
- **Accept:** for the NY Vir field, the list and the reasons agree with Siril's rules applied by hand.

### 18. Crowded fields
**open**
- **Reference:** DAOPHOT allstar (neighbours fitted and subtracted); Siril PSF with Gaussian or Moffat.
- **Ours:** grouped Gaussian PSF fits.
- **Build:** a Moffat PSF; neighbours subtracted before aperture photometry of the target.
- **Accept:** a blended pair 1.5 FWHM apart gives each star's flux within 1 %.

## P3 — workflow

### 19. Real-time photometry at the telescope
**open**
- **Reference:** AIJ real-time mode (new files calibrated and measured as they arrive).
- **Ours:** live photometry exists.
- **Build:** check that it now uses the same per-frame checks, sky options and star list as the night run (items
  2–7); show the lost frames live.
- **Accept:** a night replayed file by file gives the same curve as the batch run.

### 20. The same run without the window
**open**
- **Reference:** Siril scripts, IRAF CL scripts.
- **Ours:** engine steps exist but there is no saved "photometry recipe".
- **Build:** save the page's settings and star list as a recipe; run it from the command line on a folder.
- **Accept:** GUI run and command-line run give identical tables.

### 21. Photometry of moving objects
**open**
- **Reference:** MaxIm tags first and last frame and tracks an asteroid.
- **Ours:** astrometry of moving objects only.
- **Build:** a light curve of a moving object (aperture follows the track, comparison stars fixed).
- **Accept:** a synthetic moving star of constant brightness gives a flat curve.

## Order proposed

New items found by research, trials or tests are inserted where their urgency puts them (numbers may then be
given letters, e.g. 3a); this order is updated with them.


0 (after interface I2) → 1 → 6 → 7 → 2 → 3 → 4 → 5 → 8 → 9, then P2 in the order the owner's work needs (13, 14 and 16 first for eclipsing
binaries). Item 1 comes first: every later change is then checked against AstroImageJ automatically.

## Done

(none yet)
