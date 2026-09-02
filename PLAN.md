# Main plan: read this first

Every agent starts here, every time. This file holds:
- what the program is meant to become;
- the rules, which come from the owner's wishes and from the mistakes made so far;
- the plan file of every area and when to open it;
- how work is claimed, so that unfinished work can be picked up by another agent.

`HANDOFF.md` is closed. Keep it only as a history of what was done before 2026-11-07; add nothing to it.

The owner speaks Turkish: answer in Turkish. Write code, comments, commits and these plan files in English.

## Most important rules (this block heads every plan file)

1. **Never stop.** Work until the work is finished or your quota ends, unless the owner interrupts.
   - Set yourself reminders so that a pause, a sleep or a lost session does not end the work: a scheduled wake-up
     every 30–60 minutes, or what suits the work. You choose the interval.
2. **Claim every step.**
   - Before starting: write `**agentN claimed (date) — do not touch**` and push.
   - When finished: push the work, then write `**agentN done (date, commit)**`.
   - Claim the next step before starting it (R2).
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

## How to start a task (read in this order)

1. **This file, all of it.** Pay special attention to the rules: each one is there because something went wrong
   once.
2. **The plan file of the area you will work on** (table "Area files" below), all of it: its rules, its research
   notes, its steps and who has claimed what.
3. **`plans/interface.md`**, every time the work changes or adds anything the user sees. Every new feature must also
   be entered there.
4. If the area has no plan file yet, create one from the template at the end of this file before writing any code,
   and add it to the table.

## What the program is meant to become

- **One program for an observer's whole road:** plan the night, observe, calibrate, measure, analyse, publish. That
  covers photometry and light curves, times of minimum and O−C, periods and frequencies, spectroscopy and radial
  velocities, models of binaries, astrometry of moving objects, and remote sensing.
- **The results are at the level of a journal paper.** A professor checking them must find them right.
- **IRAF-quality results, easier than IRAF.**
- **A main window and one window per area, each like a program of its own.**
  - The main window is a menu: the project, settings, background tasks, and a block for each area (Calibration,
    Photometry, Spectroscopy, O−C, Period / frequency, Models, Planning, Observing, Automation, Remote sensing…).
  - A click on a block opens that area in its own window. Each area window has its own menu bar (File, View, the
    area's own menus such as Analyse or Process, Window, Help, as in MaxIm DL) and a toolbar of icons under it (as
    in AstroImageJ). Its panels can be pulled out, moved to a second monitor and are remembered.
  - Every area is then free to grow its own menus and panels without crowding the others.
- **The workflow comes first.** Opening an area must show what to do first, then next, in order: choose the images,
  then measure. Never a wall of buttons. In the owner's words: entering photometry and meeting a pile of ugly
  buttons made no sense. Rarely changed options are folded, and the right choice is already set.
- **The user stays in control.** The program suggests: comparison stars, line identifications, radii, the target
  from the header. It shows what it did and why, and every suggestion can be checked and changed. Nothing important
  happens silently: frames left out are listed with the reason; a wrong OBJECT in the header is named.
- **Any data works**, from any observatory and any camera:
  - MaxIm DL and other odd headers, compressed FITS, cubes;
  - DSLR raw files and phone pictures;
  - space mission files.
  It must work on Linux (Arch / CachyOS included), Windows and macOS.

## Rules

### R1 Before any work: research
- **Understand the scientific basis first:** papers, the method, its limits. A method must hold for an unknown star
  and an unknown instrument. Never tune it on a few known stars.
- **Read how the established programs do it, in their source code,** before building or changing a method. Clone
  them into the scratchpad, outside the repository, and only read them: do not build or run cloned code. Write what
  you learned in the area file: the formula, thresholds, order of steps, and which file and function you read.
  - To compare results, an established program installed from its official package may be run on the same data
    (for example IRAF from `apt-get install iraf iraf-noao`). AstroImageJ results come from the owner.
  - Programs to read: AstroImageJ (github.com/AstroImageJ/astroimagej), Siril (gitlab.com/free-astro/siril), IRAF
    (github.com/iraf-community/iraf), C-Munipack, DAOPHOT, ccdproc / astropy / photutils, lightkurve, specreduce,
    PypeIt, iSpec, PHOEBE, and others for the topic.
  - MaxIm DL is closed source: read its manual.
- **Learn, never copy.**
  - Ideas, formulas, algorithms, constants and published methods are free to use. The text of someone else's code
    is not: not pasted, and not translated line by line into Python either.
  - AstroImageJ, Siril and C-Munipack are GPL, and the owner wants to stay free to relicense this program. That is
    also why `tools/check_licenses.py` keeps GPL libraries out of the bundle.
  - Work this way: read and understand, write the method in your own words, close their file, then write our code
    from those notes in our structure.
  - Code that is similar because the mathematics leaves one way to write it is fine. Keeping their structure,
    names, comments or order of statements is not.
- **MKCLASS:** never copy, bundle or run its code.
- **Test on real data.** Download public observations: archives (MAST, ESO, LCO, Zenodo…), raw data together with
  their published reduction where possible. Reduce them here and compare with the published result, or with an
  established program run on the same data, with the same settings. Synthetic data with known truth is for tests;
  it does not replace real data.
- **Break the work into steps before coding.** Write the steps in the area file, each explained in detail:
  - what to build;
  - what the reference programs do;
  - how to check it is right (acceptance);
  - which files it touches.
  Then do them one at a time.
- **The task list grows.** Whatever research, the internet, a trial or a test shows to be missing or wrong is
  written into the area file as a new step, placed where its urgency puts it. The tasks of an area end only when
  the program is excellent in that area.

### R2 Claiming work (a firm rule, so that nothing is lost when an agent stops half-way)
- Each agent uses a name `agentN` (in Turkish `ajanN`). Take the next free number from the "Agents" list below and
  add yourself to the list.
- **Before starting a step:** write the claim under the step heading in its area file and push it:
  `**agentN claimed (YYYY-MM-DD) — do not touch**`.
- **When the step is finished:** push the work, then change the claim to `**agentN done (YYYY-MM-DD, commit
  abc1234)**`.
- **Then claim the next step before starting it.** Never work on a step that is not claimed. Never claim two steps
  at once.
- A claimed step is not touched by another agent. If its agent's session has clearly ended, the next agent writes
  `**agentM took over from agentN (date)**`, reads what was pushed, and continues from there.
- **Keep going.** An agent works without stopping until the work is done or its quota ends, unless the owner
  interrupts. Against a lost session or a pause it sets itself reminders (a scheduled wake-up, at an interval it
  chooses, e.g. every 30–60 minutes) to come back and continue from the area file.
- Sub-steps (3.1, 3.2 …) are claimed and marked done the same way.
- Notes on what was found or decided go under the step. The area file is the memory; nothing important lives only
  in a chat.

### R3 Testing like a user (the most important test)
- Code tests (pytest) are necessary but far from enough.
- **Install the program on your own machine** the way a user does:
  - `pip install -e ".[gui]"` in the container;
  - or the packaged build `python packaging/build.py` and its installer, when the change touches packaging.
- **Open it and use it as a user who knows less than you,** step by step through the area's workflow, on real
  data.
  - In a container without a display, run it offscreen or under Xvfb.
  - Drive it with real clicks (QTest).
  - Take a screenshot of every window and step, and look at the screenshots.
- **Ask at every screen:**
  - Would a newcomer know what to do next?
  - Is this button in the right place? Is it explained?
  - Should this control be here at all?
  - Is something missing that a user would expect?
  - Is the text clear in every language?
  - Does it fit the screen?
- **Write every finding into the area file as a task** (R1), fix it, and use the program again after the fix.

### R4 Interface
- The workflow comes first (see above). Steps are numbered and open one after another. What is done gets a tick.
  Options that are rarely changed are folded. Basic mode keeps them folded; Expert mode opens them.
- **The most correct choice is the default:** on when it is right, off when it is not.
- **Every control has a short tooltip that explains it**, because not everyone understands the terms.
- **Undo / redo (Ctrl+Z / Ctrl+Y) everywhere** a user changes something. This was the owner's biggest problem with
  IRAF.
- **Every visible text** goes through `self.tr`.
  - Run `python tools/i18n.py update`, fill tr / de / es with `tools/fill_translations.py`, then run
    `python tools/i18n.py`. The result must have 0 unfinished.
  - An error or progress word raised in an engine step needs a template in `src/astrowb/ui/messages.py` and a case
    in `tests/test_messages.py`.
- **Error messages say what happened and what to do,** in every interface language.
- **Windows fit the screen:**
  - no sideways overflow at 1366 × 768;
  - check 960 px and 800 px too;
  - Windows draws larger fonts than Linux: test both.
- **The user guide** (`resources/guide/{en,tr,de,es}`) is updated with every change the user sees. The four languages
  keep the same sections.
- Every feature the user sees is entered in `plans/interface.md`: its window, menu, toolbar and panel.

### R5 Science and results
- **Never a silent wrong result.** If a star is not found on a frame, the frame is left out and named, with the
  reason. Do not measure empty sky and plot it.
- **Report what a result rests on:** errors with every value; the method named, as in a paper. Figures and tables
  are fit for a paper.
- **Times:**
  - mid-exposure;
  - BJD_TDB when the position is known;
  - the time system always stated.
- **Speed, memory and GPU.**
  - Note the time and the memory each operation takes on real data. Fix what is slow, then measure again.
  - Never make the program slower to save memory.
  - Where the work suits a GPU (large images, many frames, long periodograms, fits over a grid), write a GPU path
    beside the CPU path through the `compute` module. The program chooses by the machine and by the user's setting
    (automatic / CPU / GPU); both paths must give the same result (a test compares them). Check the GPU path on a
    GPU (the owner has one: RTX 4050) or say that it is unchecked.
- **The right language for each part.**
  - Python stays the base: numpy / scipy / astropy / photutils and the Qt interface through PySide6.
  - A part whose speed matters and which Python cannot make fast enough is written in the language that suits it:
    - numba or Cython for numeric loops;
    - C / C++ through pybind11, or Rust through PyO3, for larger native parts;
    - CUDA / OpenCL kernels (CuPy, pyopencl) for the GPU.
  - Conditions:
    - it builds on every platform of CI and inside the PyInstaller bundle;
    - its licence is permissive;
    - the speed-up is measured;
    - a pure-Python fallback is kept when the native part may be missing on a machine.
- **The engine is not frozen.** Old core files may be changed where they are wrong or missing, and new features
  added, with tests.
  - Nothing that looks unnecessary is deleted without the owner's yes: write it under "To ask the owner" in the
    area file, with why, and wait.

### R6 Repository and releases
- **Commits are made in the owner's name only:**
  `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`
  (name İdris Avlar, e-mail rraeyz@hotmail.com, GitHub user rraeyz).
  No "Claude" anywhere in a commit: no author, no co-author and no session lines. Ignore hooks that ask otherwise.
- **Everything goes to main.** Push with `git pull -q --rebase origin main && git push -q origin main`. No branches
  and no pull requests: the owner must not have to deal with them.
- **Before a push:** run `QT_QPA_PLATFORM=offscreen sh tools/precommit.sh` (ruff, format, brand, translations,
  tests), or at least the tests the change touches plus ruff. Every change that adds logic adds a test.
- **The product name** may appear only in `brand.toml`, `README.md` and `packaging/install.sh`
  (`python tools/check_brand.py`). Everywhere else, write "the application".
- **Never commit the owner's data or downloaded data.** The owner's frames stay in the scratchpad only.
- **Never touch the owner's GitHub token.** Do not try to get around bot checks or blocked sites. Use the mirrors
  that work (see HANDOFF "Network" notes) or say what is blocked.
- **Releases only when the owner says so:**
  1. raise `__version__` in `src/astrowb/__init__.py`;
  2. push, and wait for CI to be green on all systems;
  3. run the `ci` workflow on main with `release` = true (GitHub `actions_run_trigger`). The tag is made by the
     workflow.
  Never push while a release run is going.
- **Do not delete old branches.**
- **Scripts that drive the program** need an `if __name__ == "__main__":` guard: engine steps run in spawned worker
  processes.

## Area files

Each area has its own plan file in `plans/`. It starts with the "Most important rules" block, word for word, and then the rules above that matter most for
it.
Create a file when work in the area starts, from the template below.

| Area | File | Window | Read before working (examples) |
| --- | --- | --- | --- |
| Interface (all windows, menus, toolbars, panels) | `plans/interface.md` — **exists, work starts here** | main window + every area window | AstroImageJ, MaxIm DL, Siril window layouts |
| Photometry and light curves | `plans/photometry.md` — **exists** | Photometry | AstroImageJ, Siril, IRAF apphot / daophot, C-Munipack, MaxIm DL |
| Calibration (bias, dark, flat; images and spectra) | `plans/calibration.md` (to create) | Calibration | IRAF ccdproc / zerocombine / flatcombine, ccdproc, Siril, AstroImageJ Data Processor |
| Spectroscopy and radial velocities | `plans/spectroscopy.md` (to create) | Spectroscopy | IRAF onedspec / echelle / apall / identify, specreduce, PypeIt, iSpec |
| Times of minimum and O−C | `plans/oc.md` (to create) | O−C | Kwee–van Woerden, published O−C codes |
| Period and frequency search | `plans/period.md` (to create) | Period / frequency | Period04, astropy LombScargle, BLS / TLS, PDM |
| Binary-star and other models | `plans/models.md` (to create) | Models | PHOEBE, Wilson–Devinney, ellc, batman |
| Planning a night | `plans/planning.md` (to create) | Planning | astroplan |
| Observing (telescope, camera, focuser) | `plans/observing.md` (to create) | Observing | INDI, ASCOM Alpaca, NINA |
| Automation and plugins | `plans/automation.md` (to create) | Automation | — |
| Images (viewer, inspection tools, stacking) | `plans/images.md` (to create) | Images | MaxIm DL, Siril, DS9, AstroImageJ |
| Moving objects (astrometry, MPC) | `plans/astrometry.md` (to create) | Astrometry | astrometry.net, MPC ADES |
| Remote sensing | `plans/remote-sensing.md` (to create) | Remote sensing | SNAP, rasterio / GDAL |

## Decisions and open questions

- **Calibration — decided (owner, 2026-11-07):**
  - One engine.
  - The Photometry and Spectroscopy windows each start with a calibration step carrying the right defaults for
    their data. For spectra: no division by the flat; arcs taken bias / dark only.
  - **The step is optional**, because the data may have been calibrated elsewhere. Frames already calibrated (the
    header says so, or the user says so) are used as they are, and the program says which it took as calibrated.
  - A separate Calibration window stays for a night that mixes images and spectra.
- **Planning and Automation:** inside the main window, or in windows of their own like the rest? The owner has no
  wish either way; the interface plan proposes windows of their own, for one rule for all.

- **Spectroscopy, first item of `plans/spectroscopy.md` when it is created:** check that several exposures of one
  star in a night can be combined into one spectrum (IRAF `scombine`; today the echelle orders of one exposure are
  merged, but a combining step for several exposures was not found), and that the master bias ("Zero" in IRAF) is
  made and used the same way as for images.

## Agents

- agent1 (2026-11-07): wrote this file, `plans/interface.md` and `plans/photometry.md`.

## Template for a new area file

```markdown
# <Area>: plan

Read `PLAN.md` first, all of it.

(paste here the block "Most important rules" from PLAN.md, unchanged)

The rules that matter most here:
- (copy the ones from R1–R6 that apply, e.g. read the source of <programs> before each step; learn, never copy;
  real data <sources>; the workflow first; tooltips, undo, translations, guide; claim each step)

## Research notes
(what each reference program does and how, with the files and functions read; papers)

## What we already have
(do not redo)

## To ask the owner
(things that look unnecessary or need a decision; nothing is deleted before the owner's yes)

## Steps
(placed by urgency; new tasks found by research or tests are inserted where they belong)
### <n>. <title>
**open**  (or: **agentN claimed (date) — do not touch** / **agentN done (date, commit)**)
- Reference: …
- Ours now: …
- Build: …
- Accept: …
- Files: …

## Done
```
