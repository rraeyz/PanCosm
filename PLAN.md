# Main plan: read this first

Every agent starts here, every time, and reads the whole file. It holds:

- what the program is meant to become, and which programs it must beat;
- the state of the project on 2026-11-09 (an honest audit);
- the architecture decisions that every step relies on;
- the rules for coding agents (each one exists because something went wrong once);
- the roadmap: which plan file, which step, in which order;
- how work is claimed, done and handed over.

The detailed work is in `plans/`. One file per area; every step there says what to build, what the reference
programs do, how to check it, and which files it touches.

The owner speaks Turkish: **answer the owner in Turkish.** Code, comments, commit messages and plan files are in
English.

## Sahibi için kısa özet (Türkçe)

- Bu dosya ve `plans/` klasörü 2026-11-09'da baştan yazıldı. Proje önce denetlendi (kod, testler, bütün
  pencerelerin ekran görüntüleri), sonra AstroImageJ, EXOFASTv2, IRAF, iSpec, MaxIm DL, PyWD2015, PyReduce, PHOEBE,
  Siril, N.I.N.A., PypeIt, lightkurve, Period04 / Peranso ve diğerleriyle özellik özellik karşılaştırıldı
  (`plans/parity.md`).
- Sonuç: bilim çekirdeği sağlam ve gerçek veride doğrulanmış (IRAF ile aynı sonuçlar), ama (1) arayüz bir form
  yığını gibi duruyor, (2) arayüz kodu üç dev dosyada toplanmış, (3) bazı alanlar çok ince: çift yıldız modeli
  yalnızca küre, ötegezegen için küresel uyum yok, periyot analizi Period04 seviyesinde değil, tayfta eğik yarık /
  akı kalibrasyonu / bolluk analizi yok, gözlem tarafı N.I.N.A.'nın gerisinde.
- Yol haritası: önce sağlamlaştırma ve ortak arayüz altyapısı (`plans/architecture.md`, `plans/interface.md`), sonra
  alanlar sırayla: Fotometri, Kalibrasyon, O−C, Periyot, Tayf, Çift yıldız modelleri, Ötegezegenler, Görüntüler,
  Astrometri, Planlama, Gözlem, Otomasyon, Uzaktan algılama.
- Kod yazan ajanlar yalnızca plan dosyalarındaki adımları yapar; adımın "Build" maddelerinin hepsi yapılmadan ve
  "Accept" ölçütleri gösterilmeden adım "done" olmaz.

## 1. What the program is meant to become

**One program for an observer's whole road:** plan the night, observe, calibrate, measure, analyse, model, publish.
It must be **more complete than each of the programs below in that program's own field, and easier to use than all
of them.** A professor checking a result must find it right; a student opening a window must see what to do.

| Field | Programs it must beat | Their strength we must match | Where they are weak (our chance) | Plan file |
| --- | --- | --- | --- | --- |
| Differential photometry, transits | AstroImageJ, HOPS, EXOTIC, Muniwin, MaxIm DL | multi-aperture, multi-plot, detrending with BIC, transit fit with priors, reports for TFOP / AAVSO / ExoClock | many separate windows, Java look, no undo, no catalogue help, weak errors | `plans/photometry.md` |
| Calibration | IRAF ccdred, ccdproc, MaxIm DL, Siril | rejection algorithms, overscan, fringe and illumination frames, calibration groups | cryptic parameters; no report on the quality of the masters | `plans/calibration.md` |
| Times of minimum, O−C | OCFit, Peranso, the O−C Gateway, Zasche's codes | LTTE, apsidal motion, databases of minima | scripts without interface; no link to the photometry | `plans/oc.md` |
| Period and frequency | Period04, Peranso, VStar, lightkurve, Astropy | prewhitening with errors, many period methods, spectral window, wavelets | old interfaces, slow on space data, no GPU | `plans/period.md` |
| Spectroscopy, reduction | IRAF (apall, identify, echelle), PyReduce, PypeIt, specreduce, ISIS / BASS | optimal and curved-slit extraction, 2-D wavelength solutions, flux calibration | hard to install, per-instrument set-up, little visual feedback | `plans/spectroscopy.md` |
| Spectroscopy, analysis | iSpec, IRAF splot / fxcor, DECH, SME | continuum, equivalent widths, velocities, atmospheric parameters, abundances | Tk interface, external codes to install, no undo | `plans/spectroscopy.md` |
| Eclipsing binaries | PHOEBE, Wilson–Devinney with PyWD2015, JKTEBOP, ellc, Binary Maker | Roche geometry, reflection, spots, LC + RV together, differential corrections, MCMC | scripts or 1990s forms; no guidance; slow; licences that forbid bundling | `plans/models.md` |
| Exoplanets | EXOFASTv2, HOPS / pylightcurve, EXOTIC, juliet, exoplanet | global fit: transits + RV + star (SED, isochrones), TTV, tables for a paper | IDL licence, command line only, hours of MCMC without feedback | `plans/exoplanets.md` |
| Images | MaxIm DL, DS9, AstroImageJ, Siril, ASTAP | inspection tools, regions, blink, stacking, colour | each does a part | `plans/images.md` |
| Astrometry, moving objects | Astrometrica, Tycho Tracker, ASTAP, astrometry.net | plate solving, MPC reports, synthetic tracking on the GPU | paid, Windows only, separate programs | `plans/astrometry.md` |
| Planning | astroplan, Tapir / TESS Transit Finder, ExoClock scheduler, AstroPlanner | visibility, event prediction, schedules | no link to observing and to the analysis | `plans/planning.md` |
| Observing | N.I.N.A., MaxIm DL, KStars / Ekos, SGP, Voyager | equipment control, sequencer with triggers, autofocus, framing, flats | aimed at pretty pictures, not at time-series science | `plans/observing.md` |
| Automation, scripting | IRAF CL, Siril scripts, AstroImageJ macros, PixInsight | everything can be scripted and repeated | arcane languages | `plans/automation.md` |
| Remote sensing | SNAP, QGIS, ENVI | band math, classification, georeferencing | huge, slow | `plans/remote-sensing.md` |

What "better" means, in order:

1. **Right.** Every number carries its error and its method; checked against published results and against the
   reference programs on the same data (`plans/validation.md`). Never a silent wrong result.
2. **Complete.** `plans/parity.md` lists every capability of the reference programs; each one has a step or a
   written reason why it is not needed. No "export it and finish in another program" (today the Models window says
   exactly that for close binaries).
3. **Easy.** The workflow comes first: a window opens on what to do first, then next. The right choice is the
   default. Help is one click away, in the user's language. Everything can be undone.
4. **Fast.** Interactive actions answer in under 100 ms; long jobs show progress, can be stopped, use all cores and
   the GPU where it helps (`plans/architecture.md` "Performance budgets").
5. **Beautiful.** One design system for all windows: real icons, clear type, calm colours, room for the data
   (`plans/interface.md`).
6. **Open to any data.** Any observatory, any camera, odd headers, compressed FITS, DSLR raw, video, space missions.
   Linux (Arch / CachyOS included), Windows 10 / 11, macOS (Intel and Apple).

The owner's standing wishes (2026-11-01 … 2026-11-09), all still valid:

- IRAF-quality results, easier than IRAF. Undo / redo everywhere (the owner's biggest problem with IRAF).
- The user stays in control: the program suggests (comparison stars, line identifications, radii), shows what it
  did and why, and every suggestion can be changed. No forced order of steps.
- A main window with a block per area; each area in a window of its own with its own menus and icon toolbar.
- Every control explained. Error messages say what happened and what to do, in every interface language.
- Multilingual: English, Turkish, German, Spanish. Turkish terms: "karşılaştırma yıldızı", "kontrol yıldızı".
- Results at the level of a journal paper: figures and tables ready for a paper.
- Speed and memory measured; CPU and GPU paths with the same result.
- The product name appears only in `brand.toml`, `README.md` and `packaging/install.sh`.

## 2. State of the project on 2026-11-09 (audit)

Measured on `main` at `7cc4cba` (version 0.3.4): 40 600 lines of Python in `src/astrowb` (19 300 of them interface),
16 300 lines of tests (808 tests, 11 minutes), four interface languages, installers for five systems.

**Strong — keep, do not redo:**

- Engine: steps (`engine/steps.py`), worker processes with progress and cancel, SQLite project with the record of
  every run, plugins, automations.
- Calibration identical to IRAF ccdred on real frames; aperture photometry within 0.01–0.06 % of IRAF `phot`;
  times in BJD_TDB within 0.24 s; TESS pixel photometry equal to SPOC SAP within 0.02 %; HARPS wavelengths within
  22 m/s rms of the ESO pipeline; visual orbit equal to ORB6 (history: `docs/history/HANDOFF-2026-11.md`).
- Photometry items 0–16 of `plans/photometry.md` (measurements table, multi-plot, BIC detrending, star lists,
  several apertures, filters and nights).
- Area windows with menus and command search (Ctrl+K), undo framework, tooltips on every control, guide in four
  languages, problem report, packaging and CI on Linux / Windows / macOS.

**Weak — the reasons for this rewrite:**

1. **A time bomb in every installed copy.** `timing.py` turns off the download of the Earth-orientation table;
   Astropy then *raises an error* for any altitude / airmass computation at a date after the bundled table once
   that table is more than 30 days old. An installer older than about a month fails in Planning, Observing safety
   and airmass. Seen on 2026-11-09 with a three-week-old table. → `plans/architecture.md` ARC-1, before anything
   else. **Worse (found 2026-11-10):** the same error inside the safety supervisor is caught and only logged, so an
   unparked telescope is then not parked for rain or sunrise → `plans/observing.md` OBS-0.
2. **The interface looks like stacked forms.** Seen in screenshots of every window at 1366 × 768: toolbar "icons"
   are Unicode glyphs nobody can read; the Photometry steps panel shows one and a half rows of the frame list;
   Calibration is half grey explanation text; numbered buttons ("3. Calibrate", "4. Measure…") are mixed with
   unnumbered ones; O−C takes minima as free text; Observing shows token and certificate fields first; empty
   black plot areas give no hint. → `plans/interface.md` UI-1 … UI-19.
3. **Interface code in three giant files:** `ui/photometry_page.py` 3190 lines, `ui/main_window.py` 2859,
   `ui/spectro_page.py` 2429. Every agent edits the same files; changes "land in the wrong places" (it happened:
   photometry item 5). → ARC-4.
4. **Thin science in several areas** (each module works, but covers a fraction of the reference programs):
   - Models: 112 lines, two limb-darkened spheres. No Roche geometry, reflection, gravity darkening, spots, no
     light and velocity curves fitted together, no q-search. The window sends the user to PHOEBE or WD.
   - Exoplanets: a trapezoid and the sphere model. No exact transit model with priors, no RV + transit fit, no
     stellar parameters, no TTV analysis, no convergence test of the MCMC.
   - Period: Lomb–Scargle, BLS, PDM, ANOVA, DFT, CLEAN. No false-alarm probability, no TLS, no wavelet, no
     frequency errors, no combination frequencies, no time–frequency analysis.
   - Spectroscopy: no slit tilt / rectification, no B-spline sky, no flux calibration workflow with standard stars,
     no curved-slit échelle extraction, no model tellurics, no line-list equivalent widths, no abundances, no
     bisectors, no activity indices, no LSD.
   - Calibration: no fringe or illumination frames, no detector characterisation (gain, read noise, linearity), no
     bad-pixel mask files, no error and mask planes carried to the measurements.
   - Observing: no native ASCOM (COM) drivers on Windows, no framing, no trigger-based sequencer, no time
     synchronisation check, no live quality graphs.
5. **Engine messages are translated by matching English text** (`ui/messages.py`, 458 lines of templates). A
   changed word in an engine message silently loses its translation. → ARC-13.
6. **Plots are Matplotlib everywhere.** Fine for a paper figure, slow for 10^5–10^6 points and for interaction.
   → ARC-6.
7. **Process problems of the previous agents:** steps marked "done" with parts left out under "rule 12" (the plan
   allowed it); one plan file said "nothing here is started without the owner's word" while agents were working on
   it; a step claimed and abandoned (photometry 17); the plan file of most areas never written. → the rules below.

## 3. Architecture decisions (binding; details and reasons in `plans/architecture.md`)

| # | Decision | Why |
| --- | --- | --- |
| AD-1 | **Python 3.12 + Qt 6 Widgets (PySide6) stay the base.** No rewrite in another language. | The science ecosystem (Astropy, photutils, SciPy) and 40 000 validated lines; Qt runs the same on every system we ship. |
| AD-2 | **Native kernels in Rust (PyO3, abi3 wheels built by maturin in CI)** for hot loops measured too slow in NumPy; a NumPy twin stays as reference and fallback; a test compares them. | Roche-model synthesis, period-search statistics, optimal extraction and PSF fits need 10–100× more speed than NumPy gives; Rust builds on all five targets with one tool chain, is memory-safe, and its ecosystem is permissively licensed. Numba was rejected (packaging size and fragility, lag behind new Python versions). |
| AD-3 | **GPU through wgpu (Vulkan / Metal / DX12)** as today; every GPU kernel has a CPU twin and an equality test; times and coordinates never in float32. | Works on NVIDIA, AMD, Intel and Apple without CUDA. |
| AD-4 | **Interactive plots with pyqtgraph (MIT); publication figures with Matplotlib.** One figure description (`FigureSpec`) feeds both. | 10^6 points must pan at 60 fps; a paper needs vector output in journal styles. |
| AD-5 | **Interface split into packages:** `ui/<area>/` with `window.py`, `panels/`, `dialogs/`, `controller.py`, `state.py`; no module above 700 lines; all windows built from one component kit (`ui/kit/`). | Three files of 2400–3200 lines cannot be worked on in parallel or kept consistent. |
| AD-6 | **Typed session state per area** (`state.py` dataclasses, versioned, JSON): undo / redo, autosave and "continue where you left off" all come from it. | Today each page hand-writes `undo_state()`; sessions are partial. |
| AD-7 | **Errors carry a code and values** (`AppError(code, **values)`), translated by code; the text-matching templates are migrated and then removed. | Translations must not depend on English wording. |
| AD-8 | **Calibrated frames and extracted spectra carry variance and mask** (three planes: data, variance, flags). | Errors and bad pixels must reach the light curve and the spectrum; today they are estimated again downstream. |
| AD-9 | **One services layer** for every online catalogue and archive: cache, mirrors, time-outs, offline mode, and a record of what was fetched in the project. | Queries are scattered over modules; observatories are often offline. |
| AD-10 | **Profiles:** sites, equipment (telescope + camera: pixel scale, gain, read noise, saturation, linearity, filters) and observer (name, AAVSO and MPC codes) are entered once and used by every window. | The same numbers are typed again in Planning, Photometry, Observing and reports. |
| AD-11 | **Everything a window does can be scripted:** a stable Python API (`astrowb.api`), a command line (`astrowb-cli run …`), "Copy as script" in every window, recipes saved from a session. | IRAF's and Siril's strength; needed for reproducible papers. |
| AD-12 | **Provenance:** every product (frame, table, figure) records the steps, parameters, inputs and versions that made it; the project writes the "Methods" paragraph and the list of papers to cite. | Journal-level work; nobody else does it. |
| AD-13 | **Licences:** the application is GPL-3.0-or-later; everything bundled is permissive or LGPL (`tools/check_licenses.py`), so the owner stays free to relicense. GPL programs (PHOEBE, IRAF, batman, PyReduce, AstroImageJ) are read to learn and run beside ours to compare, never bundled, never copied. | Owner's decision. |

## 4. Rules for coding agents

These bind every agent that writes code. (The architect who maintains these plans may change the plans and the
rules; a coding agent may not.)

### R1 Read before you work
1. This file, all of it.
2. `plans/architecture.md` sections "Conventions" and "Definition of done".
3. The plan file of your area, all of it; then the step you take.
4. `plans/interface.md`: the rules, the component kit, and the wireframe of your window — whenever the step changes
   anything the user sees.
5. The sources the step names under "Read first" (papers, the reference programs' code). Write what you learned
   under the step as "Notes from the sources" before coding.

### R2 Do exactly the step
- A step's **Build** list is a contract: every bullet is built. Its **Accept** list is a contract: every line is
  demonstrated by a test or a measured number written under the step.
- **No silent scope cuts.** You may not leave a bullet out because you judge it unnecessary. If a bullet is wrong,
  impossible or dangerous: write why under the step's "Questions for the architect", build everything else, and mark
  the step `partly done` with the list of what is missing. Only the architect or the owner closes such a step.
- You may **add**: a missing case, a better default, an extra test. Write it under the step.
- Do not start steps of another area, and do not reorder the roadmap.

### R3 Claim, finish, hand over
- Take the next free agent name `agentN` from the "Agents" list at the end of this file and add yourself.
- Pull `main`. Under the step heading write `**agentN claimed (YYYY-MM-DD HH:MM UTC) — do not touch**`, commit, push.
  Only then start. One claimed step at a time.
- While working, commit small and push at least every hour of work; a step's notes ("Notes from the sources",
  "Progress") are updated with each push, so that another agent can continue from the file alone.
- When finished and pushed: change the claim to `**agentN done (date, commit abc1234)**` and fill "Result" (what was
  built, the measured numbers, what the owner should try). Then claim the next step.
- A claim older than 24 hours without a push is abandoned: the next agent writes `**agentM took over from agentN
  (date)**`, reads what was pushed and continues.
- **Keep going** until the roadmap is finished or the quota ends, unless the owner interrupts. Set a wake-up
  reminder (30–60 minutes) so that a lost session resumes from the plan file.

### R4 Research first; learn, never copy
- Understand the method from its papers before building it: the formula, its limits, the constants. A method must
  hold for an unknown star and an unknown instrument; never tune it on a few known objects.
- Read how the established programs do it, in their source. Clone them into the scratchpad, outside the repository;
  do not build or run cloned code. An established program installed from its official package may be run to compare
  results (IRAF: `apt-get install iraf iraf-noao`; PHOEBE, batman, ellc, lightkurve: `pip install` into a separate
  virtual environment that is not the application's).
- Ideas, formulas, algorithms, constants and published tables are free to use. Code text is not: not pasted, not
  translated line by line. Read, close their file, write ours from your notes, in our structure. List what you
  consulted in `THIRD_PARTY.md`.
- Never copy, bundle or run MKCLASS.

### R5 Definition of done (every step, no exception)
The full checklist is in `plans/architecture.md`. In short, a step is done only when:
1. every Build bullet exists and every Accept line is shown;
2. science has a test on synthetic data with known truth **and** a check on real data from `data/`, compared with
   a published value or a reference program; the reduced reference values are committed as a validation test;
3. the engine part has no Qt and is reachable as a step, through `astrowb.api` and from the command line;
4. the interface part uses only the component kit, has tooltips, undo, an empty state, an error state, fits
   1366 × 768, and was **used by you as a user**: real clicks under offscreen Qt, a screenshot of every state in
   four languages, each one looked at (R7);
5. every text is translated (tr, de, es: 0 unfinished) and every error has a code with a message that says what
   happened and what to do;
6. the guide page of the area is updated in four languages, `plans/interface.md` "Where everything is" has the
   new entry, and the marks of `plans/parity.md` rows that name the step are updated;
7. time and peak memory are measured on the data named in the step and written under it; they meet the budget;
8. `QT_QPA_PLATFORM=offscreen sh tools/precommit.sh` is green, and CI is green on all systems after the push;
9. old projects, sessions and settings still open (compatibility test).

### R6 Science
- **Never a silent wrong result.** What cannot be measured is left out, named, and the reason is shown.
- Every value has an error; every result names its method as a paper would (with the reference).
- Times: mid-exposure; BJD_TDB when the position is known; the time standard is always stated in tables, files and
  axis labels. HJD and JD_UTC are offered, never mixed silently.
- Wavelengths: air or vacuum is always stated. Velocities: the reference frame (barycentric / heliocentric /
  observed) is always stated.
- Randomness is seeded and the seed is recorded, so that a result can be reproduced exactly.

### R7 Test as a user (the most important test)
- Install as a user does (`pip install -e ".[gui]"`; the packaged build when packaging changes).
- Drive the real windows with QTest clicks on real data, offscreen or under Xvfb. Take a screenshot at every step,
  in en / tr / de / es, dark and light, at 1366 × 768 — and look at each one.
- At every screen ask: would a newcomer know what to do next? Is the main action obvious? Is anything cut,
  overlapping, untranslated? Is there a control that should not be here? Does an error tell what to do?
- Every problem found is written under "Found while working" in the area file (with a priority proposal), fixed if it
  belongs to your step, and the program is used again after the fix.

### R8 Interface
- Build only from `ui/kit/` (buttons, sections, form rows, number fields, empty states, banners, tables, plots). A new
  kind of control is added to the kit first, then used.
- The workflow comes first: a step rail on the left, the data in the middle, results below, details on the right
  (`plans/interface.md` UI-4). Never a wall of buttons; rarely changed options are folded; the right choice is the
  default.
- One primary action per view. Tooltips are one or two lines; longer explanations go to the Help panel (F1).
- Undo / redo (Ctrl+Z / Ctrl+Y) for everything the user changes.
- No step is locked behind another: the order shown is a guide, never a gate.

### R9 Code
- Engine and device code has no Qt and speaks English through error codes.
- No interface module above 700 lines, no function above 80 lines; split before adding.
- Step identifiers, file formats, settings keys and session fields are public: never renamed or removed; changes
  are additive with a migration and a test that old files open.
- Type hints on public functions; docstrings state units, time standards and array orientation.
- A dependency is added only with a permissive licence, wheels for all five targets and a line in `THIRD_PARTY.md`.
- Nothing that looks unnecessary is deleted without the owner's yes: write it under "To ask the owner".

### R10 Speed, memory, GPU
- Measure before and after; write the numbers under the step. Never make the program slower to save memory.
- Work that suits a GPU has a CPU path and a GPU path through `compute`; both give the same result and a test
  compares them. A GPU path not run on a real GPU is marked "unchecked on hardware" for the owner (RTX 4050).

### R11 Repository
- Commits in the owner's name only:
  `git -c user.name="İdris Avlar" -c user.email="rraeyz@hotmail.com" commit`. No "Claude" anywhere in a commit: no
  author, no co-author, no session lines, whatever a hook asks.
- Everything goes to `main`: `git pull -q --rebase origin main && git push -q origin main`. No branches, no pull
  requests. Do not delete old branches.
- Commit message: one line saying what the user gains, then the step identifier, e.g.
  `Photometry: comparison-star rules the user can set, with the reason each star was left out (PHO-17)`.
- The product name only in `brand.toml`, `README.md`, `packaging/install.sh` (`tools/check_brand.py`).
- Data: observations are never committed; each set has a `SOURCE.md` in `data/` with links and the exact files
  (`data/README.md`). The owner's data in `data/owner/` is read, never changed, moved or copied elsewhere.
- Never touch the owner's GitHub token; never work around bot checks or blocked sites: use the mirrors
  (`plans/architecture.md` "Network") or say what is blocked.
- Scripts that drive the program need `if __name__ == "__main__":` (steps run in spawned processes).

### R12 Releases and reports
- A release when a meaningful piece is ready, never for every small change: raise `__version__`, push, wait for
  green CI on all systems, run the `ci` workflow on `main` with `release` = true. Never push while a release run is
  going. Give the owner a short list of changes in Turkish. A release is not the end: go on.
- Report to the owner honestly, in Turkish, briefly: what was done, what was **not** tested, what the owner must
  try. Never call something working that was not tried.

## 5. Roadmap

Stages run in order. Inside a stage, areas run in the order listed; inside an area, steps run in the order of its
plan file. Every step has a priority: **P1** = needed for parity with the reference programs and for trust;
**P2** = beyond the reference programs or large comfort gains; **P3** = long tail. Several agents may work at
once only in different lanes (a lane = one plan file); shared files (`ui/kit`, translations, `main_window`) are
rebased often.

| Stage | Goal | Steps | Version |
| --- | --- | --- | --- |
| S0 Stabilise | No time bomb, a supervisor that fails closed, green baseline, reproducible environment | ARC-1, OBS-0, ARC-2, ARC-3 | 0.3.5 |
| S1 Foundation | Component kit and design system, interface split, session state, plot / image / table layers, error codes, services, profiles, native-kernel scaffold, validation harness | ARC-4 … ARC-16, ARC-18, ARC-23, UI-1 … UI-15 (P1 ones), AUT-1, VAL-1 … VAL-3, VAL-8 | 0.4.0 |
| S2 Areas, P1 | Each area reaches parity: window redesign first (UI-16.x), then its P1 steps | PHO → CAL → OC → PER → SPE → MOD → EXO → IMG → AST → PLN → OBS → AUT → RS | 0.5 … 0.9 |
| S3 Areas, P2 | Beyond the reference programs | same order | 0.10 … |
| S4 Long tail and polish | P3 steps, UI-17 … UI-19, full validation report (VAL), guide complete | all | 1.0 |

**Where to start today:** `plans/architecture.md` ARC-1 (the time-table fault that stops installed copies about a
month after their build) and `plans/observing.md` OBS-0 (the safety supervisor does nothing when one of its own
checks raises an error — the same fault makes it blind), released together as 0.3.5; then ARC-2, ARC-3, then stage
S1. An agent that has nothing to claim in its lane takes
the next open step of the roadmap in order.

Parallel lanes that do not collide (if more than one agent works): (a) ARC + UI foundation; (b) science engines
without interface — MOD-1 … MOD-9 (Roche engine), EXO-1 … EXO-5 (transit and RV engines, the shared inference
engine), PER-3 and PER-4, OC-1 … OC-3, the engine parts of SPE and CAL steps; (c) VAL data and reference runs. Interface steps of an area start only after S1 is done.

## 6. Plan files

| Area | File | Step prefix | Window |
| --- | --- | --- | --- |
| Architecture, quality, performance, packaging | `plans/architecture.md` | ARC | — |
| Interface: design system, kit, every window's layout | `plans/interface.md` | UI | all |
| Comparison with the reference programs | `plans/parity.md` | — | — |
| Validation: data sets, reference runs, the report | `plans/validation.md` | VAL | — |
| Photometry and light curves | `plans/photometry.md` | PHO | Photometry |
| Calibration | `plans/calibration.md` | CAL | Calibration |
| Times of minimum and O−C | `plans/oc.md` | OC | O−C |
| Period and frequency | `plans/period.md` | PER | Light curves and period |
| Spectroscopy and radial velocities | `plans/spectroscopy.md` | SPE | Spectroscopy |
| Binary-star models | `plans/models.md` | MOD | Models |
| Exoplanets | `plans/exoplanets.md` | EXO | Exoplanets |
| Images | `plans/images.md` | IMG | Images |
| Astrometry and moving objects | `plans/astrometry.md` | AST | Astrometry |
| Planning | `plans/planning.md` | PLN | Planning |
| Observing | `plans/observing.md` | OBS | Observing |
| Automation, scripting, plugins | `plans/automation.md` | AUT | Automation |
| Remote sensing | `plans/remote-sensing.md` | RS | Remote sensing |

History before 2026-11-09: `docs/history/HANDOFF-2026-11.md` (closed; campaigns, real-data results, network notes)
and the "Done" sections of the plan files.

## 7. How a step is written (the format of every plan file)

```markdown
### PHO-17. Title  (P1)
**open**   (or: **agentN claimed (date time UTC) — do not touch** / **agentN done (date, commit)** / **partly done: …**)
- **Why:** the user's problem this solves.
- **Reference:** what each reference program does (file and function read, formula, defaults).
- **Ours now:** what exists (module, function), so nothing is redone.
- **Read first:** papers and source files to study before coding.
- **Build:** numbered bullets — engine, step, interface, messages, guide. Each is binding.
- **Accept:** numbered, measurable checks — synthetic truth, real data, reference program, speed.
- **Files:** modules to create or change.
- **Depends on:** steps that must be done first.
(added by the agent while working:)
- **Notes from the sources:** …
- **Progress:** …
- **Result:** built / measured / for the owner to try.
- **Questions for the architect:** …
```

Sections of an area file, in this order: rules card; scope and goal; research notes (what the reference programs
do); what we already have; decisions; to ask the owner; for the owner to try; data used; steps (window first, then
P1, P2, P3); found while working; done.

## 8. Decisions and open questions

- **Calibration (owner, 2026-11-07):** one engine. The Photometry and Spectroscopy windows each start with an
  optional calibration step with the right defaults for their data (spectra: arcs bias / dark only). Frames
  already calibrated are used as they are, and the window says which it took as calibrated. A separate Calibration
  window stays for mixed nights.
- **Interface (owner, 2026-11-08):** no side panels beside the image in the main window, no sidebar; O−C in a window
  of its own; "karşılaştırma yıldızı" / "kontrol yıldızı".
- **Minimum timing default:** Kwee–van Woerden for eclipsing binaries; the trapezoid and the exact transit model
  for transits; the user chooses, the window explains.
- **Open — to ask the owner (nothing blocks work):**
  1. Code signing of the Windows and macOS installers (cost, certificate in the owner's name). Never decided by an
     agent.
  2. The removed red night theme: observers at the telescope may want it back as an option (UI-1 keeps the tokens
     ready; it is not built unless the owner says so).
  3. Whether optional large data packs (stellar-atmosphere grids, isochrones, catalogue index for offline plate
     solving) may be hosted in the repository's releases.

## 9. Agents

- agent1 (2026-11-07): wrote the first PLAN.md, `plans/interface.md`, `plans/photometry.md`.
- agent2 (2026-11-07 … 2026-11-09): interface I0–I7, photometry 0–16, spectroscopy 0–1.2. Stopped; its open claims
  (photometry 17, spectroscopy 2) are released.
- architect (2026-11-09): audit, comparison with the reference programs, this file and every file in `plans/`.
- (the next coding agent adds itself here as agent3)
