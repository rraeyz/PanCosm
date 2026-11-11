# Matemáticas de los métodos
Cada ajuste y cada búsqueda del programa es un método publicado: el modelo de abajo es lo que calcula el código, y el artículo citado es su origen. Nada es una regla práctica inventada para el programa. Símbolos: t tiempo, y el valor medido (flujo, magnitud, velocidad), σ su error, N el número de puntos.

## Mínimos cuadrados, errores y MCMC {#methods-least-squares-errors-mcmc}
Cada ajuste minimiza la suma ponderada de cuadrados

    χ² = Σ [(yᵢ − modelo(tᵢ; p)) / σᵢ]²

sobre los parámetros p. Los problemas lineales (efemérides, polinomios, constantes de Thiele–Innes, cocientes de luz) se resuelven exactamente; los demás con Levenberg–Marquardt (scipy least_squares). Los errores 1σ son las raíces cuadradas de la diagonal de la covarianza (JᵀWJ)⁻¹ (J las derivadas del modelo, W = 1/σ²). Cuando el χ²ᵣ reducido = χ² / (N − número de parámetros) supera 1, la dispersión es mayor de lo que dicen los errores y la covarianza se multiplica por χ²ᵣ. Sin errores, la dispersión de los residuos es el error.

**MCMC** (las casillas «Incertidumbres MCMC»): el muestreador de conjunto invariante afín (Goodman & Weare 2010; emcee, Foreman-Mackey et al. 2013) extrae conjuntos de parámetros con probabilidad ∝ exp(−χ²/2) (priores planos dentro de los límites físicos), partiendo de la solución de mínimos cuadrados. La primera mitad de la cadena se descarta; cada parámetro se da como la mediana con los percentiles 16 y 84. A diferencia de la covarianza, esto es correcto cuando los parámetros dependen unos de otros (inclinación y radios, e y ω).

## Búsqueda de períodos {#methods-period-search}
Los cuatro métodos prueban una malla de frecuencias f = 1/P cuyo paso desplaza la fase del último punto una cantidad pequeña fija, de modo que ningún pico puede caer entre dos períodos de prueba; luego el mejor pico se refina en una malla 50 veces más fina.

**Lomb–Scargle** (Lomb 1976, Ap&SS 39, 447; Scargle 1982, ApJ 263, 835; con media flotante y los errores, Zechmeister & Kürster 2009, A&A 496, 577). En cada f se ajusta por mínimos cuadrados una onda sinusoidal más una constante:

    y(t) = c + a cos 2πft + b sin 2πft,     potencia P(f) = 1 − χ²(f) / χ²₀

χ²₀ corresponde a una constante sola. P es la fracción de la varianza que explica la sinusoide (de 0 a 1). Es el mejor para curvas sinusoidales: pulsaciones, manchas, variación elipsoidal.

**BLS — mínimos cuadrados con caja** (Kovács, Zucker & Mazeh 2002, A&A 391, 369; astropy). En cada f, para cada duración de prueba q y cada fase, se ajusta una caja a la curva plegada: nivel H fuera, H − δ dentro. La profundidad es la diferencia de las medias ponderadas, δ = ȳ_fuera − ȳ_dentro, y la potencia es la mejora de la log-verosimilitud, ½ δ² / σ_δ². Es el mejor para caídas cortas y planas: tránsitos, eclipses de tipo Algol.

**PDM — minimización de la dispersión de fase** (Stellingwerf 1978, ApJ 224, 953). Los datos se pliegan con el período de prueba y se dividen en M intervalos de fase (20 por defecto). Con s² la varianza combinada dentro de los intervalos y σ² la varianza total:

    s² = Σⱼ (nⱼ − 1) sⱼ² / (Σⱼ nⱼ − M),     θ = s² / σ²

En el período correcto los puntos de un intervalo se superponen y θ es pequeño; el gráfico muestra 1 − θ. No se supone ninguna forma, por lo que sirve para binarias eclipsantes con dos mínimos.

**ANOVA — análisis de varianza multiarmónico** (Schwarzenberg-Czerny 1996, ApJ 460, L107). En cada f se ajusta una serie de Fourier de n = 2 armónicos,

    y(t) = c + Σₖ₌₁ⁿ [aₖ cos 2πkft + bₖ sin 2πkft]

y su varianza explicada se compara con la varianza residual mediante el estadístico F del análisis de varianza:

    Θ = [(N − 2n − 1) / 2n] · P / (1 − P)

(P la fracción explicada, como en Lomb–Scargle). Dos armónicos siguen formas no sinusoidales (RR Lyrae, cefeidas, binarias) y el estadístico F tiene una distribución conocida, de modo que se pueden comparar picos de curvas distintas.

**Alias.** El muestreo (noches, órbitas de satélites) se repite, así que cada frecuencia verdadera f da también picos en f ± 1/T_hueco. En binarias eclipsantes con mínimos iguales, el pico más fuerte suele estar en la mitad del período verdadero: compruebe la curva plegada.

## Análisis de frecuencias y preblanqueo {#methods-frequency-analysis-prewhitening}
El espectro de amplitud de datos muestreados irregularmente (Deeming 1975, Ap&SS 36, 137):

    A(f) = (2/N) | Σ (yᵢ − ȳ) exp(−2πi f tᵢ) |

La **ventana espectral** es la misma suma con 1 en lugar de yᵢ − ȳ; sus picos laterales son los alias del muestreo. El pico más alto se ajusta por mínimos cuadrados, y luego todas las frecuencias halladas hasta entonces juntas, cada una con su amplitud y su fase:

    y(t) = c + Σₖ Aₖ sin 2π(fₖ t + φₖ)

La curva ajustada se resta (**preblanqueo**) y se vuelve a buscar en los residuos. Una frecuencia se conserva mientras S/N = Aₖ / (amplitud residual media dentro de ±1 c/d) ≥ 4 (Breger et al. 1993, A&A 271, 482). Errores (Montgomery & O'Donoghue 1999, DSSN 13, 28), con σ el rms de los residuos y T el intervalo de tiempo:

    σ(f) = √6 σ / (π √N A T),    σ(A) = √(2/N) σ,    σ(φ) = σ(A) / (2π A)  (en ciclos)

**CLEAN** (Roberts, Lehár & Dreher 1987, AJ 93, 968) elimina del espectro los lóbulos laterales de la ventana, una fracción (0,2) del pico más alto cada vez.

## Tiempos de mínimo {#methods-times-minimum}
**Kwee & van Woerden** (1956, BAN 12, 327). La curva de luz se interpola en una malla uniforme y se refleja respecto a un tiempo de prueba T. S(T), la diferencia cuadrática media entre la rama descendente y la ascendente, es mínima en el tiempo del mínimo. Cerca de él S es una parábola, S(T) = aT² + bT + c, así que

    T_min = −b / 2a,     σ² = (4ac − b²) / (4a² (Z − 1))

con Z el número de pares de puntos independientes. La fórmula clásica subestima el error con datos ruidosos (Deeg 2020, Galaxies 9, 1); por eso también se calcula un error bootstrap (los residuos de un ajuste simétrico remuestreados 200 veces) y se informa el mayor.

**Polinomio**: una parábola ajustada por mínimos cuadrados a los puntos alrededor del mínimo; T_min en su vértice, error de la covarianza.

**Trapecio** (para tránsitos de fondo plano): un trapecio simétrico de profundidad δ, duración total T₁₄ y entrada τ, centrado en T_min, sobre una línea de base recta; los seis parámetros se ajustan por mínimos cuadrados.

## Efemérides y O-C {#methods-ephemeris-o-c}
Los mínimos se numeran con la época E = round((T − T₀) / P) y se ajustan con

    lineal:      T(E) = T₀ + P E
    cuadrática:  T(E) = T₀ + P E + Q E²,     dP/dt = 2Q / P

ponderados con 1/σ² de cada mínimo. El ajuste se hace alrededor de la época central (donde T₀ y P están menos correlacionados) y se traslada a la época indicada. O − C = T_observado − T₀ − P E. dP/dt se da en segundos por año.

## Tercer cuerpo y movimiento apsidal {#methods-third-body-apsidal-motion}
**Efecto de tiempo de luz** (Irwin 1952, ApJ 116, 211). La pareja eclipsante se mueve con una tercera estrella alrededor del centro de masas, así que la luz llega antes o después en

    τ = A [ (1 − e²) / (1 + e cos ν) · sin(ν + ω) + e sin ω ],     A = a₁₂ sin i / c

ν es la anomalía verdadera de la órbita del tercer cuerpo (período P₃, periastro T₃) a partir de la ecuación de Kepler M = E − e sin E. Se ajusta el modelo T = T₀ + P E + τ; de él sale la función de masa f(m₃) = (a₁₂ sin i)³ / P₃² (UA, años, masas solares).

**Movimiento apsidal** (Giménez & García-Pelayo 1983, Ap&SS 92, 203; primer orden en e, i ≈ 90°). Con ω = ω₀ + ω̇ E y el período anomalístico Pₐ = Pₛ / (1 − ω̇/360°):

    T_I  = T₀ + Pₛ E − (Pₐ/π) e cos ω
    T_II = T₀ + Pₛ E + Pₐ/2 + (Pₐ/π) e cos ω

Los mínimos primarios y secundarios oscilan en sentidos opuestos; el período apsidal es U = 360° / ω̇ ciclos. Para e mayor de ~0,1 importan los términos de orden superior.

## Curva de luz de una binaria eclipsante {#methods-eclipsing-binary-light-curve}
Dos esferas en una órbita kepleriana (la aproximación esférica de EBOP / JKTEBOP, Popper & Etzel 1981, AJ 86, 102; Southworth 2013, A&A 557, A119). Con los radios r₁, r₂ en unidades del semieje mayor, la separación proyectada es

    d = (1 − e²) / (1 + e cos ν) · √(1 − sin² i sin²(ν + ω))

Cada estrella tiene oscurecimiento al limbo cuadrático I(μ) = I₀ [1 − u₁(1 − μ) − u₂(1 − μ)²], y J = I₀,₂ / I₀,₁ es el cociente de brillos superficiales. La luz perdida cuando un disco cubre al otro es la integral de I sobre la parte cubierta, calculada con cuadratura de Gauss–Legendre:

    ΔF = ∫ I(x) · 2x θ(x) dx,     θ(x) = arccos[(x² + d² − r_delante²) / (2xd)]

El flujo del modelo, F = (1 − L₃)(F₁ + F₂ − ΔF)/(F₁ + F₂) + L₃ (1 fuera de los eclipses, la tercera luz L₃ como fracción del total), se ajusta por mínimos cuadrados (y por MCMC si se pide). No se modelan la reflexión, la deformación de marea ni el oscurecimiento gravitatorio; las binarias cercanas necesitan PHOEBE o WD (botones de exportación).

## Velocidades radiales y órbitas espectroscópicas {#methods-radial-velocities-spectroscopic-orbits}
**Correlación cruzada** (Tonry & Davis 1979, AJ 84, 1511). Espectro y plantilla en una malla de ln λ, donde una velocidad es un desplazamiento: Δln λ = v/c. La correlación normalizada C(v) tiene su pico en la velocidad; una parábola por los tres puntos más altos la da, y el error sigue a Zucker (2003, MNRAS 342, 1291):

    σᵥ² = −[N · C''/C · C² / (1 − C²)]⁻¹

**TODCOR** (Zucker & Mazeh 1994, ApJ 420, 806) correlaciona con dos plantillas a dos desplazamientos a la vez:

    R(s₁, s₂) = [C₁(s₁) + α C₂(s₂)] / √(1 + 2α C₁₂(s₁ − s₂) + α²)

con α, el cociente de luz, resuelto en cada punto. El R más alto da ambas velocidades.

**Función de ensanchamiento** (Rucinski 1992, AJ 104, 1968; 2002, AJ 124, 1746). El espectro observado es la plantilla convolucionada con B(v): un sistema lineal P = D · B, resuelto por mínimos cuadrados (descomposición en valores singulares). Cada estrella aparece como un perfil de rotación (Gray 2005, ec. 18.14) con su velocidad, v sin i y fracción de luz.

**Órbita** (de una y de dos líneas):

    v(t) = γ + K [cos(ν + ω) + e cos ω],     M = 2π(t − T)/P = E − e sin E

ajustada por mínimos cuadrados con √e cos ω y √e sin ω como parámetros (estable cerca de órbitas circulares); en una binaria de dos líneas ambas estrellas comparten P, T, e, γ, y ω₂ = ω₁ + 180°. Magnitudes derivadas (Hilditch 2001, ec. 2.52–2.53):

    f(m) = P K³ (1 − e²)^{3/2} / 2πG,     m₁ sin³ i = P (K₁ + K₂)² K₂ (1 − e²)^{3/2} / 2πG
    a sin i = P (K₁ + K₂) √(1 − e²) / 2π

Con la inclinación y los radios de la curva de luz: masas, radios R = r · a y log g, a partir de las mismas extracciones aleatorias de cada dato (como JKTABSDIM), de modo que los errores se propagan con sus correlaciones.

## Órbita de una binaria visual {#methods-visual-binary-orbit}
Forma de Thiele–Innes (Heintz 1978, Double Stars). Con la anomalía excéntrica E de la ecuación de Kepler:

    X = cos E − e,    Y = √(1 − e²) sin E
    x = ρ cos θ = A X + F Y,    y = ρ sin θ = B X + G Y

Para P, T y e fijos, las constantes A, B, F, G son lineales: se resuelven exactamente. P, T, e se buscan en una malla y luego los siete elementos se refinan juntos con Levenberg–Marquardt. Los elementos de Campbell a, i, Ω, ω salen de A, B, F, G; la masa total, de la tercera ley de Kepler: M₁ + M₂ = a³ / (ϖ³ P²) (a y la paralaje ϖ en segundos de arco, P en años).

## Espectros: longitud de onda, atmósfera, telúricas, separación {#methods-spectra-wavelength-atmosphere-telluric}
**Solución de longitud de onda**: las líneas del arco se centran con un ajuste gaussiano; λ(x) = Σ cₖ xᵏ se ajusta con recorte sigma, como IRAF identify. En espectros echelle la ecuación de la red hace de m·λ una función suave del píxel x y del orden m, así que una sola superficie Σ cᵢⱼ xⁱ mʲ cubre todos los órdenes (IRAF ecidentify; Baranne et al. 1996).

**Parámetros atmosféricos** (el enfoque de iSpec / SME, sobre una malla precalculada): el espectro observado se modela como

    F(λ) = Pₖ(λ) · [S(Teff, log g, [Fe/H]) ∗ G_rot(v sin i) ∗ G_inst(R)](λ / (1 + v/c))

S interpolado en la malla PHOENIX (Husser et al. 2013), Pₖ un polinomio de grado bajo por tramo de longitud de onda que absorbe la respuesta del instrumento; ajustado con Levenberg–Marquardt.

**Corrección telúrica**: la absorción escala como la profundidad óptica, así que T_ciencia = T_estándar^s con s ≈ el cociente de masas de aire; s = Σ ln F ln T / Σ (ln T)² dentro de las bandas telúricas, y también se ajusta un desplazamiento subpíxel.

**Separación espectral** (González & Levato 2006, A&A 448, 283): el espectro de cada estrella es la media de los espectros observados, desplazados a su sistema en reposo, tras restar el espectro actual de la otra estrella; se repite hasta converger.

## Fotometría {#methods-photometry}
**Fotometría de apertura**: el cielo es el nivel con recorte sigma de un anillo; F = suma en la apertura − N_ap · cielo; su error es la ecuación del CCD con el ruido del cielo σ_cielo medido en el anillo (Merline & Howell 1995, Exp. Astron. 6, 163):

    σ_F² = F / ganancia + N_ap (1 + N_ap / N_cielo) σ_cielo²

**Extinción**: mᵢⱼ = cⱼ + k Xᵢ (una constante por estrella de comparación, un solo k), la recta de Bouguer.

**Transformación** (la convención de la AAVSO para dos filtros A, B): (A − B) = T_ab (a − b) + Z_ab, (B − b) = T_b (A − B) + Z_b, con a, b las magnitudes instrumentales; ajustada por mínimos cuadrados en un campo estándar.
