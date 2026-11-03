# Astronomy workbench (working title)

**One desktop application for the whole observing workflow** — from choosing a target to the number that goes
into a paper:

> plan the night → control the telescope and camera → calibrate the frames → measure (photometry,
> spectroscopy, remote sensing) → times of minimum, O-C, periods, orbits and models → reports.

Most observers today chain five or six programs together: one to plan, one to run the telescope, one to
calibrate, one for photometry, a spreadsheet for O-C, another program for spectra. Every hand-over is a chance
to lose a header keyword, mix up time systems or type a number wrong. This application keeps the whole chain in
one place, records every step it runs, and lets you **start at whatever step your data are at**: raw FITS
frames, calibrated images, reduced spectra, a GeoTIFF from a satellite, a list of minimum times or a table of
radial velocities.

It is meant for everyone from amateurs with a small telescope to professional observatories: the defaults do
the right thing, and every setting is there when you need it.

- **Platforms:** Windows 10/11, macOS 12+ (Apple Silicon and Intel), Linux (Ubuntu 22.04+, Debian 12+, Fedora,
  Arch / CachyOS) on 64-bit PCs and on 64-bit ARM (e.g. a Raspberry Pi at the telescope).
- **Speed:** heavy array work runs on the graphics card (Vulkan / Metal / DirectX 12) when that is faster, on
  the processor otherwise — automatically.
- **Languages:** English, Turkish, German and Spanish — interface, training guide (with screenshots), automation
  templates and messages, all bundled (no online translation). German and Spanish are drafts awaiting review by native
  speakers; more languages can be added without touching the code.
- **Look:** a blue-black dark theme (default) and a light theme.

The product name is defined in one file only (`src/astrowb/resources/brand/brand.toml`), so it can still change;
this README says "the application".

---

## Contents

1. [Download and install](#download-and-install)
2. [First start](#first-start)
3. [What it does, page by page](#what-it-does-page-by-page)
4. [Typical workflows](#typical-workflows)
5. [Observatory control and safety](#observatory-control-and-safety)
6. [Projects, automations and plugins](#projects-automations-and-plugins)
7. [File formats](#file-formats)
8. [How the results are checked](#how-the-results-are-checked)
9. [Run from source](#run-from-source)
10. [Documentation](#documentation)
11. [Licence](#licence)

---

## Download and install

**Releases:** the repository's **Releases** page has the installers of every published version (the
first is 0.1.0). *Help → Check for updates…* in the application tells you when a newer one is out.

**Latest development build:** every change is built, installed and tested automatically on all three
systems, and the tested installers can be downloaded from GitHub:

1. Open the repository on GitHub and go to the **Actions** tab (you need to be signed in to GitHub).
2. Click the most recent run of the **ci** workflow with a green tick.
3. Scroll down to **Artifacts** and download the one for your system:

| Your system | Artifact | File inside the zip |
|---|---|---|
| Windows 10 / 11 (64-bit) | `installer-Windows-X64` | `<name>-<version>-windows-x64-setup.exe` |
| macOS 12+ on Apple Silicon (M1–M4) | `installer-macOS-ARM64` | `<name>-<version>-macos-arm64.dmg` |
| macOS on an Intel Mac | `installer-macOS-X64` | `<name>-<version>-macos-x86_64.dmg` |
| Linux, 64-bit PC | `installer-Linux-X64` | `<name>-<version>-linux-x86_64.AppImage` |
| Linux on 64-bit ARM (Raspberry Pi 4/5 with a 64-bit OS, other ARM boards) | `installer-Linux-ARM64` | `<name>-<version>-linux-aarch64.AppImage` |

GitHub delivers artifacts as a `.zip`; unpack it first. Artifacts are kept for 90 days by default; a newer run always
has fresh ones.

The installers are **not code-signed yet** (signing certificates are a later decision), so the system warns
the first time. The steps below show how to get past that warning.

### Windows 10 / 11

1. Double-click `…-windows-x64-setup.exe`.
2. If Windows SmartScreen says *"Windows protected your PC"*, click **More info → Run anyway**.
3. The installer needs no administrator rights: it installs for your user (under
   `%LOCALAPPDATA%\Programs`) unless you choose *install for all users*. It adds a Start-menu entry and
   optionally a desktop shortcut.
4. Start it from the Start menu.

Uninstall: *Settings → Apps → Installed apps*, or *Control Panel → Programs and Features*. Your settings,
plugins and automations stay in `%LOCALAPPDATA%\<name>`, so a reinstall keeps them.

Installed and started in CI on the current Windows image and on Windows Server 2022.

### macOS (Apple Silicon and Intel)

1. Double-click the `.dmg`, drag the application into **Applications**.
2. The first time, **right-click (or Control-click) the application → Open → Open**. A double-click shows
   *"cannot be opened because the developer cannot be verified"* until you have done this once.
   - On macOS 15 (Sequoia) and later, open **System Settings → Privacy & Security**, scroll down and click
     **Open Anyway** after the first attempt.
   - Or, in Terminal: `xattr -dr com.apple.quarantine /Applications/<name>.app`
3. Start it from Applications or Launchpad.

Uninstall: move the application to the Bin. Settings are in `~/Library/Application Support/<name>`.

### Linux (AppImage — all distributions)

An AppImage is a single file that runs without installation:

```bash
chmod +x ./*-linux-*.AppImage
./*-linux-*.AppImage
```

Or right-click the file → *Properties → Permissions → Allow executing file as program*, then double-click it.

AppImages need **FUSE 2**. Most desktops have it; if the file does not start and the terminal mentions FUSE:

| Distribution | Command |
|---|---|
| Ubuntu 22.04 / Debian 12 | `sudo apt install libfuse2` |
| Ubuntu 24.04 and later | `sudo apt install libfuse2t64` |
| Fedora | `sudo dnf install fuse fuse-libs` |
| Arch / CachyOS / Manjaro | `sudo pacman -S fuse2` |

Without FUSE it still runs with `./…AppImage --appimage-extract-and-run`.

For a menu entry, put the file in `~/Applications` and use a tool such as *Gear Lever* or *AppImageLauncher*,
or create a `.desktop` file yourself. Settings are in `~/.config/<name>`.

Tested in CI on Ubuntu 22.04 and 24.04, Debian 12, Fedora and Arch Linux.

### Graphics card

Nothing to install for the GPU part: the application uses the graphics driver you already have (Vulkan on
Linux and Windows, Metal on macOS, DirectX 12 on Windows). If no usable driver is found, everything runs on the
processor. To compare the two on your machine run the application with `--benchmark`
(on Linux: `./…AppImage --benchmark`).

### Optional programs that work together with it

None of these is needed to start; install them when you use the matching feature.

| For | Program | Notes |
|---|---|---|
| Plate solving | [ASTAP](https://www.hnsky.org/astap.htm) + one star database, or astrometry.net | Runs locally; nothing is sent over the internet |
| Telescope / camera / focuser / filter wheel / dome | ASCOM Alpaca drivers, or INDI (`indiserver`) | Classic Windows ASCOM drivers through *ASCOM Remote* |
| Autoguiding and dithering | [PHD2](https://openphdguiding.org/) | Controlled over its network API |
| Roche-model light curves | PHOEBE 2 | The application exports the data and a starting solution |

---

## First start

The first window is in English and asks three things, all changeable later in the **Settings** menu:

- **Language** — English, Turkish, German or Spanish; applied at once.
- **Computations run on** — *Automatic* (graphics card when it is faster; recommended), *Graphics card* or
  *Processor only*.
- **Look** — *Dark* (blue-black) or *Light*.

A one-minute **quick tour** then points at the pages, the Tasks panel and the menus (skip it, or reopen it with
*Help → Quick tour*). Everything is explained in detail on the **Guide** page (*Help → Training guide*, F1):
twelve categories from *Getting started* to *Troubleshooting*, searchable, in every interface language.

---

## What it does, page by page

The sidebar lists the pages in the order of an observing night. Long jobs run in the background in separate
processes with their progress in the **Tasks** panel, so the window never freezes and a crash in one job never
takes the application down.

### Start
Pick what you have — raw frames, calibrated images, spectra, a list of minima or radial velocities, or
nothing yet and you want to plan — and you are taken to the right page. New or existing project, or just
open a FITS file.

### Plan
Your site, the date and the targets (looked up in SIMBAD by name, cached for offline use, or typed as
coordinates). The plot shows the altitude of every target through the night, with civil / nautical /
astronomical twilight, the Moon and its phase, the airmass scale and your altitude limit. With T0 and the
period of an eclipsing binary or exoplanet, every eclipse or transit of the night is listed with its start,
middle and end and whether it can be observed.

### Observe
Connect to the observatory (see [Observatory control and safety](#observatory-control-and-safety)). Slew,
park, abort, autofocus; preview frames; camera cooler, focuser and filter wheel; imaging **sequences** with
several filters and exposure rows, dithering, meridian flips, start at dusk, repeat until dawn; twilight
**sky flats** with automatic exposure times. The safety state is always visible.

### Calibrate
Point it at a folder of raw frames (sub-folders included). It recognises bias, dark, flat and light frames
from the headers (or file names), shows exposure, filter, temperature and binning, builds sigma-clipped master
frames and applies the right ones to every light frame — darks matched by exposure and temperature (scaled when
bias frames allow it), flats by filter and binning. Missing calibration frames are reported, never silently
ignored. Optional cosmic-ray removal (L.A.Cosmic). Then align and stack into a deep image with a coverage map.

### Images
A FITS viewer with zoom, pan and display stretches (ZScale, min–max, 99.5 %; linear, square root, log, asinh),
the header, and pixel value + sky coordinates under the mouse. **Plate solving** with ASTAP or astrometry.net.
**Image processing:** pixel math between images, flips, 90° rotations, binning and cropping with the WCS
carried along exactly, Gaussian / median / unsharp filters, background-gradient removal.

### Photometry
Click the target and comparison stars (or let the application suggest comparison stars: similar brightness,
unsaturated, isolated, inside every frame). Aperture photometry with errors from the CCD equation, an ensemble
of comparison stars, re-centring and drift tracking through the night, times in **BJD_TDB**. Times of minimum
(Kwee–van Woerden or trapezoid fit, with bootstrap errors) and O-C against an ephemeris. Export to CSV or the
**AAVSO extended format**. A **live** mode follows the camera's folder during the night and grows the light
curve frame by frame. **Polarimetry** for dual-beam (Wollaston + half-wave plate) and single-beam data.

### Light curves & O-C
**Period search** with Lomb–Scargle (pulsators), BLS (transits, Algol-type eclipses) or PDM (any shape), with
the periodogram and the folded light curve. **O-C diagrams** from a list of minimum times (paste or load;
primary and secondary, with errors and sources): linear or quadratic ephemeris, the new T0 and P with errors,
and dP/dt in seconds per year.

### Spectroscopy
- **Long-slit and slitless** reduction: tracing, optimal (Horne) or box extraction with sky subtraction, arc
  line identification from a few clicked lines and bundled line lists (He-Ne-Ar, Th-Ar, Cu-Ar, Fe-Ar…),
  polynomial wavelength solution with its rms.
- **Echelle**: order tracing on the flat, blaze, per-order extraction, a global 2-D wavelength solution,
  absolute order numbers and a blaze-corrected merged spectrum. Fibre-fed and coudé instruments are supported;
  settings are saved as named **instrument profiles**.
- **Telluric correction** from a standard star (strength and shift fitted in the telluric bands).
- **Radial velocities**: cross-correlation; **TODCOR** for double-lined binaries; the **broadening function**
  for fast rotators and contact (W UMa) binaries, which also gives v sin i and the light ratio. Barycentric
  correction from the time, the target position and the site.
- **Orbits**: single- and double-lined spectroscopic orbits (P, e, ω, K, γ; K2, q, M sin³i, a sin i).
- **IFU data cubes**: images over a wavelength window, continuum-subtracted line maps, spectra of single
  spaxels; cubes larger than the memory are read directly from the file.

### Orbits & models
A detached eclipsing-binary / transit light-curve model (limb-darkened spheres on a Keplerian orbit) fitted to
your light curve: inclination, radii, surface-brightness ratio, third light, eccentricity. Combined with a
double-lined orbit it gives **absolute dimensions** (masses, radii, separation, log g with errors). Close and
contact systems: export the data and the starting solution for **PHOEBE**, and overlay a model computed there.

### Remote sensing
Satellite and aerial images (Landsat, Sentinel-2, drones): multi-band GeoTIFF / Cloud-Optimised GeoTIFF or FITS
with map coordinates; NDVI, NDWI, EVI, SAVI, NDBI; your own band math (parsed safely, never executed as code);
statistics, unsupervised classification (k-means), principal components, change detection. Every product is a
GeoTIFF that opens in the right place in QGIS.

### Automation
Chain steps into your own pipeline, or start from a ready template:
*Eclipsing binary night*, *Exoplanet transit*, *End-of-night calibration and stack*,
*Spectroscopy night → RV → orbit*, *Variable star: light curve → period*. Templates with an observing part send
the sequence to the Observe page; tick one box and the processing starts by itself when the night's sequence
ends (frames from a remote observatory are copied over first).

### Project and Guide
The **Project** page lists the files and the full history of every step with its settings. The **Guide** is
the built-in training manual.

---

## Typical workflows

**An eclipsing binary minimum.** Plan → see that the minimum is observable from 21:40 to 01:10 UTC → Observe:
a V-filter sequence from dusk to dawn, darks and bias at the end → Calibrate the folder → Photometry: click the
star, *Suggest comparison stars*, *Measure light curve* → *Time of minimum* (Kwee–van Woerden) with T0 and
period → the epoch and O-C → paste it with your earlier minima on the O-C page. The *Eclipsing binary night*
automation does everything after the observation in one run.

**An exoplanet transit.** The same, with the trapezoid fit, which gives the mid-transit time, depth and
duration; export the light curve for further modelling or fit it on the Orbits & models page.

**A double-lined spectroscopic binary.** Reduce each spectrum (Reduce or Echelle tab) → Telluric correction if
needed → Radial velocity: two templates (TODCOR) or the broadening function → *Fit orbit* → with the light curve
on Orbits & models: masses and radii.

**A satellite image.** Remote sensing → open the GeoTIFF → set the band roles → NDVI → classify → save the
products and open them in QGIS.

---

## Observatory control and safety

Telescope safety does not depend on the window. The devices are owned by a separate **observatory process**
with a **safety supervisor**, which checks every few seconds:

- the weather (safety monitor, humidity, wind, rain, cloud cover), with your limits;
- the Sun (no slews near it; at sunrise the night is over);
- the altitude limit and an optional horizon profile;
- that every device still answers.

When anything is unsafe it aborts the exposure, stops the sequence, **parks the mount and closes the dome** —
even if the window has crashed or was closed. Nothing restarts by itself; the operator presses *Resume*.

Devices: **ASCOM Alpaca** and **INDI** (mount, camera, filter wheel, focuser, dome, safety monitor, observing
conditions), classic Windows ASCOM drivers through ASCOM Remote, **PHD2** for guiding and dithering. The
observatory is described by one JSON file (example in the Guide, *Observing and safety*).

The observatory can run on another computer (e.g. at the telescope) and be controlled over the network through
a token-protected API. Frames of a finished sequence are copied back for processing; the observatory only
hands out frames it has saved itself.

Before using real hardware, test the same configuration with the ASCOM Alpaca or INDI simulators.

---

## Projects, automations and plugins

- **Projects** (`.astroproj`, one file) record the files and every step run: the step, its settings, the start
  time, the result and the versions of the libraries used — months later you can see exactly how a number was
  obtained. Paths are relative, so the project folder can be moved with its data.
- **Automations** are JSON files; build them on the Automation page or edit them by hand, and share them by
  copying the file.
- **Plugins** are Python files in the settings folder that register new steps with the same decorator the
  built-in steps use. They appear in the *Plugins* menu (with a generated form) and in the automation editor,
  and run in worker processes with progress and cancel. See [`docs/PLUGINS.md`](docs/PLUGINS.md).

---

## File formats

| Reads | Writes |
|---|---|
| FITS images (also `.gz`, any image extension), FITS headers of all common capture programs | FITS (calibrated frames, masters, stacks with coverage, processed images; history in the header) |
| 1-D spectra: FITS tables, 1-D FITS with a wavelength WCS, text | 1-D spectra as FITS tables with wavelength, flux, error |
| IFU cubes (3-D FITS with a spectral WCS) | Spaxel spectra |
| GeoTIFF / Cloud-Optimised GeoTIFF, FITS, JPEG2000, NetCDF, HDF5 (remote sensing) | GeoTIFF with the input's georeferencing |
| Light curves (CSV), minimum-time lists (text), radial-velocity tables | CSV, AAVSO extended format, PHOEBE input files |
| Automations (JSON), observatory configuration (JSON) | Projects (`.astroproj`, SQLite) |

Remote sensing also reads JPEG2000 (e.g. Sentinel-2 band files, without their map position), NetCDF 3 / 4 and HDF5.

---

## How the results are checked

*"A wrong number silently entering a table"* is treated as the biggest risk, so:

- Every science module is tested on **simulated data with a known answer** (calibration against ccdproc,
  photometry, minima, periods, wavelength solutions, TODCOR, the broadening function, orbits, light-curve
  models, band math…): over 230 automatic tests.
- **Real data:** the HAT-P-32 b transit time from public MicroObservatory frames agrees with the published
  ephemeris (+1.5 ± 4.8 min), checked in CI on every change.
- **Hardware:** sequences, safety rules and the supervisor are tested against simulated devices and against
  the real INDI simulators.
- **Packages:** on every change, the installers for Windows, macOS and Linux are built, **installed and
  started** in CI (current Windows and Windows Server 2022; Ubuntu 22.04/24.04, Debian 12, Fedora, Arch), and a smoke test
  runs real calibration, photometry, planning, spectroscopy, model fitting and remote sensing inside the
  installed application.
- Comparisons with AstroImageJ, IRAF, published orbits and real observatory hardware on real data are the
  next step.

---

## Run from source

Works on every platform, including Intel Macs, with Python 3.11 or newer.

```bash
git clone <this repository>
cd <repository folder>
python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"
python tools/i18n.py                 # compile the translations
python -m astrowb                    # start the application
```

Linux without a desktop needs a few system libraries for Qt:
`sudo apt install libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3` (Debian/Ubuntu).

Useful commands:

```bash
python -m astrowb --benchmark                 # CPU vs GPU timing on this machine
python -m astrowb --observatory config.json   # the observatory process alone (at the telescope)
python -m astrowb --smoke-test /tmp/smoke     # the same end-to-end check the installers pass
sh tools/precommit.sh                         # every check CI runs: lint, brand guard, translations, tests
python packaging/build.py                     # build the installer for this system
```

---

## Documentation

| File | What |
|---|---|
| The **Guide** page in the application | The full user manual, by category, searchable (in every interface language) |
| [`docs/PLUGINS.md`](docs/PLUGINS.md) | Writing plugins |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setting up the code, the rules of every change, code map |
| [`THIRD_PARTY.md`](THIRD_PARTY.md) | Libraries, data and sources used |

---

## Licence

Copyright © 2026 the authors (see the Git history). The application is free software: you can redistribute it and/or modify it under
the terms of the **GNU General Public License, version 3 or (at your option) any later version** — see
[`LICENSE`](LICENSE). It is distributed in the hope that it will be useful, but **without any warranty**.
The libraries it bundles keep their own licences ([`THIRD_PARTY.md`](THIRD_PARTY.md)).
