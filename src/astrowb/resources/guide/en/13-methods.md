# Mathematics of the methods
Every fit and search in the program is a published method: the model below is what the code computes, and the paper named is where it comes from. Nothing is a rule of thumb made up for the program. Symbols: t time, y the measured value (flux, magnitude, velocity), σ its error, N the number of points.

## Least squares, errors and MCMC {#methods-least-squares-errors-mcmc}
Every fit minimises the weighted sum of squares

    χ² = Σ [(yᵢ − model(tᵢ; p)) / σᵢ]²

over the parameters p. Linear problems (ephemerides, polynomials, Thiele–Innes constants, light ratios) are solved exactly; the others by Levenberg–Marquardt (scipy least_squares). The 1σ errors are the square roots of the diagonal of the covariance (JᵀWJ)⁻¹ (J the derivatives of the model, W = 1/σ²). When the reduced χ²ᵣ = χ² / (N − number of parameters) is above 1, the scatter is larger than the errors claim, and the covariance is multiplied by χ²ᵣ. Without errors, the scatter of the residuals is the error.

**MCMC** (the "MCMC uncertainties" boxes): the affine-invariant ensemble sampler (Goodman & Weare 2010; emcee, Foreman-Mackey et al. 2013) draws parameter sets with probability ∝ exp(−χ²/2) (flat priors inside the physical limits), starting around the least-squares solution. The first half of the chain is discarded; each parameter is given as the median with the 16th and 84th percentiles. Unlike the covariance, this is right when parameters depend on each other (inclination and radii, e and ω).

## Period search {#methods-period-search}
All four methods try a grid of frequencies f = 1/P whose step moves the phase of the last point by a fixed small amount, so no peak can fall between two trial periods; the best peak is then refined on a 50× finer grid.

**Lomb–Scargle** (Lomb 1976, Ap&SS 39, 447; Scargle 1982, ApJ 263, 835; with a floating mean and the errors, Zechmeister & Kürster 2009, A&A 496, 577). At every f a sine wave plus a constant is fitted by least squares:

    y(t) = c + a cos 2πft + b sin 2πft,     power P(f) = 1 − χ²(f) / χ²₀

χ²₀ belongs to a constant alone. P is the share of the variance the sine explains (0 to 1). Best for sine-like curves: pulsations, spots, ellipsoidal variation.

**BLS — box least squares** (Kovács, Zucker & Mazeh 2002, A&A 391, 369; astropy). At every f, for each trial duration q and phase, the folded curve is fitted by a box: level H outside, H − δ inside. The depth is the difference of the weighted means, δ = ȳ_out − ȳ_in, and the power is the improvement of the log-likelihood, ½ δ² / σ_δ². Best for short, flat dips: transits, Algol-type eclipses.

**PDM — phase dispersion minimisation** (Stellingwerf 1978, ApJ 224, 953). The data are folded on the trial period and cut into M phase bins (default 20). With s² the pooled variance inside the bins and σ² the total variance:

    s² = Σⱼ (nⱼ − 1) sⱼ² / (Σⱼ nⱼ − M),     θ = s² / σ²

At the right period the points of a bin lie on top of each other and θ is small; the plot shows 1 − θ. No shape is assumed, so it suits eclipsing binaries with two minima.

**ANOVA — multi-harmonic analysis of variance** (Schwarzenberg-Czerny 1996, ApJ 460, L107). A Fourier series of n = 2 harmonics is fitted at every f,

    y(t) = c + Σₖ₌₁ⁿ [aₖ cos 2πkft + bₖ sin 2πkft]

and its explained variance is compared with the residual variance by the F statistic of analysis of variance:

    Θ = [(N − 2n − 1) / 2n] · P / (1 − P)

(P the explained share, as for Lomb–Scargle). Two harmonics follow non-sinusoidal shapes (RR Lyrae, Cepheids, binaries) and the F statistic has a known distribution, so peaks of different curves can be compared.

**Aliases.** The sampling (nights, satellite orbits) repeats, so every true frequency f also gives peaks at f ± 1/T_gap. For eclipsing binaries with equal minima the strongest peak is often at half the true period: check the folded curve.

## Frequency analysis and prewhitening {#methods-frequency-analysis-prewhitening}
The amplitude spectrum of unevenly sampled data (Deeming 1975, Ap&SS 36, 137):

    A(f) = (2/N) | Σ (yᵢ − ȳ) exp(−2πi f tᵢ) |

The **spectral window** is the same sum with yᵢ − ȳ replaced by 1; its side peaks are the aliases of the sampling. The highest peak is fitted by least squares, and then all frequencies found so far together, each with its own amplitude and phase:

    y(t) = c + Σₖ Aₖ sin 2π(fₖ t + φₖ)

The fitted curve is subtracted (**prewhitening**) and the residuals are searched again. A frequency is kept while S/N = Aₖ / (mean residual amplitude within ±1 c/d) ≥ 4 (Breger et al. 1993, A&A 271, 482). Errors (Montgomery & O'Donoghue 1999, DSSN 13, 28), with σ the rms of the residuals and T the time span:

    σ(f) = √6 σ / (π √N A T),    σ(A) = √(2/N) σ,    σ(φ) = σ(A) / (2π A)  (in cycles)

**CLEAN** (Roberts, Lehár & Dreher 1987, AJ 93, 968) removes the window's side lobes from the spectrum, a fraction (0.2) of the highest peak at a time.

## Times of minimum {#methods-times-minimum}
**Kwee & van Woerden** (1956, BAN 12, 327). The light curve is interpolated on an even grid and reflected about a trial time T. S(T), the mean squared difference between the descending and the rising branch, is smallest at the time of minimum. Near it S is a parabola, S(T) = aT² + bT + c, so

    T_min = −b / 2a,     σ² = (4ac − b²) / (4a² (Z − 1))

with Z the number of independent point pairs. The classic formula underestimates the error for noisy data (Deeg 2020, Galaxies 9, 1), so a bootstrap error (the residuals of a symmetric fit resampled 200 times) is also computed and the larger is reported.

**Polynomial**: a parabola fitted by least squares to the points around the minimum; T_min at its vertex, error from the covariance.

**Trapezoid** (for flat-bottomed transits): a symmetric trapezoid of depth δ, total duration T₁₄ and ingress τ, centred on T_min, on a straight baseline; the six parameters are fitted by least squares.

## Ephemeris and O-C {#methods-ephemeris-o-c}
The minima are numbered by the epoch E = round((T − T₀) / P), and fitted by

    linear:     T(E) = T₀ + P E
    quadratic:  T(E) = T₀ + P E + Q E²,     dP/dt = 2Q / P

weighted by 1/σ² of each minimum. The fit is made around the middle epoch (where T₀ and P are least correlated) and carried back to the epoch you gave. O − C = T_observed − T₀ − P E. dP/dt is shown in seconds per year.

## Third body and apsidal motion {#methods-third-body-apsidal-motion}
**Light-travel-time effect** (Irwin 1952, ApJ 116, 211). The eclipsing pair moves around the centre of mass with a third star, so the light arrives early or late by

    τ = A [ (1 − e²) / (1 + e cos ν) · sin(ν + ω) + e sin ω ],     A = a₁₂ sin i / c

ν is the true anomaly of the third-body orbit (period P₃, periastron T₃) from Kepler's equation M = E − e sin E. The model T = T₀ + P E + τ is fitted; the mass function follows: f(m₃) = (a₁₂ sin i)³ / P₃² (AU, years, solar masses).

**Apsidal motion** (Giménez & García-Pelayo 1983, Ap&SS 92, 203; first order in e, i ≈ 90°). With ω = ω₀ + ω̇ E and the anomalistic period Pₐ = Pₛ / (1 − ω̇/360°):

    T_I  = T₀ + Pₛ E − (Pₐ/π) e cos ω
    T_II = T₀ + Pₛ E + Pₐ/2 + (Pₐ/π) e cos ω

Primary and secondary minima swing in opposite directions; the apsidal period is U = 360° / ω̇ cycles. For e above ~0.1 the higher-order terms matter.

## Eclipsing binary light curve {#methods-eclipsing-binary-light-curve}
Two spheres on a Keplerian orbit (the spherical approximation of EBOP / JKTEBOP, Popper & Etzel 1981, AJ 86, 102; Southworth 2013, A&A 557, A119). With radii r₁, r₂ in units of the semi-major axis, the projected separation is

    d = (1 − e²) / (1 + e cos ν) · √(1 − sin² i sin²(ν + ω))

Each star has quadratic limb darkening I(μ) = I₀ [1 − u₁(1 − μ) − u₂(1 − μ)²], and J = I₀,₂ / I₀,₁ is the surface-brightness ratio. The light lost when one disc covers the other is the integral of I over the covered part, computed by Gauss–Legendre quadrature:

    ΔF = ∫ I(x) · 2x θ(x) dx,     θ(x) = arccos[(x² + d² − r_front²) / (2xd)]

The model flux, F = (1 − L₃)(F₁ + F₂ − ΔF)/(F₁ + F₂) + L₃ (1 outside eclipses, third light L₃ a fraction of the total), is fitted by least squares (and MCMC on request). Reflection, tidal distortion and gravity darkening are not modelled; close binaries need PHOEBE or WD (export buttons).

## Radial velocities and spectroscopic orbits {#methods-radial-velocities-spectroscopic-orbits}
**Cross-correlation** (Tonry & Davis 1979, AJ 84, 1511). Spectrum and template on a ln λ grid, where a velocity is a shift: Δln λ = v/c. The normalised correlation C(v) peaks at the velocity; a parabola through the top three points gives it, and the error follows Zucker (2003, MNRAS 342, 1291):

    σᵥ² = −[N · C''/C · C² / (1 − C²)]⁻¹

**TODCOR** (Zucker & Mazeh 1994, ApJ 420, 806) correlates with two templates at two shifts at once:

    R(s₁, s₂) = [C₁(s₁) + α C₂(s₂)] / √(1 + 2α C₁₂(s₁ − s₂) + α²)

with α, the light ratio, solved at every point. The highest R gives both velocities.

**Broadening function** (Rucinski 1992, AJ 104, 1968; 2002, AJ 124, 1746). The observed spectrum is the template convolved with B(v): a linear system P = D · B, solved by least squares (singular value decomposition). Each star appears as a rotational profile (Gray 2005, eq. 18.14) with its velocity, v sin i and light share.

**Orbit** (single- and double-lined):

    v(t) = γ + K [cos(ν + ω) + e cos ω],     M = 2π(t − T)/P = E − e sin E

fitted by least squares with √e cos ω and √e sin ω as parameters (stable near circular orbits); for a double-lined binary the two stars share P, T, e, γ, and ω₂ = ω₁ + 180°. Derived quantities (Hilditch 2001, eq. 2.52–2.53):

    f(m) = P K³ (1 − e²)^{3/2} / 2πG,     m₁ sin³ i = P (K₁ + K₂)² K₂ (1 − e²)^{3/2} / 2πG
    a sin i = P (K₁ + K₂) √(1 − e²) / 2π

With the inclination and radii of the light curve: masses, radii R = r · a and log g, from the same random draws of every input (as JKTABSDIM does), so the errors are propagated with their correlations.

## Visual binary orbit {#methods-visual-binary-orbit}
Thiele–Innes form (Heintz 1978, Double Stars). With the eccentric anomaly E from Kepler's equation:

    X = cos E − e,    Y = √(1 − e²) sin E
    x = ρ cos θ = A X + F Y,    y = ρ sin θ = B X + G Y

For fixed P, T and e the constants A, B, F, G are linear: they are solved exactly. P, T, e are searched on a grid, then all seven elements are refined together by Levenberg–Marquardt. The Campbell elements a, i, Ω, ω follow from A, B, F, G; the total mass from Kepler's third law: M₁ + M₂ = a³ / (ϖ³ P²) (a and parallax ϖ in arcsec, P in years).

## Spectra: wavelength, atmosphere, telluric, disentangling {#methods-spectra-wavelength-atmosphere-telluric}
**Wavelength solution**: arc lines are centred by a Gaussian fit; λ(x) = Σ cₖ xᵏ is fitted with sigma clipping, as IRAF identify does. For echelle spectra the grating equation makes m·λ a smooth function of pixel x and order m, so one surface Σ cᵢⱼ xⁱ mʲ covers every order (IRAF ecidentify; Baranne et al. 1996).

**Atmospheric parameters** (the approach of iSpec / SME, on a precomputed grid): the observed spectrum is modelled as

    F(λ) = Pₖ(λ) · [S(Teff, log g, [Fe/H]) ∗ G_rot(v sin i) ∗ G_inst(R)](λ / (1 + v/c))

S interpolated in the PHOENIX grid (Husser et al. 2013), Pₖ a low polynomial per wavelength chunk that takes up the instrument response; fitted by Levenberg–Marquardt.

**Telluric correction**: the absorption scales as optical depth, so T_sci = T_std^s with s ≈ the airmass ratio; s = Σ ln F ln T / Σ (ln T)² inside the telluric bands, and a sub-pixel shift is fitted too.

**Disentangling** (González & Levato 2006, A&A 448, 283): each star's spectrum is the mean of the observed spectra, shifted to its rest frame, after the other star's current spectrum has been removed; this is repeated until it converges.

## Photometry {#methods-photometry}
**Aperture photometry**: the sky is the sigma-clipped level of an annulus; F = sum in the aperture − N_ap · sky; its error is the CCD equation with the sky noise σ_sky measured in the annulus (Merline & Howell 1995, Exp. Astron. 6, 163):

    σ_F² = F / gain + N_ap (1 + N_ap / N_sky) σ_sky²

**Extinction**: mᵢⱼ = cⱼ + k Xᵢ (one constant per comparison star, one k), the Bouguer line.

**Transformation** (the AAVSO convention for two filters A, B): (A − B) = T_ab (a − b) + Z_ab, (B − b) = T_b (A − B) + Z_b, with a, b instrumental magnitudes; fitted by least squares on a standard field.
