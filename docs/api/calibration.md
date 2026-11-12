# calibration

Python: `from astrowb import api; api.calibration.<step>(…)`; command line: `astrowb-cli run calibration.<step> key=value …`.

## calibration.run

```text
calibration.run

Build every master the plan needs, then calibrate every light. Missing corrections are skipped and listed.
linearity: coefficients c0, c1, c2... of the camera's linearity correction (masters.linearity), or empty.

inputs:      frames, output_dir
outputs:     masters, calibrated, missing, failed_masters, arcs, dark_scales
parameters (default):
  sigma = 3.0  (float, >= 0.0)  Sigma: Rejection limit of the masters in standard deviations
  temp_tol = 2.0  (float, °C, >= 0.0)  Temperature tolerance: A dark is used for a light within this sensor temperature
  cosmic_rays = false  (bool)  Remove cosmic rays: L.A.Cosmic (astroscrappy) on every light
  read_noise = 10.0  (float, e⁻, >= 0.0)  Read noise: For the cosmic-ray search when the header does not give it
  optimize_dark = false  (bool)  Scale the dark: The dark is scaled to remove the most noise (as PixInsight's optimisation)
  fix_defects = false  (bool)  Mend bad pixels: Hot and cold pixels found in the masters are replaced by their neighbours
  divide_flat = true  (bool)  Divide by the flat: Off: bias and dark only
  split_colour = true  (bool)  Split colour frames: A colour camera's frames become one file per colour
  linearity = []  (table)  Linearity correction: Coefficients c0, c1, c2… of the camera's linearity curve; empty: none
```

## calibration.scan

```text
calibration.scan

Camera raw files (DSLR, mirrorless) in the folder are first written as FITS to folder/fits_from_raw.
folder: calibration frames (bias / dark / flat) or everything mixed, several separated by ";"; lights: a folder
of light frames — as observers keep them (a BDF folder and a data folder), every frame there is a light whatever
its name, unless its own header states another type.

inputs:      folder
optional:    lights
outputs:     frames, problems, raw_converted
parameters (default):
  clock_utc_offset = 0.0  (float, h, >= -14.0, <= 14.0)  Camera clock − UTC: For camera raw files and pictures without a UTC time (DSLR)
```
