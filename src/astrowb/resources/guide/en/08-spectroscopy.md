# Spectroscopy
The **Spectroscopy** page reduces spectra and measures radial velocities. Its tabs follow the work: **Reduce** (long-slit and slitless), **Echelle**, **Telluric**, **Radial velocity & orbit** and **IFU cube**.

## Instrument profiles
Settings that belong to a spectrograph (orientation, aperture and sky widths, line list, gain, read noise…) can be stored as an **instrument profile**: choose a profile at the top, change the settings, **Save as…** under a name such as "1 m telescope + Shelyak LHIRES", or **Delete** it. Profiles are kept in your settings, so they are there in every project.

## Orientation
**Dispersion along** rows (x) or columns (y), and **blue on the right** when wavelengths decrease from left to right. Set these once per instrument; everything else follows.

## Long-slit reduction (Reduce)
1. Choose the **Science frame** (calibrated 2-D image) and, for wavelengths, the **Arc lamp** frame.
2. **Optimal extraction (Horne)** weights each pixel by the spatial profile — better signal-to-noise for faint stars. **Aperture width**, **Sky offset** and **Sky width** (pixels) set the extraction window and the two sky bands on both sides of the trace.
3. **1. Extract**: the spectrum is traced along the dispersion and extracted; the arc is extracted with the same trace and its lines are found.
4. **2. Click arc lines** in the lower plot and type their wavelengths (Å) in the table. Two lines are the minimum; 4–6 spread over the whole range are much better. Choose the **Arc line list** of your lamp (He-Ne-Ar, Th-Ar, Cu-Ar, Fe-Ar…): the remaining lines are identified automatically from it.
5. **3. Solve wavelengths and save**: a polynomial wavelength solution is fitted; its rms (Å) and the number of lines are shown. The 1-D spectrum is saved as FITS with wavelengths.

## Echelle
Calibrate the frames first on the Calibrate page with **Spectra: do not divide by the flat** ticked (bias, dark and cosmic rays only), then give the master flat here.

1. Choose the **Science frame**, the **Flat** (traces the orders and gives the blaze) and the **Arc lamp (ThAr)**. Tick **Fibre-fed** when there is no sky between the orders.
2. **Lowest order number:** the absolute order number of the lowest order in the image, from the spectrograph manual. If unknown: m = λ2 / (λ2 − λ1), with λ1, λ2 the wavelengths at the same pixel in two neighbouring orders (λ2 the longer). Say whether **order numbers** increase or decrease upwards.
3. **1. Trace and extract orders.** **Show order** selects which order's arc is shown.
   **Checking the orders (optional):** **Show the orders on the flat** draws the traces the program found on the flat. On good data they are right and nothing needs doing. Click a wrong trace (a ghost, a defect, a half order at the edge) to remove it; click anywhere on an order that was missed to add it: it is moved along the neighbouring orders' curvature to the centre column and traced. Orders that cannot be traced are shown as red crosses and left out. The extraction then uses exactly the orders shown. Unlike IRAF apfind/aptrace there is nothing to set: the search window follows the order spacing.
4. **2. Click arc lines** — at least three per order in at least two orders — and type their wavelengths.
5. **3. Solve, merge and save:** a global 2-D solution (pixel and order) is fitted, the orders are divided by the blaze and merged into one spectrum, which is saved.
6. **Check the fit as in IRAF ecidentify:** the bottom plot shows the residual (mÅ) of every arc line against its pixel, coloured by order; lines rejected by the 3σ clipping are grey crosses. Click a point to leave that line out (a blend, a wrong identification), then **Refit without the left-out lines**; **Use all lines again** forgets them.
7. Besides the merged spectrum, every order is saved on its own in `<name>_orders.fits` (flux, error and wavelength images, one row per order; the ORDERS keyword gives the order numbers), for work order by order.

**Subtract scattered light** (as IRAF apscatter) fits the light in the gaps between the orders — across the dispersion with a clipped polynomial, then smoothed along it — and subtracts it from the science frame and the flat before extraction. Use it on bright stars and with spectrographs whose orders sit on a glow; it needs gaps of at least 3 pixels (not for tightly packed fibre orders).

## Telluric correction
Choose the **Spectrum (1-D)** and the spectrum of a **telluric standard** (a hot, fast-rotating star observed close in time and airmass). The standard gives the atmospheric transmission; its strength (airmass, water vapour) and a small wavelength shift are fitted inside the telluric bands. **Correct and save** writes the corrected spectrum and shows the before/after plot.

## Radial velocity and orbit
1. **Add…** the 1-D spectra (FITS tables, 1-D FITS with wavelength WCS, or text files).
2. Choose a **Template** (a spectrum of a similar star, or a synthetic one). For a **double-lined binary**, add a **Second template**: both stars are then measured with TODCOR.
3. **Method:** *Cross-correlation* for sharp-lined stars (TODCOR when a second template is given); *Broadening function* for fast rotators (one star) and contact or close binaries (two stars). The broadening function is the Doppler profile itself, so each star appears as its own rotational profile even when the lines are very broad; it gives the velocities, **v sin i** of each star and their light ratio. Use a sharp-lined template of a similar spectral type and a velocity range wider than both profiles.
4. **Target RA Dec** (from the header if empty), the **velocity range** and optionally a **wavelength window** (avoid telluric bands).
5. **Measure radial velocities:** each spectrum is cross-correlated with the template. The table gives the observed RV, its error, the **barycentric correction** and the corrected RV. The correction needs the observation time, the target position and the site (Plan page); otherwise it shows "not applied".
6. **Period guess (d)** (e.g. from the period search) and **Fit orbit:** P, e, ω, K, γ with errors and the rms. For double-lined binaries also K2, the mass ratio q, M sin³i of both stars and a sin i; for single-lined ones the mass function f(m).

## Disentangling a double-lined binary
After measuring both stars' velocities (TODCOR or the broadening function), **Separate the two stars' spectra (disentangling)** recovers each star's own spectrum from the series (iterative shift-and-add, González & Levato 2006). It uses the velocities measured on these spectra and the light ratio, and writes `star1.fits` and `star2.fits`. Use at least four spectra spread over the orbit, ideally several near both quadratures; the separated spectra are the best templates for a second, more precise velocity measurement, and show each star's lines for classification.

## Spectral type and templates
**Spectral type of the first spectrum (and a template)** on the Radial velocity tab compares the first spectrum with the Pickles (1998) library of 131 stars, O5 to M6 in all luminosity classes (downloaded from STScI the first time, about 6 MB, then kept in the settings folder). Both spectra are divided by their own smooth continuum, so the instrument's colour response does not matter; the template is smoothed to your resolution and the telluric bands are left out. The three closest types are listed and the best one becomes the template for the radial velocities. You can also put your own spectra (with SPTYPE in the header or the type in the file name) into the `templates` folder.

## Stellar parameters (Teff, log g, [Fe/H])
**Spectrum tools → Stellar parameters** fits synthetic spectra to the open spectrum of an FGK star and gives the effective temperature, surface gravity, metallicity, v sin i and radial velocity, with errors.

1. Open the spectrum (wavelength-calibrated; flux calibration and normalisation are not needed: each 100 Å piece gets its own smooth continuum).
2. Give the **Resolution R** = λ / Δλ of your spectrograph (λ divided by the FWHM of an arc line).
3. Optionally choose a **solar spectrum taken with the same spectrograph** (twilight sky, the Moon or an asteroid). It is the best reference; without it the Kurucz (2005) solar flux atlas is used.
4. **Find Teff, log g, [Fe/H], v sin i.** The first time the model spectra are downloaded: the PHOENIX library (Husser et al. 2013), only the points needed (about 6 MB each, kept as 1 MB), and the solar atlas (30 MB, once). Later runs take seconds.

**How it stays honest.** Model spectra do not reproduce real stars line for line: fitted to the real Sun, PHOENIX alone gives Teff up to 250 K too low and [Fe/H] up to 0.4 dex too low, depending on the wavelength range and resolution. So the program does what careful spectroscopists do: it fits the Sun in exactly the same way (same pixels, same resolution), leaves out the wavelengths where the models do not reproduce the Sun, and gives the star **relative to the Sun**. Tested on the real Sun at R = 20 000 it returns 5738 ± 21 K, log g 4.40 ± 0.05, [Fe/H] −0.02 ± 0.02 (true: 5772 K, 4.44, 0.00). The errors include the noise, the solar reference and the interpolation between grid points.

**Limits.** It is meant for FGK stars; for stars far from the Sun (the result says so) the solar reference is less reliable. So far the method has been checked on the Sun only: before publishing parameters, check it on a few benchmark stars with known parameters (Gaia FGK benchmark stars) observed with your spectrograph, or at least use a solar spectrum from your own spectrograph.

## IFU data cubes
**Load cube** opens a 3-D FITS cube (x, y, wavelength).

- **Mean over a wavelength window** shows an image; **Line map (continuum subtracted)** shows the emission of one line: give its **Centre (Å)** and **Width (Å)**, then **Show image**.
- **Click a spaxel** to see its spectrum; **Spaxel aperture radius** sums the spaxels around it. **Save spectrum…** writes it.

## Spectrum tools
The **Spectrum tools** tab works on one 1-D spectrum, as IRAF splot, BASS or ISIS do. **Open spectrum…** reads the application's own spectra, 1-D FITS images with a wavelength solution (ISIS, BASS, IRAF) and text files.

- **Line markers:** H, He I/II, Ca II, Na D, Mg b, Fe, O I, C, N and forbidden lines; shift them by a radial velocity to match the star.
- **Measure a line:** drag over the line on the plot (or type the limits) and press **Measure**. The continuum is a straight line through the window's two ends, so leave some continuum on both sides. You get the equivalent width by integration with its error (pixel noise and continuum placement), the centre, FWHM, depth and EW of a **Gaussian** or **Voigt** fit, the integrated line flux and the S/N of the continuum. EW is positive for absorption, negative for emission. Each measurement is a row of the table (right-click: CSV or LaTeX).
- **V/R:** for double-peaked emission (Be stars) on a normalised spectrum: (I_V − 1) / (I_R − 1) with the peak velocities.
- **Measure in several spectra…:** the same window in many files; each row has the file, its DATE-OBS, EW and V/R — the Hα monitoring series of a Be star in one click.
- **Change the spectrum:** smoothing (Gaussian, boxcar, median), arithmetic with a number or with **spectrum B** (resampled onto this one), resampling to an even step, automatic normalisation or a continuum through points you click (**Pick continuum points**, then **Normalise through points**). **Undo** steps back.
- **Instrument response:** open the spectrum of a reference star, press **Instrument response…** and choose its known flux distribution (a Pickles spectrum of the same type — the library the spectral-type tool downloads — or a spectrophotometric standard). Stellar lines and telluric bands are left out and the ratio is smoothed with a spline. Then open the target (same setup, same night) and press **Divide by response**: the result is in relative flux.
- **Save as…** writes the result; **Export for BeSS / ARAS…** writes the 1-D FITS with the keywords the BeSS database asks for (object, observer, date, exposure, instrument, site, heliocentric correction, telluric and cosmic flags) on an even wavelength step. Check the file with BeSS's own checker before submitting.
