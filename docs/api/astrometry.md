# astrometry

Python: `from astrowb import api; api.astrometry.<step>(…)`; command line: `astrowb-cli run astrometry.<step> key=value …`.

## astrometry.moving

```text
astrometry.moving

Positions of a moving object on plate-solved frames (marked on the first and the last frame).

inputs:      images, first_xy, last_xy
outputs:     positions, unsolved
parameters (default):
  box = 11
```

## astrometry.solve

```text
astrometry.solve

Plate-solve an image; the solution goes into a copy (<name>_wcs.fits), the original is untouched.

inputs:      image
outputs:     solved
parameters (default):
  radius_deg = 30.0
  refine_gaia = true
```
