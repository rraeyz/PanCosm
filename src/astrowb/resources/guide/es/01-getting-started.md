# Primeros pasos
La aplicación cubre todo el trabajo de observación en una sola ventana: elegir objetivos, planificar la noche, observar, calibrar, medir, modelar e informar. Puede empezar en cualquier paso con los datos que ya tenga.

Cada página y pestaña de trabajo tiene arriba una línea plegada **Flujo de trabajo** que nombra el paso siguiente. Al pulsarla se ve el orden de trabajo habitual (la tarea de IRAF entre paréntesis cuando la hay), cada paso marcado como hecho (✓), omitido (–) o siguiente (▶), y qué hacer en el paso siguiente. Es una guía, nunca un bloqueo: empiece en el paso donde estén sus datos —un espectro ya extraído solo necesita sus longitudes de onda, una curva de luz de un archivo no necesita fotometría— y omita lo que sus datos no necesiten.

## El primer inicio
La primera vez que se abre, la aplicación muestra una breve ventana de bienvenida en inglés con tres opciones:

- **Language** (idioma) — el idioma de la interfaz. Se aplica de inmediato; más adelante puede cambiarlo en **Configuración → Idioma**.
- **Computations run on** (cálculos en) — *Automatic* usa la tarjeta gráfica cuando es más rápida que el procesador (recomendado), *Graphics card* la usa siempre, *Processor (CPU) only* nunca.
- **Look** (aspecto) — *Dark* (negro azulado, el predeterminado) o *Light* (claro).

Pulse **Start**. Las opciones se guardan y no se vuelven a preguntar. A continuación viene un **Recorrido rápido** de un minuto; puede saltarlo y abrirlo de nuevo desde **Ayuda → Recorrido rápido**.

## Su primera noche (datos de práctica)
Un ejercicio completo con datos simulados cuya respuesta se conoce: desde las imágenes brutas hasta el instante del mínimo de una binaria eclipsante.

1. **Ayuda → Datos de práctica para una primera noche…** y elija una carpeta vacía. Aparece una carpeta `raw` con 7 bias, 7 darks (60 s), 7 flats V y 48 tomas de ciencia V de una binaria durante un eclipse primario, y `truth.json` con las respuestas correctas.
2. **Calibrar:** elija la carpeta `raw` y pulse **Explorar**: la tabla muestra 7 bias, 7 darks, 7 flats y 48 tomas de ciencia, sin que falte nada. Elija una carpeta de salida (p. ej. `cal`) y pulse **Calibrar**.

![Página Calibrar después de Explorar](images/es/first-night-calibrate.png)

3. **Fotometría:** **Elegir imágenes…** y seleccione los `light_V_*.fits` calibrados. Pulse **Encontrar las imágenes malas (nubes, foco, trazas)**: todas las tomas son buenas. Haga clic en la estrella del centro de la imagen (la binaria, en x = 100, y = 80) y luego en **Sugerir estrellas de comparación** (o haga clic en las otras tres estrellas). Escriba la posición `02:04:10.3 +46:41:16` en *AR Dec del objeto* para que los tiempos estén en BJD_TDB y pulse **Medir curva de luz**: aparece un eclipse de unos 45 % de profundidad.
4. Deje **Binaria eclipsante: método de Kwee–van Woerden** (la opción por defecto) y pulse **Instante del mínimo**. Compárelo con `t_min_bjd_tdb` de `truth.json`: ambos coinciden en uno o dos minutos.

![Página Fotometría con la curva de luz y el instante del mínimo](images/es/first-night-photometry.png)

5. **Todo de una vez:** en la página **Automatización** elija *Noche de una binaria eclipsante*, indique la carpeta `raw`, una carpeta de salida nueva y la posición del objetivo `100 80`, y pulse **Ejecutar**. Calibración, calidad de las imágenes, estrellas de comparación, curva de luz y mínimo se ejecutan uno tras otro; el resultado aparece abajo.

![La automatización «Noche de una binaria eclipsante» lista para ejecutarse](images/es/first-night-automation.png)

6. Para ir más allá: pegue el mínimo en la pestaña **O-C** con su propio T0 de referencia y su periodo, exporte la curva de luz (**Exportar CSV…**) o ajústela en la página **Órbitas y modelos**.

## La ventana
- **Barra lateral (izquierda):** las páginas en el orden de una noche de observación — Inicio, Planificar, Observar, Calibrar, Imágenes, Fotometría, Curvas de luz y O-C, Espectroscopía, Órbitas y modelos, Teledetección, Automatización, Proyecto y esta Guía.
- **Panel de tareas (abajo):** cada trabajo largo (calibración, fotometría, ajustes, espectros…) se ejecuta en segundo plano en su propio proceso. El panel muestra su progreso y estado (en cola, en curso, hecha, fallida, cancelada). Puede seguir trabajando mientras se ejecutan las tareas, y una tarea que falla nunca cierra la ventana.
- **Barra de estado:** el valor del píxel y las coordenadas celestes bajo el ratón cuando hay una imagen abierta, y una barra de progreso mientras se ejecutan tareas.
- **Menús:** Archivo (proyectos, FITS), Ver (zoom y estiramiento de la visualización), Imagen (reducción astrométrica, procesado), Complementos, Configuración y Ayuda.
- **Deshacer y rehacer:** Editar → Deshacer (Ctrl+Z) revierte el último cambio en la página mostrada — una estrella marcada o quitada, puntos borrados, una eliminación de tendencia, valores atípicos quitados, una operación de imagen, un cambio en la cabecera, una línea del arco identificada u omitida — y Editar → Rehacer (Ctrl+Y o Ctrl+Mayús+Z) lo vuelve a hacer paso a paso. El menú nombra el paso. En un campo de texto Ctrl+Z deshace lo escrito en ese campo.

## La página de inicio
Empiece por lo que tenga:

- **Nuevo proyecto… / Abrir proyecto…** mantienen juntas las tomas, los ajustes y los resultados.
- **Abrir una imagen FITS** para ver una imagen y su cabecera.
- **Tengo imágenes brutas** → Calibrar. **Tengo imágenes calibradas** → Fotometría. **Tengo espectros** → Espectroscopía. **Tengo listas de mínimos o de VR** → Curvas de luz y O-C. **Quiero planificar una noche** → Planificar.

## Proyectos
Un proyecto es un único archivo con la extensión `.astroproj`. Registra cada archivo que añada y cada paso que ejecute: qué paso, sus ajustes, cuándo empezó, si tuvo éxito y sus resultados, junto con las versiones de las bibliotecas usadas. Así el trabajo es reproducible: meses después puede ver exactamente cómo se obtuvo un número.

- **Archivo → Nuevo proyecto…** crea el archivo; **Archivo → Abrir proyecto…** continúa un trabajo anterior.
- Las rutas de los archivos se guardan relativas al archivo del proyecto, así que puede llevar la carpeta del proyecto con sus datos a otro ordenador.
- La página **Proyecto** lista los archivos (con su tipo) y el historial de ejecuciones con sus ajustes.
- Seleccione una fila del historial para ver todo sobre esa ejecución: entradas, ajustes, resultados (o error) y versiones de las bibliotecas. **Ejecutar de nuevo con las mismas entradas y ajustes** la repite exactamente; la repetición se registra como una ejecución nueva.
- Sin proyecto también puede trabajar; entonces no se registra nada.

## Configuración
- **Básico o Experto** (en la página de Inicio o **Ajustes → Modo experto**): en el modo básico las opciones poco usadas (más opciones de calibración y de apilado, las opciones de seeing / PSF / centelleo de la fotometría, otras herramientas) están plegadas —un clic las abre, no se quita nada— y la página Espectroscopia muestra el orden de sus pestañas; en el modo experto todas las secciones están abiertas.
- **Configuración → Idioma:** inglés, turco, alemán o español. Puede hacer falta reiniciar para que cambien todos los textos.
- **Configuración → Aspecto:** Oscuro o Claro. Los gráficos ya mostrados adoptan los colores nuevos. **Figura para publicación…** en la barra de herramientas de cada gráfico lo guarda en negro sobre blanco (PDF, SVG, EPS o PNG a 300 ppp) sea cual sea el aspecto; con un clic derecho sobre cualquier tabla se exporta como CSV o LaTeX.
- **Configuración → Unidad de cálculo:** Automático, solo CPU o GPU. La barra de estado muestra qué unidad está en uso. Ejecute la aplicación con `--benchmark` para medir la velocidad de ambas.
- La configuración se guarda en un pequeño archivo JSON en su carpeta de configuración de usuario; los complementos y sus propias automatizaciones están a su lado.

## Tarjeta gráfica (GPU)
El trabajo pesado con matrices (por ejemplo, el apilado con recorte sigma) puede ejecutarse en la tarjeta gráfica mediante Vulkan, Metal o DirectX 12. Cada cálculo en GPU tiene un gemelo en CPU que da el mismo resultado, y *Automático* solo usa la tarjeta cuando realmente es más rápida. Si no se encuentra un controlador gráfico utilizable, se usa el procesador y no cambia nada más.
