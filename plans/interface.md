# Interface: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done".
Every step of every area that changes what the user sees follows this file.

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, `plans/architecture.md` "Conventions" and "Definition of done", your area file, and this file before
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

The look and behaviour of every window: the design system, the component kit, the anatomy shared by all area
windows, the layout of each window, help, onboarding and the tests that keep it right.

**Goal:** a newcomer opens a window and knows what to do first; an expert finds every function of AstroImageJ,
MaxIm DL, IRAF, iSpec, Period04 and PHOEBE within two clicks; the data get most of the screen; the program looks like
one modern product, not a set of forms.

## What the audit found (screenshots of every window, 1366 × 768, 2026-11-09)

1. Toolbar icons are Unicode glyphs (✶ ◎ ✦ ⋎ ⌁ ◈ …): unreadable; some render differently on each system.
2. Photometry: the steps panel is a scroll column squeezed into a dock; the frame table shows one and a half rows;
   the image gets a third of the window; a results dock titled "Results: light curve, stars, minimum, export".
3. Calibration: half the left side is grey explanatory paragraphs; buttons numbered "3. Calibrate", "4. Measure…"
   next to unnumbered ones; no picture of any frame or master anywhere.
4. Spectroscopy: a form of spin boxes ("Spectrum at row: the brightest") before any data are shown; two folded
   explanations stacked on top; the plot toolbar floats in an empty black area.
5. Light curves: nine buttons and fields in a column, "Undo edits" as a button, an empty white-on-black void.
6. O−C: minima as a free text box; radio buttons for models; no table.
7. Models: a parameter table with seven rows visible, six export buttons in a grid, an empty plot.
8. Observing: address, token and certificate fingerprint are the first things shown; fourteen buttons in a grid.
9. Start window: a plain two-column list of blocks; three quarters of the window empty; a Tasks dock always open.
10. Everywhere: titles repeated inside the window ("Photometry" under the title bar), walls of text instead of help
    on demand, no empty states with a first action, default Qt spin boxes and tables.

What is good and stays: one window per area with its own menus; Ctrl+K command search; dark / light themes;
tooltips on every control; undo; four languages; the Workflow idea.

## What the reference programs teach (read 2026-11-07 … 2026-11-09; details in `docs/history/interface-plan-2026-11-08.md` I1)

- **AstroImageJ:** per-window menus; a toolbar of toggles on the image window; RA / Dec at the cursor; Multi-Plot
  with one row per plotted series and a fit panel per series; a measurements table with a filter. Avoid: a dozen
  floating windows and settings spread among them.
- **MaxIm DL:** a plain menu bar (File, Edit, View, Analyze, Process, Filter, Color, Plug-In, Window, Help); tool
  windows that dock or float (Information, Photometry, Observatory, Screen Stretch); the Photometry tool's tabs follow
  the workflow left to right (Select, Quality, Match, Identify, Graph); the Information window changes its content
  with a mode (Aperture, Astrometric, Magnitude, Region, Area).
- **Siril:** the right panel is a notebook whose tabs follow the workflow (Conversion, Sequence, Calibration,
  Registration, Plot, Stacking); display tools under the image. Avoid: menus hidden in a header bar.
- **N.I.N.A.:** a vertical strip of areas with large icons; the Imaging tab is a docking area whose panels (image,
  statistics, HFR history, guiding, autofocus) the user arranges; a simple and an advanced sequencer; layouts saved
  per profile with "Reset layout".
- **DS9 / Ginga:** the image is the window; scale, colour, zoom, regions and analysis in menus and a button bar;
  frames locked by WCS; magnifier and panner always visible.
- **iSpec:** the spectrum is the window; several spectra overlaid with one active; an *Action × Element* mode
  (create / modify / remove × continuum / lines / segments) so that regions are drawn on the plot.
- **PypeIt Identify, IRAF identify / apall:** the fit and its residuals stay visible beside the arc; single keys
  act on the feature under the cursor.
- **Period04:** three modules as tabs (Time string, Fourier, Fit) and a log; the list of frequencies with tick boxes
  is always in view; every result plot opens in its own window.
- **PHOEBE 1 / PyWD2015:** tabs per parameter group (system, stars, surface, spots, third body), a fitting tab with
  the table of adjustable parameters and their corrections, a synthetic-curve window, a star-shape view. Avoid:
  dozens of numeric fields with cryptic WD names (IPB, IFAT, MREF) and no guidance.
- **Modern production tools** (video editors with pages left-to-right, raw developers with module strips, code
  editors with an activity bar and a command palette): a narrow rail chooses the stage of the work; the middle
  belongs to the content; details live in an inspector on the right; a palette reaches everything.

## Design principles (every decision is tested against these)

1. **The data are the hero.** At 1366 × 768 the main view (image, spectrum, curve) has at least 55 % of the window
   area in every working state.
2. **One stage at a time.** The left side shows the controls of the current stage only; the rail shows all stages
   and their state. Never one long scroll of everything.
3. **One primary action per stage,** blue, at the bottom of the stage panel, named by its result ("Measure the
   light curve"), never numbered.
4. **Guide, never gate.** Every stage can be opened at any time; a stage that lacks an input says which and offers
   to open a file instead ("I already have a light curve").
5. **Defaults first, options folded.** A stage shows the three to six controls most users change; the rest is under
   "More options" (always open in Expert mode).
6. **Explain on demand.** Labels are short; a tooltip is one or two lines; the "?" of a section opens the Help
   panel at the right guide paragraph. No paragraph of explanation lives in a working panel.
7. **Show what happened.** Every automatic choice (comparison stars, radii, lines matched, frames left out) is
   listed with its reason and can be changed; nothing important is silent.
8. **Everything undoable, nothing lost.** Ctrl+Z everywhere; sessions autosave; closing a window never asks "are you
   sure" because nothing is lost.
9. **The same thing looks and works the same everywhere:** plots, tables, images, file fields, number fields,
   progress, errors, export.
10. **Calm.** Few colours, used for meaning: blue = action / selection, green = target / done, vermilion =
    comparison stars, amber = attention, red = error. No decoration.

## The design system (binding values; built by UI-1 … UI-3)

### Colour tokens

| Token | Dark | Light | Use |
| --- | --- | --- | --- |
| `surface.0` | `#14171c` | `#f4f6f9` | window background |
| `surface.1` | `#1b1f26` | `#ffffff` | panels, inputs, tables |
| `surface.2` | `#242a33` | `#eef1f5` | raised: buttons, headers, cards |
| `surface.3` | `#2d3440` | `#e3e8ef` | hover |
| `border` | `#343c49` | `#d3d9e2` | hairlines, input borders |
| `border.strong` | `#465062` | `#b6bfcc` | separators that must be seen |
| `text` | `#e7eaf0` | `#1a2130` | main text |
| `text.muted` | `#9aa3b2` | `#5b6576` | labels, captions |
| `text.faint` | `#6b7485` | `#8a93a3` | placeholders, disabled |
| `accent` | `#4f8cff` | `#2f6fe4` | primary action, selection, focus ring |
| `accent.hover` / `accent.pressed` | `#6ea0ff` / `#3b74e0` | `#4a83ea` / `#2459c2` | states |
| `on.accent` | `#ffffff` | `#ffffff` | text on accent |
| `ok` | `#3ecf8e` | `#1f9d63` | done, valid |
| `attention` | `#f5a524` | `#b7791f` | warnings, things to look at |
| `error` | `#f0544f` | `#d1343f` | errors |
| `image.background` | `#000000` | `#000000` | behind images (always black) |

Data roles (the same in images, plots and tables; chosen from the Okabe–Ito palette so that red–green colour
blindness keeps them apart; each role also has its own shape and label):

| Role | Colour | Shape / label |
| --- | --- | --- |
| target | `#00b386` (bluish green) | solid ring, `T1`, `T2` |
| comparison | `#e8642c` (vermilion) | solid ring, `C1` … |
| check | `#56b4e9` (sky blue) | dashed ring, `K1` … |
| suggested, not yet accepted | `#c8ccd4` | dotted ring |
| rejected / left out | `#6b7485` | thin ring with a stroke through, or a hollow point |
| attention on a point (saturated, non-linear, partial) | `#f5a524` ring (non-linear), `#f0544f` ring (saturated) | around the point |

Plot series palette, in order: `#4f8cff`, `#e69f00`, `#00b386`, `#e8642c`, `#cc79a7`, `#56b4e9`, `#f0e442`,
neutral (`text.muted`). Filters have fixed colours wherever a series is one filter: U `#7b5cd6`, B `#4f7dff`,
V `#3aa657`, R `#e5484d`, I `#a23b3b`, u′ `#6f52c9`, g′ `#2fa8a0`, r′ `#e5674d`, i′ `#b0413e`, z′ `#7a2e2e`,
clear / luminance `#9aa3b2`, TESS `#c2410c`, Kepler `#b45309`, Gaia G `#6aa84f`, BP `#4f7dff`, RP `#e5484d`.
Model curves are `text` colour at 1.5 px; residuals share the series colour.

### Type, spacing, shape

- **Fonts bundled** (SIL Open Font Licence, listed in `THIRD_PARTY.md`): Inter for the interface, JetBrains Mono for
  numbers in tables, read-outs, logs and code. Tabular figures on (`QFont.setFeature("tnum")`), so columns of numbers
  line up.
- **Sizes:** base 10 pt; small 9 pt (captions, table headers, status bar); section title 11 pt semibold; window
  stage title 13 pt semibold. No larger text inside working windows. View → Text size scales all of them.
- **Spacing on a 4 px grid:** 4, 8, 12, 16, 24, 32. Panel padding 12; gap between form rows 8; between sections 16.
- **Controls:** height 28 px (24 in tables and toolbars' compact mode); radius 6; cards radius 8; docks square.
  Icon buttons 32 × 32 with a 20 px icon. Minimum hit target 28 px.
- **Borders, not shadows;** popovers and menus have a 1 px `border` and a soft shadow.
- **Focus:** a 2 px `accent` ring on the focused control, always visible with the keyboard.
- **Motion:** 120 ms for folding, hover and the Help panel; none on data.

### Icons

- One set: **Lucide** (ISC licence) SVG files bundled in `resources/icons/` plus our own SVGs for astronomy, drawn on
  the same 24 × 24 grid with 1.75 px round strokes. Rendered by `QSvgRenderer`, tinted with `text` (normal),
  `text.faint` (disabled), `accent` (checked) for the current theme and pixel ratio; cached.
- Every toolbar button has an icon **and**, by default, its short name under or beside it (View → Toolbar: icons
  and names / icons only). A newcomer reads names; an expert hides them.
- The table of icons is in `ui/kit/icons.py` (`ICONS: kind → file`). Mapping of the kinds that exist today (Lucide
  names; "own" = drawn by us in UI-2):

| Kind | Icon | Kind | Icon |
| --- | --- | --- | --- |
| open | `folder-open` | open_folder | `folder-plus` |
| save | `save` | export | `share` |
| publication | `file-chart-line` | new_window | `picture-in-picture-2` |
| previous / next | `chevron-left` / `chevron-right` | blink | own: two overlapping frames with an arrow |
| fit | `maximize` | zoom_in / zoom_out | `zoom-in` / `zoom-out` |
| levels | `contrast` | overlays | `layers` |
| process | `wand-sparkles` | solve | own: grid with a star and a tick |
| bad_frames | `image-off` | comparisons | own: three stars, one ringed |
| radii | own: aperture with annulus | measure | own: aperture with a ruler mark |
| minimum | own: dipping curve with a vertical line | scan | `scan-search` |
| calibrate | own: frame minus bias / dark / flat stack | stack | `layers-2` |
| send | `arrow-right-from-line` | add_target | `crosshair` with plus (own) |
| ephemeris | `calendar-clock` | plan_night | `moon-star` |
| exposure | `timer` | schedule | `list-ordered` |
| connect | `plug` | slew | own: telescope with arrow |
| centre | `locate-fixed` | park | `house` |
| preview | `camera` | autofocus | `focus` |
| start / abort | `play` / `square` | new | `file-plus` |
| add_step | `list-plus` | compute | `calculator` |
| classify | `grid-3x3` | pca | `axis-3d` |
| download | `download` | period_search | own: periodogram peak |
| frequency | `audio-waveform` | variable_search | own: star with a sine |
| lookup | `search` | fit_model | `chart-spline` |
| posterior | own: corner-plot blob | visual_orbit | `orbit` |
| long_slit | own: slit with a spectrum | echelle | own: stacked curved orders |
| telluric | own: spectrum with absorption bands | velocity | own: shifted line pair |
| cube | `box` | spectrum_tools | `chart-line` |
| undo / redo | `undo-2` / `redo-2` | settings | `settings` |
| help | `circle-help` | tasks | `list-checks` |
| info / warning / error | `info` / `triangle-alert` / `circle-x` | close / more | `x` / `ellipsis` |

  Area icons for the start window and Window menus (own drawings, 32 px, two-tone): Planning (horizon with an
  altitude curve), Observing (telescope), Calibration (stacked frames), Images (frame with a star), Photometry
  (aperture rings), Light curves and period (folded curve), O−C (points around a zero line with a sine), Spectroscopy
  (spectrum with lines), Models (two touching lobes), Exoplanets (star with a transiting disc), Astrometry (grid with
  a moving dot), Automation (linked boxes), Remote sensing (globe grid), Project (folder with a clock).

### The component kit (`ui/kit/`; nothing outside it creates raw Qt controls for these purposes)

| Component | What it is | Must have |
| --- | --- | --- |
| `Button(text, kind=primary|normal|quiet|danger, icon=None)` | all push buttons | one `primary` per stage; busy state (spinner, disabled) while its task runs |
| `ToolButton(kind, text)` | toolbar and icon buttons | tooltip = name + shortcut; checked state |
| `Section(title, help=None, folded=False, advanced=False)` | a titled group; folds | "?" opens Help at `help`; `advanced` sections are folded in Basic mode |
| `FormRow(label, control, unit=None, help=None, reset=True)` | label left (fixed column 132 px), control, unit right | a dot when the value differs from the default; click the dot to reset |
| `NumberField(value, min, max, step, decimals, unit, allow_auto=False)` | numbers | no accidental wheel changes unless focused; drag on the label to scrub; red border and reason when invalid; "auto" state with the automatic value shown faint |
| `ChoiceField`, `Toggle`, `Segmented(options)` | choices | Segmented for 2–4 exclusive options instead of radio buttons |
| `PathField(kind=file|files|folder, filters, recent_key)` | choosing files | drop target; recent list; shows count and first name for many files; "…" button |
| `ObjectField` | a star or object by name or coordinates | resolves through `services`; shows what was found; works offline from the cache |
| `StageRail(stages)` | the vertical rail of stages | number or icon, name on hover or expanded, state dot: empty / current / done ✓ / attention ! |
| `StagePanel(title, help)` | the left panel of the current stage | scrolls inside; primary action pinned at the bottom with a one-line status above it |
| `EmptyState(icon, title, text, primary, secondary=None, sample=None)` | shown in any view that has no data | says what the view will show and offers the first action and "Try with practice data" |
| `InfoBanner(kind=info|ok|attention|error, text, actions=[])` | in-window messages | dismissible; stacks at the top of the view it concerns; never a modal dialog for information |
| `Toast` | brief confirmations ("Saved to …" + "Show in folder") | bottom right, 5 s, never for errors |
| `ErrorDialog` / `errors.show` | failures of a task | what happened, what to do, Details, Copy, Report |
| `TableView` (ARC-8) | all tables | sort, filter, columns, copy, export, link to plots |
| `PlotView` (ARC-6) with `PlotToolbar` | all interactive plots | the common interactions and export |
| `ImageView` (ARC-7) with `ImageToolbar` | all images | the common tools, read-out, layers |
| `Inspector(title)` with `KeyValue` rows | the right panel of details | selectable text; copy; units |
| `HelpPanel` | guide paragraphs beside the work | opens with F1 or a "?"; shows the paragraph for the control in focus; "Open the full guide" |
| `TaskChip` / `TaskPopover` | background work | chip in the window's toolbar: count running; popover lists tasks with progress, cancel, details |
| `StatusBar` segments | read-out · message · progress | read-out left (monospace), message middle, progress and cancel right |
| `Splitter` | resizable panes | sizes remembered per window; double-click resets |
| `Badge(text, kind)` | small state labels | "calibrated", "from cache", "simulated" |
| `Dialog(title)` | the few real dialogs (preferences, export options) | buttons right-aligned, primary last; Esc cancels; remembers size |

## Anatomy of an area window (binding; built by UI-4)

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ File  Edit  View  <area menus>  Tools  Window  Help                                           │ menu bar
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│ [open][save] │ <frequent actions of the area, icon + name> │        [🔍 Find an action] [tasks]│ toolbar
├────┬───────────────────────┬───────────────────────────────────────────────┬──────────────────┤
│ 1 ✓│ Stage title        ?  │                                               │ Inspector    [×] │
│ 2 ●│ ───────────────────── │              MAIN VIEW                        │ (details of the  │
│ 3 ○│ form rows of this     │        image / spectrum / plot                │  selected star,  │
│ 4 ○│ stage only            │        (≥ 55 % of the window)                 │  frame, line,    │
│ 5 ○│                       │                                               │  parameter)      │
│ 6 ○│ ▸ More options        ├───────────────────────────────────────────────┤                  │
│    │                       │ [Plot] [Table] [Frames] [Log]            [⤢]  │                  │
│    │ status line of stage  │        RESULTS DOCK (tabs; any tab can be     │                  │
│ ?  │ [ Primary action    ] │        pulled out to another monitor)         │                  │
├────┴───────────────────────┴───────────────────────────────────────────────┴──────────────────┤
│ x 1024.3  y 512.7  value 1834.2   α 13 38 48.1  δ −02 01 49   │ message          │ ▓▓▓░ 62 % [×]│ status bar
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Rail** 48 px (icons with numbers); expands to 180 px with names on hover or when pinned. The last rail entry is
  Help (opens the Help panel in place of the Inspector).
- **Stage panel** 320 px (280–420, resizable, hideable with F9). Its content scrolls; its primary action never
  scrolls away.
- **Inspector** 300 px, shown when something is selected or when pinned (F10); hidden by default below 1500 px width.
- **Results dock** 240 px high by default (resizable; F11 toggles; any tab floats). A window without tabular or
  plotted results has none.
- **No title inside the window** repeating the title bar. The title bar reads "<Area> — <project or first file>".
- **Sizes at 1366 × 768** (client area about 1366 × 700): rail 48 + stage 320 + main 998 (inspector hidden);
  main view height 700 − 28 menu − 44 toolbar − 26 status − 240 dock = 362 px with the dock open, 602 px with the
  dock closed. The 55 % rule is checked by a test with the dock at its default.
- **Basic / Expert** (start window and Settings): Basic folds `advanced` sections and hides the Inspector's raw
  fields; Expert opens them. No function is removed in Basic.

## To ask the owner

- The red night theme as an option for the telescope (PLAN.md §8, question 2).
- After UI-5 and UI-16.1: screenshots on the owner's Windows and CachyOS machines at their real scaling.

## For the owner to try

- After UI-5: start the program; say whether the start window shows what you expect first.
- After UI-16.1 (Photometry): measure NY Vir with the new window and send a screenshot of any stage where it was
  unclear what to do.

## Steps

Order of work: UI-1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15 in stage S1 (PLAN.md §5; UI-8 and UI-14 are P2 and
follow the windows they need); UI-16 sub-steps each as the first step of its area in stage S2; UI-17, 18, 19 in
stage S4. UI steps depend on ARC-4.7 (kit location); UI-16.x depend on ARC-5, ARC-6, ARC-7, ARC-8
for the window concerned.

### UI-1. Tokens and theme  (P1)
**partial** — items 1, 2 (partly), 6 and the grep test done by agent3 (2026-11-11); mono font and ratchet lowered (2026-11-27)
- **Progress (agent3):** `ui/kit/tokens.py`: DARK, LIGHT (the table above), NIGHT prepared (red on black, not
  offered), data ROLES, the SERIES palette, FILTERS with `filter_colour()` (Rc → R, SG → g′, CV → clear …),
  `contrast()`; `ui/theme.py` builds its palette, style sheet (hover, focus ring, primary hover, disabled faint,
  image background) and Matplotlib's colours from it — no colour literal left in it; an old "night" loads as dark.
  `tests/test_tokens.py`: every text token on every surface ≥ 4.5 : 1 (faint ≥ 2.5), and a ratchet on colour
  literals in `ui/` (`tests/data/colour_literals.json`, 80 → 43 now; the rest goes as UI-16 rebuilds each window).
  **Changed from the plan:** the grep test is a shrink-only count per file instead of "none", since the old pages
  are rebuilt in UI-16, not edited twice. Item 3: Inter 4.1 (variable) and JetBrains Mono 2.304 bundled in
  `resources/fonts/` with their OFL texts, registered at start-up, tabular figures on (Qt 6.7+); the layout tests
  pass with them in every language. Item 4: `PlotView` takes its background and axis colours from the theme.
  2026-11-27: `theme.mono_font()` (bundled JetBrains Mono, system fixed font when missing, never raises) in the
  `DataTable` numeric cells, the pixel read-outs (main window, Images window, Remote sensing) and the kit table,
  status bar and inspector; colour literals in `photometry_page`, `spectro_page`, `overlay_actions`, `viewer`
  mapped to `tokens.role()` (ratchet lowered); test `test_numeric_cells_use_the_mono_family_and_the_helper_falls_back`.
  Pending: the full style sheet for every kit control (item 2), live theme change of icons (5).
- **Ours now:** `ui/theme.py`: eight colours per theme in a tuple, one style sheet, Matplotlib rcParams.
- **Build:**
  1. `ui/kit/tokens.py`: the tables above as data (`DARK`, `LIGHT`), with `role()` and `filter_colour()` helpers; a
     `Theme` object given to every kit component; a third token set `NIGHT` (red on black) prepared but not offered
     until the owner says so.
  2. `ui/kit/theme.py`: builds the palette and one style sheet from the tokens for every Qt control the kit wraps
     (buttons by kind, inputs, spin boxes with our own up / down arrows as SVG, combo boxes, check boxes and toggles,
     sliders, tabs, tables, headers, scroll bars, menus, tool tips, docks' title bars, splitters, progress bars,
     group boxes). No colour literal outside `tokens.py` (a test greps for `#[0-9a-f]{6}` in `ui/`).
  3. Fonts registered at start-up from `resources/fonts/`; tabular figures; the text-size setting scales the four
     sizes.
  4. pyqtgraph and Matplotlib take their colours from the same tokens (`ui/plot/style.py`).
  5. Theme change at run time repaints everything without restart (icons included).
  6. Contrast test: every text token on every surface it is used on ≥ 4.5 : 1 (≥ 3 : 1 for `text.faint`).
- **Accept:** screenshots of a kit gallery window (UI-3) in dark and light show no default-Qt control; the grep test
  and the contrast test pass; old `ui.theme` values `dark` / `light` (and `night` → dark) still load.
- **Files:** `ui/kit/{tokens,theme}.py`, `resources/fonts/`, `ui/theme.py` (shim), tests.

### UI-2. Icons  (P1)
**partial** (2026-11-21) — done: Lucide + 16 own SVGs; `ui/kit/icons.py` renders them tinted from the widget's palette (normal / disabled / checked, screen pixel ratio); `tools/icon_sheet.py` writes the contact sheet docs/design/icons.png. 11 area icons on the start window's blocks; `glyph` removed (no caller left). Item 4 exists as View → "Toolbar text" (default stays off: the stored value cannot tell a choice from the old default; owner to decide). Item 3 for menu-only actions (2026-11-21): the window's own Open…, Open session…, Save session…, Close window, Undo, Redo and Find an action get icons through `AreaWindow._build_menus` → `set_icons` (test_one_icon_set_and_icon_toolbars). Left: the area menus' remaining items (no icon kind yet: view toggles, Help items, overlays, process filters).
- **Build:**
  1. `resources/icons/lucide/*.svg` (only the files used) with the ISC licence text; `resources/icons/own/*.svg` drawn
     by hand as SVG path data on the 24 × 24 grid, stroke 1.75, round caps and joins, no fill except small dots —
     every "own" entry of the table above and the fourteen area icons. Each own icon is reviewed at 16, 20, 24 and 32
     px in both themes (a contact-sheet picture is written by `tools/icon_sheet.py` and looked at; the sheet is
     committed under `docs/design/icons.png`).
  2. `ui/kit/icons.py`: `icon(kind, theme, size=20, state=normal)` → `QIcon` with normal / disabled / checked
     pixmaps at 1× and 2×; cache keyed by theme; unknown kind raises in tests, shows a placeholder in release.
  3. Every `QAction` and `ToolButton` in the program gets its icon from here; `ui/widgets.glyph` is removed from use
     (kept only until the last caller is gone); the start window's blocks use the area icons.
  4. View → Toolbar → "Icons and names" (default) / "Icons only"; setting `ui.toolbar_text` migrates (old default
     off → new default on, unless the user had chosen).
  5. Test: no two kinds share a file; every kind has a tooltip name; every toolbar action in every window has an
     icon (walk of all windows).
- **Accept:** no Unicode glyph is used as an icon anywhere (a test scans toolbars and menus for single-character
  icon text); the contact sheet shows every icon readable at 20 px in both themes; four-language screenshots of
  every toolbar fit 1366 px with names on.
- **Files:** `resources/icons/`, `ui/kit/icons.py`, `tools/icon_sheet.py`, every window's toolbar code, tests.
- **Depends on:** UI-1.

### UI-3. The component kit and its gallery  (P1)
**partial** — done: Button, ToolButton, Section, FormRow, NumberField, ChoiceField, Toggle, Segmented, PathField, StageRail, StagePanel, EmptyState, InfoBanner, Badge, Toast, ErrorDialog (failed tasks use it), Inspector, StatusSegments, Splitter, Dialog in `ui/kit/`; ObjectField (2026-11-21: `kit/object_field.py`, name resolved through `planning.resolve` via the window's `run_step`, answer line with RA/Dec/source or the offline sentence, `precheck` hook; used by `ui/photometry_name.py`; test `test_object_field_resolves_and_says_failures`; by name only, no coordinate input); `tools/kit_gallery.py`; one test per component in tests/test_kit.py. Shortcuts: PathField lists many files in a tooltip, not a popover; NumberField shows the unit as a suffix (not faint) and has no label scrubbing. Left: HelpPanel (UI-7), TaskChip / TaskPopover (UI-9), the focus-chain and FormRow-alignment checks over the gallery in four languages (UI-15), item 5 (with UI-16).
- **Build:**
  1. Every component of the table above in `ui/kit/` (`buttons.py`, `sections.py`, `forms.py`, `fields.py`,
     `rail.py`, `empty.py`, `banners.py`, `toast.py`, `inspector.py`, `help.py`, `tasks.py`, `status.py`,
     `dialogs.py`, `splitter.py`, `badge.py`), each with a docstring that shows its use, each using only tokens.
  2. `NumberField` details: validation on every keystroke; Enter commits, Esc restores; units shown faint at the
     right inside the field; `allow_auto` adds a small "auto" toggle and shows the automatic value in `text.faint`;
     wheel changes the value only when the field has focus; Shift = ×10, Ctrl = ×0.1 steps.
  3. `PathField` details: accepts drops from the file manager and from our own windows; many files show "48 files —
     first: light_V_000.fits" with a popover listing them; a missing file turns the field amber with the reason.
  4. `tools/kit_gallery.py`: a window showing every component in every state (normal, hover, focus, disabled,
     invalid, busy), used for the screenshots of UI-1 and for visual review; `tests/ui/test_kit.py` drives each
     component (keyboard and mouse).
  5. The existing `Collapsible`, `StepGuide`, `_Columns`, `PlotCanvas`, `DataTable` remain as thin wrappers over the
     kit until their callers move.
- **Accept:** gallery screenshots (dark / light × four languages with long sample texts) show no cut text and
  consistent heights and gaps (a test measures that all controls in a `FormRow` column share left edges and
  heights); every component is keyboard-usable (focus chain test).
- **Files:** `ui/kit/*`, `tools/kit_gallery.py`, tests.
- **Depends on:** UI-1, UI-2, ARC-4.7.

### UI-4. The area window frame  (P1)
**partial** — done: `kit/anatomy` on AreaWindow: `set_stages([Stage])` (rail + stage panels in a dock), `show_stage`, `set_stage_state`, `set_inspector`, `add_result_tab` (items 1 without set_main / set_empty_state, 5: F9, F10, F11, Ctrl+1…9, Ctrl+Tab); a window whose title bar would open on no screen is moved onto one (item 2); the toolbar ends with Find an action and Help and the TaskChip (item 4). No area uses the stages yet (UI-16). (2026-11-20) `set_main`, `set_empty_state`, `set_result_stale` ("(out of date)"), `Stage.hint`; layout memory per screen arrangement (`ui/kit/layout_memory.py`: docks, floating tabs, the rail; a missing screen's window moved back); `tests/ui/test_anatomy.py`. Left: a shared Tools menu, something setting the stale mark.
- **Ours now:** `ui/area_window.AreaWindow` (menus, toolbar, docks, layout memory, command search, sessions frame).
- **Build:**
  1. `ui/kit/window.py`: `AreaWindow` rebuilt on the anatomy above: `set_stages([Stage(key, title, icon, panel,
     help)])`, `set_main(widget)`, `add_result_tab(key, title, widget)`, `set_inspector(widget)`, `set_empty_state`.
     Stage state (`empty | current | done | attention`) is set by the controller from the session state.
  2. Layout memory per window and per screen arrangement (geometry, splitter sizes, floating tabs, rail pinned);
     View → "Reset layout"; a layout that would open off-screen (monitor removed) is moved onto a screen.
  3. Common menus built once (File, Edit, View, Tools, Window, Help) with the area adding its own between View and
     Tools; the same shortcuts everywhere (UI-12).
  4. The toolbar's right end: "Find an action" field (Ctrl+K), the `TaskChip`, Help (F1).
  5. Keys: F9 stage panel, F10 inspector, F11 results dock, Ctrl+1 … Ctrl+9 jump to stage n, Ctrl+Tab next result
     tab.
  6. A window never blocks on a task: the stage's primary button shows the task; the rest stays usable; results of
     an older run stay visible, marked "out of date" (a `Badge`) when their inputs changed.
  7. `tests/ui/test_anatomy.py`: for every window, at 1366 × 768 with the dock at its default: main view ≥ 55 % of
     the central area; nothing overflows; the primary action is visible without scrolling.
- **Accept:** a demo window with six stages, an image, two result tabs and an inspector passes the anatomy test in
  four languages; pulling a tab to a second (virtual) screen and restarting restores it; old layouts are ignored
  without error.
- **Files:** `ui/kit/window.py` (moved there from `ui/area_window.py` in ARC-4.7), tests.
- **Depends on:** UI-3.

### UI-5. The start window  (P1)
**partial** — done: the Tonight line (item 3: dark hours and Moon from `planning.visibility.tonight`, computed in a thread; without a site a link to Settings → Profiles); Continue as cards (item 1 from the recent files: area icon, file, area, when saved; at most six, a click reopens; sessions with ARC-5); a banner while working offline (item 5 in part); the status strip (item 5: "Processing: automatic / CPU / GPU" without probing the GPU at start-up, and "● Online / ● Offline", a click switches working offline; time tables and tasks not yet); the area icons on the blocks (UI-2). (2026-11-20) Practice data…, All sessions…, a one-line empty state, a right-click on area cards (Open, the guide chapter), time-table and task chips in the status strip, Find anything with Ctrl+K (`ui/start_search.py`), the welcome's "Set up my site and equipment now". Left: Practice data opening one set in its window, the keyboard-only accept test.
- **Ours now:** `ui/start_page.py` (blocks per area, project buttons, Basic / Expert), `ui/welcome.py`, `ui/tour.py`.
- **Reference:** N.I.N.A.'s area strip with icons; raw developers' and editors' start pages (recent work first, then
  what you can do); MaxIm DL has none (a blank frame) — a chance to be clearer.
- **Build:**

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ File  Edit  Tools  Plugins  Settings  Window  Help                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  <logo>  <product name>                 [🔍 Find anything…  Ctrl+K]        Basic ◉ Expert ○  │
│                                                                                              │
│  Continue                                             Start something                        │
│  ┌───────────────────────────┐ ┌──────────────────┐   [ New project ] [ Open project… ]      │
│  │ NY Vir 2026-11-03         │ │ HD 189733 RV     │   [ Open images… ] [ Practice data ▾ ]   │
│  │ Photometry · light curve  │ │ Spectroscopy     │                                          │
│  │ yesterday 23:10           │ │ 3 days ago       │   Tonight at <site>:  dusk 17:42 · Moon  │
│  └───────────────────────────┘ └──────────────────┘   34 % · 3 planned targets  [Plan →]     │
│                                                                                              │
│  Areas                                                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  icon    │ │  icon    │ │  icon    │ │  icon    │ │  icon    │ │  icon    │ │  icon    │  │
│  │ Planning │ │ Observing│ │Calibrat. │ │ Images   │ │Photometry│ │Light crv.│ │  O−C     │  │
│  │ one line │ │ one line │ │ one line │ │ one line │ │ one line │ │ one line │ │ one line │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Spectrosc.│ │ Models   │ │Exoplanets│ │Astrometry│ │Automation│ │Remote s. │ │ Project  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ ● GPU: RTX 4050 · ● Online · ● Time tables up to date · ● 0 tasks              version 0.4.0 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

  1. "Continue" cards from the autosaved sessions (ARC-5) of the open or the recent projects: area icon, object or
     first file, what was last done, when; a click reopens the window exactly as left. At most six; "All sessions…".
  2. "Start something": the four buttons; "Practice data" lists the sample sets (ARC-21) and opens the right window
     with them.
  3. "Tonight" line only when a site profile exists; otherwise "Set up your site to see tonight's sky" (opens
     Settings → Profiles).
  4. Area cards 150 × 110 px with the area icon (32 px), name, one line of what it is for; hover lifts the border
     to `accent`; Enter / click opens; right-click: "Open in a new window", "Open the guide chapter".
  5. The status strip: GPU (name or "none — using the processor"), Online / Offline (click: the services check),
     Time tables (ARC-1), Tasks (opens the task popover). The always-open Tasks dock is removed from the start
     window; the task list lives in the popover and as a tab of the Project window.
  6. The search field is the command palette over everything: areas, actions of every window, recent files, guide
     topics, settings.
  7. The welcome dialog (first run) keeps: language, processing device, look — plus the time-table setting
     (ARC-1) and "Set up your site and equipment now / later".
- **Accept:** at 1366 × 768 and 1920 × 1080, in four languages, no card text is cut (names may wrap to two lines);
  with no project and no sessions the left column shows an empty state with "Open images…" and "Try the practice
  night"; a QTest opens every area by keyboard only.
- **Files:** `ui/shell/start/*.py`, `ui/welcome.py`, tests, guide 01.
- **Depends on:** UI-3, UI-4, ARC-5 (cards), ARC-16 (tonight line; without it the line shows the set-up hint).

### UI-6. Empty, loading and error states for every view  (P1)
**partial** — done: every PlotCanvas (21 plots) says why it is empty until something is drawn (`set_empty_hint` for a page's own words); the image viewers of Images, Photometry, Spectroscopy and Remote sensing already had their hint. Loading state: while a window's task runs, its empty plots say "Working: <step> — n %" (`AreaWindow._show_busy`). Error state: a plot whose drawing fails says "This plot could not be drawn: …" over itself (logged to app.log), the next good drawing removes it. The walk test (2026-11-13, `tests/test_empty_states.py`): every area window
opened in a fresh profile, every visible plot and image view has data or words. Left: the table of views with their
own texts.
- **Build:** a table in this step (filled by the agent) of every main view and result tab of every window with its
  `EmptyState` text, primary action and practice set; loading states (skeleton: the view's frame with a thin
  progress line and the task's phase text); error states (the `InfoBanner` with the error's what / do and "Try
  again"). No view may show a black or blank rectangle without words. Texts are written for a newcomer: what will
  appear here, and the one thing to do to get it.
- **Accept:** a test opens every window in a fresh profile and asserts that every visible view shows either data or
  an `EmptyState`; screenshots in four languages reviewed.
- **Files:** every window's panels, `tests/ui/test_empty_states.py`.

### UI-7. Help on demand  (P1)
**partial** — done: item 1 (every guide topic has a stable anchor `{#area-words}`, the same in all four languages; `guide_page.anchors`, `GuidePage.show_anchor`; a Section's or stage's help button opens its topic; a test checks every anchor used exists); item 2 in part: `kit/help.HelpPanel` at the right of an area window, F1 opens the topic of the Section or stage around the control in focus, with "Open the full guide" (no search box or picture yet); Help → What is this? (Shift+F1): the pointer becomes a question mark and the next click opens that control's topic instead of acting (Esc: never mind; `kit/help.WhatsThis`); item 3: nine long panel texts became one line with "More…" opening their guide topic (`kit/help.help_line`; a test keeps labels ≤ 140 characters). Kept, for the owner to decide: Spectroscopy's "In what order?" (asked for in the window). (2026-11-20) The Help panel's search and Related list; coach marks the first time a stage opens (`kit/help.coach_mark`, `ui.hints_seen`, Settings → General → Hints). Left: the glossary chapter (definitions in four languages), pictures in the panel, the F1 walk test.
- **Ours now:** the Guide page (Markdown in `resources/guide/<lang>/`, searchable), tooltips, F1 opens the guide.
- **Build:**
  1. Guide paragraphs get stable anchors (`{#photometry-comparison-stars}`); every `Section(help=…)` and stage names
     an anchor; a test checks that every anchor used exists in all four languages.
  2. `HelpPanel` (right side, replaces the Inspector while open): shows the anchored paragraph with its picture,
     "Related" links, "Open the full guide", and a search box. F1 opens it for the control in focus; Shift+F1 turns
     the cursor into "What is this?" for one click.
  3. The grey paragraphs now inside working panels (Calibration's folder explanation, the type-detection text, the
     Models window's model note, Spectroscopy's "In what order?") move into the guide under anchors; the panel keeps
     at most one short line.
  4. A glossary chapter (guide 14) from `resources/i18n/glossary.toml` (ARC-18): every term with one sentence; terms
     in help texts link to it.
  5. First-use hints: a small dismissible coach mark on a stage the first time it is opened ("Click a star to mark
     the target"); "Don't show hints" in Settings.
- **Accept:** no working panel contains a text longer than 140 characters (a test measures labels); F1 on every
  kit control of every window opens a paragraph (a walk test).
- **Files:** `ui/kit/help.py`, `resources/guide/*`, the panels, tests.

### UI-8. Guided tasks  (P2)
**partial** — done (2026-11-12): `kit/guided.py` (a bar at the top of the real area window: step n of m, the text, Show me marks the control for 3 s without covering it, Back / Next / Close) and scripts in `resources/guided/*.toml` (widget = an attribute of the area's page; texts per language, English as fallback); Help → Guided tasks lists them. Tasks (5) "minima to O−C and a third body", (6) "frequencies of a pulsating star", (4) "the orbit of a double-lined binary", (3) "a long-slit spectrum from raw frames to wavelengths" (practice `slit_science.fits` / `slit_arc.fits`), (1) "a night of an eclipsing binary: raw frames to a time of minimum" across Calibration and Photometry (a step may name its own area; Show me raises that window and its stage) (on the practice data) and (7) "plan tonight's eclipses", English and Turkish (Show me brings the tab holding the control forward); a test walks every task's Show me. (2) "an exoplanet transit: raw frames to a timing report" on the practice transit night (`sampledata.make(transit=True)`, written by Help → Practice data into transit/). All seven tasks exist; left: the QTest that completes each by following Show me with real input, which follows the windows of UI-16. (2026-11-20) Every guided step followed by Show me in four languages (`test_every_guided_step_is_followed_by_show_me`); Show me now applies a stage switch's layout before it marks (`kit/guided.py`). Left: German and Spanish step texts (English shown).
- **Why:** "easier than all of them": a newcomer wants "a light curve from my night", not eleven windows.
- **Build:** Help → "Guided tasks": (1) calibrate a night and measure a light curve of an eclipsing binary; (2) an
  exoplanet transit from raw frames to an ExoClock / AAVSO report; (3) a long-slit spectrum from raw to wavelength
  calibrated; (4) a radial-velocity curve and orbit from a set of spectra; (5) times of minimum to an O−C diagram;
  (6) period of a variable from a survey light curve; (7) plan tonight's eclipses. A guided task is a thin overlay
  (a bar at the top: step n of m, what to do now, "Show me" highlights the control, Back / Next) driving the real
  windows — no separate wizard code paths. Each can run on the practice data.
- **Accept:** each guided task is completed by a QTest that only follows "Show me" highlights; in four languages.
- **Files:** `ui/shell/guided/*.py`, `resources/guided/*.toml` (the scripts), tests.
- **Depends on:** the windows it drives (added as each UI-16.x lands).

### UI-9. Tasks, progress, notifications  (P1)
**partial** — done: `kit/tasks.TaskChip` in every area window's toolbar (running count; popover with state, progress, elapsed, estimate from 5 %, Cancel); a Toast in the window when its task finishes. System notification: work longer than 60 s that ends while its window is not in front also gives a desktop notification (`kit/notify.py`, a tray icon made once; Settings → General → Notifications turns it off). The popover's running rows name the phase ("measuring"); a finished task opens to how long each phase took (`Task.timeline`). Left: (done since: a failed task in the popover offers Report a problem…) the primary button as Stop: done in part — the stage's main button that started the work stays disabled and shows its progress ("Measure — 40 %") until it ends; Esc or Cancel stop it (`kit/tasks.HeldButton`). (2026-11-20) The stage's main button becomes "Stop — 40 %" while its task runs; a two-window QTest (two tasks, one cancelled, own chips, one notification for a long task). Done.
- **Ours now:** `engine/tasks.TaskQueue` (progress, cancel), the Tasks dock, status-bar progress of area windows (I2.7).
- **Build:** `TaskChip` in every window (running count; pulses when one finishes); `TaskPopover` (name of the step
  in words, the window that started it, phase text, progress or "working…", elapsed and estimated time, Cancel,
  Details with the timeline of ARC-17); a finished task raises a `Toast` in its window with "Show result" (and a
  system notification when the program is not in front and the task ran longer than 60 s; Settings can turn it
  off); failed tasks stay in the popover with the error and "Report". The stage's primary button shows the progress
  of its own task and becomes "Stop". Estimated time from the step's own progress reports, never a guess before 5 %.
- **Accept:** a QTest starts two tasks from two windows, cancels one, and sees the right chips, popover rows and
  toasts; a 90 s task in the background raises one system notification.
- **Files:** `ui/kit/tasks.py`, `ui/shell/tasks_panel.py`, `engine/tasks.py` (phase and ETA fields), tests.

### UI-10. Plot behaviour standard  (P1)
**partial** — done: every PlotCanvas (the plots the windows show) has the right-click menu Show all, Copy picture, Copy data, Save data…, Publication figure…; a click on a legend entry hides or shows its series. Left: the PlotToolbar of ARC-6's PlotView and the rest, with UI-16 when the windows move to PlotView. (2026-11-20) Measure mode (hold X or the toolbar button: two clicks give Δx, Δy), "Axis limits…" on every PlotCanvas (`ui/plot/limits.py`; an inverted axis stays inverted); `test_measure_two_clicks_and_the_delete_key`, `test_axis_limits_are_read_and_applied_and_keep_an_inverted_axis`. Left: the axis menus (time standard, units), Leave out / Bring back with hollow markers, the toolbar in every window. (2026-11-20, audit) Every PlotView in every area window sits under a PlotToolbar (`plot_box`); the three matplotlib PlotCanvas plots (Plan polar sky chart, posterior corner plot, Images 3-D surface) keep the PlotCanvas menu with "Axis limits…", Copy / Save data, Publication figure; `test_every_plot_has_a_toolbar_and_every_table_a_house_widget` (`tests/test_plot_table_standard.py`) walks all area windows. Empty hint and the busy text come from PlotView itself. Still left: the axis menus (time standard, units), Leave out / Bring back with hollow markers, the listing table of plots, the contact sheet. (2026-11-28) Leave out / Bring back with hollow markers: a series with `SeriesSpec.left_out` is drawn hollow by every PlotView and in the publication figure, and the PlotView right-click menu has "Show left-out points" (`PlotView.set_show_left_out`); the Time series light curve (`PeriodPage.delete_points` keeps the points in `left_out`, `bring_back` by a click in delete mode or Delete over a lassoed / hovered hollow point, both undoable, shown in the time and the folded plot); `test_left_out_points_stay_as_hollow_markers_and_come_back`, `test_left_out_points_are_hollow_in_the_publication_figure`. Left: the axis menus (time standard, units), the listing table of plots, the contact sheet, hollow left-out points in the other windows (O−C keeps its grey points).
- **Build:** on top of ARC-6: the `PlotToolbar` (show all, box zoom, select range, pick points, lasso, measure
  (Δx, Δy between two clicks), export…, publication figure…, pop out); axis menus (time as BJD_TDB − offset / UT /
  phase; flux / magnitude with the y axis inverted for magnitudes; wavelength in Å / nm / µm, velocity space around a
  chosen line); legend with toggles; "Leave out" / "Bring back" for selected points wherever points belong to the
  user's data (undoable, the left-out points stay visible as hollow markers when "Show left-out points" is on);
  consistent markers (points 5 px, error bars 1 px, model 1.5 px); right-click menu with Copy picture, Copy data,
  Save data…, Axis limits…; every plot has a title-less frame (the tab or panel names it).
- **Accept:** a table in this step lists every plot in the program and ticks the standard for each; a QTest per
  window drives select-range and leave-out; publication export of each plot type reviewed in a contact sheet
  (`docs/design/figures.png`).
- **Files:** `ui/plot/toolbar.py`, every plot panel.
- **Depends on:** ARC-6.

### UI-11. Table behaviour standard  (P1)
**partial** — done: the count line under every TableView ("12 of 48 rows · 2 selected"); numbers in the monospace font. The header menu: sort ascending / descending by the column clicked, fit its width, show or hide columns. Digits by error: a float column with a partner `<name>_err` (`_error`, `_sigma`, `_e`) shows the decimals two significant digits of its error allow, the error column itself to two digits (the copy keeps every digit). Left: the row-action words, time standards in headers, (an empty table now says "No rows yet" or that the filter keeps none, in its count line). (2026-11-20) One wording for row actions (`row_word`, `TableView.set_row_actions` in the right-click menu), the time standard in a column's header; `test_row_actions_use_one_wording_and_act_on_the_selected_rows_and_time_standard_shows`. Left: each window's actions wired to it. (2026-11-20, audit) The Plan night tables (`plan_tables._table`) are DataTables now (filter, sort, column menu, copy, export). Still plain QTableWidget (with the window's copy / export menu only, no count line, header menu or row actions) in the windows plan (targets), observe (exposures), calibrate, image, astrometry, photometry (frames, stars, measures), timeseries, spectroscopy (lines), orbits and automation; they carry edits, clicks and per-cell marks of their window and move to TableView one by one; the same test lists the windows (`PLAIN_TABLES`) so a new plain table fails it. (2026-11-20) Moved to TableView: the Time series windows' tables (`varfind_page` stars, `frequency_page` frequencies and maxima), the spectrum tools' lines (`spectrum_tools._show_lines`) and the visual orbit's elements (`visual_orbit_tab.show_orbit`); timeseries left `PLAIN_TABLES`. (2026-11-20) The RV table (`VelocityTab`) is a TableView; the editable guesses tables (`ReduceTab`, `EchelleTab`) and the orbits' parameter table (`ModelsPage`, Fit tick boxes kept as cell widgets, undo unchanged) sit in a `DataTable` made with `DataTable.prepare` (editable, no sorting so rows keep their cells and widgets); spectroscopy and orbits left `PLAIN_TABLES`; `test_prepared_data_table_keeps_cells_and_widgets_in_place`, the RV table read in `test_sb2`. (2026-11-20) Observe (exposures), Calibrate (frames), Images (`image_header_table.header_frame`, the FITS keywords) and the moving-object table (`moving_dialog`) sit in a `DataTable` made with `DataTable.prepare` (cell widgets, edits, double-clicks, Delete key and undo unchanged; the page still points at the inner QTableWidget); observe, calibrate, image and astrometry left `PLAIN_TABLES`, `test_every_plot_has_a_toolbar_and_every_table_a_house_widget`. (2026-11-21) Plan (targets `PlanPage.table`, night events `events`, schedule `schedule_table` via `_read_only`), Photometry (`frame_table`, `star_table`, `meas_table`) and Automation (`settings_table`) sit in a `DataTable` made with `DataTable.prepare` (pages still point at the inner QTableWidget; the Frames tab and the settings form anchor on `table.parent()`; the schedule table hides its filter line to keep the Plan window short); `PLAIN_TABLES` is gone and `test_every_plot_has_a_toolbar_and_every_table_a_house_widget` now asserts no plain QTableWidget remains in any area window. No time-standard header added: none of these columns states its standard in code. (2026-11-27) Time standards in headers: the Exoplanets Mid-times table names the scale its fitted files state (`exoplanets_midtimes.tc_header`: "Tc (BJD_TDB)", "Tc (BJD)" when a file states none or they differ); `test_tc_header_names_the_scale_the_files_state`. Other time columns already name theirs (photometry measures, frames, RV, converter, moving) or have no standard in code (Time series maxima, O−C minima table: only the pasted text may name it). Left: the same two.
- **Build:** on top of ARC-8: header menu (sort, hide, columns…, fit width); filter line with examples in its
  placeholder; a count line ("48 frames, 3 left out, 2 selected"); row actions in a context menu, the same words
  everywhere ("Leave out", "Bring back", "Show in the image", "Show in the plot", "Copy"); numbers right-aligned in
  the monospace font with the digits their errors justify; times shown with the standard in the header; empty table
  = `EmptyState`.
- **Accept:** a table in this step lists every table in the program and ticks the standard; QTests for filter,
  columns and export in each window.
- **Depends on:** ARC-8.
- **Files:** `ui/kit/table.py`, every window's table panels, `tests/ui/test_table_standard.py`

### UI-12. Keyboard  (P1)
**partial** — done: Help → Keyboard shortcuts (Ctrl+/) in every area window, a searchable sheet read from the actions (`kit/shortcuts.py`); a test finds a key given to two actions of a window (it found the text-size keys twice in every area window: fixed). Image keys: + / − zoom, 0 fit, 1 100 % in every image viewer. [ and ] step the frames (Images, Photometry). i inverts, n turns North up. b blinks (Photometry: the series; Images: the blink window); a over a plot shows all (matplotlib's o, p, h stay). F5 presses the stage's main (primary) button — Photometry marks one per stage —, Esc stops the window's running work (enabled only while work runs, so fields and popups keep Esc). Spectrum tools take IRAF splot's keys over the plot (`ui/spectrum_keys.py`: w w a window, m centre it, f measure, c a continuum point, d delete the nearest; each one undo step; listed in the plot's tooltip). Settings → Shortcuts: every action named after its method (`kit/shortcuts.own_keys`) takes the user's keys, kept in the settings (`shortcuts`), applied at once in every open window and at the next start; a dot puts the program's keys back. **Changed from the plan:** the map lives in the settings, not a separate shortcuts.toml. Left: the other plot keys (R range, L lasso, Delete leave out). (2026-11-20) Plot keys from one table (R, L, Z, X held; Delete → `key_pressed("delete")`). Left: binding Delete to leave-out per window, the plot keys on the shortcut sheet. (2026-11-20) Delete over the plot leaves out points in the Period (lasso or the hovered point, one undo step) and Photometry windows; the plot keys on the shortcut sheet. (2026-11-27) Nothing small and fully specified left in the list (the Delete binding for the other windows names no target), so nothing added.
- **Ours now:** shortcuts set one by one in `main_window.py` and `area_window.py` (Ctrl+K, Ctrl+Z / Y, text size, F1).
- **Build:** one map for all windows (file `resources/shortcuts.toml`, shown by Help → "Keyboard shortcuts"
  (Ctrl+/) as a searchable sheet, and editable in Settings): Ctrl+O open, Ctrl+S save session, Ctrl+E export,
  Ctrl+Z / Ctrl+Y, Ctrl+K find an action, F1 help, F5 run the stage's primary action, Esc stop / cancel, Ctrl+W
  close window, Ctrl+, settings, Ctrl+1…9 stages, F9 / F10 / F11 panels, Ctrl++ / Ctrl+− text size; image keys
  (space-drag pan, `+` / `−` zoom, `0` fit, `1` 100 %, `[` / `]` previous / next frame, `B` blink, `I` invert,
  `N` north up, the `imexamine` letters of ARC-7); plot keys (`A` all, `R` range, `L` lasso, `Z` box zoom, Delete
  leave out); spectrum keys (IRAF / PypeIt habit: `m` mark a line, `f` fit, `d` delete, `w` window, `c` continuum
  point). A test finds duplicate shortcuts within a window and missing ones for every menu action marked as
  frequent.
- **Accept:** the sheet lists every shortcut in four languages; every stage of every window can be completed without
  the mouse except where a position on an image or plot must be chosen.
- **Files:** `resources/shortcuts.toml`, `ui/kit/shortcuts.py`, tests.

### UI-13. Settings in one place  (P1)
**partial** — done: Settings → All settings… (Ctrl+,) — `ui/settings_window.py`: General (language, look, text size, Expert mode), Profiles (site, camera, observer), Processing (device), Online services (offline, Earth-rotation tables); a search field over labels and descriptions; changes apply at once and the menus agree. Time (the camera clock's offset from UTC, through Calibration's own field). Plugins (the folder, the plugins waiting to be allowed, asked about one by one) and Advanced (the settings and logs folder) added. Shortcuts added (UI-12). Left: Files, units, Data packs; Reset per setting for the settings with a program default (a dot while changed, a click resets; `FormRow(default=…)`). A test checks that every settings key read is shown or listed as internal (`INTERNAL`, `SHOWN`); Toolbar text added to General. (2026-11-20) A Files category (the observing download folder), Hints, reset dots on numeric profile fields. Left: units and data packs (nothing reads them yet).
- **Ours now:** a Settings menu (language, look, processing device) and settings scattered in pages.
- **Build:** one Settings window (Ctrl+,) with a search field and categories: General (language, look, text size,
  Basic / Expert, hints), Profiles (ARC-16: sites, equipment, observer), Processing (CPU / GPU, threads, memory cap,
  cache), Files (default folders, output naming patterns, FITS writing: float32 / compression), Time and units
  (default time standard shown, flux or magnitude, wavelength unit, air / vacuum), Online services (offline mode,
  mirrors, cache size, time-table refresh), Data packs (ARC-20), Shortcuts, Plugins, Advanced (logs, reset).
  Every setting has a one-line description and "Reset"; changes apply at once and are undoable inside the window.
  The Settings menu of each window opens this window at the right category.
- **Accept:** every key in the settings file appears in the window or is listed as internal in a test; search finds
  a setting by any word of its label in four languages.
- **Files:** `ui/shell/settings/*.py`, tests.

### UI-14. Windows on several monitors  (P2)
**partial** — done: every Window menu (the main window's and each area window's) lists the open windows and adds "Tile side by side" and "Bring all windows to this screen" (`kit/screens.py`; the screen of the window the menu belongs to); a window whose title bar is on no screen at start comes back (`kit/window.on_screen`). Closing the start window while area windows are open hides it (back from any Window menu); the program ends with the last window or by File → Quit. Left: floating result tabs remembering their screen, the two-screen QTest (offscreen with two screens needs its own process). (2026-11-20) Floating tabs and windows remember their place per screen arrangement (layout_memory). Left: the two-virtual-screen QTest (needs a real two-screen setup).
- **Build:** Window menu: list of open windows, "Tile side by side", "Bring all to this screen"; floating result
  tabs remember their screen; the Photometry image and its plot can live on two monitors; closing the start window
  with area windows open asks nothing and keeps them (the program ends when the last window closes, or by File →
  Quit).
- **Accept:** QTest on two virtual screens (offscreen platform with two screens) moves, restarts and finds the
  windows where they were.
- **Files:** `ui/kit/window.py`, `ui/shell/menus.py` (Window menu), `tests/ui/test_multi_screen.py`

### UI-15. The gallery test: every window, every language, every theme  (P1)
**partial** — done: `tools/ui_gallery.py` opens every area window in en / tr / de / es × dark / light at 1366 × 768 (90 s), saves the screenshots and measures cut labels and buttons; `tests/test_gallery.py` fails on a cut text (Linux) and names the widget. Seen in the sheets: no cut text; German and Spanish show English where not translated yet (ARC-25). (2026-11-21) Contact sheets (`contact_sheet`: `gallery/<area>-<lang>.jpg`, dark and light side by side), `overlapping` (labels / buttons / fields of one layout covering each other), `small_main_view` (central widget under 55 % of the window width, as test_anatomy; only windows with stages), `untranslated` (visible text equal to an English source whose finished translation differs), the CI artifact (`GALLERY_OUT` set in ci.yml, the test writes the sheets, `upload-artifact` "gallery"); `tests/test_gallery.py::test_overlap_main_share_untranslated_and_contact_sheet`. The new check found astrometry's "Solve" toolbar button untranslated (`t(...)` alias in `area_menus.astrometry` that lupdate does not read; fixed). Left: the focus-chain and FormRow-alignment checks of the kit (UI-3), the owner's own screen and Windows fonts, the agent's written note under each step.
- **Ours now:** `tests/test_layout_fits.py` (every page fits a small window, four languages × two themes), `tools/guide_screenshots.py`.
- **Why:** rule R7 needs to be cheap, or it is skipped.
- **Build:** `tools/ui_gallery.py`: opens every window with its practice data in a fixed state per stage, grabs
  1366 × 768 screenshots for en / tr / de / es × dark / light, writes contact sheets (`gallery/<area>-<lang>.jpg`)
  and a JSON of measurements (cut texts found by comparing each label's size hint with its geometry; overlaps;
  main-view share; untranslated strings = equal to English while a translation exists). CI runs it on Linux and
  uploads the sheets as an artifact; `tests/ui/test_gallery.py` fails on any cut, overlap or untranslated string.
  The agent looks at the sheets of the windows it changed and writes under its step what it saw.
- **Accept:** the tool runs in < 4 min; a deliberately long German label makes the test fail and name the widget.
- **Files:** `tools/ui_gallery.py`, `tests/ui/test_gallery.py`, CI.

### UI-16. The windows  (P1; each sub-step is the first step of its area in stage S2)

Each sub-step: rebuild the window on the anatomy with the kit, the session store (ARC-5), `PlotView`, `ImageView`,
`TableView`; move every existing function to its stage, menu and toolbar (nothing is lost: the agent first lists
every control of the old window under the sub-step and ticks each one off as it finds its new place); update "Where
everything is"; guide chapter rewritten around the stages with new screenshots; the old page class is deleted only
after the owner has tried the new window (until then View → "Classic layout" opens the old one).
**Accept for every sub-step:** the anatomy test; the gallery test; a QTest of the window's main workflow on its
practice data and on one real set from `data/`; every old control accounted for; old sessions open.

#### UI-16.1 Photometry
**partial** — done: the steps are stages (rail: Images, Stars, Apertures, Measure, Light curve, Timing, Report, Other tools — the results' Plot, Minimum and Export tabs became the last stages, the results panel keeps the light curve, Stars and Measurements; each stage's controls and its guide topic; the page's step logic moves the rail: a step done gets ✓, the next opens by itself, a stage the user went back to stays). The inspector: a click on the image shows the star's role, position, peak (saturated), sky, net counts, S/N and FWHM. Rail names on hover as tooltips; pinned, it widens the panel instead of squeezing it. The frame list (use box, time, FWHM, sky; bad and partial frames coloured with their reasons) is the Frames results tab. Done since: the Checks result tab (PHO-33, with the next-night advice of PHO-43); the toolbar of the sketch (Leave out added, 2026-11-13). The Field stage (2026-11-14, the owner's go-ahead): `ui/photometry_field.py` between Images and Stars — Identify the field and the AAVSO sequence, the answer and the variable list, and what is drawn on the first frame (variables, the solution's Gaia stars); its rail mark turns ✓ when the field is identified (test_ui). (2026-11-20) Each automatic choice shown with its reason in its stage (`ui/photometry_choices.py`: the target from OBJECT, the comparison stars, the radii); the stage "Timing and fit"; `tests/ui/walks/test_walk_photometry.py::test_practice_night_in_seven_clicks`: the practice night in 4 clicks (load, target, Measure, Time of minimum; the Field stage not counted: the practice frames have no plate scale). The Images stage's summary (frames, span, filters, calibrated from CALB / CALD / CALF, bad frames; `ui/photometry_images.py`), Multi-plot as its own results tab (`ui/photometry_multi.py`), target by name in the Field stage (SIMBAD through `planning.resolve`, cached; `ui/photometry_name.py`); `tests/test_photometry_stages_more.py`. (2026-11-21) Draggable radius lines: the aperture, sky-inner and sky-outer lines of the Apertures profile plot can be dragged (`ui/aperture_lines.ApertureLines`, snapped to 0.1 px, clamped aperture < inner < outer); the fields stay the source of truth and a field change redraws the lines; `tests/ui/test_aperture_lines.py`. (2026-11-21) The Images window's image tools on the Photometry image: Move (default, a click marks stars), Star, Area and Line with their radius / line-width row, and a Measurements inspector tab (Information, Graph) beside the star inspector; the measuring code is the Images page's own (`ui/photometry_tools.attach` points an unseen `ImagePage` at Photometry's viewer; `PhotometryPage._clicked` ignores clicks while a tool other than Move is chosen); `tests/ui/test_photometry_image_tools.py`. (2026-11-21) The results dock holds results only: the plot choice, detrending and export tabs were already the Light curve, Timing and Report stages; the last controls in it, the next-step buttons (Period search, Fit an eclipse or transit model, which saves the CSV) moved to the Report stage (`ui/photometry_results.attach`); the plot's own toolbar (export data, publication figure) and the Measurements table's CSV button stay with what they export; `tests/ui/test_photometry_results_dock.py`. Left: nothing of the Left list.
```
rail            stage panel (example: 3 Stars)          main: image                         inspector
1 Images        Target and comparison stars    ?       ┌───────────────────────────────┐   Star C2
2 Field         ◉ Mark: Target  Comparison  Check      │  frame with rings and labels  │   Gaia DR3 36151…
3 Stars  ●      Suggest comparison stars  [Suggest]    │  T1 ◎   C1 ◎  C2 ◎   K1 ◌     │   G 12.31  BP−RP 0.84
4 Apertures     ▸ Comparison-star rules (PHO-17)       │                               │   V 12.52 (GSPC)
5 Measure       Star list: [Open…] [Save…]             └───────────────────────────────┘   not variable (VSX)
6 Light curve   ─────────────────────────────          [◀] ───────●─────────── [▶] 17/48    peak 31 204 ADU
7 Timing, fit   T1 + 4 comparison + 1 check            results: [Light curve][Multi-plot]  FWHM 3.1 px
8 Report        [ Next: apertures → ]                  [Measurements][Stars][Frames][Checks] profile ▁▃█▃▁
```
- Stages: **1 Images** (PathField; calibrated? badge and optional calibration with the Photometry defaults; frame
  quality summary: n frames, time span, filters found; bad frames listed with reasons). **2 Field** (plate solution
  status, OBJECT check, target by name or click, catalogue overlay toggles; "Solve again" options folded).
  **3 Stars** (above). **4 Apertures** (radii with `auto`; rule choice; profile plot of the target with the three
  radii as draggable lines; "Scale radii with seeing"). **5 Measure** (sky method, noise model, time-stamp
  convention, other radii — all folded but the first; primary "Measure the light curve"). **6 Light curve** (leave
  out points / frames, detrend with BIC, flip, spline, normalisation range, binning). **7 Timing and fit** (time of
  minimum by Kwee–van Woerden / Mikulášek / polynomial / Gaussian / Lorentzian / bisector / trapezoid / exact model (PHO-26), "Compare methods" table; send to O−C; fit a transit with
  priors). **8 Report** (exports: CSV / ECSV, AAVSO Extended, AAVSO Exoplanet, ExoClock, ETD / VarAstro, TFOP
  package (PHO-27), measurement table, figure).
- Results dock tabs: Light curve (with comparison–check curve below it), Multi-plot, Measurements, Stars (table
  with scatter, weights, catalogue magnitudes), Frames (table: use, time, FWHM, sky, airmass, shift, flags; a click
  shows the frame), Checks (diagnostics of PHO-38).
- Under the image: the frame slider with play; the image toolbar (levels, zoom, layers: apertures / names /
  catalogue / variables / bad pixels).
- Toolbar: Images…, Previous, Next, Blink, Suggest comparisons, Radii, Measure, Leave out, Time of minimum, Export.
- **Files:** `ui/photometry/` (see PHO-W)

#### UI-16.2 Calibration
**partial** (2026-11-20: the window has the stages Frames (folders, Scan, the frames' summary), Calibrate
(where to write, rejection, options, the result) and Continue (Photometry, stacking with its options one per row)
beside the list of frames and its problems; the step guide moves the rail; test_the_calibration_window_has_stages.
(2026-11-21) The rail is now Frames, Check, Masters, Calibrate, Review, Continue (`ui/calibration_checks.py`): Check
= the groups tree (`calibration/groups.group`), "Check the frames" marks the frames that stand apart (`outliers`),
a click shows a frame's median, noise, min, max, saturated share, "Leave out the marked frames" is an undoable edit;
Masters = the masters to make and "Choose the masters by hand…"; Review = the masters' quality table (CAL-6, amber
where a check fails) and the frames left out with reasons; the Plan result tab: per filter and exposure of the lights
the bias, dark and flat each gets (automatic shows the match, each cell a choice kept in `master_choices`, missing
pieces in amber with what is done instead); test_the_calibration_check_masters_plan_and_review. (2026-11-21) `ui/calibration_preview.py`: Check shows the clicked frame's image and histogram (`FramePreview`, read
on click, on the UI thread, below the groups, errors by `messages.translate`); Review has the Raw / Calibrated / Blink
pane (`BeforeAfter`, `pair_of`: a calibrated file is named after its light); the Problems result tab mirrors the frames
list's note box; test_the_calibration_preview_and_blink. (2026-11-21) The Report and Log result tabs (`ui/calibration_report.py`: `report_text`, `show_report`, `start_log`, `log_update`; `area_actions.calibrate` feeds the Log from the task's updates): Report = the run's result as text (images calibrated, masters written, arc frames, dark scale range) and the frames the Check stage left out with reasons; Log = the run's progress messages as the task sent them (time, share done, phase); `test_report_text_lists_the_result_and_the_frames_left_out`, `test_the_window_has_report_and_log_tabs_that_follow_a_run` (tests/ui/test_calibration_report.py). Shortcut: the Log is kept for the window's session only, and the result holds no per-frame statistics. (2026-11-21) Saved report and History: Review has "Save report…" (`calibration_report.save_dialog`, `save_file`), and after each run the report is written to `calibration_report.txt` in the output folder over the previous run's file (`save_beside_frames`, named in the Review line, tooltip says so); the History result tab (`ui/calibration_history.py`: `history_lines`, `make`, `refresh`) shows the project's `calibration.*` runs and the app.log lines about calibration written since the window opened, with a filter line, read-only, hidden until it has a line, refreshed when a run finishes; `test_history_lines_hold_calibration_runs_and_this_sessions_log_lines`, `test_the_history_tab_is_hidden_until_it_has_lines_and_filters`, `test_the_report_is_saved_by_hand_and_beside_the_frames`, `test_refresh_reads_app_log_and_the_project` (tests/ui/test_calibration_report_log.py). Shortcut: History is read when a run ends, not on opening a project. (2026-11-21) The Continue stage opens with three cards (`ui/calibration_cards.py` `make`: Measure in Photometry, Stack, Open in Images; a card presses the page's own button, so the hand-over is the same, and the two old buttons are hidden; Images is the new `images_requested` signal -> `AreaActions.send_to_images`); enabled after a result; `test_cards_are_disabled_until_a_result_exists`, `test_a_card_click_does_the_hand_over_of_the_old_button` (tests/ui/test_calibration_continue_cards.py). Shortcut: no "Reduce in Spectroscopy" card, Spectroscopy has no loader for calibrated frames to hand them to. Left: threaded statistics, the Spectroscopy card, the three-clicks walk on the practice night)
```
1 Frames        Frames of the night            ?       ┌ groups ─────────────────────┬ preview ─────────┐
2 Check  ●      [ Add folders… ] (drop here)           │ ▾ Bias  20  1×1  −10 °C     │  selected frame  │
3 Masters       Lights 48 · Bias 20 · Dark 10 · Flat   │ ▾ Dark  10  60 s  −10 °C    │  or master with  │
4 Calibrate     V 12, R 12                             │ ▾ Flat V 12   Flat R 12     │  statistics:     │
5 Review        ⚠ 2 problems to look at                │ ▾ Light V 24  NY Vir        │  median, noise,  │
6 Continue      ▸ How frame types are recognised       │ ▾ Light R 24  NY Vir        │  histogram       │
                [ Next: build the masters → ]          └─────────────────────────────┴──────────────────┘
                                                       results: [Plan][Problems][Report][Log]
```
- **Plan** tab: one row per group of lights: which bias, dark (scaled?), flat it will get and why (temperature
  difference, exposure, date), each cell a choice the user can change; missing pieces in amber with what will be
  done instead.
- **5 Review:** before / after blink of one light, the masters' quality table (CAL-6), frames left out with reasons.
- **6 Continue:** "Measure in Photometry", "Reduce in Spectroscopy", "Stack", "Open in Images" as cards.
- **Files:** `ui/calibration/` (see CAL-W)

#### UI-16.3 Spectroscopy
**partial** — done (2026-11-21): the window on stages (`ui/spectro_stages.py`: `spectroscopy_stages`, called from `area_menus.spectroscopy`; `SpectroscopyPage.window_parts` returns the jobs' columns): one rail, each job showing only its own stages (Overview = instrument profile and the folded order of work, in every job; long slit and échelle: Frames, Extract, Wavelengths from the existing columns by `boxes_from_column`; Telluric, Velocities, IFU cube, Spectrum tools one stage each); the job stays the toolbar switch and the Job menu, a stage of another job brings that job forward; the step guides of Reduce and Echelle hide and tick the rail. Nothing removed. The steps dock no longer asks 572 px: check boxes wrap (`fit_width`), the profile row flows, the tools' three-column grids lay out in two (`two_columns`), a button wider than a stage breaks into two lines (`_two_lines`); `small_main_view` now applies to this window (56 % in en / tr / de / es). Tests: `test_the_spectroscopy_window_has_stages_per_job`, `test_opened_folds_fit_the_window`, `tests/ui/walks/test_walk_spectroscopy.py`. (2026-11-21) The job switch is a `Segmented` in the toolbar (`spectro_stages.job_switch`, called from `area_windows.spectroscopy_window`; the Job menu keeps the actions; the tabs stay the owner of the current job), and the inspector shows the selected arc line (`ui/spectro_inspector.py`: `line_rows`, `line_inspector`: order, pixel, wavelength, line list, the fit's residual and left-out flag, the fit's lines, degree and rms, all read from the page's table and result; hidden until a row is chosen and outside the long-slit and échelle jobs); `test_the_job_switch_is_a_segmented_that_follows_the_tabs`, `test_line_rows_hold_the_line_and_the_fit`, `test_the_inspector_follows_the_selected_row_and_the_job` (tests/ui/test_spectro_inspector.py). Shortcut: the échelle row has no residual (its fit lines are keyed by order). (2026-11-21) The instrument profile is also a toolbar combo (`spectro_stages.profile_switch`: the page's own profile list as its model, both kept in step with signals blocked while syncing; the Overview one stays), and Telluric (Spectra, Correct), Velocities (Method, Measure, Table) and Spectrum tools (Measure a line, Change the spectrum, Stellar parameters) are several stages each (`spectro_split.split_job` over `boxes_from_column`); `test_the_toolbar_profile_combo_and_the_overview_one_agree`, `test_split_jobs_have_stages_and_keep_every_widget` (tests/ui/test_spectro_stages_more.py). (2026-11-21) The inspector also follows the Spectrum tools' lines table (`ui/spectro_tools_inspector.py`: `tool_rows`, `window_data`, `tool_plot`; `SpectrumToolsTab.measures` keeps each row's result and the data in its window): the file, centre, FWHM, EW, depth, line flux, S/N, V/R with their errors, the profile and window, and a small plot_box with the fitted curve and continuum the result holds (the result has the fitted curve, not profile parameters) over the data around the line; rows from the open spectrum and from a batch keep their data, a row without data shows the fitted curve alone; hidden until a row is chosen and outside the Spectrum tools job; `test_tool_rows_hold_only_what_the_result_holds`, `test_the_inspector_shows_the_chosen_measured_line` (tests/ui/test_spectro_tools_inspector.py). Left: none of the two listed items.
- The toolbar starts with a job switch (Segmented with icons): **Long slit · Échelle · Spectrum · Velocities ·
  Orbit · Parameters · Cube**; each job has its own rail.
```
Long slit:                                             ┌ 2-D frame: trace, aperture, sky bands drawn ───┐
1 Frames        Trace and apertures            ?       │                                                │
2 Trace  ●      Spectrum at: ◉ brightest ○ row [  ]    ├ profile across the slit (drag the limits) ─────┤
3 Sky           Aperture ±[ 5.0 ] px  auto ◉           ├ extracted spectrum / arc with marked lines ────┤
4 Extract       Sky bands [15–25] px both sides        └────────────────────────────────────────────────┘
5 Wavelengths   ▸ More options                         inspector: Lines table · Fit · Residuals
6 Flux, sky     [ Extract the spectrum ]               (pixel → wavelength fit and residuals always in view
7 Save                                                  while identifying, as PypeIt Identify)
```
- Échelle rail: Frames · Orders (on the flat) · Scattered light · Extract · Wavelengths (2-D) · Blaze and merge ·
  Save. Spectrum rail (one or several 1-D spectra overlaid, one active): Open · Continuum · Lines (equivalent
  widths, fits) · Combine / arithmetic · Telluric · Flux · Save. Velocities: Spectra · Template or mask · Method
  (CCF, TODCOR, broadening function, LSD) · Measure · Table. Orbit: Velocities · Fit · Uncertainties · Report.
  Parameters: Spectrum · Method (grid fit, equivalent widths, classification) · Result.
- Instrument profile chooser in the toolbar (from ARC-16), not a row in the panel.
- **Files:** `ui/spectroscopy/` (see SPE-W)

#### UI-16.4 Light curves and period
**partial** — 2026-11-27: the peak table has the S/N column too (`significance.peak_snrs`, output `peak_snr` of `timeseries.period`: Breger 1993 as the Frequencies table, a sinusoid fitted at each peak over the mean residual spectrum within ±1 c/d; Lomb–Scargle/GLS only, "—" with a tooltip otherwise; below 4 marked `saturated` with the Breger tooltip by `lightcurve_fold.peak_marks`; `test_period_step_gives_the_peak_snr_and_fap`, `test_peak_table_shows_snr_and_marks_the_weak_ones`). 2026-11-21: the peak table has a FAP column (`significance.peak_faps` via `frequency_faps`, output
`peak_faps` of `timeseries.period`, `lightcurve_fold.peak_table`/`fap_text`): scientific below 0.001, "—" with a
tooltip for methods other than Lomb–Scargle/GLS (`test_peak_fap.py`). 2026-11-20: the Period search tab's column as the stages Data, Clean, Search beside the three
plots (the stage dock hides on the Frequency and Variable-search tabs; the load button's text shortened to fit in
every language; test_the_light_curves_window_has_stages). 2026-11-14: a click on a periodogram peak folds at the highest peak there; the ×2 and ÷2 aliases are drawn dotted; ← → step to the neighbouring peaks (test_ui). (2026-11-21) The rail now also has Frequencies and Variables (`ui/lightcurve_stages.py`: `light_curve_stages`, called from `area_menus.timeseries`; `stage_boxes.period_stages(extra=)`): the two tabs' whole columns are one stage each, a stage of another tab brings that tab forward, choosing a tab shows its first stage, the stage dock stays on every tab, their step guides are replaced by the rail (second step done ticks the stage); `test_the_light_curves_window_has_stages`. (2026-11-21) The stages Fold (the phase-bins field moved from Search, Next / Previous peak buttons = the ← → keys) and Report (Save light curve moved from Data, Copy the peak table) and the peak table in the inspector (`ui/lightcurve_fold.py`: `fold_stage`, `report_stage`, `peak_inspector`, `peak_table`; a `TableView` of the ten highest periodogram peaks, hidden until a search; a click on a row folds there); `test_peak_table_lists_local_maxima_highest_first`, `test_fold_and_report_stages_and_the_peak_table` (tests/ui/test_lightcurve_stages.py). (2026-11-21) The frequencies table of the Frequencies tab has FAP and S/N columns (S/N was already there; `significance.frequency_faps`, Baluev 2008 via Astropy on the data's LS power, added as `fap` to each row of `frequencies_step`; S/N below 4 marked with the `saturated` role and a Breger tooltip; `ui/frequency_page.py`; `tests/test_fap_snr.py`). (2026-11-21) The frequencies table has a Note column: `timeseries/combinations.py: combination_notes` (within 1.5/T, Loumos & Deeming 1978, of n·f_i n=2..5, f_i ± f_j, f_i ± k·1.0027 c/d k=1,2; earlier = stronger; always listed, worded "possible"), added as `note` to each row of `frequencies_step`; `tests/test_freq_combinations.py`. (2026-11-27) The shared selections: leaving points out (lasso/click/Delete, in the time plot or the folded plot) already removes them from the page's one `time`/`flux`/`err` lists that every plot is drawn from, so they are gone from all; Undo edits restores them (no separate Restore button). A periodogram older than the points in use is marked "(out of date: points were left out)" on its axis until the next search (`PeriodPage._period_label`, `_searched_n`); `test_points_left_out_leave_the_data_of_every_plot_and_the_periodogram_is_marked_stale` (tests/ui/test_lightcurve_stages.py). Shortcut: a left-out point is deleted, not masked, so "Restore all" is Undo edits (also undoes binning).
```
1 Data   ●      Light curves                   ?       ┌ light curve (time) ─────────────────────────────┐
2 Clean         ☑ TESS s14  18 512 pts  120 s          ├ periodogram (frequency or period axis, window)──┤
3 Search        ☑ TESS s15  17 944 pts                 ├ folded curve (phase), binned mean overlaid ─────┤
4 Fold          ☐ ASAS-SN V    612 pts                 └─────────────────────────────────────────────────┘
5 Frequencies   [Open…] [Download…] [From Photometry]  inspector: peak table (period, power, FAP, S/N,
6 Report        [ Next: clean → ]                      harmonic / alias notes)
```
- A click on a periodogram peak folds at once; arrow keys step to neighbouring peaks and aliases (×2, ÷2, ±1 d⁻¹
  marked). The three plots share selections (points left out in one disappear in all).
- **Files:** `ui/lightcurves/` (see PER-W)

#### UI-16.5 O−C
**partial** — the window has the stages Minima, Ephemeris, Model, Fit and report beside the O−C diagram
(0.3.19, test_the_oc_window_has_stages). 2026-11-14: "Minima table…" after a fit (`ui/oc_minima.py`: time, error, kind, source, epoch, O−C, residual; sortable, copyable; test_oc_models). The editable table replacing the text box is left. (2026-11-21) Stages Minima, Ephemeris, Model, Uncertainty (the MCMC controls), Fit and report (`ui/oc_stages.py` `oc_stages`, moved from `stage_boxes`); the results tabs "Minima" (time, error, kind, source, epoch, O−C, residual) and "Parameters" (the fit table's values and errors) under the diagram, marked "(out of date)" when the minima, T0, period or model change after a fit (`test_the_oc_window_has_stages`, `test_the_oc_window_results_tabs_and_stale_mark`). Shortcut: the Minima tab and its table are kept out of the Tab chain (a tab behind the front one has a stale geometry; "Minima table…" has the full keyboard use). (2026-11-21) The editable minima table under the paste box (`ui/oc_minima_table.py`: `add_minima_table`, `fill`, `minima_for_fit`, `as_text`; columns Use ☑, Time, Error, Type, Source, Weight; the text box and the Paste button fill it through `parse_minima`, keeping Use and Weight of times already there; the fit reads the ticked rows and takes a weight w as error / sqrt(w); `tests/ui/test_oc_minima_table.py`). (2026-11-21) The Correlations result tab, added at the first fit (`ui/oc_correlations.py` `show_correlations`; |r| > 0.9 cells marked with a tooltip, read-only, marked out of date like the others): the engine keeps `correlation` {names, matrix} on `ephemeris.Fit` (from the covariance, T0, P, Q) and in `fit.mcmc["correlation"]` of the LTTE / apsidal fits (`oc_uncertainty.correlation_dict`, np.corrcoef of at most 2000 posterior draws of the physical parameters); an LTTE / apsidal fit without MCMC has no matrix (its covariance is in internal parameters) and the tab stays empty (`tests/test_oc_correlations.py`). (2026-11-21) The count line ("86 minima · 61 primary · 25 secondary") and the time-standard line under the minima table, updated on every change of the text (paste, box, Load): a named standard is shown, HJD without a scale reads "HJD (UTC assumed) ⚠" (the ARC-15 item 4 rule, `hjd_scale_unknown`), no standard reads "not stated ⚠", both with a tooltip (`ui/oc_minima_table.py` `show_summary`; `tests/ui/test_oc_time_standard.py`). (2026-11-27) The year axis over the epoch axis: `ui/oc_years.py` `year_ticks` / `year_axis` (round years, step 1–100 yr for 3–8 ticks, tick epoch = (JD of 1 Jan − T0) / P; none when T0 is not a full JD) fill the O−C panel's `top` axis in `_draw_oc` (`tests/test_oc_years.py`; the top axis itself in both outputs: `test_a_second_x_axis_along_the_top_in_both_outputs`). (2026-11-27) The "Send the ephemeris to Planning" button in Fit and report (`ui/oc_to_planning.py`; `tests/ui/test_oc_to_planning.py`). (2026-11-27) The Method column (CCD, pe, pg, vis or empty; `parse_minima` reads it from a separate token, also visual / photographic / photoelectric, nothing else; `Minimum.method`; last column of the table, editable, kept when the text changes; `as_text` writes it back) and the "Weight by method" checkbox under the table (`weights_by_method`; a row with no method keeps its error's weight); symbols by method in the diagram when a row has one: vis + / x, pg ◆ / ▲, others ● / ■, one series (and legend entry) per present (kind, method) (`ui/oc_symbols.py` `point_series`; `tests/ui/test_oc_minima_table.py`). Left: the guide chapter and screenshots; the owner's try-out.
```
1 Minima  ●     Times of minimum               ?       ┌ O−C diagram (epoch and year axes; symbols by ───┐
2 Ephemeris     [Open…] [Paste] [From databases…]      │ kind: primary ●, secondary ○; by method: colour)│
3 Models        86 minima · 61 primary · 25 secondary  ├ residuals of the model ────────────────────────┤
4 Uncertainty   time standard: HJD (UTC assumed) ⚠     └─────────────────────────────────────────────────┘
5 Report        [ Next: ephemeris → ]                  results: [Minima table][Parameters][Correlations]
```
- The minima table replaces the text box: time, error, kind (I / II), method (CCD, pe, pg, vis), source, weight,
  use ☑, epoch, O−C, residual; editable; sortable; paste from the clipboard in any common layout.
- **Files:** `ui/oc/` (see OC-W)

#### UI-16.6 Models (binary stars)
**partial** (2026-11-20: the eclipsing-binary tab's column as the stages Data, Parameters, Fit beside the
curve and its model, the buttons one per row; the stage dock hides on the Visual binary tab;
test_the_models_window_has_stages. (2026-11-21) The column re-split into the stages Data, System (the one parameter table), Stars (limb darkening), Extras (exposure, absolute dimensions, compare with a model curve), Fit (Fit, the exports, Export results, the status), Uncertainty (MCMC, steps, Posterior…) and a "Parameters" results tab (name in words, value, error, unit; fixed ones marked) filled after each fit: `ui/models_stages.py` `models_stages`, `parameter_rows`; `test_the_models_window_has_stages`, `test_models_page_fits_a_light_curve`; the posterior corner plot stays on PlotCanvas (contours are not in the plot spec). (2026-11-21) The Fit history result tab (one row per fit of the session, in memory: time, model, χ²ᵣ, rms, points, free parameters; "Restore these values" through the page's undoable `edit`) and the Report tab (the fit text and table caption, Copy): `ui/models_history.py` `add_history_tabs`; `test_history_lists_each_fit_and_restores_values_and_report_copies` in `tests/ui/test_models_history.py`. (2026-11-21) Lower and Upper columns of the parameter table (empty: the engine's limits; part of the undo state; a start outside its limits marks the row and Fit shows the message): `ui/models_bounds.py`, `models.fit.limits` / `check_start`, the `bounds` parameter of `models.eb_fit`; `tests/ui/test_models_bounds.py`. (2026-11-21) Prior column (Uniform / Log-uniform per row, after Upper, in the undo state): `ui/models_priors.py`; `models.fit.mcmc(priors=…)` / `log_uniform_names` (log-uniform needs finite limits above zero, else ValueError; `core.inference.mcmc.around(log_uniform=…)` uses `LogUniform`), the `priors` parameter of `models.eb_fit`; `tests/test_models_priors.py`, `test_a_log_uniform_prior_with_a_non_positive_limit_is_refused_and_undoable`. Left: the 3-D system view, the WD / PHOEBE symbol, per-band third light, spots and third body, several light curves with RVs)
```
1 Data   ●      Light and velocity curves      ?       ┌ light curves + model, residuals below ──┬ view ─┐
2 System        ☑ V   1 204 pts  σ 0.006               │ (phase or time; one colour per filter)  │ 3-D   │
3 Stars         ☑ R   1 198 pts  σ 0.005               ├ radial velocities + model, residuals ───┤ system│
4 Extras        ☑ RV1 24  ☑ RV2 22                     └─────────────────────────────────────────┴───────┘
5 Fit           [Add…] [From Photometry / Spectroscopy] results: [Parameters][Fit history][Posterior][Report]
6 Uncertainty   [ Next: describe the system → ]         view: stars at the phase under the cursor; Roche
7 Results                                               lobes; spots; plays through the orbit
```
- **Parameters** tab: one table for all parameters: name in words (and the WD / PHOEBE symbol in a column for
  experts), value, error, free ☑, limits, prior, unit; rows grouped (Orbit, Star 1, Star 2, Surface, Spots, Third
  light per band, Third body). No field anywhere else holds a parameter.
- **Files:** `ui/models/` (see MOD-W)

#### UI-16.7 Exoplanets
**partial** — done (2026-11-20): a new area window on a saved light curve (`ui/exoplanets_page.py`; the Photometry window keeps its transit controls): Data (light-curve files or CSV with errors), Star (u1, u2), Planets (start values), Model (detrending), Fit (`photometry.transit_fit` through the engine), Uncertainty (β, MCMC steps), Results (values, the transit plot shared with Photometry, ExoClock and ETD files); `tests/test_exoplanets_window.py`. Done (2026-11-21): the result tabs Chains (trace per parameter), Corner and Report (fit text with Copy) and the convergence lines (R̂ > 1.01 or ESS < 400 warns) in `ui/exoplanets_docks.py`; `photometry/transit_chains.py` keeps the thinned chains (≤ 2000 draws) and R̂ / ESS in `result["mcmc"]`; `tests/ui/test_exoplanets_docks.py`. Done (2026-11-21): the stellar density ρ★ = 3π(a/R★)³/(GP²) with its error (MCMC draws of a/R★, else first-order from a/R★ and P) in g/cm³ and ρ☉ (`photometry/stellar_density.py` `stellar_density`), the Results line and the "Expected ρ★" field with the σ apart (`ui/exoplanets_density.py` `density_line`); `tests/test_stellar_density.py`. Done (2026-11-21): the "Mid-times" result tab (`ui/exoplanets_midtimes.py` `midtimes_dock`: one row per fitted file with Tc and σ, the linear ephemeris of `timeseries/ephemeris.fit` with epochs from the entered period, the O−C plot, "Send to O−C" through `ExoplanetsPage.midtimes_to_oc`); `tests/ui/test_exoplanets_midtimes.py`. Left: TFOP from a file, several nights at once, archive fill / SED, radial velocities, planet cards, per-filter limb darkening, the guide chapter.
```
rail           stage panel (example: 3 Planets)             main                                   inspector
1 Data         Planet b                            ?        ┌ transits: one row per night, data + ─┐ Parameter Rp/R★
2 Star         Name [ Qatar-1 b        ] [Fill from archive]│ model, residuals under each          │ value 0.1463
3 Planets ●    Period        1.4200242 d   prior ◉ fixed    ├ folded transit per filter ───────────┤ prior none
4 Model        Mid-transit   2460000.4055  prior ○ free     ├ radial velocities (time | phase) ────┤ limits 0–0.5
5 Fit          Depth, a/R★, b: starts from the archive      ├ O−C of the mid-times ────────────────┤ source: archive
6 Uncertainty  [+ Add a planet]                             └──────────────────────────────────────┘ (Bonomo+ 2017)
7 Results      [ Next: model options → ]                    results: [Parameters][Chains][Corner][Report]
```
- **1 Data:** a table of data sets (kind: transit night / radial velocities / mid-times; file; instrument; filter;
  points; time span; exposure; "use"); add by file, from Photometry (the open session's light curve), from
  Spectroscopy (the velocities table), from the archives (published mid-times); each transit night shows a thumbnail
  curve. Empty state: the three ways in (One transit · Ephemeris · Global fit) as cards.
- **2 Star:** the inputs table (Teff, log g, [Fe/H], parallax, magnitudes: value, error, source, "use as a
  constraint"), "Fetch from catalogues", the choice of stellar model (isochrones · empirical relations · typed
  mass and radius), the SED plot and the H–R diagram as two small plots under the table; the consistency line of
  EXO-6.5.
- **3 Planets:** above; one card per planet.
- **4 Model:** per filter: limb darkening (from tables: fixed · prior · free), dilution; per night: detrending
  columns (additive / multiplicative ticks), baseline, error scaling; orbit: circular · eccentric; exposure
  integration (automatic); extra terms folded (secondary eclipse, phase curve, Rossiter–McLaughlin, noise model).
- **5 Fit:** "Quick fit" (least squares) as the primary action; the live χ² and the model redrawn; the fit's
  messages in words ("the period is not constrained by one transit: it stays fixed").
- **6 Uncertainty:** the run panel of EXO-5.7 (sampler choice folded; progress; convergence bars per parameter;
  Pause / Resume / Stop); a banner while the result is not converged.
- **7 Results:** the summary cards (planet radius, mid-time with O−C against the catalogue, depth, duration;
  mass and density when velocities exist), then Export cards (tables, figures, upload files).
- Results dock: **Parameters** (all fitted and derived, grouped as EXOFAST's tables, with intervals; search),
  **Chains** (traces with the burn-in mark), **Corner** (choose parameters), **Report** (preview of the LaTeX table
  and the files).
- Toolbar: Open data…, Fill from archive, Quick fit, Run uncertainty, Stop, Report…, Send mid-time to O−C.
- **Files:** `ui/exoplanets/` (see EXO-W)

#### UI-16.8 Planning
**partial** — 2026-11-28: the inspector for the chosen target (`ui/plan_inspector.py`: `plan_inspector`, `target_rows`; empty state "Select a target to see its details"; follows the row, date, site and the planned night; test_plan_inspector); left out: type and magnitude (the row holds neither), the field view with the sensor footprint, the exposure calculator, last observed. 2026-11-27 (owner's report: the chart choices were too hidden): "More charts…" (`PlanPage.more_button`) moved from the Schedule stage to a row right above the chart in the main view, so it shows with every stage chosen (`test_the_plan_chart_choices_are_visible_in_every_stage`). 2026-11-14: the window on the stage anatomy (`ui/plan_window.py`: Site and night, Targets, Night, Schedule as stages from the page's four parts, the chart and the tables in the middle, the step guide moving the rail; test_ui). Earlier the same day: stage 1's almanac line is in the present Plan page (`ui/plan_almanac.py`: sunset, dark hours, sunrise and the Moon in local time under the site, refreshed as the site or date changes; test_plan_chart)
```
rail            stage panel (example: 2 Targets)            main                                   inspector
1 Site, night   Targets of 2026-11-14            ?          ┌ altitude / airmass against time, ────┐ NY Vir
2 Targets ●     [ + Add… ] [ What can I observe tonight? ]  │ twilight bands, Moon dashed, events  │ 13 38 48.1 −02 01 49
3 Night         ☑ NY Vir      EB   V 13.3   min 22:41 ±1 m  │ as bars with ± uncertainty, horizon  │ sdB+dM, P 0.1010 d
4 Schedule      ☑ Qatar-1 b   tr   V 12.8   20:10–21:47     ├ [Night chart][Sky map][Year] ────────┤ next minima: …
5 Send          ☐ RZ Cas      EB   V 6.2    not tonight     │                                      │ field view with
                lists: [my EBs ▾]  [Import…]                └──────────────────────────────────────┘ sensor footprint
                [ Next: look at the night → ]               results: [Events][Finder results][Schedule table]
```
- **1 Site and night:** the site profile (chooser + "Edit…"), the date (calendar with Moon phase per day), the
  almanac line (sunset, dusk, dawn, sunrise, dark hours, Moon), the month strip to choose nights.
- **2 Targets:** above; the finder (PLN-5) opens as a panel in the results dock with its filters on the left and
  the ranked table on the right.
- **3 Night:** chart options (time axis: local · UT · sidereal; altitude limit; show Moon distance labels);
  the three tabs of the main view.
- **4 Schedule:** the timeline as the main view (blocks per target, overhead slivers, twilight flats, conflicts in
  amber); block details in the Inspector; "Make a schedule" as the primary action, then drag to adjust.
- **5 Send:** summary of what will be sent (targets, exposure plans, protected event windows), "Check in the
  simulator first" (OBS-6 dry run) and "Send to Observing".
- Inspector (selected target): identity and coordinates, magnitudes, ephemeris with source and uncertainty, the
  events of the night, the field view (survey image, sensor footprint, comparison stars by PHO-17's rules), the
  exposure calculator (PLN-6), "last observed".
- Toolbar: Add target…, What can I observe tonight?, Plan the night, Exposure…, Make a schedule, Send to Observing.
- **Files:** `ui/planning/` (see PLN-W)

#### UI-16.9 Observing
**partial** — done (2026-11-20): the stages Connect (address, token, Connect / Set up / Start local, the cooler with the devices line, the safety label), Point, Focus, Sequence, Night (`stage_boxes.observing_stages`), the exposure rows as the main view; `test_the_observing_window_has_stages`; done (2026-11-21): the device chips in the toolbar (`observe_chips.ObserveChips`: mount, camera, focuser, filter wheel, rotator, dome from the polled status; amber when busy, red when the device reports an error; a click shows the device's stage and its values) and the inspector (the clicked device's values or the selected exposure row; frame HFR/stars/sky, guider, weather, clock chips and the popover are not in the status and stay out), `test_observe_chips.py`; more done (2026-11-21, `ui/observe_results.py::ObserveResults`): the results dock's Log (the polled status's log lines, filter line) and Graphs (camera temperature and focuser position over time, `plot_box`) tabs, hidden until the first content; `tests/ui/test_observe_results.py`. Left: the results dock's Program and Live light curve tabs and the Graphs' HFR, star count, sky, guiding, airmass (not in the status), "Check the program" (no dry run exists in the engine), "Edit as a tree".
```
┌ devices: [● Mount tracking][● Camera −10.0 °C][● Focuser 12 034][● Filter V][● Guider 0.6″][● Dome][● Weather][● Clock +0.03 s][● Safe] ─ [■ Stop everything] ┐
│ rail          stage panel (example: 4 Sequence)       main: the last frame (ImageView)            inspector          │
│ 1 Connect     Tonight's program              ?        ┌─────────────────────────────────────────┐ Frame 124 of 300  │
│ 2 Point       ▸ NY Vir   22:05–23:40   V 60 s × ∞     │ image with the star list's rings        │ HFR 2.3 px (1.4″) │
│ 3 Focus       ▸ Qatar-1 b 19:30–22:30  R 90 s × ∞     │                                         │ stars 412         │
│ 4 Sequence ●  ▸ flats at dawn  B V R                  │                                         │ sky 812 ADU       │
│ 5 Night       [Check the program] [Edit as a tree…]   └─────────────────────────────────────────┘ peak T1 61 % lin. │
│               now: exposing 124 / 300  ▓▓▓░ 38 s      filmstrip of the last frames with HFR       guiding 0.6″ rms  │
│               [ Pause ]  [ Skip target ]              results: [Program][Graphs][Live light curve][Log]             │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
- **1 Connect:** "Set up the observatory…" (the only place for addresses, tokens, certificates, drivers);
  "Connect all"; a card per device with its state and its problem in words; "Use the simulated observatory".
- **2 Point:** target (from Planning or typed), "Slew and centre", the live preview with crosshair and framing
  rectangle, rotation, nudge buttons, "Solve where I am".
- **3 Focus:** current position and temperature, "Autofocus", the V-curve plot of the last run, filter offsets,
  rules (when to refocus), the focus history.
- **4 Sequence:** above: the simple list by default; "Edit as a tree" opens the full program editor in the main
  area; "Check the program" runs the dry run and lists its findings.
- **5 Night:** conditions (weather values against their limits), safety state with the reasons, the time-line of
  the night so far, "End the night" (park, warm up, close), the night report.
- Device chips: a click opens a small popover with that device's controls (cooler set point and power, focuser
  moves, filter change, park / unpark, dome and cover actions); a chip is amber when slow, red when lost.
- Results dock: **Program** (the running tree with state per instruction), **Graphs** (HFR, star count, sky,
  guiding, focus / temperature, camera, airmass, linear-range fraction on one time axis), **Live light curve**
  (PHO-19), **Log** (the timeline as text, filterable).
- Addresses, tokens and certificates never appear on this face. "Stop everything" is always visible and always
  enabled.
- **Files:** `ui/observing/` (see OBS-W)

#### UI-16.10 Images
**partial** — done (2026-11-21): the window on the anatomy, no rail (`ui/image_stages.py::image_anatomy`): the image with its tool rows is the main view, the open images are the file strip at the left (a dock, shown when more than one is open, F9-style hide), the header, Information and Graph tabs are the inspector at the right (F10), Tab follows the screen; every menu, toolbar button and option kept; `test_every_moved_area_opens_in_its_own_window`, `test_borders_drag_and_the_image_follows_the_window`, gallery clean in en/tr/de/es. more done (2026-11-21, `ui/image_inspector.py`): the empty state (`empty_state`: Open images…, Open the practice night; shown while the viewer has no image), the Levels (the `LevelsDialog` class as a panel), Layers (`LayersList`, check box per overlay) and History (`QUndoView` on the page's undo stack) inspector tabs (dialogs and menus kept), the strip's filter line and multi-selection (`file_strip`; Stack uses two or more selected files); `test_every_moved_area_opens_in_its_own_window`. more done (2026-11-21, `ui/image_follow.py`): the strip's Thumbnails switch (`set_thumbnails`: icon mode with large previews, the page's lazy per-file thumbnails; list mode as before) and "Follow a folder…" (`FolderFollower`, QFileSystemWatcher; new FITS files go through `add_open`); `tests/ui/test_image_strip.py`. more done (2026-11-21, `ui/image_selection.py`): the strip's right-click menu loops Close image, Save FITS as (into a folder) and Blink images over the selected files; the Layers tab has an opacity slider for the chosen layer (`image_inspector.layers_tab`, `ImageViewer.layer_opacity`); `tests/ui/test_image_selection_actions.py`. more done (2026-11-21, `ui/image_sources.py`): the Sources result tab (made at the first Analyse → Find stars, which calls the existing `photometry.fieldstars.detect_stars` with its defaults; the house `TableView` with x, y and the peak value, all that detection gives; a row click centres the viewer on the star and marks it); `tests/ui/test_image_sources.py`. more done (2026-11-21, `ui/image_measure_table.py`): the "Measurements" result tab (`record` at the first Star / Area / Line measurement via `win.add_result_tab`; one row per measurement: tool, file, the values it returned; Delete and the table's Export); `tests/ui/test_image_measure_table.py`. Left: processing forms in the inspector (still dialogs); the guide chapter and screenshots.
```
┌ toolbar: [Open][Save] │ [◀][▶][Blink] │ [Fit][+][−][1:1] │ tools: [Pan][Star][Region ▾][Ruler][Cut] │ [Levels][Layers][N↑] ┐
│ file strip        │ image (ImageView): tabs or 1–9 tiles, locked by pixel or sky     │ inspector tabs:              │
│ ▣ light_001  V    │                                                                  │ [Info][Header][Levels]       │
│ ▣ light_002  V    │                                                                  │ [Layers][History]            │
│ ▣ light_003  V    │                                                                  │ Star  x 512.31  y 498.77     │
│ (thumbnails or a  │                                                                  │ α 13 38 48.14 δ −02 01 49.2  │
│  list with header │                                                                  │ FWHM 3.1 px (1.8″)  e 0.08   │
│  columns)         ├──────────────────────────────────────────────────────────────────┤ net 184 320 ADU  S/N 410     │
│                   │ [Graph: profile / radial / histogram][Table: measurements][Sources]│ V 12.52 ± 0.02 (zero point)  │
└───────────────────┴──────────────────────────────────────────────────────────────────┴──────────────────────────────┘
```
- No rail (a viewer, not a workflow). File strip: thumbnails or list mode, multi-selection, filter line, "Follow a
  folder"; hidden with F9.
- Inspector tabs: **Info** (what the last tool measured: IMG-3; "Add to table"), **Header** (plain-words summary,
  searchable table, edit, verify, compare: IMG-10), **Levels** (IMG-2), **Layers** (overlays with visibility and
  opacity: catalogues, regions, grid, annotations), **History** (IMG-8).
- Menus as today (File, Edit, View, Process, Analyse, Overlays, Astrometry, Colour, Stack) with every existing
  action kept; a processing action opens its form in the Inspector (not a modal dialog) with the preview in the
  image.
- Empty state: "Open images…", "Open the practice night", drop target.
- **Files:** `ui/images/` (see IMG-W)

#### UI-16.11 Astrometry
**partial** — done (2026-11-20): an area window (`MovingObjectPage` in `ui/moving_dialog.py`, the dialog kept as a wrapper; the Image menu's entry opens the window): Images, Solve (`astrometry.solve` on frames without a WCS), Find (marking on the first and last frame), Measure, Report (ADES PSV); `test_the_astrometry_window_has_stages`. more done 2026-11-21: the inspector (`astrometry_inspector.position_inspector`: the chosen measurement row's frame, time, RA/Dec, x/y, residual, the fit's rms and catalogue; hidden until a row is chosen); `tests/ui/test_astrometry_inspector.py`. more done 2026-11-21: "Blink the frames…" in the Find stage (`astrometry_blink.blink_button`/`open_blink`: opens the blink window with the frames in time order, aligned by it; disabled under 2 frames); `tests/ui/test_astrometry_blink.py`. Left: track and stack, search, known objects, per-frame errors and magnitudes (the measurement computes neither a position error nor a magnitude per frame yet), other report formats, the validator.
```
rail          stage panel (example: 3 Find)                 main: image with blink strip             inspector
1 Images      Moving objects in this field       ?          ┌──────────────────────────────────────┐ (433) Eros
2 Solve       Known objects: 3 in the field [Show]          │ frames aligned on the stars; known   │ V 9.8  1.9″/min PA 251°
3 Find  ●     ◉ Blink  ○ Track and stack  ○ Search (GPU)    │ objects with motion arrows; the      │ O−C  +0.08″ −0.03″
4 Measure     Rate up to [ 3.0 ] ″/min   S/N ≥ [ 7 ]        │ candidate's stack in an inset        │ frames measured 24/24
5 Report      about 2 000 vectors, 40 s on this GPU         └──────────────────────────────────────┘
              [ Search for moving objects ]                 results: [Detections][Residuals][Report preview]
```
- **1 Images:** the series (time span, exposure, filter), calibrated? solved?; **2 Solve:** state per frame, hints
  used, residuals, "Solve again" options folded; **3 Find:** above; **4 Measure:** the object's positions per frame
  with uncertainties and magnitudes, flags (blended, trailed), choice of centroid; double-star and "any object"
  modes here too; **5 Report:** header from the profiles, format (ADES PSV / XML, 80-column, comets), validator
  result, preview, "Open the submission page".
- **Files:** `ui/astrometry/` (see AST-W)

#### UI-16.12 Automation
**partial** — done (2026-11-20): the library on the left, the steps as a chain of cards (`ui/step_chain.StepChain`: title and a one-line summary of its settings), the selected step's settings as the inspector; `test_the_automation_window_chain_of_cards`. more done 2026-11-21: Run from here (a card's right-click action, `StepChain.runFromHere` → `AutomationPage._run(row)`: runs the steps from that card on; the outputs of earlier steps are not kept, so what they would give is asked in the inputs form), Stop (the Run button is "Stop — n %" while a chain runs, `automation_run.RunState`), missing-input badges (`automation_run.show_badges`, `StepChain.set_badge`); `tests/ui/test_automation_run_controls.py`. more done 2026-11-21: drag from the library and to reorder (`step_library.StepLibrary` lists every step; `StepChain` takes the drop, `stepDropped`/`cardMoved`, `drop_place`; `AutomationPage.add_step(id, at)`, `_reorder`; the buttons stay the keyboard path); `tests/ui/test_automation_drag.py`. more done 2026-11-21: "on error: stop / skip / continue" per step (engine: `automation.Failed` sent into `calls`, the step's optional `on_error` key, `run` and `AreaActions.run_automation` send it; inspector `automation_error.OnErrorBox`); `tests/test_automation_errors.py`, `tests/ui/test_automation_on_error.py`. Save as template done 2026-11-21 (`automation.save_template` into `user_dir()/templates/`, listed by `available()` as templates; `ui/automation_template`: button, name dialog, a used name is refused; `test_user_templates_are_listed_as_templates_and_names_are_unique`, `tests/ui/test_automation_template.py`). more done 2026-11-21: the run plan (`ui/automation_plan.plan_text`, `confirm_plan`: each step in order, each input with its source (earlier step's output, the automation's value, asked in the form, missing) and what is missing; shown as the "Run plan" result tab made at first use and a confirm dialog with "Don't ask again", settings key `dialog.automation_run_plan_skip`; only in a window with a results area; "what is reused" is not shown: the engine has no incremental runs yet); `tests/ui/test_automation_run_plan.py`. Schedule done 2026-11-21 (no engine scheduler exists: `ui/automation_schedule`: "Schedule…" asks a local time, a single-shot QTimer of the page runs `_run` at the next such time, line "Scheduled: 22:30" with Cancel; lost when the program closes; "after the night" stays the checkbox); `tests/ui/test_automation_schedule.py`. Left: container cards.
```
┌ toolbar: [New][Open][Save] │ [▶ Run][■ Stop][Run from here] │ [Schedule…][Save as template] ──────────────────────────┐
│ library (search)      │ chain                                                  │ selected step: Light curve          │
│ ▾ Templates           │ ┌ 1 Scan frames ─────────┐   folder ← (asked at run)   │ (the generated form of the step:    │
│   Eclipsing-binary…   │ └────────┬───────────────┘                             │  the same rows as in Photometry)    │
│ ▾ Calibration         │ ┌ 2 Calibrate ───────────┐   frames ← 1.frames         │ Aperture  [ auto ]                  │
│   Scan frames         │ └────────┬───────────────┘                             │ Sky from  [ median ▾ ]              │
│   Calibrate           │ ┌ 3 Light curve ● ───────┐   images ← 2.calibrated     │ ▸ More options                      │
│ ▾ Photometry          │ └────────┬───────────────┘   target ← (asked at run)   │ on error: ◉ stop ○ skip ○ continue  │
│   Light curve …       │ ┌ 4 Time of minimum ─────┐   ⚠ needs T0 or period      │                                     │
├───────────────────────┴────────────────────────────────────────────────────────┴─────────────────────────────────────┤
│ [Run plan: what will run, what is reused][Log][Results]                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
- Cards show inputs with where each comes from (an earlier step's output, a question, a fixed value); a missing
  input is amber with the fix offered; drag from the library to add, drag cards to reorder; loops and conditions
  are container cards.
- "Run" first shows the run plan (AUT-2.3) unless the user ticked "don't ask"; results open in their area window.
- **Files:** `ui/automation/` (see AUT-W)

#### UI-16.13 Remote sensing
**partial** (2026-11-20: the stages Scene, Display, Indices, Classes beside the map; the pixel read-out, the
status and the plot stay in the column under them; band roles two per row; test_the_remote_sensing_window_has_stages.
more done 2026-11-21: the Export stage (`rs_views.export_stage`: the products written, "Save the map as a picture…"),
the Histogram and Statistics result tabs of the shown band or product (`rs_views.add_views`, `histogram_figure`,
`statistics_rows`); test_the_remote_sensing_window_shows_histogram_statistics_and_products.
more done 2026-11-21: the Layers list (`rs_layers.LayersList`, `install`, `draw`, `compose`: bands and products with a
visibility box and an opacity slider, the map alpha-composites the visible layers in list order, first row at the bottom;
composites, masks and vectors are not layers yet); test_rs_layers.py.
more done 2026-11-21: the inspector (`rs_inspector.pixel_inspector`: hidden until a click on the map, then the pixel's x/y,
longitude/latitude when georeferenced, each band's value and a value-vs-band-number plot: the scene holds no band
wavelengths); test_rs_inspector.py.
more done 2026-11-21: the map's longitude/latitude grid, scale bar and north arrow (`rs_map_layers.MapLayers`, check boxes
under the Layers list, off by default, redrawn on `view_changed`; grid only when `lonlat` works, scale bar only for a CRS
in metres, north from `lonlat` of the pixels around the centre; disabled with a tooltip otherwise); test_rs_map_layers.py.
Left: the Change stage (needs an engine step `rs.change` on two
products, designed first), the Classes and Time series tabs, GeoTIFF export options and the map layout)
```
rail           stage panel (example: 3 Indices)            main: the map                           inspector
1 Scene        Index or formula               ?            ┌─────────────────────────────────────┐ Pixel 5120, 3311
2 Display      [ NDVI ▾ ]  (NIR − Red) / (NIR + Red)       │ map (ImageView) with geographic grid,│ 41.0321° N 29.0142° E
3 Indices ●    range −1 … 1 · vegetation vigour            │ scale bar, north arrow; layers       │ B4 0.061  B8 0.412
4 Classes      mask clouds ☑ (from the scene's quality     │ drawn in order                       │ NDVI 0.742
5 Change       layer)                                      └─────────────────────────────────────┘ spectrum ▁▂▂▇▆▃
6 Export       [ Compute ]                                 results: [Histogram][Statistics][Classes][Time series]
```
- Left of the rail's panel, a **Layers** list is always visible (bands, composites, products, masks, vectors with
  visibility and opacity). Stages: **1 Scene** (product recognised, bands and roles, quality masks), **2 Display**
  (composite presets, stretch), **3 Indices**, **4 Classes** (unsupervised / supervised with training polygons and
  the accuracy table), **5 Change** (two dates, time series), **6 Export** (GeoTIFF, map layout).
- **Files:** `ui/remotesensing/` (see RS-W)

#### UI-16.14 Project
**partial** — done (2026-11-20): tabs Files, History, Methods text (`core.methods`, Copy); `test_the_project_window_has_tabs`. Tasks tab added (2026-11-21): `project_tasks.TasksTab` (all windows' tasks from `kit.tasks.SEEN`, Cancel row action, ticks while shown); `test_project_tasks`. Left: Products, Sessions (no record marks a product yet).
```
┌ Project: NY Vir 2026 — /data/nyvir/nyvir.astroproj ─────────────────────────────────────────────────────────────────┐
│ [Files][History][Products][Sessions][Tasks][Methods text]                                              [🔍 filter]  │
│ History                                                                                                             │
│ 2026-11-03 22:41  Calibrate 48 frames            3.2 s   ✓   [Run again] [Copy as script] [Show products]           │
│ 2026-11-03 22:44  Light curve (T1 + 4 C)         9.1 s   ✓   radii 6 / 14 / 20 px · sky median · …                  │
│ 2026-11-03 22:45  Time of minimum (Kwee–van W.)  0.2 s   ✓   2460983.40546 ± 0.00009                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
- **Files:** what the project refers to (kind, size, where; missing files flagged with "Locate…"; a moved folder is
  re-linked in one action); **History:** every run in words with its parameters (the step descriptions of AUT-1),
  filter by area / date / result; **Products:** frames, tables, figures with their provenance ("made by … from …"),
  "Reproduce", "Open in its window"; **Sessions:** autosaved and named sessions per area; **Tasks:** everything
  running and finished in this run of the program; **Methods text:** ARC-11.
- **Files:** `ui/shell/project/{window,files,history,products,sessions,tasks,methods}.py`, `engine/project.py`, `tests/ui/walks/project.py`, guide 01

### UI-17. Polish  (P3)
**open** — 2026-11-14: the splash (`__main__._splash`: the icon and "Starting …" at once, before the long imports, closed when the main window shows; tests/test_splash.py). About with version, licences and the privacy text was there already.
- **Build:** a splash that appears in < 300 ms and shows what is loading; About with version, licences
  (generated), the privacy statement; consistent window icons; hover and pressed states everywhere; drag feedback;
  cursor shapes for tools; smooth splitter moves; no layout jump when a banner appears (space reserved or
  animated).
- **Accept:** a review walk with the gallery sheets finds no state without feedback.
- **Files:** `ui/shell/{splash,about}.py`, `ui/kit/*` (states), `resources/icons/app/`

### UI-18. Language review  (P2)
**open** — done (2026-11-11): Turkish buttons and menu items are imperatives, never infinitives (`translation_review.infinitives`, in `tests/test_glossary.py`; none found); the glossary grew to 106 terms (ARC-18). (2026-11-14) Turkish consistency pass: the same short English text translated two ways was unified (37 strings: Hava kütlesi, Dalga boyu, Bilim karesi, Normalleştir, uydur, okunamadı …); the 14 left differ by context (Dark as a frame and as darkness, Preview as noun and verb).
- **Build:** with ARC-18's glossary: every Turkish, German and Spanish string of each window read in context on the
  gallery sheets by an agent fluent in that language's astronomy vocabulary; awkward machine phrasing rewritten;
  consistency of imperative forms on buttons (Turkish: "Ölç", "Kaydet" — verb stems as commands, never "Ölçmek");
  capitalisation rules per language; the Turkish list of terms sent to the owner once for approval (in
  "To ask the owner").
- **Accept:** the review notes per window are written under this step; the glossary test passes.
- **Files:** `resources/i18n/app_{tr,de,es}.ts`, `resources/i18n/glossary.toml`, `resources/guide/{tr,de,es}/`

### UI-19. Onboarding refreshed  (P3)
**done** — (2026-11-27) the accept holds: `tests/ui/test_tour.py` walks both tours in four languages at 1366 × 768 with no stop off screen. Done (2026-11-11): the tour's last stop names the area windows' keys (stages Ctrl+1…9, F5, F1 / Shift+F1, Ctrl+K, Ctrl+/) and offers Help → Practice data. The tour on the area window's anatomy itself (2026-11-14): Help → Tour of this window in every area window (`tour.start_area`: stages, the stage's controls, the main view, results, toolbar, menus and keys; test_theme at 1366 × 768). (2026-11-20) The quick tour: six stops on the start window (areas, rail, primary button, results, F1, Ctrl+K) ending with "Practice night in five minutes" (practice data, then the first-night guided task); the old 16-stop tour kept as Help → Full tour (`ui/tour_full.py`); `tests/ui/test_tour.py`, `test_full_tour_keeps_the_old_stops`.
- **Build:** the quick tour redone on the new start window and anatomy (six steps: the areas, a window's rail, the
  primary action, results dock, help with F1, find anything with Ctrl+K); "Practice night in five minutes" as the
  tour's last offer (UI-8 task 1).
- **Accept:** QTest of the tour in four languages; no highlighted element is off-screen at 1366 × 768.
- **Files:** `ui/tour.py` → `ui/shell/tour.py`, `ui/welcome.py`, `tests/ui/test_tour.py`, guide 01

## Where everything is (keep this up to date)

Every feature the user sees, with its window, menu, toolbar and panel. Add a row whenever any area gains a
feature; UI-16.x rewrites the rows of its window (stage instead of the old panel).

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
| Find the best comparison set (without the target) | Photometry | Stars | — | Results: Stars |
| Frames missing some comparison stars kept (orange in the frame list) | Photometry | — | — | Frames tab, under the plot |
| Header time as start / middle / end, shutter delay; HJD_UTC column | Photometry | — | — | Steps 4, More measuring options |
| Transit fitted together with the detrending (BIC) | Photometry | — | — | Results: Minimum |
| Several apertures at once, radius chosen afterwards, aperture correction | Photometry | — | — | Steps 4 options; Results: Plot |
| Several filters in one run, colour index against time | Photometry | (filter question) | — | Results: Plot |
| Several nights joined on one zero point | Photometry | — | — | Results: Export |
| Export for ETD / VarAstro | Photometry | File → Export | — | Results: Export |
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

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

Before 2026-11-09 (agent2; details and commits in `docs/history/interface-plan-2026-11-08.md`):

- I0 big interface file split a first time; I1 research of AstroImageJ, MaxIm DL, Siril, N.I.N.A.
- I2 the area window frame: window, command search (Ctrl+K), recent files, drag and drop, sessions frame, problem
  report, text size, shared plot and table views, long work in the status bar.
- I3 the main window as a menu of blocks; I4 every page moved into its area window; I4a–I4d findings fixed.
- I5 Photometry's first full window (steps, image, results dock).
- I6a user walk of every window with findings I6b fixed; I6c icon toolbars (glyphs) and full menu bars for every
  window; I6d the owner's answers (side panels and sidebar removed, Turkish terms, O−C window).
- I7 names, Basic / Expert reach, window screenshots in the guide, guide read against the windows.

### UI-20. Automatic steps the user controls  (P1)
**The rule (the owner, 2026-11-13):** an automatic step switched off never blocks the work: each has a manual way in
which the user decides what it uses. The table as it stands:

| Automatic | Switch (Settings → Automatic steps) | By hand |
|---|---|---|
| Scan when a folder is chosen | calibration.scan_on_folder | Scan; frame types changed by a double click |
| Masters matched to the lights | (always offered) | Choose the masters by hand…: per filter the bias, dark, flat group or none |
| Stacking alignment (shift / star patterns) | Align choice | none (aligned already); on stars I pick: one star and two or three around it, rotation included |
| Images window stack | asked every time | the same four ways |
| Field identification on opening | photometry.identify_field | Identify the field; or the target's RA Dec typed |
| Comparison stars after the target | photometry.suggest_comparisons | click them; Suggest comparison stars; Why these stars? |
| Radii after the comparisons | photometry.choose_radii | the three radii typed; Choose the radii |
| Frames placed by the whole frame's shift | (empty field: automatic) | Place the frames on: stars picked on the first frame |
| Centring | Centring choice | 1-D, 2-D Gaussian, centre of light, or none (positions follow the field) |
| Next stage opens | photometry.next_stage | click the stage |
| Light curve sent to Light curves | timeseries.take_light_curve | Period search → |
| Times to O−C | oc.take_minima | Add the times to the O−C list; the O−C list is text to edit |
| Spectra to Velocities | spectroscopy.take_spectra | Add… in Velocities |
| Échelle orders found on the flat | (shown to check) | click a wrong trace to remove it |

**partial** — done (2026-11-13, the owner: "her şey otomatik olsun gibi bir niyetim yok"): `ui/automatic.py` lists
the steps the program takes without a press; Settings → Automatic steps turns each off; every one keeps its button.
Defaults are today's. The list: calibration — scan a folder as soon as it is chosen (button Scan); photometry —
identify the field when frames are opened (button Identify the field, new), suggest comparison stars after the
target (Suggest comparison stars), choose the radii after them (Choose the radii), open the next stage (click the
stage); light curves — each measured curve sent there, replacing the open one (with it off, Period search → sends
it); O−C — each time of minimum and transit mid-time added to the list; spectroscopy — each reduced spectrum added to
Velocities (Add…). Stacking: alignment "none (the frames are aligned already)" and "on stars I pick" (a picker on
the first frame; each click snaps onto its star; the stars followed frame to frame, shift only) beside shift and
star patterns. Test: with every switch off nothing starts by itself and the buttons still work. The audit in
Planning, Observing, Images, Models and Remote sensing (2026-11-13): no step starts there without a press (Observing
connects by itself only to the observatory the user has just started); repeat it as those windows are rebuilt; the Images
window's Stack (done: it now asks how to align, the four ways); rotation from two or more picked stars (done: stacking.follow_stars fits a similarity).
