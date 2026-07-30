# Images
The **Images** page shows a FITS image, its header and coordinates, and runs image operations.

## Opening and viewing
- **File → Open FITS…** (or the Start page) opens `.fits`, `.fit`, `.fts` and their `.gz` versions. A file with several images (multi-extension FITS: mosaic cameras, HST/JWST products) asks which one to show; that image is saved as a file of its own next to the original (`<name>_<EXTNAME>_<n>.fits`, the primary header's keywords kept) and opened, so every tool — header editing, processing, plate solving, photometry — works on it. The original file is not changed.
- **Any kind of image:** besides FITS, **File → Open FITS…** opens camera raw files (CR2, NEF, ARW, DNG, …) and ordinary pictures from a phone or a camera (JPEG, PNG, TIFF, BMP, WebP). They get a FITS copy in a folder *fits_from_raw* next to them (made once), with the time, exposure and ISO from the file; colour pictures become one brightness image. The same works on every page that asks for images (Photometry, Blink, Variable-star search, Calibrate, colour image, processing). JPEG and other 8-bit pictures are processed by the camera and not linear: good for viewing, stacking and positions, not for accurate photometry — use raw files for that. Files (and a project) can also be dragged onto the window to open them.
- **Many images at once:** choose several files (Ctrl or Shift) in **File → Open FITS…** — 200 or 1000 are fine. They are listed with small pictures beside the image; click one, use the arrow keys in the list, or **View → Previous / Next image** (Page Up / Page Down over the image) to step through them. Only the image on the screen is read, so memory does not grow with the number of files. **File → Close image** (Ctrl+W) or **Close all images** takes them out of the list; the files are not touched. The small icons above the image are short cuts to the menus: open, save, previous / next, fit and zoom, levels and colours, blink, overlays, processing and plate solving.
- Mouse wheel or **View → Zoom in / out**; **F** fits the image to the window. Drag to pan.
- The status bar shows the pixel (FITS convention: the first pixel is 1, 1), its value and, when the image has a WCS, its RA and Dec.
- The table beside the image lists every header keyword with its value and comment.
- **Right click on the image** opens a menu for the star or place under the mouse: *Measure this star*, *Photometry: this star as the target* (the open images go to the Photometry page with this star marked; mark it on the first image in time), *Photometry: add as a comparison star*, *Copy the position* (pixel and, on a plate-solved image, RA and Dec), *Look up in SIMBAD* (opens the browser; plate-solved image), *Centre the view here*, *Zoom to fit* and *Statistics of the whole image*.
- **Pages beside the image:** right-click a page in the sidebar and choose **Show beside the image** (or tick it in **View → Panels beside the image**): the page becomes a panel next to the image, as MaxIm DL's tool windows — e.g. Photometry or the light curve while you look through the images. Drag its title bar to move it to another side, out as a window of its own, or onto another panel to make tabs. Clicking the page in the sidebar brings the panel forward; closing it puts the page back in its place. The panels are opened again at the next start.

## Display stretch
**View → Interval** chooses which values are mapped to black and white: **ZScale** (the usual astronomical choice), **Min–max** or **99.5 %**. **View → Stretch** chooses the curve: Linear, Square root, Logarithmic or Asinh. Faint nebulosity shows best with Asinh or Logarithmic. Only the display changes; the data are untouched.

**View → Display levels and colours…** (Ctrl+L) shows the image's histogram with the black and white levels as two lines: type the levels to stretch by hand, or press **Automatic** to go back to the interval. **Colours** gives false-colour maps (heat, viridis, inferno, magma, cividis, cool, rainbow) that make faint detail and small differences easier to see; **Inverted** shows black stars on a white sky, as on printed charts.

## Overlays: contours, grid, catalogues, DS9 regions
**View → Overlays** draws over the image (a new image clears them):

- **Contours…** — lines of equal brightness, spaced logarithmically from 3 σ above the sky to the brightest pixel.
- **Coordinate grid** — lines of constant RA and Dec with labels (the image must be plate-solved).
- **Catalogue stars (Gaia DR3)…** — Gaia stars down to the magnitude you give, labelled with G; **Variable stars (VSX)** — known variables with their names. Both are queried from VizieR (internet) and need a plate-solved image: a quick way to identify the field and to check whether a "new" variable is already known.
- **Asteroids and comets (SkyBoT)** — the known minor planets and comets in the field at the image's mid-exposure time, with their names, from the IMCCE SkyBoT service (internet; plate-solved image with DATE-OBS). Useful to tell a moving object from a new variable, or to find the asteroid you want to measure.
- **Load DS9 regions…** reads a DS9 `.reg` file (circles, boxes, lines, points, texts; image or fk5 coordinates). **Save markers as DS9 regions…** writes the stars marked on the image (e.g. target and comparisons) for DS9 or AstroImageJ.
- **Finder chart…** makes a chart in the AAVSO style (PNG or PDF): black stars on white, coordinate grid, north and east arrows, the target between two ticks and the brightest stars labelled with their V magnitude × 10 without the decimal point (11.2 → 112, from Gaia). It uses the current plate-solved image; with no image open it asks for coordinates and downloads a DSS image of the field (internet).
- **Clear overlays** removes them all.

## Measuring on the image
The buttons above the image choose what the mouse does (as the Information and Graph windows of MaxIm DL, or AstroImageJ's tools). Results appear in the **Information** tab, graphs in the **Graph** tab; right-click the table to export or copy it, and **Export data (CSV)…** writes the numbers behind the graph. As in MaxIm DL, clicking a star or drawing a line or rectangle opens two small floating windows over the image, **Information** (the numbers) and **Graph**; they stay on top, follow every new measurement, can be moved anywhere and closed (the next measurement opens them again). The **⧉** button at the corner of the tabs switches them off: the results then appear in the tabs beside the image.

- **Move:** drag to move the image, wheel to zoom.
- **Star:** click a star. It is re-centred and measured in an aperture with a sky annulus (three rings drawn: aperture, then the left-out gap, then the annulus). You get the centroid (and RA/Dec on a solved image), the **peak pixel** (with a warning when it reaches the saturation level from SATURATE / DATAMAX or the 16-bit limit), the **background per pixel**, the **net counts** in the aperture with their error (and electrons when the header has the gain), the **signal-to-noise**, the **instrumental magnitude** (per second when EXPTIME is known), **FWHM** and **half-flux diameter** (also in arcseconds on a solved image), **ellipticity** and its angle, and the radii. **Aperture radius** 0 (*from the star*) chooses the radii from the star's profile as on the Photometry page; type a radius to fix it (the sky annulus is then 3–3.6 times larger). The graph shows the radial profile.
- **Area:** drag a rectangle: its size, **pixel count, sum of counts** (and electrons), mean, median, standard deviation, robust standard deviation (MAD), minimum and maximum with their positions. The graph is the region's **histogram**, the **profile along x or y** (mean of each column or row) or a **3-D surface**. **Whole image** gives the same for the entire frame.
- **Line:** drag a line: the **pixel values along it** (one sample per pixel, interpolated; **Line width** averages across a wider strip), its length (also in arcseconds) and angle, and on a solved image the separation and position angle on the sky — a ruler for double stars and extended objects.

All positions are in FITS pixels (the first pixel is 1, 1), as in the status bar and other programs.

## Plate solving
**Image → Plate solve** finds the exact sky position, scale and rotation of the image and writes them (WCS) into a copy of the file, which is then opened. It uses **ASTAP** (with one of its star databases) or **astrometry.net** installed on your computer; nothing is sent over the internet. Approximate coordinates in the header (`RA`/`DEC` or `OBJCTRA`/`OBJCTDEC`) make the search fast; without them it can take much longer.

## Image operations
**Image → Process** works on the current image and writes a new file next to it (the name gets a suffix such as `_bin`), which then opens. The coordinates (WCS) are carried over exactly. **Process → Apply to all open images** makes the next operations run on every image in the list (in the background, one task each); each processed copy takes the place of its original in the list, and the originals stay unchanged on disk.

- **Pixel math…** — an expression where `A` is this image and `B`, `C`, … are other images you choose, e.g. `A - 0.95 * B`.
- **Flip left–right**, **Flip top–bottom**, **Rotate 90°**, **Bin 2×2**, **Crop…** (x0 x1 y0 y1, 0-based, end excluded).
- **Rotate by any angle…** (counter-clockwise, about the centre; corners from outside are blank) and **Resample (change the pixel size)…** (factor 2: twice as many pixels across; counts per star are kept). Both keep the WCS.
- **Gaussian smoothing…** (sigma in pixels), **Median filter…** (box size, odd), **Unsharp mask…** (sigma).
- **Remove background gradient…** (box size): fits and subtracts a smooth background, e.g. light pollution or moonlight gradients.
- **Kernel filter…**: 3 × 3 low pass, high pass (sharpen), Laplacian, Sobel edges, vertical or horizontal edges. **Deconvolution (Richardson–Lucy)…**: give the stars' FWHM (measure it with the Star tool) and the number of iterations; the sky level and the total counts are kept, more iterations sharpen more and raise the noise. **Digital development (DDP)**: faint parts stay linear and bright cores are compressed, so a nebula and its stars show at once. **Match the histogram of another image…** gives this image the brightness distribution of a reference (each pixel takes the reference's value at the same rank), e.g. so the frames of a mosaic or an animation look alike. These are for looking at an image; measure on the original.

## Colour image
**Image → Colour image from three filters…** asks for a red, a green and a blue frame (e.g. stacks in R, V, B or r′, g′, B) and a PNG file. The green and blue frames are aligned on the red one, each sky is removed and the channels are balanced, then the asinh stretch of Lupton et al. (2004) is applied to all three together, so bright stars keep their colours instead of turning white. The picture opens when it is ready.

## Asteroids and comets
**Image → Asteroid and comet astrometry…** measures a moving object for the Minor Planet Center. Choose the frames (calibrated and plate-solved), click the object on the first frame, then on the last one; every frame is measured at the position predicted from that motion and re-centred, and its RA/Dec comes from the frame's own plate solution, at mid-exposure UTC. The residual column shows how far each position lies from a straight-line motion: more than about 1″ means a blended star or a poor solution in that frame. Fill in the object (provisional designation, number, or your own name for a new object), your MPC observatory code and the observers, then **Write MPC report (ADES)…**: the file is in the MPC's ADES PSV format, ready to send.

Frames without a plate solution are solved first (ASTAP or astrometry.net must be installed; the pointing and the pixel scale are read from the header); a frame the solver cannot solve is left out and the window says how many.

## Saving
**File → Save FITS as…** writes the current image to a new file; the header is kept and a history line is added.

**File → Save picture (PNG / JPEG / TIFF)…** saves the image as shown (with the levels and colours) for a report or a web page, or, as TIFF, the pixel values themselves (32-bit) for other programs. **File → Convert many images (PNG / JPEG / TIFF)…** does the same for a whole set of FITS files at once (with the current display interval and stretch), e.g. for an animation or a web gallery; the names are kept and nothing is overwritten.

## Editing the header
In the **Header** tab, **Add or change keyword…** sets a keyword (select a row first to change it; values are text, numbers or T / F) and **Delete keyword** removes the selected one. The changes are shown at once and written by **Save a copy with these header changes…** into a new file, which then opens — the original file is never changed. Keywords that describe the data (SIMPLE, BITPIX, NAXIS…, BZERO, BSCALE) cannot be edited, and the FITS standard allows only plain ASCII text (no accented letters).

## Blinking a series
**View → Blink images…** shows the chosen frames one after the other with the same display levels, aligned on the stars, like a blink comparator: asteroids, comets, novae and variables catch the eye. **Play** / **Pause**, the arrows and the slider move through the frames; **Interval** sets the speed.
