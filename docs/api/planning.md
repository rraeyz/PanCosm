# planning

Python: `from astrowb import api; api.planning.<step>(…)`; command line: `astrowb-cli run planning.<step> key=value …`.

## planning.ephemeris

```text
planning.ephemeris  (Look up the ephemeris)

Coordinates, period, epoch and duration from VSX or the NASA Exoplanet Archive.

inputs:      name
outputs:     target
  name  (text)  Name
parameters (default):
  catalogue = "auto"  (text)  Catalogue: auto: VSX for variable stars, the NASA Exoplanet Archive for planets
```

## planning.night

```text
planning.night  (Plan the night)

targets: [{name, ra, dec, [t0, period, duration, secondary]}]; times in JD (UTC).

inputs:      site, date, targets
outputs:     night
  site  (object)  Observatory site
  date  (date)  Date of the night
  targets  (object)  Targets
parameters (default):
  min_alt = 20.0  (float, °, >= 0.0, <= 90.0)  Lowest altitude: A target lower than this is not observable
  step_min = 5.0  (float, min, >= 0.1)  Time step: The night is computed at this spacing
```

## planning.resolve

```text
planning.resolve  (Find the target)

Coordinates of a target name (SIMBAD), kept in a cache file for later nights.

inputs:      name, cache_file
outputs:     target
  name  (text)  Name
  cache_file  (new_file)  File for the answers kept offline
```
