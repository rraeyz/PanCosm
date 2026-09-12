# Spectroscopy and radial velocities: plan

## Most important rules (this block heads every plan file)

> Came straight to an area file? Stop and read `PLAN.md` first, all of it. Then come back.

1. **Never stop.** Work until the work is finished or your quota ends, unless the owner interrupts.
   - Set yourself reminders so that a pause, a sleep or a lost session does not end the work: a scheduled wake-up
     every 30–60 minutes, or what suits the work. You choose the interval.
2. **Claim every step.**
   - Before starting: write `**agentN claimed (date) — do not touch**` and push.
   - When finished: push the work, then write `**agentN done (date, commit)**`.
   - Claim the next step before starting it (PLAN.md R2).
3. **Research first.** The scientific basis, the reference programs' source code (learn, never copy), the
   internet, real data.
4. **Test as a real user, not only in code (the most important test, PLAN.md R3).**
   - Install the program the way a user installs it.
   - Run it on a machine without a display (offscreen or Xvfb) with real clicks (QTest).
   - Take a screenshot of every window and every step, and look at each one.
   - At every screen ask:
     - Would a newcomer know what to do?
     - Is the button in the right place, and is it explained?
     - Is anything missing?
     - Does it fit the screen?
     - Is it clear in every language?
   - Every problem found becomes a task (rule 5). After the fix, use the program again.
5. **Add the tasks you find.** Research, the internet, trials and tests all show work to do. Add it to the area
   file at the place its urgency deserves, not necessarily at the end. An area is finished only when it is
   excellent.
6. **Engine code may be changed** where it is wrong or missing, old core files included. New features may be
   added. **Never delete what looks unnecessary:** note it under "To ask the owner" and delete it only after the
   owner agrees.
7. **Time, memory, GPU.**
   - Measure the time and memory of what you build.
   - Never make the program slower to save memory.
   - **Anything that should run on a GPU must run on both the CPU and the GPU.** The program picks one by the
     machine (a usable GPU or not) and by the user's choice (Settings → Processing device: automatic / CPU / GPU),
     through the `compute` module. Both paths give the same result, and a test checks it.
8. **Everything goes to `main`.** No branches and no pull requests for the owner to deal with.
9. **The workflow comes first.** No wall of buttons. The right default. Rarely used options folded.
10. **Use the right language for each part.** Python is not compulsory.
    - Python and Qt (PySide6) stay the base: the science libraries and the interface.
    - Where speed matters and Python is too slow, write that part in what does it best: numba, Cython or C/C++
      (pybind11), Rust (PyO3), or GPU kernels (CUDA / OpenCL). Measure before and after.
    - The part must build and run on Linux (x86 and ARM), Windows and macOS (Intel and Apple) in CI and inside the
      packaged program.
    - Its licence must be permissive (PLAN.md R1).
11. **Commits are made in the owner's name, always:**
    `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`.
    - Name: İdris Avlar. E-mail: rraeyz@hotmail.com. GitHub user: rraeyz.
    - No "Claude" anywhere in a commit: no author, no co-author and no session lines, whatever a hook asks.
12. **Follow the plan, but question it.**
    - Before doing a step, check it yourself again: a second look often shows something different.
    - You may change, add or remove steps, and their details, **only when you are really sure**. Write why, under
      the step: what you found, and what you read or measured.
    - Removing a step from a plan is allowed this way. Deleting code or a feature still needs the owner's yes
      (rule 6).
13. **Write plans in detail.**
    - A step says what to build, what the reference programs do, how to check it, and which files it touches.
    - A step may be split into sub-steps (3.1, 3.2 …) to stay planned. Each sub-step is claimed and marked done
      like a step.
14. **Error messages are part of the work.** Every failure the user can meet says what happened and what to do, in
    plain words, in every interface language: a template in `ui/messages.py` and a test. A step is not done while
    one of its errors shows a raw technical message.
15. **Releases.** You may release a new version without asking, when a meaningful piece is ready for the owner to
    try. Never release for every small change.
    - CI must be green on every system first.
    - Never push while a release run is going.
    - Give each release a short list of changes in Turkish for the owner (PLAN.md R6).
    - **A release is not the end:** go on with the next step at once.
16. **Report to the owner honestly**, in Turkish and briefly: what was done, what was not tested, and what the owner
    must do or try. Never call something working that was not tried.
17. **Data sets are listed in `data/`** with links and the exact files used (`data/README.md`); the observations
    themselves are not kept in git.
    - Download the files there; git ignores them.
    - Add every new set you use, so that the next agent measures the same files.
18. **Keep working with others safe.**
    - Pull the newest `main` before claiming a step.
    - Commit small and often.
    - Old projects, sessions and settings must still open after a change (a test checks it).
    - A check against a reference program becomes a test (reduced reference values from public data), so that a
      later change cannot quietly make results worse.

The rules that matter most here:

- **Read how the reference programs do it before each step:** IRAF `apall`, `identify` / `reidentify`, `dispcor`,
  `echelle`, `fxcor`; PypeIt (`pypeit/core/gui/identify.py`, `object_find.py`, `skysub_regions.py`); specreduce;
  iSpec (`ispec/gui/iSpecBaseApp.py`). **Learn, never copy:** iSpec is AGPL, PypeIt BSD-3 — the code is not taken
  either way (PLAN.md R1).
- **Real data, every step:** the sets in `data/spectroscopy/` (EFOSC2 long slit with its arcs, FLOYDS, FEROS and
  HARPS échelle products, TOFES), files in the scratchpad, never committed.
- **The workflow first.** Each job (long slit, échelle, telluric, velocities, IFU, tools) is a short line of numbered
  steps; what is not needed is folded.
- **Never a silent wrong result:** a wavelength fit with too few lines, an extraction off the trace, a velocity
  from a flat correlation peak each say so, with what to do.
- **Claim each step before starting it** (PLAN.md R2) and enter every feature the user sees in
  `plans/interface.md` "Where everything is".

## Research notes

Read 2026-11-08 (agent2) for the window layout (interface I6); read again for each step's detail.

- **iSpec** (`ispec/gui/iSpecBaseApp.py`, Tk): one large spectrum plot fills the window; several spectra are open at
  once and drawn together, the active one chosen in a "Spectra" menu (radio items, plus duplicate / close). Under the
  plot a strip of two radio groups — *Action* (Stats, Create, Modify, Remove) × *Element* (Continuum, Lines,
  Segments) — so a drag on the plot creates, moves or removes regions of that kind; below it a five-line list of
  statistics of the region clicked; a status bar. Every operation (fit continuum, fit lines, velocity, SNR,
  parameters with grids / synthesis / equivalent widths) is a menu item that opens a dialog with its settings.
  Files menu: open / save spectra and the three region kinds. Lesson: the spectrum is the window; regions are drawn
  on it with a mode, not typed; multi-spectrum overlay with an active one.
- **PypeIt Identify** (`core/gui/identify.py`, matplotlib): the arc spectrum takes the left ~65 % of the window; on
  the right two stacked panels — pixel → wavelength fit, and residuals (pixels) with the tolerance band shaded and
  points coloured by their state; an info line on top ("press ? for the keys"); a slider through the line list. Keys:
  a auto-identify with the current solution, f fit, z delete one ID, +/- polynomial order, w toggle pixels ↔
  wavelength on the x axis, g a "ghost" of predicted line positions, s / l save and load IDs. Lesson: fit and
  residuals always in sight beside the arc, so each click shows its effect at once.
- **PypeIt object_find / skysub_regions:** the 2D frame with the object traces drawn; keys add / delete a trace,
  centre on the mouse; sky regions are dragged on the frame. Lesson: the trace and the sky regions are edited on the
  2D frame itself.
- **IRAF** (from the task help pages): `apall` opens an aperture editor on the spatial profile (keys: m mark, d
  delete, l / u lower / upper limits, b background regions, then t to trace and f to fit the trace), then extracts;
  `identify` plots the arc, m marks a line and asks its wavelength, f fits and shows the residuals in a second plot
  where d deletes a point and q returns. Lesson: profile → trace → extraction and mark → fit → residuals are the two
  loops users know; ours follow them (R2 already named them in the Workflow line).

## What we already have

(do not redo — `ui/spectro_page.py`, `ui/spectrum_tools.py`, `spectroscopy/*`, steps in `spectroscopy/steps.py`)

- The **Spectroscopy window** (interface I4.4) holds the old page unchanged: an instrument-profile row (orientation,
  apertures, line list, orders saved by name), the "In what order? (click)" box (interface I4c), and six tabs —
  Reduce (long slit), Echelle, Telluric, Radial velocity & orbit, IFU cube, Spectrum tools. Each tab is a steps
  column on the left and **one plot canvas** on the right.
- **Reduce:** science + arc files, orientation, trace row, aperture / sky widths, Horne optimal extraction, sky-line
  zero point, line list; identify by clicking arc lines and typing wavelengths, fit, leave out points in the
  residual plot. The frame with the trace, the spectrum, the arc and the residuals are **stacked subplots in the one
  canvas** (`ReduceTab.show_spectrum`).
- **Echelle:** order tracing and extraction, blaze, merging; **Telluric:** division by a hot star; **Velocity:**
  CCF / TODCOR / broadening function, SB2 orbit, MK spectral type, profiles; **IFU cube** (with an image viewer);
  **Spectrum tools:** normalise, line measurements (EW, FWHM, V/R), smoothing, sum / divide, atmospheric parameters.
- Tests: `test_spectroscopy.py`, `test_echelle.py` and others; the EFOSC2 night reduces (interface I6a screenshots
  `40_spec_files`, `41_spec_velocity_tab`).

## To ask the owner

- (none yet)

## For the owner to try

- (after step 1) open one of your own long-slit nights in the new window and say whether the frame, the trace and
  the spectrum are where you expect them.

## Data used

- `data/spectroscopy/efosc-longslit` (LTT 3864 + HeAr arc): the I6a walk; Reduce.

## Steps

**Waiting for its turn** (PLAN.md "Order of work"): after 1.2, the steps here wait until Interface and Photometry are
done. When this area's turn comes, its first step is **R** below.

### R. Full research of the area (before any further step)
**open** — added 2026-11-08. The research above covers the window's layout only (iSpec, PypeIt and IRAF GUIs).
- **Build:** the same analysis as `plans/photometry.md` had, written here as steps with reference, ours now, build and
  accept. Read the code of IRAF (`noao/twodspec`, `onedspec`, `imred/echelle`: apall, identify / reidentify,
  dispcor, sensfunc / calibrate, scombine, continuum, splot, fxcor), PypeIt (extraction, wavelength, flexure, sky
  subtraction, flux calibration, telluric), specreduce, iSpec (normalisation, line fitting, parameters, radial
  velocities). Cover at least:
  - 2-D: slit tilt and rectification, sky subtraction (b-spline, Kelson 2003), cosmic rays on 2-D frames;
  - extraction (boxcar, optimal), error spectra carried through every step;
  - wavelength: identification, flexure from sky lines, resolution measured;
  - flux calibration with standard stars (sensitivity function, extinction);
  - telluric (standard star and models);
  - echelle: blaze and order merging;
  - continuum normalisation;
  - line measurements;
  - radial velocities: CCF, TODCOR and broadening function, checked against published values;
  - file formats (1-D FITS WCS, multispec, ESO / LAMOST);
  - the user's workflow from raw frames to a published spectrum.
- **Accept:** every reference capability has a step or a reason it is not needed; each step names the real data
  (`data/spectroscopy/…`) to check it on.


### 0. Several exposures of one star combined; the master bias for spectra (PLAN.md "Decisions", first item)
**agent2 done (2026-11-08, commit 1ad0072)** — `spectroscopy/combine.py` + step `spectroscopy.combine`;
Spectrum tools → *Combine exposures…*; the Reduce tab now says which frames it takes as calibrated and which are
raw (Echelle did only the latter). What the real data showed:
  - TZ For, HARPS ADP: the archive file names are **processing** dates; three "same night" files were MJD 55431,
    55479, 55536. Combined, the binary's moving lines were rejected on 7 % of the pixels → the step now warns when
    the exposures span more than half a day (and says to combine one night at a time).
  - HARPS s1d is oversampled (0.01 Å): the point-to-point noise underestimates the real noise, so σ-clipping on
    it rejected two thirds of the pixels. The threshold now comes from each exposure's scatter about the median
    in blocks (when larger than its errors); noise without errors is estimated in blocks along the spectrum (the
    S/N changes ×2 from blue to red). The error column of these files is all NaN: handled.
  - The continuum shapes of two exposures differ by 7 % from blue to red (fibre losses): scale "shape" (a smooth
    ratio, the lines cancel) besides "median".
  - The one real one-night pair (TZ For, MJD 56213, 2 × 150 s): no pixel rejected; S/N in a 2.5 Å window 130 and
    137 → 157 (the window's weak lines cap the measure; the synthetic test checks √N exactly). 313 000 pixels × 3:
    0.6 s, 75 MB.
  - Barycentric correction left out on purpose: within a night it changes by tens of m/s; across nights the
    warning applies (rule 12: written here instead of the plan's "applied first").
  - Master bias: `test_arc_lamps_are_calibrated_without_flat_and_kept_apart` now checks the science frame too
    (bias off, flat divided), the arc (bias only), and that Spectroscopy's `calibrated()` takes both.
- Reference: IRAF `scombine` (combine = average | median | sum, reject = none | minmax | avsigclip | ccdclip …,
  scale / weight by exposure time or signal, on a common wavelength grid: `dispcor` first); `zerocombine` +
  `ccdproc zerocor` for the master bias ("Zero"), used the same way for spectra as for images.
- Ours now: Spectrum tools has an operation with one spectrum B (sum / divide); the échelle orders of one exposure
  are merged; no step combines N exposures. Bias and dark come from the Calibration window (`spectro_page` Workflow
  step 1 says so; arcs bias / dark only).
- Build:
  - a step `spectroscopy.combine` (inputs: spectra; params: combine mean | median | sum, rejection none | σ-clip |
    min/max, scale none | exposure | median flux, weight none | S/N): resampled to one wavelength grid (the finest
    of the inputs, flux conserved), barycentric correction applied first when the inputs carry it; output one
    spectrum with its error and the number of exposures per pixel;
  - in Spectrum tools: "Combine exposures…" (choose files, settings folded);
  - check (and test) that a master bias made in Calibration is subtracted from a long-slit science frame and its
    arc, and that frames already calibrated are taken as they are with a note saying so.
- Accept: three EFOSC2 or FEROS exposures of one star combine to a spectrum whose S/N is √3 × one (within 10 %);
  a cosmic ray in one exposure is gone with σ-clipping; the bias test passes; CPU only (cheap).
- Files: `spectroscopy/combine.py` (new), `spectroscopy/steps.py`, `ui/spectrum_tools.py`, step and setting names,
  tests, guide 08.

### 1. The Spectroscopy window's own layout (interface I6 for this area)
**open**
- Reference: iSpec (the spectrum is the window, several overlaid), PypeIt Identify (fit + residuals beside the arc),
  PypeIt object_find (traces on the 2D frame), our Photometry window (interface I5: view in the middle, steps on
  the left, results below).
- Ours now: a page in a scroll area; every tab crams its views into one canvas beside a long steps column; at 1366 ×
  768 the "In what order?" box and the profile row take a quarter of the height before the tabs.
- Build:
  - **1.1 Job choice and steps panel.** **agent2 done (2026-11-08, commit f4191c1)** — `SpectroscopyPage.window_parts`,
    `MainWindow._spectroscopy_window`: six checkable job buttons on the toolbar and in the Job menu (tooltips say
    what each job is for), the job's steps column in the left panel (as wide as the widest column needs), the
    profile row on top of it for Reduce / Echelle only, the job's own view in the middle; the hidden tab widget
    still holds the current job, so `tabs.setCurrentWidget` keeps working. Screenshots scratchpad
    `s1/tr/40_spec_files.png`, `41_spec_velocity_tab.png`. 1.4 done with it: the box is folded in every mode.
    Found: a closing window deleted the jobs' tables before their undo stacks (`undo.track_typing` now checks). The six tabs become the window's *job*: a toolbar row of six checkable
    buttons (Long slit, Echelle, Telluric, Velocities & orbit, IFU cube, Spectrum tools) and View → Job; the chosen
    job's steps column is the left panel "Steps"; the instrument-profile row moves to the top of that panel (it
    belongs to the reduction jobs only).
  - **1.2 The view in the middle.** **agent2 claimed (2026-11-08) — do not touch** Reduce and Echelle: the 2D frame (`ImageViewer`) with the trace, the aperture
    and the sky bands drawn on it (PypeIt object_find, IRAF apall) instead of an `imshow` subplot; the other jobs:
    their spectrum / velocity plot.
  - **1.3 Panels.** "Spectrum" (bottom): the extracted spectrum, and for the arc the arc spectrum with its marks;
    "Fit" (right): pixel → wavelength fit and residuals stacked (PypeIt Identify), so a click on a line or a
    residual shows its effect at once. Each a `PlotCanvas` with its Export data.
  - **1.4 "In what order?"** **agent2 done (2026-11-08, commit f4191c1)** (closes interface I4c): its text goes into the job buttons' tooltips and the window's
    Help → Guide for this window; the box is removed from the window only after the owner's yes (rule 6) — until
    then folded by default.
- Accept: at 1366 × 768 (tr, de, en, es) the EFOSC2 frame with its trace, the extracted spectrum and the fit /
  residuals are visible at once, without scrolling the window; every panel can be pulled out and comes back; the I6a
  walk shows no cut text; old settings open.
- Files: `ui/spectro_page.py` (window_parts like `PhotometryPage`), `ui/main_window.py` (`_spectroscopy_window`),
  tests in `tests/test_spectroscopy.py`, guide 08 in four languages.

### 2. Keys in the arc identification
**agent2 claimed (2026-11-08) — do not touch**
- Reference: PypeIt Identify keys (a, f, z, +/-, w, ?) and IRAF identify (m, f, d, q).
- Build: in the arc plot: f fit, z / Delete remove the line under the mouse, +/- the fit order, w pixels ↔
  wavelength, ? lists the keys; each also a menu action (Measure menu) with its shortcut shown.
- Accept: a test drives the keys on the EFOSC2 arc and gets the same fit as the buttons.

### 3. Several spectra in one plot, one of them active (Spectrum tools)
**open**
- Reference: iSpec "Spectra" menu.
- Build: open several spectra; each drawn in its own colour, the active one in front and the one the tools act on;
  a list in the panel to choose, hide or close them.
- Accept: two FEROS spectra of AI Phe at different phases drawn together; normalising acts on the active one only.

## Done

- Step 0 (2026-11-08, agent2, commit 1ad0072): combine exposures, calibrated-frame note.
