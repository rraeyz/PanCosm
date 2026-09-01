# Curvas de luz y O-C
La página **Curvas de luz y O-C** tiene tres pestañas: **Búsqueda de períodos**, **Análisis de frecuencias** y **Diagrama O-C**.

## Búsqueda de períodos
La curva de luz medida en la página Fotometría se usa automáticamente; o bien **Cargar CSV (tiempo, flujo)…**.

- **Lomb–Scargle** — ajusta una onda sinusoidal en cada período de prueba y elige la que explica la mayor parte de la variación. Para variaciones sinusoidales: estrellas pulsantes, rotación y manchas.
- **BLS** (mínimos cuadrados con caja) — ajusta una caída corta en forma de caja en cada período de prueba. Para tránsitos de planetas y eclipses de tipo Algol.
- **PDM** (minimización de la dispersión de fase) — no supone ninguna forma: pliega los datos con cada período de prueba y elige aquel en que los puntos se superponen con más orden. Para cualquier forma de curva de luz, p. ej. binarias eclipsantes con dos mínimos.
- **ANOVA** (análisis de varianza multiarmónico) — ajusta una curva de dos armónicos en cada período de prueba y la evalúa estadísticamente. Para formas suaves no sinusoidales como RR Lyrae y cefeidas.

Cómo funciona cada método, con sus fórmulas y referencias: **Matemáticas de los métodos** (el último capítulo de esta guía). Al pasar el ratón sobre la lista de métodos aparece un resumen de una línea de cada uno.

**TESS y Kepler:** escriba el nombre de una estrella (o un número TIC / KIC), elija TESS, Kepler o K2 y pulse **Descargar**. Las curvas de luz propias de la misión (flujo PDCSAP, corregido de tendencias instrumentales) vienen del archivo MAST; los puntos marcados se descartan, cada sector o trimestre se normaliza y todos se unen, con tiempos en BJD_TDB. Se guardan en la carpeta de configuración, así que una segunda descarga es instantánea. Luego busque el período como se indica abajo.

**ZTF y AAVSO:** elija ZTF (curvas de luz de la Zwicky Transient Facility desde IRSA, buscadas por la posición de la estrella) o AAVSO (observaciones de la AAVSO International Database) y pulse **Descargar**. Los archivos exportados de AAVSO, ZTF o ASAS-SN Sky Patrol también se abren con **Cargar CSV…**. Se conserva una banda (la de más puntos), se descartan los límites superiores y los puntos marcados, las magnitudes pasan a flujo relativo y los tiempos a BJD_TDB, de modo que estos datos se pueden unir con TESS o con los suyos.

Fije el **Período más corto** y el **Período más largo** (el más largo es, por defecto, la mitad del intervalo de tiempo) y pulse **Buscar**. Se muestran el periodograma y la curva de luz plegada con el mejor período. Revise la curva plegada: la mitad o el doble del período es un alias frecuente, sobre todo en binarias eclipsantes con mínimos iguales.

**Intervalos de fase** dibuja la curva media sobre los puntos plegados. **Editar la curva de luz:** *Quitar valores atípicos (σ)*, *Agrupar en tiempo (min)*, *Borrar puntos con un clic* (luego haga clic en un punto de la gráfica), *Flujo ↔ magnitud* y *Deshacer ediciones*. La búsqueda de periodo y el análisis de frecuencias usan la curva editada. *Quitar valores atípicos* compara cada punto con sus vecinos en el tiempo (y, una vez hallado un periodo, en la curva plegada), así que los eclipses y las pulsaciones se conservan. **Errores:** si la curva de luz los tiene (de la página Fotometría, de las descargas de TESS / Kepler / ZTF / AAVSO o de una tercera columna del CSV), se dibujan como barras de error, siguen cada edición (puntos atípicos, agrupado —el error de cada media—, puntos borrados, flujo ↔ magnitud) y ponderan las búsquedas Lomb–Scargle y BLS con 1/σ²; **Guardar** los escribe como tercera columna.

## Análisis de frecuencias
Para estrellas pulsantes con varios modos (δ Scuti, γ Dor, β Cep), como Period04. Indique la **frecuencia máxima** (ciclos por día) y pulse **Analizar frecuencias**:

1. Se calcula el espectro de amplitud (transformada de Fourier de Deeming para muestreo irregular).
2. Su pico más alto se ajusta como sinusoide, se elimina (**preblanqueo**) y se buscan de nuevo los residuos.
3. Cada nueva frecuencia se ajusta junto con las anteriores (frecuencias, amplitudes y fases libres).
4. Se detiene cuando la **S/R** del siguiente pico (su amplitud / amplitud residual media en ±1 c/d) queda bajo el límite; el criterio de Breger es 4.

La tabla da cada frecuencia, periodo, amplitud y fase con sus errores (Montgomery & O'Donoghue 1999) y la S/R. Las gráficas muestran el espectro original, el espectro residual con el límite de S/R y la **ventana espectral**: un pico de la ventana en 1 c/d significa que los huecos diarios crean alias a ±1 c/d de cada frecuencia real; compare una frecuencia con su alias antes de creerla. Con **Mostrar también el espectro CLEAN** se dibuja el espectro sin esos alias (CLEAN, Roberts, Lehár y Dreher 1987): la frecuencia real se queda y sus alias desaparecen.

Los **tiempos de máximo** se miden en cada ciclo cubierto (parábola alrededor de cada máximo de la curva ajustada); marque *Los valores son magnitudes* si la curva está en magnitudes. **Enviar los máximos al diagrama O-C** los añade a la lista O-C.

## Diagrama O-C
El O-C (observado menos calculado) muestra cómo se apartan los instantes de mínimo de un período constante.

1. Escriba o pegue los **instantes de mínimo**, uno por línea: `tiempo [error] [I/II] [fuente]` — p. ej. `2459876.43215 0.00021 I TESS`. O **Cargar archivo…**. Tiempos en BJD o HJD; no los mezcle.
2. Indique un **T0 de referencia** y el **Período (d)**: con ellos se calcula la época de cada mínimo.
   O escriba el nombre de la estrella en **Estrella** y pulse **Buscar**: T0 y el período vienen de AAVSO VSX. Un T0 vacío es el primer mínimo primario.
3. Elija **Efemérides lineales** o **Cuadrática (cambio de período)** y pulse **Ajustar y dibujar O-C**. **Exportar resultados (CSV / LaTeX)…** escribe los valores ajustados con errores 1σ, redondeados como en un artículo, y un pie que nombra el modelo.

El resultado da el nuevo T0 y P con sus errores; el ajuste cuadrático da además el ritmo de cambio del período dP/dt en segundos por año, y el χ² reducido. Los mínimos primarios se dibujan como círculos y los secundarios como cuadrados; el gráfico inferior muestra los residuos.

## Tercer cuerpo y movimiento apsidal
- **Tercer cuerpo (tiempo de luz):** la pareja eclipsante orbita el centro de masas con una tercera estrella, por lo que sus eclipses llegan antes y después a lo largo de una órbita (Irwin 1952). El ajuste da el período del tercer cuerpo P3 (años), la semiamplitud A (minutos), la excentricidad e, el argumento ω y la función de masa f(m3), el límite inferior de la masa de la tercera estrella. Necesita al menos 8 mínimos repartidos en más de un P3.
- **Movimiento apsidal:** en una órbita excéntrica la línea de los ápsides gira, de modo que los mínimos primarios y secundarios oscilan en sentidos opuestos. Dé ambos tipos (I y II); el ajuste da e, ω en la época 0, dω/dE (grados por ciclo) y el período apsidal U (años). El modelo es de primer orden en e (bueno para e ≲ 0,1).
- **Incertidumbres MCMC:** en estos dos modelos, la casilla ejecuta una cadena de Markov (emcee) tras el ajuste: intervalos del 68 % de cada parámetro, e y ω incluidos, y de f(m3) y U, honestos cuando los parámetros dependen unos de otros (como en OCFit). Tarda unos segundos; más pasos dan errores más estables. Las efemérides lineal y cuadrática son problemas lineales: sus errores de mínimos cuadrados ya son exactos y la casilla está desactivada.

## Leer un diagrama O-C
- Una recta inclinada: el período es ligeramente incorrecto — el ajuste lo corrige.
- Una parábola: el período cambia (transferencia de masa, actividad magnética, pérdida de momento angular).
- Una onda: efecto de tiempo de luz de un tercer cuerpo, o movimiento apsidal (en sistemas excéntricos, los mínimos primarios y secundarios se mueven en sentidos opuestos).
- Los errores importan: los mínimos sin error reciben el mismo peso.
