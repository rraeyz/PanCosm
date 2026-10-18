# Plugins

In plain words: a plugin is a small extra tool you add yourself — one Python file in the plugins folder. It shows
up in the **Plugins** menu with a form for its inputs, runs in the background like every built-in step, is
recorded in the project and can be a step of an automation. **Plugins → Install the example plugins** copies three
ready examples (`src/astrowb/resources/plugins/`): `exposure_time` (seconds for a wanted S/N from the CCD equation,
numbers only), `sky_level` (sky and noise of a FITS image) and `light_curve_summary` (points, span, scatter and
deepest point of a light-curve CSV). Copy one and change it to start your own. The training guide (Automation and
plugins) explains the same for users who do not program.


**Allowing a plugin:** a plugin runs with your rights, like any program. A file that is new, or changed since it
was allowed, waits in the Plugins menu as "Allow …" until you allow it (its SHA-256 is kept in `.trusted.json` in
the plugins folder). The bundled examples, and the files that were there before this check, are trusted.

**Steps a plugin can call:** every built-in step, with its inputs, parameters and defaults, is listed in
[`docs/api/`](api/README.md) (generated from the step registry).

A plugin is a Python file in the `plugins` folder of the settings folder
(**Plugins → Open plugins folder** opens it). Each file registers one or more steps with the same
decorator the built-in steps use; they appear in the **Plugins** menu, which builds a form from the
step's inputs and parameters and runs the step in a worker process (progress, cancel, crash-safe).

```python
from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level of a FITS image after sigma clipping."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    ctx.progress(0.5, "statistics")
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "std": float(std)}}
```

Rules
- Step ids start with `plugin.`; a plugin cannot add or replace built-in steps.
- Inputs typed in the form are read as JSON when possible (numbers, lists, `true`), otherwise as text
  (file paths). Return JSON-like values (numbers, strings, lists, dicts).
- Call `ctx.progress(fraction, message)` for long work and `ctx.check()` in loops so Cancel works.
- The installed application contains numpy, scipy, astropy, photutils, matplotlib; other packages
  are available only when running from a Python installation that has them.
- A plugin that fails to import is listed as "Failed to load" with its error; it never stops the app.
- Plugins run with your rights like any program you install: only use files you trust.
