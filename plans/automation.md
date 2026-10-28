# Automation, scripting and plug-ins: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done" (ARC-12 is the
base of this file), then `plans/interface.md` (rules, kit, anatomy, UI-16.12).

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, this file's "Conventions" and "Definition of done", your area file, and `plans/interface.md` before
   you touch anything the user sees.
2. Claim the step in its file and push before starting (English or Turkish); one step at a time; push at least
   hourly; mark it done with the commit.
3. First search the code: reuse or improve what exists, never write it twice. Question the step: if a bullet is
   wrong, do what is right, write why under the step and tell the owner (no approval needed).
4. Research first (papers, reference programs' source); learn, never copy; nothing GPL bundled.
5. Synthetic test with known truth **and** real data against a reference; the reference numbers become a test.
6. Use the program as a user (real clicks, screenshots in four languages, looked at) before calling it done.
7. Only kit components in the interface; workflow first; one primary action; tooltips; undo; nothing locked.
8. Errors by code, saying what happened and what to do, translated into Turkish (German and Spanish wait for ARC-25,
   PLAN.md R0). Guide updated in English and Turkish.
9. Measure time and memory; meet the budget; CPU and GPU paths give the same result.
10. Commits in the owner's name only, no "Claude" anywhere; everything to `main`; never delete without the owner.

## Scope and goal

Doing things again without clicking again: recipes saved from any window, chains of steps with conditions and
loops, runs triggered by new files or by the end of a sequence, a Python console, a stable plug-in interface, and a
bundle that lets someone else reproduce a paper's numbers.

**Goal:** the scripting power that keeps people on IRAF, with none of its language: every action in a window is
already a step; a chain is built by dragging steps or by pressing "Save as recipe" after doing the work once; the
same recipe runs from the command line on a hundred nights.

## What the reference programs do

Read: IRAF CL (tasks with parameter files, `epar`, scripts, `@file` lists, `mkscript`); Siril scripts (`.ssf`
command files run on a working directory; Python scripts in 1.4 with an API to the running program); AstroImageJ
macros and the Data Processor's "run macro after each image"; PixInsight's process containers and
`WeightedBatchPreprocessing` (as descriptions); PypeIt's reduction files (`.pypeit`: a parameter block + a frame
table, run by one command); lightkurve / Astropy as libraries used from notebooks; N.I.N.A.'s plug-in system
(manifest, versions, a plug-in manager); QGIS's processing toolbox and model designer (typed inputs and outputs,
a graphical chain, batch mode).

| Topic | IRAF | Siril | PypeIt | QGIS model designer | Ours now |
| --- | --- | --- | --- | --- | --- |
| Unit of work | task with typed parameters and a help page | command | pipeline step | algorithm with typed parameters | step (`engine/steps.py`) with inputs, outputs and default values, untyped |
| Chain | CL script | script file | one reduction file | graph of algorithms | automation JSON: steps, links, "each" loops; five templates |
| Parameters remembered | parameter files per task | — | the reduction file | model inputs | the project's run records |
| Batch | `@lists`, loops | sequences | by set-up | batch dialog | "each" over a list |
| Triggers | — | — | — | — | after an observing sequence ends |
| Extending | CL scripts, SPP tasks | Python scripts | spectrograph classes | plug-ins | user step files in the plug-ins folder; a generated form; three examples |
| Console | the CL itself | command line in the window | — | Python console | none |

## What we already have (do not redo)

- `engine/automation.py` (format above; `needed`, `check`, `calls`, `run`), templates in `resources/automations/`,
  `engine/plugins.py` (user steps loaded in the window and in every worker), `ui/automation_page.py`,
  `ui/plugin_dialog.py`, `docs/PLUGINS.md`; automations run task by task and are recorded; an automation's observing
  part goes to the Observing window and the processing starts when the sequence ends.

## Decisions

- One format: the automation JSON grows into the **recipe** of ARC-12 (same file, a `version` field, old files
  load); TOML is accepted for hand-written recipes.
- Steps describe their parameters once (AUT-1); forms, command-line help, API documentation, validation and
  translation keys all come from that description.
- Plug-ins add steps, file readers and exporters. They do not add interface code; their forms are generated.
- Expressions inside recipes use the same safe evaluator as band maths (`ast`-based, no code execution).

## To ask the owner

- Whether the engine should also be published as a Python package on PyPI for notebook users (a public release
  decision; nothing depends on it).

## For the owner to try

- After AUT-W and AUT-2: do a night's photometry once by hand, press "Save as recipe", and run it on another night
  from the Automation window.

## Steps

Order of work: AUT-1 (engine, early: other areas' forms depend on it), AUT-W, then P1: 2, 3, 5; P2: 4, 6, 7, 8, 9;
P3: 10.

### AUT-1. Steps describe themselves  (P1)
**open** — items 1–3 started (2026-11-12): `engine/params.py` (`P(name, kind, default, unit, min, max, choices, label, help, advanced)`, the plan's kinds; labels and help marked for translation in the "Steps" context without Qt in the engine); `@step(..., params=[P…])` beside the old keyword form; `steps.execute` checks described values before running (number, whole number, range, true / false, choice; a translated message naming the setting); `astrowb-cli help` and docs/api show kind, unit, range and the help. Described: `timeseries.frequencies`, `timeseries.survey_lc`, `timeseries.oc_fit`, and with `steps.describe(step_id, P…)` beside the old form (a P's default must equal the step's, so a description never changes a step): period, minimum, mission light curves, quality, comparisons, apertures, variable search, catalogue magnitudes, transformation (AUT-1.1, photometry and time series); spectroscopy's orbit, RV, combine, disentangle, classification and stellar parameters (AUT-1.3, in `spectroscopy/step_params.py`); calibration scan and run, stack and drizzle (AUT-1.2, `calibration/step_params.py`). A ratchet (`tests/test_step_params.py`, `tests/data/steps_not_described.json`) lets the old form only shrink: 21 steps left. Left: the 21 steps (AUT-1.1 … 1.8 by area), `IO` descriptions of inputs and outputs, file-existence checks, the generated `ui/kit/stepform.py`, the recipe JSON Schema.
- **Read first:** QGIS processing parameter types (the idea of typed, self-describing parameters); IRAF parameter
  files (name, type, mode, default, min, max, prompt); Python's `inspect` and `typing`; our `ui/setting_names.py`
  and `ui/step_names.py` (today's hand-written names of steps and settings).
- **Ours now:** `@step(id, inputs, outputs, optional, **defaults)`: names only; display names and tooltips kept in
  separate interface files; the plug-in dialog guesses a form from default values.
- **Build:**
  1. `engine/params.py`: `P(name, kind, default, *, unit=None, min=None, max=None, choices=None, label, help,
     advanced=False, depends=None)` with kinds: `int`, `float`, `bool`, `text`, `choice`, `file`, `files`, `folder`,
     `xy` (pixel position), `positions`, `sky` (coordinates), `time`, `band`, `expression`, `table`, `object` (a
     result of another step, by its type name); `IO(name, kind, label, help)` for inputs and outputs with a data
     type name (`frames`, `light_curve`, `spectrum`, `minima`, `table`, …).
  2. `@step(id, inputs=[IO…], outputs=[IO…], params=[P…], title=…, summary=…, area=…)`; the old keyword form keeps
     working (parameters inferred as today) and a test lists the steps not yet described — the list must be empty
     when this step is done (every built-in step migrated, area by area as sub-steps AUT-1.1 … 1.8).
  3. Validation before a run: types, ranges, choices, file existence, units; violations as error codes naming the
     parameter in words.
  4. Labels and help texts are extracted for translation by `tools/i18n.py` (context `Steps`); `setting_names.py`
     and `step_names.py` become generated views of the registry and are then removed.
  5. Generators: the kit form for any step (`ui/kit/stepform.py`: `FormRow`s grouped, advanced folded,
     dependencies enabling / disabling rows); command-line help (ARC-12); API signatures and docstrings; the
     recipe schema (JSON Schema file for editors).
- **Accept:** every built-in step has full descriptions in four languages; the generated form of
  `calibration.run` shows the same controls as the hand-built panel's options; a recipe with a wrong parameter
  type is refused with the parameter named; old automations and plug-ins run unchanged.
- **Files:** `engine/{params,steps}.py`, every `*/steps.py`, `ui/kit/stepform.py`, `tools/i18n.py`, tests.

### AUT-W. The Automation window  (P1)
**open**
- `plans/interface.md` UI-16.12: library (steps and templates, searchable by area), the chain as cards with named
  links, the selected step's generated form, run log and results.
- **Extra accept:** build "calibrate → light curve → time of minimum → report" from the library in **eight
  clicks**; a missing input shows on the card in amber with the fix offered ("link it to … / ask me when run").
- **Depends on:** AUT-1, ARC-4.6, ARC-5, UI-1 … UI-4.
- **Files:** `ui/automation/{window,controller,state,menus}.py`, `ui/automation/panels/{library,chain,form,run}.py`, `tests/ui/walks/automation.py`, guide 11

### AUT-2. Recipes from what you just did, and chains that think  (P1)
**open**
- **Ours now:** `engine/automation.py` (chains, links, `each`), five templates, `ui/automation_page.py`.
- **Build:**
  1. "Save as recipe" in every area window (ARC-12): the session's steps in order with their parameters; inputs
     that should change next time (folders, files, target) become the recipe's **questions** (with defaults); star
     positions are saved as sky coordinates when a plate solution exists (so the recipe works on another night),
     else as pixels with a warning.
  2. Chain features beyond "each": conditions (`when: "quality.fwhm < 4"`), branches, loops over nights / targets /
     filters (a table input: one run per row), error policy per step (stop | skip this item | continue), named
     intermediate results, sub-recipes (a recipe used as a step), safe expressions for parameters (`"{exptime} *
     2"`), and "ask the user" pauses (confirm comparison stars, then go on).
  3. **Incremental runs**: a step whose inputs (by checksum), parameters and code version are unchanged since a
     recorded run is skipped and its recorded outputs reused (the provenance hash of ARC-11); "Run from here"; a
     plan view before running: what will run, what is reused, on which files.
  4. Run view: per step progress, the items of a loop with their state, results opened in their area window by a
     click ("Open this light curve in Photometry").
- **Accept:** the practice night done by hand → recipe → run on a second synthetic night (shifted pointing): same
  kind of results with no manual step; rerunning unchanged takes < 2 s (all reused); changing only the aperture
  radius reruns from photometry on; a failing frame in a loop is skipped and listed under the "skip" policy.
- **Files:** `core/recipe.py`, `engine/automation.py`, each window's controller (export), UI, tests.

### AUT-3. Templates for the common jobs  (P1)
**open**
- **Ours now:** eclipsing-binary night, exoplanet transit, end-of-night calibration, spectra to RV and orbit,
  variable-star period.
- **Build:** one template per guided task (UI-8) and per area's main path, each with questions, defaults and a
  two-line description in four languages: time-series night (one filter / several filters); transit to ExoClock /
  AAVSO report; whole-series minima → O−C; survey light curve → period → report; long slit raw → calibrated
  spectrum; échelle night → velocities; binary solution from light and velocity curves (estimate → fit → MCMC);
  asteroid astrometry → ADES; field variability search; all-sky standards night; detector characterisation;
  many nights calibration. Each template is a test: it runs on its practice set in CI.
- **Accept:** every template runs on its practice data from the Automation window and from the command line with
  identical products.
- **Files:** `resources/automations/*.json` (one per template), `tests/test_automation_templates.py`, guide 11

### AUT-4. Triggers and unattended processing  (P2)
**open**
- **Build:** triggers: manual; when an observing sequence ends (have); when new files appear in a folder (the
  recipe's file question bound to a watched folder; debounce; partial files ignored); at a time; `astrowb-cli watch
  recipe.toml` as a headless service for an observatory computer; a small "Automations running" list in the Tasks
  popover with pause / stop; results and failures notified (UI-9); never two runs of the same recipe on the same
  files at once (a lock in the output folder).
- **Accept:** a replayed night dropped file by file into a watched folder produces the same final products as the
  batch recipe; killing and restarting the watcher resumes without redoing finished frames.
- **Files:** `engine/triggers.py`, `__main__.py` (`watch` subcommand), `ui/kit/tasks.py` (running automations), `tests/test_triggers.py`

### AUT-5. Plug-ins, second version  (P1)
**open**
- **Ours now:** `engine/plugins.py` (load `.py` files from the plug-in folder, examples), `ui/plugin_dialog.py` (generated form), `docs/PLUGINS.md`.
- **Read first:** N.I.N.A.'s plug-in manifest and manager (as a model of what users need to see); Python packaging
  entry points; our `docs/PLUGINS.md`.
- **Build:** a plug-in is a folder or single file with a manifest (name, version, author, description, the
  application versions it supports, what it needs: network / writing outside the output folder); it may register
  **steps** (with AUT-1 descriptions → forms and menus by themselves, under the Plugins menu and in the Automation
  library), **readers** (`@reader(extensions, kind)` returning our `ImageSource` / `LightCurve` / `Spectrum1D` /
  table) and **exporters** (`@exporter(kind, name)` adding a report format); the manager (Settings → Plugins):
  install from a file or folder, enable / disable, the permissions it asked for, load errors in words, "Open the
  folder", the first-run warning with the file's hash (ARC-22); `astrowb-cli plugin check <path>` validates a
  plug-in (manifest, imports, a dry call of each step on tiny synthetic inputs when the author provides them); a
  template plug-in and a page of the guide written for a scientist who knows a little Python.
- **Accept:** the three example plug-ins ported; a new reader plug-in for a made-up text format makes its files
  open in Light curves; a broken plug-in is reported and does not stop the program; the stability test of
  `astrowb.api` covers what plug-ins may import.
- **Files:** `engine/plugins.py`, `engine/extension_points.py` (`reader`, `exporter`), `ui/shell/settings/plugins.py`, `resources/plugins/` (examples and template), `docs/PLUGINS.md` (generated), `tests/test_plugins.py`

### AUT-6. A Python console inside the program  (P2)
**open**
- **Build:** Tools → "Console": an editor pane (our own on `QPlainTextEdit`: syntax colours, line numbers, run
  selection / file, find) and an output pane; code runs in a worker process with `astrowb.api` imported and
  read-only snapshots of the windows' current data offered as variables (`photometry.light_curve`,
  `spectroscopy.active_spectrum`, `oc.minima` …); results that are tables, light curves, spectra or figure specs
  open as tabs (`TableView`, `PlotView`); "Copy as Python" from any window pastes here; snippets library (the
  guide's scripting examples); the session's scripts saved in the project. No notebook server is bundled; the guide
  explains using the engine from an external Python / Jupyter when installed with `pip`.
- **Accept:** the script produced by "Copy as Python" in Photometry runs in the console and returns the same light
  curve; an exception shows the traceback in the output pane without affecting the window; a long loop can be
  stopped.
- **Files:** `ui/shell/tools/console.py`, `ui/kit/code_editor.py`, `engine/script_runner.py` (worker side), `tests/ui/test_console.py`

### AUT-7. Batches and parameter studies  (P2)
**open**
- **Build:** run a recipe over a table (CSV: one row per night / target with its questions' answers) with a summary
  table of results and failures; parameter sweeps (a parameter over a list or range → a table and plot of chosen
  outputs against it, e.g. aperture radius against light-curve scatter); parallelism bounded by cores and memory
  (`engine.parallel`).
- **Accept:** a sweep of aperture radius on the Qatar-1 night reproduces the aperture-scan result of Photometry.
- **Files:** `core/recipe.py` (table runs, sweeps), `ui/automation/panels/batch.py`, `tests/test_recipe_batch.py`

### AUT-8. The reproducibility bundle  (P2)
**open**
- **Build:** File → "Export for publication…": a zip with the recipe(s), the answers used, checksums and locations
  of every input (and the inputs themselves on request), the products, the methods text and BibTeX (ARC-11), the
  environment (versions, the lock file's hash), and a `REPRODUCE.md`; `astrowb-cli reproduce bundle.zip` reruns and
  compares (identical or the largest differences per product); suitable for a paper's supplementary material or a
  data repository.
- **Accept:** the practice night's bundle reproduces on another machine class in CI (Linux → Windows) within the
  cross-platform tolerance of VAL-9.
- **Files:** `core/bundle.py`, `__main__.py` (`reproduce` subcommand), `ui/shell/project/export.py`, `tests/test_bundle.py`

### AUT-9. External programs as steps  (P2)
**open**
- **Build:** a generic step "run an external program" (command template with input / output file patterns, a
  time-out, the working folder inside the output folder), shown with the permission prompt of ARC-22 and never run
  from a recipe received from elsewhere without the user's confirmation; ready descriptions for tools users may
  have installed (ASTAP, astrometry.net's `solve-field`, Find_Orb, MOOG, Source Extractor) that other areas'
  adapters use.
- **Accept:** a recipe step calling a harmless test program runs after confirmation and is refused when the
  confirmation is declined; the command is recorded in the provenance.
- **Files:** `engine/external.py`, step `external.run`, `resources/external_tools/*.toml`, `tests/test_external_step.py`

### AUT-10. Interop of recipes  (P3)
**open**
- **Build:** export a calibration + stacking recipe as a Siril script and a photometry star list as an
  AstroImageJ apertures / RA–Dec file, where the meaning maps cleanly; import of an AstroImageJ measurements table
  as a light curve (PHO) — for users who move between programs.
- **Accept:** the exported Siril script's commands exist in Siril's reference and reference the right files
  (checked textually; Siril itself is not run in CI).
- **Files:** `core/interop/{siril_script,aij_files}.py`, tests with stored expected texts

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
