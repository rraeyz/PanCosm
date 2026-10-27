# photometry

Python: `from astrowb import api; api.photometry.<step>(…)`; command line: `astrowb-cli run photometry.<step> key=value …`.

## photometry.apertures

```text
photometry.apertures

Aperture and sky annulus from the stars' own profiles on the first frame given (see choose_apertures). rule
"snr": the best signal-to-noise, then the steadiest light curve of a series; "aij": AstroImageJ's radii.

inputs:      images, target_xy
optional:    comps_xy
outputs:     apertures
parameters (default):
  rule = "snr"  (choice, one of snr, aij)  Rule: snr: the radius of the best signal-to-noise; aij: AstroImageJ's, from the FWHM
```

## photometry.catalog

```text
photometry.catalog

Catalogue magnitudes (APASS / Gaia) of the comparison stars and the target, found by the image's WCS.

inputs:      image, comps_xy, target_xy
outputs:     catalog
parameters (default):
  filter = "V"  (band)  Band: The band of the standard magnitudes
```

## photometry.identify_field

```text
photometry.identify_field

The frame solved against Gaia (no solver to install), the VSX variable stars in it, and whether the OBJECT of
its header is in it (field.identify).

inputs:      image
outputs:     field
```

## photometry.light_curve

```text
photometry.light_curve

Differential aperture photometry of the target against the comparison stars on every frame: the light curve
and its table.

inputs:      images, target_xy, comps_xy
optional:    coord, extra_xy, ref_image
outputs:     light_curve
parameters (default):
  r_ap = 4.0
  r_in = 10.0
  r_out = 16.0
  gain = null
  auto_apertures = false
  follow_seeing = false
  psf = false
  aperture_m = null
  camera = null
  sky_method = "median"
  fixed = []
  header_time = "auto"
  shutter_delay = 0.0
  apertures = []
```

## photometry.multifilter

```text
photometry.multifilter

A mixed sequence of filters (plans/photometry.md item 11): a light curve per filter, with the same stars,
radii and options, and the colour-index curve of the bluer pair (multifilter.colour_curve).

inputs:      images, target_xy, comps_xy
optional:    coord, extra_xy, ref_image
outputs:     curves, colour
parameters (default):
  r_ap = 4.0
  r_in = 10.0
  r_out = 16.0
  gain = null
  auto_apertures = false
  follow_seeing = false
  psf = false
  aperture_m = null
  camera = null
  sky_method = "median"
  fixed = []
  header_time = "auto"
  shutter_delay = 0.0
  apertures = []
  t_ab = null
  comp_colour = null
```

## photometry.polarimetry

```text
photometry.polarimetry

Dual-beam linear polarimetry: ordinary and extraordinary images of one star on each frame, the
half-wave-plate angle from the header (or 0, 22.5, 45, 67.5 deg repeating in time order).

inputs:      images, o_xy, e_xy
outputs:     polarimetry
parameters (default):
  r_ap = 4.0
  r_in = 10.0
  r_out = 16.0
  angle_key = null
  zero_point = 0.0
```

## photometry.quality

```text
photometry.quality

FWHM, background, star count of every frame; "good" lists the frames that pass (for photometry/stacks).

inputs:      images
outputs:     quality, good
parameters (default):
  fwhm_factor = 1.5  (float, >= 1.0)  FWHM limit: A frame whose FWHM exceeds this times the median is bad (focus, trails)
  star_fraction = 0.5  (float, >= 0.0, <= 1.0)  Star fraction: A frame that finds fewer than this share of the stars is bad (clouds)
  background_factor = 3.0  (float, >= 1.0)  Sky limit: A frame whose sky exceeds this times the median is bad (Moon, twilight)
```

## photometry.suggest_comparisons

```text
photometry.suggest_comparisons

Comparison stars around the target. With the field identified on the marked frame (photometry.identify_field)
they come from Gaia, as Siril chooses them (field.comparison_stars); "catalogue" then holds the target's colour
and whether the stars share it. Without it, from the image (aperture.suggest_comparisons).

inputs:      images, target_xy
optional:    field
outputs:     comps_xy, catalogue
parameters (default):
  r_out = 16.0  (float, px, >= 0.0)  Outer sky radius: No other star may fall inside it
  n = 4  (int, >= 1, <= 50)  Comparison stars: How many to suggest
```

## photometry.transformation

```text
photometry.transformation

Transformation coefficients from two plate-solved images of a standard field (catalogue from VizieR).

inputs:      image_a, image_b
outputs:     transformation, stars
parameters (default):
  band_a = "B"  (band)  First band: The filter of the first image
  band_b = "V"  (band)  Second band: The filter of the second image
```

## photometry.varfind

```text
photometry.varfind

Every star of the field on every frame, and which of them vary (fieldstars.py).

inputs:      images
outputs:     field, variability
parameters (default):
  max_stars = 300  (int, >= 1)  Most stars: The brightest stars of the field that are measured
  method = "aperture"  (choice, one of aperture, psf)  Method: Aperture photometry, or PSF fitting for crowded fields
  threshold = 3.0  (float, >= 0.0)  Threshold: How many times its expected scatter a star must vary to be listed
```
