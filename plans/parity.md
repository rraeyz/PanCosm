# Comparison with the reference programs

Read `PLAN.md` first. This file answers one question for every capability of the programs we must beat: **do we
have it, and if not, which step builds it?** It was written on 2026-11-09 from the programs' source code, manuals
and papers (the lists of what was read are in each area file) and from our own code at `7cc4cba`.

- ● = we have it, checked on real data · ◐ = partly (the note says what is missing) · ○ = missing.
- A step in the last column means "this step completes it". A row with ● and no step needs nothing.
- **Keeping this file true is part of every step:** the agent who finishes a step changes the marks of the rows
  that name it, in the same commit. A capability found in a reference program and not listed here is added (with
  its mark and a step, or under "Found while working" of the area file when no step exists yet).
- "Better than them" is the last section: what none of the reference programs has and we plan.

## AstroImageJ (photometry, transits)

| Capability | Ours | Step |
| --- | --- | --- |
| Multi-aperture photometry on an image series, target and comparison stars, ensemble | ● | — |
| Exact pixel-overlap aperture sums; sky annulus with star rejection or plane | ● | — |
| Apertures placed by RA / Dec through the WCS; apertures saved and opened | ● (star lists) | — |
| Variable aperture scaled with each frame's FWHM | ● | — |
| Radii from the radial profile (the 1 % rule) | ● | — |
| Centroid on / off per aperture; Howell centroid | ◐ (target only; one centring method) | PHO-44 |
| Elliptical and free-form pixel apertures | ○ | PHO-22 |
| Moving-target tracking in Multi-Aperture (5.5.0) | ○ | PHO-21 |
| Opens TESScut files, TESS postage stamps, TICA and SPOC full-frame images | ◐ (pixel files and TESScut) | PHO-32 |
| Multi-threaded photometry (5.5.0) | ● | — |
| Noise model with gain, read noise, dark current, quantisation | ● | — |
| Saturation and linearity warnings per star | ● | — |
| Automatic comparison stars | ◐ (catalogue-based; rules fixed; reasons not shown) | PHO-17 |
| Measurements table with filter and column chooser | ● | — |
| Multi-plot: many series, normalisation, binning, shift, per-series detrend | ◐ (detrend only for the target) | PHO-46 |
| Detrending with BIC, exhaustive search, meridian flip, spline smoothing | ● | — |
| Comparison-star set optimisation | ● | — |
| Transit fit (Mandel & Agol) with priors, locks, residuals, derived parameters, host-star panel | ○ (trapezoid only in the window) | PHO-26, EXO-1 |
| Odd / even view at twice the period | ○ | PHO-26 |
| NEB check reports for TESS follow-up | ○ | PHO-23 |
| AAVSO variable-star report | ● | — |
| AAVSO exoplanet report; TFOP file set; "save all" | ○ | PHO-27 |
| Data Processor: calibration, header updates (airmass, BJD), plate solve, run photometry on new files (real time) | ◐ (pieces exist; live path is separate code; no header tool) | PHO-19, CAL-22, CAL-23 |
| Linearity correction, outlier removal in calibration | ● / ◐ (cosmic rays by L.A.Cosmic; no preview) | CAL-12 |
| Stack aligner (apertures or WCS), image stabiliser | ◐ (shift and star-pattern; no WCS mode) | CAL-15 |
| Coordinate converter (times, coordinates, airmass) | ○ | ARC-15 |
| BLS and TLS periodograms on the GPU | ◐ (BLS; no TLS) | PER-3, PER-8 |
| Image window: toolbar toggles, RA / Dec read-out, measure tool, annotations, contour and 3-D plots, seeing profile, header editor | ◐ (most exist; measure between stars and uniform keys missing) | ARC-7, IMG-3, PHO-24 |
| Photometric debayer, RGB composer | ● | — |
| Create mean PSF | ○ | PHO-18 |
| Macros | ◐ (automations; no "copy as script") | ARC-12, AUT-2 |

## HOPS, EXOTIC (transit pipelines for observers)

| Capability | Ours | Step |
| --- | --- | --- |
| One guided path: reduction → alignment → photometry → transit fit → upload files | ◐ (the steps exist; no guided path; trapezoid fit) | UI-8, PHO-26, PHO-27 |
| Planet parameters and priors fetched from the archives | ◐ (ephemeris only) | EXO-10 |
| MCMC / nested-sampling transit fit with limb darkening from tables | ○ | EXO-1, EXO-3, EXO-5 |
| Aperture and PSF photometry options | ◐ (Gaussian PSF only) | PHO-18 |
| ExoClock and AAVSO Exoplanet Database files | ◐ (ExoClock, ETD) | PHO-27 |

## EXOFASTv2 (global exoplanet fits)

| Capability | Ours | Step |
| --- | --- | --- |
| Quadratic-law transit model, stable for all geometries, long-cadence integration | ○ | EXO-1 |
| Several planets, bands, telescopes; per-transit baseline and detrending (additive and multiplicative) | ○ | EXO-7 |
| Radial velocities: per-instrument zero point and jitter, slope, quadratic | ◐ (single orbit fits in Spectroscopy) | EXO-2 |
| Star: SED + parallax + MIST / YY / PARSEC or Torres relations in the same fit | ○ | EXO-6, EXO-7 |
| Limb-darkening priors from Claret tables per band | ○ | EXO-3, MOD-6 |
| Prior file: Gaussian, bounds, fixed, start values for any parameter | ○ | EXO-5, EXO-7 |
| DE-MC with parallel tempering; Gelman–Rubin and independent-draw stopping rule | ○ (emcee, fixed length, no test) | EXO-5 |
| Derived parameters (durations, densities, temperatures, probabilities…) with intervals | ○ | EXO-4 |
| TTVs, depth and inclination variations per transit | ○ | EXO-7, EXO-9, OC-13 |
| Secondary eclipse, thermal and reflected light, dilution, beaming | ○ | EXO-1, EXO-8 |
| Rossiter–McLaughlin; Doppler tomography | ○ | EXO-8; EXO-18 |
| Astrometry in the fit | ○ | not planned (EXOFASTv2 itself marks it untested); MOD-20 covers visual orbits |
| LaTeX tables, figures of every data set, PDFs, chains | ○ | EXO-12 |
| Mass–radius relation when only one of mass or radius is measured (Chen & Kipping) | ○ | EXO-17 (context plots); a prior option is added under EXO-7 when a data set needs it |

## IRAF (the standard for results)

| Package / task | Capability | Ours | Step |
| --- | --- | --- | --- |
| `ccdred` | `ccdproc`: overscan, trim, zero, dark, flat | ● | — |
| | `fixpix`, bad-pixel files | ◐ (map from dark and flat; no files) | CAL-8 |
| | `zerocombine`, `darkcombine`, `flatcombine` with all rejection, scaling, weighting choices | ◐ (median + MAD clipping for masters) | CAL-5 |
| | `mkfringecor`, `mkillumcor`, `mkillumflat`, `mkskycor`, `mkskyflat` | ○ | CAL-10, CAL-11 |
| | `ccdmask`, `ccdlist`, `ccdgroups`, `ccdhedit`, `setinstrument` | ◐ (classification and matching; no header tools, no rule files) | CAL-1, CAL-2, CAL-8, CAL-23 |
| | multi-amplifier / mosaic data (`mscred`) | ○ | CAL-4 |
| | `findgain` | ○ | CAL-9 |
| `images` | `imcombine`, `imarith`, `imexpr`, `imstat`, `imhead`, `hedit` | ● / ◐ | CAL-5, IMG-10 |
| | `imexamine` | ◐ (tools exist; no keys, fewer fits) | ARC-7, IMG-3 |
| | `imalign`, `geomap`, `geotran`, `imshift` | ◐ (shift, similarity) | CAL-15 |
| | `ccmap`, `ccsetwcs`, `cctran` (plate solutions) | ◐ (needs header hints or an external solver) | AST-1, AST-2, AST-3 |
| `apphot` | `phot` with `centerpars`, `fitskypars`, `photpars`, `datapars` | ● (validated; centroid sky algorithm and centring choice missing) | PHO-44, PHO-45 |
| | several apertures in one pass, `mkapfile` growth curves | ● / ◐ (relative correction only) | PHO-28 |
| `daophot` | `daofind`, `psf`, `nstar`, `allstar`, `substar`, `addstar` | ◐ (grouped Gaussian fits) | PHO-18, PHO-29 |
| `photcal` | `mknobsfile`, `fitparams`, `evalfit`, `invertfit` | ◐ (extinction and two-filter transformation) | PHO-28, PHO-35 |
| `apextract` | `apall`, `apfind`, `aptrace`, aperture editor | ◐ (one object; no editor) | SPE-3 |
| | variance-weighted extraction with cleaning | ● | — |
| | `apflatten`, `apnormalize`, `apscatter` | ◐ (scattered light for échelle; no flat normalisation) | SPE-1, SPE-9 |
| `longslit` | `identify`, `reidentify`, `autoidentify` | ◐ (user identifies; reference arcs; no keys, no automatic proposal without a reference) | SPE-7 |
| | `fitcoords`, `transform` (2-D rectification) | ○ | SPE-4 |
| | `background`, `response`, `illumination` | ◐ (polynomial sky) | SPE-5, SPE-1 |
| `onedspec` | `dispcor`, `refspectra` | ◐ (native pixels kept; no rebin option; nearest arc only) | SPE-7 |
| | `standard`, `sensfunc`, `calibrate`, extinction | ◐ (response from one reference spectrum) | SPE-10 |
| | `splot` (equivalent widths, profile fits, deblending, arithmetic, smoothing) | ◐ (single profile; no deblend) | SPE-12, SPE-13 |
| | `continuum`, `scombine`, `sarith`, `specplot`, `deredden`, `telluric`, `skytweak` | ◐ (continuum, combine, arithmetic, telluric by standard) | SPE-5, SPE-11, SPE-12 |
| `echelle` | `ecidentify`, `ecreidentify`, `ecdispcor`, order merging | ● / ◐ (2-D solution validated; panel and propagation missing) | SPE-7, SPE-9 |
| `rv` | `fxcor`, `rvidlines`, `rvcorrect` | ● / ◐ (CCF, barycentric correction; no line-list velocities) | SPE-14 |
| `astutil` | `setairmass`, `setjd`, `asttimes` | ◐ (computed, not written to headers) | CAL-23, ARC-15 |
| CL | scripts, parameter files, lists | ◐ (automations) | ARC-12, AUT-1, AUT-2 |
| `stsdas` | `ellipse` isophotes | ○ | PHO-39 |
| `artdata` | artificial stars and noise for tests and teaching | ◐ (practice night generator) | OBS-16 |

## PyReduce and PypeIt (échelle and slit reduction)

| Capability | Ours | Step |
| --- | --- | --- |
| Order tracing, editing of orders | ● | — |
| Scattered-light model between orders | ● | — |
| Normalised flat and blaze from the flat | ◐ (blaze; flat not normalised) | SPE-9 |
| Slit curvature (tilt, shear) measured and used | ○ | SPE-4 |
| Slit-function decomposition extraction with curved slits | ○ | SPE-6 |
| 2-D wavelength solution (pixel × order), comb / etalon refinement | ● / ○ | SPE-23 |
| Continuum normalisation splicing orders | ◐ | SPE-9, SPE-12 |
| Instrument definitions as data | ◐ (user profiles) | SPE-2 |
| PypeIt: frame typing and configurations, calibration groups | ◐ | SPE-1 |
| PypeIt: object finding, several objects, manual traces | ◐ | SPE-3 |
| PypeIt: B-spline sky subtraction with tilts; nod pairs | ○ | SPE-4, SPE-5 |
| PypeIt: automatic wavelength identification | ◐ (from a reference arc) | SPE-7 |
| PypeIt: flexure from sky lines | ● | SPE-8 (adds telluric bands) |
| PypeIt: sensitivity function, flux calibration, telluric model fit, co-adding | ◐ | SPE-10, SPE-11 |
| PypeIt: quality-assurance pictures of every stage | ○ | SPE-6, SPE-7 (diagnostic views) |

## iSpec (spectral analysis)

| Capability | Ours | Step |
| --- | --- | --- |
| Several spectra open, one active; regions drawn on the plot (continuum, lines, segments) | ○ | SPE-12 |
| Continuum fit: splines, polynomials, template, fixed value; with regions | ◐ | SPE-12 |
| Find continuum regions, line masks, segments | ○ | SPE-12, SPE-13 |
| Fit lines, cross-match with atomic line lists, export fitted lines | ◐ | SPE-13 |
| Radial velocity by CCF with atomic masks, telluric masks or templates | ◐ (templates) | SPE-14 |
| Barycentric velocity | ● | — |
| Estimate S/N; errors from S/N; add noise; degrade resolution; resample; combine; clean; mathematical expression | ◐ | SPE-12 |
| Clean telluric regions | ◐ (standard star) | SPE-11 |
| Parameters with a grid of synthetic spectra | ● | SPE-17 (more grids, masks, benchmarks) |
| Parameters and abundances with synthesis or equivalent widths (external codes) | ○ | SPE-19 |
| Interpolate a spectrum from a grid; synthesise a spectrum | ◐ (grid interpolation) | SPE-17, SPE-19 |
| Send a spectrum to other programs (SAMP) | ○ | SPE-12, IMG-12 |

## MaxIm DL (imaging suite)

| Capability | Ours | Step |
| --- | --- | --- |
| Camera, filter wheel, focuser, telescope, rotator, dome control | ◐ (Alpaca and INDI; no COM drivers) | OBS-1 |
| Sequences with autosave; sub-frames; binning | ● | OBS-6 (triggers, dry run) |
| Autoguiding (built in, multi-star) | ◐ (through PHD2) | OBS-5 |
| Autofocus | ● | OBS-4 (backlash, wizards, triggers) |
| Observatory window (dome, weather, telescope status) | ◐ | OBS-10, UI-16.9 |
| Pier flip with guide-star reacquisition | ◐ | OBS-8 |
| Calibration with automatic groups; dark scaling modes; combine types | ● / ◐ | CAL-1, CAL-5 |
| Stack: align modes, combine methods, drizzle | ● / ◐ | CAL-15, CAL-16 |
| Information window (aperture, astrometric, magnitude, region, area) | ◐ | IMG-3 |
| Screen stretch window | ◐ (levels dialog) | IMG-2 |
| Photometry tool with tabs following the workflow | ● (ours goes further) | PHO-W |
| Astrometry with PinPoint; blind solving | ◐ | AST-1, AST-2 |
| Process and Filter menus (flatten, gradient, deconvolution, DDP, kernels, FFT, unsharp, wavelets, bin, resize, rotate, pixel math) | ◐ (16 operations; no wavelets, FFT, sample-point background) | IMG-7 |
| Colour: RGB / LRGB, balance | ◐ | IMG-7 |
| Batch processing, command sequences | ◐ | IMG-8 |
| FITS header editor, batch header edit | ◐ | IMG-10, CAL-23 |
| Blink, animate, annotate | ◐ | IMG-13, IMG-11 |
| Scripting (COM) | ◐ | ARC-12 |

## N.I.N.A. (acquisition)

| Capability | Ours | Step |
| --- | --- | --- |
| Equipment through ASCOM (COM and Alpaca) | ◐ | OBS-1 |
| Sky atlas, framing assistant, mosaics | ○ | PLN-5, PLN-6, PLN-10 |
| Simple sequencer | ● | — |
| Advanced sequencer: containers, conditions, triggers, templates | ○ | OBS-6 |
| Autofocus: overshoot, several fits, triggers, filter offsets | ◐ | OBS-4 |
| Plate solve, sync, centre, rotate | ◐ (no rotation step) | OBS-3 |
| Meridian flip trigger | ◐ | OBS-8 |
| Flat wizard | ◐ | OBS-9 |
| Dither, guide graph, centre after drift | ◐ | OBS-5 |
| Imaging tab panels: statistics, HFR and star history, guiding, image history | ○ | OBS-11 |
| Safety monitor, weather, dome synchronisation, switches | ◐ | OBS-10 |
| Profiles | ○ | ARC-16 |
| Plug-ins | ◐ | AUT-5 |

## Wilson–Devinney with PyWD2015, PHOEBE, JKTEBOP, ellc (eclipsing binaries)

| Capability | Ours | Step |
| --- | --- | --- |
| Roche geometry; detached, semi-detached, overcontact, double-contact modes | ○ | MOD-1, MOD-10 |
| Limb darkening laws with table interpolation | ◐ (quadratic, typed) | MOD-2, MOD-6 |
| Gravity darkening, reflection (simple, detailed, multiple) | ○ | MOD-2, MOD-4 |
| Atmosphere-based passband intensities; many passbands | ○ | MOD-6 |
| Spots | ○ | MOD-8 |
| Eccentric orbits, asynchronous rotation, dω/dt, dP/dt, third-body light-time | ◐ (e cos ω, e sin ω) | MOD-5 |
| Third light per band | ◐ (one band) | MOD-10 |
| Several light curves and both velocity curves fitted together | ○ | MOD-7, MOD-10, MOD-12 |
| Velocity curves with proximity and Rossiter effects | ○ | MOD-7 |
| LC program: synthetic curves, star positions, dimensions, conjunction times | ◐ | MOD-3, MOD-15, MOD-16 |
| DC program: differential corrections with subsets, history of iterations | ◐ (least squares; no history) | MOD-12 |
| q-search | ○ | MOD-13 |
| Eclipse timings in the solution; O−C window | ◐ (separate O−C window) | MOD-17 |
| Line-profile synthesis | ○ | MOD-17 (data kinds, P2), MOD-22 |
| PHOEBE: estimators for starting values | ○ | MOD-11 |
| PHOEBE: optimisers (Nelder–Mead, differential evolution…), samplers (emcee, dynesty), priors, constraints | ◐ (least squares, emcee) | MOD-12, MOD-14, EXO-5 |
| PHOEBE: mesh plots and animations | ○ | MOD-16 |
| PHOEBE: Gaussian processes, extinction, boosting, misaligned spins | ○ | EXO-13 (GP), MOD-5 (boosting); extinction and misalignment not planned until a data set needs them (written in MOD-22's scope) |
| JKTEBOP: simple model with all limb-darkening laws, numerical integration, polynomial terms | ◐ | MOD-18 |
| JKTEBOP: Monte Carlo and residual-permutation errors | ◐ (emcee) | MOD-14 |
| JKTEBOP: light-ratio and third-light constraints, velocities and minima with the light curve | ○ | MOD-17, MOD-18 |
| Absolute dimensions and distance | ◐ (masses, radii, log g) | MOD-15 |
| Binary Maker: interactive star-shape view | ○ | MOD-16 |

## Period04, Peranso, VStar, lightkurve (period and frequency)

| Capability | Ours | Step |
| --- | --- | --- |
| DFT amplitude spectrum, spectral window, noise spectrum | ● | — |
| Multi-frequency least squares ("improve all"), fixed harmonics and combinations | ◐ (automatic prewhitening) | PER-6 |
| Errors: analytic, correlation, Monte Carlo | ◐ | PER-4, PER-6 |
| Subsets, weights, zero-point adjustment | ○ | PER-1, PER-6 |
| Amplitude / phase variations; periodic time shift | ○ | PER-6 |
| Peranso's method list (Lomb–Scargle, DCDFT, CLEANest, FALC, ANOVA, PDM, string lengths, Jurkevich, EEBLS…) | ◐ (LS, DFT, CLEAN, ANOVA, PDM, BLS) | PER-3, PER-18 |
| Significance (false-alarm probability, permutation) | ○ | PER-4 |
| Alias and harmonic identification | ○ | PER-4 |
| WWZ wavelet (VStar) | ○ | PER-9 |
| Extremum timing, O−C (Peranso) | ● | OC-2 (more methods) |
| lightkurve: mission products, quality masks, stitch, flatten, fold, bin | ◐ | PER-1, PER-2, PER-7 |
| lightkurve: pixel files, custom masks, PLD / regression correctors | ◐ (apertures on pixel frames) | PHO-32 |
| lightkurve: seismology (νmax, Δν, échelle diagram) | ○ | PER-14 |
| TLS | ○ | PER-3 |
| AAVSO, ASAS-SN, ZTF, TESS, Kepler sources | ● | PER-1 (more surveys) |

## OCFit and the O−C services

| Capability | Ours | Step |
| --- | --- | --- |
| Linear and quadratic ephemeris fits | ● | OC-5 (weights, tests, segments) |
| LTTE with one body; MCMC | ● | — |
| LTTE with two bodies; with a parabola | ○ | OC-6 |
| Apsidal motion | ◐ (first order) | OC-7 |
| Global search without start values (genetic algorithm) | ◐ (grid in P₃) | OC-6 |
| TTV models (Agol) | ○ | OC-13, EXO-15 |
| Databases of minima per star | ○ | OC-4 |
| Predictions of minima per night | ◐ (listed targets) | PLN-4, PLN-5 |

## Astrometrica, Tycho Tracker, ASTAP, astrometry.net

| Capability | Ours | Step |
| --- | --- | --- |
| Reduction against Gaia with plate constants and residual report | ◐ | AST-3 |
| Known-object overlay, blink | ● | AST-4 |
| Track and stack | ○ | AST-5 |
| Synthetic tracking on the GPU | ○ | AST-5 |
| Magnitudes with a catalogue zero point | ○ | IMG-5, AST-4 |
| MPC reports (ADES, 80-column) | ◐ (ADES PSV) | AST-6 |
| Blind, offline solving | ○ (external solvers only) | AST-2 |
| Image inspector (tilt, curvature, aberration tiles) | ○ | IMG-4 |
| Light curves of moving objects | ○ | PHO-21 |

## DS9, Siril (viewing and processing)

| Capability | Ours | Step |
| --- | --- | --- |
| Scales and limits (zscale, percentiles, log, asinh, histogram) | ● | IMG-2 |
| Frames tiled and locked by WCS; blink | ◐ | IMG-2, ARC-7 |
| Regions (full language), region statistics | ◐ | IMG-6 |
| Magnifier, panner, pixel table | ○ | ARC-7, IMG-3 |
| Catalogue overlays | ● | IMG-11 |
| SAMP | ○ | IMG-12 |
| Siril: registration modes, stacking rejections (winsorized, linear fit, GESD), normalisation, weights | ◐ | CAL-5, CAL-15, CAL-16 |
| Siril: background extraction with samples, deconvolution, wavelets, stretches | ◐ | IMG-7 |
| Siril: photometric and spectrophotometric colour calibration | ○ | IMG-7 |
| Siril: light curves with comparison stars from catalogues | ● | — |
| Siril: scripts, Python scripting | ◐ | ARC-12, AUT-6 |

## SNAP, QGIS (remote sensing)

| Capability | Ours | Step |
| --- | --- | --- |
| Sentinel-2, Landsat products with roles, scales, quality masks | ◐ (Sentinel-2) | RS-1 |
| RGB composites, stretch, layers, spectrum view | ◐ | RS-2 |
| Resample, subset, reproject, mosaic | ○ | RS-3 |
| Band maths, index library | ● / ◐ | RS-5 |
| k-means; supervised classification with accuracy assessment | ● / ○ | RS-6 |
| Change detection, time series | ◐ | RS-7 |
| Vector layers, zonal statistics | ○ | RS-8 |
| Map export | ○ | RS-13 |

## Where we go beyond all of them

| What no reference program has | Step |
| --- | --- |
| One project from planning to paper, with every result passed between windows without files | (the architecture) |
| Undo / redo and autosaved sessions in every window | ARC-5 |
| The reason for every automatic choice shown and editable (comparison stars, frames left out, lines matched) | PHO-17, CAL-1, SPE-7 |
| A calibration plan the user reads before running, and a quality report of the masters | CAL-3, CAL-6 |
| Variance and mask planes from the raw frame to the light curve and the spectrum | CAL-13, PHO-36, SPE-6 |
| Honest errors by default (largest of several estimates; red-noise factor; coverage-tested) | OC-2, PHO-34, VAL-7 |
| Starting values estimated from the data for binary models; a parameter table in plain words | MOD-11, MOD-10 |
| A convergence light on every MCMC; runs that pause and resume | EXO-5 |
| "What can I observe tonight?" that knows the horizon, the equipment's precision and the observer's own history | PLN-5, PLN-6, PLN-13 |
| Phase-coverage planning over many nights from the data already taken | PLN-8 |
| Framing chosen so that the best comparison stars are in the field | PLN-6 |
| Time stamps checked against network time, with the offset in every header | OBS-2 |
| No refocus, flip or dither inside an ingress or egress; exposure held in the linear range | OBS-7 |
| A dry run of tomorrow's program and a simulated observatory rendering the real sky | OBS-6, OBS-16 |
| Advice for the next night from tonight's data | PHO-43 |
| Methods paragraph and citations written from what was actually done; a reproducibility bundle | ARC-11, AUT-8 |
| "Save as recipe" and "Copy as Python" in every window; the same run from the command line | ARC-12, AUT-2 |
| The same windows in four languages with a glossary of astronomy terms | ARC-18, UI-18 |
| CPU and GPU paths with identical results on any graphics card | ARC-10 |
| A validation report regenerated by CI for every release | VAL-3, VAL-10 |
