# spectroscopy

Python: `from astrowb import api; api.spectroscopy.<step>(…)`; command line: `astrowb-cli run spectroscopy.<step> key=value …`.

## spectroscopy.atmosphere

```text
spectroscopy.atmosphere

Teff, log g, [Fe/H], v sin i and RV of an FGK star relative to the Sun (spectroscopy/atmosphere.py).
grid: a folder of synthetic spectra (else PHOENIX points are downloaded into `cache` as needed); sun: a solar
spectrum taken with the same spectrograph (else the Kurucz solar atlas, downloaded once); resolution: the
spectrograph's R = lambda / FWHM.

inputs:      spectrum, cache
optional:    grid, sun
outputs:     atmosphere
parameters (default):
  resolution = null
  vacuum = false
```

## spectroscopy.classify

```text
spectroscopy.classify

Spectral type from the best-matching library templates; the Pickles library is fetched if the folder
is empty (needs the internet once).

inputs:      spectrum, library
outputs:     classes
parameters (default):
  fwhm = null
```

## spectroscopy.combine

```text
spectroscopy.combine

Several exposures of one star in a night combined into one spectrum (IRAF scombine), see combine.py.

inputs:      spectra
optional:    output
outputs:     combined
parameters (default):
  method = "mean"
  rejection = "sigma"
  sigma = 3.0
  scale = "median"
  weight = "none"
```

## spectroscopy.disentangle

```text
spectroscopy.disentangle

The two stars' spectra of a double-lined binary from the series and its observed velocities.

inputs:      spectra, rv1, rv2, output_dir
optional:    light_ratio
outputs:     components
parameters (default):
  iterations = 40
```

## spectroscopy.echelle

```text
spectroscopy.echelle

Echelle / cross-dispersed frame -> orders -> one merged spectrum.

Orders are traced on the flat (or on the science frame when no flat is given); the flat also
gives the blaze. With an arc, `first_order` (absolute number of the lowest traced order,
numbers changing by `order_step` upwards) and identified lines [(order, pixel, wavelength), ...]
the global 2-D wavelength solution is fitted and the merged spectrum written to `output`.
sky=False for fibre-fed spectrographs whose orders leave no sky between them. scatter: subtract the
scattered light (from the gaps between the orders) from the science frame and the flat first. exclude:
[(order, pixel)] arc lines left out of the wavelength solution by hand. rows: the orders' rows at the central
column as checked by hand on the Echelle tab (None: found automatically). With an output file the orders
are also written one by one (<output>_orders.fits: flux, error and wavelength images, one row per order).
extracted: the science frame (and the flat and arc with it) is already extracted, one row per order (IRAF apall
output, a pipeline's e2ds): wavelengths only, as IRAF ecidentify; None: from the header (looks_extracted).

inputs:      science
optional:    flat, arc, guesses, output
outputs:     echelle
parameters (default):
  first_order = null
  order_step = 1
  optimal = true
  gain = null
  read_noise = 5.0
  line_list = "thar"
  sky_lines = true
  deg_x = 4
  deg_m = 3
  min_blaze = 0.1
  orientation = "x"
  reverse = false
  sky = true
  scatter = false
  exclude = []
  rows = null
  extracted = null
```

## spectroscopy.orbit

```text
spectroscopy.orbit

Keplerian orbit; double-lined (shared elements, K1 and K2) when rv2 is given.

inputs:      time, rv
optional:    error, rv2, error2
outputs:     orbit
parameters (default):
  period = null
  fix_period = false
```

## spectroscopy.orders

```text
spectroscopy.orders

Orders of an echelle flat (or bright star) found and traced, to be checked on the Echelle tab: rows at the
central column, trace coefficients, and the rows that could not be traced. rows: start from these instead of
the automatic search (after the user removed or added orders).

inputs:      image
outputs:     orders
parameters (default):
  orientation = "x"
  reverse = false
  rows = null
```

## spectroscopy.reduce

```text
spectroscopy.reduce

2-D long-slit/slitless frame (dispersion along x) -> 1-D spectrum; wavelengths from an arc
when an arc and at least two identified (pixel, wavelength) pairs are given.

inputs:      science
optional:    arc, guesses, output
outputs:     spectrum
parameters (default):
  guess_row = null
  trace_row = null
  width = 10.0
  sky_offset = 15.0
  sky_width = 10.0
  optimal = true
  gain = null
  read_noise = 5.0
  line_list = "henear"
  order = 5
  orientation = "x"
  reverse = false
  sky_lines = true
  exclude = []
```

## spectroscopy.rv

```text
spectroscopy.rv

Radial velocity of each spectrum against a template, barycentric-corrected when the header
gives the time and the sky position (or coord) and a site is known. With a second template
(double-lined binary) both components are measured with TODCOR. method="bf": the broadening
function with `components` rotational profiles (fast rotators, contact binaries); also v sin i.
template_rv / template2_rv: the templates' own velocities (km/s; a real star's spectrum is not at rest: tau
Ceti -16.5, put on every velocity of TZ For); the second defaults to the first. template_vsini / template2_vsini:
the templates' lines broadened by rotation (km/s) to match each star (a fast rotator against a sharp template).

inputs:      spectra, template
optional:    coord, site, template2
outputs:     rvs, skipped
parameters (default):
  v_min = -300.0
  v_max = 300.0
  wave_min = null
  wave_max = null
  method = "ccf"
  components = 1
  template_rv = 0.0
  template2_rv = null
  template_vsini = 0.0
  template2_vsini = 0.0
```

## spectroscopy.telluric

```text
spectroscopy.telluric

Divide out the atmosphere measured in a telluric standard (strength and shift fitted).

inputs:      spectrum, standard
optional:    output
outputs:     telluric
```
