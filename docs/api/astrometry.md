# astrometry

Python: `from astrowb import api; api.astrometry.<step>(…)`; command line: `astrowb-cli run astrometry.<step> key=value …`.

## astrometry.moving

```text
astrometry.moving

Positions of a moving object on plate-solved frames (marked on the first and the last frame).

inputs:      images, first_xy, last_xy
outputs:     positions, unsolved
parameters (default):
  box = 11  (int, px, >= 3, <= 101)  Box: The object is looked for in a box this wide
```

## astrometry.solve

```text
astrometry.solve

Plate-solve an image; the solution goes into a copy (<name>_wcs.fits), the original is untouched.

inputs:      image
outputs:     solved
parameters (default):
  radius_deg = 30.0  (float, °, >= 0.0, <= 180.0)  Search radius: Around the header's position
  refine_gaia = true  (bool)  Refine on Gaia: The solution is fitted again on Gaia DR3 stars (higher-order distortion)
```
