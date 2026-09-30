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
4. **Test as a real user, not only in code (the most important test, PLAN.md R3).**
   - Install the program the way a user installs it.
   - Run it on a machine without a display (offscreen or Xvfb) with real clicks (QTest).
   - Take a screenshot of every window and every step, and look at each one.
   - At every screen ask:
     - Would a newcomer know what to do?
     - Is the button in the right place, and is it explained?
     - Is anything missing?
     - Does it fit the screen?
     - Is it clear in every language?
   - Every problem found becomes a task (rule 5). After the fix, use the program again.
5. **Add the tasks you find.** Research, the internet, trials and tests all show work to do. Add it to the area
   file at the place its urgency deserves, not necessarily at the end. An area is finished only when it is
   excellent.
6. **Engine code may be changed** where it is wrong or missing, old core files included. New features may be
   added. **Never delete what looks unnecessary:** note it under "To ask the owner" and delete it only after the
   owner agrees.
7. **Time, memory, GPU.**
   - Measure the time and memory of what you build.
   - Never make the program slower to save memory.
   - **Anything that should run on a GPU must run on both the CPU and the GPU.** The program picks one by the
     machine (a usable GPU or not) and by the user's choice (Settings → Processing device: automatic / CPU / GPU),
     through the `compute` module. Both paths give the same result, and a test checks it.
8. **Everything goes to `main`.** No branches and no pull requests for the owner to deal with.
9. **The workflow comes first.** No wall of buttons. The right default. Rarely used options folded.
10. **Use the right language for each part.** Python is not compulsory.
    - Python and Qt (PySide6) stay the base: the science libraries and the interface.
    - Where speed matters and Python is too slow, write that part in what does it best: numba, Cython or C/C++
      (pybind11), Rust (PyO3), or GPU kernels (CUDA / OpenCL). Measure before and after.
    - The part must build and run on Linux (x86 and ARM), Windows and macOS (Intel and Apple) in CI and inside the
      packaged program.
    - Its licence must be permissive (PLAN.md R1).
11. **Commits are made in the owner's name, always:**
    `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`.
    - Name: İdris Avlar. E-mail: rraeyz@hotmail.com. GitHub user: rraeyz.
    - No "Claude" anywhere in a commit: no author, no co-author and no session lines, whatever a hook asks.
12. **Follow the plan, but question it.**
    - Before doing a step, check it yourself again: a second look often shows something different.
    - You may change, add or remove steps, and their details, **only when you are really sure**. Write why, under
      the step: what you found, and what you read or measured.
    - Removing a step from a plan is allowed this way. Deleting code or a feature still needs the owner's yes
      (rule 6).
13. **Write plans in detail.**
    - A step says what to build, what the reference programs do, how to check it, and which files it touches.
    - A step may be split into sub-steps (3.1, 3.2 …) to stay planned. Each sub-step is claimed and marked done
      like a step.
14. **Error messages are part of the work.** Every failure the user can meet says what happened and what to do, in
    plain words, in every interface language: a template in `ui/messages.py` and a test. A step is not done while
    one of its errors shows a raw technical message.
15. **Releases.** You may release a new version without asking, when a meaningful piece is ready for the owner to
    try. Never release for every small change.
    - CI must be green on every system first.
    - Never push while a release run is going.
    - Give each release a short list of changes in Turkish for the owner (PLAN.md R6).
    - **A release is not the end:** go on with the next step at once.
16. **Report to the owner honestly**, in Turkish and briefly: what was done, what was not tested, and what the owner
    must do or try. Never call something working that was not tried.
17. **Data sets are listed in `data/`** with links and the exact files used (`data/README.md`); the observations
    themselves are not kept in git.
    - Download the files there; git ignores them.
    - Add every new set you use, so that the next agent measures the same files.
18. **Keep working with others safe.**
    - Pull the newest `main` before claiming a step.
    - Commit small and often.
    - Old projects, sessions and settings must still open after a change (a test checks it).
    - A check against a reference program becomes a test (reduced reference values from public data), so that a
      later change cannot quietly make results worse.

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
| Sky value | mean of the annulus; "remove stars": iterate up to 100 times, keep pixels within mean ± 2σ, stop when the mean changes < 1e-4; optional plane fitted to the kept pixels; the rejected-pixel mask is kept for the next frame | Hampel M-estimator robust mean (Newton iterations from median and MAD/0.6745), pixels outside [minval, maxval] dropped | `fitskypars.salgorithm`, default **centroid of the sky histogram** (khist ±3σ, bins of 0.1σ), with iterative rejection (sloreject / shireject 3σ, up to 10 times) and `rgrow` (pixels around a rejected one go too); mode (3 median − 2 mean), median, mean, gauss… on request | sigma-clipped (3σ, 10 iterations) median |
| Error of the flux | √(F·g + N_ap(1 + N_ap/N_sky)(sky·g + dark + RON² + 0.289²·g²)) / g — the sky noise is modelled from the sky level, read noise and dark current (Merline & Howell 1995) | area_sq·σ²_sky + F/gain + area²·σ²_sky/N_sky (σ_sky measured) | area·σ² + F/epadu + area²·σ²/N_sky (σ measured) — the same as Siril | F/gain + N_ap(1 + N_ap/N_sky)·σ² (σ measured) — the same as IRAF |
| Centre | iterative moments in a circle (Howell's marginal-sum method by default; up to 100 iterations, stop when the move < 0.01 px), the sky taken off first (or a plane); can be turned off per aperture | PSF fit of each star on each frame (Gaussian or Moffat) | `centerpars`: calgorithm centroid (default) / gauss / ofilter / none, in a box of `cbox` 5 px, at most `cmaxiter` 10 times, refused if it moves more than `maxshift` or the S/N is below `minsnratio`; optional cleaning of bad pixels | 1-D Gaussians on the marginal sums |
| Radii from the star | radial profile in 1-px bins, normalised by the peak; FWHM where it crosses 0.5; r_ap where it falls below 1 % (`autoModeFluxCutOff` 0.010), r_in = 2 r_ap, r_out = 4 r_ap; fallback 1.7 / 3.4 / 6.8 FWHM | r_ap = factor × FWHM / 2; r_in, r_out = 4.2 and 6.3 FWHM ("autoring") | fixed values typed in (the curve of growth is a separate task) | profile, then a scan of 1–3 FWHM for the steadiest curve; r_in ≥ 4.5 FWHM |
| Ensemble | T: F_T / Σ comps; each C_k: F_C / Σ the other comps; errors added in quadrature | target − (−2.5 log Σ flux / n); a frame is dropped unless every reference is valid | not part of phot (done afterwards) | the same as AstroImageJ; a frame is dropped when a comparison star is lost (as Siril) |
| Saturation | peak per aperture compared with a saturation and a linearity level; the cell is coloured in the measurements table | any aperture pixel outside [minval, maxval] makes the star invalid on that frame | `datamax`: the measurement is flagged | peak measured, a level read from the header; not shown per point |
| Suggesting comparison stars | "Auto comparison stars" without a catalogue: local maxima with peak between mean + 1σ of the image and 0.9 × its maximum, brightness 50–150 % of T1, no neighbour within 2 r_ap, ranked by 0.5 × brightness closeness + 0.5 × nearness to T1, at most 12, only inside the region common to all frames (WCS) | from a catalogue by ΔV, Δ(B−V), catalogue error, not variable | — | from Gaia by rules (pixel rules without a solution) |
| Optimising the ensemble | "Optimise": exhaustive search of comparison-star sets, or toggling one star at a time, for the lowest RMS of the fit | — | — | scatter of each star against the others; scatter weights; no search |
| Detrending | linear terms in the χ² of the fit; BIC = χ² + k ln n; exhaustive search of covariate sets for the lowest BIC (threshold ΔBIC); meridian flip as a step from a time or a column; Kepler spline (fixed or automatic knot spacing); outlier removal | — | — | linear least squares in chosen covariates, no BIC |
| Star lists | apertures saved and opened (`.apertures`), exported / imported as an RA/Dec list | comparison-star CSV | coordinate files (`coords`) | none |
| Periodogram on the light curve | BLS and TLS, on the GPU through OpenCL (JOCL), several planets in turn | — | — | BLS / PDM / LS on the Period page (GPU paths exist) |
| Reports | AAVSO variable-star report; NEB (nearby eclipsing binary) check reports and plots for TESS follow-up; plot configuration saved as files and templates; plots to PNG / JPG / vector PDF | ETD, AAVSO | text tables (`txdump`) | CSV, AAVSO extended |
| Image window | menus File, Preferences, Scale, View, Annotate, Measure, Edit, Process, Color, Analyze, WCS; a toolbar of toggles (negative, region exclusion, bad-pixel map, annotations, sky rings, star names, counts on the image, centroid on / off, aperture settings, draw / clear apertures, clear table, run multi-aperture, align, plate solve, header, zoom ×4, auto contrast); RA / Dec at the cursor; a frame slider; a measure tool (separation, position angle, Δmag and flux ratio between two stars) | — | — | ImageViewer with pixel / profile / histogram / radial / surface / ruler tools |

Three things this changes in the list below:
- Our error formula is IRAF's and Siril's; AstroImageJ differs because it models the sky noise from the camera
  numbers. Item 2 is therefore "add the camera model as an option", not "fix a wrong formula".
- AstroImageJ's automatic radii are much larger than ours (to 1 % of the peak, sky from 2× to 4× that). Our scan
  picks by scatter; the validation (item 1) must use the same radii in both programs, or the comparison means nothing.
- AstroImageJ keeps the background-star mask from one frame to the next; this is cheap and worth copying as an idea
  in item 3.
- IRAF's default sky is the centroid of the sky histogram, not the mode (corrected 2026-11-07, read in
  `fitskypars.par`); IRAF also refuses a centre that moves too far or has too low an S/N, which matches our per-frame
  check.
- MaxIm DL (manual only): the Photometry window has tabs Select (files grouped by OBJECT and FILTER, optional
  automatic calibration), Quality (frames rejected by FWHM, roundness, background), Match (star matching or
  astrometric), Identify (tag the variable, reference stars with their magnitudes, check stars), Graph (plot, remove
  bad frames, export, print). Its errors come from the scatter of the reference stars when there are 3 or more.

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

## For the owner to try
- Measure the NY Vir night with the newest version, choosing the images and pressing Measure; send a screenshot of
  any step where it was unclear what to do.
- When convenient: an AstroImageJ Measurements table of the same night with the radii written down (item 1).

## Data used
- `data/photometry/qatar1-lco` (24 of 265 frames here): 0 frames lost, p2p 0.44 %, aperture scan chose 2 FWHM, plate
  solution 196 stars / 0.15 px after the Gaia row-limit fix (2026-11-07).
- `data/photometry/ai-dra-tess`: target-pixel-file photometry and 42 minima (HANDOFF, third campaign).
- `data/photometry/sa98-landolt-lco`: transformation coefficients (HANDOFF).

## P0 — the photometry window

The page is one column of four folding steps beside the image. Items 6 (measurements table), 7 (star lists), 8
(multi-plot) and 9 (detrending with BIC) will not fit in that column: AstroImageJ uses separate windows for them
(image with apertures, Multi-Aperture settings, Measurements table, Multi-Plot main, Multi-Plot Y-data, fit panel).

### 0. Photometry in a window of its own
**agent2 done (2026-11-08, commit 790b52b)** — built as interface I5 (first layout); the Measurements table, multi-plot
and detrend panels come with items 6, 8, 9. Findings of its first user test: `plans/interface.md` I6b (1), (2).
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
**agent2 done (2026-11-08, commit 18bda6b)** — against IRAF 2.17 `apphot.phot` (installed here; the AstroImageJ table
waits for the owner, see "For the owner to try"):
- **Two public nights, same centres, radii and sky** (IRAF `calgorithm=none` at our centres, `salgorithm=median`
  with 3σ rejection 10 times, gain from the header, no read noise):
  - Qatar-1, LCO 0.4 m, 24 calibrated frames (float), radii 9 / 18.75 / 25.99 px: fluxes IRAF/ours = 1.0001
    (spread ≤ 0.02 %), relative flux median |Δ| 0.0065 %, max 0.026 %; flux errors IRAF/ours 1.0001.
  - HAT-P-32, MicroObservatory 6-inch, 142 raw frames (integer ADU), radii 4 / 10 / 16 px: fluxes 1.00015, relative
    flux median |Δ| 0.006 %; flux errors within 0.01 %.
  - The 0.01–0.015 % is the aperture edge: IRAF weights an edge pixel linearly (r_ap − r), photutils by its exact
    area.
- **Found and fixed:** on integer data our sky was the plain median of whole numbers, off by up to 0.5 ADU: faint
  comparison stars differed from IRAF by up to 1.1 % on single frames. `aperture._grouped_median` takes the median
  inside its unit bin (grouped-data median) when the ring's pixels are whole numbers; float data are unchanged. On the
  HAT-P-32 night the point-to-point scatter fell from 0.659 to 0.625 % (4 px) and from 0.682 to 0.588 % (5 px), and
  the transit time moved 0.6 min closer to the ephemeris. IRAF itself returns a whole-number median on some of these
  frames and an interpolated one on others, so up to 0.6 % remain on single frames of faint stars, explained in the
  test.
- **Built:** `tests/validation/test_iraf_phot.py` with the reduced IRAF table of the HAT-P-32 night
  (`tests/validation/data/hatp32_iraf_phot.csv`, 142 × 3 stars; CI already downloads that night), so any drift of
  centres, fluxes or errors fails CI; the IRAF runs are scratchpad `p1/run.py` (Qatar-1) and `p1/hatp.py`.
- **Built:** "Rule: as AstroImageJ" beside Choose the radii (`aperture.aij_radii`, AstroImageJ's `Seeing_Profile`
  rule read in its source: aperture where the mean profile falls below 1 % of the peak after the half maximum,
  rounded up; sky 2× and 4× that; 1.7 / 3.4 / 6.8 FWHM otherwise), so a night can be measured with AstroImageJ's
  apertures; the light-curve scan is skipped with it. Guide 06 in four languages; tests `test_astroimagej_radii`,
  `test_grouped_median_of_integer_data`, `test_radii_rule_reaches_the_step`.
- **Still open:** the AstroImageJ Measurements table of a night from the owner, measured here with the AstroImageJ
  rule and compared the same way (a reduced table into `tests/validation` when it comes).
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
**agent2 done (2026-11-08, commit 0d8cf5f)** — `aperture.camera_pixel_noise` (√(S g + D + R² + 0.289² g²) / g per sky
pixel, AstroImageJ's model, Collins et al. 2017 app. B; Merline & Howell 1995) and `measure(..., camera=(read noise,
dark))`, carried through `light_curve(camera=…)` and the step (dark current per second times each frame's EXPTIME).
Photometry window, More measuring options: **Sky noise from the camera** with read noise and dark current, filled from
RDNOISE / READNOIS / RDNOIS and DARKCUR; off by default (the measured sky scatter, as IRAF and Siril, stays the
default: it also holds faint stars and gradients in the ring). The S/N of every star on every frame is the
measurements table's Source_SNR (item 6). Accept met: on simulated frames (gain 2, read noise 8 e⁻, dark 30 e⁻, the
dark subtracted, rounded to ADU) the predicted error matches the scatter of 1000 realisations within 5 %
(`test_camera_noise_model_predicts_the_scatter`); `test_camera_noise_option_reads_the_header_and_goes_with_the_measurement`.
Guide 06 in four languages.
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
**agent2 done (2026-11-08, commit eb4d273)** — `aperture.sky_estimate` and `measure(..., sky_method=…)` through
`light_curve` and the step: **median** (now; inside its bin for integer data, item 1), **mode** (IRAF: 3 median −
2 mean after iterative 3σ clipping), **mean** (AstroImageJ: ±2σ iterations until the mean changes < 1e-4), **plane**
(a + b dx + c dy over the ring with 3σ clipping of the residuals; its value at the centre is the sky, and over a full
circle the tilt cancels). Photometry window, More measuring options: **Sky from the ring**. Accept met: a frame with a
gradient (0.8 and −0.5 ADU/px) and a bright star in the ring — the plane gives the true sky within 0.1 σ, median, mode
and mean are more than twice as far off (`test_sky_estimates_with_a_gradient_and_a_star_in_the_ring`; the whole light
curve with each estimate and the camera noise: `test_light_curve_with_the_other_sky_estimates`). Guide 06 in four
languages.
- **Not built (rule 12, written why):** AstroImageJ's rejected-pixel mask carried from frame to frame, and IRAF's
  histogram centroid with `rgrow`. The plane's residual clipping already leaves a star in the ring out on every frame,
  and the measured gain from carrying a mask needs a crowded real night to show; they become item 3b when a night
  shows the need (a faint star in the ring changing the curve).
- **Reference:** IRAF `fitskypars.salgorithm` (mode, median, centroid…); MaxIm median-mean; AIJ iterative 2σ
  rejection of stars in the annulus and an optional plane fit; Siril rejects deviant pixels.
- **Ours:** sigma-clipped median only; no plane fit; a bright star in the annulus is clipped but not masked.
- **Build:** a choice of median (now) / mode (3 median − 2 mean with iterative clipping, IRAF) / clipped mean with
  ±2σ iterations (AstroImageJ) / plane fit (gradients from the Moon or twilight). The rejected pixels of the first
  frame kept as a mask for the next frames (AstroImageJ's idea), so a star in the ring is masked even when faint; and
  IRAF's histogram centroid with `rgrow` (the pixels around a rejected one rejected too), so a star's faint wings in
  the ring are taken out with its core.
- **Accept:** on a synthetic frame with a sky gradient and a star in the annulus, the plane fit gives the true sky
  within 0.1 σ, and the median is biased as expected.

### 4. Saturation and non-linearity flagged per point
**agent2 done (2026-11-08, commit 6143b83)** — a **Linearity limit (ADU)** under the plot (from LINLIMIT / MAXLIN, or
typed in; takes effect at once, no new measurement): points ringed orange above it, red at saturation as before, a
summary line for each; the measurements table colours the star's Peak with "non-linear" or "saturated" and the
level; **Leave out saturated and non-linear points** excludes those frames from every result (undoable). Accept met:
a synthetic night whose target saturates on exactly frames 5–9 and passes the linearity limit on 10–12 marks exactly
those, and the button leaves out exactly those 8 (`test_saturated_and_non_linear_points_are_marked_and_left_out`).
Guide 06 in four languages.
- **Reference:** IRAF `datamax` flags each measurement; AIJ warns about saturated or non-linear stars.
- **Ours:** the peak pixel is measured and a saturation level is read from the header; this is not shown per point,
  and there is no linearity limit.
- **Build:** a linearity limit (header or typed in) next to saturation; each point whose target or comparison star
  passes it is marked in the plot and the table, with an option to leave such points out.
- **Accept:** a synthetic night where the target saturates in 5 frames marks exactly those 5.

### 5. Centring per star
**agent2 done (2026-11-09, commit 9e918b6; its photometry_page.py lines landed in the wrong places, complete in f6e9fc9)** — **The target follows the field (not centred)** under the stars (step 2):
`light_curve(..., fixed=(0,))` keeps the target off centring; on each frame it gets the predicted position plus the
median shift of the centred stars (AIJ's un-centred aperture). Donuts wider than the box: `_wide_centroid` now also
takes over when the box sits in the dark hole or the brightest pixel is on the box's edge, and centres on the light in
a box that holds the ring (a 30 px ring, 2.9 px off, centred within 0.2 px: `test_donut_star_is_centred`). The
measurements table has `Centring_Move_<star>` per frame. A move beyond `max_move` (2.5 px, IRAF's `maxshift`) keeps
the prediction. Not built (rule 12): a centroid / Gaussian choice — the Gaussian is kept for stars that fit the box and
the centre of light takes over for wider ones by itself, so a choice would only add a way to get it wrong; and a
minimum S/N — `_wide_centroid` already needs 5 sigma, and a failed centroid keeps the prediction. Accept note: in the
synthetic test (a star about 70× brighter 6 px away) the 2.5 px limit already keeps the free target near its place;
with centring off it stays within 0.3 px. Guide 06 in four languages.
- **Reference:** AIJ turns centring off per aperture (an un-centred aperture follows the mean shift of the others);
  IRAF `calgorithm` = none / centroid / gauss / ofilter.
- **Ours:** every star is always re-centred with a 1D Gaussian centroid. A faint target next to a bright star can be
  pulled to the bright star.
- **Build:** per star, "do not centre: follow the field" (the shift from the other stars), and a choice of centroid /
  Gaussian. The table shows how far each star was moved on each frame.
- **Also:** a moments centroid in a circle (AstroImageJ's default, after Howell) for defocused "donut" stars, where a
  Gaussian fit fails; a limit on how far a centre may move and a minimum S/N, as IRAF's `maxshift` / `minsnratio`.
- **Accept:** a faint star 6 px from a bright one stays on the faint star when centring is off; a defocused star
  (donut, 30 px) is centred within 0.2 px.

### 6. Measurements table (one row per frame, every number)
**agent2 done (2026-11-08, commit 9af253c)** — `photometry/measurements.py` (`measurements`, `filter_rows`, `star_names`)
and a **Measurements** tab in the Photometry window's Results panel: one row per frame, AstroImageJ's column names and
star numbering (T1, C2 …, further targets T after them), numbers sorted by value with the digits they need (times to
1e-6 day), a saturated peak coloured with the level in its tooltip, **Columns** (choose what is shown), a filter in
AstroImageJ's form (`rel_flux_err_T1 < 0.002 and AIRMASS < 2`; an unknown column or a malformed rule is said in plain
words, templates in `ui/messages.py`), **Export the table (CSV)…** (the rows and columns shown), Ctrl+C, and a click
on a row shows that frame. Every AstroImageJ column for one star has a column here or a reason why not, written in the
module's docstring: X(IJ)/Y(IJ) (ImageJ's convention, the same position as X/Y(FITS)), RA/DEC per star (each frame's
plate solution is not kept with the curve), Mean / Variance / Width / Roundness / Angle per star (not measured per
star; the frame's FWHM is FWHM_Mean), N_Sky_Pixels is the ring's area before rejection. Guide 06 in four languages;
`tests/test_measurements.py`, and the real-measurement UI test checks the tab. Screenshots scratchpad `p6/`.
- **AstroImageJ's column names** (read in its `Aperture_.java`, 2026-11-08): `Label`, `slice`, `J.D.-2400000`, `JD_UTC`,
  `BJD_TDB`, `AIRMASS`; per star with the suffix `_T1`, `_C2`…: `X(IJ)`, `Y(IJ)`, `X(FITS)`, `Y(FITS)`, `RA`, `DEC`,
  `Source-Sky`, `Source_Error`, `Source_SNR`, `Source_AMag`, `Source_AMag_Err`, `N_Src_Pixels`, `Sky/Pixel`,
  `N_Sky_Pixels`, `Peak`, `Mean`, `FWHM`, `Width`, `X-Width`, `Y-Width`, `Roundness`, `Angle`, `Variance`,
  `Source_Radius`, `Sky_Rad(min)`, `Sky_Rad(max)`, `Saturated`; then `rel_flux_T1`, `rel_flux_err_T1`,
  `rel_flux_SNR_T1`, `tot_C_cnts`, `tot_C_err`.
- **Reference:** the AIJ Measurements table: JD, BJD, airmass, and for every star x, y, source counts, sky per pixel,
  peak, FWHM, S/N, rel_flux and its error.
- **Ours:** the frame list and a CSV with time, rel_flux, comparison fluxes, airmass, FWHM, Δm.
- **Build:** a full table in its own panel (sortable, copyable, a column chooser, a filter such as
  `rel_flux_err_T1 > 0.0006` as AstroImageJ's table filter, saturated and non-linear cells coloured with the reason
  in the tooltip) and the same columns in the CSV; columns named as AIJ names them where they mean the same, so
  that tables can be compared side by side; a click on a row shows that frame with its apertures.
- **Accept:** every column AIJ writes for one star has a column here or a stated reason why not.

### 7. Star list saved and used again on another night
**agent2 done (2026-11-08, commit 1bbd095)** — `photometry/starlist.py` (`save_star_list`, `load_star_list`): target,
comparison, check stars and further targets and the three radii in a small `.stars.json`, in RA / Dec through the
first frame's plate solution (and the pixels, for frames without one); opened on another night through that night's
solution — pointing, rotation, a mirrored camera all fine (test: 47° rotation and a flip, positions to 1e-6 px; the
plan's limit 1 px); stars off the frame named, a non-list file said in plain words. Photometry window: **Save the star
list…** / **Open a star list…** in the Stars step and the Stars menu; the load is undoable. Not done: keeping the list
inside the project (a project keeps files, the list is a file the user saves where they like). Guide 06 in four
languages; `tests/test_starlist.py`, `test_star_list_saved_and_opened_on_another_night`.
- **Reference:** AIJ saves apertures (in RA/Dec when the frame has WCS); Siril saves a comparison-star CSV; MaxIm
  labels reference stars so a run can be repeated.
- **Ours:** the stars are marked again on every night.
- **Build:** save target, comparison and check stars and the radii in RA/Dec to a small file (and in the project);
  loading it on another night puts the stars back through that night's plate solution.
- **Accept:** a list saved on night 1 of a public data set lands within 1 px of the same stars on night 2.

### 8. Multi-plot
**agent2 done (2026-11-09, commit f6e9fc9)** — `photometry/multiplot.py` (`available`, `series`, `prepare`,
`leave_each_out`, `save_template` / `load_template`) and **Multi-plot** in the Plot tab: the series named as in the
measurements table (`rel_flux_T1`, check stars and further targets, each comparison star's `Source-Sky_C…`, airmass,
sky, FWHM, x, y) ticked in a list and drawn one below the other with the spacing, each normalised on its own (the
night, or a typed time range, shaded: out of eclipse); a colour per series (double-click); binning by N points or by
minutes (mean and error, `timeseries.fourier.bin_time`); **Leave each comparison star out** (Analyse menu too): T1's
point-to-point scatter with the whole ensemble and every ensemble less one, best first, naming the star that helps
most; the set-up saved to and opened from a `.plot.json` (series by name, range in hours after the first frame, so
it carries over to another night; missing series named). Unbinned, clicking T1's points away works as before
(undoable). PNG / SVG / PDF and the plotted numbers to CSV were already in the plot's toolbar. Not built (rule 12):
residuals under a fit — the eclipse and transit fit is in the Models window, which draws its residuals under the
curve; a detrend per series — the detrend applies to T1, the curve every result uses, and other series are context
for it. Guide 06 in four languages; `tests/test_multiplot.py`, `test_multi_plot_series_binning_and_template`.
- **Reference:** AIJ Multi-Plot: many series on a shared time axis (target, comparison stars, check star, airmass,
  sky, FWHM, x / y), normalisation region, binning, residuals, shift-click to drop or restore a point, "cycle the
  comparison stars less one".
- **Ours:** the light curve, per-star plots, a hand-made frame exclusion list, and each comparison star's scatter.
- **Build:** one plot with selectable series stacked with offsets, each series with its own normalisation, detrend and
  colour (AstroImageJ's Y-data rows); binning by N points or by minutes; a normalisation range; residuals under a
  fit; click a point to drop it or bring it back (undoable); "leave each comparison star out in turn" with the
  scatter of every variant; the plot set-up saved as a template and opened on another night; export to PNG, SVG and
  vector PDF, and the plotted numbers to CSV.
- **Accept:** each AIJ plot used in the owner's NY Vir check can be made here.

### 9. Choosing the detrending with numbers
**agent2 done (2026-11-09, commit ee194fa)** — `differential.detrend_bic` (every set of the covariates, with and without
the flip step, fitted to ln(rel) on the same out-of-event points; BIC = χ² + k ln n with the errors, n ln(RSS/n) + k
ln n without; reduced χ²; the chosen set is the fewest terms within 2 of the lowest BIC, AstroImageJ's rule),
`detrend(..., flip_time=)` (a step in ln(rel) from the flip on), `flip_from_headers` (PIERSIDE changing during the
night) and `spline_detrend` (a cubic spline in time, knot spacing from 0.5 to 6 h chosen by the BIC, 3-sigma
clipping in three passes, bridging the left-out range, after Vanderburg & Johnson 2014 as AIJ's Kepler spline). In the
Plot tab: **Meridian flip at**, **Smooth trend (spline)** (applied after the ticked quantities), **Choose the
detrending (BIC)** (ticks and applies the chosen set, lists the six best with BIC, ΔBIC, χ²ᵣ) and **Leave out
outliers** (`timeseries.fourier.sigma_clip` against the neighbours in time, the light-curve page's test; undoable);
the last two in the Analyse menu. Times in the left-out range, the flip and the multi-plot range can be typed in
full or as the plot's axis shows them. Accept met: on a synthetic curve with an airmass trend and a flip jump the
true model (airmass + flip) has the lowest BIC and is chosen; without the jump the flip is not kept
(`test_bic_picks_the_true_model_with_the_flip`). Constant covariates are left out of the search (they tie with the
set without them). Guide 06 in four languages.
- **Reference:** AIJ shows χ², reduced χ² and BIC; a parameter is kept when BIC drops by more than 2; a meridian-flip
  term removes the jump at the flip.
- **Ours:** detrending against chosen covariates, with no BIC and no meridian-flip term.
- **Build:** BIC and ΔBIC for each covariate set (also out-of-eclipse only), with an exhaustive search over the sets
  as AstroImageJ does; a step term at the meridian flip (time from the header pier side or typed in); a smooth
  detrend (spline with knot spacing chosen automatically, as AstroImageJ's Kepler spline) for long trends; outlier
  removal against neighbours in time (the light-curve page already does this; reuse it).
- **Accept:** on a synthetic curve with an airmass trend and a flip jump, the true model has the lowest BIC.

### 9a. Optimising the ensemble
**agent2 done (2026-11-09, commit 7df5bb9)** — added 2026-11-07 after reading AstroImageJ `FitOptimization.java`.
`differential.best_comparison_sets`: every set of two or more comparison stars (up to 12 stars; more: one star
toggled at a time until the score stops improving, AIJ's second search); a set's score is the median point-to-point
scatter (mmag) of every comparison star and the check star divided by the sum of the set's other stars — the target is
never used. **Find the best comparison set** (Stars tab, Stars menu) lists the best sets in a box, uses the best one
(Ctrl+Z) and another when chosen. Accept met: one variable star among six is left out exactly, exhaustively, by
toggling and with a check star (`test_best_comparison_set_leaves_out_the_variable_star`). Rule 12: the search does
not take an out-of-eclipse range — it never looks at the target, so the eclipse cannot affect it. Also fixed: the
multi-plot's "leave each comparison star out" named the stars in AstroImageJ's numbering (C2, C3 …) while the star
table says C1, C2 …; it now uses the table's names. Guide 06 in four languages.
- **Reference:** AstroImageJ searches comparison-star sets for the lowest RMS: exhaustively, or by toggling one star
  at a time until the RMS stops improving.
- **Ours now:** each star's scatter against the others and optional scatter weights; the user unticks stars by hand.
- **Build:** "Find the best set": both searches on the out-of-eclipse part (or the whole night for a constant
  star), a table of the best sets with their RMS, and one click to use a set (undoable). The search must not choose
  a set that hides the variation of the target: it compares only the comparison stars with one another and with the
  check star.
- **Accept:** in a synthetic night with one variable comparison star, the search leaves exactly that star out.

### 9b. Speed of a night (time, memory, GPU, native code)
**agent2 done (2026-11-09, commit fa527fa; corrected in 59cf01b)** — added 2026-11-07. Profiled on 64
synthetic 4096 × 4096 16-bit frames (40 stars, a slow drift with jumps; 6 stars measured; 4 cores, 15 GB):
- **The cause was not the arithmetic.** The frame-to-frame shifts that the parallel path adds up drift (0.05 px per
  pair binned 2x2 here, the same sign every time: 3 px after 64 frames); past the 2.5 px centring limit every frame
  was read whole and matched by its star pattern (3.4 s instead of 0.27 s).
- **First fix, withdrawn:** a new shift estimate without that drift (fa527fa) was better on these synthetic frames but
  worse on the real HAT-P-32 night (undersampled MicroObservatory stars, FWHM 1.5 px): 1.5 px of drift there, a
  comparison star kept at its prediction, point-to-point scatter 0.0056 -> 0.0096, and the IRAF validation failed in
  CI. The old estimate is back (that night is again identical to the IRAF reference).
- **The fix kept:** when the stars are not where the shifts put them, a centring pass three times as wide (repeated
  until it settles) finds their median offset and the frame is measured from there; only if that fails is the frame
  read whole and matched by its star pattern (`lightcurve._field_offset`,
  `test_stars_a_few_pixels_off_their_prediction_are_found_without_the_slow_path`).
- Also kept: binning by strided sums (the same means, 150 -> 30 ms per 4k frame); the alignment keeps only binned
  frames; `load` subtracts the overscan in place (one full-size copy less per process).
- Before -> after: 64 synthetic frames, shifts known: 1575 -> 184 ms per frame, largest worker 1149 -> 327 MB; from
  scratch (shifts measured too): 1945 -> 336 ms per frame including two process starts, peak memory of the machine
  1.98 GB. Real Qatar-1 night (265 LCO frames, shifts known): 30.5 -> 10.9 s, results identical to the old code
  (relative flux and positions, difference 0.0). HAT-P-32: identical to the IRAF reference again.
- Estimate for 1000 × 4k² frames on 4 cores: about 0.16 s alignment + 0.09 s measuring per frame, about 4 minutes,
  just under 2 GB; not run on 1000 real frames (64 GB of frames do not fit this machine's disk).
- Not done (rule 12): numba or C for the inner loops — no loop dominates now (a frame: reading 0.06 s, six Gaussian
  centroids 0.07 s, apertures and sky the rest); GPU sky statistics — a few stars per frame do not pay for the
  transfer. Reading ahead was already there.
- Lesson written down: the validation data (`ASTROWB_VALIDATION_DATA`) must be set for the local full check; the 9b
  commit was checked without it.

## P2 — complete for eclipsing binaries and variable stars

### 10. Several apertures at once and aperture correction
**agent2 done (2026-11-09, commit 0953f9f)** — `light_curve(..., apertures=)` measures every frame through each radius
asked for (inside the sky ring), with the same centres and sky, and keeps them in `lc["by_aperture"]`;
`with_aperture(lc, i)` gives the curve of radius i without measuring again (stars a frame lacks stay out, item 13);
`aperture_correction(lc)` the curve of growth: each radius's median share of the light through the largest, and
−2.5 log10 of it. In the window: *Also measure other radii, to choose one later* (0.6–2 × the aperture) under More
measuring options; **Aperture radius** in the Plot tab switches (undoable) and shows the share and the correction.
Accept met: switching to 7 px after measuring 3, 5, 7, 9 px gives the same relative flux and fluxes as measuring with
7 px (to 1e-9; `test_switching_the_aperture_after_measuring_equals_measuring_with_it`). Rule 12: the errors of a
switched radius do not carry the scintillation term (added only for the radius measured); the aperture correction is
relative to the largest radius measured, not extrapolated to infinity. Guide 06 in four languages.
- **Reference:** IRAF `phot` measures a list of apertures in one pass; `mkapfile` builds a curve of growth and the
  aperture correction.
- **Ours:** the scan tries several radii but keeps one; there is no aperture correction.
- **Build:** keep the curves for every scanned radius (pick one later without measuring again); a curve of growth
  and aperture correction for catalogue magnitudes.
- **Accept:** switching radius after the measurement gives the same curve as measuring with that radius.

### 11. Several filters in one night
**agent2 done (2026-11-09, commit 4c79ab3)** — `photometry/multifilter.py` (`by_filter`, moved here from the Calibrate
page; `colour_pair`, the bluer filter first; `colour_curve`, each image of the sparser filter paired with the nearest
of the other within 1.5 cadences, Δm_a − Δm_b, and with T_ab and the comparison colour the standard colour
(A − B) = comp_colour + T_ab Δ(a − b)) and the `photometry.multifilter` step (every filter with the same stars,
radii and options, positions carried from the frame they were marked on). In the window: the filter question for a
mixed set offers *All of them*; the measurement then runs every filter, shows the marked filter's curve and adds
**Colour index (a − b) against time** to the Plot tab. Accept met: a synthetic B / V night with the target reddening by
0.05 mag gives that change in the colour curve, and the standard colour follows T_bv
(`test_two_filter_night_gives_the_injected_colour_change`). Rule 12: the transformed magnitudes of each filter are not
built here — the per-filter calibration exists (catalogue magnitudes, transformation step); the colour is what a mixed
night adds. Also: item 10's guide text had not been written (a failed insertion); it is in this commit. Guide 06 in
four languages.
- **Reference:** IRAF photcal transformation equations; common practice in B and V monitoring.
- **Ours:** the images are grouped by filter, but each filter is measured on its own; the transformation exists only
  as separate steps.
- **Build:** one run over a mixed B / V / R sequence giving a curve per filter, the colour-index curve (B−V against
  time), and transformed magnitudes when coefficients exist.
- **Accept:** a synthetic two-filter night gives the injected colour change.

### 12. Several nights together
**agent2 done (2026-11-09, commit 1a70b14)** — `photometry/nights.py`: `join_nights` puts the raw fluxes of all nights into
one ensemble (`differential.ensemble`, item 13's shares from the frames with every comparison star, so a night that
lacks a star all night is scaled by the share it lacks) and returns one curve with the raw fluxes, the night of each
point and how far each night moved; `read_export` reads the window's CSV export back. **Add other nights (exported
CSV)…** in the Export tab joins them with the night measured now; with T0 and the period the minimum step already
times every eclipse of a long series, so every night's minimum goes to O−C at once. `ensemble` also sums the stars
there when no frame has every star (it gave NaN). Accept met: two nights with comparison star C2 missing all of the
second night (a 0.05 mag step in a plain join) join with less than 0.002 mag between the nights, also from the
exported CSV files (`test_two_nights_with_a_star_missing_one_night_join_without_a_step`). Rule 12: the export keeps
relative errors only, so a night read back shares its error between the target and the comparison stars. Guide 06 in
four languages.
- **Reference:** Muniwin and AIJ work per night; observers join the nights afterwards.
- **Ours:** one night at a time (survey curves can be joined, nightly ones cannot).
- **Build:** join nights measured with the same star list; offsets per night from the common comparison stars; the
  minima of every night go to O−C at once.
- **Accept:** two nights of one star with a 0.05 mag offset injected are joined without the step.

### 13. Frames where a comparison star is missing
**agent2 done (2026-11-09, commit 2d87162)** — `differential.ensemble` takes NaN comparison fluxes: a frame's ensemble
is the sum of the stars it has divided by their median share of the whole sum on the frames with every star
(Honeycutt 1992's zero point per frame, in flux), the error grown accordingly. `light_curve` keeps a frame whose only
problem is missing comparison stars when at least one is left; their fluxes are NaN and `lc["partial"]` names them
per file. The window shows such frames orange in the frame list (the missing stars in the tooltip) and counts them
under the plot. Accept met: a synthetic night where C2 leaves the field half-way keeps all 10 frames with no jump
(< 0.5 %; `test_light_curve_keeps_the_frames_a_comparison_star_left`; ensemble alone < 0.1 %). Guide 06 in four
languages.
- **Reference:** Honeycutt 1992 inhomogeneous ensemble photometry (each frame uses the stars it has); Muniwin's
  artificial comparison star.
- **Ours:** a frame without one comparison star is left out of the light curve.
- **Build:** an ensemble zero point per frame from the stars that frame does have (Honeycutt), with the frame marked.
- **Accept:** a night where one comparison star leaves the field half-way keeps every frame, with no jump.

### 14. Time systems
**agent2 done (2026-11-09, commit 59cf01b)** — `light_curve` writes `hjd_utc` (timing.hjd, astropy's heliocentric light
travel time) whenever the target's position is known; it is the `HJD_UTC` column of the measurements table
(AstroImageJ's name) and of the CSV export. `timing.mid_time(header, ref, delay)`: the header's time read as the
start, middle or end of the exposure ("auto" keeps the old reading: start, or what the DATE-OBS comment says) and a
shutter delay in seconds added; both under More measuring options (**The header's time marks**, **Shutter delay**),
passed through the light-curve step. Accept met: HJD equals astropy's light-travel-time computation (< 1 s) and
differs from JD by more than a minute for the test star; "mid" with a 0.5 s delay moves a 10 s exposure's times by
−4.5 s (`test_header_time_convention_shutter_delay_and_hjd`, `test_light_curve_keeps_the_frames_a_comparison_star_left`).
Rule 12: a shutter delay per camera is one number per measurement here, not a camera database — the program does not
keep camera profiles yet (devices item). Guide 06 in four languages.
- **Reference:** AIJ writes HJD_UTC and BJD_TDB; much eclipsing-binary O−C literature is in HJD.
- **Ours:** BJD_TDB (or JD_UTC without coordinates).
- **Build:** HJD_UTC as an extra column; the header time read as start, middle or end (choice); a shutter-delay
  correction per camera.
- **Accept:** HJD matches astropy's light-travel-time computation within 1 s for a test star.

### 15. Export formats
**agent2 claimed (2026-11-09) — do not touch**
- **Reference:** Siril writes ETD (Exoplanet Transit Database) format and AAVSO extended; AIJ writes its
  measurements table and MPC magnitudes.
- **Ours:** CSV and AAVSO extended.
- **Build:** ETD format; the AIJ-style measurements table (item 6); a light-curve file the Models page reads
  directly.
- **Accept:** the ETD file is accepted by the ETD upload check (or matches its published column layout).

### 16. Eclipse and transit fit on the light-curve page
**agent2 done (2026-11-09, commit de3d416)** — `minima.trapezoid_fit(..., covariates=)`: the trapezoid times
exp(Σ c_k (z_k − mean z_k)) in one least-squares fit (the starting point from the curve with a first trend divided
out, since the trend can be deeper than the transit), with the coefficients and the BIC; the `timeseries.minimum`
step takes `detrend_with` (airmass, fwhm, sky, x, y) and fits them on the light curve before any detrending. In the
Photometry window's Minimum tab: **Fit the ticked detrending quantities together with the transit** (with the
trapezoid; the quantities ticked in the Plot tab); the result shows the coefficients and the BIC, and the time goes to
O−C as before. Accept met: a synthetic transit on a curved airmass trend gives depth and mid-time within their 1σ
(times 1.5 for the test's margin) and the airmass coefficient; the fit without the trend has a BIC more than 10
higher (`test_transit_fitted_together_with_an_airmass_trend`). Rule 12: only the trapezoid gets the joint fit — the
Kwee–van Woerden time has no model to put a trend in, and the physical eclipse models stay on the Models page.
Guide 06 in four languages.
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

### 22. Aperture shapes
**open** — added 2026-11-07 (AstroImageJ `ShapedApertureRoi`, `FreeformPixelApertureRoi`).
- **Reference:** AstroImageJ offers circular, elliptical and free-form (painted pixel) apertures, for trailed or
  elongated stars and for blends.
- **Build:** elliptical apertures (axis ratio and angle from the star's moments) and a painted aperture, measured
  with exact pixel areas like the circles.
- **Accept:** a trailed star (3:1) gives the same flux as its untrailed copy within 1 %.

### 23. Nearby eclipsing binary check
**open** — added 2026-11-07 (AstroImageJ NEB reports).
- **Reference:** for a target whose eclipse was found in survey data (TESS pixels are 21″), AstroImageJ measures
  every Gaia star nearby and reports whether one of them could make the dip.
- **Build:** the Gaia stars within a radius measured on every frame; for each, the depth it would need to cause the
  target's dip; those that show it, or could, listed and plotted.
- **Accept:** on a synthetic field where a neighbour carries the eclipse, the neighbour is named.

### 24. Measuring between two stars on the image
**open** — added 2026-11-07 (AstroImageJ Measure menu).
- **Reference:** separation, position angle, Δmag and flux ratio between two clicked stars, written to a table.
- **Build:** the ruler tool also gives Δmag and flux ratio (apertures at both ends), on any frame.
- **Accept:** two synthetic stars of known flux ratio give it within 0.5 %.

## Order proposed

New items found by research, trials or tests are inserted where their urgency puts them (numbers may then be
given letters, e.g. 3a); this order is updated with them.


0 (after interface I2) → 1 → 6 → 7 → 2 → 3 → 4 → 5 → 8 → 9 → 9a → 9b, then P2 in the order the owner's work needs (13, 14 and 16 first for eclipsing
binaries). Item 1 comes first: every later change is then checked against AstroImageJ automatically.

## Done

(none yet)
