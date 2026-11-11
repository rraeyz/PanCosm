# stacking

Python: `from astrowb import api; api.stacking.<step>(…)`; command line: `astrowb-cli run stacking.<step> key=value …`.

## stacking.drizzle

```text
stacking.drizzle

Dithered, undersampled frames onto a finer grid (see calibration/drizzle.py); weights as extension 2.

inputs:      images, output
outputs:     stack
parameters (default):
  scale = 2
  pixfrac = 0.6
```

## stacking.stack

```text
stacking.stack

Calibrated frames aligned and combined into one image (mean or median, with rejection); the coverage as a
second extension.

inputs:      images, output
outputs:     stack
parameters (default):
  sigma = 3.0
  method = "mean"
  rejection = "sigma"
  low = 1
  high = 1
  normalize = "none"
  weighting = "none"
  align = "translation"
```
