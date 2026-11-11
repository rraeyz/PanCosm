# fits

Python: `from astrowb import api; api.fits.<step>(…)`; command line: `astrowb-cli run fits.<step> key=value …`.

## fits.save_as

```text
fits.save_as

A copy of a FITS file, with header cards set or deleted on the way.

inputs:      source, destination
outputs:     destination
parameters (default):
  overwrite = false
  set_cards = {}
  delete = []
```
