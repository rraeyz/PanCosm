# Interface: plan

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

The rules that matter most here:

- **The workflow comes first.** An area window opens on what to do first, then next. There is never a wall of
  buttons. Rarely changed options are folded, and the right choice is already the default.
- **Research before building.** Look at how AstroImageJ, MaxIm DL and Siril lay out their windows, menus and
  toolbars, from screenshots, manuals and their source (AstroImageJ: `Astronomy/MultiPlot_.java`,
  `Astronomy/MultiAperture_.java`, `ij/` window classes). **Learn, never copy their code.**
- **The usual rules for every control:**
  - every control has a tooltip;
  - undo / redo where the user changes something;
  - every text in `self.tr`, translated into tr / de / es (0 unfinished);
  - engine messages have templates in `ui/messages.py`;
  - the guide is updated in 4 languages.
- **Fit the screen.**
  - Test 1366 × 768, 960 px and 800 px.
  - Test on Linux and Windows: Windows draws larger fonts.
- **Claim each step before starting it.** Write `**agentN claimed (date) — do not touch**`, push, and finish with
  `**agentN done (date, commit)**` (PLAN.md R2).
- **This file is used a lot.** Every new feature of any area is entered in the "Where everything is" table below:
  its window, menu, toolbar and panel.

## The design (agreed with the owner, 2026-11-07)

```
Main window                                      Area window (e.g. Photometry)
┌───────────────────────────────────┐            ┌───────────────────────────────────────────────┐
│ File  Settings  Window  Help      │            │ File Edit View Measure Analyse Window Help    │  menu bar
│ project · background tasks        │            │ [icon][icon][icon] …                          │  toolbar
│                                   │  click →   │ steps │        image / main view    │ panel   │
│ [Calibration] [Photometry]        │            │       │                             │         │
│ [Spectroscopy] [O−C] [Period]     │            ├───────┴─────────────────────────────┴─────────┤
│ [Models] [Planning] [Observing]   │            │ [tab][tab][tab] (pull out, move, remembered)  │  panels
│ [Automation] [Images] …           │            │ status: what is running, what is next         │  status bar
└───────────────────────────────────┘            └───────────────────────────────────────────────┘
```

- **The main window** is a menu of blocks, one per area, each with a short line saying what it does. It also holds
  the project, the settings, the list of background tasks and help.
- **Each area opens in its own window, like a program of its own.** Several can be open at once. Results still flow
  between them as today:
  - a timed minimum goes to O−C;
  - a light curve goes to Period and Models;
  - calibrated frames go to Photometry or Spectroscopy.
- **Each area window has:**
  - its own **menu bar**: File, Edit (undo / redo), View, the area's own menus, Window, Help — as MaxIm DL does;
  - a **toolbar of icons** under it for the frequent actions, as AstroImageJ does;
  - a **central view** (image, spectrum, diagram);
  - a **steps panel** that shows the workflow;
  - **dockable panels** that can be pulled out, tabbed, moved to a second monitor, remembered between sessions, and
    reset with "Reset layout";
  - a **status bar**.
- **Each area is free to add** menus, icons and panels of its own without crowding the others.
- **Calibration is an optional first step** in the Photometry and Spectroscopy windows, with the right defaults for
  their data (PLAN.md "Decisions"). Data calibrated elsewhere is used as it is, and the window says which frames
  it took as calibrated. A separate Calibration window stays for mixed nights.
- **Nothing in the engine changes.** The steps, projects and saved files stay as they are; only where the controls
  live changes.

## What exists now

- **One main window:** a sidebar of 13 pages (`MainWindow.PAGES`): start, plan, observe, calibrate, image,
  photometry, timeseries (light curve, period, O−C, frequency tabs), spectroscopy, orbits (models), remotesensing,
  automation, project, guide.
- **Menu bar:** File, Edit, View (overlays, "Panels beside the image"), Image (Process), Plugins, Settings
  (language, look, processing device), Help.
- **Pages beside the image:** `MainWindow.dock_page` can already show a page as a panel beside the image, and that
  panel can be dragged out as a window. This is the base to reuse for area windows.
- **Already built:**
  - Basic / Expert mode (folded sections);
  - collapsible numbered steps on the Photometry page (`Collapsible`, `_advance`);
  - `_Columns` (side-by-side columns that stack on a narrow window);
  - `StepGuide` (the workflow line at the top of a page).
- **Known limits:**
  - 800 px windows still overflow by 20–80 px on 4 pages;
  - the Photometry page is one column of steps beside the image, with Plot / Stars / Minimum / Export tabs below:
    too narrow for a measurements table, a multi-plot and the detrending (`plans/photometry.md` items 6–9).

## To ask the owner
(nothing yet)

## Steps
(placed by urgency; new tasks found by research or tests are inserted where they belong)

Language: the interface stays Qt through PySide6 (Python), which runs the same on every system we ship; heavy
drawing (very large images, thousands of plotted points) may move to OpenGL or native code if measured too slow
(PLAN.md rule 10).

### I1. Research: how the reference programs lay out their windows
**open** — partly done 2026-11-07 (AstroImageJ and MaxIm DL below); Siril, NINA and users' complaints still to do.

Found so far:
- **AstroImageJ** (source `astroj/AstroStackWindow.java`, `Astronomy/MultiPlot_.java`):
  - The image window has its own menu bar: File, Preferences, Scale, View, Annotate, Measure, Edit, Process,
    Color, Analyze, WCS.
  - Under the menu bar is a toolbar of toggles and actions: negative; region exclusion; bad-pixel map;
    annotations; sky rings; star names; counts on the image; centroid on / off; aperture settings; draw and clear
    apertures; clear table; run multi-aperture; align; plate solve; header; zoom in fast / in / out / fit; auto
    contrast.
  - RA and Dec of the cursor are shown beside the image; a slider walks the frames.
  - Multi-Plot is a window of its own with menus File, Preferences, Table, X-axis, Y-axis, Style, Auto Priors. It
    has Y-data rows (one row per plotted series, each with its own settings), a reference-star panel of checkboxes
    and a fit panel.
  - The measurements table is a window of its own, with a filter and coloured cells.
  - Every window remembers its place.
  - Users' usual complaint: too many windows and dialogs, settings scattered among them.
  - What to take: the per-window menus, the toolbar of toggles, the cursor read-out. What to avoid: a dozen
    floating windows; ours dock into one area window and can be pulled out only when wanted.
- **MaxIm DL** (manual):
  - Menu bar: File, Edit, View, Analyze, Process, Filter, Color, Plug-In, Window, Help.
  - Tool windows can be docked or floated: Information, Photometry, Observatory, Screen Stretch.
  - The Photometry tool is one window with tabs Select, Quality, Match, Identify, Graph: it follows the workflow
    left to right, which is the model for our steps panel.
- **Read:**
  - AstroImageJ: the main toolbar window, the image window with its toolbar, the Multi-Aperture and Multi-Plot
    windows, and the measurements table. Use screenshots, the user guide and the source.
  - MaxIm DL: the menu bar (File, Edit, View, Analyze, Process, Filter, Color, Plug-in, Window, Help), the toolbars,
    and the tool windows (Information, Photometry, Observatory).
  - Siril: the header bar, the left / right panels and the tabs.
  - NINA: the area tabs.
- **Write here:**
  - which menus each has;
  - what goes on the toolbar;
  - how windows are opened and arranged;
  - what users dislike in them (forum complaints).
- **Accept:** a short note per program, and a proposal of the menus and toolbar for each of our area windows,
  shown to the owner before I3.

### I2. The area window frame (shared by every area)
**open**
- **Shared parts every area window gets from the frame** (built once, not per area):
  - **Image view:** the existing `ImageViewer`, extended with:
    - zoom, pan and levels;
    - a cursor read-out (x, y, value, RA / Dec when solved);
    - a frame slider and blink;
    - overlay toggles on the toolbar (apertures, sky rings, names, counts, catalogue stars, VSX);
    - the measure tool.
  - **Plot view:** one plot component with:
    - zoom and pan;
    - several series with offsets, binning and residuals;
    - a click to drop or restore a point;
    - export to PNG / SVG / vector PDF and the numbers to CSV.
  - **Table view:** one table component with:
    - sorting, a column chooser and a filter;
    - coloured cells with the reason in the tooltip;
    - copy and CSV export;
    - a click on a row that tells the window to show that frame.
  - **Keyboard:** the same keys in every window (Ctrl+Z / Ctrl+Y, Ctrl+O, Ctrl+S, F1 for help on the current
    window, arrows for frames). Plus **a command search (Ctrl+K):** type a few letters to find any action of the
    window. This keeps the toolbar short without hiding anything.
  - **Files:**
    - recent files per area;
    - drag and drop onto any window;
    - **save and open a whole session of the area** (data chosen, stars, settings, plots), as AstroImageJ's
      "Save all".
  - **Night work:** a red night theme beside light and dark (it keeps the eyes dark-adapted at the telescope);
    high-DPI and second monitors; the font size can be changed.
  - **Long work:** progress and cancel in the status bar; a notice when a long task ends while the window is in the
    background.
- **Build** one class (`ui/area_window.py`): a top-level window with:
  - a menu bar built from what the area declares, plus the common File / Edit / Window / Help;
  - a toolbar;
  - a central widget;
  - a left steps dock;
  - dockable panels;
  - a status bar;
  - layout saved and restored per area (`QMainWindow.saveState` in the settings);
  - "Reset layout";
  - undo / redo wired to the area's undo stack.
- **Accept:**
  - an empty test area opens, a panel is pulled out, the window is closed and opened again, and the panel is back
    where it was;
  - Ctrl+K finds every action of the test window by name, in every interface language;
  - a saved session opens again with the same data, stars and plots;
  - the window fits 1366 × 768;
  - tests offscreen.

### I3. The main window as a menu of blocks
**open**
- **Also:** a "Continue where you left off" list (the last sessions of each area) at the top; the first-night
  tutorial reachable from here.
- **Build:**
  - the start page becomes the main window's content: one block per area, each with an icon, a name and one line
    of what it does;
  - the project, settings, background tasks and help stay;
  - a click opens or raises the area window;
  - "Window" menus in every window list the open area windows.
- **Accept:**
  - every block opens its area;
  - an open area is raised, not opened twice;
  - the main window fits 800 px.

### I4. Move each page into its area window, unchanged
**open**
- **Build:** one area at a time, in this order; each is its own commit:
  1. Photometry;
  2. Calibration;
  3. Light curves / Period / O−C (split into O−C and Period / frequency windows, or kept together: ask the owner);
  4. Spectroscopy;
  5. Models;
  6. Images;
  7. Planning;
  8. Observing;
  9. Automation;
  10. Remote sensing;
  11. Project / Guide (these may stay in the main window).
- Each page goes into its window as it is now. Its menus are moved from the main menu bar into the area's own
  menus: Image / Process goes to the Images window; the overlays go to the windows that show images.
- **Accept:**
  - every existing test passes, adjusted only where a test reaches a page through the main window;
  - every cross-area link still works (minimum → O−C, light curve → Period and Models, calibrated frames →
    Photometry / Spectroscopy, Plan → Observe sequence).

### I5. Photometry gets its full window
**open** — the first area to use the frame fully; details in `plans/photometry.md` item 0.
- **Build:**
  - the image in the middle;
  - the steps on the left;
  - Stars on the right;
  - Light curve / Frames / Minimum / Export tabs below, with room for Measurements table, Multi-plot and
    Detrend & fit;
  - a toolbar for: choose images, blink, previous / next frame, find bad frames, suggest comparisons, choose radii,
    measure;
  - menus: File, Edit, View, Measure, Analyse, Window, Help.
- **Accept:** on 1366 × 768 the image, the light curve and the star table are visible at once; every panel can be
  pulled out and comes back where it was.

### I6. The other areas get their full windows
**open** — one at a time, each planned in its own area file first (for example Spectroscopy: orders and spectrum in
the middle, lines and fit in panels).

### I6a. Test every window as a user (PLAN.md R3)
**open** — after I4 and again after each I5 / I6 window.
- **Build:** a driving script per window (QTest clicks, offscreen or Xvfb) that walks its workflow on real data
  and saves a screenshot of each step at 1366 × 768 and 1920 × 1080, in the four languages. A reviewer (the agent)
  looks at every screenshot as a newcomer would and writes each finding here as a task.
- **Accept:** the screenshots are attached to the step's notes (scratchpad paths); no finding left without a task.

### I7. Basic / Expert, guide, screenshots
**open**
- **Build:**
  - Basic / Expert decides which panels open by default in each area window;
  - the guide is rewritten around the area windows, in 4 languages, with new screenshots
    (`tools/guide_screenshots.py`).
- **Accept:** the guide's sections match the windows, in all 4 languages.

## Where everything is (keep this up to date)

Every feature the user sees, with its window, menu, toolbar and panel. Fill it in as I4 moves each page; add a row
whenever any area gains a feature.

| Feature | Window | Menu | Toolbar | Panel / tab |
| --- | --- | --- | --- | --- |
| Choose images, frame list, bad frames | Photometry | File | yes | Steps 1, Frames tab |
| Mark target / comparison / check stars, suggestions from Gaia | Photometry | Measure | yes | Steps 2, Stars |
| Radii from the star profiles and the aperture scan | Photometry | Measure | yes | Steps 3 |
| Measure the light curve, lost frames shown | Photometry | Measure | yes | Steps 4, Light curve |
| Field identification (Gaia solve, VSX, OBJECT check) | Photometry | Analyse | — | Steps 1 note |
| Minimum timing → O−C | Photometry | Analyse | — | Minimum tab |
| O−C diagram, ephemeris look-up (VSX) | O−C | — | — | — |
| (rows for every other page are added in I4) | | | | |

## Done
