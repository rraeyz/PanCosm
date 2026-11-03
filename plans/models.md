# Binary-star models: plan

Read `PLAN.md` first, all of it, then `plans/architecture.md` "Conventions" and "Definition of done", then
`plans/interface.md` (rules, kit, anatomy, UI-16.6).

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

Physical models of eclipsing and spectroscopic binaries fitted to light curves in several bands and to radial
velocities together: detached, semi-detached, contact (W UMa) and eccentric systems; reflection, gravity darkening,
limb darkening from tables, spots, third light, third body; uncertainties; absolute dimensions and distance; and
the figures and tables of a paper. Visual-binary orbits live here too.

**Goal:** the physics of Wilson–Devinney and PHOEBE with our own engine (nothing GPL bundled), faster than both,
with guidance none of them has: starting values estimated from the data, a parameter table in plain words, a view
of the stars at every phase, a q-search in one click, and honest uncertainties. Today the window says "export and
model in PHOEBE or WD" — that sentence must disappear.

## What the reference programs do

Read (never copied; PHOEBE and ellc are GPL-3, PyWD2015 is an MIT interface over Wilson's Fortran program): Wilson &
Devinney 1971 (ApJ 166, 605); Wilson 1979 (ApJ 234, 1054: eccentric orbits, asynchronous rotation, the generalised
potential); Wilson 1990 (ApJ 356, 613: detailed reflection); Wilson 2008 (ApJ 672, 575: direct distance), Wilson &
Van Hamme 2014 (ApJ 780, 151: ephemeris parameters, third body) and the WD program documentation ("Computing Binary
Star Observables"); PyWD2015 (Güzel & Özdarcan 2020, CoSka 50, 535; its windows: main / system / surface / third
body, LC and DC, spots, eclipse timings, O−C, star positions, synthetic curve, dimensions, conjunction, line
profile, history); Prša & Zwitter 2005 (PHOEBE 1); Prša et al. 2016 (ApJS 227, 29: PHOEBE 2 — triangulated mesh,
passband intensities, eclipse algorithm); Horvat et al. 2018 (ApJS 237, 26: Roche geometry and misalignment), 2019
(irradiation); Jones et al. 2020 (ApJS 247, 63: boosting, extinction); Conroy et al. 2020 (ApJS 250, 34: the
inverse problem: estimators, optimisers, samplers); JKTEBOP (Southworth 2013 and its documentation: tasks 1–9,
limb-darkening laws, numerical integration, residual permutation, Monte Carlo); EBOP (Popper & Etzel 1981; Nelson
& Davis 1972); ellc (Maxted 2016, A&A 591, A111); Binary Maker 3's manual; Kallrath & Milone, *Eclipsing Binary
Stars: Modeling and Analysis*; Hilditch, *An Introduction to Close Binary Stars*.

| Topic | Wilson–Devinney (PyWD2015) | PHOEBE 2 | JKTEBOP | ellc | Ours now |
| --- | --- | --- | --- | --- | --- |
| Shapes | Roche equipotentials; modes: detached, semi-detached, overcontact, double contact | Roche, rotating star, sphere; contact envelopes; misaligned spins | biaxial ellipsoids | spheres, ellipsoids, Roche (volume-matched) | spheres |
| Surface grid | latitude rows with longitude points (N1, N2), fine grids near the horizon | triangulated mesh (marching), re-meshed in eccentric orbits | concentric rings | Gauss–Legendre on the disc | 1-D radial integral of the eclipsed disc |
| Intensities | blackbody or Kurucz atmospheres (per-band tables, Van Hamme & Wilson 2003) | passband tables from Castelli–Kurucz, PHOENIX; blackbody; extinction | surface-brightness ratio | surface-brightness ratio | surface-brightness ratio J |
| Limb darkening | linear, logarithmic, square-root; coefficients from Van Hamme 1993 tables, per surface element | interpolated from the atmosphere tables or manual (linear, log, sqrt, quadratic, power) | linear, quadratic, log, sqrt, cubic, power-2, four-parameter | many laws, also per-element | quadratic, typed |
| Gravity darkening | exponent g per star | β per star | coefficient per star | coefficient per star | none |
| Reflection | simple and detailed, multiple reflections, bolometric albedo | Wilson and Horvat irradiation, redistribution | simple geometric term | simple and "heat" terms | none |
| Spots | circular: latitude, longitude, radius, temperature factor; drifting and ageing spots | circular spots; Gaussian-process noise | — | circular spots | none |
| Orbit | e, ω, dω/dt, dP/dt, phase shift, third-body light-time | the same plus hierarchical orbits | e cos ω, e sin ω | e, ω, light-time, apsidal motion | e cos ω, e sin ω |
| Data fitted together | several light curves, both velocity curves, eclipse timings | light curves, velocities, line profiles, astrometric orbits | one light curve with velocities and minima times as extra data | light and velocity curves | one light curve; velocities separately for absolute dimensions |
| Velocities | Keplerian + proximity and eclipse (Rossiter) effects | flux-weighted over the mesh | Keplerian | flux-weighted, Rossiter | Keplerian (`spectroscopy/orbit.py`) |
| Fitting | differential corrections (least squares with Marquardt damping), subsets of parameters, formal errors | estimators (geometry, EBAI), optimisers (Nelder–Mead, differential evolution, differential corrections…), samplers (emcee, dynesty), priors and constraints | Levenberg–Marquardt; Monte Carlo; residual permutation | user's own (emcee) | least squares; emcee around the solution |
| Extras | conjunction times, absolute dimensions, distance, line profiles, star-position plots | meshes plotted and animated, many passbands | light-ratio and third-light constraints from spectroscopy | Doppler boosting, exposure-time integration | PHOEBE and WD starting files; Roche warning for close systems |

## What we already have (do not redo)

- `models/eb.py` (spheres, quadratic limb darkening, eccentric orbit, third light), `fit.py` (JKTEBOP-style
  parameters r1 + r2, k, i, J, e cos ω, e sin ω, l3, T0, P; least squares; absolute dimensions by Monte Carlo;
  `roche_check`; emcee), `data.py` (reading curves; PHOEBE export), `wd.py` (WD files; pole potentials),
  `visual.py` (visual orbit, Thiele–Innes, grid in P, T, e), `transit_report.py`; steps `models.eb_fit`,
  `models.visual_orbit`; window "Models" with tabs Eclipsing binary / transit and Visual binary orbit.
- Checked: i = 86.46° against 86.5° on synthetic data; η CrB visual orbit against ORB6.

## Decisions

- **Our own Roche engine**, written from the papers, in NumPy first (the reference) and as a native kernel (ARC-9)
  for speed; validated against PHOEBE 2, the WD program and ellc run **beside** ours as external programs.
- Conventions (binding, stated in every table): star 1 is the star eclipsed at phase 0 (primary minimum, the deeper
  one by default); q = M₂ / M₁; lengths in units of the semi-major axis a; inclination 0–90° (or to 180° only with
  astrometry); ω is the argument of periastron of star 1's orbit; potentials in Wilson's convention (below); phase
  0.25 follows phase 0 in time; third light l₃ is its fraction of the **total** light at phase 0.25 in each band.
- Two model levels in one window: **Simple** (spheres or biaxial ellipsoids: fast, for well-detached systems and
  transits) and **Roche**; the program suggests the level from `roche_check` and the light-curve shape, and warns
  when Simple is used beyond its range.
- Parameters have plain names first ("Surface potential of star 1", "Mass ratio"), with the Wilson–Devinney and
  PHOEBE symbols in a column for experts.

## The physics, written down (the specification the engine must meet)

Coordinates: origin at the centre of star 1; x towards star 2; z along the orbital angular momentum; instantaneous
separation D in units of a (D = 1 for circular orbits). For a surface point of star 1 at distance r in the
direction (λ, μ, ν) = (sin θ cos φ, sin θ sin φ, cos θ):

```
Ω(r, θ, φ) = 1/r + q [ (D² + r² − 2 r λ D)^(−1/2) − r λ / D² ] + ½ F² (1 + q) r² (1 − ν²)
```

(Wilson 1979 eq. 1; F = rotation rate / orbital rate). Star 2's surface is computed in its own frame with q′ = 1/q
and reported in the same convention: Ω₂ = q Ω′ + (1 − q)/2.

- **Surface:** r(θ, φ) from Ω = Ω₀ by Newton iteration from the pole outward; normal n = −∇Ω / |∇Ω|; local gravity
  g ∝ |∇Ω|; area element dS = r² sin θ dθ dφ / (n · r̂).
- **Critical surfaces:** inner (through L1) and outer (through L2) potentials by solving ∂Ω/∂x = 0 on the x axis;
  fill-out of a contact system f = (Ω_in − Ω) / (Ω_in − Ω_out) ∈ [0, 1]; detached: Ω > Ω_in for both;
  semi-detached: Ω = Ω_in for the filling star.
- **Eccentric orbits:** the star's volume is conserved around the orbit; Ω at each phase is solved for that volume
  at the instantaneous D (Wilson 1979).
- **Temperature:** T_local = T_pole (g / g_pole)^(β/4) with the bolometric gravity-darkening exponent β (1 for
  radiative envelopes, von Zeipel 1924; 0.32 for convective, Lucy 1967; any value typed; Claret's tabulated values
  offered). The star's stated T_eff is the flux-weighted mean over its surface (T_mean⁴ = Σ T⁴ dS / Σ dS), from
  which T_pole follows.
- **Reflection:** each element receives bolometric flux from every element of the companion that sees it; its
  temperature rises as T′⁴ = T⁴ + A F_irr / σ with bolometric albedo A (1 radiative; 0.5 convective, Ruciński 1969);
  iterated between the stars n times (Wilson 1990). A fast "point source" version for wide systems.
- **Emergent intensity:** I(band, T, log g, [M/H], cos γ) = I_normal(band, T, log g, [M/H]) × ld(cos γ), with
  I_normal from passband tables built from model atmospheres (MOD-6) or from the Planck function integrated over
  the passband; limb-darkening laws: linear, quadratic, square-root, logarithmic, power-2, four-parameter (Claret
  2000), coefficients per surface element interpolated from tables in (T, log g, [M/H]) or typed per star.
- **Visibility:** an element is seen when cos γ = n · ô > 0 (ô to the observer) and the line from it to the
  observer does not pass through either star. Flux in a band at a phase = Σ visible I cos γ dS over both stars,
  plus third light.
- **Spots:** circular regions (colatitude, longitude, angular radius, temperature factor); elements inside have
  T × factor; partially covered elements are subdivided.
- **Velocities:** each element's velocity = orbital velocity of its star's centre + rotation (F) ; the observed
  velocity of a star is the flux-weighted mean over its visible elements (proximity and Rossiter–McLaughlin
  effects), or the centre-of-mass value when asked.
- **Small terms** (each can be switched): light-travel time across the orbit; Doppler boosting (flux × [1 − B v_r /
  c], B from the passband and temperature; Loeb & Gaudi 2003, Jones et al. 2020); integration over the exposure.

## To ask the owner

- A light curve and velocity curves of a system the owner has already solved with WD / PyWD or PHOEBE, with that
  solution's parameters, as the first user-level comparison (MOD-21).

## For the owner to try

- After MOD-W and MOD-12: load one of your contact binaries, press "Estimate starting values", run the q-search and
  the fit; compare with your PyWD solution; say where the window was less clear than PyWD and where clearer.

## Data used

- To add (each with `SOURCE.md` and the published solution to reproduce): AI Phe (TESS light curve + published
  velocities; the benchmark of Maxted et al. 2020, MNRAS 498, 332, solved there with several codes); a detached
  eccentric system with apsidal motion; a semi-detached Algol with strong reflection; a totally eclipsing W UMa
  with a spectroscopic mass ratio (to test the photometric q-search); a spotted RS CVn-type system; Kepler / TESS
  curves of each morphology class. Reference model curves computed with PHOEBE 2 and with the WD program for a grid
  of 40 synthetic systems (MOD-9), stored as small CSV files with the scripts that made them.

## Steps

Order of work: the engine first — MOD-1, 2, 3, 4, 5, 6, 7, 8, 9 — which can start before the interface
foundation is finished (PLAN.md §5, lane b); then MOD-W and P1: 10, 11, 12, 13, 14, 15, 16, 19, 21; then P2: 17, 18,
20; P3: 22.

### MOD-1. Roche geometry  (P1)
**partial** — done (2026-11-12), items 1–2 and the volume radius in one module, `models/roche.py`: Wilson's modified
Kopal potential (q, D, F), L1–L3 by bracketed roots on the line of centres, Ω_in and Ω_out, fillout both ways, the
radius along any direction (the first crossing outward, never past L1 towards the companion; a potential below
Ω_out refused as an open surface), pole / side / back / point radii, the volume-equivalent radius (Gauss in cos θ ×
48 longitudes) and its inverse. Tests: L1 at ½ and Ω_in = 3.75 for q = 1, L2 and L3 mirror images; the Roche-lobe
volume radius within 1 % of Eggleton 1983 for q = 0.1–1; a small star a sphere to 1e-5; radii round-trip to 1e-9;
fillout 0 and 1 at the critical surfaces. Then `gradient` (∇Ω) and `surface` (rows of equal θ, longitudes ∝ sin θ; normals, gravity, area elements r² dω / (r̂·n̂), total area and volume): a small star's area and volume to 1e-4, a stretched star's volume equal to its volume radius, pole gravity above the nose's. Left: second derivatives,
contact envelopes split at the neck, eccentric volumes, Mochnacki's tables to 1e-5, error codes,
the 2 ms surface.
- **Read first:** Wilson 1979 (the potential and its derivatives; volume conservation); Kopal 1959 ch. 3;
  Mochnacki 1984 (ApJS 55, 551: tables of critical potentials and radii to test against); Horvat et al. 2018 §2–3
  (robust computation of critical points, areas and volumes); Kallrath & Milone ch. 3 and appendix on potentials.
- **Build:**
  1. `models/roche/potential.py`: `omega(r, lam, nu, q, D, F)`, its gradient in Cartesian and spherical forms,
     second derivatives needed by Newton solves; the star-2 transformation; vectorised over points.
  2. `critical.py`: L1, L2, L3 positions and Ω_in, Ω_out for any q > 0, D, F (bracketed root finding on the x
     axis; valid for F ≠ 1 as "limiting lobe"); `fillout(Ω, q)`, `omega_from_fillout(f, q)`; conversions between Ω
     and fractional radii: pole, side, back, point (towards the companion) and the volume-equivalent radius, both
     ways (root finding), for star 1 and star 2.
  3. `surface.py`: the surface grid: N latitude rows with the number of longitude points ∝ sin θ (equal-area-like,
     as WD's N1 / N2), hemispheric symmetry used; r by Newton with safeguards near L1 (the "nose"); normals,
     gravity, area elements; total area and volume (analytic checks on a sphere and against Mochnacki's tables);
     contact envelopes: each star's surface ends at the neck plane (x of minimum cross-section between the stars),
     elements beyond it belong to the other star.
  4. `volume.py`: `omega_for_volume(V, q, D, F)` for eccentric orbits.
  5. Errors as codes: `models.potential_below_critical` (a detached star set to overflow: says which star and the
     limit), `models.fillout_out_of_range`.
  6. Tests on closed forms: sphere limit q → 0; point radius → L1 distance as Ω → Ω_in; symmetry under q ↔ 1/q with
     star swap; Mochnacki's tabulated Ω_in, Ω_out, r_pole, r_side, r_back for q = 0.1 … 1 to 1e-5; volume and area
     converge as N grows (error ∝ N⁻² documented).
- **Accept:** all tests above; a surface of 40 × (up to 80) points per star in < 2 ms NumPy; radii conversions
  round-trip to 1e-10.
- **Files:** `models/roche/{potential,critical,surface,volume}.py`, `tests/test_roche_geometry.py`.

### MOD-2. Radiation: temperatures, intensities, limb darkening  (P1)
**partial** — done (2026-11-12), the parts without tables: the seven limb-darkening laws are `occult/laws.py`
(shared with the transits) with their disc integrals now in closed form; `models/radiation.py`: `temperatures`
(gravity darkening T = T_pole (g/g_pole)^β with T_pole set by the area-weighted mean of T⁴), `planck` and
`band_intensity` (the blackbody through a passband linear between its points). Tests: every law's disc flux equals
adaptive quadrature to 1e-10; the gravity-darkened mean T_eff equals the input to 0.01 K on a Roche surface; band
intensities equal adaptive quadrature to 1e-8 at 3500–20000 K. Left: local log g, coefficient tables (MOD-6),
atmosphere intensities with the blackbody ramp, bolometric terms for reflection, the passband registry.
- **Read first:** von Zeipel 1924; Lucy 1967; Claret & Bloemen 2011 (A&A 529, A75: limb- and gravity-darkening
  coefficients for many passbands; the laws' definitions), Claret 2017 (TESS), Claret 2000 (four-parameter law);
  Van Hamme 1993 (the WD tables' scheme); Prša et al. 2016 §5 (passband intensities and why per-element
  interpolation matters); Kipping 2013 (sampling of quadratic coefficients).
- **Build:**
  1. `models/roche/radiation.py`: local temperatures from β and the mean T_eff (the specification above); local
     log g in cgs when the absolute scale is known (a, masses) or from a typed polar log g otherwise.
  2. `limbdark.py`: the six laws as functions of cos γ with their disc integrals in closed form (for
     normalisation); `coefficients(band, law, T, log g, [M/H])` interpolated from the tables of MOD-6 with clear
     behaviour outside the grid (nearest edge + a warning code naming the star and the value).
  3. `intensity.py`: `normal_intensity(band, T, log g, [M/H], source = atmosphere | blackbody)`; blackbody
     integrated over the passband curve; automatic fallback from atmosphere to blackbody outside the grid, with a
     warning and continuity (the blackbody scaled to match at the grid edge, as WD's ramp).
  4. Bolometric quantities for reflection (σ T⁴, bolometric limb darkening).
  5. `models/passbands.py`: the registry of bands (name, curve, effective wavelength, tables present).
- **Accept:** disc-integrated flux of a sphere equals π R² I_normal × the law's closed-form factor to 1e-10 for
  each law; gravity-darkened mean T_eff equals the input to 0.01 K; coefficients equal the published table values
  at grid nodes and interpolate monotonically between them; band-integrated Planck matches numerical quadrature
  to 1e-8.
- **Files:** `models/roche/{radiation,limbdark,intensity}.py`, `models/passbands.py`, tests.
- **Depends on:** MOD-6 for the tables (blackbody and typed coefficients work without it).
- **Notes from the sources (architect, 2026-11-10):** PHOEBE 2.5 (2025–2026) added atmospheres for hot, compact stars (TMAP,
  Tremblay) and "support for extrapolating atmospheres and blending them into blackbody models" — the same problem
  Build 3 solves with the scaled-blackbody ramp; read its release notes for the blending rule before fixing ours.
  A hot-star table (sdB, white dwarfs: the owner's NY Vir is an sdB binary) is a later data pack of MOD-6.

### MOD-3. Visibility, eclipses and the light curve  (P1)
**partial** — done (2026-11-12): `models/roche_lc.py`: a star as a grid (a sphere, or the Roche surface of MOD-1 with
gravity-dependent intensity), the second star turned by 180° about z; the eclipse test of item 1 (circumscribed /
inscribed spheres, then the other star's potential along the sight line); the projected area of each cell from
its exact ∫u dω (r² M·v for a sphere, first order for Roche); horizon cells split k × k with their own μ; cells near
the other star's limb split k × k, each sub-point a ramp across its own width (no aliasing, smooth in the
parameters) weighted by its projected area; `flux(phases, i, star1, star2)`. Measured against the analytic
two-sphere eclipses (models.eb, quadratic law; total, annular and partial): 1.8–2.8e-5 of the flux with 60 rows
("normal"), 0.9–2.1e-5 with 90 ("fine") — the plan's 2e-5 / 5e-6 not yet; a Roche pair's ellipsoidal light at
i = 40°; no jumps in the flux over small steps of i. **Found:** equal sub-point weights biased the depth by 5e-4,
the midpoint rule of each cell's projected area by O(h²) — both gone. Left: the 5e-6 of "fine", contact
envelopes and the neck's self-eclipse, sub-point radii on Roche surfaces (the centre's now), the PHOEBE
comparison (MOD-9), normalisation options and magnitudes, outputs for the views.
- **Read first:** Wilson & Devinney 1971 §III and the WD documentation on horizon and eclipse computation
  (fractional-area corrections); Prša et al. 2016 §4 (horizon and eclipse detection on a mesh); Maxted 2016 §2
  (ellc's integration scheme and its accuracy tests); Hilditch ch. 5.
- **Build:**
  1. `models/roche/visibility.py`: observer direction ô(phase, i) in the rotating frame; cos γ per element; the
     eclipse test for an element of star A by star B: (a) quick decisions with B's inscribed sphere (r_min:
     certainly hidden if the sight line passes within it and B is in front) and circumscribed sphere (r_max:
     certainly clear if the sight line misses it); (b) for the elements in between, the exact test: the maximum of
     B's potential function along the sight line (a 1-D search with a few Newton steps from the point of closest
     approach to B's centre) compared with B's surface value — hidden when the line enters B's surface. Method
     binding unless the Accept cannot be met; then write the alternative under "Questions for the architect".
  2. Boundary smoothing: elements whose visibility differs from a neighbour's (horizon or eclipse limb) are
     subdivided (k × k, k from the accuracy setting) so that the light curve is smooth in the parameters (needed by
     derivative-based fits); self-eclipse of the neck region in contact systems handled by the same test with the
     star's own surface.
  3. `models/roche/lightcurve.py`: `flux(phases, params, band)` = Σ I cos γ dS over visible parts of both stars;
     geometry built once per model for circular synchronous orbits and reused for all phases and bands;
     normalisation options: by the model's flux at phase 0.25, by a fitted scale per data set, or in absolute
     units (for distance); third light as defined in Decisions; magnitudes as a view.
  4. Accuracy settings `coarse | normal | fine` (grid density and subdivision) with their measured errors in the
     docstring and in the interface tooltip.
  5. Outputs for the views (MOD-16): per-element visibility and intensity at a phase.
- **Accept:**
  1. Two spheres (q → potentials large, no distortion: F = 0 limit handled by a sphere switch): equal to the
     analytic limb-darkened eclipse (EXO-1's exact model for quadratic law; our current integral otherwise) within
     2e-5 (normal), 5e-6 (fine) of the total flux at every phase, for total, annular and partial eclipses.
  2. Against PHOEBE 2 reference curves (MOD-9's grid; blackbody and fixed linear limb darkening so that only
     geometry is compared): detached and semi-detached within 1e-4, contact within 3e-4 (normal); the differences
     shrink with `fine`.
  3. Smoothness: the numerical derivative of the flux with respect to i, Ω₁, q has no jumps larger than 1e-6 over
     1000 small steps (a test).
- **Files:** `models/roche/{visibility,lightcurve}.py`, tests.
- **Depends on:** MOD-1, MOD-2.

### MOD-4. Reflection  (P1)
**partial** — done (2026-11-12): `models/reflection.py`: `incident_point` (the companion as a point of its
luminosity, inverse square and projection), `incident_detailed` (element to element, both horizons, bolometric
limb darkening normalised to σT⁴), `heated` (T⁴ + A F/σ), on the grids of models.roche_lc. Tests: a far sphere
catches its solid angle of the light within 0.5 % by both; with A = 1 the re-radiated power equals the intercepted
one (by construction, checked); point and detailed within 2 % for r₁ + r₂ = 0.27. Left: iterations of mutual
heating, eclipse of the irradiating element by the receiver's own limb, eccentric scaling, the heated temperatures
in the light curve (MOD-2's intensities per element), the PHOEBE comparison.
- **Read first:** Wilson 1990 (the detailed reflection scheme and its convergence); Ruciński 1969; Horvat et al.
  2019 (irradiation frameworks; what Wilson's scheme assumes); Budaj 2011 (AJ 141, 59) for context.
- **Build:** `models/roche/reflection.py`: (a) `point` — the companion as a limb-darkened point-like source with
  the inverse-square law and the projection factor (fast, valid for separations ≫ radii); (b) `detailed` — the
  element-to-element sums with mutual visibility (the horizon of each element; eclipse of the irradiating element
  by the receiver's own limb), bolometric limb darkening, n iterations until the temperatures change by < 0.1 K or
  n_max; the heated temperatures feed MOD-2. Computed once per model (circular) or per phase (eccentric: scaled
  with D⁻² by default, exact on request). The interface says which was used.
- **Accept:** energy conservation: with A = 1 the bolometric luminosity re-radiated equals the intercepted one
  within 0.5 %; against PHOEBE 2 with Wilson irradiation for a hot + cool semi-detached pair (T = 20 000 K and
  5000 K): the out-of-eclipse reflection hump agrees within 3 % of its amplitude; `point` equals `detailed` within
  2 % of the effect for (r₁ + r₂) < 0.3.
- **Depends on:** MOD-3.
- **Files:** `models/roche/reflection.py`, `tests/test_roche_reflection.py`

### MOD-5. Orbit and timing terms  (P1)
**partial** — done (2026-11-12): `models/orbit_terms.py`: `conjunction_phases` (secondary minimum and periastron
after the primary, exact through the eccentric anomaly), `cycle` / `phase` on T = T0 + P E + ½ (dP/dE) E²,
`pseudo_synchronous` (Hut 1981 eq. 42), `integrate_exposure` (midpoint rule, n doubled until the answer is within
the tolerance), `boosting` (Loeb & Gaudi 2003). Tests: e = 0.3, ω = 60°: the minima and periastron phases equal
the conjunctions found by root-finding to 1e-9; the quadratic ephemeris round-trips to 1e-8 cycles; a 30-minute
exposure of a short eclipse within 1e-6 of a 2001-point sum. Left: dω/dt, the instantaneous separation with volume
conservation, asynchronous rotation in the Roche model, light time across the system and from a third body in
the model, the PHOEBE comparison.
- **Read first:** Wilson 1979; Wilson & Van Hamme 2014 (ephemeris with dP/dt and dω/dt; third-body light-time in
  the light-curve model); Kipping 2010 (MNRAS 408, 1758: binning of the model over the exposure); Loeb & Gaudi 2003.
- **Build:** `models/roche/orbit.py`: time → phase with P, T0 (of primary minimum **or** periastron — both
  supported, conversion exact), dP/dt, e, ω₀, dω/dt; the conjunction phases (primary, secondary), with the
  conversion between T0 conventions when e ≠ 0; instantaneous D and true anomaly (native Kepler solver); volume
  conservation through MOD-1; asynchronous rotation F₁, F₂ (pseudo-synchronous value offered: Hut 1981 eq. 42);
  light-travel-time correction between the stars; third-body light-time on the times (parameters as OC-6);
  exposure integration (n sub-samples per point from each data set's exposure time, default automatic: n so that
  the error < 1e-5); Doppler boosting.
- **Accept:** e = 0.3, ω = 60°: phases of minima and their separation equal the analytic conjunction solution to
  1e-9; volume constant around the orbit to 1e-8; against PHOEBE 2 for an eccentric detached system within 2e-4;
  30-minute integration of a 2-hour eclipse equals a brute-force fine sum to 1e-6.
- **Depends on:** MOD-3.
- **Files:** `models/roche/orbit.py`, `occult/orbit.py` (shared Kepler and conjunction code), `tests/test_roche_orbit.py`

### MOD-6. Passbands and atmosphere tables as a data pack  (P1)
**open**
- **Read first:** Castelli & Kurucz 2003 (the ATLAS9 grid: public); Husser et al. 2013 (PHOENIX, public, with
  specific intensities); the SVO Filter Profile Service (Rodrigo & Solano 2020) and its citation rules; Prša et al.
  2016 §5.2 (how passband tables are built); Claret's tables on VizieR.
- **Build:** `tools/build_passband_tables.py`: for each passband (Johnson U B V, Cousins R I, Bessell set, SDSS
  u′ g′ r′ i′ z′, Pan-STARRS g r i z y, Strömgren u v b y, Gaia G BP RP, Hipparcos, Tycho, 2MASS J H Ks, Kepler,
  TESS, CoRoT, CHEOPS, PLATO, clear / luminance with a typical CCD curve) integrate the model fluxes over the
  curve (photon-weighted for CCD bands, energy-weighted where the system is defined so) on the grid (T, log g,
  [M/H]) → `I_normal` tables after dividing by the law's disc factor; limb-darkening coefficient tables for each
  law fitted by us to the PHOENIX specific intensities where available, and Claret's tables fetched from VizieR by
  the data manager as an alternative source the user can choose (their citation shown); gravity-darkening y
  coefficients likewise; everything stored as compact binary tables with a manifest (sources, versions, citations,
  checksums) in a data pack (ARC-20). A small built-in subset (blackbody + linear coefficients for the main bands
  at solar metallicity) ships inside the program so that the model works before any download.
- **Accept:** our V-band linear coefficients agree with Claret & Bloemen's (same atmosphere family) within 0.02 for
  4000–10 000 K; passband fluxes reproduce published colours (B − V, V − I) of the model grid within 0.02 mag; the
  pack is < 150 MB and loads lazily (first use of a band < 0.2 s).
- **Files:** `tools/build_passband_tables.py`, `models/passbands.py`, `core/datapacks.py` entries, tests.

### MOD-7. Radial velocities from the same model  (P1)
**partial** — done (2026-11-12): `models/roche_lc.velocities`: flux-weighted radial velocities of both stars from
the light-curve grids (each visible element moving with its star about the barycentre and spinning at F times the
orbital rate; circular orbit; the observer's turn in the rotating frame fixed to the orbit's sense). Tests: out
of eclipse the mean velocity is the centre's Keplerian one to 1e-3 km/s; the Rossiter effect of a small dark body
on a synchronous star equals the first-order formula (the hidden light's velocity missing from the mean) within
0.1 % (3 % asked). Left: eccentric orbits, K from a, q, i, P, per-instrument offsets, the CCF note, the PHOEBE
comparison.
- **Read first:** Wilson & Sofia 1976 (proximity effects on velocities); Ohta, Taruya & Suto 2005 and Hirano et al.
  2011 (Rossiter–McLaughlin: what a CCF measures against a flux-weighted mean); the WD documentation on velocity
  curves.
- **Build:** `models/roche/velocity.py`: `rv(times, params, star, mode = centre | flux_weighted)`: K₁, K₂ from a,
  q, i, P, e (or fitted directly); γ and per-instrument offsets; flux-weighted velocities over visible elements in a
  chosen band (the spectrograph's); a note in the interface that a CCF does not measure exactly the flux-weighted
  mean (Hirano's correction offered for transits in EXO-8); the a sin i ↔ K relations and the physical scale (a in
  R☉) entering MOD-2's log g and MOD-15.
- **Accept:** Keplerian mode equals `spectroscopy/orbit.rv_model` to 1e-9 km/s; the Rossiter effect of a rotating
  star eclipsed by a small dark body equals the analytic first-order formula within 3 %; against PHOEBE 2
  flux-weighted velocities of a semi-detached pair within 0.5 km/s through the eclipses.
- **Depends on:** MOD-5.
- **Files:** `models/roche/velocity.py`, `tests/test_roche_velocity.py`

### MOD-8. Spots  (P1)
**partial** — done (2026-11-12): `models/spots.py`: up to 8 spots per star (colatitude, longitude from the line of
centres in the sense the orbit turns, angular radius, temperature factor); overlap by product (WD) or "the later
wins"; every element split into k × k sub-points so edges are shared smoothly; intensities scaled by I(T f) / I(T)
in the band (bolometric by default); longitudes move with F ≠ 1 and a drift per cycle. Tests: a 3° spot equals the
analytic small-spot curve within 0.8 % of its amplitude (limit 2 %); a cool spot gives a 0.02 mag difference of
the maxima of a contact system (q = 0.4, fillout 0.3) and a fit from 30° away recovers its longitude within 0.5°
and factor within 0.002. Contact stars now end at the plane through L1 (`roche.radius(neck=True)`); cells the
rays cross badly (the neck's rim, steep cells) are measured as 6 × 6 quadrilaterals on the surface, the neck plane
left dark: a contact envelope's projected area equals an independent pixel count within 1e-3. Left: the parameter
table flag for the drift (MOD-10); the guide picture.
- **Read first:** the WD spot parameters (latitude, longitude, radius, temperature factor); Eker 1994 and Budding
  1977 (analytic spot curves for tests); Prša et al. 2016 §3 (spots on meshes).
- **Build:** up to 8 circular spots per star: colatitude, longitude (0 towards the companion, increasing in the
  direction of orbital motion — stated in the tooltip with a picture in the guide), angular radius, temperature
  factor (< 1 cool, > 1 hot); overlap rule (the product of factors, as WD, selectable to "the later spot wins");
  elements cut by a spot's edge subdivided (smooth light curve as the spot moves across the limb); spots rotate
  with the star (F); optional linear drift in longitude per data set / season (P2 flag in the parameter table).
- **Accept:** a small spot on a slowly rotating sphere equals the analytic curve (Eker 1994) within 2 % of the
  spot amplitude; a contact system's O'Connell asymmetry of 0.02 mag is reproduced by one cool spot and recovered
  by a fit from a start 30° away in longitude.
- **Depends on:** MOD-3.
- **Files:** `models/roche/spots.py`, `models/roche/surface.py` (subdivision hook), `tests/test_roche_spots.py`

### MOD-9. Native kernel, speed, and the reference grid  (P1)
**open**
- **Build:**
  1. `native/src/roche.rs` (ARC-9): surface solve, visibility with the eclipse test, intensities and the phase
     loop, threaded over phases; the NumPy implementation of MOD-1 … MOD-8 stays as twin and reference.
  2. Reference grid: 40 synthetic systems spanning q = 0.1–1, detached (wide and close), semi-detached (each star
     filling), contact (f = 0.1, 0.5, 0.9), eccentric (e = 0.1, 0.4), with and without reflection, spots, third
     light, in V and TESS bands; each computed with PHOEBE 2 (installed in a separate virtual environment, never in
     ours) and, where the feature exists, with the WD program built from its public source and with ellc; the
     scripts in `tests/validation/scripts/binary_reference/`, the curves in `tests/validation/data/binary_reference/`.
  3. `tests/validation/test_roche_reference.py`: our curves against each reference with the tolerances of MOD-3 …
     MOD-8; the differences between the reference programs themselves are measured and written here (they bound
     what "agreement" can mean).
  4. Benchmarks in `tools/speed.py`: one curve of 500 phases at each accuracy setting; a 20 000-evaluation fit.
- **Accept:** native = NumPy twin within 1e-10 relative; 500 phases at `normal`: < 20 ms native on the reference
  machine (4 threads), `fine` < 100 ms; the reference tests pass; a table of ours / PHOEBE / WD / ellc differences
  and timings is written into the guide's methods chapter.
- **Depends on:** MOD-1 … MOD-8, ARC-9.
- **Files:** `native/src/roche.rs`, `models/roche/engine.py` (chooses native or NumPy), `tests/validation/scripts/binary_reference/{phoebe,wd,ellc}_*.py`, `tests/validation/data/binary_reference/`, `tests/validation/test_roche_reference.py`, `tools/speed.py`

### MOD-W. The Models window on the new anatomy  (P1)
**open**
- `plans/interface.md` UI-16.6: stages Data, System, Stars, Extras, Fit, Uncertainty, Results; light curves and
  velocities with residuals; the 3-D view; result tabs Parameters, Fit history, Posterior, Report. A toolbar
  switch: **Eclipsing binary · Visual orbit**.
- **Extra accept:** load V and R light curves and two velocity curves → "Estimate starting values" → model drawn
  over the data → Fit → results table: **six clicks**; the sentence sending users to other programs is gone; a
  model evaluation after any parameter edit redraws in < 150 ms (normal accuracy).
- **Depends on:** ARC-4.6, ARC-5, ARC-6, ARC-8, UI-1 … UI-4, MOD-10.
- **Files:** `ui/models/{window,controller,state,menus}.py`, `ui/models/panels/{data,system,stars,extras,fit,uncertainty,results,parameters,history,view3d}.py`, `ui/models/visual/` (the visual-orbit job), `tests/ui/walks/models.py`, guide 09

### MOD-10. Data sets, parameters, constraints  (P1)
**partial** — done (2026-11-12): `models/system.py`: `Parameter` (value, free, limits, prior, unit, locked with the
reason), `DataSet`, `System` with the morphology applied on every edit (detached; semi-detached 1 / 2: Ω = Ω_in;
contact: both potentials from the fill-out); exact conversions (r₁ + r₂, k; e cos ω, e sin ω; √e cos ω, √e sin ω;
star 2's own-frame potential; potentials ↔ volume radius and fill-out in models.roche) round-tripping to 1e-10;
`check` (codes with advice: T0 far, no period, beyond the lobe, RV with a fixed a, third light with the inclination
on a partial eclipse); the TOML system file both ways. Left: per-band parameters (item 4), double contact, T₂ tied
by gravity darkening, the WD and PHOEBE importers.
- **Read first:** Conroy et al. 2020 §2–3 (parameters, constraints, distributions); the WD modes (what each
  constrains: mode 2 detached; 3 overcontact; 4 / 5 semi-detached; 1 overcontact with T₂ tied by gravity darkening;
  6 double contact); JKTEBOP's parameter choices (r₁ + r₂, k, e cos ω, e sin ω; why they are less correlated).
- **Build:**
  1. `models/system.py`: `DataSet` (kind: light curve in a band | RV of star 1 | RV of star 2 | minima times
     (MOD-17); times with their standard, values, errors; exposure time; a noise scale factor and a zero point /
     flux scale, each free or fixed; phase or time domain; the option to bin in phase for speed with the binning
     noted); `Parameter` (key, plain name, symbol WD / PHOEBE, value, unit, free, lower / upper limit, prior:
     none | uniform | Gaussian, step for derivatives, group); `System` holding parameters, data sets, model level,
     morphology, accuracy.
  2. Morphology as constraints applied automatically and shown as locked rows with the reason: detached (none);
     semi-detached, star 1 or 2 filling (Ω = Ω_in(q)); contact (Ω₂ = Ω₁; fill-out f as the free parameter; β and A
     equal by default; T₂ free, or tied through gravity darkening on request); double contact.
  3. Alternative parameterisations the user can switch, converted exactly: potentials ↔ fractional radii (volume,
     pole) ↔ (r₁ + r₂, k) ↔ fill-out; (e, ω) ↔ (e cos ω, e sin ω) ↔ (√e cos ω, √e sin ω); T₂ ↔ T₂ / T₁; band
     luminosities computed from temperatures and radii (coupled) or free per band (decoupled, as WD's IPB = 1).
  4. Per-band parameters: limb-darkening source (tables / typed, law), third light, luminosity coupling, boosting
     factor.
  5. Sanity checks before any run, as codes with advice: T0 far from the data span; period missing; a star beyond
     its lobe in a "detached" set-up; RV data without the semi-major axis free; third light free in every band
     together with the inclination on a partially eclipsing curve (strong degeneracy: warn, not forbid).
  6. Serialisation in the session (ARC-5) and as a human-readable TOML "system file"; importers for a PyWD / WD
     `lcin` / `dcin` parameter set and a PHOEBE 2 bundle's JSON (parameters only) so that an existing solution can
     be opened here.
- **Accept:** round trip of every parameterisation to 1e-10; each morphology's constraints hold after random
  parameter edits (property test); a stored WD parameter file and a PHOEBE bundle load to the same model curve as
  the reference programs gave for them (within MOD-3's tolerances).
- **Files:** `models/system.py`, `models/io_wd.py`, `models/io_phoebe.py`, tests.

### MOD-11. Starting values from the data  (P1)
**partial** — done (2026-11-12), the light-curve part: `models/estimate.py`: Mowlavi et al.'s two-Gaussian model
(constant, ellipsoidal cosine, one wrapped Gaussian per eclipse; several starts for the secondary's phase) and from
it e cos ω (within 0.01 on 25 random detached systems), e sin ω from the widths, r₁ + r₂ from the widths (within
35 %: partial eclipses and e), J from the depths, a morphology suggestion with its reason (a W UMa curve called
contact), `oconnell` (the maxima's difference: a spot suggested beyond 3σ). Left: the velocity part (SPE-15), T₁
from Gaia colours, the inclination from the depth and shape, the 40-system convergence test (needs MOD-12), the
step and the one-click table.
- **Why:** the hardest part for a newcomer in every reference program; PHOEBE's estimators are its most praised
  addition.
- **Read first:** Conroy et al. 2020 §4.1 (`lc_geometry`: two-Gaussian models of the eclipses → positions, widths,
  depths → e cos ω, e sin ω, r₁ + r₂, T₂ / T₁; `rv_geometry`; `ebai`); Mowlavi et al. 2017 (two-Gaussian models);
  Matijevič et al. 2012 (the morphology parameter); Kopal's and Russell & Merrill's classical relations between
  eclipse depths, durations and elements; Wyithe & Wilson 2001 and Terrell & Wilson 2005 (when a photometric mass
  ratio is reliable: total eclipses in contact / semi-detached systems).
- **Build:** `models/estimate.py`: from the folded light curve(s): eclipse positions (→ e cos ω from the
  secondary's phase), widths (→ e sin ω and r₁ + r₂ for a first guess of i from the depth and shape: flat bottom →
  total eclipse), depths (→ surface-brightness / temperature ratio in the band, with T₁ from the colour or typed),
  the out-of-eclipse curvature and maxima difference (→ ellipticity → close system; O'Connell effect → a spot
  suggested), a morphology suggestion (detached / semi-detached / contact) from the shape with its confidence;
  from velocities: K₁, K₂, γ, q, a sin i, e, ω (SPE-15's fit); T₁ from Gaia BP − RP (with reddening typed or from a
  map the user chooses) offered as a start, never as a result; for contact systems without velocities: a note that
  q needs the q-search and total eclipses. The result is a table "estimated from the data: value, how, how sure"
  that the user applies in one click or per row.
- **Accept:** on the 40 reference systems with noise added (σ = 0.5 %): the estimates start a local fit that
  converges to the true solution in ≥ 85 % of the systems (a test with the fits of MOD-12); morphology suggested
  right in ≥ 90 %; e cos ω within 0.01.
- **Depends on:** MOD-9.
- **Files:** `models/estimate.py`, step `models.estimate`, `tests/test_model_estimate.py`

### MOD-12. Fitting, with a history the user can walk  (P1)
**partial** — done (2026-11-12): `models/fitting.py` on MOD-10's System: the objective over data sets with their
noise scales and Gaussian priors, weights by the errors or by each set's scatter; the flux scale / zero point solved
exactly inside; optimisers lm, nelder_mead, powell, de, basin (kicked local fits), careful (DE over the geometric
parameters, then lm); every run a History row (optimiser, free, χ² before / after, time, values, formal errors)
restored exactly. Tests on the analytic eclipse model with an unknown flux scale: lm, Nelder–Mead and basin recover
r₁, r₂, i, J within 4σ; careful from a poor start reaches i within 0.3°; the history restores the earlier row.
Left: per-iteration sub-rows, live feedback, residual diagnostics, the 40-system test with Roche models, speed.
- **Ours now:** `models/fit.fit_light_curve` (bounded least squares, covariance errors) — kept as the Simple-level fitter and migrated into `models/fitting.py`.
- **Read first:** the WD documentation on differential corrections (subsets, damping, why solutions oscillate);
  Conroy et al. 2020 §4.2 (optimisers; differential corrections as a Levenberg–Marquardt variant); Prša & Zwitter
  2005 (heuristic scanning, parameter kicking); Southworth 2008 (JKTEBOP practice).
- **Build:**
  1. `models/fitting.py`: the objective: Σ over data sets of weighted squared residuals with each set's noise
     scale (weights by given errors, or equal with σ from the residual scatter per set — as WD's curve-dependent
     weights; the choice shown), plus prior terms.
  2. Optimisers: `lm` (bounded Levenberg–Marquardt with finite-difference derivatives using each parameter's step,
     run in parallel over parameters; equals differential corrections with damping), `nelder_mead`, `powell`,
     `differential_evolution` (global, within the limits), `basin` (repeated local fits from kicked starts, as
     PHOEBE 1's kicking); a "Careful" preset: DE over the geometric parameters → LM over all free ones.
  3. Linear parameters solved exactly inside each evaluation (flux scales, zero points, optionally third light
     and γ) to remove them from the search.
  4. **Fit history** (as PyWD's history window): every run is a row (optimiser, free parameters, χ² before / after,
     time), every iteration of LM a sub-row with the corrections and formal errors; any row can be restored
     (undo); two rows compared (parameters and curves side by side).
  5. Live feedback: χ² and the curves update during the run (throttled), Stop keeps the best so far.
  6. Correlation matrix and formal errors after a local fit, with the standing note that formal errors of such fits
     are underestimates (pointing to MOD-14).
  7. Residual diagnostics: residuals against phase per data set, their autocorrelation, a normality test, and
     systematic patterns named ("residuals correlated around phase 0.3–0.4: a spot or a wrong third light?").
- **Accept:** on the 40 systems with noise: the "Careful" preset recovers all free parameters within 3σ of the
  truth in ≥ 90 % from MOD-11's starts; LM alone from a start 5 % away converges in ≤ 15 iterations; a fit of 2000
  points in two bands with 10 free parameters: < 30 s (normal accuracy); the history restores an earlier row
  exactly.
- **Depends on:** MOD-10, MOD-11.
- **Files:** `models/fitting.py`, `models/history.py`, step `models.fit` (old `models.eb_fit` kept as a wrapper), `tests/test_model_fitting.py`

### MOD-13. The q-search and other scans  (P1)
**partial** — done (2026-11-12): `models/scan.py` on MOD-12's fitting: `scan` (one parameter on a grid, the other
free ones fitted at each value warm-started, the minimum by a parabola, the 1σ range where χ² rises by χ²ᵣ, a
sharp / shallow verdict from the depth and the width) and `scan2` (a χ² map of two). Tests: the inclination's
minimum within 0.1° and sharp; a curve without its eclipses leaves the surface-brightness ratio shallow; the 2-D
map's minimum at the truth. Left: the q-search on Roche contact models (the totally / partially eclipsing pair),
adaptive refinement, parallel grid points, the W UMa set, the verdict's wording about total eclipses.
- **Read first:** Terrell & Wilson 2005 (Ap&SS 296, 221) and Hambálek & Pribulla 2013 (CoSka 43, 27) on the
  reliability of photometric mass ratios; any classical W UMa paper's q-search figure.
- **Build:** `models/scan.py`: q fixed on a grid (default 0.05–1.0 and, on request, the inverse range for W-type
  systems; adaptive refinement around the minimum), all other free parameters fitted at each value (warm-started
  from the neighbour), Σ weighted residuals² against q plotted live with the minimum and its 1σ range from Δχ²;
  run in parallel over q values; the same tool for any one or two parameters (χ² maps: i–q, Ω₁–Ω₂, l₃–i) to show
  degeneracies; a verdict line: "total eclipses seen: the photometric mass ratio is reliable" or "partial eclipses
  and no velocities: the minimum is shallow (Δχ² < … over q = 0.3–0.7); a spectroscopic mass ratio is needed".
- **Accept:** synthetic totally eclipsing contact system (q = 0.25): the scan's minimum within 0.01; a partially
  eclipsing one: the verdict says unreliable; the real W UMa set: the photometric q within 0.02 of the
  spectroscopic one; 40 q values × fits in < 5 min.
- **Depends on:** MOD-12.
- **Files:** `models/scan.py`, step `models.scan`, `ui/models/panels/scan.py`, `tests/test_model_scan.py`

### MOD-14. Uncertainties  (P1)
**open**
- **Ours now:** `models/fit.mcmc` (emcee, fixed steps, flat priors) and `models/fit.absolute_dimensions` (Monte Carlo).
- **Read first:** Conroy et al. 2020 §4.3; Southworth 2008 (residual permutation and Monte Carlo in JKTEBOP);
  Foreman-Mackey et al. 2013 (emcee) and ter Braak 2006 (differential-evolution MCMC); Hogg & Foreman-Mackey 2018
  (practical MCMC: convergence, autocorrelation time); Maxted et al. 2020 (the AI Phe comparison of codes and
  error methods).
- **Build:** the shared sampler of EXO-5 on the binary model with priors and constraints; parameters sampled in
  the less-correlated set (MOD-10.3); convergence by R̂ and effective sample size before results are shown as
  final; residual permutation ("prayer bead") and Monte Carlo of synthetic data sets as cheaper alternatives, all
  three compared in one table; derived quantities (radii, luminosity ratio, absolute dimensions) from the
  posterior; corner plot; the red-noise estimate of each light curve (β, PHO-34) offered as an error inflation;
  the chain stored with the session.
- **Accept:** on five reference systems with noise: 68 % intervals cover the truth at 60–76 % over 100 data
  realisations (run with the Simple model for speed and with Roche on two systems); AI Phe: masses and radii
  within 0.5 % and errors comparable to the published benchmark (± a factor 1.5); 50 000 samples with the native
  kernel < 20 min on 4 cores.
- **Depends on:** MOD-12, EXO-5.
- **Files:** `models/uncertainty.py`, `core/inference/` (EXO-5), `models/fit.py` (old `mcmc` becomes a wrapper), `tests/test_model_uncertainty.py`, `tests/coverage/test_binary_coverage.py`

### MOD-15. Absolute dimensions, distance, where the stars sit  (P1)
**open**
- **Read first:** Torres, Andersen & Giménez 2010 (A&ARv 18, 67: accurate masses and radii, the nominal solar
  values to use, the consistency checks); IAU 2015 Resolution B3 (nominal solar and conversion constants); Wilson
  2008 (direct distance); Stassun & Torres 2016 (eclipsing binaries against Gaia parallaxes).
- **Ours now:** `fit.absolute_dimensions` (M, R, a, log g from i, r₁, r₂ and M sin³ i, a sin i by Monte Carlo).
- **Build:** from the joint solution (or the light solution + an SB2 orbit): M, R, log g, mean density, synchronous
  v sin i (to compare with spectroscopy), L from R and T_eff, M_bol, with the IAU nominal constants; distance from
  the apparent magnitude at quadrature, the bolometric corrections of MOD-6's tables (or the surface-brightness
  relation of Kervella et al. 2004 as an independent route), extinction typed — compared with the Gaia parallax in
  one line; without velocities: the estimates possible from a mass–luminosity assumption, clearly labelled as
  assumptions; plots: mass–radius and H–R diagrams with the zero-age and terminal main sequence (from the
  isochrone pack of EXO-6 when installed), Roche-lobe filling percentages; a table in the layout of Torres et al.
- **Accept:** AI Phe's published M and R reproduced within the published errors from our fit; the distance within
  2σ of Gaia's; constants are the IAU nominal ones (a test).
- **Files:** `models/absolute.py` (from `fit.absolute_dimensions`, re-exported), `core/constants.py`, `stars/` (bolometric corrections), `tests/test_absolute.py`

### MOD-16. Seeing the system  (P1)
**open**
- **Ours now:** nothing; `models/fit.roche_check` gives the fill-out only.
- **Reference:** Binary Maker 3 (the star-shape animation is why observers use it); PyWD2015 "star positions";
  PHOEBE mesh plots.
- **Build:** `ui/models/panels/view3d.py` (pyqtgraph's OpenGL view if its dependency PyOpenGL is acceptable on all
  targets — check licence and wheels — else a painter's-algorithm 2-D projection drawn by us, which is enough for
  convex lobes): the two surfaces at the phase under the cursor, shaded by local temperature or by emergent
  intensity in the band, spots visible, the eclipsed part dimmed; the phase follows the mouse over the light curve
  and can play; views: observer, top (orbital plane), side; a second tab: equipotential cross-sections in the
  orbital plane with L1–L3, the lobes and both surfaces; export of a picture (through publish) and of an animation
  (PNG sequence and GIF through Pillow).
- **Accept:** the silhouette areas at 50 phases equal the model's projected areas within 1 %; 30 fps while dragging
  the phase; the picture of a contact system shows the neck; four-language labels.
- **Files:** `ui/models/panels/view3d.py`, `models/roche/render.py` (projection and shading without Qt), `tests/test_roche_render.py`

### MOD-17. More kinds of data in the same fit  (P2)
**open**
- **Build:** times of minimum as a data set (constraining P, T0, dP/dt, dω/dt, third-body terms — as WD 2015 and
  JKTEBOP); a spectroscopic light ratio at a wavelength as a constraint (Gaussian prior on L₂ / L₁ in that band);
  a known third-light fraction from imaging; v sin i measurements constraining F; a parallax prior with the
  distance of MOD-15; colour-index curves.
- **Accept:** each constraint moves a synthetic solution towards the truth and narrows the posterior as expected
  (tests); the apsidal-motion system of OC-7 fitted with light curve + minima gives ω̇ within its error.
- **Files:** `models/system.py` (new data kinds), `models/fitting.py` (their likelihood terms), `tests/test_model_datakinds.py`

### MOD-18. The Simple level, complete  (P2)
**open**
- **Read first:** Nelson & Davis 1972; Popper & Etzel 1981; Southworth's JKTEBOP documentation (tasks and options);
  Etzel 1981.
- **Build:** biaxial ellipsoids with oblateness from q and the radii, the EBOP reflection term, gravity darkening
  coefficients, all limb-darkening laws (through EXO-1's occultation integrals for uniform + polynomial laws, and
  our numerical integral otherwise), exposure integration, polynomial and sine terms per data set, light-ratio and
  third-light constraints, velocities and minima fitted with the light curve; a strict validity check (oblateness
  > 0.04 → advise Roche).
- **Accept:** against JKTEBOP run beside ours on two detached systems: parameters within 0.2σ, curves within 1e-5.
- **Files:** `models/simple.py` (from `eb.py`, old names re-exported), `occult/`, `tests/test_simple_model.py`, `tests/validation/scripts/jktebop/`

### MOD-19. Reports and exchange  (P1)
**open**
- **Ours now:** `models/data.export_for_phoebe`, `models/wd.write_wd_files`, `models/transit_report.py`, `ui/export.save_results` (CSV / LaTeX of the fit).
- **Build:** figures through `ui/plot/publish`: light curves per band with model and residual panels (phase and
  time), velocity curves with residuals, the 3-D views at four phases, the q-search plot, the corner plot; tables:
  the solution in the journal layout (parameter, value ± error, fixed marks, the method of the errors), absolute
  dimensions, spots; the synthetic curves as files; the system file (MOD-10.6); exports to WD (`lcin` / `dcin`
  with every parameter we have mapped to its WD name) and to a PHOEBE 2 script that rebuilds the bundle — for users
  who must cross-check; the methods text (ARC-11) naming every physical ingredient switched on and its reference.
- **Accept:** the WD export of five reference systems run through the WD program reproduces our curve within the
  cross-program tolerance; the PHOEBE script likewise; LaTeX tables compile.
- **Files:** `models/report.py`, `models/{io_wd,io_phoebe}.py` (writers), `models/wd.py` and `models/data.py` (old exports kept), `resources/methods/models_*.txt`, `tests/test_model_report.py`

### MOD-20. Visual binaries  (P2)
**open**
- **Ours now:** `models/visual.py` (grid + linear Thiele–Innes fit, Campbell elements with errors, ephemeris).
- **Read first:** Hartkopf, Mason & Worley 2001 (ORB6 conventions and grades); Lucy 2014 (A&A 563, A126: orbits
  from short arcs, Bayesian); Pourbaix 1994 and 2000 (simultaneous visual + spectroscopic solutions).
- **Build:** data from the WDS / INT4 / ORB6 by name (`services`), with techniques and weights (micrometer, speckle,
  Gaia, interferometry: default weight table editable); quadrant ambiguity flips handled; MCMC for short arcs with
  the posterior of P and a shown as they are (not Gaussian); combined visual + SB1 / SB2 fits (orbital parallax,
  individual masses); precession correction of position angles to a common equinox; ephemeris tables for observers;
  an orbit plot in the sky plane with the line of nodes and periastron, residual plots in ρ and θ; dynamical mass
  sum with the parallax (Gaia) and its error.
- **Accept:** three ORB6 grade-1 orbits reproduced within their errors from the INT4 measures; a synthetic visual +
  SB2 system: masses and distance within 1σ.
- **Files:** `models/visual.py`, `models/visual_joint.py`, `services/{wds,orb6,int4}.py`, `ui/models/visual/`, `tests/test_visual_orbit.py`

### MOD-21. Benchmarks against published solutions  (P1)
**open**
- **Build:** `tests/validation/test_binary_benchmarks.py` and a chapter of the guide: for each system of "Data
  used", our solution from our own fit against the published one (parameters, errors, residual scatter), with the
  differences discussed; the owner's own solved system when provided.
- **Accept:** every benchmark's key parameters (radii, inclination, temperature ratio, q where photometric) within
  the published errors, or the difference explained by a stated cause.
- **Files:** `tests/validation/test_binary_benchmarks.py`, `data/models/*/SOURCE.md`, guide 13

### MOD-22. Further models  (P3)
**open**
- **Build (each only when asked for or when a data set needs it):** synthetic line profiles of the components
  (rotation and orbital broadening over the visible surface) as a data kind; interstellar extinction per passband
  in the absolute-flux mode; spin axes not aligned with the orbit; a single rotating spotted star (rotational
  modulation fits); pulsation as a multi-sine term added to the binary model (for pulsating components, with PER-6's
  frequencies); a simple optically thick disc and hot spot for Algols and cataclysmic variables (Zola 1991's model
  as described in the literature) — listed so that the limits of the engine are stated in the guide.
- **Files:** `models/extra/{spotted_star,pulsation,disc}.py` (only when built)

## Found while working

(agents add findings here with a proposed priority; the architect moves them into steps)

## Done

(history before 2026-11-09: `docs/history/HANDOFF-2026-11.md`)
