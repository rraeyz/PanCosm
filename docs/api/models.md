# models

Python: `from astrowb import api; api.models.<step>(…)`; command line: `astrowb-cli run models.<step> key=value …`.

## models.eb_fit

```text
models.eb_fit

Fit the detached-binary / transit model to a light-curve file; absolute dimensions when a
double-lined orbit is given; PHOEBE start files when export_dir is given.

inputs:      light_curve, start
optional:    orbit, export_dir
outputs:     model
parameters (default):
  free = null
  ld1 = [0.0, 0.0]
  ld2 = [0.0, 0.0]
  mcmc_steps = 0
  export_format = "phoebe"
```

## models.visual_orbit

```text
models.visual_orbit

Visual-binary orbit from "epoch theta rho [rho_err] [theta_err]" lines (see models/visual.py).

inputs:      measures
outputs:     orbit
parameters (default):
  p_min = null
  p_max = null
  parallax_mas = null
```
