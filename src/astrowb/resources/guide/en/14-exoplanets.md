# Exoplanets
The **Exoplanets** window fits an exact transit model to a saved light curve. It opens from its block on the Start page or the Window menu. The stages run down the left rail: Data, Star, Planets, Model, Fit, Uncertainty, Results. The main view shows the transit with the fitted model and its residuals, a table of the fitted parameters and a line of text with the result.

## Data {#exoplanets-data}
**Open light curves…** takes one or more light-curve files: the `.lc.ecsv` files written by the Photometry window, or a CSV / text table of time, flux and error (at least 10 rows). The table lists each file with its number of points, its time span in days and its time scale; choosing a row chooses the light curve that is fitted, and shows its last fit. A file that cannot be read is named in the text under the plot, with the reason. Times in BJD_TDB are needed for the ExoClock file (see Results).

## Star {#exoplanets-star}
The star's limb darkening follows a quadratic law with the coefficients **u1** and **u2** (defaults 0.4 and 0.2). They are fixed unless **Fit the limb darkening** is ticked; a single night rarely decides them, so leave them fixed and take the values for the star's temperature and the filter from a table.

## Planets {#exoplanets-planets}
Start values of the transit: **Period (d)** (fixed: one transit does not fix it), **Mid-transit** and **Rp/R★** (both *auto* by default: the middle and the square root of the depth of the dip of the smoothed curve), **a/R★** and the **Impact parameter**. The fit refines the mid-transit time, Rp/R★, a/R★ and b from these. The period and a first guess of the others can be taken from the NASA Exoplanet Archive in the Planning window (**Add with ephemeris**) or the Photometry window; this window does not look them up.

## Model {#exoplanets-model}
**Detrend against** lists the quantities that slow trends not due to the planet are fitted against together with the transit: airmass, fwhm, sky, x, y, comma-separated (default `airmass`; empty: none). The light curve must contain those columns; the Photometry window writes them.

## Fit {#exoplanets-fit}
**Fit the transit** fits the chosen light curve in the background; the result replaces the plot, the table and the text when it is ready. Stop is in the status bar.

## Uncertainty {#exoplanets-uncertainty}
The least-squares errors can be too small when the residuals are correlated in time. **Account for red noise (errors × β)** multiplies the errors by β, the factor by which the scatter of the residuals fails to average down with the time bin. **MCMC steps** runs a posterior sampling after the fit (it stops earlier once converged; 0: none) and gives asymmetric errors for the mid-transit time, Rp/R★, a/R★ and b; if the text says *not converged*, use more steps.

## Results {#exoplanets-results}
The text and the table give the mid-transit time (BJD), depth (ppt and mmag), durations T14 and T23, a/R★, b, inclination, the stellar density, the reduced χ², the RMS of the residuals and β. **ExoClock file…** writes the upload file of the ExoClock transit-timing project (time in BJD_TDB, normalised flux, error) and **ETD file…** the file for the Exoplanet Transit Database (Julian date, magnitude, error). A light curve whose times are not BJD_TDB cannot be written for ExoClock: give the target's position when measuring.
