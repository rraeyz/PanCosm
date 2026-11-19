# photometry

Python: `from astrowb import api; api.photometry.<step>(…)`; command line: `astrowb-cli run photometry.<step> key=value …`.

## photometry.afrho

```text
photometry.afrho  (Comet Afρ)

Afρ (A'Hearn et al. 1984) in cm from the comet's flux in a circle of physical radius ρ, the sky from a far
ring; the band's solar magnitude and the image's zero point come from the user (none is bundled).

inputs:      image, target_xy
outputs:     afrho
  image  (file)  Image
  target_xy  (xy)  Target position in the first frame (x y)
  afrho  (object)  Afρ of the comet
parameters (default):
  rho_km = 10000.0  (float, km, >= 1.0)  Aperture radius at the comet: Physical radius ρ of the measuring circle
  sky_in_km = 50000.0  (float, km, >= 1.0)  Sky ring inner radius: At the comet; far enough to hold no coma
  sky_out_km = 70000.0  (float, km, >= 1.0)  Sky ring outer radius: At the comet
  delta_au = null  (float, au, >= 0.0)  Distance from the Earth (Δ): Geocentric distance of the comet at the time of the image
  r_h_au = null  (float, au, >= 0.0)  Distance from the Sun (r): Heliocentric distance of the comet at the time of the image
  pixel_scale = null  (float, ″/px, >= 0.0)  Pixel scale: Arcseconds per pixel of the image
  zero_point = null  (float, mag)  Zero point: Magnitude of 1 ADU in this image and band
  m_sun = null  (float, mag)  The Sun's magnitude at 1 au: Apparent magnitude of the Sun in the same band, from a published table
```

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

Catalogue magnitudes of the comparison stars and the target, found by the image's WCS: source "auto" (Gaia
GSPC, APASS, the Gaia polynomials; catalog.star_magnitude) or "aavso" (the field's AAVSO sequence and chart).

inputs:      image, comps_xy, target_xy
outputs:     catalog
  image  (file)  Image
  comps_xy  (positions)  Comparison stars (x y)
  target_xy  (xy)  Target position in the first frame (x y)
  catalog  (object)  Catalogue magnitudes
parameters (default):
  filter = "V"  (band)  Band: The band of the standard magnitudes
  source = "auto"  (choice, one of auto, apass, aavso)  Magnitudes from: auto: Gaia GSPC, APASS, Gaia colours; apass: APASS first; aavso: the field's AAVSO sequence
```

## photometry.compare_minimum_methods

```text
photometry.compare_minimum_methods  (Compare timing methods)

The same minimum by each eclipse method: rows of time, error and difference from Kwee–van Woerden (s).

inputs:      light_curve
outputs:     comparison
  light_curve  (file)  Light curve
  comparison  (object)  Timing methods compared
```

## photometry.dia_curve

```text
photometry.dia_curve  (Difference-imaging light curve)

Flux change of the target on every frame relative to a reference of the sharpest frames (photometry.dia_curve),
in reference counts, with its error, the frame's scale and its mid-exposure JD (UTC).

inputs:      images, target_xy
outputs:     dia
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  dia  (object)  Difference-imaging flux changes
parameters (default):
  n_best = 5  (int, >= 1)  Frames in the reference: The frames of smallest FWHM that are combined into the reference
  fwhm = 3.0  (float, px, >= 0.5)  FWHM: Of the reference frame's stars; the PSF the flux changes are fitted with
```

## photometry.identify_field

```text
photometry.identify_field  (Identify the field)

The frame solved against Gaia (no solver to install), the VSX variable stars in it, and whether the OBJECT of
its header is in it (field.identify). fresh: the catalogues asked again, not read from the saved answers.

inputs:      image
outputs:     field
  image  (file)  Image
  field  (object)  Identified field
parameters (default):
  fresh = false  (bool)  Ask the catalogues again: Not the answers saved from an earlier look-up
```

## photometry.isophotes

```text
photometry.isophotes  (Isophotes (surface brightness profile))

Ellipses fitted round the object (photutils isophote): semi-major axis, intensity and its error, ellipticity,
position angle; with a zero point and a pixel scale (arcsec) also the surface brightness in mag arcsec⁻².

inputs:      image, target_xy
outputs:     isophotes
  image  (file)  Image
  target_xy  (xy)  Target position in the first frame (x y)
  isophotes  (object)  Isophote profile
parameters (default):
  sma0 = 10.0  (float, px, >= 1.0)  First semi-major axis: The ellipse the fit starts from
  eps = 0.2  (float, >= 0.0, <= 0.95)  First ellipticity: 1 − b/a of the first ellipse
  pa_deg = 0.0  (float, °)  First position angle: From the +x axis, counter-clockwise
  zero_point = null  (float, mag)  Zero point: With the pixel scale: the surface brightness in mag/arcsec²
  pixel_scale = null  (float, ″/px, >= 0.0)  Pixel scale: With the zero point: the surface brightness in mag/arcsec²
```

## photometry.light_curve

```text
photometry.light_curve  (Measure the light curve)

Differential aperture photometry of the target against the comparison stars on every frame: the light curve
and its table.

inputs:      images, target_xy, comps_xy
optional:    coord, extra_xy, ref_image, stars_sky
outputs:     light_curve
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  comps_xy  (positions)  Comparison stars (x y)
  coord  (sky)  Sky position of the target
  extra_xy  (positions)  Check stars and other targets (x y)
  ref_image  (file)  Frame the stars were marked on
  stars_sky  (object)  The stars by the sky (RA, Dec)
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
  sky_method = "median"  (choice, one of median, mode, mean, plane, centroid)  Sky: How the sky level is read
  fixed = []  (table)  Fixed positions: Stars measured where marked, not re-centred
  header_time = "auto"  (choice, one of auto, start, mid, end)  Header time marks: What the header's time marks: the start, middle or end of the exposure
  shutter_delay = 0.0  (float, s)  Shutter delay: Added to the header time
  apertures = []  (table)  Other radii: More aperture radii measured at the same time
  remove_neighbours = false  (bool)  Remove neighbours: Stars near the measured ones are fitted and subtracted before the apertures
  centring = "auto"  (choice, one of auto, moments, gauss, none)  Centring: How each star is centred on every frame
  box = 11  (int, px, >= 3)  Centring box: Width of the box a star is centred in
  max_move = 2.5  (float, px, >= 0.0)  Largest centring move: A centroid farther than this from the predicted place is not used
  track_stars = []  (positions)  Stars that place the frames: Picked on the first frame; empty: the frames are placed automatically
  combine = 1  (int, >= 1, <= 100)  Combine frames: Faint targets: groups of this many frames aligned and added before measuring; 1: each frame
  aperture_shape = null  (object)  Aperture shape: Empty: circles; {"kind": "ellipse", "ratio", "angle"} or {"kind": "racetrack", "length", "angle"} for stretched or trailed stars
  trails = false  (bool)  Look for trails: Flag the frames where a satellite or aircraft trail crosses an aperture (2-3 s more per 2k frame)
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
  sky_method = "median"  (choice, one of median, mode, mean, plane, centroid)  Sky: How the sky level is read
  fixed = []  (table)  Fixed positions: Stars measured where marked, not re-centred
  header_time = "auto"  (choice, one of auto, start, mid, end)  Header time marks: What the header's time marks: the start, middle or end of the exposure
  shutter_delay = 0.0  (float, s)  Shutter delay: Added to the header time
  apertures = []  (table)  Other radii: More aperture radii measured at the same time
  remove_neighbours = false  (bool)  Remove neighbours: Stars near the measured ones are fitted and subtracted before the apertures
  centring = "auto"  (choice, one of auto, moments, gauss, none)  Centring: How each star is centred on every frame
  box = 11  (int, px, >= 3)  Centring box: Width of the box a star is centred in
  max_move = 2.5  (float, px, >= 0.0)  Largest centring move: A centroid farther than this from the predicted place is not used
  track_stars = []  (positions)  Stars that place the frames: Picked on the first frame; empty: the frames are placed automatically
  combine = 1  (int, >= 1, <= 100)  Combine frames: Faint targets: groups of this many frames aligned and added before measuring; 1: each frame
  aperture_shape = null  (object)  Aperture shape: Empty: circles; {"kind": "ellipse", "ratio", "angle"} or {"kind": "racetrack", "length", "angle"} for stretched or trailed stars
  trails = false  (bool)  Look for trails: Flag the frames where a satellite or aircraft trail crosses an aperture (2-3 s more per 2k frame)
  t_ab = null  (float)  Colour coefficient: T_ab of the transformation; with the comparison colour, a standard colour
  comp_colour = null  (float, mag)  Comparison colour: The comparison ensemble's catalogue colour
```

## photometry.neb_check

```text
photometry.neb_check  (Nearby-eclipsing-binary check)

Nearby-eclipsing-binary check (TFOP): every Gaia star near the target that could make the depth, measured on
every frame, with its disposition (photometry.neb).

inputs:      images, target_xy, comps_xy, field
outputs:     neb
  images  (files)  Images
  target_xy  (xy)  Target position in the first frame (x y)
  comps_xy  (positions)  Comparison stars (x y)
  field  (object)  Identified field
  neb  (object)  Nearby-eclipsing-binary check
parameters (default):
  depth_ppt = 5.0  (float, ppt, >= 0.0)  Transit depth: The depth TESS saw on the target
  radius_arcsec = 150.0  (float, ″, >= 0.0)  Search radius: Stars this near the target are checked (TFOP: 2.5′)
  r_ap = 6.0  (float, px, >= 0.5)  Aperture radius: As the light curve's
  r_in = 10.0  (float, px, >= 0.5)  Sky ring, inner radius: As the light curve's
  r_out = 16.0  (float, px, >= 0.5)  Sky ring, outer radius: As the light curve's
  tc = 0.0  (float, d)  Predicted mid-transit: JD (UTC); 0: no box fit
  duration_h = 0.0  (float, h, >= 0.0)  Transit duration: T14; with the mid-transit time, a box is fitted there on every star
  apertures = []  (table)  Several apertures: [radius, sky inner, sky outer] triples; each star keeps its best disposition. Empty: the one aperture above
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

## photometry.save_light_curve

```text
photometry.save_light_curve  (Save the light-curve file)

The light curve written as a .lc.ecsv file (photometry/lcfile.py: every series and value kept), as File →
Export in the window writes it; a recipe's last step (PHO-20).

inputs:      light_curve, output
outputs:     file
  light_curve  (file)  Light curve
  output  (new_file)  Output file
  file  (new_file)  Light-curve file (.lc.ecsv)
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
  rules = null  (object)  Comparison-star rules: The rules' settings; each star left out is given its reason (with a field)
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

## photometry.transit_fit

```text
photometry.transit_fit  (Fit the transit)

The exact transit (quadratic limb darkening) with the chosen detrending; values, errors, derived values and
fit statistics (photometry.transitfit).

inputs:      light_curve
outputs:     transit
  light_curve  (file)  Light curve
  transit  (object)  Transit fit
parameters (default):
  period = 1.0  (float, d, >= 0.0)  Period: Fixed for a single transit
  tc = 0.0  (float, d)  Mid-transit time (start): 0: the middle of the night
  k = 0.1  (float, >= 0.0, <= 0.5)  Radius ratio (start): Rp/R★; the square root of the depth
  a_rs = 8.0  (float, >= 1.0)  Scaled distance (start): a/R★
  b = 0.3  (float, >= 0.0, <= 1.5)  Impact parameter (start): 0: across the centre of the star
  u1 = 0.4  (float)  Limb darkening u1: Quadratic law; fixed unless chosen to fit
  u2 = 0.2  (float)  Limb darkening u2: Quadratic law; fixed unless chosen to fit
  eclipse = false  (bool)  Fit the eclipse: The secondary eclipse (circular orbit, half a period after the transit) instead of the transit; the shape stays as given
  occ = 0.001  (float, >= 0.0, <= 5.0)  Eclipse depth (start): The companion's light as a fraction of the star's
  detrend = "airmass"  (text)  Detrend against: Comma-separated: airmass, fwhm, sky, x, y (empty: none)
  fit_ld = false  (bool)  Fit the limb darkening: A single night rarely decides it: leave it fixed
  red_noise = false  (bool)  Account for red noise: The errors multiplied by β, the time-averaging factor of the residuals
  mcmc_steps = 0  (int, >= 0, <= 100000)  MCMC steps: Posterior errors after the fit (the chains stop earlier once converged); 0: none
```

## photometry.varfind

```text
photometry.varfind  (Search for variable stars)

Every star of the field on every frame, and which of them vary (fieldstars.py).

inputs:      images
outputs:     field, variability, candidate_periods
  images  (files)  Images
  field  (object)  Identified field
  variability  (object)  Variability of the stars
  candidate_periods  (object)  Quick period of each candidate
parameters (default):
  max_stars = 300  (int, >= 1)  Most stars: The brightest stars of the field that are measured
  method = "aperture"  (choice, one of aperture, psf)  Method: Aperture photometry, or PSF fitting for crowded fields
  threshold = 3.0  (float, >= 0.0)  Threshold: How many times its expected scatter a star must vary to be listed
```
