# Planning: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.8).

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, this file's "Conventions" and "Definition of done", your area file, and `plans/interface.md` before
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

Deciding what to observe, when and how: the site and the night, target lists, visibility, predicted eclipses,
transits and maxima, "what can I observe tonight?", exposure and framing, standards, a schedule with overheads,
phase coverage over many nights, and the hand-over to Observing.

**Goal:** astroplan's rigour, the event tables of the TESS Transit Finder and the national eclipsing-binary
prediction services, the framing of N.I.N.A. — and what none has: planning that knows your own data (which phases
you already have, when you last observed a star, what your camera's noise will be) and feeds the observing
sequence without retyping.

## What the reference programs and services do

Read: astroplan (Morris et al. 2018: constraints — altitude, airmass, at-night, Moon separation and illumination,
time, phase; observability tables; sequential and priority schedulers with transition times); the TESS Transit
Finder / Tapir (Jensen 2013: constraints on elevation and hour angle at ingress, mid-transit and egress, depth,
magnitude; per-event rows with twilight and Moon information and finding charts); the ExoClock scheduler; the
predictions pages of the Czech variable-star section (VarAstro) and of Kreiner's ephemerides in Krakow, the BAV
circular (minima and maxima tables per night); the AAVSO Target Tool; `staralt` (ING: altitude against time with
Moon distance, the classic night plot) and JSkyCalc (Thorstensen: hourly airmass tables, seasonal observability,
parallactic angle); N.I.N.A.'s Sky Atlas and Framing Assistant (survey image under the sensor footprint, rotation,
mosaic panels); KStars / Ekos and ACP schedulers (priorities, constraints, twilight and weather rules).

| Topic | astroplan | Transit Finder / EB services | N.I.N.A. | Ours now |
| --- | --- | --- | --- | --- |
| Visibility | constraints, observability fractions, airmass and sky plots | per-event altitude and twilight flags | altitude chart per target | altitude / airmass chart for several targets, twilight, Moon (dashed), `planning/visibility.py` |
| Events | `PeriodicEvent`, eclipsing systems | tables of all events in a date range with filters | — | eclipses and transits of listed targets from T0 and P (`events`) |
| Finding targets | — | by site, date, depth, magnitude, type | Sky Atlas filters | type a name; VSX and Exoplanet Archive ephemeris look-up |
| Exposure | — | — | — | CCD-equation calculator (`planning/exposure.py`) |
| Framing | — | finding-chart links | Framing Assistant, mosaics | finder chart (DSS + stars) |
| Schedule | sequential / priority schedulers with transitions | — | sequencer (not a planner) | events first, then the highest target per hour (`schedule.py`), sent to Observing |
| Own data | — | — | — | none |

## What we already have (do not redo)

- `planning/targets.py` (typed coordinates, cache, SIMBAD, solar-system bodies), `visibility.py`, `ephemerides.py`,
  `exposure.py`, `schedule.py`, `sites.py`, steps `planning.{resolve, night, ephemeris}`; the Planning window with
  menus Targets and Night; altitudes checked against JPL Horizons (0.005–0.01° rms; dusk / dawn within a minute).

## Decisions

- The site, horizon and equipment come from the profiles (ARC-16); Planning never keeps its own copy.
- Every predicted time carries its uncertainty (propagated from the ephemeris) and its source; the chart draws it.
- Ephemeris precedence: the user's own fit (O−C window) → ExoClock / recent literature → catalogue (VSX, Exoplanet
  Archive); the table shows which was used.
- Works offline from the caches and data packs; whatever needs the network says so and degrades to the cache.

## To ask the owner

- The owner's usual target classes and magnitude range (to set the finder's default filters).

## For the owner to try

- After PLN-W and PLN-5: ask "which eclipsing binaries have a primary minimum tonight above 30° between dusk and
  dawn, brighter than 13 mag?" and compare the list with the service you use today.

## Data used

- Recorded service responses (VSX, Exoplanet Archive, ExoClock) under `tests/data/services/`; JPL Horizons tables
  for the Sun, Moon and planets at two sites; a Tapir output page and an eclipsing-binary prediction page for one
  night as stored references (PLN-14).

## Steps

Order of work: PLN-W, then P1: 1, 2, 3, 4, 5, 6, 7; P2: 8, 9, 10, 11, 13, 14; P3: 12.

### PLN-W. The Planning window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.8: stages Site and night, Targets, Night, Schedule, Send; Inspector for the selected
  target.
- **Extra accept:** from an empty window: "What can I observe tonight?" → pick three results → chart → schedule →
  "Send to Observing": **six clicks**; no site set → the first stage says so and opens the profile.
- **Depends on:** ARC-4.5, ARC-5, ARC-6, ARC-8, ARC-16, UI-1 … UI-4.
- **Files:** `ui/planning/{window,controller,state,menus}.py`, `ui/planning/panels/{site,targets,night,schedule,send,inspector}.py`, `tests/ui/walks/planning.py`, guide 02

### PLN-1. Site, horizon and the night  (P1)
**partial** — done (2026-11-14): `planning/night.py`: `summary` (sunset / sunrise at −0.833°, the three dusks and
dawns, dark hours, Moon rise / set / highest / illumination / hours up in the dark, LST at dusk, local midnight and
dawn; polar day and night give None), `month` (dark hours and the Moon per night), `parse_horizon` (two columns,
any separator, comments and header lines skipped), `limit` (the profile, never below the altitude limit). The site
carries its horizon (`Site.horizon`); `planning.night` gives each target its per-time `limit`, the night chart draws
a curve thick only above it and the legend / tables' rise and set use it; the Plan page's "Horizon profile…" loads
a file and keeps it. Tests (tests/test_night.py): equinox day at the equator 12 h 7 min, TUG's order of twilights,
68° N midnight Sun and polar night, a target above 20° behind an eastern wall not observable, the page's file kept
and sent. Left: the horizon drawn in the charts and an editor, the mount's meridian limits, the month strip in the
window, the four-site comparison with JPL Horizons.
- **Ours now:** `planning/visibility.night` (twilights, interpolated crossings), `moon`, `Site`; `devices/safety.Rules.horizon` (a horizon profile exists for safety only).
- **Read first:** Meeus, *Astronomical Algorithms* (twilight, rising and setting with refraction); the USNO
  definitions of twilights; Astropy's `AltAz` refraction parameters; JSkyCalc's almanac output (what observers
  expect to see).
- **Build:** the night summary for a date (local evening date; the date line and polar day / night handled):
  sunset, civil / nautical / astronomical dusk and dawn, sunrise, darkness hours; Moon rise / set, phase,
  illumination, and altitude through the night; local sidereal time at dusk, midnight, dawn; times shown in local
  time, UT and LST together (axis choice in the chart); the horizon profile from the site (azimuth–altitude pairs,
  drawn in charts and used in every observability computation) with an editor (table and a drag-on-the-sky-map
  mode) and import of common horizon files; minimum altitude and the mount's limits (meridian limits for German
  mounts from the equipment profile); a month view: darkness and Moon for each night (to choose nights).
- **Accept:** sunset / twilight / moonrise for four sites (equator, mid-latitude both hemispheres, 68° N in
  summer and winter) within 1 minute of JPL Horizons; a target behind a horizon obstruction is "not observable"
  there although above the altitude limit; four-language date and time formats correct.
- **Files:** `planning/night.py`, `visibility.py`, UI, tests.

### PLN-2. Target lists that remember  (P1)
**open**
- **Ours now:** `planning/targets.py` (`Resolver` with a local cache, SIMBAD, solar-system bodies), the Planning window's target table.
- **Build:** the target table (kit `TableView`): name, aliases, coordinates (ICRS; proper motion applied to the
  date), type, magnitudes (band, source), ephemeris (period, epoch, standard, uncertainty, source), event duration
  and depth, priority, per-target constraints (minimum altitude, maximum airmass, Moon separation, time or phase
  windows), exposure plan (filters, times), notes, "last observed" and "nights observed" (from the project's
  frames and the observing log, PLN-13); lists saved in the project and in a personal library (named lists:
  "my EBs", "ExoClock"); import / export: CSV with a column wizard, our own format, the AAVSO Target Tool's and
  common planetarium list formats where documented; multi-add by pasting names; duplicates merged by position;
  solar-system bodies and minor planets by designation with ephemerides from Horizons for the night.
- **Accept:** a pasted list of 50 names resolves (recorded responses) with the unresolved ones listed and
  editable; a list survives restart and project move; a high-proper-motion star's coordinates at the date differ
  from J2000 by the right amount.
- **Files:** `planning/targets.py`, `planning/target_lists.py`, `ui/planning/panels/targets.py`, `tests/test_target_lists.py`

### PLN-3. The night chart, the sky map, the year  (P1)
**partial** — done (2026-11-14, user feedback UF-1 … UF-5): `ui/plan_chart.py` (altitude and airmass, the twilight
bands with their times, UTC and local rows named with arrows, LST on top, the Moon dashed with its illumination,
the Moon's distance along each curve every hour, rise / set above the limit in the legend, events with ±1σ, the
horizon profile as each curve's floor); `ui/plan_more.py` ("More charts…": the Moon's distance per hour, the sky
map with an hour slider and the Moon's track, the year's night length), `ui/plan_tables.py` (Sun, Moon, and per
target rise, set, highest point, airmass, closest Moon). Left: the meridian and mount limits, the "now" line, the
hover read-out, event bars from ingress to egress with the baseline, the year tab per target (hours observable
per night), the 150 ms redraw budget.
- **Read first:** `staralt`'s plot conventions; astroplan's `plot_airmass` / `plot_sky`; N.I.N.A.'s altitude chart
  (the "risk" shading); colour-blind-safe choices (interface tokens).
- **Ours now:** altitude / airmass curves of several targets with twilight bands and the Moon.
- **Build:** through `PlotView`: altitude (left axis) and airmass (right axis) against time with twilight shading,
  the horizon profile as a filled floor per target azimuth, the Moon's altitude (dashed) and, on each curve, the
  Moon separation labelled at the hours; **events as bars** on the target's curve (ingress → egress in the role
  colour, a thin extension for the baseline wanted before / after, and a lighter band for the ± 1σ timing
  uncertainty); the meridian crossing marked (flip) and the mount's limits; "now" line when the date is today;
  hover read-out (time in three scales, altitude, azimuth, airmass, hour angle, parallactic angle, Moon distance);
  a **sky map** tab (alt-az polar plot with the horizon, the tracks through the night, the Moon, the pole;
  north-up / east-left conventions selectable); a **year** tab per target: hours above the altitude limit in
  darkness for each night of the year (curve) and a time-of-night × date map of altitude — the best season at a
  glance; a table: rise, transit, set (above the limit), hours observable, maximum altitude, Moon distance at
  transit.
- **Accept:** 30 targets redraw in < 150 ms while dragging the date; the event bars equal PLN-4's times; the year
  tab's best date for a star equals the date its right ascension transits at local midnight (± 2 days).
- **Files:** `planning/charts.py` (FigureSpec builders), `planning/visibility.py`, `ui/planning/panels/night.py`, `tests/test_planning_charts.py`

### PLN-4. Events with honest uncertainties  (P1)
**partial** — done (2026-11-14): `planning/events.py`: `sigma` (√(σ_T0² + (Eσ_P)² + 2E cov)), `digits_error` (half
a unit of the last printed digit), `ephemeris_errors`, `annotate`; every event of `planning.night` carries its
epoch and σ in minutes (estimated from the digits when no error is given, and said so); the night chart draws ±1σ
on each event, the events table writes "± 3 min" (≈ when estimated); the Plan page passes the typed T0 and P as
text so their digits count. Tests (tests/test_events.py). Left: errors and covariance from VSX / the Exoplanet
Archive look-ups, the depth, the baseline / Moon / meridian flags, the observability score, the Transit Finder and
prediction-service comparisons.
- **Read first:** Mallonn et al. 2019 and Kokori et al. 2022 (ExoClock: ephemeris drift and how uncertainties grow);
  the VSX field definitions (epoch as HJD, eclipse duration D in per cent of the period, the period's precision
  as given by its digits); the Exoplanet Archive's ephemeris columns and their errors.
- **Ours now:** `visibility.events(t0, period, …)`, `ephemerides.vsx / exoplanet`.
- **Build:** `planning/events.py`: for each target and night the events in darkness (or all, with flags): kind
  (primary / secondary minimum, transit, occultation, maximum, quadrature for velocities), predicted mid-time in
  BJD_TDB converted to UTC and local time for the site, σ of the time = √(σ_T0² + (E σ_P)² + 2 E cov) with missing
  errors estimated from the digits given (stated as estimated), start and end from the duration (VSX's D, the
  transit T14, or our own model), depth; flags: fully in darkness, ingress / egress above the altitude limit,
  baseline available before and after, Moon separation and illumination, meridian crossing inside the event;
  secondary minima at phase 0.5 unless an eccentricity / measured phase is known; time-standard care (HJD catalogue
  epochs → BJD_TDB with the stated approximation); an "observability score" 0–1 used by the finder and the
  scheduler.
- **Accept:** for ten planets the predicted mid-times and windows equal the stored Transit Finder page for the
  same site and night within 1 minute; for ten eclipsing binaries the stored prediction service page within 2
  minutes; σ grows correctly with epochs since T0 (test against the formula on synthetic ephemerides).
- **Files:** `planning/events.py` (from `visibility.events`, re-exported), `planning/ephemerides.py`, `tests/test_events.py`

### PLN-5. "What can I observe tonight?"  (P1)
**partial** — done (2026-11-14), the engine of item 2 and 5: `planning/finder.py` `tonight_events` (filters by
magnitude, period, kind, depth and the declinations the site can reach before any astronomy; every event of the
night at once, primary and secondary; altitudes at start, middle and end in one call; whole-event or mid-event
rule; a score by the lowest altitude, primaries first, with its reason in words). Tests (tests/test_finder.py):
the same events as `planning.night` for the same stars; a 40 000-star table in ~5 s. Left: the VSX / Exoplanet
Archive / ExoClock packs (item 1), the Moon / uncertainty / "not observed lately" filters, the ranking by
expected S/N and priority, the results table and "Add to tonight's list", the stored-page comparisons.
- **Why:** the question every observer asks first; today answered by three web sites that do not know the
  observer's horizon or equipment.
- **Read first:** the Transit Finder's filter list; the prediction services' filters (type, magnitude, declination,
  minimum altitude); VSX's table on VizieR (B/vsx: columns, types, the share with usable ephemerides); the ExoClock
  priority scheme (low / medium / high / alert) and the public TOI table's ephemeris columns.
- **Build:**
  1. Data: `services` + a data pack "variable-star ephemerides" built by `tools/build_vsx_pack.py` from the public
     VSX table (objects with period and epoch; types grouped: eclipsing EA / EB / EW and subtypes, pulsating by
     class, others), refreshed on request; transiting planets from the Exoplanet Archive and ExoClock (cached
     table); TOIs from ExoFOP with their ephemeris uncertainties.
  2. `planning/finder.py`: filters — kind (eclipsing minima: primary / secondary; transits; maxima), type classes,
     magnitude range (in a band), declination limits from the site, minimum altitude at mid-event and at both
     contacts, event wholly in darkness (or ≥ x %), minimum depth, period range, minimum Moon distance, maximum
     timing uncertainty, "not observed by me in the last N days", "few recent minima in the databases" (when OC-4's
     services are reachable: the date of the newest minimum per star) and ExoClock priority.
  3. Ranking by the observability score × the expected signal-to-noise for the active equipment (EXO-14 /
     PLN-6: depth against predicted precision) × priority; ties by altitude.
  4. Results table with a mini altitude curve per row, the event bar, depth, duration, magnitude, score and the
     reason for the rank in words; multi-select → "Add to tonight's list".
  5. Speed: the whole VSX pack for one night with a vectorised pre-filter (declination, magnitude, period) then
     event times: < 5 s.
- **Accept:** for a stored night and site the eclipsing-binary list contains every star of the stored prediction
  page that passes the same filters (and explains each extra or missing one by a filter difference); the planet
  list equals the stored Transit Finder page under the same constraints; offline after one online refresh.
- **Files:** `planning/finder.py`, `tools/build_vsx_pack.py`, `core/datapacks.py` entry, UI, tests, guide 02.

### PLN-6. Exposure, precision and framing for photometry  (P1)
**partial** — done (2026-11-14), the framing engine: `planning/framing.py` `suggest` (the pointing offset and, when
the camera turns, the angle that keep the target well inside and the most comparison-star weight inside the
frame's margins; the target nearer the middle breaks ties) and `inside`. Tests (tests/test_framing.py): eight good
stars east of NY Vir — centred keeps fewer than 6, the suggestion keeps ≥ 6 and moves east; a north–south line of
stars needs the camera turned. Left: the comparison stars from PHO-17's rules on the field, the survey image, the
bad columns, writing the pointing into the target's plan; the exposure part (zero points from the user's frames,
the Moon's sky, the noise budget, defocus) and its real-night checks.
- **Read first:** Howell 2006 ch. 4; Young 1967 and Osborn et al. 2015 (scintillation); Southworth et al. 2009
  (defocused photometry: why and how much); Collins et al. 2017 §appendix (what limits ground-based precision).
- **Ours now:** `planning/exposure.py` (S/N and exposure from a typed zero point), a dialog.
- **Build:** the calculator fed by the equipment profile: zero points per filter **measured from the user's own
  frames** (IMG-5.4 writes them to the profile with date and airmass) or estimated from aperture, throughput and
  quantum efficiency when none exists (marked as an estimate); sky brightness from the site profile and the Moon
  (Krisciunas & Schaefer 1991 model for the Moon's contribution); outputs: counts at the peak for the seeing and
  focus (so: the exposure that reaches 60 % of the linearity limit), S/N per exposure with the noise budget (photon,
  sky, read, dark, scintillation), precision per transit / per minimum timing for the chosen cadence, the
  recommended defocus when the star saturates in less than the read-out time allows; **framing**: the field of the
  sensor on a survey image (DSS / Pan-STARRS through `services`) with rotation, the target and the comparison
  stars chosen by PHO-17's rules for that field, and a suggested pointing offset / rotation that keeps the target
  and the best comparison set inside the frame away from edges and known bad columns (from the bad-pixel mask in
  the library) — written into the target's plan (centre coordinates, rotation) for Observing.
- **Accept:** predicted peak counts and S/N for the Qatar-1 and HAT-P-32 nights (their real zero points) within
  25 % and 20 % of the frames' measured values; the suggested framing for NY Vir's field keeps ≥ 6 rule-passing
  comparison stars where the target-centred frame keeps fewer (asserted on the catalogue).
- **Files:** `planning/exposure.py`, `planning/framing.py`, `photometry/comprules.py` (used), `services/hips2fits.py`, `ui/planning/panels/inspector.py`, `tests/test_framing.py`

### PLN-7. The schedule  (P1)
**partial** — done (2026-11-14): `schedule.plan` (the schedule with an overhead block at each change of target —
taken from a filler, never from an event's window — the events left out with the target that holds their time,
and the hours per target, overheads and idle); the Plan page shows the overheads in the schedule table, sends only
the observing blocks, and says the totals and what was left out. Test (tests/test_schedule.py). Left: overheads
from the equipment profile (slew rate, autofocus, filter changes, read-out, meridian flip), the merit function and
its brute-force check, calibration blocks, the editable timeline, the N.I.N.A. / ACP exports.
- **Read first:** Morris et al. 2018 §4 (scoring and the priority scheduler; transition times); the Ekos and ACP
  scheduler documentation (constraints, priorities, twilight rules) for what users expect.
- **Ours now:** `schedule.schedule(night, targets, min_alt, block_min, baseline_min)`.
- **Build:** `planning/scheduler.py`: blocks = (target, start, end, purpose, exposure plan); fixed blocks for
  time-critical events with their baselines (conflicts resolved by priority and score, the loser listed with the
  reason); the free time filled by a merit function (priority, altitude / airmass, setting soonest, Moon distance,
  time still needed this season) with minimum and maximum block lengths; **overheads** from the equipment profile
  (slew rate, settle, plate-solve centring, autofocus, filter change, read-out, meridian flip) inserted as their own
  thin blocks so that the times are real; calibration blocks (sky flats at dusk / dawn in filter order from
  narrowest to widest in the evening, standards from PLN-9, darks at the end); a timeline the user can edit (drag
  edges, reorder, delete, lock), with every violation of a constraint flagged at once; totals (time on each
  target, idle time); export: to Observing (the sequencer's instruction tree, OBS-6), as a table (CSV / PDF night
  plan with charts), and as a N.I.N.A. advanced-sequence file and an ACP plan where their formats are documented
  well enough (for observers who run those).
- **Accept:** a synthetic night with two overlapping events and five filler targets: the schedule respects every
  constraint, includes overheads, and equals a brute-force optimum of the merit function within 5 % on a small
  case; dragging a block updates conflicts in < 50 ms; the exported sequence runs in the simulator (OBS-16) to the
  planned times within a minute.
- **Files:** `planning/scheduler.py` (from `schedule.py`, re-exported), `planning/export_{nina,acp}.py`, `ui/planning/panels/schedule.py`, `tests/test_scheduler.py`

### PLN-8. Phase coverage over many nights  (P2)
**partial** — done (2026-11-14), the engine: `planning/phase_coverage.py` (`covered`: the phase bins the data hold;
`windows`: each dark, high-enough stretch of the next N nights with the share of the missing bins it covers, best
first; `commensurability`: weeks until a period near a whole day drifts round). Tests
(tests/test_phase_coverage.py): history over 0–0.4 → only stretches reaching 0.4–1.0, ordered by the share;
P = 1.0003 d flagged (hundreds of weeks). Left: the phases read from the project's light curves and velocities,
the phase wheel and bar, "Add the best three windows", the RV quadratures and Fisher score, both minima and maxima.
- **Why:** an orbit or a full light curve needs all phases; nobody plans that for the observer.
- **Build:** for a periodic target: the phases already covered, read from the project's light curves and velocity
  tables (or typed), drawn as a phase wheel and a bar; the gaps; for the next N nights at the site the times when
  each missing phase range is observable (altitude, darkness, Moon), ranked; "Add the best three windows to my
  plans"; for radial-velocity work the quadratures and the phases that most constrain e and K (from the current
  orbit's Fisher information — a simple derivative-based score), for eclipsing binaries both minima and the
  maxima.
- **Accept:** synthetic history covering phases 0–0.4: the planner proposes only windows in 0.4–1.0 and orders them
  by the stated score; a period commensurable with the day (P = 1.0003 d) is flagged "phase gaps close only after
  N weeks".
- **Files:** `planning/phase_coverage.py`, `ui/planning/panels/coverage.py`, `tests/test_phase_coverage.py`

### PLN-9. Standards and calibration targets  (P2)
**open**
- **Build:** lists as data with sources: Landolt and Stetson photometric standard fields, spectrophotometric
  standards (the SPE-10 pack's names), telluric standards (bright, hot, rapidly rotating stars from a published
  list), radial-velocity standards, polarimetric standards, blank fields for sky flats; for a target and its
  observing window: the standards that will be at the same airmass (± 0.1) close in time and azimuth, and a pair
  bracketing the night's airmass range for an extinction solution; inserted into the schedule as blocks.
- **Accept:** for a stored night the suggested telluric standard's airmass matches the target's within 0.1 at the
  proposed time; lists carry their references.
- **Files:** `planning/standards.py`, `resources/data/standards/*.ecsv` (with references), `tests/test_standards.py`

### PLN-10. Finder charts, field preview, mosaics  (P2)
**partial** — done (2026-11-14): `planning/framing.mosaic` (rows × columns on one tangent plane about the centre,
the chosen overlap and rotation, each panel's camera angle turned by the plane's north there) and `_unplane`.
Test (tests/test_framing.py): a 2 × 3 mosaic at declinations 10° and 85° overlaps by 15 % within 1 % between every
pair of neighbours in their own planes, not slid sideways; near the pole the panels turn. Left: the survey image
with the footprints, guider footprint, bright-star warnings, guide stars, the panels as targets, printable charts.
- **Build:** the Inspector's field view: survey image with the sensor footprint (and guider / off-axis-guider
  footprint from the profile), rotation handle, bright-star warnings (glare, diffraction, saturation trails for the
  camera), guide-star availability; mosaic panels for large objects (rows × columns, overlap, rotation) each
  becoming a target; printable finder charts (IMG-11).
- **Accept:** footprints agree with the plate scale and a real frame's solved corners within 1 %; a 2 × 3 mosaic's
  panels overlap by the chosen 15 % everywhere (spherical geometry test at declination 85°).
- **Files:** `planning/framing.py`, `images/chart.py`, `ui/planning/panels/inspector.py`, `tests/test_footprints.py`
- **Notes from the sources (architect, 2026-11-10):** N.I.N.A. 3.2 ships an optional offline sky-map cache (3.3 GB)
  so that framing works without a network; ours: survey cut-outs are cached per field by `services` (ARC-14), and
  an optional low-resolution all-sky pack is listed in the data manager (ARC-20) only if its source's licence
  allows redistribution — decide and write the source here.

### PLN-11. Weather and sky conditions  (P2)
**partial** — done (2026-11-14): the service chosen is **Open-Meteo** (free for non-commercial use, data CC BY 4.0;
attribution "Weather data by Open-Meteo.com (CC BY 4.0)" shown with every forecast). `services/forecast.py` (hourly
total / low / middle / high cloud, humidity, dew point, wind, temperature for the site; cached one hour; offline
gives the last answer; `during` reads a block's mean cloud); "More charts…" → Weather: "Get the forecast" (off the
window's thread) draws the clouds and humidity over the night's twilight shading with the fetch time and the
attribution. Tests (tests/test_forecast.py, test_plan_chart). Left: the bands under the main chart, the
scheduler's "cloud < x %" per block, seeing / transparency classes.
- **Read first:** the terms of use of free forecast services (Open-Meteo, 7Timer! astronomy forecast) — use only
  one whose terms allow this application; write the choice and its attribution here.
- **Build:** `services/forecast.py`: hourly cloud cover (low / mid / high), humidity, dew point, wind, temperature,
  and seeing / transparency classes where offered, for the site; drawn as bands under the night chart; the
  scheduler can require "cloud < x %" per block and shows the risk; refreshed on request and when the window opens
  (cached 1 hour); clearly labelled as a forecast with its source and issue time.
- **Accept:** recorded responses parse; offline shows the last forecast with its age; the attribution text is
  shown.
- **Files:** `services/forecast.py`, `ui/planning/panels/night.py`, `tests/test_forecast.py`

### PLN-12. Alerts and campaigns  (P3)
**open**
- **Build:** target sources from public feeds where terms allow (AAVSO alert notices and campaigns, the Transient
  Name Server's public list, Gaia Science Alerts, ExoClock alerts): a "News" tab listing items with coordinates
  observable from the site tonight; one click adds a target. Each feed optional and off by default.
- **Accept:** recorded feed samples parse into targets; nothing is fetched unless a feed is switched on.
- **Files:** `services/feeds_*.py`, `ui/planning/panels/news.py`, tests with recorded samples

### PLN-13. The observing log and the night report  (P2)
**partial** — done (2026-11-14), the engine: `planning/obslog.py` (`frames_from_headers`: target, mid-time,
exposure, filter, airmass, and the night named by its evening at the site's longitude; `night_log`: spans per night
and target, a pause over an hour starts a new one; `coverage`: whole / ingress / egress / middle; `statistics`;
`to_csv`). Tests (tests/test_obslog.py): a night across midnight UTC stays one night, two spans after a pause,
filters, exposure and airmass range, the CSV. Left: Observing's event log and the conditions (FWHM, sky), the
calendar view, the night report (PDF / HTML), "last observed" in the target lists, the practice and public nights.
- **Build:** from the project's frames (headers) and Observing's event log: per night and target the time spans
  observed, filters, exposure counts, airmass range, conditions (FWHM, sky, transparency from PHO-33 / IMG-4),
  events caught (whole / ingress only / egress only), problems; a calendar view; statistics (hours per month, per
  target, clear-night fraction); export of a night report (PDF / HTML) and of the log (CSV); "last observed"
  columns for PLN-2 and PLN-5.
- **Accept:** the practice night and two public nights produce the right spans and event coverage; the report
  compiles.
- **Files:** `planning/obslog.py`, `engine/project.py` (queries), `ui/planning/panels/log.py`, `tests/test_obslog.py`

### PLN-14. Validation  (P2)
**open**
- **Build:** tests with stored references: almanac values against JPL Horizons (have for altitudes: extend to
  twilights, Moon, four sites); events against the stored Transit Finder and eclipsing-binary prediction pages;
  the exposure predictor against real nights (PLN-6's accept); the scheduler's times against a simulated run
  (OBS-16).
- **Accept:** `pytest -m validation` covers almanac, events, exposure and schedule.
- **Files:** `tests/validation/test_planning_*.py`, `tests/validation/data/planning/` (stored reference pages and Horizons tables)

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
