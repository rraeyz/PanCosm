# app

Python: `from astrowb import api; api.app.<step>(…)`; command line: `astrowb-cli run app.<step> key=value …`.

## app.check

```text
app.check  (Check the installation)

The installation (every module, library and data file) and every web service the application uses.

inputs:      none
outputs:     report, ok
```

## app.check_gpu

```text
app.check_gpu  (Check the GPU)

Every GPU job against its CPU twin (time and result), as text and as gpu-report.json (ARC-10).

inputs:      none
outputs:     report, path
```

## app.update_time_tables

```text
app.update_time_tables  (Update the Earth-rotation tables)

Download the Earth-orientation (IERS-A) and leap-second tables and keep them for every later run.

inputs:      none
outputs:     status
```
