# Photometry: what a full-featured tool needs, and what is still missing

Written 2026-11-07 at the owner's request: "scan AstroImageJ, Siril, MaxIm DL, IRAF and the others, and write down
everything that has to be done; do not do it yet". **Nothing here is started without the owner's word.** Work one
item at a time, in order; when an item is done, tick it and add the commit hash. HANDOFF.md keeps the history; this
file keeps only the photometry to-do list.

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

## P1 — trust in the light curve

### 1. Same frames, same answer as AstroImageJ (validation)
- **Reference:** the owner compares against AIJ by eye; no number says we agree.
- **Ours:** checked only on synthetic frames and Qatar-1 scatter.
- **Build:** a validation script that measures one public night (Qatar-1 LCO and one eclipsing binary night) with
  fixed target, comparisons and radii, and compares per-frame rel_flux and its error with an AIJ Measurements table
  exported for the same settings. A reduced reference table (time, rel_flux, error; public data only) goes into
  `tests/validation`, so CI catches any drift.
- **Accept:** median |ours/AIJ − 1| < 0.1 % per frame and errors within 10 %; any larger difference explained in the
  test.

### 2. Noise model with the camera's numbers
- **Reference:** AIJ appendix B (source and sky Poisson noise, dark current, read noise, quantisation); IRAF
  `datapars` (epadu, readnoise).
- **Ours:** F/gain plus the scatter of the sky ring; read noise and dark current enter only through that scatter, and
  S/N per star is not shown.
- **Build:** GAIN, RDNOISE / READNOIS, DARKCUR (or values typed once per camera) in the error; S/N of every star on
  every frame in the table.
- **Accept:** on simulated frames with known gain, read noise and dark current, the predicted error matches the
  scatter of 1000 noise realisations within 5 %.

### 3. Sky estimate choices
- **Reference:** IRAF `fitskypars.salgorithm` (mode, median, centroid…); MaxIm median-mean; AIJ iterative 2σ
  rejection of stars in the annulus and an optional plane fit; Siril rejects deviant pixels.
- **Ours:** sigma-clipped median only; no plane fit; a bright star in the annulus is clipped but not masked.
- **Build:** a choice of median / mode (3 median − 2 mean, DAOPHOT) / plane fit (for gradients from the Moon or
  twilight). Pixels of other stars found in the annulus are masked before the estimate.
- **Accept:** on a synthetic frame with a sky gradient and a star in the annulus, the plane fit gives the true sky
  within 0.1 σ, and the median is biased as expected.

### 4. Saturation and non-linearity flagged per point
- **Reference:** IRAF `datamax` flags each measurement; AIJ warns about saturated or non-linear stars.
- **Ours:** the peak pixel is measured and a saturation level is read from the header; this is not shown per point,
  and there is no linearity limit.
- **Build:** a linearity limit (header or typed in) next to saturation; each point whose target or comparison star
  passes it is marked in the plot and the table, with an option to leave such points out.
- **Accept:** a synthetic night where the target saturates in 5 frames marks exactly those 5.

### 5. Centring per star
- **Reference:** AIJ turns centring off per aperture (an un-centred aperture follows the mean shift of the others);
  IRAF `calgorithm` = none / centroid / gauss / ofilter.
- **Ours:** every star is always re-centred with a 1D Gaussian centroid. A faint target next to a bright star can be
  pulled to the bright star.
- **Build:** per star, "do not centre: follow the field" (the shift from the other stars), and a choice of centroid /
  Gaussian. The table shows how far each star was moved on each frame.
- **Accept:** a faint star 6 px from a bright one stays on the faint star when centring is off.

### 6. Measurements table (one row per frame, every number)
- **Reference:** the AIJ Measurements table: JD, BJD, airmass, and for every star x, y, source counts, sky per pixel,
  peak, FWHM, S/N, rel_flux and its error.
- **Ours:** the frame list and a CSV with time, rel_flux, comparison fluxes, airmass, FWHM, Δm.
- **Build:** a full table on the page (sortable, copyable) and the same columns in the CSV; columns named as AIJ
  names them where they mean the same, so that tables can be compared side by side.
- **Accept:** every column AIJ writes for one star has a column here or a stated reason why not.

### 7. Star list saved and used again on another night
- **Reference:** AIJ saves apertures (in RA/Dec when the frame has WCS); Siril saves a comparison-star CSV; MaxIm
  labels reference stars so a run can be repeated.
- **Ours:** the stars are marked again on every night.
- **Build:** save target, comparison and check stars and the radii in RA/Dec to a small file (and in the project);
  loading it on another night puts the stars back through that night's plate solution.
- **Accept:** a list saved on night 1 of a public data set lands within 1 px of the same stars on night 2.

### 8. Multi-plot
- **Reference:** AIJ Multi-Plot: many series on a shared time axis (target, comparison stars, check star, airmass,
  sky, FWHM, x / y), normalisation region, binning, residuals, shift-click to drop or restore a point, "cycle the
  comparison stars less one".
- **Ours:** the light curve, per-star plots, a hand-made frame exclusion list, and each comparison star's scatter.
- **Build:** one plot with selectable series stacked with offsets; binning by N points or by minutes; a normalisation
  range; click a point to drop it or bring it back (undoable); "leave each comparison star out in turn" with the
  scatter of every variant.
- **Accept:** each AIJ plot used in the owner's NY Vir check can be made here.

### 9. Choosing the detrending with numbers
- **Reference:** AIJ shows χ², reduced χ² and BIC; a parameter is kept when BIC drops by more than 2; a meridian-flip
  term removes the jump at the flip.
- **Ours:** detrending against chosen covariates, with no BIC and no meridian-flip term.
- **Build:** BIC and ΔBIC for each covariate set (also out-of-eclipse only); a step term at the meridian flip (time
  from the header pier side or typed in).
- **Accept:** on a synthetic curve with an airmass trend and a flip jump, the true model has the lowest BIC.

## P2 — complete for eclipsing binaries and variable stars

### 10. Several apertures at once and aperture correction
- **Reference:** IRAF `phot` measures a list of apertures in one pass; `mkapfile` builds a curve of growth and the
  aperture correction.
- **Ours:** the scan tries several radii but keeps one; there is no aperture correction.
- **Build:** keep the curves for every scanned radius (pick one later without measuring again); a curve of growth
  and aperture correction for catalogue magnitudes.
- **Accept:** switching radius after the measurement gives the same curve as measuring with that radius.

### 11. Several filters in one night
- **Reference:** IRAF photcal transformation equations; common practice in B and V monitoring.
- **Ours:** the images are grouped by filter, but each filter is measured on its own; the transformation exists only
  as separate steps.
- **Build:** one run over a mixed B / V / R sequence giving a curve per filter, the colour-index curve (B−V against
  time), and transformed magnitudes when coefficients exist.
- **Accept:** a synthetic two-filter night gives the injected colour change.

### 12. Several nights together
- **Reference:** Muniwin and AIJ work per night; observers join the nights afterwards.
- **Ours:** one night at a time (survey curves can be joined, nightly ones cannot).
- **Build:** join nights measured with the same star list; offsets per night from the common comparison stars; the
  minima of every night go to O−C at once.
- **Accept:** two nights of one star with a 0.05 mag offset injected are joined without the step.

### 13. Frames where a comparison star is missing
- **Reference:** Honeycutt 1992 inhomogeneous ensemble photometry (each frame uses the stars it has); Muniwin's
  artificial comparison star.
- **Ours:** a frame without one comparison star is left out of the light curve.
- **Build:** an ensemble zero point per frame from the stars that frame does have (Honeycutt), with the frame marked.
- **Accept:** a night where one comparison star leaves the field half-way keeps every frame, with no jump.

### 14. Time systems
- **Reference:** AIJ writes HJD_UTC and BJD_TDB; much eclipsing-binary O−C literature is in HJD.
- **Ours:** BJD_TDB (or JD_UTC without coordinates).
- **Build:** HJD_UTC as an extra column; the header time read as start, middle or end (choice); a shutter-delay
  correction per camera.
- **Accept:** HJD matches astropy's light-travel-time computation within 1 s for a test star.

### 15. Export formats
- **Reference:** Siril writes ETD (Exoplanet Transit Database) format and AAVSO extended; AIJ writes its
  measurements table and MPC magnitudes.
- **Ours:** CSV and AAVSO extended.
- **Build:** ETD format; the AIJ-style measurements table (item 6); a light-curve file the Models page reads
  directly.
- **Accept:** the ETD file is accepted by the ETD upload check (or matches its published column layout).

### 16. Eclipse and transit fit on the light-curve page
- **Reference:** AIJ fits a transit model with the detrending in the same χ² and reports BIC.
- **Ours:** minimum timing (KvW and others) on the Photometry page; transit and eclipsing-binary models live on the
  Models page.
- **Build:** a fit of the eclipse or transit with the detrending together, run from the light curve without changing
  pages; the result's time of minimum goes to O−C.
- **Accept:** a synthetic transit with an airmass trend: depth and mid-time recovered within 1σ.

### 17. Comparison-star criteria the user can set
- **Reference:** Siril findcompstars: ΔV (default 3), Δ(B−V) (default 0.5), largest catalogue error (0.03 mag),
  catalogue APASS or NOMAD, centred circle or whole image, variable catalogues GCVS / VSX / Gaia.
- **Ours:** fixed |ΔG| ≤ 2.5 and colour within 0.5 (a preference), Gaia flag and VSX, no catalogue-error limit.
- **Build:** these criteria in a folded "Comparison-star rules" section; GCVS and a catalogue-error limit added;
  why each nearby star was rejected shown on request.
- **Accept:** for the NY Vir field, the list and the reasons agree with Siril's rules applied by hand.

### 18. Crowded fields
- **Reference:** DAOPHOT allstar (neighbours fitted and subtracted); Siril PSF with Gaussian or Moffat.
- **Ours:** grouped Gaussian PSF fits.
- **Build:** a Moffat PSF; neighbours subtracted before aperture photometry of the target.
- **Accept:** a blended pair 1.5 FWHM apart gives each star's flux within 1 %.

## P3 — workflow

### 19. Real-time photometry at the telescope
- **Reference:** AIJ real-time mode (new files calibrated and measured as they arrive).
- **Ours:** live photometry exists.
- **Build:** check that it now uses the same per-frame checks, sky options and star list as the night run (items
  2–7); show the lost frames live.
- **Accept:** a night replayed file by file gives the same curve as the batch run.

### 20. The same run without the window
- **Reference:** Siril scripts, IRAF CL scripts.
- **Ours:** engine steps exist but there is no saved "photometry recipe".
- **Build:** save the page's settings and star list as a recipe; run it from the command line on a folder.
- **Accept:** GUI run and command-line run give identical tables.

### 21. Photometry of moving objects
- **Reference:** MaxIm tags first and last frame and tracks an asteroid.
- **Ours:** astrometry of moving objects only.
- **Build:** a light curve of a moving object (aperture follows the track, comparison stars fixed).
- **Accept:** a synthetic moving star of constant brightness gives a flat curve.

## Order proposed

1 → 6 → 7 → 2 → 3 → 4 → 5 → 8 → 9, then P2 in the order the owner's work needs (13, 14 and 16 first for eclipsing
binaries). Item 1 comes first: every later change is then checked against AstroImageJ automatically.

## Done

(none yet)
