# image

Python: `from astrowb import api; api.image.<step>(…)`; command line: `astrowb-cli run image.<step> key=value …`.

## image.catalogue

```text
image.catalogue

Catalogue stars (Gaia DR3 or VSX, from VizieR) inside a plate-solved image, with their pixel positions.

inputs:      image
outputs:     stars
parameters (default):
  catalogue = "gaia"
  mag_limit = 16.0
```

## image.convert

```text
image.convert

Many FITS images to PNG / JPEG (as displayed, with the given interval and stretch) or 32-bit TIFF (the data).
Names are kept (light_001.fits -> light_001.png); an existing picture is never overwritten.

inputs:      images, output_dir
outputs:     written
parameters (default):
  fmt = "png"
  interval = "zscale"
  stretch = "linear"
```

## image.finder_chart

```text
image.finder_chart

Finder chart (PNG/PDF) from a plate-solved image, or from DSS around ra/dec; comparison stars labelled with
their V magnitude x 10 from Gaia (labels left out when the catalogue cannot be reached).

inputs:      output
optional:    image, ra, dec
outputs:     chart, labelled
parameters (default):
  fov_deg = 0.3
  mag_limit = 14.0
  title = ""
```

## image.minor_planets

```text
image.minor_planets

Asteroids and comets inside a plate-solved image at its mid-exposure time (IMCCE SkyBoT), with pixels.

inputs:      image
outputs:     objects
parameters (default):
  mag_limit = 20.0
```

## image.process

```text
image.process

One image operation (see io.process.OPERATIONS, or "pixel_math" with an expression and other images
named B, C, ...); the result is a new FITS file next to the input, the original is untouched.

inputs:      image, operation
optional:    others, output
outputs:     image
parameters (default):
  args = {}
```

## image.rgb

```text
image.rgb

Colour picture (PNG) from red, green and blue frames, aligned and stretched together.

inputs:      red, green, blue, output
outputs:     rgb
parameters (default):
  stretch = 0.5
  q = 8.0
  align = true
```
