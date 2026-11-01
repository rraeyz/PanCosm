# stacking

Python: `from astrowb import api; api.stacking.<step>(…)`; command line: `astrowb-cli run stacking.<step> key=value …`.

## stacking.drizzle

```text
stacking.drizzle  (Drizzle the frames)

Dithered, undersampled frames onto a finer grid (see calibration/drizzle.py); weights as extension 2.

inputs:      images, output
outputs:     stack
  images  (files)  Images
  output  (new_file)  Output file
  stack  (new_file)  Stacked image
parameters (default):
  scale = 2  (int, >= 1, <= 4)  Scale: The output pixels are this many times finer
  pixfrac = 0.6  (float, >= 0.0, <= 1.0)  Drop size: The share of each input pixel that is dropped (pixfrac)
```

## stacking.stack

```text
stacking.stack  (Stack the frames)

Calibrated frames aligned and combined into one image (mean or median, with rejection); the coverage as a
second extension.

inputs:      images, output
outputs:     stack
  images  (files)  Images
  output  (new_file)  Output file
  stack  (new_file)  Stacked image
parameters (default):
  sigma = 3.0  (float, >= 0.0)  Sigma: Rejection limit in standard deviations
  method = "mean"  (choice, one of mean, median, sum)  Combine: mean: the least noise; median: robust; sum: keeps the counts
  rejection = "sigma"  (choice, one of none, sigma, mad, winsorized, minmax, percentile)  Rejection: Pixels left out before combining (satellites, cosmic rays)
  low = 1  (float, >= 0.0)  Low: Frames or percent dropped at the low end (min / max, percentile)
  high = 1  (float, >= 0.0)  High: Frames or percent dropped at the high end (min / max, percentile)
  normalize = "none"  (choice, one of none, additive, multiplicative)  Normalise: Each frame shifted or scaled to the first before combining
  weighting = "none"  (choice, one of none, noise)  Weights: noise: 1/σ² weights
  align = "translation"  (choice, one of translation, stars)  Align: Shift only, or star patterns (rotation and scale too)
```
