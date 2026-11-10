# Observing: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.9).

## Rules card (the same in every plan file; the full rules are PLAN.md R1–R12)

1. Read PLAN.md, this file's "Conventions" and "Definition of done", your area file, and `plans/interface.md` before
   you touch anything the user sees.
2. Claim the step in its file and push before starting; one step at a time; push at least hourly; mark it done with
   the commit, or `partly done` with what is missing.
3. Build every bullet, show every Accept line. No silent scope cuts: doubts go under "Questions for the architect".
4. Research first (papers, reference programs' source); learn, never copy; nothing GPL bundled.
5. Synthetic test with known truth **and** real data against a reference; the reference numbers become a test.
6. Use the program as a user (real clicks, screenshots in four languages, looked at) before calling it done.
7. Only kit components in the interface; workflow first; one primary action; tooltips; undo; nothing locked.
8. Errors by code, saying what happened and what to do, translated (tr, de, es: 0 unfinished). Guide updated.
9. Measure time and memory; meet the budget; CPU and GPU paths give the same result.
10. Commits in the owner's name only, no "Claude" anywhere; everything to `main`; never delete without the owner.

## Scope and goal

Running the telescope for science: devices (mount, camera, focuser, filter wheel, rotator, guider, dome or roof,
covers, switches, weather, safety), time, pointing, focus, guiding, sequences, flats, safety and unattended nights,
live quality and light curves, remote use — and a simulated observatory to practise and to test.

**Goal:** the equipment coverage and sequencer of N.I.N.A., the observatory integration of MaxIm DL, the
unattended reliability of Ekos / ACP — tuned for **time-series science**, which none of them is: accurate time
stamps that are checked, exposures kept in the linear range, no refocus or flip in the middle of an ingress, the
light curve growing as the frames arrive.

**Safety comes before every feature here.** The supervisor fails closed (when in doubt: stop, park, close). No
step may weaken a safety rule; every new action goes through `Observatory`'s guarded calls; every step's tests
include its failure cases with the simulators.

## What the reference programs do

Read: N.I.N.A. (MPL-2; `NINA.Sequencer`: the instruction, condition and trigger classes — connect / cool / slew /
centre / rotate / focus / filter / expose / dither / flats / park / dome / switches / waits for time, altitude,
Sun and Moon altitude, safety; triggers for autofocus after time, temperature change, HFR increase, filter change,
exposures; meridian flip; centre after drift; dither after exposures; dome synchronisation; reconnect on failure;
`NINA.Equipment`, `NINA.Astrometry`, the autofocus and flat-wizard descriptions, the imaging tab's panels); MaxIm DL
manual (Camera Control: expose / guide / setup tabs, sequences; Observatory window: telescope, dome, focuser,
rotator, weather, all-sky and zoom views; autofocus; multi-star guiding; pier-flip handling); KStars / Ekos
(scheduler with constraints and priorities, capture, focus algorithms: linear 1-pass with curve fits, align with
astrometry.net, guide, dome and weather handling, the Analyze timeline); ACP / SGP / Voyager descriptions of
unattended operation; PHD2's event-server documentation; the ASCOM interface standards (Platform 7: telescope,
camera, focuser, filter wheel, rotator, dome, safety monitor, observing conditions, switch, cover calibrator;
Alpaca REST and discovery; the `ImageBytes` transfer) and the INDI protocol and standard properties.

| Topic | N.I.N.A. | MaxIm DL | Ekos | Ours now |
| --- | --- | --- | --- | --- |
| Devices | ASCOM (COM and Alpaca), native camera SDKs | ASCOM, native cameras | INDI | Alpaca (alpyca) and INDI (own client) for telescope, camera, filter wheel, focuser, dome, weather; rotator; no COM |
| Sequencing | simple target list; advanced tree with loops, conditions, triggers; templates | sequence table with autosave | scheduler + capture queues | targets with exposure rows, time windows (dusk / dawn / UTC), repeat until the end, dither |
| Focus | overshoot, curve fits (hyperbolic, parabolic, trend lines), star HFR or contrast, triggers, filter offsets | V-curve autofocus | several algorithms, per-filter offsets | HFR V-curve with a hyperbola fit; per-filter offsets; temperature following |
| Pointing | plate solve, sync, centre, rotate; framing assistant; three-point polar alignment (plug-in) | PinPoint solve and sync | align module, polar alignment assistant | centre by solving (slew, solve, sync, repeat); polar alignment error from three solves |
| Guiding | PHD2 and others; dither; guide graph | built-in, multi-star | internal or PHD2 | PHD2: guide, dither with settling, stop |
| Meridian flip | automatic with re-centre and guiding restart; pause windows | automatic with guide-star reacquisition | automatic | `needs_flip` and a flip in sequences |
| Flats | flat wizard (sky, panel; target ADU), trained exposures | — | flat capture to ADU | sky flats with auto exposure; panel flats |
| Safety / weather | safety monitor conditions and triggers | weather and dome links | weather, dome, scheduler shutdown | rules (Sun, altitude, weather, link age), supervisor that parks at unsafe and at sunrise, fail-closed |
| Live information | HFR and star-count history, statistics, guide graph, image history | information windows | Analyze timeline | device state line, log, preview |
| Time | — | — | — | DATE-OBS from the computer clock |
| Remote | — (plug-ins) | COM scripting | client / server by INDI | separate observatory process with token and pinned TLS; frames copied back |

## What we already have (do not redo)

- `devices/`: `observatory.py` (guarded calls, `slew`, `park`, `check`, supervisor), `safety.py` (rules), `indi.py`,
  Alpaca through alpyca, `sequence.py` (exposures with full headers, filters, focus offsets and temperature focus,
  rotator, dither, sky and panel flats, `tonight`, time windows), `focus.py` (HFR, V-curve, meridian flip need),
  `phd2.py`, `pointing.py`, `server.py` + `client.py` + `tls.py` + `setup.py` (discovery, configuration, problems),
  the Observing window with menus Devices, Telescope, Camera, Focus, Flats, Sequence; tests with fake devices and
  with the INDI simulators in CI.

## Decisions

- The observatory stays a **separate process** that keeps the telescope safe when the window closes or crashes.
- Three device back-ends behind one interface: Alpaca, INDI, and **ASCOM COM on Windows** (OBS-1); native camera
  SDKs are not bundled (licences and maintenance) — cameras come through their ASCOM / Alpaca / INDI drivers.
- Guiding stays with PHD2 (the standard); we add supervision, graphs and science-frame drift correction.
- Every exposure's header states the time system, the mid-exposure time, the clock offset measured that night and
  the camera's time-stamp convention (OBS-2).
- A **simulated observatory** (OBS-16) is a user feature, not only a test tool.

## To ask the owner

- The owner's equipment (mount, camera, focuser, filter wheel, dome or roof, weather sensors; operating system of
  the telescope computer; which drivers) — decides the order of OBS-1's back-ends and the hardware checklist.

## For the owner to try (with real hardware; each item says what to send back)

- After OBS-1: connect every device; send the device report file (Help → "Device report").
- After OBS-2: the clock check's reading over one night (the log).
- After OBS-6 and OBS-16: run tomorrow night's sequence first in the simulator, then on the telescope; send the
  night report.

## Data used

- Simulators: INDI simulators (CI job exists); ASCOM Alpaca simulators (the ASCOM "OmniSim", cross-platform) to add
  to CI; our own simulated observatory (OBS-16); recorded PHD2 event streams.

## Steps

Order of work: OBS-W, then P1: 1, 2, 3, 4, 6, 7, 8, 10, 11, 16, 17, 18; P2: 5, 9, 12, 13, 14; P3: 15, 19.

### OBS-W. The Observing window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.9: device chips with popovers, stages Connect, Point, Focus, Sequence, Night; the last
  frame with statistics; result tabs Sequence, Graphs, Live light curve, Log; a "Stop everything" button always
  visible.
- **Extra accept:** in the simulator: connect all → slew and centre → autofocus → start a three-filter sequence →
  watch the live graphs: every state fits 1366 × 768 in four languages; no address, token or certificate is on the
  main face; "Stop everything" works from every state within 2 s (test with slow fake devices).
- **Depends on:** ARC-4.5, ARC-5, ARC-6, ARC-7, UI-1 … UI-4, OBS-16.

### OBS-1. Devices: one interface, three back-ends, every capability known  (P1)
**open**
- **Read first:** the ASCOM interface documentation (each device type's properties and methods, the `Can…`
  capability flags, error codes, the asynchronous operation rules of Platform 7); the Alpaca API reference and
  `ImageBytes`; the INDI standard properties list; N.I.N.A.'s `NINA.Equipment` (how it handles drivers that lie or
  hang: time-outs, reconnects).
- **Ours now:** duck-typed ASCOM-style objects (alpyca or INDI adapters).
- **Build:**
  1. `devices/api.py`: typed interfaces per device kind (Telescope, Camera, Focuser, FilterWheel, Rotator, Dome,
     CoverCalibrator, Switch, ObservingConditions, SafetyMonitor, Guider) with capability records (can park, can
     pulse-guide, can set tracking rates, side of pier readable, gain range, read-out modes, sub-frame, cooler,
     absolute / relative focuser, temperature probe, …) queried once at connection.
  2. Back-ends: `alpaca.py` (alpyca; image download through `ImageBytes`), `indi.py` (have; complete the standard
     properties: gain / offset, read-out mode, frame type, cooler power, rotator, dome with shutter and slaving,
     weather, dust cap / flat light, switches), `ascom_com.py` (Windows only: `win32com` / `comtypes` — check the
     licence and add as a Windows-only dependency; the ASCOM Chooser dialog; calls marshalled to one worker thread
     per device because COM drivers are apartment-threaded).
  3. Robustness for every call: time-out, classification of errors (not connected, not implemented, invalid value,
     driver fault), retry policy per call kind (never retry a slew or a shutter command blindly), automatic
     reconnect with back-off, a per-device health state (ok / slow / lost) feeding the supervisor's link rule.
  4. Camera specifics: cool-down and warm-up ramps (°C per minute from the profile), gain / offset / read-out mode
     selection by name, binning and sub-frame validation, bit depth and maximum ADU, electrons per ADU reported by
     the driver compared with the profile, Bayer pattern and offsets, download time measured (enters the
     scheduler's overheads), exposure abort that really stops.
  5. Set-up: discovery (Alpaca UDP: have; INDI server scan; COM registry list), a device picker per kind, a
     "Test this device" button running a safe self-test (connect, read state, small reversible action when the user
     confirms — e.g. focuser +10 / −10 steps), and a **device report** (capabilities, driver versions, timings) as
     a file for support.
  6. Tests against three simulator families in CI: INDI simulators (have), ASCOM Alpaca simulators (Linux), and on
     the Windows runner the ASCOM Platform's COM simulators when installable there; plus our fakes for failure
     injection (hang, wrong value, disconnect mid-exposure).
- **Accept:** the same scenario script (connect, cool, slew, expose 5 frames with filter changes, focus move,
  park) passes on all three back-ends; every injected failure ends in a safe, explained state (error code with
  what to do) and never in a hang (each call returns within its time-out + 1 s); image download of a 6k × 4k
  16-bit frame over Alpaca `ImageBytes` < 2 s on localhost.
- **Files:** `devices/{api,alpaca,indi,ascom_com,health}.py`, `devices/setup.py`, UI set-up dialog, CI jobs, tests.

### OBS-2. Time you can trust  (P1)
**open**
- **Why:** a minimum timed to ± 10 s is worthless if the computer clock is 20 s off; nobody checks.
- **Read first:** RFC 5905 / 4330 (SNTP: the four time stamps, offset and delay); Eastman et al. 2010 §4 (clock
  and time-stamp errors in transit timing); the AAVSO and IOTA guidance on computer time for observers; camera
  makers' notes on exposure-start latency and rolling shutters.
- **Build:**
  1. `devices/clock.py`: an SNTP query (our own small implementation over UDP) to several servers (pool names,
     the user's own; all configurable; none contacted unless the check is on — default on in Observing, asked at
     first connection): offset and round-trip delay, the median of three servers, repeated every 10 minutes during
     a night; GPS time through an ASCOM / INDI GPS device when present.
  2. The offset and its uncertainty on a chip in the device row (green < 0.2 s, amber < 1 s, red beyond) with the
     advice ("synchronise the computer clock: …" per operating system); a setting to **correct** the time stamps by
     the measured offset (off by default: the header then carries both the raw and the corrected time).
  3. Headers of every frame: `DATE-OBS` (start, UTC), `DATE-AVG` (mid-exposure), `DATE-END`, `TIMESYS = 'UTC'`,
     `CLKOFFS` and `CLKUNC` (seconds; measured offset and uncertainty), `CLKSRC` (ntp | gps | none), `TIMEREF`
     (start-of-exposure stamp taken before the command / from the driver's `LastExposureStartTime`), `SHUTDLY`
     (profile), `EXPTIME` requested and `EXPREAL` actual (driver's last exposure duration).
  4. Latency: the start stamp is taken as close to the shutter as the driver allows (the driver's own start time
     when it gives one; otherwise our command time with the measured command latency) and the choice is recorded;
     a tool to measure the camera's latency with a blinking LED / GPS flasher is described in the guide (not
     required).
  5. `timing.mid_time` reads these keywords first.
- **Accept:** against a local fake SNTP server with a known offset the reading is within 20 ms; a simulated clock
  jump during a night is flagged in the log and the headers; frames written by the sequence carry all keywords and
  Photometry's BJD uses the corrected mid-time when the setting is on (test end to end in the simulator).
- **Files:** `devices/clock.py`, `sequence.py` (headers), `timing.py`, UI chip, tests, guide 03.

### OBS-3. Pointing, framing and the preview  (P1)
**open**
- **Ours now:** slew with safety checks; `pointing.center` (solve, sync, repeat); preview frame.
- **Build:** the Point stage: target from Planning (with its framing: centre offset and rotation, PLN-6 / PLN-10)
  or typed / resolved; "Slew and centre" (plate solve through AST-1 with continuity hints; tolerance in arcsec;
  sync or offset mode for mounts that must not be synced); rotation: command the rotator, or tell the user the
  manual turn needed and re-measure; a **live preview loop** (continuous short exposures, optional sub-frame and
  binning) with crosshair, the framing rectangle, HFR / star count / peak read-outs, auto-stretch; "Solve where I
  am" to see the field's name and offset; nudge buttons at chosen rates; the last solved field drawn on the sky
  map; limits respected (horizon profile, meridian limits) with the reason shown when a slew is refused.
- **Accept:** in the simulator the target lands within 5″ and 0.3° of rotation in ≤ 3 iterations for mount errors
  up to 1°; a refused slew explains itself in four languages; the preview loop runs at ≥ 1 frame per second for a
  1 s sub-frame without leaking memory over 1000 frames.

### OBS-4. Focus that holds through the night  (P1)
**open**
- **Read first:** Weber & Brady 2001 (the V-curve); the documentation of N.I.N.A.'s autofocus (overshoot /
  backlash compensation, hyperbolic, parabolic and trend-line fits, star HFR over the whole frame, R² as quality)
  and of Ekos' linear 1-pass algorithm with Levenberg–Marquardt curve fits; the critical-focus-zone formula (CFZ =
  4.88 λ f²).
- **Ours now:** `focus.autofocus` (positions around the current one, median HFR, hyperbola fit, refuses to
  extrapolate), filter offsets, temperature following.
- **Build:** backlash handling (approach every position from the same side with an overshoot from the profile);
  step size from the critical focus zone (aperture, focal ratio, focuser step size) with a wizard that measures
  the V-curve slopes once; fits: hyperbola (default), parabola, trend lines, with weights from the HFR scatter and
  an R² / residual quality gate (retry once with wider range, then restore the old position and report); several
  exposures per point; whole-frame median HFR with outlier rejection, or a chosen star for sparse fields;
  per-filter offset wizard (focus each filter in turn, store the offsets with their scatter); temperature
  coefficient from the night logs (focus position against temperature: regression offered to the profile);
  triggers used by the sequencer (OBS-6): after ΔT, after HFR rises by x %, every N minutes, on filter change
  (offset only or full run), after a flip — each suppressed inside a protected event window (OBS-7); a focus
  history graph (position, temperature, HFR against time).
- **Accept:** in the simulator (a focuser with 80 steps of backlash and a temperature drift): autofocus ends
  within 0.2 CFZ of best focus in ≥ 95 of 100 runs; a clouded run (no stars) restores the previous position and
  says why; filter offsets recovered within their scatter.

### OBS-5. Guiding supervised, and drift held without a guider  (P2)
**open**
- **Read first:** the PHD2 event-server documentation (events `GuideStep`, `StarLost`, `SettleDone`, `Paused`,
  `Alert`; methods `guide`, `dither`, `get_pixel_scale`, `set_paused`); N.I.N.A.'s "centre after drift" trigger.
- **Ours now:** `phd2.PHD2`: guide, dither, stop, state.
- **Build:** subscribe to PHD2's events: RMS in RA / Dec / total in arcsec over a sliding window, the guide graph
  (Graphs tab), star-lost handling (pause exposures, wait for recovery up to a limit, then re-acquire: stop guiding,
  re-centre by solving, restart guiding and settling, resume; all logged), settling before every exposure after a
  dither or slew; per-frame guiding RMS in the header (`GUIDERMS`); dither policy by purpose: **off by default for
  time-series photometry** (stars stay on the same pixels), on for stacks; **science-frame drift correction** when
  there is no guider or to hold the field to a pixel: the field offset measured on each science frame against the
  first (the registration PHO already does) → small corrections by pulse guiding or offset slews when the drift
  exceeds a threshold, never during an exposure.
- **Accept:** with a recorded PHD2 event stream the RMS equals PHD2's own log values within 2 %; a simulated star
  loss pauses and recovers the sequence; in the simulator a mount drifting 20″ per hour is held within 2 px over
  six hours by the science-frame correction.

### OBS-6. The sequencer: simple by default, complete when needed  (P1)
**open**
- **Read first:** N.I.N.A.'s advanced sequencer concepts (containers: sequential, parallel; instructions;
  conditions that end loops; triggers that fire between instructions; templates) and its simple sequencer; Ekos'
  scheduler job states; our `sequence.run`.
- **Ours now:** targets × exposure rows, time windows, repeat until the end; a table in the window.
- **Build:**
  1. `devices/program.py`: a sequence is a tree: **blocks** (target block: slew, centre, rotate, focus, start
     guiding; loop block with end conditions; calibration block; end-of-night block), **instructions** (expose
     N × t in filter F with binning / gain / read-out mode / sub-frame; filter cycle; wait until time / Sun
     altitude / target altitude / event time − baseline; dither; autofocus; flats; cool / warm; park / unpark;
     dome and cover actions; switch on / off; run a recipe (ARC-12) on the frames; message to the user),
     **conditions** (until time, until dawn, until altitude < x, N loops, until the event's end + baseline, while
     safe), **triggers** (autofocus rules of OBS-4, meridian flip, re-centre on drift, dither every N, refocus on
     filter change, pause on unsafe and resume when safe for M minutes). JSON on disk, versioned; today's sequence
     files load into it.
  2. The **simple view** stays the default: a target list with exposure rows (today's table, kit `TableView`) —
     it is a tree with standard triggers switched on; "Show the full program" opens the tree editor (blocks as
     nested cards; add from a palette; drag to reorder; each instruction a kit form).
  3. **Check before the night**: a dry run that walks the tree with the planned date: predicted times of every
     block, altitudes, flips, focus runs, flats, the disk space needed, and every problem (target never above the
     limit, event after dawn, filter not in the wheel, exposure beyond the camera's range) listed before the
     telescope moves; the same engine drives the simulator (OBS-16).
  4. Execution in the observatory process: state persisted after every instruction so that a restart **resumes**
     where it stopped; pause / resume / skip instruction / skip block / stop after this exposure; editing a running
     program is allowed for blocks not yet started; every action and decision goes to the night log with its
     reason.
  5. Templates for science: "Time series of one target (one filter)", "Time series cycling B V R", "Eclipse with
     baseline: start 45 min before, end 45 min after", "Transit from Planning's event", "Standards then target",
     "Twilight flats then the plan then darks", "Spectra with arcs before and after".
- **Accept:** every template runs in the simulator to its planned times within a minute; a kill of the observatory
  process mid-sequence resumes at the right instruction with no duplicate file names; the dry run finds each of
  ten seeded problems; a 0.3.4 sequence file loads and runs unchanged.
- **Files:** `devices/{program,executor,dryrun}.py`, `sequence.py` (instructions reuse its functions), server
  endpoints, UI sequence panels, tests, guide 03.

### OBS-7. Science-aware exposures  (P1)
**open**
- **Why:** the features no imaging-oriented program has.
- **Build:** (a) **linear-range guard**: after each frame the peak of the target and of the chosen comparison
  stars (positions from the star list, PHO-7) against the profile's linearity limit; when above 80 % (or below
  15 %) the next exposure time is adjusted by a bounded step (and logged; photometry handles changing exposure
  times) or, if the user prefers fixed exposures, an alarm is raised; (b) **protected windows**: during ingress,
  egress and a margin around mid-event (from Planning's event with its uncertainty) the sequencer does not run
  autofocus, does not flip (it flips early or late — chosen by which loses less of the event — and says so in the
  dry run), does not dither, does not change filters out of the cycle; (c) cadence monitor: actual against planned
  cadence with the causes of gaps; (d) the live light curve (PHO-19) started automatically for time-series
  templates with the star list; (e) a low-transparency pause: when the comparison ensemble's counts fall by more
  than x % (clouds) exposures continue but the log and the graphs mark it, and an optional rule pauses for stacks.
- **Accept:** in the simulator with seeing improving through the night the target's peak stays within 40–80 % of
  the linearity limit; an eclipse straddling the meridian: the flip is placed outside the protected windows and
  the dry run states when; no autofocus starts inside a protected window in 100 randomised runs.

### OBS-8. The meridian flip, completely  (P1)
**open**
- **Build:** the procedure: decide (pier side and hour angle from the mount; limits and "flip after" from the
  profile) → finish the exposure → stop guiding → flip slew (the same coordinates; verify the pier side changed,
  else retry by slewing through the pole side the driver needs) → settle → centre by solving (rotation now differs
  by 180°: the framing and star list are told) → refocus if the rule says → restart guiding with a new star and
  calibration flip → resume; pause before the meridian when the mount cannot track past it; fork and alt-az mounts
  skip it; everything logged; failures end parked and safe with the reason.
- **Accept:** in the simulator (a German mount model with a tracking limit 5° past the meridian): 100 randomised
  sequences flip once each at an allowed time and resume on target within 10″; a mount that refuses to flip leads
  to a safe stop and a clear message.

### OBS-9. Flats and calibration frames without thought  (P2)
**open**
- **Read first:** Tyson & Gal 1993 (twilight flat exposure scaling); N.I.N.A.'s flat wizard (target ADU,
  tolerance, sky and panel modes, trained exposures).
- **Ours now:** `sky_flats` (exposure follows the sky), `panel_flats`.
- **Build:** a flats instruction per filter set: target level as a fraction of the linear range (default 40 %),
  exposure limits, the filter order for dusk and dawn, small dithers between sky flats, the predicted time window
  each filter needs (from the twilight brightness model) shown in the dry run; panel flats with brightness control
  and "trained" exposures stored per filter / binning in the profile; flat-darks and darks matched automatically
  to what was taken (CAL-3) as an end-of-night block with the cover closed or the dome dark; bias only when the
  profile's sensor kind wants them.
- **Accept:** simulator dusk: all requested flats of four filters reach the target level ± 10 % in the predicted
  order; darks matching every exposure time / gain / temperature used that night are scheduled.

### OBS-10. Dome, roof, covers, power, weather, safety  (P1)
**open**
- **Read first:** the ASCOM dome, cover-calibrator, switch, observing-conditions and safety-monitor interfaces;
  the dome-slaving geometry for a German mount offset from the dome centre (the standard derivation, e.g. Toshimi
  Taki's "matrix method" notes or the ASCOM dome-control documents); our `safety.py` rules.
- **Ours now:** safety rules (Sun distance and altitude, target altitude, weather limits, link age), the
  supervisor (parks when unsafe and at sunrise), INDI dome and weather adapters.
- **Build:** dome slaving (azimuth from the mount's pointing with the geometry parameters in the profile: dome
  radius, mount offsets north / east / up, axis distance of a German mount, side of pier), shutter control with
  states; roll-off roofs (park the telescope and verify the park sensor **before** any roof motion; never move the
  roof with the telescope unparked unless the profile says it clears); covers and flat panels; switches (power,
  dew heaters by dew point); the conditions panel (temperature, humidity, dew point, wind, sky temperature / cloud,
  rain, sky quality) with limits from the rules and a history graph; **safety logic** extended, still fail-closed:
  unsafe → finish or abort the exposure by rule, stop guiding, park, close; resume automatically only after "safe"
  for M minutes and only if the user allowed it for the night; a dead observatory-to-window link changes nothing
  (the process is autonomous), a dead device link is unsafe; a hardware watchdog hook (a switch that must be
  toggled every N seconds, for users who have one); notifications (sound, system notification; optional e-mail /
  webhook the user configures) for unsafe, sequence end and failures.
- **Accept:** scenario tests with fakes and simulators: rain during an exposure; a weather sensor that stops
  answering; the Sun rising; a roof that fails to close (alarm, telescope stays parked, repeated attempts by rule);
  a dome that lags (exposures wait until the slit is aligned) — each ends in the documented safe state; slaving
  azimuths equal an independent geometric computation within 0.5° over the sky.

### OBS-11. Live quality, the night log and the night report  (P1)
**open**
- **Build:** per frame, computed in the observatory process on a binned copy (≤ 0.3 s): HFR / FWHM (arcsec with the
  scale), star count, sky median and noise, peak, eccentricity, the registration offset from the first frame;
  graphs (Graphs tab, shared time axis): HFR, star count / transparency, sky, guiding RMS, focus position and
  temperature, camera temperature and cooler power, airmass, the linear-range guard's peak fraction; an image
  history strip (thumbnails with the numbers; click to view; mark bad); the **night log** as a timeline (every
  instruction, trigger, safety event, error with times) and a text; the **night report** at the end (targets and
  time spans, frames per filter, conditions summary, focus and guiding statistics, problems, disk used; PDF / HTML)
  saved with the frames and linked into the project (PLN-13).
- **Accept:** frame statistics agree with IMG-4's full analysis within 10 %; the report of a simulated night lists
  every event of the scenario; graphs with 2000 frames stay interactive.

### OBS-12. Remote and unattended use  (P2)
**open**
- **Ours now:** token + pinned-TLS API; frames copied to the window's computer; the observatory can run headless
  (also on ARM Linux).
- **Build:** a read-only status page served by the observatory process (a single static HTML with the device
  states, the current instruction, the last frame's thumbnail and the graphs' last values; token required) for a
  phone; a session lock (one controlling window at a time; others read-only); automatic start of tonight's program
  at dusk when armed ("armed" is an explicit, visible state that expires after one night); ARC-22's rate limiting;
  frame transfer with resume and checksum; time-zone-proof scheduling (UTC inside).
- **Accept:** two windows connect: the second is read-only until the first releases; the status page shows a
  running simulated night; an armed program starts at dusk and disarms after dawn.

### OBS-13. Pointing models and polar alignment made easy  (P2)
**open**
- **Read first:** Wallace's TPoint terms (index errors, collimation, non-perpendicularity, polar axis misalignment,
  tube flexure); the three-point polar alignment method (have) and continuous-update variants.
- **Build:** a pointing-model run (N plate solves over the sky → fit of the classic six to eight terms → residual
  map; applied to slews for mounts without their own model; the polar-axis terms reported as the alignment error);
  polar alignment assistant with a live loop: after the three-point measurement, continuous solves show the
  remaining error in altitude and azimuth as arrows while the user turns the screws.
- **Accept:** simulator mount with known model terms: recovered within 10 %; pointing RMS after the model < 20″
  from 5′ before; the polar assistant converges to < 1′ in the simulated adjustment.

### OBS-14. Spectroscopy at the telescope  (P2)
**open**
- **Build:** put a star on the slit: the slit's position (pixel line / fibre hole) on the guide or slit-viewing
  camera is stored in the profile; "Centre on the slit" offsets the solved field so that the target lands there;
  the parallactic angle for the moment shown and, with a rotator, set; calibration-lamp control through switches
  with instructions "arc before and after", "lamp flat", and safe sequencing (lamp off before science); standard
  stars from PLN-9 as blocks; exposure monitoring by the counts in the slit-viewer's wings or, for fibre
  spectrographs, by an exposure-meter channel if a device exists (described, optional).
- **Accept:** in the simulator the target lands within 1 px of the slit position; an arc is taken before and after
  each science block and the lamp is verified off.

### OBS-15. Video and lucky imaging capture  (P3)
**open**
- **Build:** fast sub-frame capture to SER with per-frame time stamps (where the driver supports fast streaming),
  for occultations, double stars and planets; drop detection in time stamps; hand-over to PHO-38 / IMG-9.
- **Accept:** 100 fps of a 320 × 240 sub-frame from the simulator camera written with monotonic stamps and no
  drops reported for 60 s.

### OBS-16. The simulated observatory  (P1)
**open**
- **Why:** practise without a telescope, check tomorrow's program today, teach students, and test every feature of
  this file in CI.
- **Build:** `devices/sim/`: a mount (German / fork models, slew rates, pointing errors, periodic error, limits,
  flip behaviour), a camera that **renders the sky** at its pointing: Gaia stars (from `services` or the offline
  pack, AST-2) through the profile's optics and seeing as a Moffat PSF with defocus from the focuser position,
  airmass extinction, sky background with twilight and Moon models, read noise, dark current, bias structure, hot
  pixels, saturation and non-linearity, flat-field vignetting and dust, cosmic rays, tracking drift and guiding
  jitter; **variable sources**: eclipsing binaries and transits from the target's ephemeris with a model from MOD /
  EXO, pulsators as sinusoids, moving asteroids from Horizons; a focuser (backlash, temperature drift), filter
  wheel (per-filter throughput and focus offsets), rotator, dome, weather script (clouds passing, wind, rain
  events from a scenario file), a guider that answers like PHD2; accelerated time (× 1 … × 600) so a night runs in
  minutes; chosen in the set-up dialog as "Simulated observatory" with the user's own equipment profile; frames it
  writes are flagged `SIMULATE = T` in the header and every window shows a "simulated" badge on such data.
- **Accept:** a simulated night of the practice eclipsing binary, reduced by Calibration and Photometry, gives the
  injected time of minimum within its error; the same observing program gives the same frame times in the
  simulator and in the dry run; a full night at × 300 with 500 frames of 2k × 2k runs in < 5 min; data flagged
  simulated cannot be exported to the AAVSO / MPC report writers without an explicit, logged override.
- **Files:** `devices/sim/*.py`, set-up dialog, tests (the scenario suite of OBS-18 runs on it), guide 03.

### OBS-17. Files and headers as other programs expect  (P1)
**open**
- **Read first:** the FITS standard 4.0 (reserved keywords, `DATE-OBS`, `TIMESYS`, `MJD-OBS`); the SBIG / MaxIm DL
  FITS keyword conventions and N.I.N.A.'s header list (what calibration and photometry programs read); the AAVSO
  and BAA recommendations for image headers.
- **Ours now:** the header list in `sequence.py`.
- **Build:** the complete header: OBS-2's time keywords; `OBJECT`, target and telescope coordinates (J2000 and
  apparent), `AIRMASS`, altitude, azimuth, hour angle, `PIERSIDE`, `ROTATANG`; site; observer; telescope / optics
  (aperture, focal length), camera (name, pixel size, binning, gain, offset, read-out mode, set point, sensor
  temperature, cooler power, `EGAIN`, `BAYERPAT`), filter, focus position and temperature; guiding RMS; weather
  values; sequence and program identifiers; `IMAGETYP` in the common spelling set; `SWCREATE`; the frame's
  place in its block; file naming patterns with tokens (object, filter, exposure, date, sequence number, type) and
  per-target / per-night folders (Settings → Files; defaults sort naturally); optional tile-compressed writing;
  free disk space watched (warn at 10 GB, stop cleanly at 1 GB); a checksum per file.
- **Accept:** frames from the simulator calibrate and measure here without any typed information and open with
  correct interpretation in AstroImageJ, Siril and IRAF (their header reads checked in the validation suite by
  small scripts); a disk filling up stops the sequence safely with the last frame complete.

### OBS-18. Scenario tests and the hardware checklist  (P1)
**open**
- **Build:** `tests/scenarios/` driven on the simulator and the fake devices: the 30 situations that break
  unattended nights — clouds, rain, wind gusts, sensor silence, guide star lost, focus runaway, filter wheel
  stuck, camera disconnect mid-download, mount stops tracking, flip refused, dome lag, roof failure, disk full,
  clock jump, power-switch off, window closed, observatory process killed and restarted, network loss to a remote
  window, target setting early, twilight earlier than planned, wrong filter name, exposure longer than the event,
  two programs armed, daylight start attempt, Sun-side slew attempt, altitude-limit crossing during an exposure,
  cooler unable to reach the set point, dew, saturation, USB hiccups (slow downloads) — each with the expected
  safe outcome asserted; a printed **hardware checklist** for the owner (per device kind: what to try, what to
  watch, what to send back) generated from the same list.
- **Accept:** all scenarios pass in CI on Linux and Windows; the checklist exists in four languages.

### OBS-19. Working with other programs  (P3)
**open**
- **Build:** import of N.I.N.A. simple-sequence targets and of common target list files into our sequence; export
  as in PLN-7; reading frames written by N.I.N.A., MaxIm DL, SGP, Ekos, ASIAIR "as if ours" (CAL-2 covers the
  headers); a note in the guide on running PHD2 and plate solvers beside the program.
- **Accept:** stored example files import to equivalent sequences.

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
