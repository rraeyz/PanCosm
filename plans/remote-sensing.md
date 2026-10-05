# Remote sensing: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.13).

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

Images of the Earth from orbit handled with the same tools as images of the sky: open satellite products, show
them as maps, compute indices and band formulas, classify, compare dates, measure areas, and export georeferenced
results. This area comes last in the roadmap (PLAN.md §5); its scope is deliberately modest and exact.

**Goal:** the everyday tasks of SNAP and QGIS (with its classification plug-in) for a student or a researcher who
needs an index map, a land-cover classification with its accuracy, or a change map — without installing a
geographic information system, and on a laptop with 8 GB of memory.

## What the reference programs do

Read: the SNAP documentation (product readers, resampling, subset, reprojection, band maths, masks, RGB windows,
spectrum view, k-means and other classifiers, collocation, mosaicking); the QGIS documentation (raster styling,
raster calculator, processing toolbox, zonal statistics) and the Semi-Automatic Classification Plugin's manual
(Congedo 2021: training inputs, spectral signatures, minimum distance / maximum likelihood / spectral angle
classifiers, DOS1 atmospheric correction, accuracy assessment); GDAL / rasterio documentation (warp, translate,
overviews; MIT / BSD licences); the Sentinel-2 and Landsat Collection 2 product guides (scale factors, quality
bands); Congalton 1991 (accuracy assessment); Chavez 1996 (dark-object subtraction).

| Topic | SNAP | QGIS + classification plug-in | Ours now |
| --- | --- | --- | --- |
| Products | Sentinel, Landsat, many readers | anything GDAL reads | GeoTIFF / COG (tifffile), FITS, HDF5 / NetCDF, Sentinel-2 SAFE reflectance, JPEG 2000 bands |
| Display | RGB and single-band windows, stretch, masks, spectrum view, pixel info | layers, styling, transparency, map tools | image view with pixel read-out and UTM → lon / lat |
| Geometry | resample, subset, reproject, collocate, mosaic | warp, merge, clip | georeferencing tags copied to products; no reprojection |
| Radiometry | sensor-specific calibration, Sen2Cor (external) | DOS1, conversion to reflectance | Sentinel-2 quantification and offsets |
| Maths | band maths with masks | raster calculator | safe expression evaluator, index presets, statistics |
| Classification | k-means, EM, random forest, maximum likelihood… | minimum distance, maximum likelihood, spectral angle; ROI tools; accuracy assessment | k-means (GPU twin), PCA |
| Change / time | time-series tool | post-classification comparison | difference with a threshold |
| Vectors | shapefile import, masks from geometry | full vector layers, zonal statistics | none |
| Output | many formats, map export | print layouts | GeoTIFF with tags kept |

## What we already have (do not redo)

- `remotesensing/raster.py` (`Raster`, `Scene`, readers, block-wise rows, `write` with tags), `analysis.py`
  (`evaluate`, `index_expression`, `statistics`, `kmeans`, `pca`, `change`, `pixel_spectrum`), steps
  `remotesensing.{expression, classify, pca}`, `compute/classify.py`, `ui/rs_page.py`; checked: NDVI identical to
  NumPy on a Sentinel-2 tile; UTM → lon / lat.
- Known weakness (history, second test round): 9.3 GB of memory on a two-band Sentinel-2 tile because the window
  and the worker each held full copies.

## Decisions

- Nothing is ever loaded whole: display from reduced-resolution levels, computations block by block (RS-1).
- Geometry operations use rasterio (BSD; bundles GDAL, MIT) **if** its wheels exist for all five targets and the
  installer stays within the size budget (ARC-20) — the agent of RS-3 measures and writes the result here; if not,
  reprojection is limited to what pyproj + our own resampling can do on GeoTIFFs, and the guide says so.
- No online base maps by default (tile services' usage policies); the user's own rasters are the map.

## To ask the owner

- Which sensors and tasks matter to the owner (land cover? vegetation indices? night lights for observing sites?):
  it orders RS-5 … RS-11.

## For the owner to try

- After RS-W and RS-2: open a Sentinel-2 scene of your region, show true and false colour, compute NDVI; say
  whether memory or speed is a problem on your machine.

## Data used

- A Sentinel-2 L2A tile (from the history; add `SOURCE.md` under `data/remote-sensing/`); to add: a Landsat 8 / 9
  Collection 2 scene pair of one place at two dates (change detection; a burn scar with a published severity map if
  available); a small scene with public ground-truth land-cover polygons for accuracy tests; reference outputs made
  with GDAL command-line tools installed in the test container.

## Steps

Order of work: RS-W, then P1: 1, 2, 5; P2: 3, 4, 6, 7, 8, 12, 13, 14; P3: 9, 10, 11.

### RS-W. The Remote sensing window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.13: bands and layers left, the map centre, tools as stages right, histogram / pixel
  spectrum / statistics below.
- **Extra accept:** open a scene → true colour → NDVI → classes: **five clicks**; memory of the interface process
  stays below 1.5 GB with a full Sentinel-2 tile open.
- **Depends on:** ARC-4.6, ARC-5, ARC-7, ARC-8, UI-1 … UI-4, RS-1.

### RS-1. Products, bands and memory  (P1)
**open**
- **Read first:** the Sentinel-2 product specification (SAFE layout, band resolutions, `BOA_ADD_OFFSET`, the scene
  classification layer); the Landsat Collection 2 Level-1 / Level-2 guides (MTL metadata, scale factors,
  `QA_PIXEL` bits); the Cloud-Optimised GeoTIFF layout (overviews, tiles); CF conventions for NetCDF grids.
- **Build:** product recognisers that set band roles (coastal, blue, green, red, red edge 1–3, NIR, narrow NIR,
  water vapour, cirrus, SWIR 1–2, thermal, pan), wavelengths, resolutions, scale / offset to reflectance or
  temperature, no-data, and quality layers → masks (cloud, shadow, snow, water, saturated): Sentinel-2 L1C / L2A
  (SAFE folder or zip), Landsat 8 / 9 C2 L1 / L2 (folder with MTL), generic GeoTIFF / COG stacks (roles asked once,
  remembered by file-name pattern), NetCDF / HDF grids (have); a `Scene` is lazy: every band a windowed reader;
  **pyramids**: reduced-resolution levels from the file's own overviews or built once into a cache beside the
  project (block-wise) for display and for sampling-based statistics; one memory budget for the window and the
  worker (Settings → Processing), with block sizes derived from it.
- **Accept:** a full Sentinel-2 tile (13 bands) opens in < 3 s and pans at 30 fps; peak memory of any operation in
  this file on that tile < 2 GB (measured by `tools/speed.py` cases); each recogniser passes on a stored product
  skeleton (metadata files + tiny synthetic bands).
- **Files:** `remotesensing/{products,raster,pyramid}.py`, tests.

### RS-2. The map  (P1)
**open**
- **Build:** on `ImageView` (ARC-7): single band with a colour table and legend; RGB composites with presets per
  sensor (true colour, colour-infrared, SWIR / agriculture, urban) and free choice; per-band percentile stretch
  (2–98 % default) from pyramid statistics, gamma; layers list with visibility, opacity, order; masks as overlays;
  swipe and blink between two layers / dates; read-out: lon / lat, projected coordinates with the CRS name, pixel,
  band values in physical units; pixel-spectrum plot against wavelength under the cursor or for a drawn region
  (mean ± σ); geographic grid, scale bar (metres), north arrow; measure distance and area (geodesic, pyproj).
- **Accept:** coordinates under the cursor agree with GDAL's (`gdallocationinfo`, stored) to 0.01 px; a measured
  polygon's area agrees with the geodesic formula within 0.1 %.

### RS-3. Geometry: put rasters on one grid  (P2)
**open**
- **Build:** stack bands of different resolution on a chosen grid (10 / 20 / 60 m Sentinel-2) with nearest /
  bilinear / cubic / average resampling; subset by extent, by pixel window, by polygon; reprojection to another
  coordinate reference system; mosaic of adjacent tiles with feathering or first / last / mean rule; align one
  raster to another's grid (for change detection); all block-wise with overviews written; engine per Decisions.
- **Accept:** results equal `gdalwarp` references (stored statistics and 1000 sampled pixels) within the
  resampling's rounding; a two-tile mosaic's seam has no step in a flat area; memory budget kept.

### RS-4. Radiometry  (P2)
**open**
- **Build:** Landsat: digital numbers → top-of-atmosphere reflectance (with Sun-elevation correction) and
  brightness temperature from the MTL coefficients; Level-2 scale factors applied; Sentinel-2: have; DOS1
  dark-object subtraction (Chavez 1996; as the classification plug-in implements the idea: the dark value per band
  from the histogram's low tail, path radiance removed) clearly labelled as approximate; a note in the guide on
  Sen2Cor and Level-2 products as the better choice; cloud / shadow masking from the quality layers applied to
  every later computation by default.
- **Accept:** TOA reflectance of a Landsat scene equals the values computed by an independent script from the
  USGS formulas at 1000 pixels to 1e-6; DOS1 brings a synthetic haze offset back within 5 %.

### RS-5. Indices and band maths  (P1)
**open**
- **Ours now:** safe evaluator, a few index presets, block-wise evaluation, GeoTIFF output.
- **Build:** an index library as data (`resources/indices.toml`: name, formula by roles, reference, value range,
  what it shows, a suggested colour table): NDVI, EVI, EVI2, SAVI, MSAVI, GNDVI, NDRE, ARVI, NDWI (McFeeters),
  MNDWI, NDMI, NDBI, BSI, NBR, NBR2, NDSI, and the tasselled-cap brightness / greenness / wetness per sensor;
  the formula editor with band names offered, live validation, a preview on the visible area; masks from
  expressions (thresholds) and their areas; statistics of an index (histogram, percentiles) for the scene, the
  view or a polygon; unit and range checks (reflectance expected: a warning when digital numbers are used).
- **Accept:** each library index equals a NumPy statement of its formula; NDVI of the stored tile unchanged from
  today; the preview updates in < 300 ms.

### RS-6. Classification with a measure of its quality  (P2)
**open**
- **Read first:** Richards, *Remote Sensing Digital Image Analysis* (minimum distance, maximum likelihood,
  spectral angle; training and testing practice); Congalton 1991 and Olofsson et al. 2014 (accuracy assessment and
  area estimation); Tou & Gonzalez (ISODATA).
- **Ours now:** k-means on a sample with GPU nearest-centre assignment.
- **Build:** unsupervised: k-means (have) with k chosen by an elbow / silhouette aid on the sample, ISODATA;
  supervised: training polygons drawn on the map per class (regions of IMG-6) or imported (RS-8), signatures plot
  (mean ± σ per band per class) and separability (Jeffries–Matusita) table; classifiers written by us: minimum
  distance, maximum likelihood (Gaussian, with priors and a rejection threshold), spectral angle mapper;
  block-wise prediction (GPU twin for the distance computations); post-processing: majority filter, sieve of small
  patches; **accuracy**: independent validation polygons or a random split → confusion matrix, overall /
  producer's / user's accuracy, kappa, with confidence intervals; class areas with units; outputs: class raster
  with a colour table and legend, the probability / distance rasters on request, the report.
- **Accept:** on a synthetic scene of five Gaussian classes: maximum likelihood reaches the Bayes accuracy within
  1 %; on the public ground-truth scene the accuracy table is produced and matches an independent computation of
  the same predictions; a full tile classified in < 3 min CPU within the memory budget.

### RS-7. Change and time  (P2)
**open**
- **Build:** two dates on one grid (RS-3): difference and ratio of an index with thresholds chosen on the
  histogram; dNBR burn severity with the USGS class limits; post-classification comparison (from–to matrix and
  map); change vector magnitude; **time series**: a folder of scenes → an index stack with cloud masks → the
  series for a point or polygon (mean, median, percentiles) as a `PlotView` with gaps for cloudy dates, a simple
  seasonal / trend decomposition, export; an animation of the map through time.
- **Accept:** synthetic two-date scenes with a known changed area: the area recovered within 2 %; the series of a
  synthetic seasonal signal with clouds: masked dates left out, amplitude within 5 %.

### RS-8. Vectors and zones  (P2)
**open**
- **Build:** read GeoJSON, shapefiles (a small permissively licensed reader, or rasterio's when present) and KML
  polygons / lines / points; draw and edit polygons; attribute table (`TableView`); zonal statistics of any raster
  per polygon (mean, median, σ, area above a threshold) → table and choropleth-like display; export of drawn
  features as GeoJSON; polygons as masks and as training / validation inputs for RS-6.
- **Accept:** zonal means equal an independent rasterised computation; a shapefile in a different CRS overlays
  correctly (reprojected with pyproj).

### RS-9. More transforms  (P3)
**open**
- **Build:** PCA (have) with loadings table and scree plot; minimum noise fraction; linear spectral unmixing with
  user endmembers (non-negative least squares) and residual map; pansharpening (Brovey, Gram–Schmidt) for sensors
  with a panchromatic band.
- **Accept:** unmixing recovers synthetic abundances within 3 %; pansharpened bands keep the multispectral means
  within 1 %.

### RS-10. Thermal  (P3)
**open**
- **Build:** land-surface temperature from Landsat's thermal band by the single-channel method with emissivity
  from NDVI (Sobrino et al. 2004), clearly labelled with its assumptions; Level-2 surface-temperature products
  read directly as the better choice.
- **Accept:** against the Level-2 surface temperature of the same scene: median difference within 2 K (reported).

### RS-11. A bridge to astronomy: night lights and observing sites  (P3)
**open**
- **Build:** open a night-time lights raster the user provides (the VIIRS day / night band composites or a sky-
  brightness atlas, each under its own licence) and read radiance / brightness at the site profiles' positions and
  over the years (a trend plot) — a quick look at light pollution for site selection; no data are bundled.
- **Accept:** the read-out at a coordinate equals GDAL's; a site list produces a table and trend plot.

### RS-12. Speed and memory  (P2)
**open**
- **Build:** benchmark cases (`tools/speed.py`) for open, composite, index, PCA, k-means, classification on a full
  tile; one copy of the data policy checked by a memory test (window + worker); thread pool over blocks; GPU twins
  where measured faster.
- **Accept:** no case above 2 GB peak; index on a full tile < 15 s; k-means < 40 s; all equal the pre-change
  results.

### RS-13. Maps and exports  (P2)
**open**
- **Build:** export products as GeoTIFF / COG with overviews, colour tables and proper tags; a map layout through
  the publish layer (title, legend, scale bar, north arrow, coordinate grid, credit line with the data source's
  required attribution); class statistics tables; KML ground overlays for quick viewing elsewhere; the methods text
  (ARC-11) naming the product, processing level and every operation.
- **Accept:** exported rasters open in QGIS with the right place and legend (checked through GDAL's metadata dump
  in tests); the map layout carries the attribution of the product.

### RS-14. Validation  (P2)
**open**
- **Build:** `tests/validation/test_remote_sensing_*.py` with references from GDAL tools (installed in the test
  container, outside the bundle) for geometry, from independent scripts for radiometry and indices, and the
  ground-truth scene for classification.
- **Accept:** every capability above has a validation test.

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
