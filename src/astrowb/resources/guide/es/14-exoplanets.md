# Exoplanetas
La ventana **Exoplanetas** ajusta un modelo exacto de tránsito a una curva de luz guardada. Se abre desde su bloque en la página de inicio o el menú Ventana. Las etapas están en la barra de la izquierda: Datos, Estrella, Planetas, Modelo, Ajuste, Incertidumbre, Resultados. La vista principal muestra el tránsito con el modelo ajustado y sus residuos, una tabla de los parámetros ajustados y una línea de texto con el resultado.

## Datos {#exoplanets-data}
**Abrir curvas de luz…** toma uno o más archivos de curva de luz: los `.lc.ecsv` que escribe la ventana Fotometría, o una tabla CSV / de texto con tiempo, flujo y error (al menos 10 filas). La tabla lista cada archivo con su número de puntos, su duración en días y su escala de tiempo; elegir una fila elige la curva de luz que se ajusta y muestra su último ajuste. Un archivo que no se puede leer se nombra, con el motivo, en el texto bajo el gráfico. Para el archivo de ExoClock hacen falta tiempos en BJD_TDB (véase Resultados).

## Estrella {#exoplanets-star}
El oscurecimiento del limbo de la estrella sigue una ley cuadrática con los coeficientes **u1** y **u2** (por defecto 0,4 y 0,2). Quedan fijos mientras no se marque **Ajustar el oscurecimiento del limbo**; una sola noche rara vez los decide, así que déjelos fijos y tome de una tabla los valores para la temperatura de la estrella y el filtro.

## Planetas {#exoplanets-planets}
Valores iniciales del tránsito: **Período (d)** (fijo: un solo tránsito no lo fija), **Mitad del tránsito** y **Rp/R★** (ambos *auto* por defecto: el centro y la raíz cuadrada de la profundidad del descenso de la curva suavizada), **a/R★** y el **Parámetro de impacto**. El ajuste refina la mitad del tránsito, Rp/R★, a/R★ y b a partir de ellos. El período y una primera estimación de los demás se pueden tomar del NASA Exoplanet Archive en la ventana Planificación (**Añadir con efeméride**) o en la ventana Fotometría; esta ventana no los consulta.

## Modelo {#exoplanets-model}
**Corregir frente a** lista las magnitudes frente a las que se ajustan, junto con el tránsito, las tendencias lentas que no son del planeta: airmass, fwhm, sky, x, y, separadas por comas (por defecto `airmass`; vacío: ninguna). La curva de luz debe contener esas columnas; la ventana Fotometría las escribe.

## Ajuste {#exoplanets-fit}
**Ajustar el tránsito** ajusta la curva de luz elegida en segundo plano; al terminar, el resultado sustituye al gráfico, la tabla y el texto. Detener está en la barra de estado.

## Incertidumbre {#exoplanets-uncertainty}
Los errores de mínimos cuadrados pueden ser demasiado pequeños si los residuos están correlacionados en el tiempo. **Tener en cuenta el ruido rojo (errores × β)** multiplica los errores por β, el factor en que la dispersión de los residuos no baja como se espera al agrupar en el tiempo. **Pasos MCMC** ejecuta un muestreo posterior tras el ajuste (termina antes si converge; 0: ninguno) y da errores asimétricos para la mitad del tránsito, Rp/R★, a/R★ y b; si el texto dice *not converged*, use más pasos.

## Resultados {#exoplanets-results}
El texto y la tabla dan la mitad del tránsito (BJD), la profundidad (ppt y mmag), las duraciones T14 y T23, a/R★, b, la inclinación, la densidad estelar, el χ² reducido, el RMS de los residuos y β. **Archivo ExoClock…** escribe el archivo de subida del proyecto de tiempos de tránsito ExoClock (tiempo en BJD_TDB, flujo normalizado, error) y **Archivo ETD…** el de la Exoplanet Transit Database (fecha juliana, magnitud, error). Una curva de luz cuyos tiempos no están en BJD_TDB no se puede escribir para ExoClock: dé la posición del objetivo al medir.
