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
**open** — items 1, 2 (partly), 6 and the grep test done by agent3 (2026-11-11)
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
  Pending: the full style sheet for every kit control (item 2), the mono font in tables and read-outs, live theme
  change of icons (5).
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
**partial** — done: Lucide + 16 own SVGs; `ui/kit/icons.py` renders them tinted from the widget's palette (normal / disabled / checked, screen pixel ratio); `tools/icon_sheet.py` writes the contact sheet docs/design/icons.png. 11 area icons on the start window's blocks; `glyph` removed (no caller left). Item 4 exists as View → "Toolbar text" (default stays off: the stored value cannot tell a choice from the old default; owner to decide). Left: item 3 for menu-only actions.
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
**partial** — done: Button, ToolButton, Section, FormRow, NumberField, ChoiceField, Toggle, Segmented, PathField, StageRail, StagePanel, EmptyState, InfoBanner, Badge, Toast, ErrorDialog (failed tasks use it), Inspector, StatusSegments, Splitter, Dialog in `ui/kit/`; `tools/kit_gallery.py`; one test per component in tests/test_kit.py. Shortcuts: PathField lists many files in a tooltip, not a popover; NumberField shows the unit as a suffix (not faint) and has no label scrubbing. Left: ObjectField (with UI-16), HelpPanel (UI-7), TaskChip / TaskPopover (UI-9), the focus-chain and FormRow-alignment checks over the gallery in four languages (UI-15), item 5 (with UI-16).
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
**partial** — done: `kit/anatomy` on AreaWindow: `set_stages([Stage])` (rail + stage panels in a dock), `show_stage`, `set_stage_state`, `set_inspector`, `add_result_tab` (items 1 without set_main / set_empty_state, 5: F9, F10, F11, Ctrl+1…9, Ctrl+Tab); a window whose title bar would open on no screen is moved onto one (item 2); the toolbar ends with Find an action and Help and the TaskChip (item 4). No area uses the stages yet (UI-16).
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
**partial** — done: the Tonight line (item 3: dark hours and Moon from `planning.visibility.tonight`, computed in a thread; without a site a link to Planning); Continue as cards (item 1 from the recent files: area icon, file, area, when saved; at most six, a click reopens; sessions with ARC-5); the area icons on the blocks (UI-2).
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
**partial** — done: every PlotCanvas (21 plots) says why it is empty until something is drawn (`set_empty_hint` for a page's own words); the image viewers of Images, Photometry, Spectroscopy and Remote sensing already had their hint. Left: the table of views with their own texts, loading and error states, the walk test.
- **Build:** a table in this step (filled by the agent) of every main view and result tab of every window with its
  `EmptyState` text, primary action and practice set; loading states (skeleton: the view's frame with a thin
  progress line and the task's phase text); error states (the `InfoBanner` with the error's what / do and "Try
  again"). No view may show a black or blank rectangle without words. Texts are written for a newcomer: what will
  appear here, and the one thing to do to get it.
- **Accept:** a test opens every window in a fresh profile and asserts that every visible view shows either data or
  an `EmptyState`; screenshots in four languages reviewed.
- **Files:** every window's panels, `tests/ui/test_empty_states.py`.

### UI-7. Help on demand  (P1)
**open**
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
**open**
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
**partial** — done: `kit/tasks.TaskChip` in every area window's toolbar (running count; popover with state, progress, elapsed, estimate from 5 %, Cancel); a Toast in the window when its task finishes. Left: phase text and timeline (ARC-17), system notification after 60 s, failed tasks with Report in the popover, the primary button as Stop.
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
**open**
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
**partial** — done: the count line under every TableView ("12 of 48 rows · 2 selected"); numbers in the monospace font. Left: header menu, the row-action words, digits by error, time standards in headers, EmptyState for an empty table.
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
**partial** — done: Help → Keyboard shortcuts (Ctrl+/) in every area window, a searchable sheet read from the actions (`kit/shortcuts.py`); a test finds a key given to two actions of a window (it found the text-size keys twice in every area window: fixed). Left: the shortcuts.toml map editable in Settings, the image / plot / spectrum keys, F5 / Esc for the stage.
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
**open**
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
**open**
- **Build:** Window menu: list of open windows, "Tile side by side", "Bring all to this screen"; floating result
  tabs remember their screen; the Photometry image and its plot can live on two monitors; closing the start window
  with area windows open asks nothing and keeps them (the program ends when the last window closes, or by File →
  Quit).
- **Accept:** QTest on two virtual screens (offscreen platform with two screens) moves, restarts and finds the
  windows where they were.
- **Files:** `ui/kit/window.py`, `ui/shell/menus.py` (Window menu), `tests/ui/test_multi_screen.py`

### UI-15. The gallery test: every window, every language, every theme  (P1)
**open**
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
**open**
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
  minimum by Kwee–van Woerden / polynomial / trapezoid / exact model (PHO-26); send to O−C; fit a transit with
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
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
**open**
- **Build:** a splash that appears in < 300 ms and shows what is loading; About with version, licences
  (generated), the privacy statement; consistent window icons; hover and pressed states everywhere; drag feedback;
  cursor shapes for tools; smooth splitter moves; no layout jump when a banner appears (space reserved or
  animated).
- **Accept:** a review walk with the gallery sheets finds no state without feedback.
- **Files:** `ui/shell/{splash,about}.py`, `ui/kit/*` (states), `resources/icons/app/`

### UI-18. Language review  (P2)
**open**
- **Build:** with ARC-18's glossary: every Turkish, German and Spanish string of each window read in context on the
  gallery sheets by an agent fluent in that language's astronomy vocabulary; awkward machine phrasing rewritten;
  consistency of imperative forms on buttons (Turkish: "Ölç", "Kaydet" — verb stems as commands, never "Ölçmek");
  capitalisation rules per language; the Turkish list of terms sent to the owner once for approval (in
  "To ask the owner").
- **Accept:** the review notes per window are written under this step; the glossary test passes.
- **Files:** `resources/i18n/app_{tr,de,es}.ts`, `resources/i18n/glossary.toml`, `resources/guide/{tr,de,es}/`

### UI-19. Onboarding refreshed  (P3)
**open**
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
