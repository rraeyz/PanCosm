# Light curves and O-C
The **Light curves & O-C** page has three tabs: **Period search**, **Frequency analysis** and **O-C diagram**.

## Period search
The light curve measured on the Photometry page is used automatically; or **Load CSV (time, flux)…**.

- **Lomb–Scargle** — for sinusoidal variations (pulsating stars, rotation).
- **BLS** (box least squares) — for short dips: transits and Algol-type eclipses.
- **PDM** (phase dispersion minimisation) — for any light-curve shape.
- **ANOVA** (multi-harmonic analysis of variance) — for smooth non-sinusoidal shapes such as RR Lyrae and Cepheids.

**TESS and Kepler:** type a star name (or TIC / KIC number), choose TESS, Kepler or K2 and press **Download**. The mission's own light curves (PDCSAP flux, corrected for instrumental trends) come from the MAST archive, flagged points are dropped, each sector or quarter is normalised and all are joined, with times in BJD_TDB. They are kept in the settings folder, so a second download is instant. Then search the period as below.

**ZTF and AAVSO:** choose ZTF (the Zwicky Transient Facility's light curves from IRSA, found by the star's position) or AAVSO (the observations in the AAVSO International Database) and press **Download**. Files exported from AAVSO, ZTF or the ASAS-SN Sky Patrol can also be opened with **Load CSV…**. One band is kept (the one with most points), upper limits and flagged points are dropped, magnitudes become relative flux and the times are converted to BJD_TDB, so these data can be joined with TESS or your own.

Set the **shortest** and **longest period** (the longest defaults to half the time span) and press **Search**. The periodogram and the light curve folded on the best period are shown. Check the folded curve: half or double the period is a common alias, especially for eclipsing binaries with equal minima.

**Phase bins** draws the mean curve over the folded points. **Editing the light curve:** *Remove outliers (σ)*, *Bin in time (min)*, *Delete points by clicking* (then click a point on the plot), *Flux ↔ magnitude* and *Undo edits*. The edited curve is what the period search and the frequency analysis use. *Remove outliers* compares each point with its neighbours in time (and, once a period is found, in the folded curve), so eclipses and pulsations are kept.

## Frequency analysis
For pulsating stars with several modes (δ Scuti, γ Dor, β Cep), as Period04 does. Set the **highest frequency** (cycles per day) and press **Analyse frequencies**:

1. The amplitude spectrum (Deeming's Fourier transform for uneven sampling) is computed.
2. Its highest peak is fitted as a sinusoid, removed (**prewhitening**), and the residuals are searched again.
3. Every new frequency is fitted together with the earlier ones (frequencies, amplitudes, phases all free).
4. It stops when the next peak's **S/N** (its amplitude over the mean residual amplitude within ±1 c/d) is below the limit; Breger's criterion is 4.

The table gives each frequency, period, amplitude and phase with their errors (Montgomery & O'Donoghue 1999) and S/N. The plots show the original spectrum, the residual spectrum with the S/N limit, and the **spectral window**: a peak of the window at 1 c/d means the daily gaps create aliases at ±1 c/d of every true frequency, so check a frequency against its alias before believing it. Tick **Also show the CLEANed spectrum** to see the spectrum with those aliases removed (CLEAN, Roberts, Lehár & Dreher 1987): a true frequency stays, its aliases fall away.

**Times of maximum** are measured for every cycle the data cover (a parabola around each maximum of the fitted curve); tick *Values are magnitudes* if the light curve is in magnitudes. **Send maxima to the O-C diagram** adds them to the O-C list.

## O-C diagram
O-C (observed minus calculated) shows how the times of minimum depart from a constant period.

1. Type or paste the **minimum times**, one per line: `time [error] [I/II] [source]` — e.g. `2459876.43215 0.00021 I TESS`. Or **Load file…**. Times in BJD or HJD; do not mix them.
2. Give a **Reference T0** and **Period (d)**: the epoch of every minimum is computed from them.
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
