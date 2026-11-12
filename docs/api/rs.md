# rs

Python: `from astrowb import api; api.rs.<step>(…)`; command line: `astrowb-cli run rs.<step> key=value …`.

## rs.classify

```text
rs.classify  (Classify (k-means))

Unsupervised k-means classes of the chosen bands (all bands by default).

inputs:      raster
optional:    output, bands
outputs:     product
  raster  (file)  Raster image
  output  (new_file)  Output file
  bands  (text)  Bands
  product  (new_file)  Product image
parameters (default):
  k = 5  (int, >= 2, <= 50)  Classes: How many k-means classes
```

## rs.expression

```text
rs.expression  (Compute a band formula)

Band math, e.g. (B8 - B4) / (B8 + B4).

inputs:      raster, expression
optional:    output, name
outputs:     product
  raster  (file)  Raster image
  expression  (text)  Band formula
  output  (new_file)  Output file
  name  (text)  Name
  product  (new_file)  Product image
```

## rs.pca

```text
rs.pca  (Principal components)

Principal components of all bands (standardised).

inputs:      raster
optional:    output
outputs:     product
  raster  (file)  Raster image
  output  (new_file)  Output file
  product  (new_file)  Product image
parameters (default):
  n = 3  (int, >= 1, <= 50)  Components: How many principal components are kept
```
