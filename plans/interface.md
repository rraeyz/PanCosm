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
4. **Test as a real user, not only in code.**
   - Install the program on your machine, open it and use it as someone who knows less than you would.
   - Look for:
     - a button that works but is in the wrong place, or has no explanation;
     - a control that should not be there;
     - something missing;
     - a step a newcomer would not find.
   - Every problem found becomes a task (rule 5).
5. **Add the tasks you find.** Research, the internet, trials and tests all show work to do. Add it to the area
   file at the place its urgency deserves, not necessarily at the end. An area is finished only when it is
   excellent.
6. **Engine code may be changed** where it is wrong or missing, old core files included. New features may be
   added. **Never delete what looks unnecessary:** note it under "To ask the owner" and delete it only after the
   owner agrees.
7. **Time, memory, GPU.**
   - Measure the time and memory of what you build.
   - Never make the program slower to save memory.
   - Where the work suits a GPU, write a GPU path with a CPU fallback (the `compute` module: auto / cpu / gpu).
8. **Everything goes to `main`.** No branches and no pull requests for the owner to deal with.
9. **The workflow comes first.** No wall of buttons. The right default. Rarely used options folded.

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

### I1. Research: how the reference programs lay out their windows
**open**
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
  - the window fits 1366 × 768;
  - tests offscreen.

### I3. The main window as a menu of blocks
**open**
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
