# Mathematik der Methoden
Jede Anpassung und jede Suche im Programm ist eine veröffentlichte Methode: Das Modell unten ist das, was der Code berechnet, und die genannte Arbeit ist seine Quelle. Nichts davon ist eine für das Programm erfundene Faustregel. Symbole: t Zeit, y der Messwert (Fluss, Helligkeit, Geschwindigkeit), σ sein Fehler, N die Zahl der Punkte.

## Kleinste Quadrate, Fehler und MCMC {#methods-least-squares-errors-mcmc}
Jede Anpassung minimiert die gewichtete Quadratsumme

    χ² = Σ [(yᵢ − Modell(tᵢ; p)) / σᵢ]²

über die Parameter p. Lineare Probleme (Ephemeriden, Polynome, Thiele-Innes-Konstanten, Lichtverhältnisse) werden exakt gelöst, die anderen mit Levenberg-Marquardt (scipy least_squares). Die 1σ-Fehler sind die Wurzeln der Diagonale der Kovarianz (JᵀWJ)⁻¹ (J die Ableitungen des Modells, W = 1/σ²). Ist das reduzierte χ²ᵣ = χ² / (N − Zahl der Parameter) größer als 1, streuen die Daten stärker als ihre Fehler angeben, und die Kovarianz wird mit χ²ᵣ multipliziert. Ohne Fehler ist die Streuung der Residuen der Fehler.

**MCMC** (die Kästchen „MCMC-Unsicherheiten“): Der affin-invariante Ensemble-Sampler (Goodman & Weare 2010; emcee, Foreman-Mackey et al. 2013) zieht Parametersätze mit einer Wahrscheinlichkeit ∝ exp(−χ²/2) (flache Priors innerhalb der physikalischen Grenzen), beginnend um die Lösung der kleinsten Quadrate. Die erste Hälfte der Kette wird verworfen; jeder Parameter wird als Median mit dem 16. und 84. Perzentil angegeben. Anders als die Kovarianz stimmt das auch, wenn Parameter voneinander abhängen (Inklination und Radien, e und ω).

## Periodensuche {#methods-period-search}
Alle vier Methoden probieren ein Frequenzgitter f = 1/P, dessen Schritt die Phase des letzten Punktes um einen festen kleinen Betrag verschiebt, sodass kein Maximum zwischen zwei Testperioden fallen kann; das beste Maximum wird dann auf einem 50-fach feineren Gitter verfeinert.

**Lomb–Scargle** (Lomb 1976, Ap&SS 39, 447; Scargle 1982, ApJ 263, 835; mit freiem Mittelwert und den Fehlern Zechmeister & Kürster 2009, A&A 496, 577). Bei jedem f wird eine Sinuswelle plus Konstante nach kleinsten Quadraten angepasst:

    y(t) = c + a cos 2πft + b sin 2πft,     Leistung P(f) = 1 − χ²(f) / χ²₀

χ²₀ gehört zu einer Konstanten allein. P ist der Anteil der Varianz, den der Sinus erklärt (0 bis 1). Am besten für sinusartige Kurven: Pulsationen, Flecken, ellipsoidale Veränderung.

**BLS — Box Least Squares** (Kovács, Zucker & Mazeh 2002, A&A 391, 369; astropy). Bei jedem f wird für jede Testdauer q und Phase ein Kasten an die gefaltete Kurve angepasst: Niveau H außerhalb, H − δ innerhalb. Die Tiefe ist die Differenz der gewichteten Mittelwerte, δ = ȳ_außen − ȳ_innen, und die Leistung ist die Verbesserung der Log-Likelihood, ½ δ² / σ_δ². Am besten für kurze, flache Einbrüche: Transits, Bedeckungen vom Algol-Typ.

**PDM — Phasendispersionsminimierung** (Stellingwerf 1978, ApJ 224, 953). Die Daten werden mit der Testperiode gefaltet und in M Phasenintervalle geteilt (Standard 20). Mit s² der gepoolten Varianz innerhalb der Intervalle und σ² der Gesamtvarianz:

    s² = Σⱼ (nⱼ − 1) sⱼ² / (Σⱼ nⱼ − M),     θ = s² / σ²

Bei der richtigen Periode liegen die Punkte eines Intervalls übereinander und θ ist klein; der Plot zeigt 1 − θ. Es wird keine Form vorausgesetzt, daher passt die Methode zu Bedeckungsveränderlichen mit zwei Minima.

**ANOVA — mehrharmonische Varianzanalyse** (Schwarzenberg-Czerny 1996, ApJ 460, L107). Bei jedem f wird eine Fourier-Reihe mit n = 2 Harmonischen angepasst,

    y(t) = c + Σₖ₌₁ⁿ [aₖ cos 2πkft + bₖ sin 2πkft]

und ihre erklärte Varianz wird mit der Restvarianz über die F-Statistik der Varianzanalyse verglichen:

    Θ = [(N − 2n − 1) / 2n] · P / (1 − P)

(P der erklärte Anteil wie bei Lomb–Scargle). Zwei Harmonische folgen nicht sinusförmigen Formen (RR Lyrae, Cepheiden, Doppelsterne), und die F-Statistik hat eine bekannte Verteilung, sodass Maxima verschiedener Kurven vergleichbar sind.

**Aliase.** Die Abtastung (Nächte, Satellitenbahnen) wiederholt sich, daher erzeugt jede wahre Frequenz f auch Maxima bei f ± 1/T_Lücke. Bei Bedeckungsveränderlichen mit gleich tiefen Minima liegt das stärkste Maximum oft bei der halben wahren Periode: die gefaltete Kurve prüfen.

## Frequenzanalyse und Prewhitening {#methods-frequency-analysis-prewhitening}
Das Amplitudenspektrum ungleichmäßig abgetasteter Daten (Deeming 1975, Ap&SS 36, 137):

    A(f) = (2/N) | Σ (yᵢ − ȳ) exp(−2πi f tᵢ) |

Das **Spektralfenster** ist dieselbe Summe mit 1 statt yᵢ − ȳ; seine Nebenmaxima sind die Aliase der Abtastung. Das höchste Maximum wird nach kleinsten Quadraten angepasst, dann alle bisher gefundenen Frequenzen gemeinsam, jede mit eigener Amplitude und Phase:

    y(t) = c + Σₖ Aₖ sin 2π(fₖ t + φₖ)

Die angepasste Kurve wird abgezogen (**Prewhitening**) und die Residuen werden erneut durchsucht. Eine Frequenz wird behalten, solange S/N = Aₖ / (mittlere Restamplitude innerhalb ±1 c/d) ≥ 4 (Breger et al. 1993, A&A 271, 482). Fehler (Montgomery & O'Donoghue 1999, DSSN 13, 28), mit σ dem rms der Residuen und T der Zeitspanne:

    σ(f) = √6 σ / (π √N A T),    σ(A) = √(2/N) σ,    σ(φ) = σ(A) / (2π A)  (in Zyklen)

**CLEAN** (Roberts, Lehár & Dreher 1987, AJ 93, 968) entfernt die Nebenkeulen des Fensters aus dem Spektrum, jeweils einen Bruchteil (0,2) des höchsten Maximums.

## Minimumszeiten {#methods-times-minimum}
**Kwee & van Woerden** (1956, BAN 12, 327). Die Lichtkurve wird auf ein gleichmäßiges Gitter interpoliert und an einer Testzeit T gespiegelt. S(T), die mittlere quadratische Differenz zwischen absteigendem und aufsteigendem Ast, ist zur Minimumszeit am kleinsten. In der Nähe ist S eine Parabel, S(T) = aT² + bT + c, also

    T_min = −b / 2a,     σ² = (4ac − b²) / (4a² (Z − 1))

mit Z der Zahl unabhängiger Punktpaare. Die klassische Formel unterschätzt den Fehler bei verrauschten Daten (Deeg 2020, Galaxies 9, 1); daher wird auch ein Bootstrap-Fehler berechnet (die Residuen einer symmetrischen Anpassung 200-mal neu gezogen) und der größere angegeben.

**Polynom**: eine nach kleinsten Quadraten angepasste Parabel durch die Punkte um das Minimum; T_min im Scheitel, Fehler aus der Kovarianz.

**Trapez** (für Transits mit flachem Boden): ein symmetrisches Trapez der Tiefe δ, Gesamtdauer T₁₄ und Eintrittsdauer τ, zentriert auf T_min, auf einer geraden Grundlinie; die sechs Parameter werden nach kleinsten Quadraten angepasst.

## Ephemeride und O-C {#methods-ephemeris-o-c}
Die Minima werden mit der Epoche E = round((T − T₀) / P) nummeriert und angepasst mit

    linear:     T(E) = T₀ + P E
    quadratisch: T(E) = T₀ + P E + Q E²,     dP/dt = 2Q / P

gewichtet mit 1/σ² jedes Minimums. Die Anpassung erfolgt um die mittlere Epoche (wo T₀ und P am wenigsten korreliert sind) und wird auf die angegebene Epoche zurückgerechnet. O − C = T_beobachtet − T₀ − P E. dP/dt wird in Sekunden pro Jahr angegeben.

## Dritter Körper und Apsidendrehung {#methods-third-body-apsidal-motion}
**Lichtlaufzeiteffekt** (Irwin 1952, ApJ 116, 211). Das bedeckende Paar bewegt sich mit einem dritten Stern um den Schwerpunkt, daher kommt das Licht zu früh oder zu spät um

    τ = A [ (1 − e²) / (1 + e cos ν) · sin(ν + ω) + e sin ω ],     A = a₁₂ sin i / c

ν ist die wahre Anomalie der Bahn des dritten Körpers (Periode P₃, Periastron T₃) aus der Kepler-Gleichung M = E − e sin E. Das Modell T = T₀ + P E + τ wird angepasst; daraus folgt die Massenfunktion f(m₃) = (a₁₂ sin i)³ / P₃² (AE, Jahre, Sonnenmassen).

**Apsidendrehung** (Giménez & García-Pelayo 1983, Ap&SS 92, 203; erste Ordnung in e, i ≈ 90°). Mit ω = ω₀ + ω̇ E und der anomalistischen Periode Pₐ = Pₛ / (1 − ω̇/360°):

    T_I  = T₀ + Pₛ E − (Pₐ/π) e cos ω
    T_II = T₀ + Pₛ E + Pₐ/2 + (Pₐ/π) e cos ω

Haupt- und Nebenminima schwingen gegenläufig; die Apsidenperiode ist U = 360° / ω̇ Zyklen. Für e über etwa 0,1 werden die Terme höherer Ordnung wichtig.

## Lichtkurve eines Bedeckungsveränderlichen {#methods-eclipsing-binary-light-curve}
Zwei Kugeln auf einer Kepler-Bahn (die Kugelnäherung von EBOP / JKTEBOP, Popper & Etzel 1981, AJ 86, 102; Southworth 2013, A&A 557, A119). Mit den Radien r₁, r₂ in Einheiten der großen Halbachse ist der projizierte Abstand

    d = (1 − e²) / (1 + e cos ν) · √(1 − sin² i sin²(ν + ω))

Jeder Stern hat quadratische Randverdunklung I(μ) = I₀ [1 − u₁(1 − μ) − u₂(1 − μ)²]; J = I₀,₂ / I₀,₁ ist das Flächenhelligkeitsverhältnis. Das Licht, das verloren geht, wenn eine Scheibe die andere bedeckt, ist das Integral von I über den bedeckten Teil, berechnet mit Gauß-Legendre-Quadratur:

    ΔF = ∫ I(x) · 2x θ(x) dx,     θ(x) = arccos[(x² + d² − r_vorn²) / (2xd)]

Der Modellfluss F = (1 − L₃)(F₁ + F₂ − ΔF)/(F₁ + F₂) + L₃ (1 außerhalb der Bedeckungen, drittes Licht L₃ als Anteil am Gesamtlicht) wird nach kleinsten Quadraten angepasst (auf Wunsch mit MCMC). Reflexion, Gezeitenverformung und Schwerkraftverdunklung werden nicht modelliert; enge Doppelsterne brauchen PHOEBE oder WD (Export-Knöpfe).

## Radialgeschwindigkeiten und spektroskopische Bahnen {#methods-radial-velocities-spectroscopic-orbits}
**Kreuzkorrelation** (Tonry & Davis 1979, AJ 84, 1511). Spektrum und Vorlage auf einem ln-λ-Gitter, wo eine Geschwindigkeit eine Verschiebung ist: Δln λ = v/c. Die normierte Korrelation C(v) hat ihr Maximum bei der Geschwindigkeit; eine Parabel durch die drei höchsten Punkte liefert sie, der Fehler folgt Zucker (2003, MNRAS 342, 1291):

    σᵥ² = −[N · C''/C · C² / (1 − C²)]⁻¹

**TODCOR** (Zucker & Mazeh 1994, ApJ 420, 806) korreliert mit zwei Vorlagen bei zwei Verschiebungen zugleich:

    R(s₁, s₂) = [C₁(s₁) + α C₂(s₂)] / √(1 + 2α C₁₂(s₁ − s₂) + α²)

mit α, dem Lichtverhältnis, an jedem Punkt gelöst. Das höchste R liefert beide Geschwindigkeiten.

**Verbreiterungsfunktion** (Rucinski 1992, AJ 104, 1968; 2002, AJ 124, 1746). Das beobachtete Spektrum ist die Vorlage gefaltet mit B(v): ein lineares System P = D · B, gelöst nach kleinsten Quadraten (Singulärwertzerlegung). Jeder Stern erscheint als Rotationsprofil (Gray 2005, Gl. 18.14) mit seiner Geschwindigkeit, v sin i und seinem Lichtanteil.

**Bahn** (ein- und doppellinig):

    v(t) = γ + K [cos(ν + ω) + e cos ω],     M = 2π(t − T)/P = E − e sin E

angepasst nach kleinsten Quadraten mit √e cos ω und √e sin ω als Parametern (stabil bei fast kreisförmigen Bahnen); bei einem doppellinigen Paar teilen beide Sterne P, T, e, γ, und ω₂ = ω₁ + 180°. Abgeleitete Größen (Hilditch 2001, Gl. 2.52–2.53):

    f(m) = P K³ (1 − e²)^{3/2} / 2πG,     m₁ sin³ i = P (K₁ + K₂)² K₂ (1 − e²)^{3/2} / 2πG
    a sin i = P (K₁ + K₂) √(1 − e²) / 2π

Mit Inklination und Radien aus der Lichtkurve: Massen, Radien R = r · a und log g, aus denselben Zufallsziehungen aller Eingaben (wie JKTABSDIM), sodass die Fehler mit ihren Korrelationen fortgepflanzt werden.

## Bahn eines visuellen Doppelsterns {#methods-visual-binary-orbit}
Thiele-Innes-Form (Heintz 1978, Double Stars). Mit der exzentrischen Anomalie E aus der Kepler-Gleichung:

    X = cos E − e,    Y = √(1 − e²) sin E
    x = ρ cos θ = A X + F Y,    y = ρ sin θ = B X + G Y

Für feste P, T und e sind die Konstanten A, B, F, G linear: Sie werden exakt gelöst. P, T, e werden auf einem Gitter gesucht, dann werden alle sieben Elemente gemeinsam mit Levenberg-Marquardt verfeinert. Die Campbell-Elemente a, i, Ω, ω folgen aus A, B, F, G; die Gesamtmasse aus dem dritten Kepler-Gesetz: M₁ + M₂ = a³ / (ϖ³ P²) (a und Parallaxe ϖ in Bogensekunden, P in Jahren).

## Spektren: Wellenlänge, Atmosphäre, Tellurik, Entflechtung {#methods-spectra-wavelength-atmosphere-telluric}
**Wellenlängenlösung**: Bogenlinien werden mit einer Gauß-Anpassung zentriert; λ(x) = Σ cₖ xᵏ wird mit Sigma-Clipping angepasst, wie IRAF identify. Bei Echelle-Spektren macht die Gittergleichung m·λ zu einer glatten Funktion von Pixel x und Ordnung m, sodass eine Fläche Σ cᵢⱼ xⁱ mʲ alle Ordnungen abdeckt (IRAF ecidentify; Baranne et al. 1996).

**Atmosphärenparameter** (der Ansatz von iSpec / SME, auf einem vorberechneten Gitter): Das beobachtete Spektrum wird modelliert als

    F(λ) = Pₖ(λ) · [S(Teff, log g, [Fe/H]) ∗ G_rot(v sin i) ∗ G_inst(R)](λ / (1 + v/c))

S interpoliert im PHOENIX-Gitter (Husser et al. 2013), Pₖ ein niedriges Polynom pro Wellenlängenabschnitt, das die Instrumentenempfindlichkeit aufnimmt; angepasst mit Levenberg-Marquardt.

**Tellurische Korrektur**: Die Absorption skaliert wie die optische Tiefe, also T_Wiss = T_Std^s mit s ≈ dem Luftmassenverhältnis; s = Σ ln F ln T / Σ (ln T)² innerhalb der tellurischen Banden, dazu wird eine Subpixel-Verschiebung angepasst.

**Entflechtung** (González & Levato 2006, A&A 448, 283): Das Spektrum jedes Sterns ist das Mittel der beobachteten Spektren, in sein Ruhesystem verschoben, nachdem das aktuelle Spektrum des anderen Sterns abgezogen wurde; dies wird bis zur Konvergenz wiederholt.

## Photometrie {#methods-photometry}
**Aperturphotometrie**: Der Himmel ist das sigma-geclippte Niveau eines Rings; F = Summe in der Apertur − N_Ap · Himmel; sein Fehler ist die CCD-Gleichung mit dem im Ring gemessenen Himmelsrauschen σ_Himmel (Merline & Howell 1995, Exp. Astron. 6, 163):

    σ_F² = F / Gain + N_Ap (1 + N_Ap / N_Himmel) σ_Himmel²

**Extinktion**: mᵢⱼ = cⱼ + k Xᵢ (eine Konstante pro Vergleichsstern, ein k), die Bouguer-Gerade.

**Transformation** (die AAVSO-Konvention für zwei Filter A, B): (A − B) = T_ab (a − b) + Z_ab, (B − b) = T_b (A − B) + Z_b, mit a, b den instrumentellen Helligkeiten; angepasst nach kleinsten Quadraten an einem Standardfeld.
