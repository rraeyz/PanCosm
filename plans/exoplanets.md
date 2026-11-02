# Exoplanets: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.7).

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

Transiting and radial-velocity planets from one night's transit to a global solution: exact transit models, radial
velocities, the host star (spectral energy distribution, isochrones, parallax), priors from the archives, timing
variations, vetting of candidates, Bayesian uncertainties with convergence tests, and the tables of a discovery or
follow-up paper. This file also builds two shared engines used by other areas: **the transit / occultation kernel**
(EXO-1, used by PHO-26 and MOD-18) and **the inference engine** (EXO-5, used by OC, SPE, MOD).

**Goal:** what EXOFASTv2 does (the reference for global fits), without IDL, without a terminal and without hours
of blind waiting: live chains, a convergence light, and a parameter table that explains itself — plus the one-night
workflow of AstroImageJ, HOPS and EXOTIC, and the candidate vetting of the TESS follow-up tools.

## What the reference programs do

Read: EXOFASTv2 (BSD-3; Eastman et al. 2019, arXiv:1907.09480; `exofastv2.pro` header, `parnames.README`,
`exofast_chi2v2.pro`, `exofast_demcpt_multi.pro`, `exofast_occultquad_cel.pro`, `derivepars.pro`, `mkticsed.pro`, the
`examples/`); Eastman, Gaudi & Agol 2013 (EXOFAST); Mandel & Agol 2002; Agol, Luger & Foreman-Mackey 2020 (AJ 159,
123); Kreidberg 2015 (batman: GPL, run beside ours only); pylightcurve (the model behind HOPS) and HOPS / EXOTIC
documentation; juliet (Espinoza et al. 2019), allesfitter (Günther & Daylan 2021), RadVel (Fulton et al. 2018),
exoplanet (Foreman-Mackey et al. 2021) as descriptions of practice; Winn 2010 ("Transits and Occultations");
Seager & Mallén-Ornelas 2003; Kipping 2013; Torres, Andersen & Giménez 2010; Stassun & Torres 2016; Dotter 2016 and
Choi et al. 2016 (MIST).

| Topic | EXOFASTv2 | juliet / allesfitter | AstroImageJ | HOPS / EXOTIC | Ours now |
| --- | --- | --- | --- | --- | --- |
| Transit model | Mandel–Agol quadratic (stable elliptic-integral form), long-cadence integration, several planets and bands | batman / catwoman / ellc | Mandel–Agol quadratic | pylightcurve (Claret four-parameter) | trapezoid; two-sphere numerical integral |
| Radial velocities | Keplerians per planet, zero point and jitter per instrument, slope, quadratic, Rossiter–McLaughlin, Doppler tomography | Keplerians, GPs, RM (allesfitter) | — | — | SB1 / SB2 orbit fits in Spectroscopy |
| Star | SED (bolometric-correction grid or atmospheres) + parallax + MIST / YY / PARSEC tracks or Torres relations, in the same fit | stellar density prior | host-star panel with tabulated relations | priors from the archive | typed radii for Rp |
| Limb darkening | Claret & Bloemen tables as priors from (Teff, log g, [Fe/H]) per band | free or Kipping-sampled; LDTk outside | typed, fit or fixed | ExoTETHyS tables | typed quadratic |
| Priors | file: Gaussian, uniform bounds, fixed, start values for any parameter | full prior language | prior centre and width per parameter | from the NASA Exoplanet Archive | bounds only |
| Sampler | differential-evolution MCMC with parallel tempering; stops on Gelman–Rubin < 1.01 and > 1000 independent draws | nested sampling (evidence, model comparison) or emcee | least squares (χ², BIC) | MCMC (HOPS); nested sampling (EXOTIC) | emcee from a least-squares solution, fixed step count, no convergence test |
| Detrending | additive and multiplicative columns per transit | linear models and GPs | multiplicative terms in the fit, BIC selection | airmass | linear terms with the trapezoid |
| Timing | TTV, depth and inclination variations per transit | TTVs | Tc per night | Tc per night | minimum times → O−C |
| Extras | secondary eclipse (thermal, reflected), dilution, beaming, astrometry, several stars | GPs for stellar noise, flares and spots (allesfitter) | odd / even view, NEB reports | ExoClock / AAVSO files | ETD / ExoClock files, transit summary |
| Output | LaTeX table of fitted and derived parameters (medians, 68 % intervals), figures of every data set, PDFs, covariances, chains | posteriors, evidence | plots, tables, reports | upload files | CSV, files for ETD / ExoClock |

## What we already have (do not redo)

- `models/eb.py` + `fit.py` usable for a planet as a dark second sphere; `minima.trapezoid_fit`;
  `models/transit_report.py`; ephemerides from the NASA Exoplanet Archive in Planning (`planning/ephemerides.py`);
  TESS / Kepler light curves and pixel files; BLS; the Qatar-1 night (O−C +0.27 min against ExoClock).

## Decisions

- Shared code lives outside this area's package: the transit / occultation kernel in `astrowb/occult/` (+ native
  twin), inference in `astrowb/core/inference/`, the host star in `astrowb/stars/`.
- Default parameter set for sampling (EXO-4): P (or log P for long baselines), Tc at the epoch that minimises its
  covariance with P, Rp/R★, b, stellar density ρ★ (so that a/R★ follows), √e cos ω, √e sin ω, K (or log K), limb
  darkening as Kipping's q1, q2; everything else is derived.
- Every reported interval is the 68 % credible interval around the median unless the user chooses mode / highest
  density; a result is "final" only when the convergence test passes.
- Times are BJD_TDB; input in any other standard is converted or refused (ARC-15).

## To ask the owner

- Nothing blocks. If the owner's 2209-A planet project has light curves or velocities of its own, they would make
  the best acceptance test of EXO-7.

## For the owner to try

- After EXO-W: fit the Qatar-1 practice transit: name the planet, press "Fill from the archive", "Fit"; say whether
  the result table tells you what you need for an ExoClock submission.

## Data used

- Qatar-1 b (LCO, our night); HAT-P-32 b (MicroObservatory); WASP-12 b (TESS sector 20 pixel file).
- To add (each with `SOURCE.md`): EXOFASTv2's public example data (HAT-P-3 b: transit and RV files, with the
  published EXOFASTv2 result to reproduce); a multi-transit, multi-band ground data set with published global
  parameters; a TESS planet with HARPS velocities public at ESO / DACE; published mid-times lists of WASP-12 b
  (decay) and of a system with strong TTVs; a TESS candidate later shown to be a blended eclipsing binary (for
  vetting); model curves from batman run beside ours (scripts stored).

## Steps

Order of work: engines first (lane b of PLAN.md §5): EXO-1, 2, 3, 4, 5; then EXO-W, 6, 7, 9, 10, 12, 16 (P1);
P2: 8, 11, 13, 14, 17; P3: 15, 18.

### EXO-1. The transit and occultation kernel  (P1)
**partial** — done (2026-11-12): `occult/laws.py` (uniform, linear, quadratic, square-root, logarithmic, power-2,
four-parameter; the disc flux; a physical check as messages; Kipping's q ↔ u), `occult/flux.py`
(`occulted_fraction(z, k, law, coeffs)`: the radial integral split at the kinks, cosine-clustered Gauss–Legendre —
the eclipsing-binary model's kernel made general; `models.eb.eclipsed_fraction` now calls it), `occult/model.py`
(`separation`: z(t) and in-front from P, Tc, a/R★, i, e, ω with the binaries' orbit code; `transit`: exposure
sub-samples chosen from the ingress, third light, the occultation as a uniform planet disc). Tests: the uniform
disc within 1e-8 of the closed form for k 0.001–2, z 0–3; every law within 1e-7 of an independent adaptive
integration (56 random cases); no jump above 1e-8 at any contact; depth, T14, occultation depth and dilution;
30-min exposures within 1e-6 of a fine midpoint average. **Changed from the plan:** the integral, not Mandel–Agol's
elliptic integrals, for every law — its error (2e-9) is already under the analytic target. Left: analytic
derivatives for the fits, several planets, phase curve, ellipsoidal and beaming terms, light-travel time, the
native twin and the 30 ms budget (0.75 s now for 10⁵ × 5 points in NumPy), the batman comparison script.
- **Read first:** Mandel & Agol 2002 (the cases and the elliptic integrals); Agol, Luger & Foreman-Mackey 2020
  (stable analytic solution for polynomial limb darkening with derivatives; their accuracy figures); Eastman et al.
  2013 §3 (numerical stability of the quadratic case; `exofast_occultquad_cel`: Bulirsch's elliptic integrals);
  Kreidberg 2015 (the general radial-integration scheme and its error control for non-linear laws); Maxted & Gill
  2019 (A&A 622, A33: power-2 law); Kipping 2010 (exposure integration); Giménez 2006 (occultation of any law).
- **Build:**
  1. `occult/laws.py`: uniform, linear, quadratic, power-2, square-root, logarithmic, four-parameter; conversions
     (u1, u2) ↔ (q1, q2) (Kipping 2013); validity checks (non-negative, monotonic intensity) as codes.
  2. `occult/flux.py`: `occulted_fraction(z, k, law, coeffs)` for the sky-projected separation z (in stellar radii)
     and radius ratio k: analytic for uniform, linear and quadratic (elliptic integrals in Carlson / Bulirsch form,
     stable at the contact points, z → 0, k → 1, z = k, z = 1 ± k), semi-analytic or adaptive radial integration for
     the other laws with a guaranteed absolute error (default 1e-7); analytic derivatives with respect to z and k
     for the quadratic case (used by the least-squares fits).
  3. `occult/orbit.py`: time → z for circular and eccentric orbits (native Kepler solver), from P, Tc (time of
     inferior conjunction), a/R★ (or ρ★ and P), b (or i), e, ω; front / behind flag; secondary-eclipse timing with
     e; light-travel time across the system on request.
  4. `occult/model.py`: `transit(t, params, band, exposure=None, n_sub=auto)`: several planets (sum of their
     independent dimmings; mutual events ignored and said so), exposure integration (sub-samples chosen from
     exposure / ingress duration to keep the error < 1e-6), dilution `d` per band (third light), **occultation**
     (secondary eclipse: the planet as a uniform disc with depth δ_occ), phase curve terms (reflected light with a
     Lambert phase function and geometric albedo; thermal as a cosine with an offset), ellipsoidal and beaming
     amplitudes as free harmonics (for hot Jupiters in space photometry; Faigler & Mazeh 2011).
  5. Native twin (ARC-9, threaded over points); NumPy reference twin; tests of equality.
  6. Tests: against closed forms (uniform disc); against high-precision brute-force 2-D integration on a 4000²
     grid for 200 random (z, k, law) cases; against batman curves computed beside ours for the laws both have;
     continuity across every special case boundary (no jump > 1e-10).
- **Accept:** absolute error ≤ 1e-8 (quadratic, analytic) and ≤ 1e-7 (other laws) of the stellar flux for
  k ∈ [0.001, 2], z ∈ [0, 3]; agreement with batman within its own stated error; 10^5 points × supersampling 5,
  quadratic: < 30 ms native; derivatives equal finite differences to 1e-6.
- **Files:** `occult/{laws,flux,orbit,model}.py`, `native/src/occult.rs`, `tests/test_occult.py`,
  `tests/validation/scripts/batman_reference.py`.

### EXO-2. Radial-velocity model  (P1)
**partial** — done (2026-11-12): `exoplanets/rv.py`: `Planet(P, tc, √e cos ω, √e sin ω, K)` with e, ω and the
periastron time (the transit at ν = 90° − ω, as occult.model), `model` (Keplerians from spectroscopy.orbit, a zero
point per instrument, linear and quadratic trend about t_ref), `log_likelihood` (jitter per instrument in the
variance), `fit_rv` (weighted least squares with the jitters taken from the residuals, then the likelihood with them
free; errors from the inverse Hessian). Tests: one planet equals `rv_model` to 1e-9; two planets, two instruments:
every parameter within 3 σ; over 20 realisations 82 % within 1.5 σ (87 % expected for exact errors) and the
jitters within 20 % on average. Left: the residual periodogram, `spectroscopy/orbit.py` using it, the 90 % with
EXO-5's sampler.
- **Read first:** Fulton et al. 2018 (PASP 130, 044504: bases, the bias of fitting e and ω directly, jitter in the
  likelihood); Eastman et al. 2013 §4; Lucy & Sweeney 1971.
- **Ours now:** `spectroscopy/orbit.py` (`rv_model`, SB1 and SB2 fits).
- **Build:** `exoplanets/rv.py`: sum of Keplerians (parameters per planet: P, Tc, √e cos ω, √e sin ω, K) + per-
  instrument zero point γ_j and jitter σ_j (in the likelihood: ln L = −½ Σ [r² / (σ² + σ_j²) + ln(2π (σ² + σ_j²))])
  + linear and quadratic trends about a reference epoch; conversion between Tc and time of periastron; the same
  conventions as `occult/orbit.py` (ω of the star's orbit — stated); zero points solved analytically inside each
  evaluation when no jitter is fitted; a periodogram of the residuals (GLS, PER) to look for further signals;
  reuse by SPE-15.
- **Accept:** equals `spectroscopy/orbit.rv_model` for one companion to 1e-9 km/s; synthetic two-planet, two-
  instrument data: every parameter within 1.5σ in 90 % of 200 realisations (with EXO-5's sampler); the jitter is
  recovered within 20 %.
- **Files:** `exoplanets/rv.py`, `spectroscopy/orbit.py` (uses it), `tests/test_exo_rv.py`

### EXO-3. Limb darkening from stellar parameters  (P1)
**open**
- **Ours now:** limb-darkening coefficients typed in the Models window (`ui/models_page.py`); no tables.
- **Read first:** Claret & Bloemen 2011; Claret 2017, 2018; Espinoza & Jordán 2015 (MNRAS 450, 1879: biases from
  fixing limb darkening, which law to use) and 2016; Morello et al. 2020 (ExoTETHyS: how coefficients should be
  fitted to model intensities); Kipping 2013.
- **Build:** `stars/limbdark.py` (shared with MOD-2): `coefficients(band, law, teff, logg, feh, source = ours |
  claret)` from MOD-6's tables with propagated uncertainty from the stellar parameters' errors plus a floor for
  model differences (default 0.05 in u1 and u2 for the quadratic law: EXOFASTv2 adds exactly this penalty,
  `u1err = u2err = 0.05` in `exofast_chi2v2.pro`, and rejects a step when the table has no value at the star's
  Teff, log g, [Fe/H]); as Gaussian priors on (u1, u2) transformed correctly to (q1, q2), or fixed, or free
  with Kipping's uniform sampling — the three choices in the Model stage with one line each on when to use which
  (low S/N single transit: fix or prior; high S/N or space data: free).
- **Accept:** coefficients for (5800 K, 4.44, 0.0) in V, R, TESS equal the published table values at the grid node
  and interpolate between nodes within 0.01 of a direct fit; the prior transformation is tested by sampling.
- **Depends on:** MOD-6.
- **Files:** `stars/limbdark.py`, `models/roche/limbdark.py` (shares it), `tests/test_limbdark_tables.py`

### EXO-4. Parameters and everything derived from them  (P1)
**partial** — done (2026-11-12): `exoplanets/derived.py`, pure functions on numbers or posterior samples with their
sources: ρ★ ↔ a/R★, b for transit and occultation, T14, T23, transit probability (Winn 2010), Mp from the mass
function, g_p without the star's mass (Southworth et al. 2007), T_eq with albedo and redistribution, incident flux,
Safronov number, TSM (Kempton et al. 2018); constants from astropy's IAU 2015 B3 nominal values (a test). Tests:
the Sun's density and the Earth's flux and 255 K from the Earth's orbit, a hot Jupiter's durations by hand,
Jupiter's mass and gravity from the Sun's 12.5 m/s. Left: the sampling set and its conversions, observed depth per
band, T_FWHM and τ, ESM, RM amplitude, occultation timing, the HAT-P-3 b comparison with EXOFASTv2.
- **Read first:** Winn 2010 (equations 14–19, 27–30: durations, probabilities, ρ★); Seager & Mallén-Ornelas 2003;
  Southworth, Wheatley & Sams 2007 (planet surface gravity from K and the light curve without the stellar mass);
  Eastman et al. 2019 table of derived parameters (`derivepars.pro`: the full list and definitions); Kempton et
  al. 2018 (TSM, ESM).
- **Build:** `exoplanets/parameters.py`: the sampling set of "Decisions" with exact conversions to and from the
  "physical" set (a/R★, i, e, ω, T_peri); **derived** quantities, each a pure function with its reference in the
  docstring, evaluated on every posterior sample: a/R★, a (AU), i, b (transit and occultation), depth (δ = k² and
  the observed depth with limb darkening per band), T14, T23, τ, T_FWHM, transit and occultation probabilities,
  time of secondary eclipse and of periastron, ρ★ from the light curve alone (to compare with the star's), Rp (R_J,
  R⊕), Mp sin i and Mp (M_J, M⊕), ρp, log gp (both routes), Safronov number, equilibrium temperature (zero albedo,
  full redistribution; and with typed albedo / redistribution), incident flux (cgs and Earth units), RM amplitude
  expected from v sin i, TSM and ESM; constants from IAU 2015 B3 nominal values (a test).
- **Accept:** every derived function against a hand-computed case from its paper; for HAT-P-3 b's published
  parameter medians the derived values equal EXOFASTv2's published ones within rounding.
- **Files:** `exoplanets/{parameters,derived}.py`, `core/constants.py` (IAU 2015 B3 nominal values), `tests/test_exo_derived.py`

### EXO-5. The inference engine (shared by O−C, Spectroscopy, Models, Exoplanets)  (P1)
**partial** — done (2026-11-12): `core/inference/`: `priors.py` (Uniform, LogUniform, Gaussian, TruncatedGaussian,
Fixed, Derived; logpdf, sample, unit-cube transform, description); `problem.py` (named parameters with prior, start,
scale; fixed ones passed to the likelihood; vectorised likelihoods evaluate whole sets of points); `diagnostics.py`
(rank-normalised split-R̂ with the folded version, bulk and tail ESS with Geyer's monotone sequence, EXOFAST's
burn-in); `mcmc.py` (DE-MC in two halves with snooker moves, γ = 1 every tenth generation, a thread pool for
likelihoods that are not vectorised, the stopping rule R̂ < 1.01 and ESS > 1000 checked at growing intervals on
chains thinned to ≤ 1000 draws, max steps / seconds, checkpoints that resume to the identical chain; chains start
spread by the parameters' scales — a tight start next to the truth passed its own cluster off as posterior and gave
73 % coverage); `results.py` (Posterior: summary with 68 / 95 % intervals and mode, derived quantities, correlation,
rounding to the error's digits, NPZ storage). Tests: the 20-dimensional correlated Gaussian (covariance within 3 %,
means within 4 Monte Carlo errors — at ESS 1000 a mean is itself good only to 3 % of σ), the banana, coverage 62–74 %
over 300 intervals, the resumed chain identical. Also done: `optimise.py` (bounds from the priors, differential
evolution from a Sobol start polished by restarted Nelder–Mead; `modes` from scattered starts, each separate
maximum reported with its log-probability); parallel tempering in `mcmc.run` (temperatures, t_max; swaps between
neighbours; cold chains kept): a 30 / 70 % mixture of two modes 8.5 σ apart is weighed within 10 %, where the
untempered chains stay in the mode they start in. Left: the emcee alternative, nested sampling, ECSV / FITS export, the interface kit (item 7) and the migration of
models/fit.py and timeseries/oc_models.py (item 8); the speed acceptance (item 4).
- **Read first:** ter Braak 2006 (Stat. Comput. 16, 239: DE-MC) and ter Braak & Vrugt 2008 (snooker update);
  Goodman & Weare 2010 and Foreman-Mackey et al. 2013 (emcee); Eastman et al. 2013 §2 and 2019 (EXOFAST's
  DE-MC with parallel tempering, its stopping rule: Gelman–Rubin < 1.01 and independent draws > 1000); Vehtari et
  al. 2021 (rank-normalised split-R̂ and effective sample size); Hogg & Foreman-Mackey 2018; Speagle 2020
  (dynesty); Higson et al. 2019 (dynamic nested sampling).
- **Ours now:** emcee runs written separately in `models/fit.py` and `timeseries/oc_models.py` with fixed step
  counts and no convergence test.
- **Build:**
  1. `core/inference/priors.py`: `Uniform(lo, hi)`, `Gaussian(mu, sigma)`, `TruncatedGaussian`, `LogUniform`,
     `Fixed`, `Derived` (a prior on a function of parameters, e.g. on ρ★ or on e through a Beta distribution —
     Kipping 2013b), each with `logpdf`, `sample`, `transform` from the unit cube (for nested sampling) and a
     one-line description for the interface.
  2. `core/inference/problem.py`: `Problem(parameters, log_likelihood, derived=…)`; parameters carry names, plain
     labels, units, start values, scales; the log-probability function is picklable and thread-safe (the native
     kernels release the GIL).
  3. `core/inference/optimise.py`: bounded differential evolution → Levenberg–Marquardt / Nelder–Mead polish; the
     start for every sampler; multi-start to detect several modes (reported, not hidden).
  4. `core/inference/mcmc.py`: (a) DE-MC with snooker moves, 2 × n_dim chains at least, optional parallel
     tempering (n temperatures) for multi-modal problems; (b) the affine-invariant ensemble (emcee) as an
     alternative; evaluation of the chains' proposals in a thread pool; checkpoints every N steps (a run can be
     paused, resumed after a restart, and extended); **stopping rule**: rank-normalised split-R̂ < 1.01 for every
     parameter **and** bulk and tail effective sample sizes > 1000 (settable), checked every few hundred steps,
     with a maximum time / steps after which the run stops and is marked *not converged*; burn-in removed
     automatically (the point where every chain has passed the median log-probability of the final quarter, as
     EXOFAST) and shown on the trace plot; thinning by the autocorrelation time only for storage.
  5. `core/inference/nested.py` (P2 within this step: build after the MCMC parts): dynesty (MIT; dependency and
     wheels checked) for evidence and multi-modal posteriors; model comparison table (ln Z differences with the
     usual interpretation scale).
  6. `core/inference/results.py`: `Posterior` (samples, log-probabilities, derived samples, diagnostics): medians
     and 68 % / 95 % intervals, mode, correlation matrix, asymmetric errors formatted to the right digits,
     storage as compressed NPZ in the project, export as ECSV / FITS table; `summary_table()`.
  7. Interface kit pieces (`ui/kit/inference.py`): the run panel (progress, live R̂ and effective sample size per
     parameter as small bars turning green, elapsed and estimated time, Pause / Resume / Stop), trace plots, corner
     plot (our own drawing through `PlotView` and publish: 1-D histograms with median and interval lines, 2-D
     contours at 39 % and 86 %; any subset of parameters), a prior editor row for parameter tables.
  8. Migration: the O−C and Models code use this engine (their old emcee calls removed); tests keep the old
     results within statistical tolerance.
- **Accept:**
  1. Known targets: a 20-dimensional correlated Gaussian (means and covariance recovered within 3 % with the
     default stopping rule), the Rosenbrock "banana", a bimodal Gaussian mixture (both modes with the right weights
     within 10 % using tempering or nested sampling) — tests with fixed seeds.
  2. Coverage: for a linear model with Gaussian noise the 68 % intervals contain the truth in 64–72 % of 500
     realisations.
  3. A run stopped and resumed gives the same chain as an uninterrupted one (same seed).
  4. Overhead of the engine itself: 10^5 calls of a model that takes 1 ms finish in < 35 s on 4 threads (the model
     alone would take 25 s); 10^5 calls of a 20 µs model in < 6 s.
- **Files:** `core/inference/*.py`, `ui/kit/inference.py`, callers in `timeseries/`, `models/`, tests.

### EXO-W. The Exoplanets window  (P1)
**open**
- `plans/interface.md` UI-16.7: stages Data, Star, Planets, Model, Fit, Uncertainty, Results. Three ways in,
  offered by the empty state: **One transit** (a light curve of tonight → PHO-26's fit in this window's fuller
  form), **Ephemeris** (many mid-times → OC-13), **Global fit** (transits + velocities + star).
- **Extra accept:** the Qatar-1 night: open the light curve → name resolved → archive values filled as starts and
  priors → least-squares fit → MCMC with the convergence light → results and report: **seven clicks**, no number
  typed; every prior shows its source ("NASA Exoplanet Archive, Bonomo et al. 2017").
- **Depends on:** ARC-4, ARC-5, ARC-6, ARC-8, UI-1 … UI-4, EXO-1 … EXO-5.
- **Files:** `ui/exoplanets/{window,controller,state,menus}.py`, `ui/exoplanets/panels/{data,star,planets,model,fit,uncertainty,results}.py`, `ui/shell/area_registry.py` (new area `exoplanets`), `tests/ui/walks/exoplanets.py`, guide 09b (new chapter) in four languages

### EXO-6. The host star  (P1)
**partial** — done (2026-11-12): `stars/relations.py`: Torres et al. 2010's calibration of M and R from Teff,
log g and [Fe/H] (coefficients read from the paper's Table 1, its scatter added to the inputs' errors); the Sun
gives their 1.051 M☉ and 1.018 R☉. Left: catalogues, the SED, the MIST tracks (data pack), the star object and
its stage.
- **Read first:** Eastman et al. 2019 §4 (the star in the global model: SED, parallax, MIST, the error floors on
  broadband photometry and on the models: Teff 2 %, bolometric flux 2 %, as Tayar et al. 2022 argue); Stassun &
  Torres 2016 and Stassun et al. 2018 (SED fitting, Gaia parallax zero point: Lindegren et al. 2021); Dotter 2016
  and Choi et al. 2016 (MIST: equivalent evolutionary points, the public tracks and bolometric-correction tables);
  Torres et al. 2010 (empirical M, R relations); Green et al. 2019 and Schlafly & Finkbeiner 2011 (reddening maps
  as upper limits); `mkticsed.pro` (which catalogues and error floors EXOFAST uses).
- **Build:**
  1. `stars/catalogues.py`: by name / coordinates: Gaia DR3 (parallax with the zero-point correction, G BP RP,
     RUWE, the astrophysical parameters when present), TIC-8, 2MASS, AllWISE, APASS, Tycho-2, SDSS / Pan-STARRS /
     SkyMapper, GALEX — through `services/` (ARC-14); each magnitude with its catalogue error and the systematic
     floor EXOFAST applies (`mkticsed.pro`, read 2026-11-10: Gaia G, BP, RP 0.02 mag; 2MASS J, H, Ks 0.02; WISE W1–W3
     0.03, W4 0.10; Strömgren 0.01–0.02; a 30 µas parallax floor is present but commented out); neighbours within 10″ from Gaia
     listed with their flux ratios (contamination warning for the SED and for dilution).
  2. `stars/sed.py`: model broadband fluxes from the bolometric-correction tables of the MIST pack (functions of
     Teff, log g, [Fe/H], A_V) or from MOD-6's atmosphere passband tables; fit of Teff, R★ (through the angular
     diameter and the parallax), A_V (uniform prior up to the line-of-sight maximum from a dust map service, or
     typed), [Fe/H] prior from spectroscopy; an error-scaling term for the photometry; outputs F_bol, L★, R★ with
     errors; the SED plot (catalogue points with band widths, model points, the model spectrum behind them,
     residuals).
  3. `stars/isochrones.py`: the MIST tracks as a data pack (ARC-20; citation and version in the manifest);
     interpolation in (initial mass, [Fe/H], EEP) → Teff, R, log g, L, age, with EXOFAST's device of comparing the
     model's Teff and R with the fit's at a penalty (so that the track is a constraint, not a hard relation); the
     age prior flat up to the age of the Universe; alternatively the Torres relations (with their intrinsic
     scatter); the H–R / Kiel diagram with the star's posterior and the track.
  4. `stars/star.py`: one object combining what is known: spectroscopic Teff, log g, [Fe/H] (typed or from SPE-17),
     the SED, the parallax, the transit's ρ★, the tracks → M★, R★, ρ★, L★, age with a posterior (EXO-5); usable
     alone ("Star" tool in other windows: MOD-15, SPE-17's cross-check table).
  5. The Star stage: "Fetch" fills the table of inputs with sources; ticks choose which constraints enter; a
     consistency line ("the light curve's stellar density 1.9 ± 0.3 g cm⁻³ against 1.4 ± 0.1 from the star: 1.6σ;
     with e = 0 this suggests …").
- **Accept:** for 15 well-characterised hosts (interferometric radii and / or asteroseismic masses in the
  literature; recorded catalogue responses): R★ within 4 % and M★ within 7 % (median absolute differences) and
  Teff within 100 K; the Sun's absolute magnitudes placed at 10 pc give 1.00 ± 0.03 R☉ and 5772 ± 60 K; HAT-P-3's
  M★ and R★ within 1σ of EXOFASTv2's published values; one star's fit < 60 s.
- **Files:** `stars/{catalogues,sed,isochrones,star}.py`, data-pack entries, UI star panel, tests, guide 09.

### EXO-7. The global fit  (P1)
**open**
- **Read first:** `exofast_chi2v2.pro` (how the likelihood is assembled: every data set's contribution, the
  penalties, the bounds — write the list under this step); Eastman et al. 2019 §5–6 (multi-band, multi-instrument
  conventions; error scaling per data set; what is fitted per transit).
- **Build:** `exoplanets/system.py`: `Star` (EXO-6), `Planet`s, data sets: `TransitLC` (a night / instrument / band;
  its own baseline F0, additive and multiplicative detrend columns chosen in Photometry or here, added-variance or
  error-scale term, exposure time), `RVSet` (instrument: γ, jitter), `MidTimes` (literature transit times as data),
  `OccultationLC`; per band: limb darkening (EXO-3), dilution, occultation depth; per planet: the sampling set,
  optional TTVs (one free mid-time per transit, the linear ephemeris then fitted to them), optional depth
  variations; the likelihood = Σ data-set likelihoods + star constraints + priors; linear nuisance parameters
  solved analytically where exact; a least-squares / DE start then EXO-5's MCMC; model selection helpers:
  circular against eccentric (BIC, evidence when nested sampling ran, and the Lucy–Sweeney style check on e), trend
  or not, another planet or not.
- **Accept:**
  1. HAT-P-3 b from EXOFASTv2's example files: every fitted and derived parameter within 1σ of the published
     EXOFASTv2 medians and our interval widths within ± 25 % of theirs.
  2. Synthetic system (two planets, three transits in two bands with airmass trends, 30 velocities from two
     instruments): all parameters within 2σ in 90 % of 50 realisations; coverage of the 68 % intervals 60–76 %.
  3. Convergence of the HAT-P-3 fit in < 15 min on the reference machine (EXOFASTv2's own example takes about 45
     min in IDL by its README).
- **Depends on:** EXO-1 … EXO-6.
- **Files:** `exoplanets/{system,likelihood,fit}.py`, step `exoplanets.global_fit`, `tests/test_exo_global.py`, `tests/validation/test_exofast_hat3.py`

### EXO-8. Rossiter–McLaughlin and occultation details  (P2)
**open**
- **Read first:** Ohta, Taruya & Suto 2005; Hirano et al. 2011 (the anomaly as measured by cross-correlation);
  Triaud 2018 (review); Albrecht et al. 2022.
- **Build:** the RM anomaly in the velocity model (λ, v sin i, with the stellar line broadening terms of Hirano's
  formula), fitted with the transit; secondary eclipses and phase curves of EXO-1 in the global fit with thermal
  and reflected parts per band, the brightness temperature and the geometric-albedo limit as derived values.
- **Accept:** a synthetic aligned / misaligned hot Jupiter: λ within 1.5σ; a published RM data set's λ reproduced
  within its error.
- **Files:** `exoplanets/rm.py`, `occult/model.py` (occultation and phase terms), `tests/test_exo_rm.py`

### EXO-9. One transit, and many transits of one planet  (P1)
**partial** — done (2026-11-12), the engine: `exoplanets/multi_night.py`: nights fitted together with a shared planet
(k, a/R★, b) and a polynomial baseline per night solved linearly inside every evaluation, on a linear ephemeris or
with a free mid-time per night; started at several impact parameters (the b–a/R★ valley); times as parameters
relative to the first mid-time (absolute JDs made the finite-difference steps 0.04 d and the fit stopped anywhere).
Tests: three nights with different trends give T0 and P within 3σ and k with an error √3 smaller than one night's.
Left: the depth against wavelength, the practice nights through the interface, the One-transit way in.
- **Build:** the "One transit" way in: the same model and table as PHO-26 with the star and archive stages of this
  window; "Many transits": a list of nights (our own light-curve files, PHO-48) fitted together with a shared
  planet and per-night baselines / detrending, free mid-times on request → the O−C diagram (OC-13) with the
  refined ephemeris, its covariance and the uncertainty of the next transits; depth against wavelength when the
  nights are in different bands (a table and plot; a constant line's χ²).
- **Accept:** three synthetic nights with different trends give the ephemeris within 1σ and Rp/R★ better than any
  single night by the expected √N; the Qatar-1 + HAT-P-32 practice nights run through the stages without typing a
  number.
- **Files:** `exoplanets/{single,multi_night}.py`, `photometry/transitfit.py` (shared model assembly), UI data panel, `tests/test_exo_nights.py`

### EXO-10. Priors and context from the archives  (P1)
**open**
- **Ours now:** `planning/ephemerides.exoplanet` (period and epoch from the Exoplanet Archive composite table).
- **Read first:** the NASA Exoplanet Archive TAP documentation (tables `ps`, `pscomppars`: default-parameter-set
  flags, references per row); ExoFOP-TESS (TOI parameters, download formats); the ExoClock ephemeris catalogue's
  access; exoplanet.eu's VO table.
- **Build:** `services/{exoplanet_archive,exofop,exoclock}.py` (ARC-14, cached): for a planet / TOI / TIC name: the
  parameter sets with their references (not only the composite row), the user picks a set or the composite; values
  fill starts and, when ticked, Gaussian priors (P and Tc priors off by default for a fit that should measure
  them; stellar priors on); the predicted mid-time for the night with its propagated uncertainty; previous
  mid-times from the literature tables where the archive has them.
- **Accept:** recorded responses for ten planets parse into complete starting sets; offline use from the cache; a
  planet with several references shows them all.
- **Files:** `services/{exoplanet_archive,exofop,exoclock}.py`, `exoplanets/priors_from_archive.py`, `tests/data/services/…`, `tests/test_exo_archive.py`

### EXO-11. Candidates: search and vetting  (P2)
**open**
- **Read first:** Thompson et al. 2018 (ApJS 235, 38: the Kepler DR25 Robovetter tests); Twicken et al. 2018 (data
  validation: odd / even, secondary, centroid, ghost tests); Eisner et al. 2020 (LATTE); Kostov et al. 2019 (DAVE);
  Giacalone et al. 2021 (TRICERATOPS: probabilities of false-positive scenarios, as background); the TFOP SG1
  sub-group's classification of follow-up results.
- **Build:** from a mission light curve (PER-7) or pixel file (PHO-32): search (TLS / BLS, PER-3) → for each
  signal a **vetting sheet** (one page): the phased transit with the model; odd and even transits overlaid with
  their depth difference in σ; the secondary-eclipse window at phase 0.5 (and at the phase an eccentric orbit
  allows) with its depth limit; the out-of-transit curve at the orbital period (ellipsoidal / heating: "SWEET"
  sinusoid test); transit shape (V-shape parameter b + k; duration against ρ★ expectation); individual transits in
  a grid (are they all there? momentum dumps marked); depth against aperture size; in- minus out-of-transit
  difference image and centroid shift (PHO-32); the Gaia neighbours within the aperture with the depth each would
  need (PHO-23's arithmetic) and RUWE; ephemeris matches with known eclipsing binaries and variables nearby (VSX,
  TESS EB catalogue); a summary of red / amber / green marks — a diagnosis aid, never a verdict.
- **Accept:** on the known planet: all green; on the blended eclipsing binary: at least the centroid or neighbour
  test red; on a synthetic EB at twice the period: odd / even red.
- **Files:** `exoplanets/vetting.py`, `ui/exoplanets/panels/vetting.py`, `tests/test_exo_vetting.py`

### EXO-12. Results for a paper  (P1)
**open**
- **Build:** the parameter table in EXOFAST's familiar layout (stellar, planetary, wavelength, telescope and
  transit parameters; symbol, description with units, median and 68 % interval) as LaTeX (AASTeX and A&A), ECSV and
  Markdown, with the right number of digits; a prior table (what was assumed, with sources); figures through
  publish: each transit (data, model, residuals; detrended), the phased multi-band transit, velocities in time and
  phase with residuals, SED, H–R track, TTV plot, corner plots (fitted; derived); the posterior as a machine-
  readable file; the ephemeris with the uncertainty of future mid-times; the files for ExoClock / AAVSO / TFOP
  through PHO-27; the methods text (ARC-11) listing every model ingredient, prior, the sampler and its convergence
  numbers, and the catalogues used.
- **Accept:** the HAT-P-3 table compiles and matches the session's numbers; every figure passes the publish
  checks; the posterior file reloads into a `Posterior` identical to the saved one.
- **Files:** `exoplanets/report.py`, `resources/methods/exoplanets_*.txt`, `tests/test_exo_report.py`

### EXO-13. Noise that is not white  (P2)
**partial** — done (2026-11-12), the simple treatments: `exoplanets/noise.py`: the β factor of the time-averaging
method (median over bin sizes, never below 1; ≈ 1 on white noise, > 1.5 on a red component) and the error scaling to
χ²ᵣ = 1. Left: the Gaussian processes (celerite2 after the licence and wheel check), the comparison table, the
coverage test.
- **Read first:** Foreman-Mackey et al. 2017 (celerite); Pont et al. 2006; Carter & Winn 2009 (wavelet
  likelihood); Rajpaul et al. 2015 (GPs for activity in velocities).
- **Build:** optional Gaussian-process noise per light curve (celerite2, MIT: Matérn-3/2 and damped-oscillator
  kernels) and for velocities (quasi-periodic, with the rotation period from PER-15 as a prior), their
  hyper-parameters sampled with the rest; the simpler alternatives kept (error scaling, β factor, PHO-34); a
  comparison table of the planet's parameters under each noise treatment.
- **Accept:** synthetic transits with red noise: white-noise fits under-cover (asserted), GP fits cover at the
  nominal rate.
- **Files:** `exoplanets/noise.py`, `pyproject.toml` (celerite2, after the licence and wheel check), `tests/test_exo_gp.py`

### EXO-14. Observing planets: can I see it, and when  (P2)
**partial** — done (2026-11-12): `exoplanets/observability.py`: `scintillation` (Young 1967), `precision` (the CCD
equation of planning.exposure, scintillation, the comparisons' share), `detectability` (depth over σ √(1/n_in +
1/n_out)), `rank` (detectable first, then detectability × the ephemeris drift; transit_timing.drift gives the drift,
planning.visibility.events the transits of a night). Left: the equipment profile, the recommended exposure and
filter, the ExoClock priority, the Qatar-1 night check, the delivery to Planning.
- **Build:** for the user's equipment profile (ARC-16) and a planet: predicted photometric precision per exposure
  and per transit (the noise budget of PHO-34 with the star's magnitude), the transit's detectability in σ, the
  recommended exposure and filter; the list of tonight's / this month's observable transits ranked by
  detectability and by the value of a new timing (ExoClock priority, ephemeris drift, EXO-12's uncertainty) —
  delivered to Planning (PLN-6).
- **Accept:** predictions for the Qatar-1 night agree with the achieved scatter within 30 %.
- **Files:** `exoplanets/observability.py`, `planning/exposure.py`, `tests/test_exo_observability.py`

### EXO-15. Dynamics of timing variations  (P3)
**open**
- **Read first:** Agol et al. 2005; Holman & Murray 2005; Lithwick, Xie & Wu 2012 (analytic near-resonant TTVs);
  Deck et al. 2014 (TTVFast, as background).
- **Build:** the Lithwick analytic formulae for a near-resonant pair fitted to two planets' mid-times (masses and
  free eccentricities with their degeneracy shown); a note in the guide on full N-body fits and which external
  tools do them.
- **Accept:** a published near-resonant pair's TTV period and amplitudes reproduced within errors.
- **Files:** `exoplanets/ttv.py`, `tests/test_exo_ttv.py`

### EXO-16. Validation  (P1)
**open**
- **Build:** `tests/validation/test_exoplanets_*.py`: EXO-1 against batman curves; EXO-7 against EXOFASTv2's
  published example results; the one-night fits against the AstroImageJ and ExoClock results for the same nights
  where public; EXO-6 against benchmark hosts; a table of all these in the guide's methods chapter.
- **Accept:** `pytest -m validation` covers each engine with a real or reference case.
- **Files:** `tests/validation/test_exoplanets_*.py`, `tests/validation/scripts/batman/`, `tests/validation/data/exoplanets/`

### EXO-17. Planets in context  (P2)
**open**
- **Build:** mass–radius diagram with the fitted planet's posterior, the archive's planets with good measurements
  and composition curves (tables of Zeng et al. 2019, cited); period–radius and insolation–radius diagrams; all
  data from the cached archive table.
- **Accept:** the plots draw offline from the cache; the planet's point equals the result table.
- **Files:** `exoplanets/context.py`, `resources/data/mass_radius_curves.ecsv` (with its citation), `ui/exoplanets/panels/context.py`, tests

### EXO-18. Doppler tomography and transmission spectra  (P3)
**open**
- **Build:** listed for completeness of the comparison with EXOFASTv2: line-profile tomography of a transit (needs
  SPE-13's mean profiles as a time series) and depth-against-wavelength fits with a flat / sloped model; built
  only when a data set calls for them.
- **Files:** `exoplanets/{tomography,transmission}.py` (only when built)

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(nothing yet)
