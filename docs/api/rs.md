# rs

Python: `from astrowb import api; api.rs.<step>(…)`; command line: `astrowb-cli run rs.<step> key=value …`.

## rs.classify

```text
rs.classify

Unsupervised k-means classes of the chosen bands (all bands by default).

inputs:      raster
optional:    output, bands
outputs:     product
parameters (default):
  k = 5  (int, >= 2, <= 50)  Classes: How many k-means classes
```

## rs.expression

```text
rs.expression

Band math, e.g. (B8 - B4) / (B8 + B4).

inputs:      raster, expression
optional:    output, name
outputs:     product
```

## rs.pca

```text
rs.pca

Principal components of all bands (standardised).

inputs:      raster
optional:    output
outputs:     product
parameters (default):
  n = 3  (int, >= 1, <= 50)  Components: How many principal components are kept
```
