# Spectroscopy and radial velocities: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.3).

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

From raw 2-D frames to science: long-slit, échelle (slit and fibre), slitless and cube data → extracted, wavelength-
and flux-calibrated spectra with errors → line measurements, radial velocities, orbits, rotation, atmospheric
parameters, spectral types.

**Goal:** the results of IRAF (`apall`, `identify`, `ecidentify`, `dispcor`, `sensfunc`, `splot`, `fxcor`), the
extraction quality of PyReduce and PypeIt, the analysis tools of iSpec and the ease of the amateur packages (ISIS,
BASS, Demetra, RSpec) — in one window where the frame, the spectrum and the fit are always in sight, every
identification is the user's to check, and nothing has to be installed beside the program.

## What the reference programs do

Read (never copied; PyReduce is GPL-3, iSpec AGPL-3, PypeIt BSD-3, specreduce BSD-3): IRAF `noao/twodspec/apextract`
(`apall`, `apfind`, `aptrace`, `apflatten`, `apnormalize`, `apscatter`), `twodspec/longslit` (`identify`,
`reidentify`, `fitcoords`, `transform`, `background`, `response`, `illumination`), `onedspec` (`splot`, `dispcor`,
`refspectra`, `standard`, `sensfunc`, `calibrate`, `continuum`, `scombine`, `sarith`, `deredden`, `telluric`,
`skytweak`, `specplot`), `imred/echelle` (`ecidentify`, `ecreidentify`, `ecdispcor`), `rv` (`fxcor`, `rvidlines`,
`rvcorrect`); PyReduce (`reduce.py` steps: mask, bias, flat, orders, scatter, norm_flat, wavecal master / init /
finalize, freq_comb, curvature, science, continuum, finalize; `extract.py` slit-function decomposition; `make_shear.py`;
`wavelength_calibration.py`; `continuum_normalization.py`); PypeIt documentation and `core/` (object finding, tilts,
B-spline sky, flexure, `arc`/`wavecal` automatic identification, fluxing, telluric, coadd); specreduce; iSpec
(`ispec/` continuum, lines, spectrum, modeling; the menus listed in `plans/interface.md`); the HARPS / ESPRESSO DRS
papers; SERVAL; Molecfit papers.

| Stage | IRAF | PyReduce | PypeIt | iSpec | Amateur (ISIS, BASS, RSpec) | Ours now |
| --- | --- | --- | --- | --- | --- | --- |
| Tracing | `apfind` / `aptrace`: several apertures, interactive editor on the profile | order polynomials from clusters of pixels, merged and edited | object finding with S/N threshold, traces from standards | — | geometric rectification by hand (tilt, slant, smile) | one object: brightest or a given row; trace followed in steps (`longslit.trace`); échelle orders found and traced on a flat |
| Geometry | `fitcoords` + `transform` (rectify with a 2-D fit of arc lines) | slit curvature per order (`make_shear`: tilt and shear polynomials) | tilts image: wavelength at every pixel; no resampling | — | tilt / slant / smile correction | none: the slit is assumed along columns |
| Sky | polynomial across the slit per column (`background`, `apall b`) | — (fibre) or in the slit function | **B-spline sky in wavelength with the tilts (Kelson 2003)**, local refinement, nod pairs | — | sky zones | polynomial per column from two bands |
| Extraction | sum; **variance-weighted (Horne 1986)** with cleaning; profile from polynomial or spline fits | **slit-function decomposition with curved slits (Piskunov, Wehrhahn & Marquart 2021)** | optimal with fitted object profile; boxcar | — | binning zone | boxcar; Horne optimal with a smoothed profile |
| Flat | `response`, `apflatten`, `apnormalize` | normalised flat + blaze from the slit-function fit | pixel flat, illumination flat, slit edges from flats | — | flat by division with a smoothed lamp | lamp flat divided as it is (échelle: blaze from the flat) |
| Scattered light | `apscatter` (2-D fit between orders) | 2-D polynomial between orders | — | — | — | `echelle.scattered_light` |
| Wavelengths | `identify` (interactive: mark, fit, delete), `reidentify`, `autoidentify`, `refspectra`, `dispcor`; échelle 2-D in order and pixel (`ecidentify`) | 2-D polynomial; line list with initial positions per instrument; laser comb / etalon | **automatic identification** (pattern matching against archived solutions and line lists), 2-D for échelle, flexure from sky lines | — | lamp presets, automatic for known spectrographs | user identifies lines; iterative match and clipped fit; reference arcs and IRAF databases reused; global 2-D échelle fit; sky-line zero point |
| Flux | `standard`, `sensfunc`, `calibrate`, extinction files per site | — | sensitivity function with telluric model, coadd in flux | — | response from an A star and a library spectrum | `analysis.response` (ratio to a reference spectrum) |
| Telluric | `telluric` (scale and shift a standard) | — | **model fit (atmosphere grid + object model)** | telluric mask from a line list | division by a standard | standard star scaled in optical depth and shifted |
| Continuum | `continuum` (interactive polynomial / spline with rejection) | per-order with the blaze, splice of orders, iterative | — | splines / polynomial / template, with regions | manual points | polynomial with asymmetric clipping; points by hand |
| Lines | `splot`: equivalent width, Gaussian / Lorentz / Voigt, **deblend**, statistics, smoothing, arithmetic | — | — | line fitting, equivalent widths from line regions, cross-match with atomic lists | measurements, Be-star tools | EW, single Gaussian / Voigt, V/R, smoothing, arithmetic, resample, BeSS export |
| Velocities | `fxcor` (Fourier cross-correlation, filter, fit of the peak, Tonry & Davis R), `rvidlines`, `rvcorrect` | — | — | CCF with **masks** or templates; barycentric correction | — | CCF on ln λ with a template, Zucker error, TODCOR, broadening function, barycentric correction, SB1 / SB2 orbits, shift-and-add disentangling |
| Parameters | — | — | — | **synthesis and equivalent-width methods with external codes (SPECTRUM, Turbospectrum, MOOG, SME, WIDTH), abundances, grids** | — | fit on a PHOENIX grid (Teff, log g, [Fe/H], v sin i, RV); MK type against standards |

## What we already have (do not redo)

- `spectroscopy/`: `longslit.py`, `echelle.py`, `wavecal.py`, `reidentify.py`, `combine.py`, `telluric.py`, `rv.py`,
  `sb2.py` (TODCOR), `bf.py`, `disentangle.py`, `orbit.py`, `atmosphere.py`, `mkstandards.py`, `templates.py`,
  `analysis.py`, `cube.py`, `spectrum_io.py`, steps `spectroscopy.{reduce, echelle, orders, telluric, combine, rv,
  orbit, classify, disentangle, atmosphere}`; line lists `resources/linelists/` (HeAr, HeNeAr, CuAr, FeAr, ThAr, Xe).
- Already-extracted spectra are recognised and only wavelength-calibrated (no forced order of steps).
- Window with six jobs, the 2-D frame with the trace above the plots (old steps 1.1, 1.2), instrument profiles.
- Checked on real data: EFOSC2 long slit against PESSTO (feature correlation 0.84–0.88, wavelengths within ~1 Å);
  raw HARPS against the ESO DRS (0.0 m/s median, 21.6 m/s rms wavelengths; velocity +9 ± 8 m/s); TOFES fibre échelle
  (886 solar lines, rms 0.005 Å; Arcturus −5.77 ± 0.20 km/s); FLOYDS; FEROS AI Phe; ARAS amateur spectra; LAMOST
  types (`docs/history/HANDOFF-2026-11.md`).

## Decisions

- No resampling unless asked: spectra keep their native pixels with a wavelength array (and variance and mask);
  rebinning to linear or log steps is an explicit, flux-conserving operation (as PypeIt; IRAF's `dispcor` habit is
  available but not the default).
- Wavelengths in air by default for optical spectra, vacuum on request; the header and every table say which.
- Line identification stays with the user: the program proposes (automatic matching), shows every line it used with
  its residual, and the user accepts, deletes or adds (owner, 2026-11-04).
- Spectral types and atmospheric parameters are suggestions with their scores, never a silent verdict; MKCLASS is
  never bundled or run.
- External radiative-transfer codes (MOOG, Turbospectrum, SPECTRUM) are never bundled; the program can drive one the
  user installed (SPE-19).

## To ask the owner

- Which spectrographs the owner's group uses (RTT150 TFOSC grisms and échelle mode, coudé échelle, Shelyak eShel /
  LISA at university observatories?) and one raw night of each, for the profiles of SPE-2 and the validation.

## For the owner to try

- After SPE-W and SPE-7: reduce one of your long-slit nights and one échelle night; identify the lamp lines with the
  new panel; say whether the identification feels as sure as with your IRAF atlas.

## Data used

- `data/spectroscopy/efosc-longslit`, `floyds-lco`, `tofes-echelle`, `harps-beta-pic`, `feros-ai-phe`,
  `feros-telluric`; `data/reference/{kurucz-solar-atlas, nist, pickles}`.
- To add (each with `SOURCE.md`): a long-slit night with a tilted, curved slit image and an extended object (SPE-4);
  raw UVES or another slit échelle with tilted lines and its pipeline product (SPE-6); an amateur eShel night with
  the ISIS product; a spectrophotometric standard night with two standards at different airmass (SPE-10); a
  Star Analyser slitless frame (SPE-21); a radial-velocity standard series and an SB2 with a published orbit
  (SPE-14, SPE-15); a Be star series from BeSS.

## Steps

Order of work: SPE-W, then P1: 1, 2, 3, 5, 6, 7, 8, 9, 12, 13, 14, 15, 22, 24; P2: 4, 10, 11, 16, 17, 18, 21, 23;
P3: 19, 20, 25, 26.

### SPE-W. The Spectroscopy window on the new anatomy  (P1)
**open** (old steps 1.3 "panels", 2 "keys in the arc identification" and 3 "several spectra in one plot" are
released and live on in SPE-7 and SPE-12)
- `plans/interface.md` UI-16.3: job switch (Long slit · Échelle · Spectrum · Velocities · Orbit · Parameters · Cube),
  a rail per job, the 2-D frame, the profile and the spectrum stacked, the identification panel with fit and
  residuals always visible.
- **Extra accept:** on the EFOSC2 set: frames chosen → trace and aperture shown on the frame → extracted → lines
  proposed and accepted → wavelength-calibrated spectrum saved: every state fits 1366 × 768 without scrolling, in
  four languages; a 1-D spectrum dropped on the window opens the Spectrum job directly (no forced order).
- **Depends on:** ARC-4.3, ARC-5, ARC-6, ARC-7, ARC-8, UI-1 … UI-4.
- **Files:** `ui/spectroscopy/{window,controller,state,menus}.py`, `ui/spectroscopy/jobs/{longslit,echelle,spectrum,velocities,orbit,parameters,cube}/`, `ui/spectroscopy/panels/{frames,profile,identify,fit}.py`, `tests/ui/walks/spectroscopy.py`, guide 08

### SPE-1. Frames, roles and associations for spectra  (P1)
**open**
- **Reference:** PypeIt's `pypeit_setup` (frames typed as bias, dark, pixel flat, illumination flat, trace, arc,
  tilt, science, standard; grouped into configurations by grating, angle, slit, binning; calibration groups); ESO
  DPR keywords; IRAF's `ccdtype` plus hand lists.
- **Ours now:** two file fields (science, arc) and the Calibration window before.
- **Build:** the Frames stage takes a folder or files and builds the table (CAL-1 groups) with **roles**: science,
  standard (flux), telluric standard, arc (by lamp), lamp flat, sky / twilight flat, bias, dark, sky frame, focus /
  test (ignored); configurations by disperser, slit, central wavelength / angle, binning, read-out; for every
  science frame its arc (nearest in time of the same configuration, or the two bracketing arcs for interpolation),
  flat and standard, shown as a small plan (as CAL's Plan tab) the user can change; basic calibration through the
  CAL engine with the spectroscopy defaults (CAL-18); frames already calibrated or already extracted are marked and
  used as they are.
- **Accept:** the EFOSC2, FLOYDS and TOFES nights each produce the right roles, configurations and associations
  (expected tables stored); a night with two gratings gives two configurations that do not mix.
- **Files:** `spectroscopy/frames.py`, UI frames panel, tests.

### SPE-2. Instrument profiles as data  (P1)
**open**
- **Reference:** PyReduce `instruments/*.json` (keyword maps, orientation, order ranges), PypeIt spectrograph
  classes, ISIS / BASS instrument presets (Alpy 600, LISA, LHIRES III, eShel, Star Analyser).
- **Ours now:** named profiles saved by the user (orientation, apertures, line list, orders).
- **Build:** `resources/spectrographs/*.toml` + `core/profiles.Spectrograph` (ARC-16): how to recognise the
  instrument from headers; dispersion axis and direction; long slit / slit échelle / fibre échelle / slitless;
  approximate dispersion and wavelength range per disperser; lamps; order numbers and blaze wavelengths for
  échelles; an archived wavelength solution and reference arc where the instrument's data are public (the automatic
  identification of SPE-7 starts from it); defaults for apertures and sky. Shipped profiles for the instruments of
  the data sets (EFOSC2, FLOYDS, TOFES, HARPS, FEROS) and the common amateur ones (Alpy 600, LISA, LHIRES III, eShel,
  UVEX, Star Analyser 100 / 200) from their public documentation; "New profile from this frame…" wizard (asks the
  three things that cannot be read: which way the dispersion runs, where blue is, which lamp).
- **Accept:** each data set's frames select their profile by themselves; a user profile made with the wizard reduces
  a rotated copy of the EFOSC2 set identically.
- **Files:** `resources/spectrographs/*.toml`, `core/profiles.py` (`Spectrograph`), `spectroscopy/instrument.py`, `ui/spectroscopy/dialogs/new_profile.py`, `tests/test_spectrograph_profiles.py`

### SPE-3. Finding objects, tracing, and the aperture editor  (P1)
**open**
- **Read first:** IRAF `apextract` documentation (the aperture editor keys and the `aptrace` algorithm); PypeIt
  "Object Finding"; Marsh 1989 §2 (tracing).
- **Ours now:** `longslit.find_spectrum`, `trace`, `shifted_trace`; one object.
- **Build:**
  1. `longslit.find_objects(image, variance, n_max, snr_min)`: the spatial profile collapsed along the dispersion
     (median over chosen columns, sky removed), peaks above `snr_min` with FWHM; each becomes an aperture with limits
     at a fraction of the peak (default 5 %) or ± k FWHM, and with sky bands placed outside all objects.
  2. Tracing each object as today; faint objects borrow the trace **shape** of the brightest or of a standard-star
     frame (have), with their own offset; trace fit order by BIC; trace residuals reported (px rms).
  3. The aperture editor: the profile plot under the frame with the apertures and sky bands as draggable ranges;
     keys under the cursor as IRAF habit (`m` mark, `d` delete, `l` / `u` lower / upper limit, `b` background
     bands, `c` centre, `t` trace again, `a` all apertures); the same ranges are drawn on the 2-D frame and can be
     dragged there; multi-aperture extraction gives one spectrum per aperture (named A1, A2 …).
  4. Extended objects: an aperture may be split into N spatial bins (spatially resolved spectra along the slit).
  5. Errors: `spectroscopy.no_object_found` (what / do: lower the threshold, mark by hand, check the orientation).
- **Accept:** a synthetic frame with three objects (S/N 100, 15, 4) and a tilted, curved trace: all found, centres
  within 0.1 px, the faint one traced by the bright one's shape within 0.2 px; the EFOSC2 science frame and the
  FLOYDS two-order frame give the apertures expected; editor keys driven by a QTest.
- **Files:** `spectroscopy/longslit.py`, `ui/spectroscopy/panels/profile.py`, tests.

### SPE-4. Slit geometry: tilt, curvature and the wavelength of every pixel  (P2)
**open**
- **Read first:** Kelson 2003 (PASP 115, 688) §2–3; PypeIt "Wavelength tilts"; IRAF `fitcoords` / `transform`;
  PyReduce `make_shear.py` (what is measured: tilt and shear of each arc line along the slit, fitted in 2-D).
- **Build:** `spectroscopy/geometry.py`: trace arc (or sky) lines along the slit (centroid per spatial bin), fit
  their tilt and curvature as a 2-D polynomial of (x, y) → `wavelength_map(y, x)` once the 1-D solution exists;
  two uses: (a) keep the frame as it is and use the map for sky modelling (SPE-5) and extraction (SPE-6) — the
  default; (b) `rectify()` to straight lines with flux-conserving resampling and propagated variance for users who
  want a rectified 2-D spectrum (extended objects, position–velocity diagrams). A view of the arc frame with the
  fitted line shapes drawn over it; residuals in px.
- **Accept:** synthetic arc with a 2° tilt and a quadratic curvature: the map is accurate to 0.03 px; sky-line
  residuals after SPE-5 with the map are ≤ 1.5 × the noise where the column-wise sky leaves P-Cygni-like residuals
  ≥ 5 × the noise (asserted on synthetic and on the real tilted set).
- **Depends on:** SPE-7 (1-D solution).
- **Files:** `spectroscopy/geometry.py`, `ui/spectroscopy/panels/geometry.py`, `tests/test_slit_geometry.py`

### SPE-5. Sky subtraction  (P1)
**open**
- **Read first:** Kelson 2003; PypeIt "Sky subtraction" (global B-spline, local refinement with the object
  profile); IRAF `background`.
- **Ours now:** `longslit.sky_model`: a polynomial across the slit per column from two bands.
- **Build:** methods: `columns` (have; order 0–2, with rejection of cosmic rays and faint objects in the bands);
  `bspline` (with the wavelength map of SPE-4: all sky pixels as samples of sky(λ) with break points every ~0.7
  px, iterative rejection, an optional low-order spatial illumination term); `nod` (A − B pairs, then residual
  removal); `separate` (a sky frame or sky fibre scaled; for échelle fibres); residual sky-line scaling
  (IRAF `skytweak`: scale and shift a sky spectrum to minimise residuals). The sky spectrum is kept with the
  product (it serves the zero point, SPE-8) and its variance enters the error.
- **Accept:** synthetic frames with bright sky lines and Poisson noise: residuals within 1.2 × the expected noise
  for `bspline` with the map; `columns` equal to today's results on the stored sets; an A − B synthetic pair gives
  an unbiased spectrum.
- **Files:** `spectroscopy/sky.py`, `longslit.py`, tests.

### SPE-6. Extraction: optimal for every geometry, with errors and masks  (P1)
**open**
- **Read first:** Horne 1986 (PASP 98, 609); Marsh 1989 (PASP 101, 1032: curved and tilted traces); Piskunov &
  Valenti 2002 (A&A 385, 1095) and Piskunov, Wehrhahn & Marquart 2021 (A&A 646, A32: slit-function decomposition
  with a curved slit image; the regularisation parameters); Zechmeister, Anglada-Escudé & Reiners 2014 (A&A 561,
  A59: flat-relative optimal extraction for fibre-fed échelles); Hynes 2002 (blended objects).
- **Ours now:** `longslit.boxcar`, `optimal` (Horne with a smoothed profile, cosmic-ray clipping);
  `echelle.extract(method=…)`.
- **Build:**
  1. One extraction interface `extract(frame: Frame, trace, aperture, sky, method, geometry) → Spectrum1D(flux,
     variance, mask, sky, n_rejected)` for long slit and échelle orders; inputs carry variance and DQ (CAL-13).
  2. Methods: `sum` (partial pixels at the aperture edges); `horne` (have; profile smoothed along the dispersion by
     polynomials per spatial pixel — Horne — or by a running median, chosen by S/N); `marsh` (profile on a
     sub-pixel grid following a tilted / curved trace); `slitfunction` (decomposition of each swath into spectrum ×
     slit function on an oversampled grid with smoothness regularisation, overlapping swaths blended, with the
     slit tilt / shear of SPE-4 — the method for échelles with tilted lines); `flat_relative` (for stable fibre
     échelles: the spectrum relative to the flat's profile — also removes the blaze and pixel response in one
     step); `blend` (two or three close objects fitted simultaneously with a shared profile shape).
  3. Rejection of deviant pixels in every optimal method (σ from the variance model; the rejected pixels counted
     per wavelength pixel and written to the mask); saturated and bad pixels never used.
  4. Native kernel (ARC-9) for the slit-function solves (banded linear systems per swath) and for Marsh's profile
     fits if profiling asks.
  5. A diagnostics view: data, model and residual images of the order / object (as PyReduce's and PypeIt's QA), the
     profile, and the reduced χ² along the dispersion.
- **Accept:**
  1. Synthetic spectra with known flux and variance: every method unbiased (< 0.3 %) and the variance estimates
     within 5 % of the scatter over 200 noise realisations; optimal methods gain the expected S/N over the sum at
     low S/N (≥ 1.3 × at S/N 5 per pixel with a 6 px wide profile).
  2. Tilted lines (3 px across the aperture): `slitfunction` keeps the resolving power (line FWHM within 3 % of the
     truth) where `horne` broadens it by > 15 % (asserted).
  3. Real slit échelle with tilted lines: our spectrum against the pipeline product: line widths within 3 %, S/N
     within 5 %.
  4. HARPS order extraction equal to today's within noise; 72 orders × 4096 px optimal < 15 s.
- **Files:** `spectroscopy/extract.py` (new, from `longslit` and `echelle`), `native/src/slitfunc.rs`, tests,
  guide 08 and 13.

### SPE-7. Wavelength calibration: the identification panel, automatic proposals, quality  (P1)
**open**
- **Read first:** IRAF `identify` / `reidentify` / `autoidentify` help; PypeIt "Wavelength calibration" (the
  automatic algorithms: matching patterns of line spacings against a line list with archived solutions) and its
  Identify GUI keys; the RASCAL method (Veitch-Michaelis & Lam 2020: Hough transform over pairs of peaks and atlas
  lines, then RANSAC); NIST Atomic Spectra Database (wavelengths in air above 2000 Å; Ritz vs observed).
- **Ours now:** `wavecal.find_lines`, `solve` (user guesses → iterative match → clipped polynomial, degree by
  n lines), `reidentify.py` (IRAF databases, reference arcs, `from_reference`, `shift_features`), échelle `solve_2d`.
- **Build:**
  1. Line lists as data with provenance: per lamp (He, Ne, Ar, Kr, Xe, Hg, Cd, Cu, Fe, Th, combinations as used:
     HeAr, HeNeAr, NeAr, HgAr, HgCd, CuAr, FeAr, ThAr, ThNe) from NIST with relative intensities, blend flags at a
     given resolving power (lines closer than λ / R are merged or dropped — computed for the profile's R), night-sky
     lines (OH from Rousselot et al. 2000, O I, Na, Hg from street lights) for sky-based solutions.
  2. `wavecal.auto_identify(peaks, line_list, hint)`: (a) from the profile's archived solution or a reference arc
     (have: cross-correlation with stretch); (b) without one: a search over (central wavelength, dispersion) by
     Hough voting of peak–line pairs within the hint's ranges (from the spectrograph profile or the user's "blue is
     about 3800, red about 7500"), then RANSAC polynomial; returns matches with a confidence and the runner-up
     solution; **nothing is accepted silently**: the panel shows the proposal ("31 lines matched, rms 0.12 Å;
     second-best solution rms 0.9 Å") for the user to accept.
  3. The identification panel (Inspector, always visible in the Wavelengths stage): the arc with marked lines and a
     ghost of the predicted line positions; the table of lines (pixel, wavelength, element, residual, used ☑); the
     fit plot and the residual plot (click a point to leave it out); keys under the cursor: `m` mark and choose the
     wavelength from the nearest list lines (a small popup with the candidates), `d` / Delete remove, `f` fit, `a`
     auto-identify from the current solution, `+` / `−` order, `w` pixel ↔ wavelength axis, `r` reset, `?` keys.
  4. A lamp atlas beside the arc: the reference spectrum of the lamp at the profile's resolution drawn from the line
     list (and the archived real arc when the profile has one) with labels — the "atlas" the owner knows from IRAF,
     for confident identification by eye.
  5. Fit: polynomial / Chebyshev / Legendre, order by BIC within limits; robust clipping; rms in Å and km/s;
     coverage warning when the lines leave more than 15 % of the range at an end without a line (extrapolation
     shaded on the plot).
  6. Resolution: FWHM of unblended arc lines against wavelength → R(λ) (table, plot, saved with the spectrum; used
     by SPE-11, SPE-16, SPE-17).
  7. Using arcs in time: nearest, or linear interpolation between bracketing arcs (IRAF `refspectra`), and the
     zero point from SPE-8.
  8. Échelle: the same panel per order with the 2-D fit across orders (have `solve_2d`): order chooser, a map of
     residuals over (order, pixel), automatic propagation of identifications to neighbouring orders through the
     grating equation (m λ ≈ constant at a pixel) — the user confirms each newly added order's first matches until
     the 2-D fit is stable.
  9. `dispcor`-like rebinning as an option (linear in λ or in ln λ, flux-conserving, variance propagated).
- **Accept:**
  1. EFOSC2 HeAr, FLOYDS HgAr, TOFES ThAr: automatic proposals from the shipped profiles match the hand solutions
     (rms within 20 %, no wrong line); with the profile's archive removed, the Hough search still finds the solution
     from a ± 15 % dispersion hint on the two long-slit sets.
  2. A synthetic arc at R = 1000 with a quadratic dispersion: recovered with rms < 0.05 px; a deliberately wrong
     accepted line is flagged by the residual plot (> 3σ) and leaving it out restores the rms.
  3. The keys and the candidate popup driven by a QTest; identification of 20 lines by hand takes ≤ 20 key presses
     after the first two.
  4. R(λ) of HARPS from its ThAr within 5 % of the nominal 115 000.
- **Files:** `spectroscopy/wavecal.py`, `linelists.py`, `resources/linelists/` (extended, with SOURCE notes),
  `ui/spectroscopy/panels/identify.py`, tests, guide 08.

### SPE-8. Zero point and flexure  (P1)
**open**
- **Ours now:** `wavecal.sky_shift` (night-sky lines), `sky_shift_orders`, `echelle.drift`.
- **Build:** the zero point of each exposure from, in order of availability: sky emission lines (have; with the
  line list of SPE-7.1 and a robust mean), telluric absorption bands of the object's own spectrum (O₂ A and B, H₂O
  near 7200 Å: cross-correlation with the telluric template of SPE-11), a simultaneous lamp fibre; reported in px,
  Å and km/s with its error; applied as a shift of the solution (never a resampling); a table per night to see the
  flexure against time and hour angle; a warning when none is available and the arc is far in time.
- **Accept:** frames shifted by a known 0.37 px are corrected within 0.03 px from sky lines and within 0.05 px
  from telluric bands (synthetic and the FEROS telluric set).
- **Files:** `spectroscopy/zeropoint.py` (from `wavecal.sky_shift`, re-exported), `tests/test_zeropoint.py`

### SPE-9. Échelle: flat, blaze, orders, merging  (P1)
**open**
- **Read first:** PyReduce's steps (normalised flat and blaze from the slit-function fit of the flat; scattered
  light; continuum normalisation that splices orders using the blaze); the HARPS DRS description; Zechmeister et
  al. 2014; Xu et al. 2019 (AJ 157, 243: alpha-shape continuum fitting for échelle orders).
- **Ours now:** `echelle.find_orders`, `trace_orders`, `scattered_light`, `extract`, `blaze`, `solve_2d`, `merge`,
  `order_number`.
- **Build:** order tracing from flats with edge detection for slit échelles (both edges traced; the order's width
  and tilt known) and centre tracing for fibres; missing / partial orders at the detector's edge handled and named;
  the normalised flat (pixel response only: flat divided by its own smooth model per order from the slit-function
  fit) and the blaze function per order; scattered light as a 2-D smooth surface fitted to inter-order minima
  (have) with a quality picture; extraction by SPE-6; blaze removal by the flat's blaze with a per-order low-order
  correction from the overlaps; merging on a common grid with inverse-variance weights in the overlaps and
  rejection of the noisy order ends; continuum normalisation of the merged spectrum by alpha-shape + local
  polynomial, or per order with continuity across orders; products: per-order spectra (e2ds-like: order × pixel
  arrays with wavelength, flux, variance, blaze) **and** the merged 1-D spectrum.
- **Accept:** in the overlaps of neighbouring orders of TOFES and HARPS the two orders agree within the noise after
  blaze removal (median ratio within 1 %); the merged HARPS spectrum against the DRS `s1d`: ratio flat within 2 %
  over 4000–6800 Å after a low-order polynomial; line depths of the merged solar spectrum against the Kurucz atlas
  convolved to the resolving power within 2 % rms.
- **Depends on:** SPE-6.
- **Files:** `spectroscopy/echelle.py`, `spectroscopy/{blaze,merge}.py`, step `spectroscopy.echelle`, `tests/test_echelle.py`, `tests/validation/test_harps_drs.py`

### SPE-10. Flux calibration  (P2)
**open**
- **Read first:** IRAF `standard`, `sensfunc`, `calibrate` (bandpass tables of standards, the sensitivity function
  fit, grey shifts, extinction); Oke 1990; Hamuy et al. 1992, 1994; Bohlin et al. (CALSPEC); Filippenko 1982 (PASP
  94, 715: atmospheric dispersion and slit losses); extinction curves of observatories (KPNO, CTIO, La Silla,
  Mauna Kea, La Palma).
- **Ours now:** `analysis.response` (ratio of an observed standard to a reference spectrum, spline with line
  masking).
- **Build:** a data pack of standards (CALSPEC, Oke, Hamuy: spectra with their sources; names resolved by SIMBAD
  aliases); extinction curves in `resources/extinction/` (per site; a mean curve scaled by the user's k_V; the site
  profile's own coefficients); `flux.sensitivity(observed standards)`: counts per second per Å corrected to the top
  of the atmosphere, divided by the reference in bands free of strong lines and tellurics, fitted by a spline;
  several standards combined (grey shifts shown; rejection); `flux.calibrate(spectrum)` with exposure, airmass and
  extinction; the result in erg s⁻¹ cm⁻² Å⁻¹ with variance; warnings computed, not guessed: slit not at the
  parallactic angle (the differential-refraction offset between 4000 and 7000 Å at this airmass against the slit
  width), second-order contamination beyond 2 × the blue cut-off without an order filter, narrow slit (relative
  calibration only); absolute scaling to a known magnitude by synthetic photometry (SPE-18).
- **Accept:** two standards at airmass 1.1 and 1.8 give one sensitivity function with residuals < 3 %; a third
  standard reduced with it matches its reference within 5 % in the continuum; the PESSTO flux-calibrated spectra of
  the EFOSC2 set are reproduced in shape within 5 % (stored comparison).
- **Files:** `spectroscopy/flux.py`, data pack, `resources/extinction/`, UI stage, tests, guide 08.

### SPE-11. Telluric correction with a model  (P2)
**open**
- **Read first:** Smette et al. 2015 and Kausch et al. 2015 (Molecfit); Gullikson et al. 2014 (TelFit); Allart et
  al. 2022 (A&A 666, A196: a simple line-by-line model sufficient for high-resolution work); HITRAN 2020 line
  parameters (free to use with citation); the standard atmosphere profiles.
- **Ours now:** `telluric.correct` with an observed standard star.
- **Build:** `spectroscopy/telluric_model.py`: precomputed transmission templates for H₂O and O₂ (and O₃ Chappuis
  as a smooth term) on a fine grid for a standard mid-latitude atmosphere at the zenith, built by a line-by-line
  script from HITRAN (the script lives in `tools/`, its output in a data pack with the HITRAN citation); the model:
  `T(λ) = T_H2O^(a) × T_O2^(b)` shifted and convolved to the spectrum's R(λ) (SPE-7.6), with a (water column
  relative to the template, also giving precipitable water vapour in mm) and b (airmass-like) fitted in windows of
  unsaturated telluric lines with the stellar lines masked or modelled by a template; correction by division with
  a floor on the transmission (regions below it are masked, not divided); the standard-star method stays, improved
  by fitting the hot star's Balmer / Paschen lines with Voigt profiles before using it.
- **Accept:** FEROS telluric set: after correction the residual in the O₂ B band and the 7200 Å water band is < 2 %
  of the continuum outside saturated cores; a synthetic stellar spectrum times a known transmission is recovered
  within 1 % where T > 0.3; the fitted water column correlates with the header's humidity-derived value where
  available (reported, not asserted).
- **Files:** `spectroscopy/telluric_model.py`, `tools/build_telluric_templates.py`, `core/datapacks.py` entry, `spectroscopy/telluric.py`, `tests/test_telluric_model.py`

### SPE-12. The Spectrum job: 1-D tools as IRAF's `splot` and iSpec, on several spectra  (P1)
**open**
- **Read first:** IRAF `splot` help (every key); iSpec's Operations and Parameters menus; specutils' documentation
  (readers and manipulation); Stoehr et al. 2008 (DER_SNR).
- **Ours now:** `analysis.py` (windowed measurements, arithmetic, smoothing, resampling, continuum by points,
  response, BeSS), `spectrum_io.py` (our table, 1-D WCS images, ESO Phase 3), `combine.py`; Spectrum tools tab on
  one spectrum with its own undo list.
- **Build:**
  1. Several spectra open at once: a list (kit `TableView`: name, object, date, range, R, S/N, colour, visible ☑)
     with one **active**; drawn together (overlaid, or stacked with an offset as IRAF `specplot`); operations act on
     the active one or on all ticked ("apply to all").
  2. Readers / writers (`spectrum_io`): 1-D FITS with linear, log and non-linear (IRAF multispec, including
     Chebyshev / Legendre `WAT2` solutions) WCS; binary tables (ours, ESO, SDSS, LAMOST, Gaia RVS / XP sampled, HARPS
     / ESPRESSO `s1d` and `e2ds` with their wavelength keywords); ASCII with a column wizard; BeSS; VOTable; writer
     for each where it makes sense; header units and air / vacuum recognised or asked — never guessed silently.
  3. Operations (each a history entry, undoable, scriptable): crop; resample (linear, log, to another spectrum's
     grid; flux-conserving); smooth (boxcar, Gaussian, Savitzky–Golay); degrade to a resolving power; Doppler shift
     (to the rest frame from a velocity, with the barycentric correction applied or removed); air ↔ vacuum;
     unit conversions (F_λ, F_ν, photons; Å, nm, µm, cm⁻¹); deredden (Cardelli, Clayton & Mathis 1989; O'Donnell
     1994; Fitzpatrick 1999 with E(B−V), R_V); arithmetic between spectra and with constants (IRAF `sarith`);
     combine (have); clean spikes (cosmic-ray residuals) with a local median test; mask regions; add noise (for
     tests); S/N estimate (DER_SNR and from the variance) per region.
  4. Continuum normalisation, interactive: methods polynomial / spline with asymmetric rejection (IRAF `continuum`
     parameters: `low_reject`, `high_reject`, `niterate`, `grow`), running maximum / median filters then a spline
     (iSpec), alpha shape, template-based (divide by a matched synthetic spectrum, fit the ratio), by hand (points
     dragged on the plot: `c` adds a point at the cursor); continuum regions can be drawn (kept as a region file)
     or found automatically; the fitted continuum is drawn over the spectrum before it is applied; for échelle
     orders per order with continuity.
  5. Stacked and trailed views of a time series (flux image: wavelength or velocity around a line against time or
     orbital phase), with the same line's EW and velocity series beside it.
  6. SAMP: send the active spectrum to another program (TOPCAT, Aladin, iSpec, SPLAT) and receive one
     (`astropy.samp`), as iSpec's "Send spectrum to…".
- **Accept:** every reader on a stored file of its kind (ten kinds) round-trips wavelengths to 1e-6 relative;
  `continuum` with the same parameters as IRAF on the EFOSC2 spectrum agrees within 1 % rms (reference stored);
  dereddening equals the `extinction`-package-independent closed forms of the papers at tabulated wavelengths to
  1e-4; a QTest normalises two FEROS spectra with "apply to all" and undoes it; 20 spectra of 300 000 pixels each
  overlay and pan at 30 fps.
- **Files:** `spectroscopy/{spectrum_io,operations,continuum}.py`, `ui/spectroscopy/…`, tests, guide 08.

### SPE-13. Lines: measuring, deblending, lists  (P1)
**open**
- **Read first:** IRAF `splot` (`e`, `k`, `d` deblend, `h`), `fitprofs`; Cayrel 1988 (EW error formula); Vollmann &
  Eversberg 2006; Sousa et al. 2007 (ARES: automatic equivalent widths with local continuum and Gaussian fits) and
  2015; Stetson & Pancino 2008 (DAOSPEC ideas); Gray, *The Observation and Analysis of Stellar Photospheres*
  (bisectors, Fourier analysis of line profiles); Queloz et al. 2001 (bisector span); the Mount Wilson S-index
  definition (Vaughan et al. 1978; Duncan et al. 1991) and Hα indices (Gomes da Silva et al. 2011).
- **Ours now:** `analysis.measure_line` (window, edge continuum, EW with error, centre, flux, one Gaussian or Voigt),
  `v_over_r`.
- **Build:**
  1. Fits of 1–8 components (Gaussian, Lorentzian, Voigt, emission or absorption) with a local polynomial
     continuum, parameters free / fixed / tied (same width, fixed separation — doublets), started by clicks on the
     plot (`d` then clicks, as `splot`); results per component: centre (wavelength and velocity for a rest
     wavelength), FWHM (Å and km/s, instrument-corrected with R), EW, flux, with errors from the covariance and a
     Monte-Carlo option.
  2. A line identification overlay: bundled lists (stellar lines by spectral class, Balmer / Paschen / He, nebular
     lines, telluric bands, night sky, ISM Na D / Ca II / DIBs) shifted by the spectrum's velocity; a click on a
     label starts a measurement there; user lists.
  3. Automatic equivalent widths for a line list (ARES-like): local continuum from the highest points with a
     rejection parameter set from the S/N, line finding by derivatives of the smoothed spectrum, Gaussian fits of
     the blend around each list line, quality flags (blended, weak, strong: EW/λ beyond the linear part); a table
     (TableView) with a small plot of each fit for checking; export in the layouts MOOG / WIDTH / iSpec read.
  4. Profile analysis of a line (or of the mean profile from SPE-14's LSD / CCF): bisector with its velocity span
     and curvature, moments (EW, centroid, variance, skewness), Fourier transform with the first zero for v sin i
     (Gray), V/R for emission lines (have), peak separation, wings' velocities at a given intensity.
  5. Indices: S-index (H and K cores against the R and V bands, with the instrumental calibration left to the user
     as a linear relation they can type or fit from standard stars — said plainly), Hα and Na D indices, Ca IRT;
     Lick indices at their resolution; all as time series for a set of spectra.
  6. Time series of any measurement over the ticked spectra (EW, centre, V/R, index) plotted against BJD / phase,
     to the Light curves window for period search.
- **Accept:** `splot`-style deblend of a synthetic triple blend: each EW within 2 % at S/N 100; automatic EWs of 60
  Fe lines of the solar spectrum (Kurucz atlas degraded to R = 50 000, S/N 200) within 3 mÅ rms of the published
  solar EWs of the line list used; bisector span of a synthetic asymmetric profile within 5 %; v sin i from the
  Fourier zero within 5 % for 10–80 km/s at R ≥ 40 000.
- **Files:** `spectroscopy/{lines,profile_analysis,indices,ew_auto}.py`, UI, `resources/linelists/analysis/`, tests.

### SPE-14. Radial velocities: every method, checked to the instrument's limit  (P1)
**open**
- **Read first:** Tonry & Davis 1979 (the R statistic and error); Baranne et al. 1996 and Pepe et al. 2002 (CCF
  with weighted binary masks); Zucker 2003 (error of a CCF maximum; combining orders); Bouchy, Pepe & Queloz 2001
  (photon-limited precision; quality factor Q); Anglada-Escudé & Butler 2012 and Zechmeister et al. 2018 (template
  matching, SERVAL); Donati et al. 1997 and Kochukhov, Makaganiuk & Piskunov 2010 (LSD); Rucinski 1992, 2002 (BF);
  Zucker & Mazeh 1994 (TODCOR); Wright & Eastman 2014 (barycentric corrections at cm/s; what must be included);
  the IAU radial-velocity standards and Gaia RV standards (Soubiran et al. 2018).
- **Ours now:** `rv.ccf` (ln λ grid, Pearson correlation, parabola, Zucker error, chunk error), `rotate`,
  `mask_emission`, `barycentric_correction`, `sb2.todcor`, `bf.broadening_function`, templates from Pickles /
  PHOENIX / an observed spectrum; step `spectroscopy.rv`.
- **Build:**
  1. `spectroscopy/velocity/` with one interface `measure(spectra, method, template_or_mask, regions, options) →
     table(BJD_TDB, RV, error, FWHM, contrast, BIS, S/N, n_orders, flags)`: `ccf_template` (have), `ccf_mask`
     (weighted box masks; masks built from our PHOENIX grid for F, G, K, M types by selecting unblended lines with
     depths as weights, tool in `tools/`), `template_match` (least-squares shift of a high-S/N template built from
     the star's own spectra, iterated co-adding in the star's frame, per order, with a polynomial continuum term),
     `lsd` (mean line profile from a line mask by regularised least squares; velocities from a Gaussian or a
     rotational-profile fit), `bf` (have), `todcor` (have; plus a grid over the light ratio and template choice),
     `lines` (velocities from identified lines' centres, as `rvidlines`, with the per-line scatter as error).
  2. Peak fitting choices (parabola, Gaussian, rotational profile) and the fit range; the CCF / profile of every
     spectrum is kept and shown (click a table row); telluric and emission regions masked by default; for échelles
     per-order velocities with a weighted mean and the order scatter as an error check (outlier orders named).
  3. Errors: formal (Zucker / Tonry–Davis / covariance), photon-limited prediction (Bouchy's Q) and the scatter
     across orders or chunks; the largest is reported; a systematic floor per instrument profile can be added in
     quadrature (from standard stars).
  4. Barycentric correction: `barycentric_correction` checked against Wright & Eastman's test cases; flux-weighted
     mid-exposure when the header gives one; the site from the header or the profile (have); the reference frame
     named in every table.
  5. Template choice help: from the spectral type (classification or typed) the nearest library / synthetic
     template broadened to the star's v sin i (estimated from the first CCF's width), with the mismatch warning
     kept ("A0 star against a G2 template").
  6. Activity and shape diagnostics per spectrum from the CCF / LSD profile: FWHM, contrast, bisector span.
  7. The Velocities job's table links to the plot of velocities against time / phase; "Fit an orbit" → SPE-15;
     "Send to Models / Exoplanets".
- **Accept:** HARPS τ Ceti series (6 spectra): scatter ≤ 3 m/s with `template_match` and ≤ 5 m/s with `ccf_mask`
  (was 9 m/s), absolute offset from the DRS velocities ≤ 20 m/s; Arcturus from TOFES within 0.3 km/s of the
  catalogue; barycentric correction within 1 cm/s of the published test cases; an SB2 with a published orbit: K1,
  K2 within their errors by TODCOR and by BF; synthetic spectra shifted by known velocities at R = 2000, 20 000,
  100 000 and S/N 20–200: every method unbiased and its error within 0.7–1.4 × the scatter; 100 HARPS spectra with
  the mask method < 60 s.
- **Files:** `spectroscopy/velocity/*.py`, `tools/build_ccf_masks.py`, UI, tests, guide 08 and 13.

### SPE-15. Spectroscopic orbits  (P1)
**open**
- **Read first:** Lucy & Sweeney 1971 (the test for spurious eccentricity); Lucy 2014 (mass function and
  inclination statistics); Fulton et al. 2018 (RadVel's parameterisations); the SB9 catalogue's conventions.
- **Ours now:** `orbit.fit_orbit` (SB1), `fit_sb2`, `sb2_dimensions`, sinusoid start values.
- **Build:** period search on the velocities (GLS with the window, PER engines) when the period is unknown;
  models: SB1, SB2, with per-instrument zero points, a jitter term, linear / quadratic trend; e–ω as √e cos ω,
  √e sin ω; the Lucy–Sweeney test and BIC for circular against eccentric; least squares, then MCMC (EXO-5's
  sampler); derived with errors: K, γ, a sin i, f(m), M sin³ i (SB2), mass ratio, minimum companion mass for a
  given primary mass; phase coverage warnings (gaps > 0.25 in phase; periastron not covered when e > 0.3); the
  velocity curve folded and in time with residuals; combined solutions: with a visual orbit (`models/visual.py`:
  shared P, T, e, ω → inclination, masses and the orbital parallax), with eclipse times, and hand-over to MOD with
  the light curve; tables in SB9 and journal layout.
- **Accept:** synthetic SB1 / SB2 with trends and two instruments' offsets: parameters within 1.5σ in 90 % of 200
  realisations; the published SB2 reproduced within the published errors; Lucy–Sweeney picks e = 0 for circular
  data in ≥ 95 %; MCMC intervals cover the truth at the nominal rate (as OC-8).
- **Files:** `spectroscopy/orbit.py`, UI orbit job, tests.

### SPE-16. Rotation, broadening and line-profile information  (P2)
**open**
- **Build:** v sin i by three independent methods with their validity ranges shown: CCF / LSD width with a
  calibration from artificially broadened templates of the same type and R; Fourier first zero (SPE-13.4);
  template-broadening fit in a region (limb-darkened rotational kernel × instrumental profile × macroturbulence
  as an optional radial-tangential term). The result table lists the three with a note when they disagree by more
  than their errors.
- **Accept:** synthetic PHOENIX spectra broadened to 5–150 km/s at R = 20 000–100 000: each method within 10 %
  inside its stated range and flagged outside it.
- **Files:** `spectroscopy/rotation.py`, `spectroscopy/profile_analysis.py`, `tests/test_vsini.py`

### SPE-17. Atmospheric parameters and classification  (P2)
**open**
- **Read first:** Blanco-Cuaresma et al. 2014 and 2019 (iSpec: grid interpolation, synthesis and EW methods, the
  systematic differences between them); Valenti & Piskunov 1996 (SME); the Gaia-ESO line list paper (Heiter et al.
  2021) for which lines are trustworthy; Gray & Corbally 2014 (MK classification); Casagrande et al. 2010 / 2021
  and Mucciarelli et al. 2021 (colour–Teff relations).
- **Ours now:** `atmosphere.py` (PHOENIX grid, rotational and instrumental kernels, fit of Teff, log g, [Fe/H],
  v sin i, RV with a polynomial continuum; solar reference), `mkstandards.py` (types against the libnor36 standards
  downloaded by the user), `templates.py` (Pickles).
- **Build:** more grids as data packs with their validity (PHOENIX; a hot-star grid; a low-resolution Castelli–Kurucz
  grid for flux-calibrated spectra; white-dwarf models if freely redistributable — each pack's licence checked and
  written); fit regions and masks chosen by spectral type (strong diagnostics: Balmer wings for Teff in A–F stars,
  Mg b and Ca IRT wings for log g, iron-line forests for [Fe/H]) with the user able to edit; uncertainties: formal
  + a systematic floor from our own benchmark runs (SPE-24: Gaia benchmark stars) stated in the result; priors from
  photometry (Teff from colours with the relations above, log g from parallax + magnitude + Teff) offered as a
  cross-check table, never merged silently; the equivalent-width route through SPE-19 when an external code is
  present; classification shown with the best three matches overlaid and the peculiarity notes (have), plus
  emission-line and Be flags.
- **Accept:** for 20 Gaia benchmark stars with public high-resolution spectra: Teff within 150 K, log g 0.3 dex,
  [Fe/H] 0.15 dex (median absolute differences; the table stored and published in the guide's methods chapter);
  the Sun (Kurucz atlas) within 60 K / 0.1 / 0.05; LAMOST spectra: MK types within two subtypes for ≥ 85 %.
- **Files:** `spectroscopy/atmosphere.py`, `spectroscopy/grids.py`, `spectroscopy/mkstandards.py`, `stars/` (photometric cross-check), `tests/validation/test_benchmark_stars.py`

### SPE-18. Synthetic photometry and absolute scaling  (P2)
**open**
- **Build:** filter curves (Johnson–Cousins, SDSS, Gaia, 2MASS, TESS, Kepler; from the SVO Filter Profile Service,
  cached / data pack with citations); `synphot(spectrum, filter)` in Vega and AB systems with errors; scale a
  flux-calibrated spectrum to an observed magnitude; colours from spectra; slit-loss correction factor from
  simultaneous photometry.
- **Accept:** Vega's CALSPEC spectrum gives V = 0.03 ± 0.01 and zero colours within 0.01; synthetic Gaia G of
  three CALSPEC stars within 0.02 of the catalogue.
- **Files:** `spectroscopy/synphot.py`, `services/svo_filters.py`, `models/passbands.py` (shared curves), `tests/test_synphot.py`

### SPE-19. Abundances through external codes  (P3)
**open**
- **Build:** an adapter that finds a user-installed MOOG, Turbospectrum or SPECTRUM (paths in Settings), writes
  their inputs (model atmosphere interpolated from a grid the user provides — MARCS / ATLAS9 — line list, EWs from
  SPE-13.3), runs them in a task, reads the outputs (abundance per line, excitation and ionisation balance plots,
  microturbulence trend); iterative solution of Teff / log g / ξ / [Fe/H] by the balance conditions; everything
  marked "computed by <code> <version>" with its citation; clear messages when none is installed (what it is,
  where to get it, that it is not part of this program).
- **Accept:** with MOOG installed in the test container (from its public source, outside the bundle) the solar EW
  list gives A(Fe) = 7.50 ± 0.05 and flat balances; without it the UI explains.
- **Files:** `spectroscopy/external_rt.py`, `engine/external.py` (AUT-9), `ui/spectroscopy/jobs/parameters/`, tests with a fake executable

### SPE-20. Disentangling in Fourier space  (P3)
**open**
- **Read first:** Simon & Sturm 1994; Hadrava 1995 (KOREL); Ilijić et al. 2004 (FDBinary); Pavlovski & Hensberge
  2010 (normalisation of disentangled spectra).
- **Ours now:** shift-and-add (`disentangle.py`).
- **Build:** Fourier disentangling on ln λ with the orbital elements free (optimised by simplex + MCMC) or fixed;
  time-dependent light ratios (eclipses) when a light-curve solution exists; renormalisation of component spectra
  with light ratios; hand-over of the components to SPE-17.
- **Accept:** synthetic SB2 series: component spectra within 1 % rms and K1, K2 within 1 % without start values
  closer than 20 %.
- **Files:** `spectroscopy/disentangle_fourier.py`, `spectroscopy/disentangle.py`, `tests/test_disentangle.py`

### SPE-21. Slitless spectra (objective gratings, Star Analyser)  (P2)
**open**
- **Reference:** RSpec, BASS and ISIS slitless modes; the Star Analyser manual.
- **Build:** the zero order as the wavelength origin (found by brightness and shape, or clicked); the first order
  rotated to horizontal by its own angle; extraction with a local sky; dispersion from two known features (e.g.
  zero order + Hβ) or from a calibration star, non-linear term optional; response from an A star against a library
  spectrum; many stars in one field (each star's spectrum by its zero order, overlaps flagged); quick
  classification by template match (as a suggestion).
- **Accept:** a synthetic slitless frame with three stars gives each spectrum with wavelengths within 1 px; the
  real Star Analyser frame of an A star shows the Balmer lines within 10 Å of their wavelengths.
- **Files:** `spectroscopy/slitless.py`, step `spectroscopy.slitless`, `ui/spectroscopy/jobs/longslit/` (slitless mode), `tests/test_slitless.py`

### SPE-22. A night, a series: one recipe applied to many frames  (P1)
**open**
- **Build:** after one science frame is reduced to the user's satisfaction, "Apply to all science frames of this
  configuration": traces re-centred per frame, the nearest arcs' solutions with each frame's zero point (SPE-8),
  the same extraction and calibration options; a results table (file, object, BJD, S/N, zero point, rms, flags)
  with thumbnails; failures listed with reasons, never stopping the batch; the outputs feed the Velocities job at
  once; recipe export (ARC-12).
- **Accept:** the six HARPS τ Ceti frames and the FEROS AI Phe series reduce in one run and their velocities come
  out as in SPE-14's accept; a deliberately broken frame is listed and skipped.
- **Files:** `spectroscopy/batch.py`, step `spectroscopy.night`, `ui/spectroscopy/panels/batch.py`, `tests/test_spectroscopy_batch.py`

### SPE-23. Echelle extras: simultaneous reference, combs, drift  (P2)
**open**
- **Build:** simultaneous-lamp fibre drift per exposure (have `drift`) applied to the science fibre; Fabry–Pérot and
  laser-comb calibration frames used to refine the solution between ThAr anchors (peak finding, mode numbering from
  the anchor solution, a smooth correction); sky fibre subtraction scaled by the fibres' throughput ratio from
  flats.
- **Accept:** a synthetic etalon exposure lowers the solution's rms by the expected factor; HARPS frames with the
  simultaneous ThAr reproduce the DRS drift within 1 m/s.
- **Files:** `spectroscopy/{drift,comb}.py`, `spectroscopy/echelle.py`, `tests/test_comb.py`

### SPE-24. Validation of the whole area  (P1)
**open**
- **Build:** `tests/validation/test_spectroscopy_*.py` with stored references: IRAF `apall` + `identify` + `dispcor`
  on the EFOSC2 night (scripts in `tests/validation/scripts/`): extracted counts within 1 %, wavelengths within
  0.1 px; HARPS against the DRS (have numbers → tests); TOFES solar lines against the Kurucz atlas; PESSTO and LCO
  FLOYDS pipeline products; the amateur eShel night against its ISIS product; radial-velocity standards; the Gaia
  benchmark stars table of SPE-17. A page in the guide's methods chapter with these numbers.
- **Accept:** `pytest -m validation` covers every reduction path and velocity method with real data.
- **Files:** `tests/validation/test_spectroscopy_*.py`, `tests/validation/scripts/iraf/spec_*.cl`, `tests/validation/data/spectroscopy/`, guide 13

### SPE-25. IFU cubes  (P3)
**open**
- **Ours now:** `cube.py` (window images, line maps, spaxel spectra), memory-mapped.
- **Build:** moment maps (flux, velocity, dispersion) from Gaussian fits per spaxel with S/N masking (threads /
  native); regions' spectra with the Spectrum job; continuum subtraction; cube formats of MUSE, KCWI, MaNGA
  recognised (variance and DQ extensions used); position–velocity cuts.
- **Accept:** a synthetic rotating disc cube gives the velocity field within the errors.
- **Files:** `spectroscopy/cube.py`, `spectroscopy/cube_maps.py`, `ui/spectroscopy/jobs/cube/`, `tests/test_cube.py`

### SPE-26. Reports and archive formats  (P3)
**open**
- **Build:** figures (spectrum with line labels; time-series stacks; velocity curves) through `ui/plot/publish`;
  tables of velocities and line measurements; FITS products with the IVOA Spectrum / ESO Phase 3 keywords; BeSS
  (have) and the AAVSO spectroscopy database layout (read its current requirements); ARAS conventions; methods
  text (ARC-11).
- **Accept:** a BeSS file passes BeSS's own header rules (checked by a validator written from its specification);
  the AAVSO file's header matches the published requirements.
- **Files:** `spectroscopy/report.py`, `spectroscopy/spectrum_io.py` (archive keywords), `spectroscopy/analysis.py` (`write_bess`), `resources/methods/spectroscopy_*.txt`, tests

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

Before 2026-11-09 (agent2; notes in `docs/history/spectroscopy-plan-2026-11-08.md`): step 0 combine exposures
(`spectroscopy.combine`); steps 1.1, 1.2, 1.4 of the first window layout (job buttons, the 2-D frame above the
plots, the "In what order?" text into tooltips).
