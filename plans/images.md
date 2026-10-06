# Images: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.10).

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

Looking at images and understanding them: any file, any size; display and comparison; inspection tools; image
quality; source lists; regions; processing with a history; colour; annotated pictures and finder charts; exchange
with other programs. (Calibration and stacking engines: `plans/calibration.md`; plate solving and moving objects:
`plans/astrometry.md`; the viewer widget: `plans/architecture.md` ARC-7.)

**Goal:** the inspection power of DS9, IRAF `imexamine` and MaxIm DL's Information window, the processing list of
MaxIm DL and Siril that a scientist needs, and the image-quality analysis of CCD Inspector / ASTAP — in one viewer
where every tool reports into the same Inspector and every operation can be undone and repeated on a hundred files.

## What the reference programs do

Read: SAOImage DS9 reference manual (scales, colour, frames and locks, regions, analysis, catalogues, SAMP); Ginga's
documentation (modes, plugins: Pick, Cuts, Histogram, Contents, Thumbs); IRAF `imexamine` (the keys: `a` aperture
sum and Moffat / Gaussian fits, `r` radial profile, `e` contours, `s` surface, `l` `c` cuts, `h` histogram, `m`
statistics, `j` `k` 1-D fits), `imstat`, `imarith`, `imexpr`, `imhead`, `hedit`; MaxIm DL manual (Information window
modes Aperture / Astrometric / Magnitude / Region / Area; Screen Stretch window; Line Profile; Graph; Process and
Filter menus: flatten background, remove gradient, deconvolve (Lucy–Richardson, maximum entropy), DDP, kernel and
FFT filters, unsharp mask, wavelet filter, bin, resize, rotate, mirror, crop, pixel math, make pixels square,
remove Bayer; Color: combine colour (RGB, LRGB), colour balance, white balance; batch process; FITS header editor;
blink; annotate); Siril (`src/filters/`, `src/algos/`: background extraction with sample points, photometric and
spectrophotometric colour calibration, deconvolution, wavelets, asinh and histogram transformations, star
detection and PSF, image statistics, plate-solve-based annotation catalogues); AstroImageJ's image window
(`astroj/AstroStackWindow.java`: its toolbar, the measure tools, contour and 3-D plots, radial profile "seeing
profile", annotations, header editor); ASTAP (image inspector: HFD and tilt, aberration tiles; photometric
calibration; annotations); photutils (BSD: background, segmentation, `SourceCatalog`, isophotes).

| Topic | DS9 / Ginga | IRAF | MaxIm DL | Siril | AstroImageJ / ASTAP | Ours now |
| --- | --- | --- | --- | --- | --- | --- |
| Formats | FITS (all), mosaics, cubes, tables | FITS, IRAF formats | FITS, TIFF, raw, video | FITS, SER, TIFF, raw, XISF | FITS, TIFF, raw | FITS (compressed, cubes: first plane, extensions chosen), pictures and DSLR raw as FITS copies |
| Scaling | linear, log, power, sqrt, squared, asinh, sinh, histogram; minmax, zscale, percentiles, user | display z1 z2, zscale | Screen Stretch window with histogram and presets | linear, log, sqrt, squared, asinh, auto-stretch, histogram | auto contrast, histogram | interval × stretch choices, levels dialog, colour tables |
| Compare | frames: tile, blink, lock by WCS / image; RGB frames | — | blink, animate | — | stack slider, blink | blink dialog; previous / next |
| Inspect | pixel table, magnifier, panner, cuts, contours, 3-D, region statistics | `imexamine` keys | Information window (5 modes), line profile | PSF of selection, statistics | aperture, seeing profile, measure | Star, Area, Line, Whole image tools: star summary, statistics, profiles, histogram, radial profile, 3-D surface |
| Image quality | — | — | CCD Inspector (separate product) | sequence FWHM plots | ASTAP: HFD, tilt, curvature, aberration tiles | frame quality of a series in Photometry only |
| Source lists | catalogue overlays | `daofind`, `starfind` | — | star finder, PSF list | — | star detection inside photometry |
| Regions | full region language, files | — | annotations | selection | apertures, annotations | DS9 regions read / written (subset) |
| Processing | — | image arithmetic, filters, geometry | long list (above) | long list (above) | image calculator, filters | 16 operations with exact WCS handling; pixel math; RL deconvolution (GPU) |
| Colour | RGB frames | — | RGB / LRGB combine, balance | colour calibration by catalogue | RGB composer, photometric debayer | colour image from three filters; channel split |
| Interop | SAMP, XPA | — | COM scripting | scripts (Python in 1.4) | macros | none |

## What we already have (do not redo)

- `ui/image_page.py` (open many images with a thumbnail list, header table with edit, tools, graph), `ui/viewer.py`,
  `display.py`, `io/fits.py`, `io/inspect.py` (star, area, line, box, histogram), `io/process.py` (flip, rotate,
  resample, bin, crop, Gaussian, median, unsharp, kernels, deconvolve, histogram match, DDP, background polynomial,
  pixel math, colour image), `overlays.py` (contours, WCS grid, catalogue stars, DS9 regions, DSS image, finder
  chart, SkyBoT), `ui/{levels_dialog,blink_dialog,overlay_actions}.py`; menus File, Edit, View, Process, Analyse,
  Overlays, Astrometry, Colour, Stack.

## Decisions

- Images is a viewer, not a workflow: no rail; file strip left, image centre, Inspector right, Graph / Table dock
  below (UI-16.10).
- Every measuring tool writes into one Inspector and can append to one Measurements table.
- Processing never changes a file: operations make a new in-memory image with a history; saving writes a new file
  with provenance.
- Pictures for people (stretch, colour) are kept apart from data for science: a processed picture is flagged in its
  header (`DATATYPE = 'picture'`) and Photometry warns when asked to measure one.

## To ask the owner

- Nothing blocks.

## For the owner to try

- After IMG-W and IMG-3: open one frame, press `a` on a star, `r` for its profile, drag a region; say whether the
  Inspector tells you what MaxIm DL's Information window does.

## Data used

- The calibration and photometry sets; to add: a 9k × 6k CMOS frame and a multi-extension mosaic (speed, ARC-7);
  a frame with strong tilt / curvature for IMG-4 (synthetic + a public example); an RGB set of a nebula for colour.

## Steps

Order of work: IMG-W, then P1: 1, 2, 3, 6, 8, 10; P2: 4, 5, 7, 11, 12, 13, 14, 16, 17; P3: 9, 15, 18.

### IMG-W. The Images window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.10 with `ImageView` (ARC-7).
- **Extra accept:** every one of the 60-odd actions of today's menus has its place (the agent's table under
  UI-16.10); a 9k × 6k frame opens in < 0.5 s; all tools usable with one hand on the keyboard (ARC-7 keys).
- **Depends on:** ARC-4.5, ARC-5, ARC-7, ARC-8, UI-1 … UI-4.
- **Files:** `ui/images/{window,controller,state,menus}.py`, `ui/images/panels/{strip,inspector_info,header,levels,layers,history,graph,table}.py`, `tests/ui/walks/images.py`, guide 05

### IMG-1. Open anything, browse a night  (P1)
**open**
- **Build:**
  1. Readers behind one `images.open(path) → ImageSource` (planes, extensions, variance / DQ when present, header,
     WCS): FITS in every flavour (multi-extension with a chooser and "all extensions as a mosaic by DETSEC"; cubes
     with a plane slider and a "time / wavelength axis" label from the WCS; tile-compressed; `.gz`, `.bz2`, `.Z`;
     scaled integers; 64-bit); XISF (PixInsight's open format: XML header + blocks; read uncompressed and zlib /
     lz4 blocks if a permissive decoder is already bundled, else say what is unsupported); TIFF 8 / 16 / 32-bit and
     float, PNG, JPEG, DSLR raw (have); SER video and FITS cubes as frame sequences (PHO-38's reader); HDF5 / NetCDF
     images through the remote-sensing reader.
  2. The file strip: thumbnails made in a thread pool (cached), with per-file columns in a list mode (type,
     filter, exposure, object, time, FWHM when measured), sortable and filterable; multi-selection for blink,
     stack, batch processing, header edit.
  3. "Follow a folder" (new frames appear and optionally become the shown image — at the telescope).
  4. Tables in files (FITS binary / ASCII tables, ECSV, VOTable, CSV) open in a `TableView` tab with a quick
     scatter / histogram plot of chosen columns (IMG-18 extends it).
  5. Never a raw exception: unreadable or truncated files → `images.unreadable` with what was found (size, first
     bytes' kind) and what to do.
- **Accept:** a folder of 500 mixed files lists in < 2 s (thumbnails follow); each format's stored sample opens
  with the right orientation and values (compared with Astropy / the format's reference reader); a truncated FITS
  says how many bytes are missing.
- **Files:** `images/sources.py`, `io/{fits,xisf,video}.py`, UI file strip, tests.

### IMG-2. Display: the stretch window, colour, comparison  (P1)
**open**
- **Build:** the Inspector's **Levels** tab as MaxIm DL's Screen Stretch: the histogram (log option) with
  draggable black and white points and a midtone slider, numeric fields, presets (zscale, 99.5 %, 99.9 %, min–max,
  "faint detail", "bright detail"), stretch functions (linear, log, square root, power, asinh, histogram
  equalisation), per-image or locked across images; colour tables (grey, inverted grey, perceptually uniform
  sequential ones, a "bad pixel" colour for NaN and for saturated pixels on request); **tiles**: 1–9 images side by
  side locked by pixel or WCS; **blink** in place with a rate and `B`; **RGB display** of three frames with
  per-channel stretch (display only); **before / after** split view with a draggable divider for any processing
  step; a colour bar with units.
- **Accept:** dragging a level redraws in < 50 ms on a 4k frame (visible tiles first); locked WCS tiles of two
  frames with different rotation show the same sky under the cursor within 0.5 px; QTest of presets and blink.
- **Files:** `ui/images/panels/levels.py`, `ui/image/{view,tiles}.py`, `display.py`, `tests/ui/test_image_display.py`

### IMG-3. The Inspector: every question about a pixel, a star, a region  (P1)
**open**
- **Read first:** IRAF `imexamine` help (what each key reports and how: the radial-profile fit, the enclosed-flux
  and direct FWHM definitions); MaxIm DL "Information Window" (the fields of each mode); Howell 2006 (S/N).
- **Ours now:** `io/inspect.py` (`star_info`, `area_stats`, `line_profile`, `box_profile`, `histogram`).
- **Build:**
  1. **Star** (`a`, click): centroid (x, y; RA / Dec), peak, background (mean, σ, the method), net counts (ADU and
     e⁻), S/N, FWHM by three definitions (Gaussian fit, Moffat fit with β, direct half-maximum of the profile),
     ellipticity and position angle from second moments, saturation / linearity flags, instrumental magnitude, and
     — when the frame has a zero point (IMG-5.4) — the calibrated magnitude with its error; the Gaia / VSX identity
     of the star when solved.
  2. **Radial profile** (`r`): points and fitted Moffat / Gaussian, enclosed-energy curve with the radii of 50 %,
     80 %, 95 % light, the three photometry radii drawn when the image came from Photometry.
  3. **Region** (drag; box, circle, ellipse, polygon): n pixels, min, max, mean, median, mode, σ, robust σ, sum,
     the same in e⁻; surface brightness in mag arcsec⁻² with a zero point and scale; histogram of the region.
  4. **Cuts** (`l`, `c`, line tool with width): profile plot with Gaussian fit of a marked feature; distance and
     position angle (arcsec, degrees east of north with a WCS).
  5. **Pixel table** (`p`): 9 × 9 values around the cursor, updating live. **Contours** (`e`) and **surface** (`s`)
     of a box around the cursor.
  6. Every result has "Add to table" (a Measurements table tab: one row per measurement with file, time, tool,
     values; export ECSV / CSV / LaTeX) and "Copy".
  7. All numbers come from engine functions in `images/inspect.py` (no Qt), callable from scripts
     (`astrowb.api.inspect_star(...)`).
- **Accept:** on synthetic stars (Moffat β = 2.5 and 4, known FWHM, S/N 20–500): FWHM within 2 % (Moffat fit),
  centroid within 0.03 px at S/N 100, flux within its error; region statistics equal NumPy on the same pixels;
  `imexamine`'s `a` and `r` outputs on a real frame (IRAF run beside ours, stored) agree within 2 % in FWHM and
  1 % in flux.
- **Files:** `images/inspect.py` (from `io/inspect.py`, old names re-exported), `ui/images/panels/inspector_info.py`, `ui/image/tools.py`, `api/`, `tests/test_inspect.py`, `tests/validation/test_imexamine.py`

### IMG-4. Image quality across the field and through the night  (P2)
**open**
- **Read first:** the descriptions of CCD Inspector's measurements (FWHM map, curvature in per cent, tilt in x and
  y, collimation) and ASTAP's image inspector (HFD in a 3 × 3 grid, tilt, off-axis aberration); N.I.N.A.'s
  aberration inspector plug-in description; Diggs & George / Weber & Brady on half-flux diameter.
- **Build:** `images/quality.py`: detect unsaturated stars over the frame (≥ 100 when available); per star FWHM,
  HFD, ellipticity, angle; maps by a smooth 2-D polynomial fit: FWHM / HFD surface, **field curvature** (centre
  against corners, per cent), **tilt** (the plane term: direction and size in per cent across the sensor),
  ellipticity whisker plot (guiding, astigmatism, coma patterns), a 3 × 3 mosaic of the corners / edges / centre
  crops at 1:1 ("aberration tiles"); background map (gradient direction and amplitude), vignetting profile, noise;
  star count and limiting magnitude (with a zero point); sky brightness. A report card with green / amber marks
  against the equipment profile's expected seeing and scale. For a series: every metric against time (seeing
  monitor), feeding Photometry's Checks (PHO-33) and Observing's graphs (OBS).
- **Accept:** synthetic frames with a known tilt (FWHM 2.0 → 3.0 px across x) and curvature: both recovered within
  10 %; a frame with elongated stars at 30°: mean angle within 3°; 4k frame analysed in < 3 s.
- **Files:** `images/quality.py`, `photometry/quality.py` (uses it), step `image.quality`, `ui/images/panels/quality.py`, `tests/test_image_quality.py`

### IMG-5. Source lists and the frame's zero point  (P2)
**open**
- **Read first:** Bertin & Arnouts 1996 (SExtractor: background mesh, thresholding, deblending, Kron apertures,
  flags); photutils `Background2D`, `detect_sources`, `deblend_sources`, `SourceCatalog` (BSD; may be used);
  Stetson 1987 (DAOFIND).
- **Build:** `images/sources.py`: background and noise maps (mesh with sigma clipping, filtered), detection by
  threshold on the matched-filtered image with deblending, measurements per source (positions with errors, fixed
  apertures and Kron-like automatic aperture fluxes, FWHM, shape, peak, flags for saturated / blended / edge /
  masked, a star-likeness measure from the FWHM–flux locus); output `Columns` table (ECSV, FITS table); overlay
  with ellipses; **cross-match with catalogues** (Gaia and the photometric catalogues of PHO-25) when solved →
  astrometric residuals and the frame's photometric **zero point** with an optional colour term in the frame's
  filter (robust fit, plot of residuals against magnitude and colour) written to the header on request (`MAGZP`,
  `MAGZPERR`, `ZPCAT`) and used by the Inspector (IMG-3.1) and by Astrometry (AST-4).
- **Accept:** on a synthetic field (5000 stars + 200 galaxies-like blobs): completeness > 95 % above 5σ with < 2 %
  spurious; positions within their errors; the zero point of an SA 98 frame within 0.02 mag of the value from the
  Landolt stars alone.
- **Files:** `images/sources.py`, `images/zeropoint.py`, step `image.sources`, `tests/test_sources.py`

### IMG-6. Regions  (P1)
**open**
- **Read first:** the DS9 region file format reference (shapes, coordinate systems, properties, include / exclude,
  composite, text); the IVOA / Astropy `regions` package documentation (BSD; a possible dependency — check wheels
  and size; else our own subset).
- **Build:** draw, move, resize, rotate regions with the tools of ARC-7 (point, circle, ellipse, box, polygon,
  annulus, line, text); properties (colour, width, label, group); read and write DS9 region files in image and sky
  coordinates completely for these shapes (unknown shapes kept and written back untouched); region statistics
  (IMG-3.3) for one or all; regions → mask (DQ user bit) and mask → regions; "apply the next operation inside /
  outside the regions" for processing; regions follow an image through geometric operations by the WCS / the
  transform.
- **Accept:** round trip of a DS9 file with every supported shape in fk5 and image coordinates to 1e-6 px; a mask
  from a polygon equals the exact polygon rasterisation; QTest draws and edits each shape.
- **Files:** `images/regions.py` (from `overlays.py`: `read_regions`, `write_regions` kept as re-exports), `ui/image/tools.py`, `tests/test_regions.py`

### IMG-7. Processing: what a scientist and an imager need  (P2)
**open**
- **Read first:** Starck & Murtagh (the à trous wavelet transform, multiscale denoising); Richardson 1972 and Lucy
  1974, with the damped / regularised variants (White 1994); Lupton et al. 2004 (PASP 116, 133: asinh colour
  images); Siril's documentation of background extraction, colour calibration and the generalised hyperbolic
  stretch (for what users expect).
- **Ours now:** the 16 operations of `io/process.py`.
- **Build:** additions, each an engine function with a kit form and a live preview (IMG-8): background extraction
  with sample points (automatic grid with star rejection + editable points; polynomial 1–4 or radial-basis
  surface; subtract or divide; the model shown); wavelet layers (à trous, 5–6 scales: per-scale gain for
  sharpening, per-scale thresholds for noise reduction); Fourier filter with a view of the power spectrum (notch /
  band filters for pattern noise, banding removal along rows / columns); deconvolution with the image's own PSF
  (ePSF from PHO-18 or a Moffat fit) and regularisation, iterations with a stopping aid (residual noise); local
  contrast (CLAHE written from the paper); hot / cold pixel cosmetic filter (σ against neighbours); replace NaN;
  normalise; clip; add / subtract / scale images (have pixel math; add named presets "A − k·B", "A / B"); align to
  a reference (CAL-15) and reproject to another image's WCS; colour: LRGB combine, background neutralisation, white
  balance by catalogue stars' colours (photometric colour calibration with PHO-25's magnitudes: the fit of
  instrumental against catalogue colours), saturation, green-noise reduction (SCNR), histogram / midtone / asinh
  stretches and curves — the picture-making ones flagged as such in the header (Decisions).
- **Accept:** each operation against an independent NumPy / SciPy statement on small arrays; wavelet transform
  reconstructs exactly; background extraction recovers an injected quadratic gradient within 1 % of its amplitude
  under a star field; colour calibration brings a synthetic RGB star field's colours onto the catalogue relation
  within 0.03 mag; GPU twins (convolution-type operations) equal CPU within 1e-5.
- **Files:** `images/process/{background,wavelets,fourier,deconvolve,contrast,colour,cosmetic}.py` (`io/process.py` re-exports), `compute/convolve.py`, step `image.process` (new operations), `tests/test_process.py`

### IMG-8. History, preview, repeat on many files  (P1)
**open**
- **Reference:** MaxIm DL's batch process and command sequences; Siril scripts; PixInsight's process containers
  and history (as descriptions).
- **Build:** each open image has a history list (operation, parameters, time) in the Inspector: undo / redo by
  clicking an entry (images recomputed lazily from the last kept state; memory capped with on-disk spill of
  intermediate states); every operation's form has a **preview** on the visible region with a before / after
  toggle (≤ 150 ms for filter-type operations on a 1000 × 1000 preview; GPU where a kernel exists); "Apply to the
  selected files…" runs the image's history (or a chosen part) on many files as a task with outputs in a folder
  and provenance; "Save as recipe" (ARC-12) and "Copy as Python".
- **Accept:** a five-operation history applied to 48 frames from the strip gives files identical to applying the
  operations one by one by hand; undo to any entry restores the pixels exactly; memory stays under the cap with a
  9k × 6k image and ten history states.
- **Files:** `images/history.py`, `ui/images/panels/history.py`, `ui/kit/stepform.py` (preview hook), `core/recipe.py`, `tests/test_image_history.py`

### IMG-9. Lucky imaging and planetary stacks  (P3)
**open**
- **Build:** for SER / cube sequences: frame quality ranking (gradient energy in a chosen box), alignment on a
  feature or the planet's limb / centre of brightness, stacking of the best x % with optional multi-point
  alignment; basic wavelet sharpening (IMG-7). Scope kept small: science users (double stars, occultations) first.
- **Accept:** a synthetic seeing-blurred sequence of a double star gives a stack with the pair resolved at the
  expected separation.
- **Files:** `images/lucky.py`, `io/video.py`, tests

### IMG-10. Headers: read, understand, fix  (P1)
**open**
- **Ours now:** header table with add / change / delete, copy, save a copy with changes.
- **Build:** search and filter in the header table; a plain-words summary on top (object, date and mid-time in UTC
  and BJD_TDB when possible, exposure, filter, binning, temperature, telescope / camera, pixel scale, field size,
  rotation and parity from the WCS, calibration state); tooltips explaining standard keywords (a dictionary in
  `resources/headers/dictionary.toml`, four languages); **verify**: FITS standard check (Astropy's verification
  mapped to plain messages: what is wrong, whether it matters, "fix in a copy"); **compare** the headers of two or
  many files (a table of keywords that differ); checksums; batch editing through CAL-23.
- **Accept:** a deliberately broken header (missing END padding fixed by Astropy, non-standard cards, wrong
  `NAXIS`) is reported in words and a fixed copy opens in other programs; compare shows only the differing
  keywords of 48 frames in < 1 s.
- **Files:** `images/header_tools.py`, `resources/headers/dictionary.toml`, `ui/images/panels/header.py`, `tests/test_header_tools.py`

### IMG-11. Annotations and charts  (P2)
**open**
- **Build:** overlays (through `services`, cached): Gaia, VSX / GCVS variables with types and periods, AAVSO
  sequence labels (PHO-25), solar-system objects for the frame's time (SkyBoT; have), deep-sky objects and bright
  stars from SIMBAD / VizieR queries (no bundled catalogue with a share-alike licence), the user's own list (CSV of
  name, RA, Dec); label placement that avoids overlaps; scale bar, compass, field-of-view rectangles of equipment
  profiles (for framing); **finder chart** export improved: AAVSO-style chart (north up or as the eyepiece shows,
  limiting magnitude, comparison labels without decimal points, the target marked), with a DSS / Pan-STARRS
  background fetched for the field when the user's image is not wanted; PDF / PNG through publish.
- **Accept:** the chart of the NY Vir field shows the AAVSO sequence stars with their labels at the right places;
  labels never overlap in a crowded field (a test on label rectangles).
- **Files:** `images/annotate.py` (from `overlays.py`), `images/chart.py` (`finder_chart` moved, re-exported), `services/{simbad,vizier,aavso_vsp,skybot}.py`, `tests/test_annotations.py`

### IMG-12. Talking to other programs  (P2)
**open**
- **Read first:** the SAMP standard (IVOA) and `astropy.samp`; DS9's SAMP / XPA commands.
- **Build:** a SAMP client (off by default, one click to connect to a running hub or start one): send the image,
  a table (source list, measurements), regions, or a sky position to TOPCAT, Aladin, DS9, SPLAT; receive "point at
  this coordinate" (the view centres and marks it) and tables (opened in a `TableView`); "Open in DS9" when DS9 is
  installed (found on the path). The same client serves Spectroscopy (SPE-12.6) and tables everywhere.
- **Accept:** a test with Astropy's hub in-process exchanges an image, a table and a coordinate both ways.
- **Files:** `core/samp.py`, `ui/shell/tools/samp.py`, `tests/test_samp.py`

### IMG-13. Blink, difference, "is this new?"  (P2)
**open**
- **Build:** blink of N frames aligned by WCS or stars (have) inside the main view with keys; an animation export
  (GIF / PNG sequence); **difference**: A − s·B after alignment and flux scaling, optionally with PSF matching
  (PHO-29), shown in a tile; "Compare with a survey": fetch the DSS / Pan-STARRS / SkyMapper cut-out of the same
  field (hips2fits through `services`), reproject, blink / difference; "What is this?" on a clicked position:
  catalogue objects within a radius (Gaia, SIMBAD, VSX, minor planets at the frame's time, known transients from
  the TNS when reachable) in the Inspector — the first questions of a nova or supernova hunter.
- **Accept:** a synthetic new star of magnitude 16 added to a real frame is obvious in the difference with the
  survey cut-out and "What is this?" returns nothing known at its position while a neighbouring catalogue star is
  identified.
- **Files:** `images/compare.py`, `services/hips2fits.py`, `ui/images/panels/compare.py`, `tests/test_image_compare.py`

### IMG-14. Mosaics and cut-outs  (P2)
**open**
- **Build:** the interface to CAL-16's mosaic engine (choose frames, preview footprints on a sky grid, background
  matching, output grid and projection); cut-outs by coordinates and size from one or many images; reprojection to
  north-up.
- **Accept:** a 2 × 2 mosaic of solved frames with 10 % overlap: stars in overlaps coincide within 0.2 px; seams
  below 0.3σ.
- **Files:** `ui/images/dialogs/mosaic.py`, `calibration/mosaic.py` (engine, CAL-16), `images/cutout.py`, tests

### IMG-15. Speed and memory  (P3)
**open**
- **Build:** benchmark cases for opening, display changes, each processing operation on 4k² and 9k × 6k; thread
  pools for per-tile work; memory accounting in the status bar's tooltip.
- **Accept:** the budgets of `plans/architecture.md`.
- **Files:** `tools/speed.py` cases, `ui/image/tiles.py`

### IMG-16. Pictures for papers and talks  (P2)
**open**
- **Build:** "Publication image…": the current view rendered through Matplotlib with WCS axes (RA / Dec ticks and
  grid), scale bar, compass, colour bar with units, regions and labels, an inset zoom, a chosen stretch written in
  the caption helper; journal sizes; PDF / PNG / TIFF.
- **Accept:** the RA / Dec ticks agree with the WCS to 0.1 px; the figure passes the publish checks.
- **Files:** `ui/plot/publish_image.py`, `ui/images/dialogs/publication_image.py`, `tests/test_publish_image.py`

### IMG-17. Colour cameras in the viewer  (P2)
**open**
- **Build:** raw mosaic frames shown as grey (true values), as a quick colour preview (bilinear), or one channel
  at a time (superpixel) with a switch; the Inspector reports per-channel values; hand-over to CAL-17 for
  calibration and to Photometry per channel.
- **Accept:** channel views equal `io/bayer.split` results; the preview never changes data on disk.
- **Files:** `ui/images/panels/cfa_view.py`, `io/bayer.py`, tests

### IMG-18. Tables as first-class citizens  (P3)
**open**
- **Build:** a light TOPCAT: open any table file, compute a new column by expression, select rows by expression or
  by lasso in a plot, scatter / histogram / density plots of columns with colour by a third, cross-match two tables
  by sky position or key, send / receive by SAMP; all on `core/table.Columns`.
- **Accept:** a 10^6-row Gaia cone table: load < 3 s, a density plot < 0.5 s, cross-match with a 10^4-row table by
  position < 2 s.
- **Files:** `core/table.py`, `ui/shell/tools/table_tool.py`, `core/crossmatch.py`, `tests/test_table_tool.py`

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md` and `docs/history/interface-plan-2026-11-08.md` I6c.8)
