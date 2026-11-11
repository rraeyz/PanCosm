# timeseries

Python: `from astrowb import api; api.timeseries.<step>(…)`; command line: `astrowb-cli run timeseries.<step> key=value …`.

## timeseries.frequencies

```text
timeseries.frequencies

Amplitude spectrum, spectral window, prewhitened multi-frequency fit and times of maximum.

inputs:      time, flux
outputs:     frequencies, grid, spectrum, residual_spectrum, window, maxima, rms, t_ref, zero_point, clean_spectrum
parameters (default):
  f_max = 50.0
  n_max = 10
  snr_min = 4.0
  magnitudes = false
  clean = false
```

## timeseries.minimum

```text
timeseries.minimum

Time of minimum of a light curve; with t0 and period also epoch and O-C (days). detrend_with: quantities
(airmass, fwhm, sky, x, y) fitted together with the trapezoid, on the light curve before any detrending
(plans/photometry.md item 16).

inputs:      light_curve
outputs:     minimum
parameters (default):
  method = "kvw"
  t0 = null
  period = null
  detrend_with = []
```

## timeseries.mission_lc

```text
timeseries.mission_lc

TESS / Kepler / K2 pipeline light curves of a target from MAST, joined (needs the internet).

inputs:      target, folder
outputs:     light_curve
parameters (default):
  mission = "TESS"
  flux = "PDCSAP"
```

## timeseries.oc_fit

```text
timeseries.oc_fit

Third-body or apsidal-motion fit to "time [error] [I/II]" lines, with MCMC errors when mcmc_steps > 0: a task,
so the page stays usable during the chain and it can be cancelled.

inputs:      minima
outputs:     fit
parameters (default):
  model = "ltte"
  t0 = 0.0
  period = 1.0
  mcmc_steps = 0
```

## timeseries.period

```text
timeseries.period

Period search of a light curve (Lomb-Scargle, BLS, PDM or ANOVA): the periodogram and the best periods.

inputs:      time, flux
optional:    err
outputs:     periods, power, best, warnings
parameters (default):
  method = "lomb-scargle"
  p_min = 0.05
  p_max = null
```

## timeseries.survey_lc

```text
timeseries.survey_lc

ZTF (IRSA) or AAVSO light curve of a star, one band, times in BJD_TDB (needs the internet).

inputs:      target
optional:    cache_file
outputs:     light_curve
parameters (default):
  source = "ZTF"
  band = null
```
