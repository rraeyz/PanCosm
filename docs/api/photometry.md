# photometry

Python: `from astrowb import api; api.photometry.<step>(…)`; command line: `astrowb-cli run photometry.<step> key=value …`.

## photometry.apertures

```text
photometry.apertures  (Choose the aperture radii)

Aperture and sky annulus from the stars' own profiles on the first frame given (see choose_apertures). rule
"snr": the best signal-to-noise, then the steadiest light curve of a series; "aij": AstroImageJ's radii.

inputs:      images, target_xy
optional:    comps_xy
outputs:     apertures
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  comps_xy  (positions)  Comparison stars (x y)
  apertures  (object)  Measurements at each aperture radius
parameters (default):
  rule = "snr"  (choice, one of snr, aij)  Rule: snr: the radius of the best signal-to-noise; aij: AstroImageJ's, from the FWHM
```

## photometry.catalog

```text
photometry.catalog  (Standard magnitudes from a catalogue)

Catalogue magnitudes (APASS / Gaia) of the comparison stars and the target, found by the image's WCS.

inputs:      image, comps_xy, target_xy
outputs:     catalog
  image  (file)  Image
  comps_xy  (positions)  Comparison stars (x y)
  target_xy  (xy)  Target position in the first frame (x y)
  catalog  (object)  Catalogue magnitudes
parameters (default):
  filter = "V"  (band)  Band: The band of the standard magnitudes
```

## photometry.identify_field

```text
photometry.identify_field  (Identify the field)

The frame solved against Gaia (no solver to install), the VSX variable stars in it, and whether the OBJECT of
its header is in it (field.identify).

inputs:      image
outputs:     field
  image  (file)  Image
  field  (object)  Identified field
```

## photometry.light_curve

```text
photometry.light_curve  (Measure the light curve)

Differential aperture photometry of the target against the comparison stars on every frame: the light curve
and its table.

inputs:      images, target_xy, comps_xy
optional:    coord, extra_xy, ref_image
outputs:     light_curve
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  comps_xy  (positions)  Comparison stars (x y)
  coord  (sky)  Sky position of the target
  extra_xy  (positions)  Check stars and other targets (x y)
  ref_image  (file)  Frame the stars were marked on
  light_curve  (file)  Light curve
parameters (default):
  r_ap = 4.0  (float, px, >= 0.0)  Aperture radius: Light inside it is the star's
  r_in = 10.0  (float, px, >= 0.0)  Inner sky radius: The sky annulus starts here
  r_out = 16.0  (float, px, >= 0.0)  Outer sky radius: The sky annulus ends here
  gain = null  (float, e⁻/ADU, >= 0.0)  Gain: Empty: from the header or the profile
  auto_apertures = false  (bool)  Radii from the profiles: The radii are chosen from the stars' own profiles
  follow_seeing = false  (bool)  Scale radii with seeing: Each frame's radii follow its FWHM
  psf = false  (bool)  PSF photometry: Stars fitted with the frame's PSF (crowded fields)
  aperture_m = null  (float, m, >= 0.0)  Telescope aperture: For the scintillation noise (Young 1967); empty: left out
  camera = null  (object)  Camera: Read noise, dark current and linearity when the header lacks them
  sky_method = "median"  (choice, one of median, mode, mean, plane)  Sky: How the sky level is read
  fixed = []  (table)  Fixed positions: Stars measured where marked, not re-centred
  header_time = "auto"  (choice, one of auto, start, mid, end)  Header time marks: What the header's time marks: the start, middle or end of the exposure
  shutter_delay = 0.0  (float, s)  Shutter delay: Added to the header time
  apertures = []  (table)  Other radii: More aperture radii measured at the same time
```

## photometry.multifilter

```text
photometry.multifilter  (Measure every filter and the colour index)

A mixed sequence of filters (plans/photometry.md item 11): a light curve per filter, with the same stars,
radii and options, and the colour-index curve of the bluer pair (multifilter.colour_curve).

inputs:      images, target_xy, comps_xy
optional:    coord, extra_xy, ref_image
outputs:     curves, colour
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  comps_xy  (positions)  Comparison stars (x y)
  coord  (sky)  Sky position of the target
  extra_xy  (positions)  Check stars and other targets (x y)
  ref_image  (file)  Frame the stars were marked on
  curves  (object)  Light curves
  colour  (object)  Colour curve
parameters (default):
  r_ap = 4.0  (float, px, >= 0.0)  Aperture radius: Light inside it is the star's
  r_in = 10.0  (float, px, >= 0.0)  Inner sky radius: The sky annulus starts here
  r_out = 16.0  (float, px, >= 0.0)  Outer sky radius: The sky annulus ends here
  gain = null  (float, e⁻/ADU, >= 0.0)  Gain: Empty: from the header or the profile
  auto_apertures = false  (bool)  Radii from the profiles: The radii are chosen from the stars' own profiles
  follow_seeing = false  (bool)  Scale radii with seeing: Each frame's radii follow its FWHM
  psf = false  (bool)  PSF photometry: Stars fitted with the frame's PSF (crowded fields)
  aperture_m = null  (float, m, >= 0.0)  Telescope aperture: For the scintillation noise (Young 1967); empty: left out
  camera = null  (object)  Camera: Read noise, dark current and linearity when the header lacks them
  sky_method = "median"  (choice, one of median, mode, mean, plane)  Sky: How the sky level is read
  fixed = []  (table)  Fixed positions: Stars measured where marked, not re-centred
  header_time = "auto"  (choice, one of auto, start, mid, end)  Header time marks: What the header's time marks: the start, middle or end of the exposure
  shutter_delay = 0.0  (float, s)  Shutter delay: Added to the header time
  apertures = []  (table)  Other radii: More aperture radii measured at the same time
  t_ab = null  (float)  Colour coefficient: T_ab of the transformation; with the comparison colour, a standard colour
  comp_colour = null  (float, mag)  Comparison colour: The comparison ensemble's catalogue colour
```

## photometry.polarimetry

```text
photometry.polarimetry  (Polarimetry)

Dual-beam linear polarimetry: ordinary and extraordinary images of one star on each frame, the
half-wave-plate angle from the header (or 0, 22.5, 45, 67.5 deg repeating in time order).

inputs:      images, o_xy, e_xy
outputs:     polarimetry
  images  (files)  Images
  o_xy  (positions)  Ordinary images (x y)
  e_xy  (positions)  Extraordinary images (x y)
  polarimetry  (object)  Polarisation
parameters (default):
  r_ap = 4.0  (float, px, >= 0.0)  Aperture radius: Light inside it is the star's
  r_in = 10.0  (float, px, >= 0.0)  Inner sky radius: The sky annulus starts here
  r_out = 16.0  (float, px, >= 0.0)  Outer sky radius: The sky annulus ends here
  angle_key = null  (text)  Angle keyword: The header keyword of the half-wave plate angle
  zero_point = 0.0  (float, °)  Angle zero point: Added to the measured position angle
```

## photometry.quality

```text
photometry.quality  (Find the bad frames)

FWHM, background, star count of every frame; "good" lists the frames that pass (for photometry/stacks).

inputs:      images
outputs:     quality, good
  images  (files)  Images
  quality  (object)  Frame quality
  good  (files)  Good frames
parameters (default):
  fwhm_factor = 1.5  (float, >= 1.0)  FWHM limit: A frame whose FWHM exceeds this times the median is bad (focus, trails)
  star_fraction = 0.5  (float, >= 0.0, <= 1.0)  Star fraction: A frame that finds fewer than this share of the stars is bad (clouds)
  background_factor = 3.0  (float, >= 1.0)  Sky limit: A frame whose sky exceeds this times the median is bad (Moon, twilight)
```

## photometry.suggest_comparisons

```text
photometry.suggest_comparisons  (Suggest comparison stars)

Comparison stars around the target. With the field identified on the marked frame (photometry.identify_field)
they come from Gaia, as Siril chooses them (field.comparison_stars); "catalogue" then holds the target's colour
and whether the stars share it. Without it, from the image (aperture.suggest_comparisons).

inputs:      images, target_xy
optional:    field
outputs:     comps_xy, catalogue
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  field  (object)  Identified field
  comps_xy  (positions)  Comparison stars (x y)
  catalogue  (object)  Catalogue stars
parameters (default):
  r_out = 16.0  (float, px, >= 0.0)  Outer sky radius: No other star may fall inside it
  n = 4  (int, >= 1, <= 50)  Comparison stars: How many to suggest
```

## photometry.transformation

```text
photometry.transformation  (Transformation coefficients)

Transformation coefficients from two plate-solved images of a standard field (catalogue from VizieR).

inputs:      image_a, image_b
outputs:     transformation, stars
  image_a  (file)  Image in the first filter
  image_b  (file)  Image in the second filter
  transformation  (object)  Transformation coefficients
  stars  (object)  Stars
parameters (default):
  band_a = "B"  (band)  First band: The filter of the first image
  band_b = "V"  (band)  Second band: The filter of the second image
```

## photometry.varfind

```text
photometry.varfind  (Search for variable stars)

Every star of the field on every frame, and which of them vary (fieldstars.py).

inputs:      images
outputs:     field, variability
  images  (files)  Images
  field  (object)  Identified field
  variability  (object)  Variability of the stars
parameters (default):
  max_stars = 300  (int, >= 1)  Most stars: The brightest stars of the field that are measured
  method = "aperture"  (choice, one of aperture, psf)  Method: Aperture photometry, or PSF fitting for crowded fields
  threshold = 3.0  (float, >= 0.0)  Threshold: How many times its expected scatter a star must vary to be listed
```
