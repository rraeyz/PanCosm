# Photometry
The **Photometry** page measures the brightness of a target star relative to comparison stars on a series of calibrated images and gives a light curve, times of minimum and reports.

## Choosing images and stars
1. **Choose images…** — calibrated frames of one field and one filter. They are sorted by time.
2. On the first image, **click the target star**, then **one or more comparison stars**. Clicks snap to the star's centre. **Clear stars** starts again.
3. Or press **Suggest comparison stars**: it picks stars of similar brightness, not saturated, without bright neighbours and inside the frame in every image. Check them before measuring.

Good comparison stars have a similar colour and brightness to the target and are not variable. Use several: their sum (an ensemble) is less noisy than one star.

## Differential photometry: targets, comparison and check stars
**Clicks add** chooses what the next clicks are: *target, then comparison stars* (the first click is the target T1, the next ones comparison stars C1, C2…), *check stars* (K1, K2…) or *more targets* (T2, T3…). Check stars and further targets are measured on every frame against the same comparison stars but are not part of them — as the check star of MaxIm DL, VPhot or AIJ. A constant check star shows how good the photometry really is: its scatter (in mmag) is listed under the plot.

The **Stars** tab lists every star with its role and position. Type the comparison stars' **known magnitudes** (from an AAVSO chart, a catalogue or your own calibration) into the last column: the target, the other targets and the check stars then get **magnitudes** frame by frame (each comparison star gives a zero point; a comparison star that disagrees by more than 0.1 mag is left out and named). **Standard magnitudes (APASS / Gaia)** fills the same column from the catalogues.

**Weight comparison stars by their scatter:** each comparison star is measured against the sum of the others and weighted by the inverse of its variance (repeated, so a variable comparison star cannot spoil the others' scatter). A variable or disturbed comparison star then hardly counts.

The **Plot** tab chooses what is drawn: T1 relative flux, its differential magnitude Δm = −2.5 log(target / ensemble), its magnitude, each further target or check star, **the comparison stars against the others** (a variable one stands out), **all stars normalised and offset**, or airmass, sky, FWHM and position against time. Frames where a star reaches the saturation level are circled red and counted.

## Frame quality
**Check frame quality** measures every chosen frame: the size of the stars (FWHM), how many stars are seen and the sky level. The plot shows the three through the night; frames far worse than the night's typical frame are marked red, with the reason — *stars blurred* (wind, focus, seeing), *few stars* or *no stars* (clouds, dew), *bright sky* (twilight, Moon). **Leave out the bad frames** removes them before measuring. The *Eclipsing binary night* and *Exoplanet transit* automations do this by themselves.

## Apertures
Every star gets three rings, drawn on the image: the **aperture** (solid), and the inner and outer edge of the **sky annulus** (dashed).

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
**Measure light curve** runs in the background and draws the relative flux (target / comparison ensemble) against time. Under the plot you see the number of points and the scatter in percent. Points from frames that could not be measured (clouds, star outside) are left out and reported.


**Scintillation:** the twinkling of a star adds noise that photon statistics do not know; for bright stars and short exposures it is the largest error. When the **Telescope aperture (m)** is given (or APTDIA, in mm, is in the header) and the site and the target position are known, every flux error includes it — σ² = 10⁻⁵ · 1.5² · D^(−4/3) · t⁻¹ · X³ · e^(−2h/8000 m) (Osborn et al. 2015, the corrected form of Young 1967; D aperture, t exposure, X airmass, h height). The line under the plot says whether it was included and how large it was (mmag per frame). The measured fluxes do not change, only their error bars.

## Deleting bad points and spacing the curves
In the **Plot** tab tick **Click a point to delete it** and click a point of the light curve (a cloud, a satellite, a frame where the star was lost): that frame is left out of the light curve, the magnitudes, the detrending, the time of minimum and the export. **Restore deleted points** brings them all back. **Spacing between curves** sets how far apart the curves are drawn in the views with several curves (*all stars*, *comparison stars against the others*); 0 puts them on top of each other, for example to see that two standard stars give the same flat line.

Every plot of the application has **Open in a new window** in its toolbar: a copy of the plot in its own window, to look at it large (zoom, pan, save) while you keep working.

## Detrending
Slow changes that are not the star's — extinction changing with airmass, a drifting sky, focus or the star moving over the chip — can be divided out (as in AstroImageJ or EXOTIC). In the **Plot** tab tick what to detrend against (airmass, FWHM, sky, x, y, time), give the start and end of the eclipse or transit under **Leave out from … to …** so the event itself is not fitted, and press **Detrend**: ln(flux) is fitted linearly in the ticked quantities on the points outside that range and divided out of all points. The line under the plot gives the scatter before and after. **Undo detrending** returns to the measured curve. FWHM is available when *Radii follow the seeing* was on; airmass needs the site and the target's position. The time of minimum, the export and the AAVSO report use the detrended curve.

**Trend degree** 1 divides out a straight-line dependence on each ticked quantity; 2 or 3 fits a curve (e.g. extinction that is not linear in airmass, or a slow drift in time that bends). Use the lowest degree that removes the trend: a higher degree can also bend a long eclipse.

## Time of minimum
- Enter the **Ephemeris T0 (BJD)** and **Period (d)** if you know them (optional): then the epoch and O-C are given too.
- Tick **Kwee–van Woerden** for eclipsing binaries; leave it for the **trapezoid fit**, which suits transits and flat-bottomed eclipses and also gives depth and duration.
- **Time of minimum** gives the time with its error (for KvW the larger of the KvW and bootstrap errors), in days and minutes.

## Standard magnitudes
With a plate-solved first image (Image → Plate solve), choose the filter of your images and press **Standard magnitudes (APASS / Gaia)**. The comparison stars are looked up on the internet: B, V, g′, r′, i′ come from APASS DR9; R and I (and V where APASS has no value) are computed from Gaia DR3 with the published Gaia-to-Johnson-Cousins relations (about 0.03 mag scatter); G is Gaia's own. The light curve then becomes magnitudes in the standard system: a zero point for every frame from all comparison stars and, when three or more comparison stars have colours, a colour term fitted for the night. A comparison star that disagrees with the catalogue by more than 0.1 mag (variable, blended, or a bad catalogue value) is reported and left out. The magnitudes are drawn (brighter up), go into the CSV export, and fill the comparison magnitudes of the AAVSO report.

## Exporting
- **Export CSV…** writes the time, relative flux, Δm and their errors, the magnitudes when known, every check star and further target, the raw fluxes, airmass and FWHM, for other programs.
- **Export AAVSO report…** writes the AAVSO extended format: star name (as in VSX), your observer code, filter, the catalogue magnitudes of the comparison stars, chart ID and notes; the first check star goes into KNAME / KMAG, as the AAVSO asks for ensemble photometry.

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
