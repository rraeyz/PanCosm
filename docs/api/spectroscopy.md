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
  resolution = null  (float, >= 0.0)  Resolving power: R = λ/Δλ of the spectrograph; 0 or empty: from the spectrum
  vacuum = false  (bool)  Vacuum wavelengths: The spectrum's wavelengths are in vacuum, not air
```

## spectroscopy.classify

```text
spectroscopy.classify

Spectral type from the best-matching library templates; the Pickles library is fetched if the folder
is empty (needs the internet once).

inputs:      spectrum, library
outputs:     classes
parameters (default):
  fwhm = null  (float, Å, >= 0.0)  Resolution FWHM: The templates are smoothed to it; empty: measured from the spectrum
```

## spectroscopy.combine

```text
spectroscopy.combine

Several exposures of one star in a night combined into one spectrum (IRAF scombine), see combine.py.

inputs:      spectra
optional:    output
outputs:     combined
parameters (default):
  method = "mean"  (choice, one of mean, median, sum)  Method: mean: the least noise; median: robust; sum: keeps the counts
  rejection = "sigma"  (choice, one of none, sigma, minmax)  Rejection: Pixels left out before combining (cosmic rays, bad pixels)
  sigma = 3.0  (float, >= 0.0)  Sigma: Rejection limit in standard deviations
  scale = "median"  (choice, one of none, median, shape)  Scaling: Each spectrum to the common level (median) or also to the common shape
  weight = "none"  (choice, one of none, variance)  Weights: variance: 1/σ² weights in the mean
```

## spectroscopy.disentangle

```text
spectroscopy.disentangle

The two stars' spectra of a double-lined binary from the series and its observed velocities.

inputs:      spectra, rv1, rv2, output_dir
optional:    light_ratio
outputs:     components
parameters (default):
  iterations = 40  (int, >= 1, <= 1000)  Iterations: Rounds of shift-and-add (González & Levato 2006)
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
  first_order = null  (int, >= 1)  First order number: The physical number of the first order; empty: found
  order_step = 1  (int)  Order step: +1 or −1: how the numbers run
  optimal = true  (bool)  Optimal extraction: Horne (1986): each pixel counts by its signal-to-noise
  gain = null  (float, e⁻/ADU, >= 0.0)  Gain: Empty: from the header or the profile
  read_noise = 5.0  (float, e⁻, >= 0.0)  Read noise: For the optimal weights
  line_list = "thar"  (text)  Line list: The arc lamp's lines
  sky_lines = true  (bool)  Night-sky lines: The wavelength zero point is checked on the sky's own lines
  deg_x = 4  (int, >= 1, <= 9)  Degree along the order: Of the 2-D wavelength solution
  deg_m = 3  (int, >= 1, <= 9)  Degree across the orders: Of the 2-D wavelength solution
  min_blaze = 0.1  (float, >= 0.0, <= 1.0)  Lowest blaze: The order ends below this share of the peak are left out of the merge
  orientation = "x"  (choice, one of x, y)  Dispersion along: The axis the spectrum runs along
  reverse = false  (bool)  Reversed: Wavelength decreases along the axis
  sky = true  (bool)  Subtract the sky: From the gaps between the orders
  scatter = false  (bool)  Scattered light: A smooth scattered-light surface is subtracted first
  exclude = []  (table)  Lines left out: Arc lines kept out of the wavelength fit
  rows = null  (table)  Order rows: Where the orders cross; empty: found on the flat
  extracted = null  (object)  Extracted orders: Orders extracted elsewhere, for the wavelengths only
```

## spectroscopy.orbit

```text
spectroscopy.orbit

Keplerian orbit; double-lined (shared elements, K1 and K2) when rv2 is given.

inputs:      time, rv
optional:    error, rv2, error2
outputs:     orbit
parameters (default):
  period = null  (float, d, >= 0.0)  Period guess: Where the orbit fit starts (e.g. from the period search)
  fix_period = false  (bool)  Keep the period: The period is not fitted (known better from photometry)
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
  orientation = "x"  (choice, one of x, y)  Dispersion along: The axis the spectrum runs along
  reverse = false  (bool)  Reversed: Wavelength decreases along the axis
  rows = null  (table)  Order rows: Where the orders cross; empty: found on the flat
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
  guess_row = null  (float, px, >= 0.0)  Spectrum row: Where the spectrum crosses; empty: the brightest
  trace_row = null  (float, px, >= 0.0)  Reference trace row: A brighter spectrum whose trace shape is used (IRAF apall)
  width = 10.0  (float, px, >= 0.0)  Width: Extraction width across the spectrum
  sky_offset = 15.0  (float, px, >= 0.0)  Sky offset: Distance of the sky bands from the trace
  sky_width = 10.0  (float, px, >= 0.0)  Sky width: Width of each sky band
  optimal = true  (bool)  Optimal extraction: Horne (1986): each pixel counts by its signal-to-noise
  gain = null  (float, e⁻/ADU, >= 0.0)  Gain: Empty: from the header or the profile
  read_noise = 5.0  (float, e⁻, >= 0.0)  Read noise: For the optimal weights
  line_list = "henear"  (text)  Line list: The arc lamp's lines
  order = 5  (int, >= 1, <= 9)  Highest degree: Of the wavelength solution; the lines choose up to it
  orientation = "x"  (choice, one of x, y)  Dispersion along: The axis the spectrum runs along
  reverse = false  (bool)  Reversed: Wavelength decreases along the axis
  sky_lines = true  (bool)  Night-sky lines: The wavelength zero point is checked on the sky's own lines
  exclude = []  (table)  Lines left out: Arc lines kept out of the wavelength fit
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
  v_min = -300.0  (float, km/s)  Lowest velocity: The velocity range searched
  v_max = 300.0  (float, km/s)  Highest velocity: The velocity range searched
  wave_min = null  (float, Å, >= 0.0)  From wavelength: Only this window is used (avoid telluric bands); empty: all
  wave_max = null  (float, Å, >= 0.0)  To wavelength: Only this window is used (avoid telluric bands); empty: all
  method = "ccf"  (choice, one of ccf, bf)  Method: Cross-correlation (TODCOR with a second template) or the broadening function
  components = 1  (int, >= 1, <= 2)  Stars: How many stars the broadening function looks for
  template_rv = 0.0  (float, km/s)  Template velocity: The template's own radial velocity
  template2_rv = null  (float, km/s)  Second template velocity: The second template's own radial velocity
  template_vsini = 0.0  (float, km/s, >= 0.0)  Template v sin i: Broadens a sharp-lined template to a fast rotator
  template2_vsini = 0.0  (float, km/s, >= 0.0)  Second template v sin i: Broadens the second template the same way
```

## spectroscopy.telluric

```text
spectroscopy.telluric

Divide out the atmosphere measured in a telluric standard (strength and shift fitted).

inputs:      spectrum, standard
optional:    output
outputs:     telluric
```
