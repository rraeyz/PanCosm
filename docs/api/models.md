# models

Python: `from astrowb import api; api.models.<step>(…)`; command line: `astrowb-cli run models.<step> key=value …`.

## models.eb_fit

```text
models.eb_fit  (Fit the light-curve model)

Fit the detached-binary / transit model to a light-curve file; absolute dimensions when a
double-lined orbit is given; PHOEBE start files when export_dir is given.

inputs:      light_curve, start
optional:    orbit, export_dir
outputs:     model
  light_curve  (file)  Light curve
  start  (object)  Starting values
  orbit  (object)  Spectroscopic orbit
  export_dir  (new_folder)  Folder for the exported files
parameters (default):
  free = null  (object)  Free parameters: The model's parameters that are fitted; empty: the usual set
  ld1 = [0.0, 0.0]  (table)  Limb darkening, star 1: Quadratic coefficients u1, u2
  ld2 = [0.0, 0.0]  (table)  Limb darkening, star 2: Quadratic coefficients u1, u2
  mcmc_steps = 0  (int, >= 0, <= 1000000)  MCMC steps: Length of the Markov chain for the errors; 0: none
  export_format = "phoebe"  (choice, one of phoebe, wd, transit)  Export for: PHOEBE, Wilson–Devinney or a transit-fitting program
```

## models.visual_orbit

```text
models.visual_orbit  (Fit the visual orbit)

Visual-binary orbit from "epoch theta rho [rho_err] [theta_err]" lines (see models/visual.py).

inputs:      measures
outputs:     orbit
  measures  (object)  Measures of the visual binary
parameters (default):
  p_min = null  (float, yr, >= 0.0)  Shortest period: With the longest: the search stays inside; empty: free
  p_max = null  (float, yr, >= 0.0)  Longest period: With the shortest: the search stays inside; empty: free
  parallax_mas = null  (float, mas, >= 0.0)  Parallax: Gives the total mass; empty: none
```
