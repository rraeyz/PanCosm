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
- **"Panels beside the image" (2026-11-08, agent2):** before the area windows, any page could be shown as a panel
  beside the image in the main window. Now every area, Images included, is its own window, so the feature has
  nothing left to show: it is switched off and its menu hidden, but the code (`MainWindow.dock_page`, `_Panel`) is
  still there. Remove it?
- **Turkish term for comparison star (2026-11-08, agent2):** the interface and the guide use both "mukayese yıldızı"
  (17 strings) and "karşılaştırma yıldızı" (18 strings), sometimes on the same screen (Photometry step 2). Which
  one? Then every string and the guide are made the same.
- **The sidebar (2026-11-08, agent2):** once every area has its own window (I4), the main window's sidebar of pages
  is no longer needed (the blocks open the areas). Remove it then, or keep it as a second way in? Nothing is removed
  before the owner says.
- **Light curves / Period / O−C (I4 item 3):** one window with tabs as today, or two windows (O−C; Period /
  frequency)? Until the owner answers, I4 keeps them in one window with tabs, as today.
- **I1 proposal (2026-11-07, agent2):** the menus and toolbar of each area window in the table under I1. Asked in
  the chat; until the owner answers, I2 builds the shared frame (which does not depend on it) and I3 / I4 follow the
  proposal, changing it when the owner says.

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
**open** — on the Spectroscopy window at 960 × 700 (es) the "In what order? (click)" box above the tabs is open in
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

### I7. Basic / Expert, guide, screenshots
**open**
- **Build:**
  - Basic / Expert decides which panels open by default in each area window;
  - the guide is rewritten around the area windows, in 4 languages, with new screenshots
    (`tools/guide_screenshots.py`);
  - the first-run tour in `main_window.py` too ("taken to the right page", "every page explained", "training
    pages"), and the sidebar's old names ("Light curves & O-C", "Orbits & models") once the owner has answered on
    the sidebar.
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
| Command search (find any action of the window) | every area window | Edit → Find an action… (Ctrl+K) | — | — |
| Open, recent files, drop files | Images, Photometry, Calibration, Light curves, Spectroscopy, Remote sensing | File | — | — |
| Save / Open session | (frame ready, no area wired yet) | File | — | — |
| Report a problem (zip for the developer) | main window, every area window | Help | — | — |
| Text size larger / smaller / normal | main window, every area window | View → Text size (Ctrl+Shift++ / − / 0) | — | — |
| Panels on / off, Reset layout | every area window | View | — | panels |
| Open an area, list of open windows | main window, every area window | Window | — | Start page blocks |
| Photometry toolbar (Images…, Blink, ◀ ▶, Bad frames, Comparisons, Radii, Measure, Minimum, Export) | Photometry | Measure | yes | — |
| Photometry results (light curve, stars, minimum, export) | Photometry | — | — | Results panel (bottom) |
| (rows for every other page are added in I4) | | | | |

## Done
