# Light curves and O-C
Two windows. **Light curves and period** has the tabs **Period search**, **Frequency analysis** and **Variable star search** (its block on the Start page or the Window menu); Edit → Undo / Redo there act on the tab shown. **O−C** is a window of its own (its block or the Window menu): times of minimum timed in Photometry and the maxima of the frequency analysis arrive there by themselves.

## Period search
The light curve measured on the Photometry page is used automatically; or **Load CSV (time, flux)…**.

- **Lomb–Scargle** — fits a sine wave at every trial period and keeps the one that explains most of the variation. For sine-like variations: pulsating stars, rotation and spots.
- **BLS** (box least squares) — fits a short, box-shaped dip at every trial period. For transits of planets and Algol-type eclipses.
- **PDM** (phase dispersion minimisation) — assumes no shape: it folds the data on every trial period and keeps the one where the points lie most neatly on top of each other. For any light-curve shape, e.g. eclipsing binaries with two minima.
- **ANOVA** (multi-harmonic analysis of variance) — fits a curve of two harmonics at every trial period and tests it statistically. For smooth non-sinusoidal shapes such as RR Lyrae and Cepheids.

How each method works, with its formulas and references: **Mathematics of the methods** (the last chapter of this guide). Hover over the method list for a one-line summary of each.

**TESS and Kepler:** type a star name (or TIC / KIC number), choose TESS, Kepler or K2 and press **Download**. The mission's own light curves (PDCSAP flux, corrected for instrumental trends) come from the MAST archive, flagged points are dropped, each sector or quarter is normalised and all are joined, with times in BJD_TDB. They are kept in the settings folder, so a second download is instant. Then search the period as below.

**ZTF and AAVSO:** choose ZTF (the Zwicky Transient Facility's light curves from IRSA, found by the star's position) or AAVSO (the observations in the AAVSO International Database) and press **Download**. Files exported from AAVSO, ZTF or the ASAS-SN Sky Patrol can also be opened with **Load CSV…**. One band is kept (the one with most points), upper limits and flagged points are dropped, magnitudes become relative flux and the times are converted to BJD_TDB, so these data can be joined with TESS or your own.

Set the **shortest** and **longest period** (the longest defaults to half the time span) and press **Search**. The periodogram and the light curve folded on the best period are shown. Check the folded curve: half or double the period is a common alias, especially for eclipsing binaries with equal minima. A ⚠ line under the result says when it cannot be trusted: the light curve is shorter than two cycles of the periods searched (observe longer), the best period is longer than half the time span, or the periodogram is highest at the edge of the range (widen it).

**Phase bins** draws the mean curve over the folded points. **Editing the light curve:** *Remove outliers (σ)*, *Bin in time (min)*, *Delete points by clicking* (then click a point on the plot), *Flux ↔ magnitude* and *Undo edits*. The edited curve is what the period search and the frequency analysis use. *Remove outliers* compares each point with its neighbours in time (and, once a period is found, in the folded curve), so eclipses and pulsations are kept. **Errors:** when the light curve has them (from the Photometry page, TESS / Kepler / ZTF / AAVSO downloads, or a third column in a CSV file), they are drawn as error bars, follow every edit (outliers, binning — the error of each mean —, deleted points, flux ↔ magnitude) and weight the Lomb–Scargle and BLS searches by 1/σ²; **Save** writes them as a third column.

## Frequency analysis
For pulsating stars with several modes (δ Scuti, γ Dor, β Cep), as Period04 does. Set the **highest frequency** (cycles per day) and press **Analyse frequencies**:

1. The amplitude spectrum (Deeming's Fourier transform for uneven sampling) is computed.
2. Its highest peak is fitted as a sinusoid, removed (**prewhitening**), and the residuals are searched again.
3. Every new frequency is fitted together with the earlier ones (frequencies, amplitudes, phases all free).
4. It stops when the next peak's **S/N** (its amplitude over the mean residual amplitude within ±1 c/d) is below the limit; Breger's criterion is 4.

The table gives each frequency, period, amplitude and phase with their errors (Montgomery & O'Donoghue 1999) and S/N. The plots show the original spectrum, the residual spectrum with the S/N limit, and the **spectral window**: a peak of the window at 1 c/d means the daily gaps create aliases at ±1 c/d of every true frequency, so check a frequency against its alias before believing it. Tick **Also show the CLEANed spectrum** to see the spectrum with those aliases removed (CLEAN, Roberts, Lehár & Dreher 1987): a true frequency stays, its aliases fall away.

**Times of maximum** are measured for every cycle the data cover (a parabola around each maximum of the fitted curve); tick *Values are magnitudes* if the light curve is in magnitudes. **Send maxima to the O-C diagram** adds them to the O-C list.

## O-C diagram (the O−C window)
O-C (observed minus calculated) shows how the times of minimum depart from a constant period.

1. Type or paste the **minimum times**, one per line: `time [error] [I/II] [source]` — e.g. `2459876.43215 0.00021 I TESS`. Or **Load file…**. Times in BJD or HJD; do not mix them.
2. Give a **Reference T0** and **Period (d)**: the epoch of every minimum is computed from them.
   Or type the star's name in **Star** and press **Look up**: T0 and the period come from AAVSO VSX. An empty T0 is the first primary minimum.
3. Choose **Linear ephemeris** or **Quadratic (period change)** and press **Fit and draw O-C**. **Export results (CSV / LaTeX)…** writes the fitted values with 1σ errors, rounded as in a paper, and a caption naming the model.

The result gives the new T0 and P with errors; the quadratic fit also gives the rate of period change dP/dt in seconds per year, and the reduced χ². Primary minima are drawn as circles and secondary minima as squares; the lower plot shows the residuals.

## Third body and apsidal motion
- **Third body (light-travel time):** the eclipsing pair orbits the centre of mass with a third star, so its eclipses come early and late along an orbit (Irwin 1952). The fit gives the third body's period P3 (years), the semi-amplitude A (minutes), eccentricity e, argument ω, and the mass function f(m3), the lower limit on the third star's mass. It needs at least 8 minima spread over more than one P3.
- **Apsidal motion:** in an eccentric orbit the line of apsides turns, so primary and secondary minima swing in opposite directions. Give both kinds (I and II); the fit gives e, ω at epoch 0, dω/dE (degrees per cycle) and the apsidal period U (years). The model is first order in e (good for e ≲ 0.1).
- **MCMC uncertainties:** for these two models, tick the box to run a Markov chain (emcee) after the fit: 68 % intervals of every parameter, e and ω included, and of f(m3) and U, honest when the parameters depend on each other (as in OCFit). It takes a few seconds; more steps give steadier errors. The linear and quadratic ephemerides are linear problems, so their least-squares errors are already exact and the box is off.

## Reading an O-C diagram
- A straight sloping line: the period is slightly wrong — the fit corrects it.
- A parabola: the period changes (mass transfer, magnetic activity, angular-momentum loss).
- A wave: light-travel time effect of a third body, or apsidal motion (primary and secondary minima moving opposite to each other in eccentric systems).
- Errors matter: minima without errors are given equal weight.
