# Orbits and models
The **Orbits & models** page fits a physical model to the light curve of a detached eclipsing binary or a transiting planet, and combines it with a spectroscopic orbit into absolute dimensions. Models opens in a window of its own (its block on the Start page or the sidebar), with its own Edit → Undo / Redo for the parameters and the fits.

## The model
Two limb-darkened spheres on a Keplerian orbit. It suits detached binaries and transits. Close, distorted or contact binaries need a Roche model: export to PHOEBE or WD instead.

## Fitting a light curve
1. Choose the **Light curve** (CSV from the Photometry page or another source; a time column and relative flux or magnitudes).
2. Give the **Period (d)** and **Primary minimum (BJD)** (from the O-C page).
3. Starting values: **r1 + r2** (sum of radii as a fraction of the separation a), **k = r2 / r1**, **Inclination (°)**, **Surface brightness ratio J**, **Third light**, eccentricity terms, and the limb darkening **u1, u2** of each star. Tick the parameters to fit.
4. **Fit**: the result gives i, r1, r2, the light ratio L2/L1 and e with errors, the rms and χ²ᵣ. The plot shows the data, the model and the residuals (O−C) against phase. **Export results (CSV / LaTeX)…** writes every parameter (free ones with errors, fixed ones marked, MCMC values when sampled), the derived and absolute quantities, as a table for a paper.

## MCMC uncertainties
The errors of a least-squares fit assume the parameters are independent; in eclipsing binaries and transits they are not (inclination, radii and limb darkening trade off). Tick **MCMC uncertainties** to sample the posterior around the fit (affine-invariant ensemble sampler, emcee) with the number of **steps** you choose: the result gives each free parameter as median −/+ its 16th/84th percentiles, and **Posterior…** shows the corner plot (histograms and pairs), where correlations are seen at once. It takes about a minute per 1000 points for 2000 steps; it runs in the background and can be cancelled.

## Absolute dimensions
When the Spectroscopy page has a double-lined orbit (K1, K2), tick **Absolute dimensions with the double-lined orbit**: masses M1, M2, radii R1, R2 (solar units), the separation a and log g of both stars are computed with propagated errors.

## PHOEBE and other models
- **Fit and export for PHOEBE…** writes the light curve (`lc.txt`), the radial velocities when there are any (`rv1.txt`, `rv2.txt`) and the fitted parameters under PHOEBE's names (`start.json`) as the starting point for a Roche model.
- **Fit and export for WD…** writes the observations in the Wilson-Devinney program's columns (`lc.dat`: time, flux, weight) and `wd_parameters.txt` with the fitted values under WD's names: PERIOD, HJD0, XINCL, E, PERR0 (radians), EL3, and — with a double-lined orbit — RM (q), the surface potentials PHSV and PCSV computed from the radii, VGA and A. Type them into the input deck of your WD version; temperatures, albedos and gravity darkening are yours to set.
- **Fit and export for ExoClock / ETD…** (transits) writes the upload files of the two transit-timing projects — `<name>_ExoClock.txt` (BJD_TDB, relative flux, error) and `<name>_ETD.txt` (BJD_TDB, magnitude, error) — and `<name>_summary.txt` with the mid-time of this transit Tc ± error (the epoch nearest to the data, from the fitted T0 and period), depth, duration T14, Rp/R*, a/R* and inclination. Enter T0 and the period from the Plan page's ephemeris look-up, fit T0 (and the shape), then upload; the observation details (observer, filter, exposure) are entered in the projects' own forms. Checked on a real transit of WASP-12 b (TESS sector 20, the target pixel file measured here, one transit of ±3.6 h): Tc 47 s from the same transit in NASA's SPOC light curve and 42 ± 70 s from the ephemeris of the whole sector; depth 1.59 % (SPOC 1.58 %).
- **Compare with a model curve…** draws a curve computed elsewhere (two columns: phase or time, and flux) over your data.

## Visual binary orbit
The **Visual binary orbit** tab fits the seven orbital elements of a resolved double star to measures of the companion's position.
1. Type or **Load** the measures, one per line in the WDS order: epoch (year), position angle θ (degrees, north through east), separation ρ (arcsec), and optionally the error of ρ (″) and of θ (°). Lines starting with `#` are skipped. At least 7 measures are needed (seven elements); far more are better.
2. Optionally limit the **shortest** and **longest period** (years); by default 0.5 to 10 times the time covered by the measures is searched.
3. Give the **parallax** (mas) to get the total mass M1 + M2 = a³ / (ϖ³ P²) from Kepler's third law.
4. **Fit the orbit**: every period in the range, every periastron phase and eccentricities 0 to 0.95 are tried with the linear Thiele–Innes solution, then all seven elements are refined together (Levenberg–Marquardt). The table gives P, T, e, a, i, Ω, ω with 1σ errors from the fit covariance (scaled by the reduced χ²), the rms of the separations and the mass. The plot shows the apparent orbit (east to the left, as on the sky), the measures and their O−C lines.

Without radial velocities Ω and ω can both be turned by 180°: the program gives Ω between 0 and 180°. Check a short period range that hides a longer real period: compare χ²ᵣ for different ranges. Method: Heintz (1978), *Double Stars*; conventions of the USNO orbit catalogues (Fifth Catalog: Hartkopf, Mason & Worley 2001, AJ 122, 3472; continued as the Sixth Catalog, ORB6).
