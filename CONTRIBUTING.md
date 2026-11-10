# Contributing

Thank you for helping. This file explains how to set up the code, the rules every change must follow and how
the code is organised.

## Licence of contributions

The application is licensed under the **GNU General Public License, version 3 or later** (`LICENSE`).

By submitting a contribution (a pull request, a patch, a translation, an image or any other material) you
confirm that you wrote it or otherwise have the right to submit it, and you agree that:

1. your contribution is licensed under GPL-3.0-or-later, and
2. you grant the project owner (rraeyz) a perpetual, worldwide, non-exclusive, royalty-free and irrevocable
   licence to use, copy, modify, distribute, sublicense and relicense your contribution, also under other
   licence terms (including a later change of the project's licence or a separate commercial licence).

You keep the copyright of your contribution. Please say so in the pull request if you cannot agree.

## Setup and checks

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[gui,dev]"
sh tools/precommit.sh     # ruff check, ruff format --check, brand guard, translations, tests
python -m astrowb --smoke-test /tmp/smoke   # QT_QPA_PLATFORM=offscreen on a machine without a display
```

Linux without a desktop needs `libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`.
The INDI simulator test needs `indi-bin` (skipped otherwise).

## Locked dependency versions

CI and the installers use the exact versions in `uv.lock` (exported to `requirements/dev.txt` and
`requirements/build.txt`), so two builds a week apart contain the same libraries. To move to newer versions, on
purpose:

```bash
uv lock --upgrade                      # or: uv lock --upgrade-package astropy
uv export --frozen --extra gui --extra dev --no-hashes --no-emit-project --no-header -o requirements/dev.txt
uv export --frozen --extra gui --extra build --no-hashes --no-emit-project --no-header -o requirements/build.txt
sh tools/precommit.sh && sh tools/run_validation.sh
python tools/check_licenses.py --table  # in an environment made from requirements/build.txt
```

The weekly `latest-deps` workflow runs the tests with the newest versions and lists what differs from the lock.

## Rules checked by CI

- **The product name lives only in `src/astrowb/resources/brand/brand.toml`** (and in `README.md`). Never write
  it anywhere else (code, docs, tests, settings keys, file formats); say "the application".
  `tools/check_brand.py` fails the build.
- **No GPL / AGPL library inside the installers** (`tools/check_licenses.py`); LGPL and permissive libraries
  only, GPL tools only as external programs. This keeps every future licensing option open.
- **Every user-interface string is translatable** (`self.tr(...)`) and no translation is left unfinished:
  ```bash
  python tools/i18n.py update
  python tools/fill_translations.py src/astrowb/resources/i18n/app_tr.ts "English=>Türkçe" ...
  python tools/i18n.py     # compile the .qm files
  ```
  Use the `{app}` placeholder for the product name in strings.
- Engine and observatory code has no Qt and speaks English. Messages a user sees from there (safety reasons,
  errors) have a template in `src/astrowb/ui/messages.py`; change both together (`tests/test_messages.py`).
- The training guide (`src/astrowb/resources/guide/<language>/`) has the same topics in every language.
- Never copy code from another project. Reading other projects to learn is fine; list what you consulted in
  `THIRD_PARTY.md`.

## Code map

| Path | What |
|---|---|
| `src/astrowb/engine` | project file, `@step` registry (`steps.py`), built-in steps (`builtin.py`), task queue (worker processes), plugins, automations |
| `src/astrowb/calibration` | frame classification, matching plan, masters, calibration, stacking |
| `src/astrowb/photometry` | apertures, light curves, live light curve, AAVSO export, polarimetry |
| `src/astrowb/timeseries` | minima, ephemeris / O-C, period and frequency search |
| `src/astrowb/planning` | targets, visibility, events |
| `src/astrowb/spectroscopy` | long-slit, echelle, wavelength calibration, radial velocities, orbits, stellar parameters |
| `src/astrowb/models` | eclipsing-binary and transit light-curve models, fits, absolute dimensions |
| `src/astrowb/remotesensing` | rasters, band math, indices, classification |
| `src/astrowb/devices` | safety rules, observatory and supervisor, sequences, focus, guiding, Alpaca, INDI |
| `src/astrowb/io` | FITS reading and saving, image operations |
| `src/astrowb/compute` | GPU kernels with CPU twins |
| `src/astrowb/ui` | Qt pages; `main_window.py` wires pages to steps with `run_step(step_id, inputs, params, on_done)` |
| `tests/` | one test file per area; synthetic data with a known answer |

## Adding a feature

1. The science as plain functions in the domain module, with a test on simulated data with a known answer.
2. An engine step (`@step("area.name", inputs=..., outputs=..., optional=..., **defaults)`) so it runs in a
   worker process and is recorded in the project. Built-in steps are imported in `engine/builtin.py`.
3. The user interface: a page emits a signal; `MainWindow` connects it to `run_step(...)` and shows the result.
4. A user-interface test with `qtbot`, translations, the guide, then `sh tools/precommit.sh`.
5. If the installed application needs it, extend `smoke_test()` in `src/astrowb/__main__.py`.

## Renaming the product

Edit `src/astrowb/resources/brand/brand.toml` (name fields, `app_id`; add the old `app_id` to
`previous_app_ids` so settings are carried over; never change `[stable]`) and replace `icon.png` (512×512).
Nothing else carries the name. The package name `astrowb`, the `ASTROWB_*` environment variables, the
`.astroproj` extension, settings keys and step ids never change, so old projects keep opening.
