# Photometry
The **Photometry** page measures the brightness of a target star relative to comparison stars on a series of calibrated images and gives a light curve, times of minimum and reports. Its **Workflow** line at the top (click to open) lists the steps as with IRAF phot or AstroImageJ, each marked done or next, with what to do next.

## Choosing images and stars
1. **Choose images…** — calibrated frames of one field and one filter. They are sorted by time.
2. On the first image, **click the target star**, then **one or more comparison stars**. Clicks snap to the star's centre. **Clear stars** starts again.
3. Or press **Suggest comparison stars**: it picks stars of similar brightness, not saturated, without bright neighbours and inside the frame in every image. Check them before measuring.

Good comparison stars have a similar colour and brightness to the target and are not variable. Use several: their sum (an ensemble) is less noisy than one star.

Over the image the pointer is a cross, and the aperture and sky-annulus rings that the next click will place follow it, in the colour of the star it will mark (green target, red comparison, orange check star). A click on a star that is already marked takes it off. Drag to move the image, wheel to zoom.

**Every frame:** the arrows and the slider under the image count go through the frames in time order, with each frame's name and time. Mark the stars on whichever frame looks best: that frame holds the positions, and the measurement carries them to the others (the shift between frames is measured, every star re-centred). The marked stars are drawn on that frame only. Untick **Use this frame** to leave a frame out (clouds, a satellite trail, a bad focus). All frames are also listed under it, as in MaxIm DL: name, mid-exposure time (UTC), and the FWHM and sky once **Find the bad frames** has run (bad frames in red); click a row to show that frame, untick it to leave it out. **Blink** shows the frames in use one after the other at the same zoom — a passing cloud, a satellite trail or a jump in the pointing catches the eye at once. **Leave out the bad frames** unticks them; a tick brings one back.

TESS and Kepler / K2 target pixel files, also TESScut cut-outs from MAST, can be chosen as they are: every cadence becomes a frame (cadences the mission flags as useless are left out) with the archive's BJD_TDB. With no atmosphere to divide out, the target can be measured **without comparison stars**: the relative flux is then the target's own flux over its median. The errors come from the archive's noise per pixel (FLUX_ERR): in an 11 × 11 px file the sky ring holds the star's wings and its neighbours, and their scatter is not noise. Rings too large for such small frames are replaced by radii chosen from the stars, and the page says so.

## Differential photometry: targets, comparison and check stars
**Clicks add** chooses what the next clicks are: *target, then comparison stars* (the first click is the target T1, the next ones comparison stars C1, C2…), *check stars* (K1, K2…) or *more targets* (T2, T3…). Check stars and further targets are measured on every frame against the same comparison stars but are not part of them — as the check star of MaxIm DL, VPhot or AIJ. A constant check star shows how good the photometry really is: its scatter (in mmag) is listed under the plot.

The **Stars** tab lists every star with its role and position. Type the comparison stars' **known magnitudes** (from an AAVSO chart, a catalogue or your own calibration) into the last column: the target, the other targets and the check stars then get **magnitudes** frame by frame (each comparison star gives a zero point; a comparison star that disagrees by more than 0.1 mag is left out and named). **Standard magnitudes (APASS / Gaia)** fills the same column from the catalogues.

**Weight comparison stars by their scatter:** each comparison star is measured against the sum of the others and weighted by the inverse of its variance (repeated, so a variable comparison star cannot spoil the others' scatter). A variable or disturbed comparison star then hardly counts.

The **Plot** tab chooses what is drawn: T1 relative flux, its differential magnitude Δm = −2.5 log(target / ensemble), its magnitude, each further target or check star, **the comparison stars against the others** (a variable one stands out), **all stars normalised and offset**, or airmass, sky, FWHM and position against time. Frames where a star reaches the saturation level are circled red and counted.

## Frame quality
**Find the bad frames (clouds, focus, trails)** measures every chosen frame: the size of the stars (FWHM), how many stars are seen and the sky level. The plot shows the three through the night; frames far worse than the night's typical frame are marked red, with the reason — *stars blurred* (wind, focus, seeing), *few stars* or *no stars* (clouds, dew), *bright sky* (twilight, Moon). **Leave out the bad frames** removes them before measuring. The *Eclipsing binary night* and *Exoplanet transit* automations do this by themselves.

## Apertures
Every star gets three rings, drawn on the image: the **aperture** (solid), and the inner and outer edge of the **sky annulus** (dashed). The radii are in image pixels, so the rings grow and shrink with the zoom: zoom in to see whether the star sits in ring 1 and only sky between rings 2 and 3. **Shift + mouse wheel** on the image makes all three rings larger or smaller (by 0.5 px); the boxes on the right show the numbers. On a frame zoomed far out, where the rings would be smaller than a few screen pixels, a small cross marks each star instead.

- **Ring 1, the aperture:** the circle in which the star's light is summed.
- **Between rings 1 and 2:** left out on purpose. It holds the wings of the star, which would make the sky look brighter than it is.
- **Between rings 2 and 3, the sky annulus:** the sky level is measured here (sigma-clipped median, so faint neighbours and hot pixels do not count) and subtracted from every aperture pixel.

**Choose the radii from the star profiles** sets the three rings from the stars you clicked, as other programs do with a seeing profile (AstroImageJ) or a curve of growth (DAOPHOT):

1. The **FWHM** of the stars is measured from their radial profile (a Moffat fit).
2. The **aperture** is the radius where the light curve has the best signal-to-noise: on the curve of growth of the target and the comparison stars, the CCD equation (photon noise of the star, noise of the sky and read-out in every pixel) is evaluated at every radius (Howell 1989). Faint stars have their best S/N in a small aperture, bright stars in a larger one. It is kept between 1 and 3 FWHM: smaller apertures lose a seeing-dependent part of the light and suffer from centring errors.
3. The **inner sky radius** is where the brightest of the selected stars has given 99.5 % of its light, and at least 3 FWHM: real stars have wings, and the seeing changes during the night.
4. The **outer sky radius** makes the annulus four times as large as the aperture in pixels, so the sky adds only 25 % to its own noise in the result (Merline & Howell 1995).

The plot shows the star's profile with the aperture (green), the left-out gap and the sky annulus (blue); the line under it gives the numbers. You can still change the radii by hand.

- **Radii follow the seeing:** on every frame all three radii are scaled by that frame's FWHM divided by the first frame's (a "variable aperture" in AstroImageJ). The aperture then always holds the same part of the light, which helps on nights when the seeing changes a lot or the focus drifts.
- For defocused stars (rings or flat discs) check the profile: the FWHM then measures the disc, and the radii follow it.
- Stars are re-centred on every frame, and the field's drift during the night is followed frame to frame.
- The automation templates choose the radii this way by themselves.

## Time and BJD
Times are taken from `DATE-OBS` and `EXPTIME` (the middle of the exposure). With the **Target RA Dec** (or `OBJCTRA`/`OBJCTDEC` in the header) and the site in the header, times are converted to **BJD_TDB**, the standard for timing eclipses and transits.

## Measure the light curve
**Measure light curve** runs in the background and draws the relative flux (target / comparison ensemble) against time. Under the plot you see the number of points and the scatter in percent. Points from frames that could not be measured (clouds, star outside) are left out and reported. The first view is the **differential plot** as it is usually drawn: Δm of the target against the comparison below, and above it the check star against the same comparison (or C1 − C2 when no check star is marked) with its scatter in mmag. A flat upper row means the comparison is constant; its scatter is the precision of the target's points. Photometry only measures: the fits come next — **Period search and O−C →** opens Light curves & O−C (which already has the curve), **Fit an eclipse or transit model →** saves the curve as CSV and opens it on Orbits & models; the time of one minimum is fitted on the Minimum tab here.


**Scintillation:** the twinkling of a star adds noise that photon statistics do not know; for bright stars and short exposures it is the largest error. When the **Telescope aperture (m)** is given (or APTDIA, in mm, is in the header) and the site and the target position are known, every flux error includes it — σ² = 10⁻⁵ · 1.5² · D^(−4/3) · t⁻¹ · X³ · e^(−2h/8000 m) (Osborn et al. 2015, the corrected form of Young 1967; D aperture, t exposure, X airmass, h height). The line under the plot says whether it was included and how large it was (mmag per frame). The measured fluxes do not change, only their error bars.

## Deleting bad points and spacing the curves
In the **Plot** tab tick **Click a point to delete it** and click a point of the light curve (a cloud, a satellite, a frame where the star was lost): that frame is left out of the light curve, the magnitudes, the detrending, the time of minimum and the export. **Restore deleted points** brings them all back. **Spacing between curves** sets how far apart the curves are drawn in the views with several curves (*all stars*, *comparison stars against the others*); 0 puts them on top of each other, for example to see that two standard stars give the same flat line.

Every plot of the application has **Open in a new window** in its toolbar: a copy of the plot in its own window, to look at it large (zoom, pan, save) while you keep working.

## Detrending
Slow changes that are not the star's — extinction changing with airmass, a drifting sky, focus or the star moving over the chip — can be divided out (as in AstroImageJ or EXOTIC). In the **Plot** tab tick what to detrend against (airmass, FWHM, sky, x, y, time), give the start and end of the eclipse or transit under **Leave out from … to …** so the event itself is not fitted, and press **Detrend**: ln(flux) is fitted linearly in the ticked quantities on the points outside that range and divided out of all points. The line under the plot gives the scatter before and after. **Undo detrending** returns to the measured curve. FWHM is available when *Radii follow the seeing* was on; airmass needs the site and the target's position. The time of minimum, the export and the AAVSO report use the detrended curve.

**Trend degree** 1 divides out a straight-line dependence on each ticked quantity; 2 or 3 fits a curve (e.g. extinction that is not linear in airmass, or a slow drift in time that bends). Use the lowest degree that removes the trend: a higher degree can also bend a long eclipse.

## Time of minimum
- Enter the **Ephemeris T0 (BJD)** and **Period (d)** if you know them (optional): then the epoch and O-C are given too.
- Under **What kind of minimum is it?** choose **Eclipsing binary: Kwee–van Woerden method** (the default; Kwee & van Woerden 1956, the method of O−C databases) or **Exoplanet transit: trapezoid fit**, which suits flat-bottomed dips and also gives depth and duration.
- **Time of minimum** gives the time with its error (for KvW the larger of the KvW and bootstrap errors), in days and minutes.
- When the light curve covers several eclipses (TESS, several nights), give T0 and the period — after a **Period search** on this light curve they are filled in for you — and every primary and secondary minimum is timed in its own window and sent to the O-C page with its type; without them the page asks for them instead of giving one meaningless time.

## Standard magnitudes
With a plate-solved first image (Image → Plate solve), choose the filter of your images and press **Standard magnitudes (APASS / Gaia)**. The comparison stars are looked up on the internet: B, V, g′, r′, i′ come from APASS DR9; R and I (and V where APASS has no value) are computed from Gaia DR3 with the published Gaia-to-Johnson-Cousins relations (about 0.03 mag scatter); G is Gaia's own. The light curve then becomes magnitudes in the standard system: a zero point for every frame from all comparison stars and, when three or more comparison stars have colours, a colour term fitted for the night — only when the stars show one (its slope more than three times its error): a few stars of similar colour cannot measure it, and a slope from their scatter, carried to a target of another colour, moved a real RR Lyrae star by 0.27 mag. When VizieR does not answer, Gaia comes straight from the ESA Gaia archive. A comparison star that disagrees with the catalogue by more than 0.1 mag (variable, blended, or a bad catalogue value) is reported and left out. The magnitudes are drawn (brighter up), go into the CSV export, and fill the comparison magnitudes of the AAVSO report.

## Exporting
- **Export CSV…** writes the time, relative flux, Δm and their errors, the magnitudes when known, every check star and further target, the raw fluxes, airmass and FWHM, for other programs.
- **Export AAVSO report…** writes the AAVSO extended format: star name (as in VSX), your observer code, filter, the catalogue magnitudes of the comparison stars, chart ID and notes; the first check star goes into KNAME / KMAG, as the AAVSO asks for ensemble photometry. MERR is the photon error together with the scatter of the comparison stars' zero points in that frame. Checked on real LCO frames: the transformation found from APASS on Landolt's SA 98 field (1 s exposures in B and V) gives Landolt's V to 0.03 mag (median −0.008) and B−V to 0.05 mag for 31 standard stars.

## Live light curve
(under **Other tools**) **Live: follow a folder during the night…** watches the folder the camera writes to. Each new frame is calibrated (with the masters you choose, or none) and measured as it arrives, and the light curve grows by itself. Click the target and comparison stars on the first frame before starting. Frames that cannot be measured are skipped and counted.

## Polarimetry (dual beam)
(under **Other tools**) For a dual-beam polarimeter (Wollaston prism + half-wave plate): click the **ordinary** image of the star as target and the **extraordinary** image as the first comparison, then **Polarimetry (dual beam)**. The half-wave plate angle is read from the header. The result is the Stokes q and u, the degree of polarisation P (also debiased) and the angle θ with their errors.

## PSF photometry and searching for variables
**PSF photometry** (tick it on the Photometry page) fits a star image of each frame's FWHM to every star instead of summing an aperture; stars closer than 2.5 FWHM are fitted together, so a blended neighbour does not leak into the target. Use it in crowded fields (clusters, the Milky Way); in sparse fields apertures are as good.

**Light curves & O-C → Variable star search** measures every star of the first frame on all frames (aperture or PSF), puts all frames on a common zero point from the constant stars (so clouds and airmass cancel) and plots each star's scatter against its brightness. Constant stars follow a curve that rises towards faint magnitudes (photon noise); stars well above it are **candidates** (red circles, listed by index). Click a point or a row to see that star's light curve, and **Send this star to Period search** to find its period. This is what Muniwin's *varfind* does: check candidates in VSX before announcing a discovery.

## Extinction and transformation coefficients
**Image → Photometric coefficients…**
- **Extinction of the night:** from the comparison stars of the light curve you measured (the frames must give the sky position, so the airmass is known): every star's instrumental magnitude against airmass, one slope k for all (mag per airmass), with the Bouguer plot. Typical values in V: 0.15–0.3 at a good site.
- **Transformation coefficients:** two plate-solved images of a standard field (e.g. a Landolt field or M67) in two filters. The stars are measured on both, their magnitudes come from APASS (B, V, g′, r′, i′) or Gaia (V, R, I), and the coefficients are fitted in the AAVSO convention: Tbv from (B−V) against (b−v), Tv and Tb from V−v and B−b against (B−V). Enter them in your reports or in AAVSO's transformation tool.
