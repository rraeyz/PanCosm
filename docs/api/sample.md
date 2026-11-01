# sample

Python: `from astrowb import api; api.sample.<step>(…)`; command line: `astrowb-cli run sample.<step> key=value …`.

## sample.night

```text
sample.night  (Make practice data)

Practice data: a simulated night of an eclipsing binary with calibration frames, a transit night in
transit/, a pulsating star's light curve, a list of minima with a third body, a double-lined binary's velocities
and a long-slit frame with its arc (see the Guide).

inputs:      folder
outputs:     truth
  folder  (new_folder)  Folder for the practice data
  truth  (object)  True values of the practice data
```
