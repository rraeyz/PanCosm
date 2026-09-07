# Órbitas y modelos
La página **Órbitas y modelos** ajusta un modelo físico a la curva de luz de una binaria eclipsante separada o de un planeta en tránsito, y lo combina con una órbita espectroscópica para obtener dimensiones absolutas. Modelos se abre en una ventana propia (su bloque en la página de inicio o la barra lateral), con su propio Editar → Deshacer / Rehacer para los parámetros y los ajustes.

## El modelo
Dos esferas con oscurecimiento al limbo en una órbita kepleriana. Sirve para binarias separadas y tránsitos. Las binarias cercanas, deformadas o de contacto necesitan un modelo de Roche: en ese caso exporte a PHOEBE o WD.

## Ajustar una curva de luz
1. Elija la **Curva de luz** (CSV de la página Fotometría u otra fuente; una columna de tiempo y flujo relativo o magnitudes).
2. Indique el **Período (d)** y el **Mínimo primario (BJD)** (de la página O-C).
3. Valores iniciales: **r1 + r2** (suma de los radios como fracción de la separación a), **k = r2 / r1**, **Inclinación (°)**, **Cociente de brillo superficial J**, **Tercera luz**, términos de excentricidad y el oscurecimiento al limbo **u1, u2** de cada estrella. Marque los parámetros que se ajustan.
4. **Ajustar**: el resultado da i, r1, r2, el cociente de luz L2/L1 y e con errores, el rms y χ²ᵣ. El gráfico muestra los datos, el modelo y los residuos (O−C) frente a la fase. **Exportar resultados (CSV / LaTeX)…** escribe todos los parámetros (libres con errores, fijos marcados, valores MCMC si se muestreó), las magnitudes derivadas y absolutas, como tabla para un artículo.

## Incertidumbres MCMC
Los errores de un ajuste por mínimos cuadrados suponen parámetros independientes; en binarias eclipsantes y tránsitos no lo son (inclinación, radios y oscurecimiento al limbo se compensan entre sí). Marque **Incertidumbres MCMC** para muestrear la distribución posterior alrededor del ajuste (muestreador de conjunto invariante afín, emcee) con el número de **pasos** que elija: el resultado da cada parámetro libre como mediana −/+ sus percentiles 16/84, y **Posterior…** muestra el gráfico de esquinas (histogramas y pares), donde las correlaciones se ven de un vistazo. Tarda alrededor de un minuto por cada 1000 puntos con 2000 pasos; se ejecuta en segundo plano y puede cancelarse.

## Dimensiones absolutas
Cuando la página Espectroscopía tiene una órbita de doble línea (K1, K2), marque **Dimensiones absolutas con la órbita de doble línea**: se calculan las masas M1, M2, los radios R1, R2 (unidades solares), la separación a y el log g de ambas estrellas con propagación de errores.

## PHOEBE y otros modelos
- **Ajustar y exportar para PHOEBE…** escribe la curva de luz (`lc.txt`), las velocidades radiales si las hay (`rv1.txt`, `rv2.txt`) y los parámetros ajustados con los nombres de PHOEBE (`start.json`) como punto de partida de un modelo de Roche.
- **Ajustar y exportar para WD…** escribe las observaciones en las columnas del programa Wilson-Devinney (`lc.dat`: tiempo, flujo, peso) y `wd_parameters.txt` con los valores ajustados con los nombres de WD: PERIOD, HJD0, XINCL, E, PERR0 (radianes), EL3 y — con una órbita de doble línea — RM (q), los potenciales de superficie PHSV y PCSV calculados a partir de los radios, VGA y A. Escríbalos en el archivo de entrada de su versión de WD; las temperaturas, los albedos y el oscurecimiento gravitatorio los fija usted.
- **Ajustar y exportar para ExoClock / ETD…** (tránsitos) escribe los archivos de los dos proyectos de cronometraje de tránsitos — `<nombre>_ExoClock.txt` (BJD_TDB, flujo relativo, error) y `<nombre>_ETD.txt` (BJD_TDB, magnitud, error) — y `<nombre>_summary.txt` con el tiempo central de este tránsito Tc ± error (la época cercana a los datos, a partir de T0 y el periodo ajustados), profundidad, duración T14, Rp/R*, a/R* e inclinación. Introduzca T0 y el periodo de la consulta de efemérides de la página Plan, ajuste T0 (y la forma) y súbalos; los datos de la observación (observador, filtro, exposición) se introducen en los formularios de los proyectos. Comprobado con un tránsito real de WASP-12 b (sector 20 de TESS, el archivo de píxeles medido aquí, un tránsito de ±3,6 h): Tc a 47 s del mismo tránsito en la curva SPOC de la NASA y a 42 ± 70 s de la efeméride de todo el sector; profundidad 1,59 % (SPOC 1,58 %).
- **Comparar con una curva modelo…** dibuja sobre sus datos una curva calculada en otro programa (dos columnas: fase o tiempo, y flujo).

## Órbita de binaria visual
La pestaña **Órbita de binaria visual** ajusta los siete elementos orbitales de una estrella doble resuelta a las medidas de posición de la compañera.
1. Escriba o **cargue** las medidas, una por línea en el orden del WDS: época (año), ángulo de posición θ (grados, de norte a este), separación ρ (segundos de arco) y, opcionalmente, el error de ρ (″) y de θ (°). Las líneas que empiezan con `#` se omiten. Hacen falta al menos 7 medidas (siete elementos); muchas más es mejor.
2. Opcionalmente limite el **período más corto** y el **más largo** (años); por defecto se busca entre 0,5 y 10 veces el tiempo que cubren las medidas.
3. Indique la **paralaje** (mas) para obtener la masa total M1 + M2 = a³ / (ϖ³ P²) por la tercera ley de Kepler.
4. **Ajustar la órbita**: se prueban todos los períodos del rango, todas las fases del periastro y excentricidades de 0 a 0,95 con la solución lineal de Thiele–Innes; después se refinan juntos los siete elementos (Levenberg–Marquardt). La tabla da P, T, e, a, i, Ω, ω con errores 1σ de la covarianza del ajuste (escalada por el χ² reducido), el rms de las separaciones y la masa. El gráfico muestra la órbita aparente (este a la izquierda, como en el cielo), las medidas y sus líneas O−C.

Sin velocidades radiales, Ω y ω pueden girarse ambos 180°: el programa da Ω entre 0 y 180°. Compruebe que un rango de períodos corto no oculte un período real más largo: compare χ²ᵣ para distintos rangos. Método: Heintz (1978), *Double Stars*; convenciones de los catálogos de órbitas del USNO (Fifth Catalog: Hartkopf, Mason & Worley 2001, AJ 122, 3472; continuado como Sixth Catalog, ORB6).
