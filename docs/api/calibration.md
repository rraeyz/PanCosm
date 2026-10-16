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
  sigma = 3.0
  temp_tol = 2.0
  cosmic_rays = false
  read_noise = 10.0
  optimize_dark = false
  fix_defects = false
  divide_flat = true
  split_colour = true
  linearity = []
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
  clock_utc_offset = 0.0
```
