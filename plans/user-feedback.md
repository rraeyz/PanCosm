# The owner's feedback from using the program

Every point the owner reported while using a release, as a step with what to do and how to check it. A step is
closed only with a test (or a walk) that shows the fix, and its line says so: **open**, **partial**, **done**.
Newest report first. Read this file before choosing the next work: these come before plan items.

## Report of 2026-11-13 (version 0.3.11 / 0.3.12, Linux, owner's own NY Vir data)

### Planning plot (UF-1 … UF-6)

- **UF-1 — the axes of a scientist, not a poster** — **done** (2026-11-14: `ui/plan_chart.py`, tests/test_plan_chart.py)
  Major tick every hour on the time axis, minor ticks between (every 10 min, unlabelled), altitude labelled every
  10° with 5° minor ticks, a grid on the major ticks (faint) and on the minor ones (fainter). Text not oversized.
  Check: a test reads the axis locators (60 min / 10 min, 10° / 5°) and that the grid is on.
- **UF-2 — local time under UTC, not on top** — **done** (2026-11-14: `ui/plan_chart.py`, tests/test_plan_chart.py)
  The local-time labels as a second row under the UTC labels (or a second axis under it), the top free.
- **UF-3 — twilight visible** — **done** (2026-11-14: `ui/plan_chart.py`, tests/test_plan_chart.py)
  Civil, nautical and astronomical twilight as distinct shades (keep the blue gradient the owner liked), each edge
  a dashed line with its time written; sunset and sunrise marked with their times.
- **UF-4 — taller plot** — **done** (2026-11-14: `ui/plan_chart.py`, tests/test_plan_chart.py)
  The plot's height grows with the window; the width was right, the height was squeezed.
- **UF-5 — at least what the ING "staralt" chart gives** (the owner's screenshot) — **done** (2026-11-14: LST
  along the top, the Moon's distance every hour along each curve, airmass on the right, rise and set through the
  altitude limit in the legend, Moon illumination, the site and date in the title, the twilights' times; the
  owner's wish: a blend of staralt, airmass.org and our own — anything he misses is a new step; 2026-11-14: each hour row is named at its right end with an arrow, and "More charts…" opens the Moon's distance per hour and a polar sky view with an hour slider — `ui/plan_more.py`; the "Through the year" tab shows the night length over the year)
  LST along the top, the Moon's distance from each target written along its curve every hour, airmass scale on the
  right, each target's rise / set (above the altitude limit) times in the legend, Moon illumination and its own
  curve, the site and date in the title. Better than staralt: our colours, the blue twilight, interactive.
- **UF-6 — CSV export** — **done** (2026-11-14: checked — plain UTF-8 CSV with a `.csv` name and a header row; Krita opening it is the desktop's file association, nothing to change)
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
- **UF-11 — Photometry, stage 5: squeezed with a scroll bar while there is free space below** — **done**
  (2026-11-14: reproduced at 1366 × 768 — the stage's page scrolls itself and sat above the panel's stretch with
  its hint's height (384 of 582 px); `StagePanel.add` gives such a page the whole height; test_kit fails before the
  fix and passes after; the Light curve stage now shows every row without a scroll bar. Earlier: the left dock takes
  the window's bottom-left corner)
  Stage panels take the height the dock offers; no fixed heights.

### Calibration (UF-12)

- **UF-12 — "Calibrating the frames" crawls (about 1 % per 2–3 s after a fast first half)** — **done**
  (2026-11-14: measured — the second half is the lights, nearly all of it the cosmic-ray cleaning; astroscrappy
  repeats its whole-frame search up to four times. `calibration/cosmics.py` runs its steps once over the frame and
  the later passes only within 9 px of what the last cleaning changed: the same mask and cleaned frame bit for bit
  (tests/test_cosmics.py, and real 4k frames with planted tracks), 2–2.5× faster (4k: 15.8 s → 6.4 s; 1536 × 1024:
  1.1 s → 0.6 s). Running frames in parallel was slower (astroscrappy already uses every core). The option's tooltip
  says it is the slow part)
  Profile the owner's night (40 lights, 2×2, cosmic-ray cleaning on): find the slow part (likely astroscrappy per
  frame on one core, or masters re-read per frame) and speed it up without changing the result.

### Photometry (UF-13 … UF-19)

- **UF-13 — variable stars drawn on empty sky** — **partial** (2026-11-14: the likely cause — VSX lists variables
  down to magnitude 20 and every one was ringed; now only those brighter than 16.5 are ringed, with their
  magnitude, the faint ones are in the list ("too faint to see") and ring when chosen; test. 2026-11-14, the second
  cause: the solution was a plain TAN fit from stars matched within 2.5 px of a first guess, i.e. near the centre;
  with the optics' distortion it was right at the centre (NY Vir) and pixels off towards the corners — a synthetic
  frame with 6 px of barrel distortion at the corners was 6.3 px off. Now every star of the frame is matched again
  through the solution and a SIP polynomial (degree 2, 3 with 60 stars) is fitted when it fits better: 0.6 px at
  the corners (test_field); on the Qatar-1 LCO frames 577 stars instead of 196, edge residual 0.16 → 0.13 px, no
  slower. Left: the owner's NY Vir frames, to confirm)
  After Identify the field, NY Vir was right but other VSX circles sat on blank sky. Either the solution is off
  away from the centre (distortion, wrong scale on a 2×2 frame) or VSX positions are not moved to the epoch. Check
  on the owner's frames: residuals of the solution across the frame, and the VSX stars' pixel positions.
- **UF-14 — "Identify the field" again only reads the cache** — **done** (2026-11-13: pressed on an identified
  field it asks the catalogues again — step parameter `fresh`; tests)
  A second press (or Shift-click / a menu item "Identify again, ignore the saved answer") must solve again.
- **UF-15 — AAVSO sequence labels in the wrong places** — **partial** (2026-11-14: same solution as UF-13 — the
  labels are placed through the field's solution, which now carries the distortion; left: the owner's frames)
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
- **UF-18 — 40 frames, the plot shows about 20 points** — **partial** (2026-11-14: the summary says "N of the M frames in the list became points; the others are named below"; the cause on the owner's night is still unknown)
  The text says 39 points. Find where the others went (frames left out? two filters in the folder? raw and
  calibrated frames mixed?) on the owner's data; the owner asks whether uncalibrated frames were included. The
  program must say which frames it used and why any was left out.
- **UF-19 — stage rail numbers look childish** — **done** (2026-11-13: the rail shows the stages' names from the
  start, no numbers, a quiet ✓ after a done stage and "!" after one needing attention; the dock keeps the rail and
  the stage's width so the stage's rows still fit — test_overflow, test_kit)
  "1 ✓ 2 ✓ … 8 ○": use the stage names with small state marks (icons), as a professional tool.

### Models (UF-20)

- **UF-20 — the eclipsing-binary fit is useless on a single night** — **done** (2026-11-14: the period and T0
  have no default and come from O−C, Light curves or Photometry, or the fit says what to do; r1 + r2 and J left
  at the table's defaults start from the curve folded on the ephemeris — `estimate.start_from_curve`; tests.
  A check on the owner's NY Vir night stays with UF-18's data)

### Services (UF-21, UF-22)

- **UF-21 — Check the installation: CDS hips2fits 404, AAVSO International Database 403** — **partial**
  (2026-11-13: CDS answered "Page unavailable" from here too — our address is right, CDS was down; the AAVSO data
  API also answers 403 here. The check now says "the service is down or moved now" / "the service refused the
  program" instead of the HTTP error. 2026-11-14, read from the AAVSO forums (no probing of the AAVSO): the documented
  address is still www.aavso.org/vsx/index.php?view=api.delim; VSX now runs on vsx.aavso.org with rate limiting
  against automated traffic, the AAVSO announced a VSX rewrite without a promise of the old API, and a March 2026
  thread reports 403 on every request from one server's address (a ban by address). Left: the owner tries the
  address from his own computer; if vsx.aavso.org answers there, it becomes the first address)
  The owner says the French (CDS) servers are having trouble; check our URLs anyway (hips2fits endpoint, AAVSO
  needs a user agent or a new address) and say "the service is down" rather than an HTTP code.
- **UF-22 — GPU check: the sigma-clipped mean is slower on the GPU (0.5×)** — **done** (2026-11-13: Automatic
  keeps it on the compiled CPU routine; the GPU check says so; test)
  "Automatic" must keep that job on the CPU (RTX 4050 laptop, the owner's numbers); the other five jobs gain
  1.8–97×.
