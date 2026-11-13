# The owner's feedback from using the program

Every point the owner reported while using a release, as a step with what to do and how to check it. A step is
closed only with a test (or a walk) that shows the fix, and its line says so: **open**, **partial**, **done**.
Newest report first. Read this file before choosing the next work: these come before plan items.

## Report of 2026-11-13 (version 0.3.11 / 0.3.12, Linux, owner's own NY Vir data)

### Planning plot (UF-1 … UF-6)

- **UF-1 — the axes of a scientist, not a poster** — **open**
  Major tick every hour on the time axis, minor ticks between (every 10 min, unlabelled), altitude labelled every
  10° with 5° minor ticks, a grid on the major ticks (faint) and on the minor ones (fainter). Text not oversized.
  Check: a test reads the axis locators (60 min / 10 min, 10° / 5°) and that the grid is on.
- **UF-2 — local time under UTC, not on top** — **open**
  The local-time labels as a second row under the UTC labels (or a second axis under it), the top free.
- **UF-3 — twilight visible** — **open**
  Civil, nautical and astronomical twilight as distinct shades (keep the blue gradient the owner liked), each edge
  a dashed line with its time written; sunset and sunrise marked with their times.
- **UF-4 — taller plot** — **open**
  The plot's height grows with the window; the width was right, the height was squeezed.
- **UF-5 — at least what the ING "staralt" chart gives** (the owner's screenshot) — **open**
  LST along the top, the Moon's distance from each target written along its curve every hour, airmass scale on the
  right, each target's rise / set (above the altitude limit) times in the legend, Moon illumination and its own
  curve, the site and date in the title. Better than staralt: our colours, the blue twilight, interactive.
- **UF-6 — CSV export** — **open (check only)**
  Krita opened the saved CSV (the desktop's file association), LibreOffice read it fine. Check the file is plain
  CSV with a `.csv` name and the text/csv type; nothing to change if so.

### Exports (UF-7)

- **UF-7 — Publication figure: PDF, SVG and EPS fail in the installed program** — **done** (2026-11-13: the
  backends bundled in packaging/app.spec; the installed program's smoke test saves PNG, PDF, SVG and EPS)
  `ModuleNotFoundError: matplotlib.backends.backend_pdf` (and `backend_svg`, `backend_ps`): the installer leaves
  matplotlib's file backends out; PNG works. Fix: bundle them (PyInstaller hidden imports) and make the installed
  program's smoke test save one figure in every format.

### Windows and layout (UF-8 … UF-11)

- **UF-8 — the Guide has no way back to the start page** — **done** (2026-11-13: "← Start page", Alt+Home; test)
  A Home / Start page button (and Alt+Home) in the Guide.
- **UF-9 — Calibration, windowed: opening "Stacking options" pushes the right column out of the window** — **done**
  (2026-11-13: the options' choices take ten characters' width; `tests/test_overflow.py` opens every fold of
  every window, every stage, at 1366 × 768 in English, Turkish and German and finds nothing wider than its place)
  Every collapsible section must fit the window's width (wrap, or scroll vertically only). Check every window's
  collapsible sections at 1366 × 768 windowed, in four languages (the gallery test opens them).
- **UF-10 — Photometry, Measure stage: "Other measurement options" overflows to the right, even full screen** —
  **done** (2026-11-13: `ui/kit/fit.py` on every stage panel — narrow choices, long check-box texts wrapping
  beside their box, too-wide rows flowing onto the next line; the Measure stage needed 586–698 px in 474)
- **UF-11 — Photometry, stage 5: squeezed with a scroll bar while there is free space below** — **open**
  Stage panels take the height the dock offers; no fixed heights.

### Calibration (UF-12)

- **UF-12 — "Calibrating the frames" crawls (about 1 % per 2–3 s after a fast first half)** — **open**
  Profile the owner's night (40 lights, 2×2, cosmic-ray cleaning on): find the slow part (likely astroscrappy per
  frame on one core, or masters re-read per frame) and speed it up without changing the result.

### Photometry (UF-13 … UF-19)

- **UF-13 — variable stars drawn on empty sky** — **open, urgent**
  After Identify the field, NY Vir was right but other VSX circles sat on blank sky. Either the solution is off
  away from the centre (distortion, wrong scale on a 2×2 frame) or VSX positions are not moved to the epoch. Check
  on the owner's frames: residuals of the solution across the frame, and the VSX stars' pixel positions.
- **UF-14 — "Identify the field" again only reads the cache** — **done** (2026-11-13: pressed on an identified
  field it asks the catalogues again — step parameter `fresh`; tests)
  A second press (or Shift-click / a menu item "Identify again, ignore the saved answer") must solve again.
- **UF-15 — AAVSO sequence labels in the wrong places** — **open**
  Follows UF-13 (same solution); check the chart's stars land on stars.
- **UF-16 — 2-D Gaussian centring crashes**: `ValueError: xpos, ypos values contain points outside the input
  data` (photutils centroid_sources) — **done** (2026-11-13: a fit that runs off the frame goes back to the
  prediction before the next pass; test_centring's edge test failed before the fix and passes after)
  Positions near or past the edge must be kept out of that call (the star is then "lost" on that frame, as with
  the other methods). Test: a star 2 px from the edge, and one off the frame, with centring "gauss".
- **UF-17 — bad-frame flags are wrong on an eclipsing binary** — **partial** (2026-11-13: the jump test follows
  the comparison stars' median position and ignores the night's steady drift; the cloud test compares counts per
  second, so a frame of another exposure is no cloud; test with a synthetic eclipse. Left: the owner's night)
  "Behind cloud" with no cloud; "field jumped" where the target is in its eclipse minimum. The cloud test must use
  the comparison stars only (never the target), and the jump test the stars' positions, not their fluxes. Test on
  a synthetic eclipse plus the owner's NY Vir night: no flag.
- **UF-18 — 40 frames, the plot shows about 20 points** — **open**
  The text says 39 points. Find where the others went (frames left out? two filters in the folder? raw and
  calibrated frames mixed?) on the owner's data; the owner asks whether uncalibrated frames were included. The
  program must say which frames it used and why any was left out.
- **UF-19 — stage rail numbers look childish** — **open**
  "1 ✓ 2 ✓ … 8 ○": use the stage names with small state marks (icons), as a professional tool.

### Models (UF-20)

- **UF-20 — the eclipsing-binary fit is useless on a single night** — **partial** (2026-11-13: the period and T0
  have no default any more; an empty one is taken from O−C, Light curves' period search or Photometry's Timing
  fields, and with none known the fit is refused with what to do; test. Left: start values estimated from the light
  curve, the plot centred on the data, a check on the owner's NY Vir night)
  It started from period 1 d and T0 0 (the table's defaults), folded the night onto phase 0.3 and drew a model
  far from the data. Needed: the period and T0 taken from Light curves / O−C / VSX (a button), the start values
  estimated from the light curve (depth, width, T0 from the deepest point), a refusal with a clear message when
  the period is unknown, and the plot centred on the data.

### Services (UF-21, UF-22)

- **UF-21 — Check the installation: CDS hips2fits 404, AAVSO International Database 403** — **open**
  The owner says the French (CDS) servers are having trouble; check our URLs anyway (hips2fits endpoint, AAVSO
  needs a user agent or a new address) and say "the service is down" rather than an HTTP code.
- **UF-22 — GPU check: the sigma-clipped mean is slower on the GPU (0.5×)** — **open**
  "Automatic" must keep that job on the CPU (RTX 4050 laptop, the owner's numbers); the other five jobs gain
  1.8–97×.
