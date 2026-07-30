# Automation and plugins
An **automation** chains steps into your own pipeline — "calibrate the frames in a folder → measure the light curve → time the minimum → O-C" — and runs it in one go. **Plugins** add your own steps.

## Ready templates
The **Automation** page lists ready templates (marked "template") and your own automations:

- **Eclipsing binary night** — a dusk-to-dawn sequence, then calibration, comparison stars, light curve, time of minimum (Kwee–van Woerden) and O-C.
- **Exoplanet transit** — the same, with the trapezoid fit for the mid-transit time.
- **End-of-night calibration and stack** — darks and bias at dawn, then masters, calibration and a stacked image.
- **Spectroscopy night → RV → orbit** — every long-slit frame reduced with the arc, radial velocities against a template, and a single-lined orbit.
- **Variable star: light curve → period** — light curve and a Lomb–Scargle period search.

Select one to see its description and its steps.

## Running an automation
1. Fill in the **Inputs** on the right (folders and files have a **…** button). Only what no step can produce is asked: for example the raw-frame folder and the target position.
2. Press **Run**. Each step runs as a normal task in the Tasks panel and is recorded in the project; the next starts when the previous one has finished. The line under the button says which step is running.
3. When it is done, the results of the last step (e.g. the time of minimum and O-C) are shown below. If a step fails, the automation stops there and the error is shown.

## The observing part
Templates with an observing sequence have **To the Observe page**: it fills in the target, start and end (e.g. dusk and dawn) and the exposure rows. Add the coordinates, check the exposure times and start it there. Tick **Process after the sequence** before sending it: when the sequence ends (also when the weather stops it early, if frames were taken), the automation runs by itself on the sequence's folder. With a remote observatory the frames are first copied to this computer, then processed.

## Building your own
1. **New** starts an empty automation (or start from a template and change it).
2. Choose a step in the list under **Steps, in order** and press **Add step**. **Remove**, **Up** and **Down** change the order.
3. Select a step to see its **settings**:
   - lines starting with **←** are its inputs. By default an input takes the data of the same name produced by an earlier step (or typed in Inputs). Type another name to link it, e.g. the stacking step's `images` ← `calibrated`;
   - `name.field` takes one field of a result, or that field of every row: e.g. the orbit's `time` ← `rvs.bjd`;
   - text with braces builds a file name, e.g. `{output_dir}/{item}_1d.fits`;
   - the other lines are the step's parameters; type numbers, `true`/`false`, `null`, lists like `[1, 2]`, or text.
4. **Save as…** stores it under a name in your settings folder (`automations`), where it appears in the list next time.

Automations are plain JSON files, so they can be shared: copy the file into another user's `automations` folder.

## Plugins
**What they are:** a plugin is a small extra tool you add to the application yourself — for a calculation the application does not have, or one only your group needs. It is one Python file. Once it is in the plugins folder it appears in the **Plugins** menu, opens a small form for its inputs, runs like every built-in step (in the background, with progress and Cancel, recorded in the project) and can be used as a step of an automation.

**You do not need to program to try them.** **Plugins → Install the example plugins** adds three ready ones:
- **plugin.exposure_time** — how many seconds to expose for a wanted signal-to-noise, from the star's magnitude, your zero point, sky, read noise and aperture (the CCD equation). Only numbers, no file.
- **plugin.sky_level** — the sky level and its noise in a FITS image (to compare nights or check flats).
- **plugin.light_curve_summary** — points, time span, scatter in millimagnitudes and the deepest point of a light-curve CSV file.

Choose one in the **Plugins** menu, fill in the form, press OK; the result opens in a window when it is ready. A plugin that has an error is listed as "Failed to load" with the reason; it never stops the application. Plugins run with your rights like any program you install: use only files you trust.

## Writing your own plugin
Open **Plugins → Open plugins folder**, copy one of the examples, rename it and change it. This is the whole sky-level example:

```python
from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level and noise of a FITS image (stars clipped)."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "noise": float(std)}}
```

- The text in quotes after `@step` is the tool's name; it must start with `plugin.`.
- `inputs` are what the form asks for (file paths or numbers); the words after them (`sigma=3.0`) are settings with their default values.
- The function receives them as `inputs["image"]` and `params["sigma"]` and returns a dictionary of results (numbers, text, lists).
- For long work call `ctx.progress(0.5, "message")` now and then, and `ctx.check()` inside loops so Cancel works.
- numpy, scipy, astropy, photutils and matplotlib are always available. Save the file; the Plugins menu picks it up the next time it opens.
