# Light curves, period and frequency: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.4).

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

Everything done with a light curve after it exists: loading and joining data from our own photometry, surveys and
space missions; cleaning; searching for periods with every established method; judging what is real; folding;
multi-frequency analysis of pulsators; time–frequency analysis; and the report.

**Goal:** Period04's frequency analysis, Peranso's breadth of period methods, VStar's wavelets, lightkurve's handling
of space data and AstroImageJ's GPU periodograms — in one window where a click on a peak folds the curve at once,
every peak comes with its significance and its aliases, and a million points stay interactive.

## What the reference programs do

Read (never copied): Period04 (Lenz & Breger 2005, CoAst 146, 53, and its manual: modules Time string, Fourier, Fit;
weights; subsets by attribute; zero-point adjustment; amplitude / phase variation mode; periodic time shift; Monte
Carlo and analytic errors; noise spectrum); Peranso (Paunzen & Vanmunster 2016, AN 337, 239: Lomb–Scargle, Bloomfield,
DFT (Deeming), DCDFT (Ferraz-Mello), CLEANest (Foster), FALC (Harris), ANOVA, PDM, Lafler–Kinman, Dworetsky, Renson,
Abbe, Jurkevich, EEBLS; spectral window; prewhitening; significance by permutation); VStar (DCDFT, WWZ, Fourier
model, polynomial fits); lightkurve (`to_periodogram`, `flatten`, `fold`, `bin`, river plots, seismology module);
Astropy `LombScargle` (fast, floating mean, multi-term, false-alarm methods) and `BoxLeastSquares`; AstroImageJ
`Periodogram_.java`, `BLSGpu.java`, `TLSGpu.java`; the Python prewhitening tools SMURFS and PyWhiten (as descriptions
of current practice: automatic frequency extraction with S/N stops, chunked time-dependent analysis).

| Topic | Period04 | Peranso | VStar | lightkurve / Astropy | AstroImageJ | Ours now |
| --- | --- | --- | --- | --- | --- | --- |
| Fourier spectrum | DFT with weights, any range and step; spectral window; noise spectrum | DFT, DCDFT, Lomb–Scargle, Bloomfield | DCDFT | Lomb–Scargle (fast, floating mean, multi-term) | — | Deeming DFT, spectral window, Lomb–Scargle (Astropy), CLEAN |
| Phase-dispersion methods | — | PDM, Lafler–Kinman, Dworetsky, Renson, Jurkevich, Abbe | — | — | — | PDM (GPU twin) |
| Variance methods | — | ANOVA | AoV | — | — | ANOVA with harmonics |
| Transits / eclipses | — | EEBLS | — | BLS | BLS, **TLS** (GPU) | BLS (Astropy; GPU twin) |
| Asteroids | — | FALC (Fourier fit with per-night zero points) | — | — | — | none |
| Significance | S/N from the noise spectrum (criterion 4) | permutation test | — | false-alarm probability (Baluev, bootstrap) | SDE for BLS / TLS | none (a warning when the data cannot hold the period) |
| Multi-frequency fit | least squares of all f, A, φ together; harmonics and combinations as fixed relations; improve all / selected | prewhitening | Fourier model | — | several planets in turn | prewhitening loop with S/N stop, linear + non-linear fit |
| Errors | analytic (Montgomery & O'Donoghue 1999), correlation matrix, Monte Carlo | period error by formula | — | — | — | covariance |
| Variable amplitudes / phases | per subset | — | WWZ | — | — | none |
| Time–frequency | — | — | WWZ (Foster 1996) | sliding periodogram ("river") | — | none |
| Data handling | subsets by 4 attributes, weights, zero points | observation sets, nights | observation sources as plug-ins | missions' files, quality flags, stitch, flatten | — | load CSV / AAVSO / ZTF / ASAS-SN, TESS / Kepler from MAST, outliers, binning |
| Speed | compiled, single thread | compiled | Java | Astropy fast LS O(N log N) | GPU (OpenCL) | NumPy; GPU for BLS and PDM |

## What we already have (do not redo)

- `timeseries/period.py` (`frequency_grid`, `search`, `lomb_scargle`, `bls`, `pdm`, `fold`), `fourier.py` (`dft`,
  `spectral_window`, `fourier_fit`, `prewhiten`, `noise_at`, `anova`, `clean`, `times_of_maximum`, `sigma_clip`,
  `bin_time`), `archive.py` (TESS / Kepler / K2 PDCSAP, sectors joined), `surveys.py` (AAVSO, ZTF, ASAS-SN),
  `compute/{bls,periods}.py` (GPU twins), steps `photometry.period`, `timeseries.frequencies`, `timeseries.survey_lc`,
  `photometry.mission_lc`; `period_warnings`.
- Window "Light curves and period" with tabs Period search, Frequency analysis, Variable star search.
- Checked: FG Vir (TESS s46) all 8 modes of Breger et al. 2005; a W UMa period to 6 digits; BLS / PDM exact on
  synthetic data.

## Decisions

- One light-curve container (PER-1) for all windows; flux is the internal unit, magnitudes are a view.
- The frequency axis is the internal axis (cycles per day); period and µHz are views.
- Every periodogram result is a table of peaks with significance, not only a best value.
- Our own TLS implementation (the reference package depends on a GPL transit model); the reference package is run
  beside ours for validation only.

## To ask the owner

- Nothing blocks. A real multi-site or multi-season data set of a pulsator from the owner's group would make a good
  validation of zero-point adjustment (PER-1.4).

## For the owner to try

- After PER-W: load a TESS light curve of an eclipsing binary by name, search, click the highest peak and its
  double; say whether the folded curve and the peak table answer "which period is right?" at a glance.

## Data used

- FG Vir TESS sector 46; a W UMa star over three TESS sectors; AI Dra sector 24; KIC 6525196 — from the history.
- To add (each with `SOURCE.md`): Period04's tutorial data set or an equivalent public multi-site δ Scuti campaign
  with a published frequency table; a TESS planet host with a known shallow transit (for TLS against BLS); an
  ASAS-SN + ZTF sparse multi-band curve of a known RR Lyrae; a Mira with a long AAVSO visual curve (for WWZ);
  a solar-like oscillator from Kepler (for PER-14).

## Steps

Order of work: PER-W, then P1: 1, 2, 3, 4, 5, 6, 7, 8, 16; P2: 9, 10, 11, 12, 13, 17; P3: 14, 15, 18.

### PER-W. The window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.4: stages Data, Clean, Search, Fold, Frequencies, Report; three linked plots (light
  curve, periodogram, folded curve); Inspector with the peak table. Jobs in the toolbar switch: **Period ·
  Frequencies · Minima of the series (OC-3) · Variable search (PHO-30)**.
- **Extra accept:** name → download → search → click a peak → folded curve in **four clicks**; arrow keys move
  between peaks; `2` and `H` fold at twice and half the period; all three plots stay above 30 fps with 10^6 points.
- **Depends on:** ARC-4.6, ARC-5, ARC-6, ARC-8, UI-1 … UI-4, PER-1.
- **Files:** `ui/lightcurves/{window,controller,state,menus}.py`, `ui/lightcurves/panels/{data,clean,search,fold,frequencies,report,peaks}.py` (jobs Minima and Variable search as sub-packages), `tests/ui/walks/lightcurves.py`, guide 07

### PER-1. The light-curve container and its sources  (P1)
**partial** — done (2026-11-12): `timeseries/lightcurve.py`: `LightCurve` (time with its standard, flux or
magnitude with errors, set, band, flag bits USER / OUTLIER / QUALITY / UPPER, metadata; select, flagged,
to_mag / to_flux, normalised per set, phase, append with the sets renumbered, Astropy tables both ways);
`zero_points` (per-set offsets fitted with the periodic model, as Period04): a 0.03 mag offset between two cameras
recovered within its error (< 0.003); `weights` (none, errors, per set, Period04's deviation weights). Left: the
readers of every source (item 2), the CSV wizard, BJD_TDB on load (item 3), the overlap join and band scaling, the
Data stage, the 5 × 10⁶-point plot check.
- **Reference:** Period04's time strings with four attributes per point (date, observatory, observer, other),
  weights and zero-point adjustment per subset; lightkurve's `LightCurve` (time, flux, flux_err, quality, meta) and
  `LightCurveCollection.stitch`; AAVSO, ASAS-SN Sky Patrol (v1 and v2), ZTF (IRSA), ATLAS forced photometry, Gaia
  DR3 epoch photometry (DataLink), OGLE, SuperWASP (public archive), KELT, NSVS, Catalina, Hipparcos epoch
  photometry, TESS / Kepler / K2 products (SPOC, QLP, TESS-SPOC FFI, TGLC, eleanor-lite on MAST as HLSPs).
- **Ours now:** dicts and arrays per page; `archive.py`, `surveys.py`; the Photometry export.
- **Build:**
  1. `timeseries/lightcurve.py`: `LightCurve` with columns time (with `TimeStandard`), flux, flux_err, optional
     magnitude view, `set` (data set id), `band`, `flag` (bit: left out by the user, outlier, bad quality, upper
     limit), and metadata (object, coordinates, source, citation, zero points applied); methods: select, mask,
     `to_flux` / `to_mag`, normalise per set, bin (time, phase), fold, append; conversion from and to PHO-48's file
     and Astropy tables; never copies arrays needlessly (10^7 points).
  2. Readers in `services/` for every source above (ARC-14), each returning one or several sets with bands and
     citations; a generic text / CSV wizard (column mapping, time standard, magnitude or flux, upper-limit marker);
     the Data stage's "Download…" searches all sources for a name / coordinates in parallel and lists what each has
     (number of points, span, bands) with tick boxes.
  3. Time standards unified to BJD_TDB on load (ARC-15) with the original kept; AAVSO JD (geocentric UTC) and
     visual estimates handled (visual and upper limits kept as their own sets, off by default for period work).
  4. Joining sets: per-set zero-point offsets fitted with the periodic model (as Period04's "adjust zero points")
     or by the overlap of nearest points; per-set scale (amplitude ratio between bands) optional; the offsets are
     shown and can be typed.
  5. Weights: none, 1/σ², per set, by deviation (Period04's deviation weights with its cut-off).
  6. The Data stage lists the sets with colour, band, points, span, median error, tick to use; the light-curve plot
     colours by set or by band.
- **Accept:** each reader passes a test on a recorded file; 5 × 10^6 points load and plot (decimated) with pan at
  30 fps; two synthetic sets with a 0.03 mag offset and different noise join with the offset recovered within its
  error; AAVSO visual + CCD data of the Mira set load as separate sets.
- **Files:** `timeseries/lightcurve.py`, `services/lc_*.py`, `timeseries/{archive,surveys}.py` (moved), UI data
  panel, tests.

### PER-2. Cleaning that does not eat the signal  (P1)
**partial** — done (2026-11-12), the engine: `timeseries/clean.py`: `segments` (gaps over k × the cadence or a
given length), `event_mask` (a known ephemeris), `trend` per segment with a mask (time-windowed biweight with the
scale fixed while the location iterates, sliding median, Savitzky–Golay, polynomial with the order by BIC, spline
with a knot spacing), `nightly_means`, `outliers` (both / up / down). Tests: the biweight equals wotan 2.1's on a
stored curve within 2e-9 (tests/validation/data/wotan_biweight.txt with its manifest and script; wotan run in its
own environment); with the events masked a 1 % transit keeps its depth within 3 % under biweight, median and spline
detrending and the trend's residual stays below the white noise. Left: the high-pass for pulsators, mission quality
flags, the history list with its switches (the interface).
- **Reference:** lightkurve `remove_outliers`, `flatten` (Savitzky–Golay with a break tolerance and a mask),
  `remove_nans`; Wōtan (Hippke et al. 2019, AJ 158, 143: comparison of detrending filters for transit searches —
  the biweight with a window of 3 × the transit duration is the best general choice); Period04 "subtract zero points
  / trends".
- **Ours now:** `fourier.sigma_clip` (against neighbours in time, per night, or in phase), `bin_time`, delete points
  by clicking, flux ↔ magnitude.
- **Build:** `timeseries/clean.py`: outliers (have; plus upward-only for flares / downward-only options); gaps and
  segments detected (a gap > 5 × the median cadence starts a segment); detrending per segment: polynomial (order by
  BIC), spline with knot spacing, sliding median, **biweight location** (window in days), Savitzky–Golay; each with
  an optional mask of events (known period / epoch / duration, or ranges drawn on the plot) so that eclipses and
  transits are not flattened; nightly means subtracted (ground-based multi-night data); high-pass with a chosen
  cut-off frequency for pulsators; quality-flag filters for mission data; binning in time. Every operation is an
  entry in the session's history (ARC-5) shown as a list in the Clean stage with eye icons to switch each off and
  compare — non-destructive.
- **Accept:** synthetic curve with a slow trend, a 1 % transit and outliers: after the default "transit-safe"
  preset the transit depth is within 3 % of the truth and the trend's residual below the white noise; the biweight
  result equals the reference implementation's on a stored curve within 1e-6 (the reference package run beside
  ours); switching a history entry off restores the earlier curve exactly.
- **Files:** `timeseries/clean.py`, UI clean panel, tests.

### PER-3. Every period-search method, one interface  (P1)
**partial** — done (2026-11-12): `timeseries/methods.py` with period.py's signature ((periods, power, best), higher
is better): `gls` (floating mean, weights, n harmonics; Astropy), `aovmh` (Schwarzenberg-Czerny 1996, 8 harmonics
by default), `conditional_entropy` (Graham et al. 2013, 10 × 5 grid), `string_length` (Lafler–Kinman); the fold
statistics go through period.search's budget. `timeseries.period` takes them all, its help says which suits which
light curve. Tests: each statistic's formula on noise-free data; with 250 points on 30 nights (7 h a night), 20
realisations each, the advised methods find a sine, an RR Lyrae-like saw-tooth and an Algol-type binary in ≥ 95 %.
**Found:** AoV with n harmonics and the string length score k · P as well as P (the cycles fold on top of each
other; AoV's spare harmonics even fit some noise in gappy data and scored 9 % higher at 7 P): both take the
shortest of the near-equal peaks (a true half period scored 0.01–0.1 of the period's own); conditional entropy
picks half an Algol's period (not advised for it). Left: dcdft, pdm2, jurkevich, tls, falc, acf, multiband,
cleanest; the grid of item 2; the chooser and "Compare methods" in the window; native and GPU kernels; budgets.
- **Read first (the papers, not other programs' code):** Lomb 1976; Scargle 1982; Zechmeister & Kürster 2009 (A&A
  496, 577: generalised LS with floating mean and weights); Ferraz-Mello 1981 (AJ 86, 619: DCDFT); Deeming 1975;
  Schwarzenberg-Czerny 1989 (ANOVA) and 1996 (ApJ 460, L107: multi-harmonic AoV with orthogonal polynomials);
  Stellingwerf 1978 (PDM) and 2011 (PDM2); Lafler & Kinman 1965; Dworetsky 1983; Renson 1978; Clarke 2002 (string
  lengths for multi-band data); Jurkevich 1971; Graham et al. 2013 (MNRAS 434, 2629: conditional entropy);
  Kovács, Zucker & Mazeh 2002 (BLS); Hippke & Heller 2019 (A&A 623, A39: TLS — the search statistic, the default
  transit shape with limb darkening, the duration grid, SDE); Harris et al. 1989 (Icarus 77, 171: FALC); Roberts,
  Lehár & Dreher 1987 (CLEAN); Foster 1995 (AJ 109, 1889: CLEANest); McQuillan, Aigrain & Mazeh 2013 (ACF for
  rotation); VanderPlas & Ivezić 2015 (ApJ 812, 18: multi-band periodogram); VanderPlas 2018 (ApJS 236, 16:
  "Understanding the Lomb–Scargle periodogram" — the practical guide for grids, windows, aliases, FAP).
- **Ours now:** LS, BLS, PDM, ANOVA, DFT, CLEAN.
- **Build:**
  1. `timeseries/methods/` one module per method with the common signature `power(lc, freqs, **options) →
     PeriodogramResult(freq, power, statistic_name, higher_is_better, options, peaks)`: `gls` (floating mean,
     weights, n harmonics), `dcdft`, `dft` (amplitude spectrum in the data's unit), `aov` (phase bins), `aovmh`
     (multi-harmonic), `pdm`, `pdm2` (binless), `string_length` (Lafler–Kinman, Dworetsky, Renson, Clarke
     multi-band), `jurkevich`, `conditional_entropy`, `bls`, `tls`, `falc` (Fourier order m with one zero point per
     night / set, the F-test for the order), `acf` (period from the first peaks of the autocorrelation of evenly
     resampled data), `multiband` (shared-phase model with per-band terms), `clean`, `cleanest`.
  2. The frequency grid: automatic from the data span T and an oversampling factor (default 5 per 1/T for
     sinusoidal methods; for BLS / TLS the optimal uniform-in-duty-cycle grid of Ofir 2014); range from a pseudo-
     Nyquist (median cadence, with the note that uneven sampling allows higher) to 1/T; "budget" guard (have) with a
     clear message and the GPU offer.
  3. A method chooser that explains: a table in the Help panel and one line under the choice ("Eclipsing binary →
     AoV multi-harmonic or PDM; shallow transit → TLS; pulsator → GLS / DFT; sparse survey data → conditional
     entropy or multi-band; asteroid → FALC"); "Compare methods" runs a chosen set and overlays the normalised
     periodograms with a table of each method's best period.
  4. Native CPU kernels (ARC-9, threaded) for the fold statistics (`pdm`, `aov`, `aovmh`, `string_length`,
     `conditional_entropy`, `tls`) and GPU twins through `compute` for `gls` (direct sums), `dft`, `pdm` (have),
     `aov`, `conditional_entropy`, `bls` (have), `tls`; all with NumPy reference twins and equality tests; the fast
     O(N log N) LS of Astropy stays the default path for evenly spaced-like data.
  5. Step `timeseries.periodogram(method, …)` replaces the per-method steps (old step ids kept as wrappers).
- **Accept:**
  1. Each method against an independent statement of its formula on small data (tests) and against a reference
     implementation where one exists (Astropy LS and BLS; the reference TLS package run beside ours: same best
     period and SDE within 2 % on the TESS planet host; Period04's or the published table for the δ Scuti set).
  2. Recovery tests: sinusoid, saw-tooth (RR Lyrae-like), Algol-type eclipses, W UMa, shallow transit (depth = 1σ
     per point, 3 transits), each with realistic gaps: the methods advised for each recover the period in ≥ 95 % of
     100 realisations.
  3. Budgets: 10^5 points × 10^5 frequencies: GLS < 3 s (fast path), PDM / AoV / CE < 10 s native on 4 cores, < 2 s
     GPU; TLS on a 27-day TESS sector at 2 minutes < 60 s CPU, < 10 s GPU.
- **Files:** `timeseries/methods/*.py`, `native/src/fold.rs`, `compute/*.py`, steps, tests, guide 07 and 13.

### PER-4. Is the peak real? Significance, window, aliases, errors  (P1)
**partial** — done (2026-11-12): `timeseries/significance.py`: `peak_table` (the highest local peaks, each noted when
it follows from a higher one: alias by k × 1 d⁻¹ or 1 yr⁻¹ including the reflection at zero, harmonic, subharmonic),
`fap_baluev` (Astropy's Baluev bound over the searched range), `fap_shuffled` (values shuffled among the times, any
method), `frequency_error` (Montgomery & O'Donoghue 1999), `verdict` (the top peak in words); `timeseries.period`
returns `peaks` and, for LS-type power, `fap`. Tests: nightly sampling with P = 0.3719 d at S/N 1 per point: the
daily aliases labelled and the true peak first in ≥ 90 % (20 of 20 measured); pure noise: the analytic 1 % level
exceeded in 1.25 % of 400 realisations; shuffled and analytic FAP within a factor 2 near 1 %; M&O's error within
20 % of the scatter of 200 fitted frequencies. Left: the window overlay, the sampling's own window peaks, S/N of DFT
peaks with selectable criteria, SDE for BLS / TLS, bootstrap / MCMC frequency errors, red-noise levels, the peak
table and verdict in the window, `period_warnings` as notes.
- **Read first:** Baluev 2008 (MNRAS 385, 1279: analytic false-alarm bound); VanderPlas 2018 §7 (window, aliases,
  failure modes); Breger et al. 1993 (A&A 271, 482: S/N ≥ 4), Baran & Koen 2021 (AcA 71, 113: thresholds for TESS
  lengths); Montgomery & O'Donoghue 1999 (DSSN 13, 28: errors of f, A, φ), Kovács 1981 (period error); Loumos &
  Deeming 1978 (resolution 1.5/T); Eyer & Bartholdi 1999 (Nyquist for uneven sampling); Schwarzenberg-Czerny 1991
  (correlated noise factor).
- **Build:**
  1. For every periodogram: the spectral window centred on the highest peak (overlay), the list of alias families
     of each peak (f ± k × 1 d⁻¹, ± 1 yr⁻¹, ± the sampling's own window peaks found numerically, harmonics f/2, 2f,
     f/3, 3f) marked on the plot and noted in the peak table ("alias of peak 1 by 1 d⁻¹").
  2. Significance per method: analytic FAP (Baluev) for LS-type; bootstrap / permutation FAP for any method (N
     shuffles in batch on the GPU or threads, with the 10 %, 1 %, 0.1 % levels drawn); S/N of a DFT peak from the
     residual spectrum's mean amplitude in a box (have `noise_at`) with the criterion line selectable (4.0, 3.5 for
     combinations, the Baran & Koen value for the data length); SDE and SNR for BLS / TLS with the usual thresholds
     (SDE ≥ 9 for TLS, ≥ 7 BLS) and odd / even depth difference, the secondary-eclipse depth at phase 0.5 and the
     number of transits.
  3. Period / frequency error: analytic (M&O 1999 with the correlated-noise factor), from the peak width and S/N
     (Kovács), by bootstrap, and by MCMC of the harmonic model; shown side by side; the largest reported.
  4. Red-noise aware levels: the periodogram of the residuals smoothed in log frequency as the local noise (for
     space data with granulation / spots).
  5. The peak table (Inspector): rank, frequency, period, power or amplitude, S/N, FAP, notes (alias / harmonic /
     combination of …), tick "accept"; a verdict line for the top peak in words ("significant (FAP < 0.1 %), not an
     alias of the sampling; its double is also plausible: check the folded curve — eclipses?").
  6. The honest warnings of `period_warnings` (span too short, fewer than two cycles, period near the sampling) move
     into this framework as notes.
- **Accept:** pure noise: the 1 % FAP level is exceeded in 0.5–2 % of 2000 realisations for GLS, PDM, AoV, CE;
  analytic and bootstrap FAP agree within a factor 2 at 1 %; ground-based-like sampling with a true period of
  0.3719 d: the daily alias family is labelled and the true peak is ranked first in ≥ 90 % at S/N 10; frequency
  errors from M&O match the scatter of fitted frequencies over 500 realisations within 20 %.
- **Files:** `timeseries/significance.py`, `timeseries/aliases.py`, UI peak table, tests, guide 13.

### PER-5. Folding and refining  (P1)
**partial** — done (2026-11-12), the engine: `timeseries/fold.py`: `binned` (median per phase bin with its error),
`refine` (a mean and n harmonics with the frequency free, by least squares about the middle of the data; error from
the covariance scaled by χ²ᵣ), `eclipses` (both minima of a folded binary: phases, depths below maximum light,
widths at half depth, e cos ω ≈ π/2 (φ_II − 0.5)), `p_or_2p` (folded on 2P, odd and even minima: a depth difference
beyond 3 σ makes 2P the orbital period). Tests: 20 refinements of a W UMa with nightly gaps, pulls with σ 0.6–1.5;
a W UMa that GLS finds at half its period gets its orbital period back (z ≈ 9), equal minima keep the half; an
eccentric Algol's depths, widths and secondary phase. Left: the fold panel (slider, keys, colours by cycle), T0
choices, "Send to O−C / Models / Exoplanets", the 10⁶-point refolding speed.
- **Ours now:** `timeseries/period.fold`, the folded plot of the Period search tab (`ui/period_page.py`, `ui/workspaces.fold_phase`).
- **Build:** the folded plot: phase −0.25 … 1.25 (or 0 … 2), points coloured by set / band / time (cycle number as
  a colour scale to see period error as a drift), binned median with error bars, optional harmonic model; a period
  slider and keys (← → by one resolution element / 10; `2` double, `H` half, `3` thirds) with the plot updating
  live; T0 choices: time of minimum (by OC-2 on the folded curve), of maximum, or typed; "Refine": local maximum of
  the chosen statistic on a fine grid + harmonic-fit refinement, with the error (PER-4.3); eclipsing-binary help:
  primary and secondary depths, their phase difference (→ e cos ω), widths, and the test "P or 2P?" (odd / even
  depth difference with its significance); outputs: ephemeris line, the folded curve as a file, "Send to O−C",
  "Send to Models / Exoplanets" with the starting values measured here.
- **Accept:** dragging the slider refolds 10^6 points at ≥ 20 fps (phase computed in the view on decimated data,
  exact on release); on the W UMa set the P-or-2P test picks the orbital period; refined periods of the recovery
  tests are within 1σ of the truth.
- **Files:** `timeseries/fold.py`, UI fold panel, tests.

### PER-6. Frequency analysis as Period04, and beyond  (P1)
**partial** — done (2026-11-12), the engine: `timeseries/frequency.py`: terms with f / A / φ fit flags and
relations (Σ n_j f_j of independent terms: computed, not fitted, their errors propagated); `improve_all`
(Levenberg–Marquardt on the normal equations with the analytic Jacobian, weights, covariance errors; 50 terms on
10⁵ points in 1.6 s here, a case in tools/speed.py — MINPACK's QR without BLAS took 10 s); `identify` (simplest
combination of up to three stronger independent terms, |n| ≤ 3, within 1.5/T or 4 σ of the propagated errors;
unresolved pairs): every injected combination found and a false one in under 5 % of 200 realisations;
`analytic_errors` (M&O 1999 with Schwarzenberg-Czerny's √D from the residual runs), `monte_carlo_errors` (model +
shuffled residuals, threads): within 25 % of each other and of the covariance on white noise; `variations`
(amplitude and phase per subset with errors). Also: `time_shift` (the orbit's light-travel time delaying every
pulsation, fitted with the terms: a 100 s light-time orbit recovered to a few seconds from a start 30 % off) and
`to_table` (c/d or µHz, amplitude units, relations as text, t_ref in the meta; ECSV and LaTeX). Left: the δ Scuti
campaign check, the interface (items 1–2, 6), the native DFT (item 8).
- **Read first:** Period04 manual (Fourier and Fit modules; "Improve all", "Calculate amplitude / phase
  variations", "Periodic time shift"); Lenz & Breger 2005; Breger et al. 1999 (combination frequencies); Pápics
  2012 (identification of combinations and harmonics by resolution); Kurtz et al. 2015 (the fσ / TESS practices);
  Shibahashi & Kurtz 2012 (frequency modulation by binary motion).
- **Ours now:** `fourier.prewhiten` (automatic loop to an S/N stop), `fourier_fit`, `noise_at`, the Frequency
  analysis tab.
- **Build:**
  1. The frequency list as the heart of the Frequencies stage (kit `TableView`, editable): id (F1 …), frequency,
     amplitude, phase, their errors, S/N, "fit" ticks per column (f / A / φ free or fixed), relation (independent |
     `2 F1` | `F1 + F2` | `F3 − F1` | typed expression — the frequency is then computed, not fitted), note.
  2. Loop by hand (Period04's way): compute the spectrum of the residuals → click a peak (or "Take the highest")
     → it is added → "Improve all" (non-linear least squares of all free parameters at once; Levenberg–Marquardt
     with analytic Jacobian; weights) → the residual spectrum redraws. And automatic: "Run until S/N < limit" (have)
     with a cap on the number and a stop when the improvement of BIC ends.
  3. Automatic identification after each improvement: harmonics and combinations (orders up to 3 terms, coefficients
     |n| ≤ 3) of stronger independent frequencies within the resolution 1.5/T (and the error bars) are proposed in
     the Relation column for the user to accept; frequencies closer than the resolution are flagged "unresolved".
  4. Errors: analytic (M&O 1999, with the correlated-noise factor from the residuals' autocorrelation), from the
     covariance of the fit, and Monte Carlo (N simulated data sets with the fitted model + shuffled residuals, in
     threads) — the three in the table on request.
  5. Subsets: by set, band, night, or ranges; zero point per subset fitted with the model; **amplitude and phase
     variation**: the same frequencies fitted per subset with A and / or φ free (table and plot A(t), φ(t));
     **periodic time shift**: an orbital light-time term (P_orb, a sin i / c, e, ω, T) applied to all pulsation
     phases and fitted (binary pulsators).
  6. Views: amplitude spectrum (original, residual, significance curve = 4 × noise), spectral window, the fit over
     the data (zoomable), residuals, phase plot of any single frequency with the others removed.
  7. Units: frequency c/d and µHz; amplitude mmag, ppt, ppm; phase in cycles (0–1) of sine with the reference time
     stated; exports of the table (LaTeX, ECSV), the model, the prewhitened curve.
  8. Scale: 10^6 points, 200 frequencies: "Improve all" with the native kernel for the design matrix and the DFT.
- **Accept:** the δ Scuti campaign's published frequencies (the first 15) are reproduced within their published
  errors and Period04's values within 1e-6 c/d where Period04's output is available as a stored table; combination
  identification finds every injected combination in a synthetic three-mode signal and proposes no false one in
  95 % of 200 realisations; Monte Carlo and analytic errors agree within 25 % on white noise; "Improve all" for 50
  frequencies on 10^5 points < 2 s; a residual DFT of 10^5 × 10^5 < 3 s (GPU < 1 s).
- **Files:** `timeseries/frequency.py` (from `fourier.py`), `native/src/dft.rs`, `compute/dft.py`, UI frequencies
  panel, tests, guide 07.

### PER-7. Data from the missions, handled as lightkurve does  (P1)
**open**
- **Ours now:** `timeseries/archive.py` (`read_mission_lc`, `join`, `download`: PDCSAP / SAP, quality ≠ 0 dropped, sectors joined).
- **Build:** in the Data stage for TESS / Kepler / K2: the choice of product per sector (author SPOC 120 s / 20 s,
  TESS-SPOC FFI, QLP, and others on MAST) with a table of what exists; flux column choice (PDCSAP default, SAP);
  quality bitmask (default / hard / none); per-sector normalisation and stitching; crowding and flux-fraction
  values shown (CROWDSAP, FLFRCSAP) with a warning below 0.8; momentum-dump and scattered-light intervals shaded
  on the plot; "Make my own from the pixels" opens PHO-32; exposure-time smearing noted for folding of short
  periods (30-minute cadence).
- **Accept:** for the W UMa set the stitched curve equals lightkurve's `stitch()` of the same files within 1e-6
  relative (reference stored); the product table for a recorded target lists what MAST has.
- **Depends on:** PER-1.
- **Files:** `services/mast.py`, `timeseries/missions.py` (from `archive.py`, re-exported), `ui/lightcurves/panels/data.py`, `tests/test_missions.py`

### PER-8. GPU and native speed for search and significance  (P1)
**open**
- **Build:** the kernels of PER-3.4 and the batch FAP of PER-4.2; `tools/speed.py` cases for each; chunking by the
  adapter's limits; the phase precision trick already used for PDM (float64 phase reference per chunk on the CPU,
  small residual on the GPU) applied to all GPU fold kernels; the owner's RTX 4050 measurements written here and in
  `compute/thresholds.json` (ARC-10).
- **Accept:** GPU = CPU within the documented tolerance for every kernel (tests under the software adapter); the
  budgets of PER-3; "auto" picks the faster path at the measured sizes.
- **Files:** `native/src/{fold,dft}.rs`, `compute/{gls,dft,aov,entropy,tls,permutation}.py`, `compute/thresholds.json`, `tests/test_compute.py`, `tools/speed.py`

### PER-9. Time–frequency analysis  (P2)
**partial** — done (2026-11-12): `timeseries/timefreq.py`: Foster's WWZ (Z, amplitude, N_eff; masked where the
effective or the absolute weight is below a minimum — N_eff alone counted far points across a gap), `ridge` (the
peak frequency per time, parabola-refined). Tests: a 300 → 330 d chirp traced within 2 %; a switch from 1.0 to
1.3 c/d seen on either side of a gap that stays empty. Left: the sliding GLS, the native / GPU twin for the 5 s
target (NumPy: 2.5 s for a quarter of the grid), the Mira set, the panel.
- **Read first:** Foster 1996 (AJ 112, 1709: the weighted wavelet Z-transform, constant c and its meaning);
  Templeton 2004 (JAAVSO 32, 41); lightkurve's sliding periodograms.
- **Build:** `timeseries/timefreq.py`: WWZ (frequency × time grid; Z statistic and the amplitude; decay constant
  choice with its trade-off explained; edge and gap masking by the effective number of points); sliding-window GLS /
  DFT ("dynamic spectrum"); a ridge tracer (period against time with errors); image plot with the time axis shared
  with the light curve; GPU twin for WWZ.
- **Accept:** a synthetic chirp (period drifting 300 → 330 d) is traced within 2 %; a mode switching between two
  frequencies is shown at the right epoch; the Mira AAVSO set shows its known period change; WWZ 5000 points × 200
  frequencies × 200 times < 5 s CPU.
- **Files:** `timeseries/timefreq.py`, `compute/wwz.py`, `ui/lightcurves/panels/timefreq.py`, `tests/test_timefreq.py`

### PER-10. Shapes and classes: Fourier parameters and a suggested type  (P2)
**partial** — done (2026-11-12): `timeseries/shape.py`: the Fourier decomposition of the folded curve (sine series,
order by BIC), R_k1 and φ_k1 with errors propagated from the covariance (inside 1σ in 60–76 % of 200 realisations),
the rise time and the skewness of the fitted curve. Left: the class boundaries with citations and the suggestion
(classify.py), the colour–magnitude position, the RRab metallicity with its validity check, the 30 stored curves.
- **Ours now:** `fourier.fourier_fit`, `fourier.times_of_maximum`; no Fourier parameters (R21, φ21) and no class suggestion.
- **Read first:** Simon & Lee 1981 (ApJ 248, 291: R21, φ21, …); Deb & Singh 2009 (A&A 507, 1729); Jurcsik & Kovács
  1996 ([Fe/H] from φ31, with its validity conditions); Gaia DR3 variability classification papers (Rimoldini et
  al. 2023) for the features that separate classes.
- **Build:** Fourier decomposition of the folded curve (order by BIC): amplitudes, R_k1, φ_k1 with errors; rise
  time, skewness, amplitude; eclipse parameters (PER-5); with Gaia colour and absolute magnitude (parallax) a
  position in the colour–magnitude diagram; a **suggested** class from published boundaries (period, amplitude,
  R21, φ21, φ31, colour, M_G) with the features shown beside the published ranges and the cross-match to VSX / Gaia
  classes — never a silent label; RRab metallicity estimate only inside the published validity ("Dm" criterion).
- **Accept:** on 30 stored survey curves of known class (RRab, RRc, DCEP, DSCT, EA, EB, EW, Mira) the suggestion
  matches the catalogue in ≥ 85 %, and where it differs the table shows which feature disagrees.
- **Files:** `timeseries/shape.py`, `timeseries/classify.py`, `resources/data/class_boundaries.toml` (with citations), `tests/test_lc_shape.py`

### PER-11. Asteroid rotation: FALC and multi-night zero points  (P2)
**open**
- **Build:** on PER-3's `falc`: nights as sets with free zero points (or fixed from calibrated magnitudes, PHO-21),
  Fourier order by F-test, the period spectrum (RMS against period), the composite light curve with amplitude and
  the usual plot style, double-peaked assumption explained (P vs P/2), export to ALCDEF with the result fields;
  light-time correction check.
- **Accept:** the asteroid set's published period is recovered within its error; synthetic three-night data with
  zero-point errors of 0.05 mag recover the period.
- **Files:** `timeseries/methods/falc.py`, `ui/lightcurves/panels/asteroid.py`, `tests/test_falc.py`

### PER-12. Injection and detection limits  (P2)
**partial** — done (2026-11-12): `timeseries/injection.py`: `recovery` (signals injected over a period × amplitude
grid into given data, any search, recovered within half the frequency resolution — a relative period tolerance
missed long periods — aliases optional for eclipses; threads), `gls_half_amplitude` (the analytic 50 % level).
Tests: the measured 50 % amplitudes of two periods within 20 % of the analytic one. Left: transit and eclipse
signal shapes, the contour plot, the GPU batch and its 2-minute target.
- **Build:** "What could I have detected?": inject sinusoids / transits / eclipses of given shape over a grid of
  periods and amplitudes into the residuals (or the cleaned data), run the chosen search, and map the recovery
  fraction; a contour plot of 50 % and 90 % detection; batch on the GPU.
- **Accept:** on white noise the 50 % contour follows the analytic expectation for GLS within 20 %; a 30 × 30 grid
  with 20 injections each finishes in < 2 min on the GPU-less reference machine for 20 000 points.
- **Files:** `timeseries/injection.py`, `ui/lightcurves/panels/limits.py`, `tests/test_injection.py`

### PER-13. Multi-band and sparse survey data together  (P2)
**partial** — done (2026-11-12): `methods.multiband` (VanderPlas & Ivezić 2015: a mean per band, shared harmonics
and each band's own, through the same coarse-to-fine search as the other methods): two sparse bands of an RRab with
different means and amplitudes give the period within 1e-4. Left: the survey readers' cleaning presets, the
stacked folded plot, the stored RR Lyrae set's alias check.
- **Build:** on PER-3's `multiband` and Clarke's string length: joint period search over g / r (ZTF), V / g
  (ASAS-SN), G / BP / RP (Gaia), o / c (ATLAS) with per-band amplitudes and means; the folded plot stacked by band;
  survey-specific cleaning presets (ASAS-SN camera offsets as sets; ZTF `catflags`; ATLAS error cuts) applied by
  the readers and listed in the Clean history.
- **Accept:** the sparse RR Lyrae set gives the catalogue period from the joint search where each single band
  alone gives an alias in at least one (asserted on the stored data).
- **Files:** `timeseries/methods/multiband.py`, `services/lc_{ztf,asassn,atlas,gaia}.py` (cleaning presets), `tests/test_multiband.py`

### PER-14. Solar-like and classical pulsators: seismology basics  (P3)
**open**
- **Read first:** Huber et al. 2009 (CoAst 160, 74: νmax and Δν pipeline); Kjeldsen & Bedding 1995 (scaling
  relations); lightkurve's seismology module (method descriptions).
- **Build:** power density spectrum (ppm² µHz⁻¹), smoothing, background fit (Harvey-like terms + white noise),
  νmax from the smoothed excess, Δν from the autocorrelation of the spectrum, the échelle diagram (interactive Δν
  slider), scaling-relation mass and radius with Teff; period spacing ΔΠ for g-mode pulsators (γ Dor) as a
  period-échelle diagram.
- **Accept:** the Kepler solar-like set's published νmax and Δν within 3 %.
- **Files:** `timeseries/seismology.py`, `ui/lightcurves/panels/seismology.py`, `tests/test_seismology.py`

### PER-15. Rotation and activity  (P3)
**open**
- **Build:** rotation period from ACF (McQuillan) and GLS with harmonic checks; a quasi-periodic Gaussian-process
  fit (celerite2, MIT — dependency checked) for the period posterior; spot-evolution plots (phase–time "river");
  flare finder (upward outliers of ≥ 3 consecutive points above nσ after detrending) with equivalent durations and,
  with a distance and band, energies; a table of flares.
- **Accept:** synthetic spotted-star curves recover the rotation period within 5 % by both methods; injected
  flares above 5σ are found with ≥ 90 % completeness and < 5 % false positives.
- **Files:** `timeseries/{rotation,flares}.py`, `tests/test_rotation.py`

### PER-16. Report  (P1)
**partial** — done (2026-11-12): `timeseries/report.py`: the peaks table (A&A style, value(error) as OC-12's
`paren`), the methods paragraph, the VSX submission sheet (type as a suggestion, period and epoch with errors,
range, rise time or eclipse duration); frequencies through `frequency.to_table`. Left: the figure set, the AAVSO /
BAV summaries, the W UMa and δ Scuti report checks.
- **Ours now:** `ui/export.save_results` (CSV / LaTeX of a results table), the plot toolbar's publication figure.
- **Build:** the figure set through `ui/plot/publish` (light curve, periodogram with significance levels and the
  window inset, folded curve with the binned mean, frequency spectrum before / after prewhitening); tables: peaks,
  frequencies (PER-6.7), ephemeris; the methods text (ARC-11: method, grid, weights, significance test, data
  sources to cite); a VSX submission helper sheet (type suggested by PER-10, period, epoch, range in the band,
  rise time for pulsators / eclipse duration for binaries, the phase plot in VSX's requested form); AAVSO / JAAVSO
  and BAV-style summaries.
- **Accept:** the report of the W UMa set and of the δ Scuti set compile and carry every number at the session's
  precision.
- **Files:** `timeseries/report.py`, `resources/methods/period_*.txt`, `tests/test_period_report.py`

### PER-17. Period search for many stars  (P2)
**open**
- **Build:** batch mode behind PHO-30 and for a folder of light-curve files: one GPU / threaded batch across stars,
  a results table (best period, FAP, second peak, class suggestion) with thumbnails; export.
- **Accept:** 2000 curves × 300 points × 20 000 frequencies < 2 min CPU, < 20 s GPU.
- **Files:** `timeseries/batch.py`, `ui/lightcurves/variable_search/`, `tests/test_period_batch.py`

### PER-18. Uncommon methods on request  (P3)
**open**
- **Build:** Bayesian periodicity (Gregory & Loredo 1992), SuperSmoother (Reimann 1994), fast χ² (Palmer 2009),
  Bloomfield, Abbe; each only when a user asks or a comparison needs it — listed so that nothing of Peranso's
  list is missing without a reason.
- **Files:** `timeseries/methods/{gregory_loredo,supersmoother,fastchi2,bloomfield,abbe}.py` (only when built)

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
