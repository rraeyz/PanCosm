# Getting started
The application covers the whole observing workflow in one window: choose targets, plan the night, observe, calibrate, measure, model and report. You can enter at any step with the data you already have.

Every working window and tab has a folded **Workflow** line at the top that names the next step. Click it to see the usual order of work (the IRAF task in brackets where there is one), each step marked done (✓), skipped (–) or next (▶), and what to do for the next step. It is a guide, never a lock: start at the step where your data are — a spectrum already extracted needs only its wavelengths, a light curve from an archive needs no photometry — and skip what your data do not need.

## The first start {#getting-started-first-start}
The first time the application opens it shows a short welcome window in English with three choices:

- **Language** — the interface language. It is applied at once; you can change it later in **Settings → Language**.
- **Computations run on** — *Automatic* uses the graphics card when it is faster than the processor (recommended), *Graphics card* always uses it, *Processor (CPU) only* never does.
- **Look** — *Dark* (blue-black, the default) or *Light*.

Press **Start**. The choices are saved and never asked again. A one-minute **quick tour** follows; you can skip it and open it again from **Help → Quick tour**.

## Your first night (practice data) {#getting-started-your-first-night-practice}
A complete exercise with simulated data whose answer is known: from raw frames to the time of minimum of an eclipsing binary.

1. **Help → Practice data for a first night…** and choose an empty folder. A `raw` folder appears with 7 bias, 7 dark (60 s), 7 V flat and 48 V light frames of a binary going through a primary eclipse, and `truth.json` with the right answers.
2. **Calibrate:** choose the `raw` folder and press **Scan**: the table shows 7 bias, 7 dark, 7 flat and 48 light frames, nothing missing. Choose an output folder (e.g. `cal`) and press **Calibrate**.

![The Calibration window after Scan](images/en/first-night-calibrate.png)

3. **Photometry:** **Choose images…** and select the calibrated `light_V_*.fits`. Press **Find the bad frames (clouds, focus, trails)**: all frames are good. Click the star in the middle of the image (the binary, at x = 100, y = 80), then **Suggest comparison stars** (or click the three other stars). Type the position `02:04:10.3 +46:41:16` into *Target RA Dec* so the times are in BJD_TDB, and press **Measure light curve**: an eclipse about 45 % deep appears.
4. Keep **Eclipsing binary: Kwee–van Woerden method** (the default) and press **Time of minimum**. Compare it with `t_min_bjd_tdb` in `truth.json`: the two agree within a minute or two.

![The Photometry window with the light curve and the time of minimum](images/en/first-night-photometry.png)

5. **The same in one go:** in the **Automation** window choose *Eclipsing binary night*, give the `raw` folder, a new output folder and the target position `100 80`, and press **Run**. Calibration, frame quality, comparison stars, light curve and minimum run one after the other; the result appears at the bottom.

![The Eclipsing binary night automation ready to run](images/en/first-night-automation.png)

6. To go further: paste the minimum into the **O-C** tab with your own reference T0 and period, export the light curve (**Export CSV…**), or fit it in the **Models** window.

## The window {#getting-started-window}
- **Area blocks:** each area, in the order of an observing night, opens in a window of its own; the **Window** menu of every window lists them too, with Start, Project and this Guide.
- **Tasks panel (bottom):** every long job (calibration, photometry, fits, spectra…) runs in the background in its own process. The panel shows its progress and state (queued, running, done, failed, cancelled). You can keep working while tasks run, and a crashing task never takes the window down.
- **Status bar:** the pixel value and sky coordinates under the mouse when an image is open, and a progress bar while tasks run.
- **Menus:** File (projects, FITS), View (zoom and display stretch), Image (plate solving, processing), Plugins, Settings and Help.
- **Undo and redo:** Edit → Undo (Ctrl+Z) takes back the last change in the window — a star marked or removed, points deleted, a detrending, outliers removed, an image operation, a header change, an arc line identified or left out — and Edit → Redo (Ctrl+Y or Ctrl+Shift+Z) does it again, step by step. The menu names the step. In a text field Ctrl+Z undoes the typing in that field.

## The Start page {#getting-started-start-page}
The Start page is a menu of the areas of the work:

- **Continue where you left off** (when there is something to continue): the last projects and the last files of each area; double-click one to open it again.
- **New project / Open project…** keep frames, settings and results together. **Open a FITS image** to look at an image and its header.
- **Choose what you want to do:** one block per area — Planning, Observing, Calibration, Images, Photometry, Light curves and period, O−C, Spectroscopy, Models, Remote sensing, Automation — each with a line saying what it does. A click opens the area. The areas are moving into windows of their own, each with its own menus, toolbar and panels; an area already in its window is brought to the front, never opened twice.
- **Window** menu: the main window and every open area window. **Help → Report a problem…** makes one zip (error log, version, system, settings, last steps; no data files and no folder names) to send to the developer. **View → Larger / Smaller / Normal text** in an area window (**Settings → Text size** in the main window) makes the text larger or smaller in every window (Ctrl+Shift++ / − / 0). The toolbar of an area window shows small icons (the name of each in its tooltip); **View → Toolbar text** writes the names beside them. Every area window also has **Edit → Copy** and the **Settings** (language, look, processing device, text size), and in **Help** the tour, **Check for updates…** and **About**.

## Projects {#getting-started-projects}
A project is one file with the extension `.astroproj`. It records every file you added and every step you ran: which step, its settings, when it started, whether it succeeded, and its results, together with the versions of the libraries used. This makes the work reproducible: months later you can see exactly how a number was obtained.

- **File → New project…** creates the file; **File → Open project…** continues earlier work.
- File paths are stored relative to the project file, so you can move the project folder together with its data to another computer.
- The **Project** page lists the files (with their type) and the history of runs with their settings.
- Select a row of the history to see everything about that run: its inputs, settings, results (or error) and the versions of the libraries. **Run again with the same inputs and settings** repeats it exactly; the repeat is recorded as a new run.
- Without a project you can still work; nothing is recorded then.

## Settings {#getting-started-settings}
- **Basic or Expert** (on the Start page or **Settings → Expert mode**): in Basic mode the rarely changed options (more calibration and stacking options, the photometry's seeing / PSF / scintillation options, other tools) are folded — one click opens them, nothing is removed — and the Spectroscopy window shows the order of its tabs; in Expert mode every section is open.
- **Settings → Language:** English, Turkish, German or Spanish. A restart may be needed for every text to change.
- **Settings → Look:** Dark or Light. Plots already on screen follow the new colours. **Publication figure…** in every plot's toolbar saves it black on white (PDF, SVG, EPS or 300 dpi PNG) whatever the look; right-click any table to export it as CSV or LaTeX.
- **Settings → Processing device:** Automatic, CPU only or GPU. The status bar shows which device is in use. Run the application with `--benchmark` to check the GPU: it says whether one was found, runs every GPU job (stacking, k-means classes, deconvolution, BLS and PDM period searches) on both devices, and reports whether the results agree and how long each took (also saved as `gpu-check.txt` in the settings folder).
- Settings are stored in a small JSON file in your user settings folder; plugins and your own automations live next to it.

## Graphics card (GPU) {#getting-started-graphics-card-gpu}
Heavy array work (for example sigma-clipped stacking) can run on the graphics card through Vulkan, Metal or DirectX 12. Every GPU calculation has a CPU twin that gives the same result, and *Automatic* only uses the card when it is actually faster. If no usable graphics driver is found, the processor is used and nothing else changes.
