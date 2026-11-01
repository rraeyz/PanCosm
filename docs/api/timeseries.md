# timeseries

Python: `from astrowb import api; api.timeseries.<step>(…)`; command line: `astrowb-cli run timeseries.<step> key=value …`.

## timeseries.frequencies

```text
timeseries.frequencies  (Frequency analysis)

Amplitude spectrum, spectral window, prewhitened multi-frequency fit and times of maximum.

inputs:      time, flux
outputs:     frequencies, grid, spectrum, residual_spectrum, window, maxima, rms, t_ref, zero_point, clean_spectrum
  time  (object)  Times
  flux  (object)  Flux
  frequencies  (object)  Frequencies
  grid  (folder)  Folder of model spectra
  spectrum  (file)  Spectrum
  residual_spectrum  (object)  Residual frequency spectrum
  window  (object)  Spectral window
  maxima  (object)  Times of maximum
  rms  (object)  Scatter of the residuals
  t_ref  (object)  Reference time
  zero_point  (object)  Zero point
  clean_spectrum  (object)  Cleaned frequency spectrum
parameters (default):
  f_max = 50.0  (float, c/d, >= 0.0)  Highest frequency: The spectrum is computed from 0 up to this frequency
  n_max = 10  (int, >= 1, <= 200)  Most frequencies: Prewhitening stops after this many frequencies
  snr_min = 4.0  (float, >= 0.0)  Smallest S/N: A peak below this signal-to-noise ends the prewhitening (Breger 1993: 4)
  magnitudes = false  (bool)  Magnitudes: The values are magnitudes (brighter is smaller), for the times of maximum
  clean = false  (bool)  CLEAN spectrum: Also a spectrum with the aliases of the sampling removed (Roberts et al. 1987)
```

## timeseries.minimum

```text
timeseries.minimum  (Time of minimum)

Time of minimum of a light curve; with t0 and period also epoch and O-C (days). detrend_with: quantities
(airmass, fwhm, sky, x, y) fitted together with the trapezoid, on the light curve before any detrending
(plans/photometry.md item 16).

inputs:      light_curve
outputs:     minimum
  light_curve  (file)  Light curve
  minimum  (object)  Time of minimum
parameters (default):
  method = "kvw"  (choice, one of kvw, trapezoid, mikulasek, gaussian, lorentzian, bisector, polynomial)  Method: Kwee–van Woerden for eclipses, a trapezoid for transits; or Mikulášek's eclipse model, a Gaussian, a Lorentzian, the bisector or a polynomial (each with its three errors)
  t0 = null  (time, d)  Reference T0: With the period: every eclipse in the curve gets its own time
  period = null  (float, d, >= 0.0)  Period: Period of the ephemeris used to count the cycles
  detrend_with = []  (table)  Detrend against: Airmass, sky, position… fitted with the transit (trapezoid only)
```

## timeseries.mission_lc

```text
timeseries.mission_lc  (Download a mission light curve)

TESS / Kepler / K2 pipeline light curves of a target from MAST, joined (needs the internet).

inputs:      target, folder
outputs:     light_curve
  target  (text)  Target
  folder  (folder)  Folder of the night's frames
  light_curve  (file)  Light curve
parameters (default):
  mission = "TESS"  (choice, one of TESS, Kepler, K2)  Mission: The space telescope whose light curves are fetched
  flux = "PDCSAP"  (text)  Flux: PDCSAP: corrected for the spacecraft; SAP: as measured
```

## timeseries.oc_fit

```text
timeseries.oc_fit  (Fit the O−C diagram)

Third-body or apsidal-motion fit to "time [error] [I/II]" lines, with MCMC errors when mcmc_steps > 0: a task,
so the page stays usable during the chain and it can be cancelled.

inputs:      minima
outputs:     fit
  minima  (object)  Times of minimum
  fit  (object)  O−C fit
parameters (default):
  model = "ltte"  (choice, one of ltte, apsidal)  Model: Third body (light-travel time) or apsidal motion
  t0 = 0.0  (time, d)  Reference T0: Epoch zero of the ephemeris
  period = 1.0  (float, d, >= 0.0)  Period: Period of the ephemeris used to count the cycles
  mcmc_steps = 0  (int, >= 0, <= 1000000)  MCMC steps: Length of the Markov chain for the errors; 0: none
```

## timeseries.period

```text
timeseries.period  (Period search)

Period search of a light curve (Lomb-Scargle, BLS, PDM or ANOVA): the periodogram and the best periods.

inputs:      time, flux
optional:    err
outputs:     periods, power, best, warnings
  time  (object)  Times
  flux  (object)  Flux
  err  (object)  Errors
  periods  (object)  Periods
  power  (object)  Periodogram
  best  (object)  Best period
  warnings  (object)  Warnings
parameters (default):
  method = "lomb-scargle"  (choice, one of lomb-scargle, bls, pdm, anova)  Method: Lomb–Scargle, box least squares (transits), phase dispersion or ANOVA
  p_min = 0.05  (float, d, >= 0.0)  Shortest period: The search starts here
  p_max = null  (float, d, >= 0.0)  Longest period: Empty: half the time span
```

## timeseries.survey_lc

```text
timeseries.survey_lc  (Download a survey light curve)

ZTF (IRSA) or AAVSO light curve of a star, one band, times in BJD_TDB (needs the internet).

inputs:      target
optional:    cache_file
outputs:     light_curve
  target  (text)  Target
  cache_file  (new_file)  File for the answers kept offline
  light_curve  (file)  Light curve
parameters (default):
  source = "ZTF"  (choice, one of ZTF, AAVSO)  Archive: Where the light curve comes from
  band = null  (band)  Band: One band of the archive; empty: the first
```
