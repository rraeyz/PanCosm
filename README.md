# PanCosm

**An astronomy workbench for the whole observing workflow — from choosing a target to the number that goes
into a paper.**

> plan the night → control the telescope and camera → calibrate the frames → measure (photometry,
> spectroscopy, remote sensing) → times of minimum, O-C, periods, orbits and models → reports

Most observers chain five or six programs together: one to plan, one to run the telescope, one to calibrate,
one for photometry, a spreadsheet for O-C, another program for spectra. Every hand-over is a chance to lose a
header keyword, mix up time systems or type a number wrong. PanCosm keeps the whole chain in one place,
records every step it runs, and lets you **start at whatever step your data are at**: raw FITS frames,
calibrated images, reduced spectra, a satellite GeoTIFF, a list of minimum times or a table of radial
velocities.

It is made for everyone from amateurs with a small telescope to professional observatories: the defaults do
the right thing, and every setting is there when you need it.

- **Free and open source** — GPL-3.0-or-later.
- **Windows, macOS and Linux** — Windows 10/11, macOS 12+ (Apple Silicon and Intel), Linux on 64-bit PCs and
  64-bit ARM (e.g. a Raspberry Pi at the telescope).
- **Fast** — heavy array work runs on the graphics card (Vulkan / Metal / DirectX 12) when that is faster, on
  the processor otherwise, automatically.
- **Four languages** — English, Turkish, German and Spanish: interface, built-in training guide, automation
  templates and messages (German and Spanish are drafts awaiting review by native speakers).
- **Safe at the telescope** — an independent safety supervisor parks the mount and closes the dome even if
  the window crashes.
- **Reproducible** — a project file records every step, its settings and the library versions used.

---

## Contents

1. [Download and install](#download-and-install)
2. [First start](#first-start)
3. [What it does](#what-it-does)
4. [Typical workflows](#typical-workflows)
5. [Observatory control and safety](#observatory-control-and-safety)
6. [Projects, automations and plugins](#projects-automations-and-plugins)
7. [File formats](#file-formats)
8. [How the results are checked](#how-the-results-are-checked)
9. [Run from source](#run-from-source)
10. [Contributing](#contributing)
11. [Licence](#licence)

---

## Download and install

Download the installer for your system from the **[Releases](https://github.com/rraeyz/PanCosm/releases)**
page. *Help → Check for updates…* in the application tells you when a newer version is out.

| Your system | File |
|---|---|
| Windows 10 / 11 (64-bit) | `PanCosm-<version>-windows-x64-setup.exe` |
| macOS 12+ on Apple Silicon (M1–M4) | `PanCosm-<version>-macos-arm64.dmg` |
| macOS on an Intel Mac | `PanCosm-<version>-macos-x86_64.dmg` |
| Linux, 64-bit PC | `PanCosm-<version>-linux-x86_64.AppImage` |
| Linux on 64-bit ARM (Raspberry Pi 4/5 with a 64-bit OS) | `PanCosm-<version>-linux-aarch64.AppImage` |

The installers are **not code-signed yet**, so your system warns the first time; the steps below show how to
get past that warning.

<details>
<summary><b>Development builds</b> (the newest changes, before a release)</summary>

Every change is built, installed and tested automatically on all three systems. Signed in to GitHub, open the
**Actions** tab, click the newest **ci** run with a green tick and download your system's installer from
**Artifacts** (`installer-Windows-X64`, `installer-macOS-ARM64`, `installer-macOS-X64`, `installer-Linux-X64`,
`installer-Linux-ARM64`). GitHub delivers them as `.zip` files; unpack first.
</details>

### Windows 10 / 11

1. Double-click `PanCosm-…-windows-x64-setup.exe`.
2. If SmartScreen says *"Windows protected your PC"*, click **More info → Run anyway**.
3. No administrator rights are needed: it installs for your user unless you choose *install for all users*,
   and adds a Start-menu entry (a desktop shortcut is optional).

Uninstall from *Settings → Apps → Installed apps*. Settings, plugins and automations stay in
`%LOCALAPPDATA%\pancosm`, so a reinstall keeps them.

### macOS

1. Open the `.dmg` and drag PanCosm into **Applications**.
2. The first time, **right-click (or Control-click) PanCosm → Open → Open**.
   On macOS 15 and later: try to open it once, then **System Settings → Privacy & Security → Open Anyway**.
   Or in Terminal: `xattr -dr com.apple.quarantine /Applications/PanCosm.app`

Uninstall by moving it to the Bin. Settings are in `~/Library/Application Support/pancosm`.

### Linux

One command installs PanCosm for your user, with an entry in the application menu (no root, no FUSE needed).
Run it again to update:

```bash
curl -fsSL https://raw.githubusercontent.com/rraeyz/PanCosm/main/packaging/install.sh | sh
```

To remove it: `curl -fsSL https://raw.githubusercontent.com/rraeyz/PanCosm/main/packaging/install.sh | sh -s -- --uninstall`

Or download the AppImage yourself and run it:

```bash
chmod +x PanCosm-*-linux-*.AppImage
./PanCosm-*-linux-*.AppImage
```

Or right-click the file → *Properties → Permissions → Allow executing file as program*, then double-click it.
AppImages need **FUSE 2**; if the file does not start and the terminal mentions FUSE:

| Distribution | Command |
|---|---|
| Ubuntu 22.04 / Debian 12 | `sudo apt install libfuse2` |
| Ubuntu 24.04 and later | `sudo apt install libfuse2t64` |
| Fedora | `sudo dnf install fuse fuse-libs` |
| Arch / CachyOS / Manjaro | `sudo pacman -S fuse2` |

Without FUSE it still runs with `--appimage-extract-and-run`. Settings are in `~/.config/pancosm`. Tested on
Ubuntu 22.04 and 24.04, Debian 12, Fedora and Arch Linux.

### Graphics card

Nothing to install: PanCosm uses the driver you already have (Vulkan on Linux and Windows, Metal on macOS,
DirectX 12 on Windows) and falls back to the processor when there is none. Compare the two on your machine with
`--benchmark`.

### Optional programs that work together with it

| For | Program |
|---|---|
| Plate solving (runs locally) | [ASTAP](https://www.hnsky.org/astap.htm) with one star database, or astrometry.net |
| Telescope, camera, focuser, filter wheel, rotator, dome | ASCOM Alpaca drivers, or INDI (`indiserver`); classic ASCOM drivers through *ASCOM Remote* |
| Autoguiding and dithering | [PHD2](https://openphdguiding.org/) |
| Roche-model light curves | PHOEBE 2 or the Wilson-Devinney program (PanCosm writes their input) |

---

## First start

The first window asks for the **language**, where computations run (**Automatic** is recommended: the
graphics card when it is faster) and the **look** (dark or light); all can be changed later in *Settings*.
A one-minute **quick tour** shows the pages, the Tasks panel and the menus. The **Guide** page
(*Help → Training guide*, F1) is the full manual: twelve searchable chapters, from *Getting started* to
*Troubleshooting*, in every interface language.

---

## What it does

The sidebar lists the pages in the order of an observing night. Long jobs run in the background in separate
processes, with progress in the **Tasks** panel: the window never freezes, and a crash in one job never takes
the application down. Right-click any page in the sidebar to show it as a **panel beside the image**; every
border can be dragged.

### Plan
Your site, the date and the targets (SIMBAD by name, cached for offline use, or coordinates). Altitude of
every target through the night with twilights, the Moon and its phase, airmass and your altitude limit.
Eclipses and transits of the night from T0 and the period — or from **VSX** and the **NASA Exoplanet Archive**
— with start, middle and end and whether they can be observed, and a **schedule** for several targets.

### Observe
Slew, park, abort; preview frames; cooler, gain, offset, binning and readout mode; focuser, filter wheel and
rotator. **Sequences** with several filters and exposure rows, dithering, meridian flips, start at dusk and
repeat until dawn. **Autofocus** (with temperature compensation), **sky flats** with automatic exposures or
**flat-panel** flats, **plate-solve centring** and a **polar-alignment** measurement. The safety state is
always visible.

### Calibrate
Point it at a folder of raw frames: bias, dark, flat and light frames are recognised from the headers (or file
names), sigma-clipped **master frames** are built and the right ones applied to every light frame — darks
matched by exposure and temperature (scaled when possible), flats by filter and binning. Missing calibration
is reported, never silently ignored. Overscan (row by row), **linearity correction**, cosmic-ray removal
(L.A.Cosmic), **frame quality** checks (FWHM, sky, star count) that leave bad frames out, colour (Bayer) cameras
and **DSLR raw files**. Then align and **stack** into a deep image with a coverage map, or **drizzle**
dithered frames onto a finer grid.

### Images
- **Many images at once** in a list with thumbnails (only the shown one is read, so hundreds are fine);
  arrow keys or Page Up / Page Down step through them, and **Blink** compares them.
- A **toolbar** of the common commands and a **right-click menu** on the image: measure this star, start
  photometry with it, copy its position, look it up in **SIMBAD**.
- Display: ZScale / min–max / percentile intervals, linear / square-root / log / asinh stretches, levels by hand,
  false-colour maps, inverted display.
- **Measuring** as in MaxIm DL, in small floating Information and Graph windows: a star (net counts,
  signal-to-noise, FWHM, HFD, ellipticity, saturation), a rectangle (statistics, histogram, profiles, 3-D surface)
  or a line (profile, length and angle).
- **Overlays:** contours, a coordinate grid, Gaia DR3 and **VSX** stars, known **asteroids and comets**
  (SkyBoT) at the exposure time, DS9 regions, and AAVSO-style **finder charts**.
- **Plate solving** with ASTAP or astrometry.net; **asteroid and comet astrometry** with an MPC (ADES) report;
  **colour images** from three filters.
- **Processing** that carries the WCS along: pixel math between images, flips, rotations, resampling, binning,
  cropping, Gaussian / median / unsharp / kernel filters, background removal, Richardson–Lucy deconvolution,
  DDP, histogram matching — on one image or on **every open image** at once.
- Header editing (into a copy), multi-extension FITS, and batch conversion to PNG / JPEG / TIFF.

### Photometry
Click the target and comparison stars, or let PanCosm suggest comparison stars (similar brightness,
unsaturated, isolated, inside every frame). Aperture or PSF photometry with errors from the CCD equation, an
ensemble of weighted comparison stars, check stars, re-centring and drift tracking, times in **BJD_TDB**,
detrending against airmass, FWHM, sky or position. Catalogue magnitudes (APASS, Gaia) for standard magnitudes,
**extinction and transformation coefficients**, and export to CSV or the **AAVSO extended format**. A **live**
mode grows the light curve frame by frame during the night. **Variable-star search** measures every star of the
field and marks the candidates. **Polarimetry** for dual-beam and single-beam data.

### Light curves & O-C
- **Times of minimum** (Kwee–van Woerden, polynomial or trapezoid fit, with errors) and **O-C** diagrams with
  linear or quadratic ephemerides, the **light-travel-time effect** of a third body and **apsidal motion**.
- **Period search:** Lomb–Scargle, BLS and PDM; **frequency analysis** with the spectral window, Fourier fits,
  prewhitening, signal-to-noise and CLEAN.
- **Light curves from archives:** TESS and Kepler/K2 (MAST), AAVSO, ZTF and ASAS-SN.

### Spectroscopy
- **Long-slit and slitless** reduction: tracing, optimal or box extraction with sky subtraction, arc-line
  identification with bundled line lists, wavelength solution with its rms.
- **Echelle:** order tracing, blaze, per-order extraction, a global 2-D wavelength solution and a merged
  spectrum; settings saved as **instrument profiles**.
- **Telluric correction**, line measurements (equivalent width, V/R), spectrum arithmetic, instrument response
  and **BeSS** export.
- **Radial velocities:** cross-correlation, **TODCOR** for double-lined binaries, the **broadening function**
  (also v sin i and the light ratio), barycentric correction, and **spectral disentangling**.
- **Stellar parameters** (Teff, log g, [Fe/H], v sin i) by fitting PHOENIX synthetic spectra, relative to the Sun.
- **Orbits** of single- and double-lined binaries, and **IFU data cubes** (line maps, spaxel spectra).

### Orbits & models
An eclipsing-binary / transit light-curve model fitted to your data (inclination, radii, surface-brightness
ratio, third light, eccentricity) with MCMC errors; with a double-lined orbit, **absolute dimensions**
(masses, radii, log g). **Visual binary orbits** from position angles and separations. A transit report, and
input files for **PHOEBE** and **Wilson-Devinney** for close and contact systems.

### Remote sensing
Landsat, Sentinel-2 and drone images (GeoTIFF / Cloud-Optimised GeoTIFF, FITS, JPEG2000, NetCDF, HDF5): NDVI,
NDWI, EVI, SAVI, NDBI, your own band math (parsed safely, never executed as code), statistics, k-means
classification, principal components and change detection. Products are GeoTIFFs that open in place in QGIS.

### Automation, Project and Guide
Chain steps into your own pipeline or start from a template (*Eclipsing binary night*, *Exoplanet transit*,
*End-of-night calibration and stack*, *Spectroscopy night → RV → orbit*, *Variable star: light curve → period*);
tick one box and the processing starts by itself when the night's sequence ends. The **Project** page shows
the files and the full history of every step; the **Guide** is the built-in training manual.

---

## Typical workflows

**An eclipsing-binary minimum.** Plan → the minimum is observable from 21:40 to 01:10 UTC → Observe: a V-filter
sequence from dusk to dawn → Calibrate the folder → Photometry: click the star, *Suggest comparison stars*,
*Measure light curve* → *Time of minimum* → paste it with your earlier minima on the O-C page. The *Eclipsing
binary night* automation does everything after the observation in one run.

**An exoplanet transit.** The same, with the trapezoid fit (mid-transit time, depth, duration), then the model
fit on Orbits & models.

**A double-lined spectroscopic binary.** Reduce each spectrum → telluric correction → radial velocities with
TODCOR or the broadening function → *Fit orbit* → with the light curve: masses and radii.

**A satellite image.** Remote sensing → open the GeoTIFF → set the band roles → NDVI → classify → open the
products in QGIS.

---

## Observatory control and safety

Telescope safety does not depend on the window. The devices are owned by a separate **observatory process**
with a **safety supervisor** that checks every few seconds:

- the weather (safety monitor, humidity, wind, rain, cloud cover) against your limits;
- the Sun (no slews near it; at sunrise the night is over);
- the altitude limit and an optional horizon profile;
- that every device still answers.

When anything is unsafe it aborts the exposure, stops the sequence, **parks the mount and closes the dome** —
even if the window has crashed or was closed. Nothing restarts by itself: the operator presses *Resume*.

Devices: **ASCOM Alpaca** and **INDI** (mount, camera, filter wheel, focuser, rotator, dome, flat panel, safety
monitor, observing conditions), classic Windows ASCOM drivers through ASCOM Remote, and **PHD2**. The
observatory can run on another computer at the telescope and be controlled over the network through a
token-protected API; finished frames are copied back for processing. Test your configuration with the Alpaca
or INDI simulators before using real hardware.

---

## Projects, automations and plugins

- **Projects** (`.astroproj`, one file) record the files and every step: its settings, start time, result and
  the versions of the libraries used — months later you can see exactly how a number was obtained. Paths are
  relative, so a project folder can be moved with its data.
- **Automations** are JSON files: build them on the Automation page or by hand, and share them by copying the file.
- **Plugins** are Python files that add new steps with the same decorator the built-in steps use; they appear in
  the *Plugins* menu with a generated form and run in worker processes. See [`docs/PLUGINS.md`](docs/PLUGINS.md).

---

## File formats

| Reads | Writes |
|---|---|
| FITS images (also `.gz` and any image extension), headers of all common capture programs, DSLR raw files | FITS (calibrated frames, masters, stacks, processed images; history in the header), PNG / JPEG / TIFF |
| 1-D spectra: FITS tables, 1-D FITS with a wavelength WCS, text | 1-D spectra as FITS tables (wavelength, flux, error), BeSS FITS |
| IFU cubes (3-D FITS with a spectral WCS) | Line maps, spaxel spectra |
| GeoTIFF / COG, FITS, JPEG2000, NetCDF, HDF5 (remote sensing) | GeoTIFF with the input's georeferencing |
| Light curves (CSV, TESS / Kepler files), minimum lists, radial-velocity tables, DS9 regions | CSV, AAVSO extended format, MPC ADES, PHOEBE and Wilson-Devinney input, DS9 regions |
| Automations and observatory configuration (JSON) | Projects (`.astroproj`) |

---

## How the results are checked

*A wrong number silently entering a table* is treated as the biggest risk, so:

- Every science module is tested on **simulated data with a known answer** — calibration, photometry, minima,
  periods, wavelength solutions, radial velocities, orbits, light-curve models, band math…: over 450 automatic
  tests on Windows, macOS and Linux for every change.
- **Real data:** the HAT-P-32 b transit time from public MicroObservatory frames agrees with the published
  ephemeris, checked automatically on every change.
- **Hardware:** sequences, safety rules and the supervisor are tested against simulated devices and the real
  INDI simulators.
- **Installers** for Windows, macOS and Linux are built, **installed and started** for every change (current
  Windows and Windows Server 2022; Ubuntu 22.04 / 24.04, Debian 12, Fedora, Arch), and an end-to-end check runs
  calibration, photometry, planning, spectroscopy, model fitting and remote sensing inside the installed application.

---

## Run from source

Python 3.11 or newer, on every platform:

```bash
git clone https://github.com/rraeyz/PanCosm.git
cd PanCosm
python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"
python tools/i18n.py                 # compile the translations
python -m astrowb                    # start PanCosm
```

Linux without a desktop needs `libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`.

```bash
python -m astrowb --benchmark                 # CPU vs GPU timing on this machine
python -m astrowb --observatory config.json   # the observatory process alone (at the telescope)
python -m astrowb --smoke-test /tmp/smoke     # the end-to-end check the installers pass
sh tools/precommit.sh                         # every check CI runs: lint, brand guard, translations, tests
python packaging/build.py                     # build the installer for this system
```

---

## Contributing

Bug reports, ideas and pull requests are welcome in [Issues](https://github.com/rraeyz/PanCosm/issues).
Before your first pull request please read [`CONTRIBUTING.md`](CONTRIBUTING.md): setup, the rules every change
follows, a map of the code and the licence terms of contributions. Libraries, data and sources used are listed
in [`THIRD_PARTY.md`](THIRD_PARTY.md).

---

## Licence

Copyright © 2026 the PanCosm authors (see the Git history).

PanCosm is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public
License, version 3 or (at your option) any later version** — see [`LICENSE`](LICENSE). It is distributed in the
hope that it will be useful, but **without any warranty**. The libraries it bundles keep their own licences
([`THIRD_PARTY.md`](THIRD_PARTY.md)).
