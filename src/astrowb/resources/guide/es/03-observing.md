# Observación y seguridad
La ventana **Observación** controla el telescopio, la cámara, el enfocador, la rueda de filtros, la cúpula y el guiado. Los dispositivos pertenecen a un **proceso del observatorio** aparte con un supervisor de seguridad, de modo que el telescopio sigue protegido aunque la ventana se cierre o falle. Se abre desde su bloque en la página de inicio o el menú Ventana, con sus propios menús, agrupados como en N.I.N.A. y MaxIm DL: **Dispositivos** (configurar el observatorio, conectar, iniciar el observatorio en este ordenador), **Telescopio** (apuntar, centrar, alineación polar, aparcar), **Cámara** (tomar vista previa, enfriar la cámara, apagar la refrigeración, cambiar el filtro), **Enfoque** (autoenfoque, mover el enfocador), **Flats** (flats de cielo, flats de panel) y **Secuencia** (añadir / quitar una fila de exposición, iniciar, abortar, reanudar, borrar el plan de la noche). Los iconos bajo los menús son las órdenes más usadas de noche: conectar, apuntar, centrar, aparcar, vista previa, autoenfoque, iniciar y abortar.

![La ventana Observación](images/es/window-observe.jpg)

## Configurar el observatorio {#observing-configuring-observatory}
**Configurar el observatorio…** abre un diálogo para todo lo siguiente: el lugar, los dispositivos (**Buscar dispositivos Alpaca en la red** lista cada dispositivo ASCOM Alpaca que responde; los dispositivos INDI se añaden a mano con la dirección del servidor y el nombre del dispositivo INDI), los límites de seguridad, PHD2 y si otros ordenadores pueden conectarse. Avisa de elecciones arriesgadas, por ejemplo una montura sin sensor meteorológico. **Guardar e iniciar** escribe el archivo e inicia el observatorio en este ordenador; **Abrir…** edita un archivo existente.

El archivo que escribe es JSON sencillo y también puede editarse a mano:

```json
{
  "site": {"lat": 39.9, "lon": 32.8, "height": 900},
  "devices": {
    "mount": {"alpaca": "127.0.0.1:11111", "number": 0},
    "camera": {"alpaca": "127.0.0.1:11111", "number": 0},
    "filterwheel": {"alpaca": "127.0.0.1:11111"},
    "focuser": {"indi": "127.0.0.1:7624", "device": "Focuser Simulator"},
    "dome": {"alpaca": "127.0.0.1:11111"},
    "monitor": {"alpaca": "127.0.0.1:11111"}
  },
  "rules": {"min_alt": 20, "max_humidity": 85, "max_wind": 10},
  "phd2": {"host": "127.0.0.1", "port": 4400},
  "listen": "127.0.0.1:11112"
}
```

- Cada dispositivo es **ASCOM Alpaca** (`"alpaca": "host:port"` y el número de dispositivo) o **INDI** (`"indi": "host:port"` y el nombre del dispositivo INDI). Los controladores ASCOM clásicos de Windows se alcanzan mediante ASCOM Remote (Alpaca).
- `monitor` es un monitor de seguridad (sensor de nubes/lluvia), `conditions` un dispositivo de condiciones de observación (humedad, viento, lluvia, nubes).
- `listen` es la dirección de la API del observatorio. Déjela en `127.0.0.1` salvo que quiera controlarlo desde otro ordenador.

## Iniciar y conectar {#observing-starting-connecting}
- **Iniciar el observatorio en este ordenador…** pide el archivo de configuración, inicia el proceso del observatorio en segundo plano y se conecta. La primera vez se crea un **token** secreto y se escribe en el archivo.
- Para controlar un observatorio remoto, inícielo allí con `--observatory config.json`, escriba aquí su **Dirección del observatorio** y el **Token** y pulse **Conectar**.
- **HTTPS:** marque *Cifrar la conexión* en la configuración (ya viene marcado cuando otros ordenadores pueden conectarse). El observatorio crea entonces su propio certificado e imprime su **huella** al arrancar; escríbala en *Huella del certificado* en el ordenador desde el que lo controla y use una dirección `https://`. La aplicación solo habla con el observatorio que tenga exactamente ese certificado, así que nadie en medio puede leer el token ni las órdenes. En el ordenador local la huella se rellena sola.
- La línea de color muestra el estado: **Seguro** (verde), **NO SEGURO** con los motivos (rojo) o **Sin conexión**.

## El supervisor de seguridad {#observing-safety-supervisor}
Cada pocos segundos el supervisor comprueba las reglas. Cuando algo no es seguro, **aborta la exposición, detiene la secuencia, aparca la montura y cierra la cúpula**. También rechaza apuntados a posiciones inseguras. Las reglas (en `"rules"` de la configuración):

- `min_alt` (15°) y un perfil `horizon` opcional `[[az, alt], …]`;
- `sun_max_alt` (−6°): por encima es de día — al amanecer se aparca el telescopio y se cierra la cúpula;
- `sun_min_sep` (30°) entre el objetivo y el Sol;
- `max_humidity` (90 %), `max_wind` (12 m/s), `max_rain_rate` (cualquier lluvia), `max_cloud_cover`;
- `link_timeout_s` (30 s): un dispositivo que deja de responder cuenta como inseguro.

Tras un periodo inseguro nada se reinicia solo: revise el telescopio y pulse **Reanudar** (se rechaza mientras siga siendo inseguro).

## Mover el telescopio {#observing-moving-telescope}
Escriba unas coordenadas (`02:04:10 +46:41:16`) y pulse **Apuntar**. **Aparcar**, **Abortar** (lo detiene todo a la vez), **Reanudar** y **Autoenfoque** están al lado. La línea de la montura muestra altura, acimut y si está siguiendo o aparcada.

**Centrar** pone el objetivo exactamente en el centro: el observatorio apunta, toma una imagen corta, la reduce astrométricamente, le dice a la montura adónde apunta de verdad (sincronización) y vuelve a apuntar, hasta que el objetivo esté a menos de 30″. Necesita ASTAP o astrometry.net en el ordenador del observatorio.

**Alineación polar** mide cuánto se aleja el eje AR de una montura ecuatorial del polo celeste: apunte aproximadamente al norte (al sur en el hemisferio sur) a declinación 60–80° y pulse el botón; se toman tres imágenes reducidas mientras solo gira el eje AR en pasos de 30°. El resultado indica, en minutos de arco, cuánto subir o bajar el eje y cuánto girarlo al este o al oeste. Ajuste y mida de nuevo hasta que el error sea de pocos minutos de arco.

## Cámara, enfocador y filtro {#observing-camera-focuser-filter}
- **Vista previa:** una exposición de la duración indicada con el filtro elegido, guardada en la subcarpeta `preview` de la carpeta de salida y abierta enseguida en el visor (encuadre y enfoque). Cuando el observatorio funciona en otro ordenador, la imagen se copia primero aquí, a `observations/preview` en su carpeta personal.
- **Refrigeración:** **Enfriar a** fija la temperatura de la cámara y enciende la refrigeración; **Apagar** la apaga. Enfríe despacio antes de la noche y caliente antes de apagar la cámara.
- **Enfocador:** **Mover** lleva el enfocador a una posición absoluta.
- **Filtro:** la lista se lee de la rueda de filtros; **Cambiar** gira la rueda.
- La línea gris muestra la temperatura de la cámara y el estado de la refrigeración, la posición del enfocador y el filtro actual.

## Autoenfoque {#observing-autofocus}
**Autoenfoque** toma imágenes en varias posiciones del enfocador, mide el radio de media luz (HFR) de las estrellas y ajusta una curva en V; el enfocador se lleva a la mejor posición. Apunte antes a un campo con estrellas.

## Secuencias {#observing-sequences}
A la derecha:

- **Nombre del objeto** y **AR Dec** (deje las coordenadas vacías para darks y bias: sin apuntado).
- **Dither cada N imágenes (PHD2):** desplaza ligeramente el apuntado entre imágenes mediante PHD2, lo que promedia los píxeles calientes y los patrones fijos.
- **Inicio:** vacío para empezar ya, `dusk` o una hora UTC como `2026-11-15T21:30`. **Fin:** vacío para parar tras los números indicados, `dawn` o una hora UTC — con un fin, la lista de exposiciones **se repite hasta entonces** (serie temporal a lo largo de un eclipse o de toda la noche).
- **Guardar en:** la carpeta del ordenador del observatorio.
- La tabla de exposiciones: **Tipo** (light, dark, bias, flat), **Filtro**, **Exposición (s)**, **Número**, **Agrupamiento**. **Añadir fila de exposición** / **Quitar fila**.
- **Iniciar secuencia**. El progreso y el número de imágenes escritas aparecen bajo la tabla; el registro de la izquierda lista cada evento.

Cuando el observatorio funciona en otro ordenador, las imágenes de una secuencia terminada se copian a este, a `observations/<última parte de la carpeta Guardar en>` en su carpeta personal. El observatorio solo entrega imágenes que ha guardado él mismo; ningún otro archivo de ese ordenador puede leerse por la red.

Cada imagen se guarda como FITS con las cabeceras que necesitan los pasos posteriores: tipo, exposición, hora de inicio (UTC), filtro, agrupamiento, temperatura, ganancia, objeto y coordenadas, lugar.

## Giros de meridiano y guiado {#observing-meridian-flips-guiding}
Las monturas ecuatoriales alemanas giran automáticamente cuando el objetivo cruza el meridiano; el guiado se detiene y se reinicia alrededor del giro. El guiado y el dither usan **PHD2** (configure `"phd2"`).

## Flats de cielo {#observing-sky-flats}
Seleccione la fila con el filtro y el número que desee, apunte el telescopio al lugar de flats (seguimiento apagado) y pulse **Flats de cielo**. En el crepúsculo, el tiempo de exposición sigue el brillo del cielo para que cada flat alcance un buen nivel.

## Una noche desatendida {#observing-unattended-night}
Dé a los objetivos `dusk` como inicio y `dawn` como fin. La secuencia espera a la oscuridad, se repite hasta el alba, y el supervisor aparca el telescopio al amanecer o cuando cambia el tiempo. Las plantillas de automatización *Noche de una binaria eclipsante* y *Calibración y apilado al final de la noche* rellenan la secuencia por usted.

## Pruebe primero con simuladores {#observing-test-simulators-first}
Antes de usar equipo real, ejecute la misma configuración con simuladores (simuladores ASCOM Alpaca, o `indiserver` con los controladores simuladores de INDI). Compruebe que las condiciones inseguras aparcan la montura y cierran la cúpula.

## Ajustes de cámara, desplazamientos de foco, rotador y panel de flats {#observing-camera-settings-focus-offsets}
Cada fila de exposición tiene **Ganancia**, **Offset**, **Modo de lectura** (su número en la lista de la cámara) y un **Subencuadre** `x, y, ancho, alto` en píxeles agrupados. Las celdas vacías mantienen el ajuste de la cámara y el cuadro completo. Los valores se escriben en cada cabecera FITS (GAIN, OFFSET, READOUTM, XORGSUBF/YORGSUBF). Tome darks, bias y flats con la misma ganancia, offset y subencuadre que las tomas de luz, o la calibración no podrá emparejarlos.

Los **desplazamientos de foco por filtro** y la **compensación de temperatura** se ajustan en *Configurar el observatorio…*: desplazamientos como `L=0, B=-30, V=15` (pasos del enfocador; al cambiar de filtro el enfocador se mueve la diferencia) y un coeficiente en pasos por °C (mídalo enfocando a dos temperaturas). Durante una secuencia el enfocador sigue su propia temperatura cada vez que cambia 0,5 °C.

Un **rotador** (ASCOM Alpaca) gira al **Ángulo del rotador** del objeto antes del apuntado; el ángulo se escribe como ROTATANG.

Los **flats de panel** usan un *CoverCalibrator* Alpaca (flip-flat o panel luminoso): la tapa se cierra, el panel se enciende, el tiempo de exposición se ajusta hasta el nivel objetivo y al final se apaga el panel. El filtro y el número de flats salen de la fila elegida.
