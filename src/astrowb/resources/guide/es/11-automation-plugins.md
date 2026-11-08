# Automatización y complementos
Una **automatización** encadena pasos en su propio flujo de trabajo — «calibrar las tomas de una carpeta → medir la curva de luz → determinar el mínimo → O-C» — y lo ejecuta de una vez. Los **complementos** (plugins) añaden sus propios pasos. Se abre en una ventana propia (su bloque en la página de inicio o la barra lateral), con sus propios menús.

## Plantillas listas
La página **Automatización** lista las plantillas listas (marcadas con «plantilla») y sus propias automatizaciones:

- **Noche de una binaria eclipsante** — una secuencia del anochecer al amanecer y después calibración, estrellas de comparación, curva de luz, instante del mínimo (Kwee–van Woerden) y O-C.
- **Tránsito de exoplaneta** — lo mismo con el ajuste trapezoidal para el centro del tránsito.
- **Calibración y apilado al final de la noche** — darks y bias al amanecer y después másteres, calibración y una imagen apilada.
- **Noche de espectroscopía → VR → órbita** — cada toma de rendija larga reducida con el arco, velocidades radiales frente a una plantilla y una órbita de línea simple.
- **Estrella variable: curva de luz → periodo** — curva de luz y búsqueda del período con Lomb–Scargle.

Seleccione una para ver su descripción y sus pasos.

## Ejecutar una automatización
1. Rellene las **Entradas** de la derecha (carpetas y archivos tienen un botón **…**). Solo se pide lo que ningún paso puede producir: por ejemplo, la carpeta de tomas brutas y la posición del objetivo.
2. Pulse **Ejecutar**. Cada paso se ejecuta como una tarea normal en el panel de tareas y queda registrado en el proyecto; el siguiente empieza cuando termina el anterior. La línea bajo el botón dice qué paso se está ejecutando.
3. Al terminar, se muestran debajo los resultados del último paso (p. ej. el instante del mínimo y O-C). Si un paso falla, la automatización se detiene ahí y se muestra el error.

## La parte de observación
Las plantillas con una secuencia de observación tienen **A la página Observar**: rellena el objetivo, el inicio y el fin (p. ej. dusk y dawn) y las filas de exposición. Añada las coordenadas, revise los tiempos de exposición e iníciela allí. Marque **Procesar tras la secuencia** antes de enviarla: cuando la secuencia termina (también si el tiempo la detiene antes, siempre que se hayan tomado imágenes), la automatización se ejecuta sola sobre la carpeta de la secuencia. Con un observatorio remoto, las tomas se copian primero a este ordenador y luego se procesan.

## Crear la suya
1. **Nuevo** empieza una automatización vacía (o parta de una plantilla y cámbiela).
2. Elija un paso en la lista bajo **Pasos, en orden** y pulse **Añadir paso**. **Quitar**, **Arriba** y **Abajo** cambian el orden.
3. Seleccione un paso para ver sus **ajustes**:
   - las líneas que empiezan por **←** son sus entradas. Por defecto, una entrada toma los datos del mismo nombre producidos por un paso anterior (o escritos en Entradas). Escriba otro nombre para enlazarla, p. ej. `images` ← `calibrated` en el paso de apilado;
   - `nombre.campo` toma un campo de un resultado, o ese campo de cada fila: p. ej. `time` ← `rvs.bjd` en la órbita;
   - un texto con llaves forma un nombre de archivo, p. ej. `{output_dir}/{item}_1d.fits`;
   - las demás líneas son los parámetros del paso; escriba números, `true`/`false`, `null`, listas como `[1, 2]` o texto.
4. **Guardar como…** la guarda con un nombre en su carpeta de configuración (`automations`), donde aparecerá en la lista la próxima vez.

Las automatizaciones son archivos JSON sencillos, así que pueden compartirse: copie el archivo en la carpeta `automations` de otro usuario.

## Complementos
**Qué son:** un complemento es una pequeña herramienta que usted mismo añade a la aplicación — para un cálculo que la aplicación no tiene o que solo necesita su grupo. Es un único archivo Python. Cuando está en la carpeta de complementos aparece en el menú **Complementos**, abre un pequeño formulario para sus entradas, se ejecuta como cualquier paso integrado (en segundo plano, con progreso y Cancelar, registrado en el proyecto) y puede usarse como paso de una automatización.

**No hace falta programar para probarlos.** **Complementos → Instalar los complementos de ejemplo** añade tres listos:
- **plugin.exposure_time** — cuántos segundos exponer para una relación señal/ruido deseada, a partir de la magnitud de la estrella, su punto cero, el cielo, el ruido de lectura y la apertura (ecuación CCD). Solo números, sin archivo.
- **plugin.sky_level** — el nivel del cielo y su ruido en una imagen FITS (para comparar noches o comprobar flats).
- **plugin.light_curve_summary** — puntos, intervalo de tiempo, dispersión en milimagnitudes y el punto más profundo de un CSV de curva de luz.

Elija uno en el menú **Complementos**, rellene el formulario y pulse Aceptar; el resultado se abre en una ventana. Un complemento con un error aparece como «No se pudo cargar» con el motivo; nunca detiene la aplicación. Los complementos se ejecutan con sus permisos, como cualquier programa que instale: use solo archivos de confianza.

## Escribir su propio complemento
Abra **Complementos → Abrir la carpeta de complementos**, copie un ejemplo, cámbiele el nombre y modifíquelo. Este es el ejemplo del cielo completo:

```python
from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level and noise of a FITS image (stars clipped)."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "noise": float(std)}}
```

- El texto entre comillas tras `@step` es el nombre de la herramienta; debe empezar por `plugin.`.
- `inputs` es lo que pide el formulario (rutas de archivo o números); las palabras siguientes (`sigma=3.0`) son ajustes con su valor por defecto.
- La función los recibe como `inputs["image"]` y `params["sigma"]` y devuelve un diccionario de resultados (números, texto, listas).
- En trabajos largos llame de vez en cuando a `ctx.progress(0.5, "mensaje")` y dentro de los bucles a `ctx.check()` para que Cancelar funcione.
- numpy, scipy, astropy, photutils y matplotlib siempre están disponibles. Guarde el archivo; el menú Complementos lo encontrará la próxima vez que se abra.
