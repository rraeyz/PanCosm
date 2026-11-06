# image

Python: `from astrowb import api; api.image.<step>(…)`; command line: `astrowb-cli run image.<step> key=value …`.

## image.catalogue

```text
image.catalogue  (Catalogue stars on the image)

Catalogue stars (Gaia DR3 or VSX from VizieR, or the AAVSO comparison sequence) inside a plate-solved image,
with their pixel positions.

inputs:      image
outputs:     stars
  image  (file)  Image
  stars  (object)  Stars
parameters (default):
  catalogue = "gaia"  (text)  Catalogue: The stars shown over the image: gaia, vsx or aavso (the AAVSO comparison sequence)
  mag_limit = 16.0  (float, mag)  Faintest magnitude: Fainter stars are left out
```

## image.convert

```text
image.convert  (Convert images)

Many FITS images to PNG / JPEG (as displayed, with the given interval and stretch) or 32-bit TIFF (the data).
Names are kept (light_001.fits -> light_001.png); an existing picture is never overwritten.

inputs:      images, output_dir
outputs:     written
  images  (files)  Images
  output_dir  (new_folder)  Folder for masters and calibrated frames
  written  (files)  Files written
parameters (default):
  fmt = "png"  (text)  Format: png, jpg or tif
  interval = "zscale"  (text)  Levels: How the black and white points are chosen
  stretch = "linear"  (text)  Stretch: linear, log, sqrt, asinh…
```

## image.finder_chart

```text
image.finder_chart  (Finder chart)

Finder chart (PNG/PDF) from a plate-solved image, or from DSS around ra/dec; comparison stars labelled with
their V magnitude x 10 from Gaia (labels left out when the catalogue cannot be reached).

inputs:      output
optional:    image, ra, dec
outputs:     chart, labelled
  output  (new_file)  Output file
  image  (file)  Image
  ra  (number)  Right ascension (°)
  dec  (number)  Declination (°)
  chart  (new_file)  Finder chart
  labelled  (object)  Labelled objects
parameters (default):
  fov_deg = 0.3  (float, °, >= 0.0)  Field of view: Width of the chart
  mag_limit = 14.0  (float, mag)  Faintest magnitude: Fainter stars are left out
  title = ""  (text)  Title: Above the chart
```

## image.minor_planets

```text
image.minor_planets  (Minor planets in the field)

Asteroids and comets inside a plate-solved image at its mid-exposure time (IMCCE SkyBoT), with pixels.

inputs:      image
outputs:     objects
  image  (file)  Image
  objects  (object)  Minor planets in the field
parameters (default):
  mag_limit = 20.0  (float, mag)  Faintest magnitude: Fainter bodies are left out
```

## image.process

```text
image.process  (Process the image)

One image operation (see io.process.OPERATIONS, or "pixel_math" with an expression and other images
named B, C, ...); the result is a new FITS file next to the input, the original is untouched.

inputs:      image, operation
optional:    others, output
outputs:     image
  image  (file)  Image
  operation  (text)  Operation
  others  (files)  Other images
  output  (new_file)  Output file
  image  (file)  Image
parameters (default):
  args = {}  (object)  Arguments: The operation's own settings
```

## image.rgb

```text
image.rgb  (Colour image from three filters)

Colour picture (PNG) from red, green and blue frames, aligned and stretched together.

inputs:      red, green, blue, output
outputs:     rgb
  red  (file)  Red frame
  green  (file)  Green frame
  blue  (file)  Blue frame
  output  (new_file)  Output file
  rgb  (new_file)  Colour image
parameters (default):
  stretch = 0.5  (float, >= 0.0)  Stretch: Lupton's stretch
  q = 8.0  (float, >= 0.0)  Softening: Lupton's Q
  align = true  (bool)  Align: The three images are aligned on their stars first
```
