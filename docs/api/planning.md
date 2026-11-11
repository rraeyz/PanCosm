# planning

Python: `from astrowb import api; api.planning.<step>(…)`; command line: `astrowb-cli run planning.<step> key=value …`.

## planning.ephemeris

```text
planning.ephemeris

Coordinates, period, epoch and duration from VSX or the NASA Exoplanet Archive.

inputs:      name
outputs:     target
parameters (default):
  catalogue = "auto"
```

## planning.night

```text
planning.night

targets: [{name, ra, dec, [t0, period, duration, secondary]}]; times in JD (UTC).

inputs:      site, date, targets
outputs:     night
parameters (default):
  min_alt = 20.0
  step_min = 5.0
```

## planning.resolve

```text
planning.resolve

Coordinates of a target name (SIMBAD), kept in a cache file for later nights.

inputs:      name, cache_file
outputs:     target
```
