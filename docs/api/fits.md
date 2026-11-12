# fits

Python: `from astrowb import api; api.fits.<step>(…)`; command line: `astrowb-cli run fits.<step> key=value …`.

## fits.save_as

```text
fits.save_as

A copy of a FITS file, with header cards set or deleted on the way.

inputs:      source, destination
outputs:     destination
parameters (default):
  overwrite = false  (bool)  Overwrite: An existing file of that name is replaced
  set_cards = {}  (object)  Header cards to set: Keyword: value pairs written into the header
  delete = []  (table)  Header cards to delete: Keywords taken out of the header
```
