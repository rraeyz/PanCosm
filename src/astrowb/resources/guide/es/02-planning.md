# Planificación
La página **Planificar** indica cuándo pueden observarse sus objetivos esta noche y qué eclipses o tránsitos ocurren durante la noche.

## Su lugar
Introduzca la **latitud** (grados, norte positivo), la **longitud** (grados, este positivo) y la **altura** (metros) del observatorio. Se recuerdan. También se usan para la corrección baricéntrica de las velocidades radiales y para los crepúsculos.

## La noche y el límite de altura
- **Noche que empieza el:** la fecha de la tarde en que empieza la noche.
- **Altura mínima (°):** por debajo, un objetivo se considera no observable (árboles, edificios, aire denso). Lo habitual es 20–30°.

## Añadir objetivos
Escriba un **nombre** (se busca en SIMBAD, p. ej. `HAT-P-32`, `V523 Cas`, `M 42`) o unas **coordenadas** (`02:04:10 +46:41:16` o grados decimales) y pulse **Añadir**.

**Añadir con efemérides** busca el nombre en el catálogo **VSX** de la AAVSO (estrellas variables) o en el **NASA Exoplanet Archive** (planetas como `HAT-P-32 b`) y rellena coordenadas, periodo, época y duración, de modo que los eclipses o tránsitos de la noche aparecen enseguida. En binarias eclipsantes la época es el mínimo primario de VSX (HJD; difiere de BJD en segundos) y se marca *Secundario*; en estrellas pulsantes solo se muestra el periodo. Necesita internet.

- Los nombres encontrados una vez se guardan en caché, así que más tarde la planificación funciona también sin internet.
- **Quitar lo seleccionado** elimina filas de la tabla.

## Eclipses y tránsitos
Para binarias eclipsantes y exoplanetas, rellene las columnas de la tabla de objetivos:

- **T0 (BJD):** un instante de mínimo primario o de centro de tránsito (BJD_TDB).
- **Período (d)** y **Duración (d)** del eclipse o tránsito.
- **Secundario:** márquelo para listar también los mínimos secundarios (en fase 0,5).

El plan lista entonces cada evento de la noche con su inicio, centro y final en UTC y si es **observable** (*sí*, *en parte* o en absoluto) según el límite de altura y la oscuridad.

## Leer el gráfico
**Planificar la noche** dibuja la altura de cada objetivo frente al tiempo UTC durante toda la noche:

- el sombreado azul se oscurece paso a paso desde la puesta de sol por los crepúsculos civil (−6°), náutico (−12°) y astronómico (−18°); la parte más oscura es la noche astronómica;
- la curva gris discontinua es la **Luna**, con su fracción iluminada en la leyenda;
- la línea roja punteada es su altura mínima;
- el eje derecho da la **masa de aire**; la fotometría es mejor por debajo de masa de aire 2 (altura superior a 30°);
- los triángulos rojos marcan el centro de cada eclipse o tránsito sobre la curva del objetivo.

La línea bajo el gráfico da el inicio y el final de la noche astronómica en UTC y el número de eventos. Cerca de los polos en verano puede no haber noche astronómica; entonces la línea dice **sin noche astronómica**.

## Del plan a la observación
**Crear un programa** (después de *Planificar la noche*) convierte la noche en un programa para varios objetivos: primero cada eclipse o tránsito observable, con 30 minutos de línea base antes y después (si dos se solapan, gana el objetivo que esté más arriba en su lista); el resto del tiempo oscuro en bloques de una hora, cada uno para el objetivo que se mantenga más alto sobre su límite de altura. **Enviar a la página Observar** pasa cada bloque a la secuencia, con su inicio y su final; las filas de exposición que ajuste allí se usan para todos los objetivos.

Use los tiempos del plan como **Inicio** y **Fin** de una secuencia en la página Observar (o escriba `dusk` y `dawn`), o parta de una plantilla de automatización como *Noche de una binaria eclipsante* o *Tránsito de exoplaneta*.
