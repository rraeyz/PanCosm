# Remote sensing
The **Remote sensing** page analyses satellite and aerial images (Landsat, Sentinel-2, drones) and any multi-band image. It opens in a window of its own (its block on the Start page or the sidebar), with its own menus.

## Opening an image
**Open image…** opens a multi-band GeoTIFF (including Cloud-Optimised GeoTIFF), FITS, JPEG2000 (e.g. Sentinel-2 band files), NetCDF (3 and 4) or HDF5 file. In NetCDF / HDF5 every 2-D variable of the main grid is a band, fill values become blank, and CF latitude / longitude coordinates give the map position (products are then written as GeoTIFF with that position). JPEG2000 files are read without their map position. The line under the button gives the number of bands, the size and the map projection. **Show** chooses the band to display; clicking a pixel shows the values of all bands there and its map coordinates. Band files of an ESA Sentinel-2 product (inside its .SAFE folder) are turned into reflectance with the offset and scale of the product's MTD_MSIL2A.xml / MTD_MSIL1C.xml: since processing baseline 04.00 (2022) the stored numbers carry +1000, and indices such as NDVI computed on them would be wrong. Element84 / AWS Sentinel-2 COGs already have the offset taken out and are read as they are. A GeoTIFF scene too large for the computer's free memory is not loaded whole: the page shows it band by band and the operations below read it in strips of rows (same results, somewhat slower).

## Band roles and indices
Tell which band is **BLUE, GREEN, RED, NIR** and **SWIR** in **Band roles**. Then **Index…** offers:

- **NDVI** (NIR − RED) / (NIR + RED) — vegetation;
- **NDWI** (GREEN − NIR) / (GREEN + NIR) — open water;
- **EVI** — vegetation, corrected for soil and atmosphere;
- **SAVI** — vegetation over bright soil (L = 0.5);
- **NDBI** (SWIR − NIR) / (SWIR + NIR) — built-up areas.

## Band math
Type any expression with the band names shown in the **Show** list (e.g. `B1`, `B2`, …) and press **Compute**, e.g. `(B4 - B3) / (B4 + B3)`. Allowed: + − × / and powers, comparisons, and `sqrt`, `log`, `log10`, `exp`, `abs`, `min`, `max`, `where`. Expressions are parsed safely, never executed as code. The statistics of the result (min, median, max, mean ± std) are shown.

## Classification and principal components
- **Classify (k-means)** groups the pixels into the given number of **classes** by their band values (unsupervised): water, forest, fields, towns usually separate well.
- **Principal components** compresses correlated bands into a few new ones; the explained variance of each is listed.

Every product is saved as a GeoTIFF with the georeferencing of the input, so it opens in QGIS on the right place.
