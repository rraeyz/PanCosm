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
- **Menu bar:** File, Edit, View (overlays), Image (Process), Plugins, Settings
  (language, look, processing device), Help.
- **Pages beside the image:** removed at the owner's word (I6d (1)); every area has a window of its own.
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
(nothing open)

### Answered by the owner (2026-11-08)
The owner: "do what is sensible". Decisions, each to be done as a step (claim it first):
- **"Panels beside the image": remove it** (`MainWindow.dock_page`, `_Panel`, the hidden menu, their tests).
- **Comparison star in Turkish: "karşılaştırma yıldızı"** everywhere, interface and guide; check star:
  **"kontrol yıldızı"**. Replace every "mukayese yıldızı" (17 strings) and make the guide the same.
- **The main window's sidebar: remove it.** The area blocks and every window's Window menu are the ways in.
- **O−C gets its own window.** Light curves, Period and Frequency stay together in one window. Minima timed in
  Photometry still go to the O−C window by themselves.
- **The I1 proposal (menus and toolbar of each window): approved.** Change it where the user tests (I6a) show a
  better way.

## For the owner to try
- After I4: open every area from the main window on Windows and on CachyOS, and send a screenshot of any window that
  does not fit or looks wrong.

## Steps
(placed by urgency; new tasks found by research or tests are inserted where they belong)

Language: the interface stays Qt through PySide6 (Python), which runs the same on every system we ship; heavy
drawing (very large images, thousands of plotted points) may move to OpenGL or native code if measured too slow
(PLAN.md rule 10).

### I0. Split the big interface file before the work starts
**agent2 done (2026-11-07, commit 4765322)** — added 2026-11-07, so that several agents can work at once without overwriting one another.
- **Why:** Photometry, Calibrate, O−C, Period, Light curves, Project and Start all live in one file,
  `src/astrowb/ui/workspaces.py` (about 4 800 lines).
- **Build:** move each page class into its own module (`ui/photometry_page.py`, `ui/calibrate_page.py`,
  `ui/oc_page.py`, …), with the shared widgets (`Collapsible`, `StepGuide`, `_FoldButton`, `_Columns`, `_title`)
  in `ui/widgets.py`. Keep `from .workspaces import X` working for a while (re-exports).
- **Translations:** lupdate contexts are class names, so they survive the move; check that 0 strings became
  unfinished.
- **Accept:** all tests pass unchanged; `tools/i18n.py update` reports no new or lost string.
- **Result (agent2):** `widgets.py` (`_title`, `_FoldButton`, `Collapsible`, `StepGuide`, `_canvas_class`, `PlotCanvas`),
  `start_page.py`, `image_page.py`, `project_page.py`, `calibrate_page.py` (with `by_filter`), `photometry_page.py`
  (with `AavsoDialog`, `export_csv`, `_without_frames`), `oc_page.py` (with `_decimals`), `period_page.py` (with
  `fold_phase`, `fourier_edit`), `lightcurve_page.py`. `workspaces.py` only re-exports them (and `QFileDialog`, which
  `tests/test_surveys.py` patches through it). New code should import from the new modules. 2258 strings before and
  after, 0 unfinished; 729 tests passed.

### I1. Research: how the reference programs lay out their windows
**agent2 done (2026-11-07, commit 951150f)** — the proposal below waits for the owner's yes (asked 2026-11-07; see "To ask the owner"); I2 does not depend on it. — partly done 2026-11-07 (AstroImageJ and MaxIm DL below); Siril, NINA and users' complaints still to do.

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
- **Siril** (source read 2026-11-07, agent2: `src/gui-gtk4/uifiles/siril.ui`, `src/core/siril.h` enum `main_tabs`):
  - One window. A GTK header bar instead of a menu bar: Open, Recent, Save, and menu buttons Image processing,
    Tools, Scripts, a "hamburger" menu (preferences, help), the precision and snapshot buttons.
  - The image in the middle with Red / Green / Blue / RGB / mask tabs; a toolbar under the image (stretch mode
    Linear / Logarithm / Squared / Asinh, auto-stretch, histogram, undo / redo, selection, crop, mask); zoom, FWHM
    and the cursor read-out in the image's status line.
  - **The right panel is a notebook whose tabs follow the workflow, left to right:** Conversion, Sequence,
    Calibration, Registration, Plot, Stacking, Console (`main_tabs` FILE_CONVERSION … OUTPUT_LOGS). The panel can be
    hidden with a button (`button_paned`). Image-processing dialogs (curves, wavelets, background extraction…) are
    separate small windows opened from the header-bar menus.
  - What to take: the **workflow as tabs in order** (our steps panel), the toolbar of display actions under the
    image, undo / redo in the toolbar, a panel that hides with one click. What to avoid: menus hidden in a header
    bar (a newcomer does not find them; MaxIm DL's plain menu bar is clearer), and dozens of separate dialogs.
- **NINA** (source read: `NINA/MainWindow.xaml`, `NINA/View/*`, ARCHITECTURE.md):
  - One window. **A vertical tab strip on the left, one tab per area with a large icon and a short name:**
    Equipment, Sky Atlas, Framing, Flat Wizard, Sequencer, Imaging, Options; the strip collapses to icons only.
  - The Imaging tab is a **docking area** (AvalonDock, `DockManagerVM`): Camera, Telescope, Image, Histogram,
    Statistics, Autofocus chart, Plate solve, Sequence… are panels that the user drags, tabs, floats onto another
    monitor; the layout is saved and can be reset.
  - The sequencer is a tree of instructions dragged from a list (an "advanced sequencer"), with a simple
    target-list mode for newcomers.
  - What to take: the **area blocks with an icon and a name** (our main window), **dockable panels with a saved
    layout and a reset**, a simple mode beside the advanced one. What to avoid: everything in one window (the owner
    wants one window per area), and the long settings tree.
- **Users' complaints (searched 2026-11-07; little direct evidence was found, so weigh these lightly):**
  - Siril: a forum post says many found its GUI hard to approach and missed a tutorial
    (discuss.pixls.us/t/graphic-user-interface-ideas/23494); on a 4K laptop the header-bar menus came apart from the
    window (discuss.pixls.us/t/application-display-issue/30936). Lesson: plain menus that stay attached, high-DPI tested,
    a first-run tutorial.
  - NINA (bitbucket.org/Isbeorn/nina issues 833, 935, 1048, PR 187): users break their docked imaging layout and need
    "Reset layout"; they want the layout kept per profile and exported; auto-hidden panels were replaced by a side
    toolbar listing every panel to show / hide. Lesson: save the layout per area, always offer Reset layout, list all
    panels in View.
  - AstroImageJ: no forum thread on "too many windows" was found; an AAVSO post only says that measuring opens "a
    series of windows" (aavso.org/node/89786). The worry stays a design judgement, not a measured complaint.
  - MaxIm DL: not searched.

**Proposal for our area windows (for the owner, before I3):**

| Window | Menus (besides File, Edit, View, Window, Help) | Toolbar |
| --- | --- | --- |
| Photometry | Measure, Analyse | open images, blink, previous / next frame, bad frames, suggest comparisons, radii, measure, apertures on/off, zoom fit |
| Calibration | Frames, Masters | add folder, scan, calibrate, stack, show master |
| Spectroscopy | Reduce, Lines, Velocity | open, extract, identify lines, fit wavelengths, normalise, measure velocity |
| O−C | Ephemeris, Models | add minima, fit ephemeris, LTTE / apsidal fit, MCMC, export |
| Period / frequency | Search, Fold | open light curve, download, clean, search, prewhiten |
| Models | Fit | open light curve, starting values, fit, errors (MCMC), export |
| Images | Process, Analyse | open, levels, zoom, header, stack, blink |
| Planning | Targets, Night | add target, plan night, schedule, send to Observing |
| Observing | Devices, Sequence | connect, expose, focus, guide, run sequence |
| Automation | Pipeline | new, run, stop |
| Remote sensing | Bands, Analyse | open, index, classify, PCA |

Common to all: File (open, recent, save / open session, export, close window), Edit (undo / redo, preferences of the
area), View (panels on / off, reset layout, zoom, theme), Window (the open area windows, the main window), Help
(guide page of this window — F1, report a problem, about).
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
**split into I2.1–I2.7 below (agent2, 2026-11-07)**
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
  - **Screens:** high-DPI and second monitors; the font size can be changed. (No red night theme: the owner
    said no, 2026-11-08.)
  - **Long work:** progress and cancel in the status bar; a notice when a long task ends while the window is in the
    background.
  - **Report a problem (Help menu of every window):** one file with `error.log`, the version, the system, the
    settings and the last steps run, ready for the owner to send; nothing personal, the owner's data files not
    included.
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

**Sub-steps (agent2, 2026-11-07)** — I2 is too large for one commit; each part below is claimed and done on its own:

#### I2.1 The window itself
**agent2 done (2026-11-08, commit a44af97)** — screenshot check (tr, 1366 × 768): side panels first opened at
their smallest and cut their titles; fixed with first sizes (steps 280 px, right 340 px, bottom 220 px).
- `ui/area_window.py`, class `AreaWindow(QMainWindow)`: built from what the area declares — a stable key, a title, the
  central widget, an optional steps widget (left dock), panels (docks, each with a stable object name), the area's
  own menus and toolbar actions, and its undo stack.
- Common menus: File (Close window, Ctrl+W), Edit (Undo / Redo of the area's stack), View (every panel and the
  toolbar on / off, Reset layout), Window (the main window and every open area window), Help (this window's guide
  page, F1). The area's menus sit between View and Window.
- Status bar. The layout (`saveState`) and geometry are saved per area in the settings when the window closes and
  restored when it opens; Reset layout goes back to the layout the window was built with. The first size fits the
  screen (at most 1366 × 768 when the screen is that small).
- Accept: `tests/test_area_window.py` — a test area with two panels; a panel moved and the window closed and built
  again comes back where it was; Reset layout puts it back; Undo / Redo act on the stack; every panel is in View;
  fits 1366 × 768; every text translated.

#### I2.2 Command search (Ctrl+K)
**agent2 done (2026-11-08, commit 0695d4b)** — Edit → Find an action… (Ctrl+K); screenshot checked in Turkish. — a small popup with a filter box listing every action of the window (menus and toolbar) by its
translated text; Enter runs it. Accept: finds every action by a part of its name in each language.

#### I2.3 Recent files, drag and drop, area sessions
**agent2 done (2026-11-08, commit 2637029)** — frame side only (`open_files`, `file_filter`, `session=(get, set)`);
each area wires its own state when it moves into its window (I4). Projects are untouched by this step. — File → Open recent (per area), files dropped on the window go to the area, Save / Open session of the
area (`.astrosession` JSON of what the area declares: data chosen, stars, settings, plots). Accept: a saved session
opens again the same; old projects still open.

#### I2.4 Report a problem
**agent2 done (2026-11-08, commit 0db6664)** — `ui/report.py` + Help → Report a problem… in `AreaWindow`; the
main window gets the same action in I3. — Help → Report a problem: one zip with `error.log`, version, system, settings (no paths of the owner's
data files), the last steps run; a dialog says where it is and what to send. Accept: test that the zip has these
files and no data file.

#### I2.5 Text size
**agent2 done (2026-11-08, commits 9d0e646, this one)** — View → Larger / Smaller / Normal text (Ctrl+Shift++ / − / 0;
Ctrl++ stays the image zoom) in the main window and every area window, 7–18 pt, kept in the settings. A red night
theme was built in 9d0e646 and **removed at the owner's word ("kırmızı tema olmayacak", 2026-11-08)**; do not add
one again. A saved "night" setting falls back to dark.

#### I2.6 Shared plot and table views
**agent2 done (2026-11-08, commit 41f77b3)** — `ui/table_view.py` `DataTable`; `PlotCanvas` → Export data (CSV). Zoom,
pan and PNG / SVG / PDF were already in `PlotCanvas`. Changed (rule 12): series with offsets, binning, residuals and
click-to-drop are the multi-plot of `plans/photometry.md` item 8, built there on `PlotCanvas`, not twice. — one plot component (zoom, pan, series with offsets and binning, residuals, click to drop / restore a
point, export PNG / SVG / PDF and CSV) and one table component (sort, column chooser, filter, coloured cells with
the reason in the tooltip, copy, CSV, a row click tells the window which frame to show), reusing `PlotCanvas` and
the existing table menu. Accept: tests for export and the row signal.

#### I2.7 Long work in the status bar
**agent2 done (2026-11-08, commit 7f6729f)** — `AreaWindow.track(task)` / `task_update`; `MainWindow._on_task` routes updates. — the area's running tasks with progress and Cancel in its status bar; a notice when a task ends while the
window is in the background. Accept: test with a fake task.

### I3. The main window as a menu of blocks
**agent2 done (2026-11-08, commit a602bc3)** — `start_page.py` (`AREAS`, `areas()`, blocks, Continue list),
`MainWindow.open_area / recent_work / _resume / _fill_window_menu / report_problem`, `MainWindow.area_windows`
(empty until I4 fills it). Screenshots: tr 1366 × 768 and 1100 × 600, de and es 800 px; found and fixed on them:
names not standing out (now bold, text muted), German descriptions cut at 800 px, Basic / Expert overflowing at
800 px, the page taller than a 1100 × 600 window (blocks now two columns from 300 px each). The sidebar stays until
I4 has moved every page (see "To ask the owner").
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
**agent2 done (2026-11-08, commits 8ce39a3 … 0ae8ae0)**
- **Build:** one area at a time, in this order; each is its own commit:
  1. Photometry — **agent2 done (2026-11-08, commit 8ce39a3)**: `MainWindow.WINDOWED`, `_place_in_window`, `_help_for`;
     tests `test_photometry_lives_in_a_window_of_its_own`, `test_undo` adjusted to the area window;
  2. Calibration — **agent2 done (2026-11-08, commit 9692e26)**;
  3. Light curves / Period / O−C (split into O−C and Period / frequency windows, or kept together: ask the owner) —
     **agent2 done (2026-11-08, commit a0c0c7f)**, kept together with tabs until the owner answers;
  4. Spectroscopy — **agent2 done (2026-11-08, commit b41844e)**;
  5. Models — **agent2 done (2026-11-08, commit bf0546b)**;
  6. Images — **moved to the end (agent2, 2026-11-08, rule 12):** the main window's View (zoom, levels,
     stretch), Image / Process and overlay menus, the header table and "Panels beside the image" all work on the
     Images page's viewer; moving it means moving those menus into its window too. Done after 7–10 — **agent2 done (2026-11-08, commit 0ae8ae0)**;
  7. Planning;
  8. Observing;
  9. Automation;
  10. Remote sensing — 7–10 **agent2 done (2026-11-08, commit 9717ca2)**, one commit for the four (each only adds its
      key to `MainWindow.WINDOWED` and its steps' area);
  11. Project / Guide (these may stay in the main window) — **kept in the main window** (agent2, 2026-11-08): they
      are the main window's own pages (the project and the guide serve every area).
- Each page goes into its window as it is now. Its menus are moved from the main menu bar into the area's own
  menus: Image / Process goes to the Images window; the overlays go to the windows that show images.
- **Accept:**
  - every existing test passes, adjusted only where a test reaches a page through the main window;
  - every cross-area link still works (minimum → O−C, light curve → Period and Models, calibrated frames →
    Photometry / Spectroscopy, Plan → Observe sequence);
  - projects, settings and sessions saved by the previous version open (a test with files saved by v0.2.7).

### I4a. Findings of the first Photometry window screenshot (2026-11-08, agent2)
**agent2 done (2026-11-08, commit 16cf333)** for (1): `run_step(area=…)`; each later area passes its own key when it moves
(I4.2 …). (2) stays for I5.
- (1) The tasks a page starts (field identification, quality, measuring) are not shown in its area window's status
  bar: the window says "Ready" while "Identifying the field (Gaia, VSX)…" runs. Route them: the main window's
  methods that run a step for an area (`measure_light_curve`, the photometry quality / suggest / field steps, …)
  call `self.area_windows[key].track(task)` when the area has a window.
- (2) The frame table's FWHM / Sky columns are cut at 1366 × 768 (the right column is ~500 px): solved by I5's
  layout (frames as a bottom tab); until then the table scrolls sideways.
- Accept: (1) a test that a photometry step started from the window shows its progress there; (2) in I5.

### I4c. Spectroscopy window: the "In what order?" box (found 2026-11-08, agent2)
**agent2 done (2026-11-08, commit f4191c1)** — folded in every mode in the Spectroscopy window; its text is in the job buttons' tooltips (`plans/spectroscopy.md` 1.1 / 1.4); whether it goes is for the owner. Finding: on the Spectroscopy window at 960 × 700 (es) the "In what order? (click)" box above the tabs is open in
Basic mode and takes a quarter of the height, while each tab already has its own Workflow line saying the same.
Decide when the Spectroscopy window gets its full layout (I6, `plans/spectroscopy.md`): fold it by default, or move
its text into the window's Help / the steps panel. Nothing is removed before that decision.

### I4d. Automation and Observing windows: findings of their first screenshots (2026-11-08, agent2)
**agent2 done (2026-11-08, commit a612314)** — step names (`ui/step_names.py`) everywhere a step is shown; the English
template texts were only the screenshot script (no language saved), but the window now follows the interface language
when none was chosen. The parameter labels followed in I6b (5).
- Automation (tr): the templates' names and descriptions stay English ("Eclipsing binary night (şablon)",
  "Observe the binary from dusk to dawn…"), and the steps are listed by their technical ids ("1. calibration.scan",
  "photometry.suggest_comparisons") and setting keys ("← folder", "clock_utc_offset"). Show translated step names
  and setting labels (the ids in the tooltip); translate the bundled templates' texts.
- Observing (tr, 1366 × 768): the sequence table's columns are cut on the right (Gain, Offset, Readout mode, …).
  (2026-11-08, agent2: the table scrolls sideways, so nothing is lost; left for the Observing window's layout in
  I6, where the sequence gets a panel of its own.)
- Accept: screenshots in four languages show no English text in Automation and no cut column header in Observing.

### I4b. "page" → "window" in every text, once all areas are in windows
**agent2 done (2026-11-08, commit cc0a34c)** for the interface strings (35, four languages). The guide's ~45 "page"
wordings per language move to I7, which rewrites the guide around the windows anyway (rule 12: not twice). — found 2026-11-08 (agent2) on the Calibration window screenshot: its button still says "4. Measure them on
the Photometry page →", and 25 interface strings (plus the guide in four languages) call the moved areas
"pages" ("the Calibrate page", "the Photometry page"…). After I4 has moved every area, change them all at once to
"window" (en, tr, de, es; guide sections; the hints of the Workflow lines), keeping each button's name in the hints
identical to the button. Accept: `grep "Photometry page\|Calibrate page"` finds nothing user-visible; 0
unfinished translations.

### I5. Photometry gets its full window
**agent2 done (2026-11-08, commit 790b52b)** — first layout: the image is the central view, the steps scroll is the left
panel, the results (plot + Stars / Plot / Minimum / Export tabs) the bottom panel (shown once a star is marked),
toolbar with short labels mirroring the page's buttons (enabled with them), menu Measure. `PhotometryPage.window_parts`,
`MainWindow._photometry_window`, `_follow_enabled`. Screenshots tr / de 1366 × 768 with 15 Qatar-1 frames and two
stars: image, steps, light-curve plot and star table visible at once; toolbar fits. Still to do (found on them):
the frame table's FWHM / Sky columns cut (the frames table belongs in a bottom tab, `plans/photometry.md` item 6);
a Measurements table, multi-plot and detrend & fit as their own panels (photometry items 6–9). — the first area to use the frame fully; details in `plans/photometry.md` item 0.
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
- Spectroscopy: planned in `plans/spectroscopy.md` step 1 (2026-11-08, agent2: iSpec, PypeIt and IRAF read for the
  layout). It also closes I4c.

### I6a. Test every window as a user (PLAN.md R3)
**agent2 done (2026-11-08, commit c046329)** — first pass after I4 / I5; run it again after each I6 window. Script
`i6a_drive.py <out> <lang> <W> <H>` (scratchpad): main → Calibration (LCO raw lights + darks + biases, sky flat; scan)
→ Photometry (15 Qatar-1 frames: bad frames, target, radii, measure) → Light curves (period search, O−C) →
Spectroscopy (EFOSC2 science + arc, velocity tab) → Models → Images → Planning → Observing → Automation → Remote
sensing; tr / en / de / es at 1366 × 768 and 1920 × 1080 (scratchpad `i6a/<lang>_<W>/`, contact sheets
`i6a/de_sheet0-4.png`). Its text check (`cut.txt`: size hint wider than the widget) found only the Workflow fold
titles, which elide on purpose with the whole text in the tooltip; it does not look at table headers. The whole
night worked in every language (15 points, scatter 0.44 %). German grammar fixed in commit c046329 ("Im Fenster
Photometrie messen", "An das Fenster Beobachten senden"). Findings, each a task in I6b.
- **Build:** a driving script per window (QTest clicks, offscreen or Xvfb) that walks its workflow on real data
  and saves a screenshot of each step at 1366 × 768 and 1920 × 1080, in the four languages. A reviewer (the agent)
  looks at every screenshot as a newcomer would and writes each finding here as a task.
- **Accept:** the screenshots are attached to the step's notes (scratchpad paths); no finding left without a task.

### I6b. Findings of the I6a run (2026-11-08, agent2)
**agent2 done (2026-11-08)** — every sub-item done (commits in each); left open inside them: a significance test for the period search (3), naming the rarer steps' settings (5), sessions and drops for Planning, Observing, Models, Automation (8).
- **(1) Photometry / Images: catalogue labels hide the image.** **agent2 done (2026-11-08, commit 96d65be)** — the labels were the 40
  VSX variables (VSX lists Gaia DR3 variables by their Gaia names). Photometry names only the one chosen in the
  variables list; the other cyan rings give their name on hover (`viewer.set_markers` style "quiet"). Images: an
  overlay of more than 25 rings (`ImageViewer.MAX_LABELS`) shows each label on hover, and the status line says so.
  No View toggle: not needed once the image is readable. Also from this screenshot: the radii text under the plot
  now scrolls past four lines (it had squeezed the plot after (2)). Screenshots: scratchpad
  `i6b1/<lang>/22_phot_target_and_comparisons.png`. Original finding: After the field identification every Gaia / VSX star
  gets a full label ("Gaia DR3 2244…"); on the Qatar-1 field they cover the stars and the target. Show only the
  target, comparisons, checks and VSX variables by name; other catalogue stars as small marks, their name on hover;
  a View toggle "Catalogue names". Accept: on the Qatar-1 screenshot (1366 × 768) every marked star is readable.
- **(2) Photometry: the star table is squeezed in the results panel.** **agent2 done (2026-11-08, commit c35decb)** — the paragraph under the table went into the
  two buttons' tooltips (its old area names fixed: "Light curves & O−C", "Orbits & models"), the result text sits
  under the plot, the buttons share a row when it holds them, plot and tabs share the width, every header column
  fits, and the panel opens at two fifths of the height. At 1366 × 768 (tr / de / es) the table shows 4 stars at
  once (target + 3 comparisons), the rest scroll — not the 5 asked: a fifth row would cost the image more height.
  Cost: the plot toolbar's "Open in a new window" moved into its » overflow in Spanish. Screenshots: scratchpad
  `i6b2/<lang>/24_phot_light_curve.png`. Also "this page" → "this window" in the Undo tooltip and the Models hint.
  Original finding: The long info text above it leaves the Stars
  tab about one row at 1366 × 768. Put the text in a one-line label with the rest in its tooltip (or below the
  table), so target + comparisons + check (at least 5 rows) are visible. Accept: screenshot shows 5 rows.
- **(3) Light curves: period search answers without a warning when the data cannot hold the period.** **agent2 done (2026-11-08, commit 23c0b7d)** — `photometry.steps.period_warnings`, shown as ⚠ lines under
  the result (templates in `ui/messages.py`, guide 07 in four languages); the Qatar-1 8-minute curve now says it
  cannot hold a period (scratchpad `i6b3/tr/31_lc_period_searched.png`). Left open: a significance test (false-alarm
  probability) for a peak that is only noise — a 9-day sine over 3 nights searched to 1.4 d gives a noise peak at
  0.19 d with no edge to warn of; and `period._refine` can step outside a grid of 2 trials (best 0.0135 d for a range
  starting at 0.05 d). Original finding: 15 points over
  8 minutes gave "best period 0.013535 d" with a periodogram rising to the edge of the grid. Warn (PLAN.md R5) when
  the time span is shorter than ~2 × the longest period searched, or when the peak is at the grid's edge, and say
  what to do (more nights, a narrower range). Template in `ui/messages.py`. Accept: a test with a 8-minute curve
  shows the warning; a 3-night curve does not.
- **(4) Observing: sequence table headers cut** **agent2 done (2026-11-08, commit 23b9182)** — columns sized to their
  contents and headers, the table scrolls sideways when narrow (`test_every_sequence_column_shows_its_whole_header`).
  The I6a script now checks table headers too: none cut in de / tr at 1366 × 768 (scratchpad `i6b4/`). Original: in German at 1366 × 768 ("elichtung (", "stärkung (G",
  "uslesemod…"). Short header names with the full name in the header tooltip, or columns sized to their headers
  with the table scrolling sideways. Folded into the Observing window's I6 layout. The I6a text check should look
  at table headers too.
- **(5) Automation: template names cut** **agent2 done (2026-11-08, commit 3e82077)** — `ui/setting_names.py`:
  names for the 82 settings and inputs of the steps in the bundled templates (four languages; a few keyed by step,
  where one key means different things), the key in the tooltip; any other setting shows its key with spaces (the
  remaining ~95 keys of rarer steps can be named the same way when their windows get their I6 layout). The template
  list word-wraps. Screenshot scratchpad `i6b5/de.png`. I4d's open leftover is closed by this. in the template list ("…am Ende der Nacht (Vorlag") with a sideways
  scroll bar, and the settings table shows parameter keys ("← folder", "lights", "clock_utc_offset") — the I4d
  leftover. Labels for the parameters (key in the tooltip); the list word-wraps or gets the room.
- **(6) Remote sensing: empty view gives no hint.** **agent2 done (2026-11-08, commit a99e75a)** — `ImageViewer.empty_hint`,
  drawn in the middle of an empty view: Remote sensing, Images ("File → Open FITS…") and Photometry; screenshots
  scratchpad `i6b6/both.png`. Images did not have one either (the finding was wrong there). Found on the way, now
  (8) below: no window is given `open_files`, so dropping files on a window and its File → Open… / Open recent do
  nothing yet. The plot toolbar in the middle of the empty Remote sensing column stays for its I6 layout.
  Original finding: The window opens on a large black view with no text; show
  "Open an image (File → Open, or drop it here)" until one is loaded, as Images does. The plot toolbar floats in
  the middle of the steps column with empty space below.
- (7) Spectroscopy "In what order?" box: already I4c. Calibration, Models, Images, Planning: nothing new.
- **(8) Dropping files on a window does nothing** **agent2 done (2026-11-08, commit cb7a002)** — `MainWindow._opener`
  gives Images (`open_many`), Calibration (the lights folder), Light curves (`PeriodPage._load(path)`),
  Spectroscopy (the science frame) and Remote sensing their handler, Photometry `set_images`; so each has File →
  Open… (Ctrl+O), Open recent and drop. The Images window no longer also gets the main window's Open FITS…: one
  Ctrl+O. The empty-view hints say "or drop … here"; guide 05 in four languages. Test
  `test_files_dropped_on_an_area_window_open_there`. Planning, Observing, Models, Automation open no file yet;
  sessions (Save / Open session) are still wired to no area. (found 2026-11-08 by agent2 during (6)). I2.3 built open / recent
  / drop / sessions into `AreaWindow`, but `MainWindow` gives no window an `open_files` handler, so drops are
  refused and the File menu has no Open… or Open recent (only the test uses them). Wire each area: Images →
  `open_many` (its File menu already has Open FITS… on Ctrl+O from the main window: one Open, not two), Photometry
  → `set_images`, Calibration → the lights folder, Light curves → Load CSV, Spectroscopy → the science file, Remote
  sensing → its open. Accept: a test per area drops a file and the area shows it; one Ctrl+O per window.

### I6d. The owner's answers of 2026-11-08, as steps (PLAN.md "Order of work" 1, first)
**agent2 done (2026-11-08)** — all four (commits in each). Written 2026-11-08 (agent2) from "Answered by the owner" above; each sub-step is claimed on its own.
- **(1) Remove "Panels beside the image".** **agent2 done (2026-11-08, commit 2790dde)** — removed `_Panel`, `dock_page`, `_fill_panels_menu`, the sidebar's right-click "Show beside the image" (it served only this), View → "Panels beside the image" and the "ui.panels" reading; guide 05 line gone in four languages; `test_settings_naming_old_side_panels_still_open`. Original: `MainWindow.dock_page`, `_Panel`, `_fill_panels_menu`,
  the hidden View → "Panels beside the image" menu and the menu items that call `dock_page`, with their tests
  (`tests/test_ui.py`). Accept: no `dock_page` / `_Panel` left; old settings that name docked panels still open (a
  test).
- **(2) "karşılaştırma yıldızı" and "kontrol yıldızı" in Turkish.** **agent2 done (2026-11-08, commit aa965bf)** — 28 interface strings and 14 guide lines (01, 05, 06, 13), suffixes in vowel harmony (karşılaştırmanın, -ya, -lar); "Denetim yıldızları" → "Kontrol yıldızları"; no "mukayese" left. Original: — every "mukayese" in `app_tr.ts` (27
  lines) and in the Turkish guide (01, 05, 06, 13) becomes "karşılaştırma"; check star "kontrol yıldızı". Accept:
  `grep -i mukayese` finds nothing in the Turkish texts; 0 unfinished.
- **(3) Remove the main window's sidebar.** **agent2 done (2026-11-08, commit 8af4e20)** — `MainWindow.nav`, its group headings and the splitter are gone; the page stack is the central widget (Start, Project, Guide), and the main window's Window menu lists those three pages before the areas. The tour points at the area blocks (one sentence reworded; the rest is I7). Guide: every "or the sidebar" became the Window menu, and 01's sidebar bullet describes the blocks, in four languages. Screenshots scratchpad `i6d3/main_1366.png`, `main_800.png`. Original: `MainWindow.nav` and what only it uses (the old page stack
  for areas that all live in windows now); the area blocks and every window's Window menu stay the ways in. Accept:
  every area opens from its block and from Window; the main window at 1366 × 768 and 800 px shows the blocks
  without a sidebar; old settings still open.
- **(4) O−C in its own window.** **agent2 done (2026-11-08, commit c132465)** — new area key `oc` (`MainWindow.oc_page`, `_make_oc_page`, its block "O−C" on the Start page, File → Open… loads a minima file); Light curves is now "Light curves and period" with Period search, Frequency analysis and Variable star search. Minima timed in Photometry still go to O−C by themselves (silently, as before); "Send maxima to the O−C diagram" also opens the O−C window. The Photometry button became "Period search →" (its tooltip says where minima go). Guide 06 and 07 updated in four languages (07 opens with the two windows; its O−C section names the window). Screenshot scratchpad `i6d4/both.png`. Original: the O−C tab of Light curves becomes the area window "O−C" (its own
  block on the main window); Light curves keeps Period, Frequency and Variable star search. Minima timed in
  Photometry go to the O−C window by themselves, as they went to the tab. Accept: a minimum timed in Photometry
  appears in the O−C window; the guide (07) splits into its two windows in four languages.

### I6c. Icon toolbars and the full menu bars, as the owner asked
**agent2 done (2026-11-08): I6c.1–I6c.11 all done** — split into I6c.1–I6c.11 below (agent2, 2026-11-08) — added 2026-11-08 (agent1, from the owner's question). Part of the interface's remaining work (PLAN.md
"Order of work" 1), before photometry.
- **The owner's wish:**
  - every area window as AstroImageJ: a row of **small icons** for the frequent actions under the menu bar;
  - as MaxIm DL: a **menu bar with the area's own menus** (Process, Analyse, …) besides File, Edit, View, Window,
    Help.
- **Ours now (read 2026-11-08):** the toolbars of Photometry and Spectroscopy show **text buttons**
  (`setToolButtonStyle(Qt.ToolButtonTextOnly)` in `MainWindow._photometry_window` and `_spectroscopy_window`).
  Photometry has only a **Measure** menu; the I1 proposal (approved by the owner) also has **Analyse**. The other
  windows have the common menus only, so their actions are still buttons inside the page.
- **Build:**
  1. **An icon for every toolbar action**, the same icon in every window for the same kind of action (open, blink,
     previous / next, measure, fit, export…). Use Qt's standard icons where they fit, and small drawn icons
     otherwise. Images already does this (`_glyph` in `_fill_image_toolbar`). Each icon has its tooltip; View →
     "Toolbar text" shows the labels beside the icons for those who want them.
  2. **The full menu bar of each area window.** Checked 2026-11-08 (agent1) against every button of every page and
     against the menus of AstroImageJ's image window and MaxIm DL. The approved I1 table named only one or two
     menus per window; the windows hold far more. These menus put every existing action in a menu, in the order of
     the workflow. Items marked *(new: …)* come with the plan items named.

     **Common to every area window:**
     - **File:** the area's Open…, Open recent, Open session… / Save session…, the area's Export items, Close
       window.
     - **Edit:** Undo, Redo, Copy, Find an action… (Ctrl+K), Settings… (language, look, processing device — the same
       settings as the main window).
     - **View:**
       - each panel on / off, Reset layout;
       - Toolbar text, Larger / Smaller / Normal text;
       - in windows with an image: zoom in / out / fit, levels and colours, overlays.
     - **Window:** the main window, then every other area.
     - **Help:** Guide for this window (F1), Tour, Report a problem…, Check for updates, About.

     **Per window** (besides the common menus):

     | Window | Menus and their items |
     | --- | --- |
     | Photometry | **Frames:** Choose images…, Live: follow a folder…, Blink, Previous / Next frame, Find the bad frames, Leave out the bad frames, Restore deleted points. **Stars:** Suggest comparison stars, Make a variable the target, Mark check stars, Clear stars, Open / Save star list *(new: item 7)*, Find the best comparison set *(new: 9a)*, Comparison-star rules… *(new: 17)*. **Measure:** Choose the radii from the star profiles, Aperture and sky settings… *(new: 2, 3, 5, 22)*, Measure light curve, PSF photometry, Standard magnitudes (APASS / Gaia), Polarimetry, Measure between two stars *(new: 24)*. **Analyse:** Detrend / Undo detrending, Choose the detrending (BIC) *(new: 9)*, Time of minimum, Fit an eclipse or transit model →, Period search and O−C →, Nearby eclipsing binary check *(new: 23)*, Identify the field (Gaia, VSX). **File → Export:** CSV, AAVSO report, measurements table *(new: 6)*, ETD *(new: 15)*. |
     | Calibration | **Frames:** Lights folder…, Add folder…, Scan, Remove from the list, Change the type, Clear. **Masters:** Make masters, Show master bias / dark / flat, options (overscan, cosmic rays, dark scaling, hot pixels, linearity, colour camera, spectra). **Process:** Calibrate, Stack into one deep picture, Align, Drizzle, RGB combine. **Send:** to Photometry, to Spectroscopy. |
     | Spectroscopy | **Reduce:** long slit (trace, sky, extract), echelle (find orders on the flat, extract orders, merge), IFU cube (load, show image). **Lines:** identify arc lines, lines from a reference arc / IRAF database, fit wavelengths, refit without the left-out lines, use all lines again. **Spectrum:** normalise (automatic / through points), smooth, resample, combine exposures, instrument response and divide by it, telluric correction, arithmetic with spectrum B. **Measure:** lines (EW, FWHM, V/R), in several spectra, Teff / log g / [Fe/H] / v sin i, spectral type. **Velocity:** measure radial velocities (CCF, TODCOR, broadening function), separate the two stars (disentangling), fit the orbit. **File → Export:** spectrum, BeSS / ARAS. |
     | Light curves / Period / Frequency | **File:** load a light curve (CSV, AAVSO, ZTF, ASAS-SN…), download (TESS, Kepler, ZTF), save. **Data:** delete points by clicking, remove outliers, bin in time, flux ↔ magnitude, undo edits. **Search:** period search (Lomb–Scargle, BLS, PDM, ANOVA), frequency analysis with prewhitening, variable stars in a set of frames. **Fold:** fold on the period, phase plot. **Send:** maxima to O−C, a star to Period search, to Models. |
     | O−C | **File:** load minima…, export results (CSV / LaTeX). **Ephemeris:** look up (VSX), fit linear / quadratic, draw O−C. **Models:** third body (light-time effect), apsidal motion, MCMC errors. |
     | Models | **File:** open a light curve, compare with a model curve. **Fit:** fit the binary model, posterior (MCMC), absolute dimensions. **Export:** PHOEBE, Wilson–Devinney, ExoClock / ETD. **Visual orbit:** load measures, fit the orbit. |
     | Images | **File:** open, save a copy with header changes, save as / convert, export data (CSV). **Edit:** header (edit, copy). **Process:** the 16 image operations of today's Image → Process menu. **Analyse:** pixel / aperture / area counts, line / row / column profile, histogram, radial profile, surface, ruler, FWHM / HFD, measure between two stars. **Catalogues** (AstroImageJ's Annotate): Gaia, VSX, grid, labels, the other overlays. **Astrometry** (AstroImageJ's WCS): plate solve, moving-object astrometry, MPC report. **Colour:** RGB combine, debayer, split channels. **Stack:** stack, drizzle, blink. |
     | Planning | **Targets:** add, add with ephemeris, look up, remove selected. **Night:** plan the night, visibility chart, make a schedule, exposure time…. **Send:** to Observing. |
     | Observing | **Devices:** set up observatory…, connect, start the observatory on this computer…. **Telescope:** slew, centre, polar alignment, park. **Camera:** expose, cooler, filter. **Focus.** **Flats:** sky flats, panel flats. **Sequence:** add / remove row, start, abort, resume, clear the night plan. |
     | Automation | **Pipeline:** new, from a template, add step, run, stop, save as. **Send:** to Observing. |
     | Remote sensing | **File:** open image (GeoTIFF, FITS, JPEG2000, NetCDF, HDF5). **Bands:** band indices (NDVI…), compute. **Analyse:** classify (k-means), principal components. **File → Export.** |
     | Main window | **File:** new / open project, open a FITS image, recent. **Settings:** language, look, processing device. **Plugins.** **Help.** |

     - **Plugins:** a plugin's action appears in the menu of the window it belongs to; the main window keeps the
       full list.
     - Every action of a page's buttons is also in a menu. A button may stay in its step when the workflow needs it
       there.
     - Names and order are checked in the I6a user walk; change them where users get lost.
  3. **Each window's toolbar,** as in the I1 table.
- **Accept:**
  - every area window shows an icon row and its own menus;
  - every icon has a tooltip;
  - Ctrl+K finds every menu action;
  - the I6a walk (four languages, 1366 × 768) shows no cut toolbar;
  - the same icon is never used for two different actions.

**Sub-steps (agent2, 2026-11-08)** — too large for one commit (rule 13); each claimed and done on its own:
- **I6c.1 One icon set, icon toolbars.** **agent2 done (2026-11-08, commit 283bc69)** — `ui/icons.py` (`ICONS`, `icon`), `AreaWindow.set_icons` (icons painted again on a palette change), View → Toolbar text (`ui.toolbar_text`); Photometry (its ◀ ▶ actions now named Previous / Next frame), Spectroscopy (one icon per job) and Images use the table. A symbol that the font drew as a coloured emoji (♒) was replaced. Guide 01 in four languages (also the Light curves / O−C block names left from I6d (4)). Screenshot scratchpad `i6c1/all.png`; `test_one_icon_set_and_icon_toolbars`. Original: `ui/icons.py`: one table
  kind → icon (Qt standard icons for open / save, font symbols drawn in the theme's text colour otherwise, as
  Images does today), the same kind always the same icon and no icon for two kinds (a test). `AreaWindow` shows its
  toolbar as icons with tooltips, View → "Toolbar text" adds the labels (kept in the settings), icons follow a
  theme change. Photometry, Spectroscopy and Images use the table.
- **I6c.2 The common menus complete in every area window:** **agent2 done (2026-11-08, commit 96a87c7)** — `MainWindow._complete_menus` adds to every area window Edit → Copy (a table's selected cells, or the text box's own copy) and the main window's Settings menu itself, and to Help the tour, Check for updates… and About (the main window's actions: they act the same everywhere). Windows built before the main window's menus are completed right after them. Guide 01 in four languages; `test_every_area_window_has_the_common_menus`. Original: Edit → Copy, Settings…; Help → Tour, Check for updates,
  About.
- **I6c.3 Photometry:** **agent2 done (2026-11-08, commit bbc0a23)** — menus Frames, Stars, Measure, Analyse and File → Export built from the page's own buttons and check boxes (`mirror` in `_photometry_window`: the button's text in the menu, the short name as the toolbar's icon text, enabled and checked as the widget); Stars → Mark check stars sets the click role. "Identify the field" is not a menu item: it runs by itself when the images are chosen (rule 12). The new items of later photometry steps (star lists, best comparison set, measurements table…) join these menus when they are built. Guide 06 in four languages; `test_photometry_window_menus_mirror_its_buttons`. Original: Frames, Stars, Measure, Analyse, File → Export, as in the table; toolbar.
- **I6c.4 Calibration:** **agent2 done (2026-11-08, commit 4f81973)** — `AreaWindow.add_menus` (menus and toolbar added after the window is built), `MainWindow._calibrate_menus` (called from `_place_in_window` by key), `_mirror` now module-level; icon kinds scan, calibrate, stack, send. Frames, Masters (the option check boxes), Process (Calibrate, Stack, Drizzle) and Send (to Photometry). Not in the program yet, so not in the menus: Show master bias / dark / flat, Send to Spectroscopy, Align and RGB combine (RGB lives in Images); the frame type is changed in the table row. Guide 04 in four languages; `test_calibration_window_menus_and_toolbar`. Original: Frames, Masters, Process, Send; toolbar.
- **I6c.5 Spectroscopy:** **agent2 done (2026-11-08, commit 5163f54)** — `MainWindow._spectroscopy_menus`: Reduce, Lines, Spectrum, Measure, Velocity and File → Export from the jobs' buttons (now attributes); each item shows its job first; Refit and Use all lines again act on the long-slit or échelle job, whichever is shown. The toolbar stays the six job buttons (I6c.1): the jobs' frequent actions differ too much for one row; a row per job is a candidate for the I6c.11 walk. Guide 08 in four languages; `test_spectroscopy_window_menus`. Original: Reduce, Lines, Spectrum, Measure, Velocity, File → Export; toolbar per job.
- **I6c.6 Light curves and O−C:** **agent2 done (2026-11-08, commit 3abd85b)** — `_timeseries_menus` (Data, Search, Send, File → Light curve; toolbar load, download, save, period search, frequencies, variable search) and `_oc_menus` (Ephemeris, Models with the four models in one exclusive group as the radio buttons, File → Export; toolbar load, look up, fit, export). Loading stays File → Open… (Ctrl+O, I6d (4)); a second Load item was taken out of both File menus. Compared with Period04 (File, Fourier, Fit menus): the same split of data, search and fit. Not built (no such action yet): Fold → fold on the period (the fold is drawn after each search), Send → to Models. Guide 07 in four languages; `test_light_curves_and_oc_window_menus`. Original: their menus and toolbars.
- **I6c.7 Models.** **agent2 done (2026-11-08, commit c46718c)** — `_orbits_menus`: Fit (fit, posterior, MCMC, absolute dimensions), Visual orbit (load measures, fit the orbit); File → Open… now chooses the light curve (an `_opener` for Models, so drops work too), File → Compare with a model curve… and File → Export (results, PHOEBE, WD, ExoClock / ETD). Changed from the table (rule 12): Export sits in File as in every other window, not as a menu of its own. Guide 09 in four languages; `test_models_window_menus`.
- **I6c.8 Images:** **agent2 done (2026-11-08, commit 66e1ff4)** — `MainWindow._fill_image_menus`: File (Open…, Open recent, Save FITS as…, Save a copy with these header changes…, Save picture, Convert many images, Export data (CSV)…, Close image, Close all images — the window had no way to close an image before), Edit (Add or change keyword…, Delete keyword, Copy the header), View (zoom, previous / next, levels, interval, stretch), Process (top level, was Image → Process), Analyse (the Move / Star / Area / Line tools as a checkable group, Whole image, Photometric coefficients), Overlays, Astrometry (Plate solve, Asteroid and comet astrometry), Colour (Colour image from three filters, **new:** Split into colour channels (R, G, B) — `bayer.split`, as calibration does), Stack (**new:** Stack / Drizzle the open images with the steps' defaults, as MaxIm DL's Combine; Blink). The Image menu is gone. Changed from the table (rule 12): the Catalogues menu keeps its name **Overlays**: contours, the finder chart and DS9 regions are not catalogues, and the guide already used it; debayering by interpolation is not added — the superpixel split keeps the pixels' true values, which photometry needs (an interpolated debayer is for pictures, and raw pictures already open in colour-to-brightness). German Process was "Bearbeiten", the same word as Edit: now "Verarbeiten". Guide 05 (and the references in 04, 06) in four languages; the quick tour no longer names the Image menu; `test_image_window_menus`. Found on the way (screenshots in four languages, scratchpad `i6c8/all.png`): the Overlays menu and every text of its dialogs had never been translated — lupdate filed them under the variable name `win`, which Qt never looks up — now `QCoreApplication.translate("Overlays", …)`, as was O−C's "Cannot fit" message; a test now rejects any such context. The Process and Overlays toolbar buttons are buttons of their own, so their icons do not replace the menus' names in the menu bar. Original: today's menus arranged as the table (Analyse, Catalogues, Astrometry, Colour, Stack).
- **I6c.9 Planning and Observing.** **agent2 done (2026-11-08, commit 30aab08)** — `_plan_menus`: Targets (Add target, Add target with ephemeris, Remove selected), Night (Plan the night, Exposure time…, Make a schedule, Send to the Observing window); `_observe_menus` (N.I.N.A. / MaxIm DL grouping): Devices (Set up observatory…, Connect, Start observatory on this computer…), Telescope (Slew, Centre, Polar alignment, Park), Camera (Take preview, Cool the camera, Cooler off, Change the filter), Focus (Autofocus, Move the focuser), Flats (Sky flats, Panel flats), Sequence (Add / Remove exposure row, Start sequence, Abort, Resume, Clear the night plan). Icon toolbars: Planning add / ephemeris / plan / exposure / schedule / send; Observing connect / slew / centre / park / preview / autofocus / start / abort. The Observing page's buttons are `ObservePage.buttons` by name. Changed from the table (rule 12): Planning's Send is the last item of Night (a menu of one item otherwise), as Make a schedule leads to it; Abort and Resume sit in Sequence (they act on the running sequence first). Guides 02 and 03 in four languages; `test_planning_and_observing_window_menus`; screenshots scratchpad `i6c9/all.png` (the preview icon looked like a radio button in the menu and was changed).
- **I6c.10 Automation and Remote sensing.** **agent2 done (2026-11-08, commit 594fe89)** — `_automation_menus`: File → New automation, Save the automation as…; Steps (Add step, Remove the step, Move the step up / down); Run (Run the automation, Send sequence to the Observing window, Process after the sequence); toolbar new / save / add step / run / to Observing. `_remotesensing_menus`: Analyse (Compute the band formula, Classify (k-means), Principal components); File → Open… already opens the bands (I6b); toolbar open / compute / classify / components. Changed from the table (rule 12): Automation's Stop is not added — a running automation is a task, stopped from the Tasks list like every other one, and the page has no stop of its own; "from a template" is choosing it in the list, not a command; Remote sensing has no Bands menu (the index list and the formula are fields, the one command Compute is in Analyse, and a menu of one item helps nobody) and no File → Export: every result is written as a GeoTIFF next to the image when computed (the page says where). Guides 10 and 11 in four languages; `test_automation_and_remote_sensing_window_menus`. Found on the way: three Turkish template descriptions still said "mukayese yıldızları" (the owner chose "karşılaştırma yıldızı", I6d): fixed.
- **I6c.11 The user walk (I6a) in four languages:** **agent2 done (2026-11-08, commit 611abd0)** — every area window opened at 1366 × 768 in English, Turkish, German and Spanish (scratchpad `i6c11/walk.py`, results `i6c11/<lang>.json`): menu bars and toolbars checked for cuts, the menu bar's Alt keys for doubles, every menu action looked up in Ctrl+K. Found and fixed: (1) the same Alt key twice in a menu bar — English O−C Edit / Ephemeris (now E&phemeris), Spectroscopy and Models View / Velocity, Visual orbit (now Velo&city, Visual &orbit); Turkish Dosya / Düzen in every window (now Dü&zen) and Yıldızlar / Düzen (Yıldızla&r); Spanish Ver / Ventana in every window (now Ven&tana, with T&omas, Tra&bajo, Telesc&opio, E&femérides moved off it) and, in the main window, Complementos / Configuración (now Co&nfiguración); German had none; (2) the plot toolbar was cut (») in the Remote sensing side panel: its three named buttons (Publication figure, Export data, Open in a new window) are now icons with their names as tooltips, as the plot's own buttons, in every window; (3) a translation overwritten to empty showed nothing: the translation test now refuses empty translations. Ctrl+K found every menu action in every window. `test_every_window_menu_bar_fits_and_has_distinct_keys` checks the English windows on every run. After the push CI found two more: on macOS the plot toolbar was still cut in the Remote sensing side panel (larger buttons): the plot toolbars now use 20 px icons, as the Images toolbar, and that panel starts wider; and the ARM Linux installer stopped at start-up in the Images window's Edit menu ("QMenu already deleted", not seen on the other systems or here): the menu is now looked up in the menu bar, and a missing one no longer stops the program. Original: no cut toolbar, Ctrl+K finds every menu action, names checked.

### I7. Basic / Expert, guide, screenshots
**agent2 done (2026-11-08): I7.1–I7.4 all done**
- **Build:**
  - Basic / Expert decides which panels open by default in each area window;
  - the guide is rewritten around the area windows, in 4 languages, with new screenshots
    (`tools/guide_screenshots.py`);
  - the first-run tour in `main_window.py` too ("taken to the right page", "every page explained", "training
    pages"); the old names "Light curves & O-C", "Orbits & models" left in the tour texts and `MainWindow._titles`.
- **Accept:** the guide's sections match the windows, in all 4 languages.
- **Split into I7.1–I7.4 (agent2, 2026-11-08):**
  - **I7.1 Names and the tour.** **agent2 done (2026-11-08, commit 3c44ee8)** — `MainWindow._titles` now takes the areas' names from the Start page blocks (`start_page.areas`, one source: "Light curves & O-C" and "Orbits & models" are gone from the Window menu and the tools); the first-run tour names the windows as their blocks do (Planning, Observing, Calibration, Photometry, then Light curves and period and O−C, Models), says "its window opens" instead of "taken to the right page", and names Help → Training guide and F1 instead of "training pages"; the page headings Plan / Observe / Calibrate became Planning / Observing / Calibration as their windows. Four languages.
  - **I7.2 Basic / Expert panels.** **agent2 done (2026-11-08, commit 9839f1e)** — found: a later change of Basic / Expert reached only the framed windows; the Photometry window's sections (More measuring options, Other tools) kept the mode they were built with. `set_ui_mode` now also applies to every area window. Changed from the step (rule 12): no panel is hidden in Basic — the two windows with panels have only what every user needs (Photometry: Steps and Results; Spectroscopy: Steps with the job's settings), and hiding Results would hide the light curve; Basic / Expert keeps its one meaning, folding the rarely changed options, as the Start page says. `test_basic_expert_reaches_the_windows_with_panels`. Original: which panels of the Photometry and Spectroscopy windows start shown in Basic, and in Expert.
  - **I7.3 Screenshots of the windows.** **agent2 done (2026-11-08, commit 58258b6)** — `tools/guide_screenshots.py` now grabs the area windows at 1366 × 768: the first-night pictures from the Calibration, Photometry and Automation windows (they were of the main window, which no longer shows the pages), and one picture of every area window (`window-<area>.jpg`, JPEG to keep the guide small: 0.7 MB per language) with the practice night's data where the exercise made some (a calibrated frame in Images, the practice star planned, the light curve in Light curves and the minimum in O−C). Guides 02–11 show their window's picture under the first paragraph, in four languages (07 both of its windows). Looked at in four languages (scratchpad `win4.png`, `win4b.png`). Original: grabs the area windows, one picture per window in four languages, and the guide pages show them.
  - **I7.4 The guide read against the windows.** **agent2 done (2026-11-08, commit 58258b6)** — every "page" that meant an area is now its window, named as its block and title bar (Planning, Observing, Calibration, Models, Light curves and period, O−C) in four languages: about 45 places per language, the button names quoted as they are now (Send to the Observing window, 4. Measure them in the Photometry window →, To the Observing window), the headings of 02, 07 and 09 as the windows (Planung, Light curves and O−C, Models), the first-night pictures' captions, "It opens in a window of its own" after a sentence that already names the window shortened. Found: the Spanish guide sent Expert mode to "Ajustes", but the menu is Configuración: fixed. The guide's sections already matched the windows (I6c wrote each window's menus into its page); I7's accept — the guide's sections match the windows in four languages — holds. Original: page by page in four languages: every menu, toolbar and panel named as on screen; old names removed.

## Where everything is (keep this up to date)

Every feature the user sees, with its window, menu, toolbar and panel. Fill it in as I4 moves each page; add a row
whenever any area gains a feature.

| Feature | Window | Menu | Toolbar | Panel / tab |
| --- | --- | --- | --- | --- |
| Choose images, frame list, bad frames | Photometry | File | yes | Steps 1, Frames tab |
| Mark target / comparison / check stars, suggestions from Gaia | Photometry | Measure | yes | Steps 2, Stars |
| Star list saved / opened on another night (RA / Dec) | Photometry | Stars | — | Steps 2 |
| Radii from the star profiles and the aperture scan | Photometry | Measure | yes | Steps 3 |
| Radii rule: best S/N or as AstroImageJ (1 % of the peak, sky 2–4×) | Photometry | — | — | Steps 3 (Rule) |
| Measure the light curve, lost frames shown | Photometry | Measure | yes | Steps 4, Light curve |
| Sky noise from the camera (gain, read noise, dark) and sky from the ring (median, mode, mean, plane) | Photometry | — | — | Steps 4, More measuring options |
| Saturation and linearity limit, leave out flagged points | Photometry | — | — | under the plot |
| Target follows the field (not centred); donut stars centred | Photometry | — | — | Steps 2 |
| Multi-plot (series, binning, normalisation range, colours, set-up file), leave each comparison star out | Photometry | Analyse | — | Results: Plot (Multi-plot) |
| Detrending: BIC of every set, meridian-flip step (PIERSIDE), spline trend, leave out outliers | Photometry | Analyse | — | Results: Plot |
| Measurements table (AstroImageJ's columns, filter, column chooser, CSV) | Photometry | — | — | Results: Measurements |
| Field identification (Gaia solve, VSX, OBJECT check) | Photometry | Analyse | — | Steps 1 note |
| Minimum timing → O−C | Photometry | Analyse | — | Minimum tab |
| O−C diagram, ephemeris look-up (VSX), third body, apsidal motion | O−C (its own window) | File → Open… (minima) | — | — |
| Command search (find any action of the window) | every area window | Edit → Find an action… (Ctrl+K) | — | — |
| Open, recent files, drop files | Images, Photometry, Calibration, Light curves, Spectroscopy, Remote sensing | File | — | — |
| Save / Open session | (frame ready, no area wired yet) | File | — | — |
| Report a problem (zip for the developer) | main window, every area window | Help | — | — |
| Combine several exposures of one star (scombine) | Spectroscopy | — | — | Spectrum tools tab |
| Spectroscopy jobs (long slit, échelle, telluric, velocities, IFU, tools) | Spectroscopy | Job | yes | Steps |
| Automation: new, save as, steps (add, remove, order), run, send its sequence to Observing | Automation | File, Steps, Run | yes | — |
| Band formula and indices (NDVI…), k-means classes, principal components | Remote sensing | Analyse | yes | — |
| Targets: add, add with ephemeris (VSX / NASA Exoplanet Archive), remove | Planning | Targets | yes | — |
| Night plan, visibility chart, exposure time, schedule, send to Observing | Planning | Night | yes | chart |
| Observatory set-up, connect, start it on this computer | Observing | Devices | yes (connect) | — |
| Slew, centre (plate solve), polar alignment, park | Observing | Telescope | yes | — |
| Preview frame, cooler, filter wheel | Observing | Camera | yes (preview) | — |
| Autofocus, focuser position | Observing | Focus | yes (autofocus) | — |
| Sky flats, panel flats | Observing | Flats | — | — |
| Exposure rows, start / abort / resume the sequence, night plan | Observing | Sequence | yes (start, abort) | Sequence |
| Image operations (pixel math, flips, rotations, resample, bin, crop, filters, deconvolution, DDP, histogram match) | Images | Process | yes | — |
| Measuring tools (Move, Star, Area, Line, Whole image), photometric coefficients | Images | Analyse | tool buttons | Information, Graph |
| Overlays (contours, grid, Gaia, VSX, SkyBoT, finder chart, DS9 regions) | Images | Overlays | yes | — |
| Plate solve, asteroid and comet astrometry (MPC report) | Images | Astrometry | yes (solve) | — |
| Colour image from three filters, split a colour camera's raw image into R, G, B | Images | Colour | — | — |
| Stack or drizzle the open images, blink | Images | Stack | yes (blink) | — |
| Header: add / change / delete keywords, copy it, save a copy with the changes | Images | Edit, File | — | Header tab |
| Save picture, convert many images, export the graph's data (CSV), close images | Images | File | yes (save) | — |
| Text size larger / smaller / normal | main window, every area window | View → Text size (Ctrl+Shift++ / − / 0) | — | — |
| Panels on / off, Reset layout | every area window | View | — | panels |
| Toolbar icons, Toolbar text (names beside the icons) | every area window | View → Toolbar text | yes | — |
| Open an area, list of open windows | main window, every area window | Window | — | Start page blocks |
| Photometry toolbar (Images…, Blink, ◀ ▶, Bad frames, Comparisons, Radii, Measure, Minimum, Export) | Photometry | Measure | yes | — |
| Photometry results (light curve, stars, minimum, export) | Photometry | — | — | Results panel (bottom) |
| (rows for every other page are added in I4) | | | | |

## Done
