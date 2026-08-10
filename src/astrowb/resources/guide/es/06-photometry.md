# Fotometría
La página **Fotometría** mide el brillo de una estrella objetivo respecto a estrellas de comparación en una serie de imágenes calibradas y da una curva de luz, instantes de mínimo e informes.

## Elegir imágenes y estrellas
1. **Elegir imágenes…** — tomas calibradas de un campo y un filtro. Se ordenan por tiempo.
2. En la primera imagen, **haga clic en la estrella objetivo** y luego en **una o varias estrellas de comparación**. Los clics se ajustan al centro de la estrella. **Borrar estrellas** empieza de nuevo.
3. O pulse **Sugerir estrellas de comparación**: elige estrellas de brillo parecido, no saturadas, sin vecinas brillantes y dentro del campo en todas las imágenes. Revíselas antes de medir.

Las buenas estrellas de comparación tienen color y brillo parecidos a los del objetivo y no son variables. Use varias: su suma (un conjunto) tiene menos ruido que una sola estrella.

Sobre la imagen el puntero es una cruz, y los anillos de apertura y de cielo que pondrá el siguiente clic lo siguen, en el color de la estrella que marcará (verde objetivo, rojo comparación, naranja de control). Un clic sobre una estrella ya marcada la quita. Arrastre para mover la imagen y use la rueda para el zoom.

Los archivos de píxeles de TESS y Kepler / K2, también los recortes TESScut de MAST, se pueden elegir tal cual: cada cadencia se convierte en una toma (se omiten las cadencias que la misión marca como inútiles) con el BJD_TDB del archivo. Sin atmósfera que dividir, el objetivo se puede medir **sin estrellas de comparación**: el flujo relativo es entonces el flujo propio del objetivo dividido por su mediana.

## Fotometría diferencial: objetivos, estrellas de comparación y de control
**Los clics añaden** elige qué son los clics siguientes: *objetivo y luego estrellas de comparación* (el primer clic es el objetivo T1 y los siguientes las estrellas de comparación C1, C2…), *estrellas de control* (K1, K2…) o *más objetivos* (T2, T3…). Las estrellas de control y los demás objetivos se miden en cada toma frente a las mismas estrellas de comparación, pero no forman parte de ellas — como la estrella de control de MaxIm DL, VPhot o AIJ. Una estrella de control constante muestra lo buena que es de verdad la fotometría: su dispersión (en mmag) aparece bajo el gráfico.

La pestaña **Estrellas** lista cada estrella con su papel y su posición. Escriba las **magnitudes conocidas** de las estrellas de comparación (de una carta de la AAVSO, un catálogo o su propia calibración) en la última columna: el objetivo, los demás objetivos y las estrellas de control obtienen entonces **magnitudes** toma a toma (cada estrella de comparación da un punto cero; una estrella de comparación que difiere en más de 0,1 mag se deja fuera y se nombra). **Magnitudes estándar (APASS / Gaia)** rellena la misma columna con los catálogos.

**Ponderar las estrellas de comparación según su dispersión:** cada estrella de comparación se mide frente a la suma de las demás y se pondera con el inverso de su varianza (de forma repetida, para que una estrella de comparación variable no estropee la dispersión de las demás). Así, una estrella de comparación variable o perturbada apenas cuenta.

La pestaña **Gráfico** elige qué se dibuja: el flujo relativo de T1, su magnitud diferencial Δm = −2,5 log(objetivo / conjunto), su magnitud, cada objetivo adicional o estrella de control, **las estrellas de comparación frente a las demás** (una variable destaca), **todas las estrellas normalizadas y desplazadas**, o la masa de aire, el cielo, la FWHM y la posición frente al tiempo. Las tomas en las que una estrella alcanza el nivel de saturación se marcan con un círculo rojo y se cuentan.

## Calidad de las imágenes
**Comprobar la calidad de las imágenes** mide cada toma elegida: el tamaño de las estrellas (FWHM), cuántas estrellas se ven y el nivel del cielo. El gráfico muestra las tres a lo largo de la noche; las tomas mucho peores que la típica de la noche se marcan en rojo, con el motivo — *estrellas borrosas* (viento, enfoque, seeing), *pocas estrellas* o *sin estrellas* (nubes, rocío), *cielo brillante* (crepúsculo, Luna). **Dejar fuera las imágenes malas** las quita antes de medir. Las automatizaciones *Noche de una binaria eclipsante* y *Tránsito de exoplaneta* lo hacen por sí solas.

## Aperturas
Cada estrella recibe tres anillos dibujados sobre la imagen: la **apertura** (línea continua) y los bordes interior y exterior del **anillo de cielo** (discontinuos). Los radios están en píxeles de la imagen, así que los anillos crecen y encogen con el zoom: acérquese para ver si la estrella queda en el anillo 1 y solo cielo entre los anillos 2 y 3. **Mayús + rueda del ratón** sobre la imagen agranda o reduce los tres anillos (0,5 px); las casillas de la derecha muestran los números. En una imagen muy alejada, donde los anillos serían menores que unos pocos píxeles de pantalla, una pequeña cruz marca cada estrella.

- **Anillo 1, la apertura:** el círculo en el que se suma la luz de la estrella.
- **Entre los anillos 1 y 2:** se deja fuera a propósito. Contiene las alas de la estrella, que harían parecer el cielo más brillante de lo que es.
- **Entre los anillos 2 y 3, el anillo de cielo:** aquí se mide el nivel del cielo (mediana con recorte sigma, así que las vecinas débiles y los píxeles calientes no cuentan) y se resta de cada píxel de la apertura.

**Elegir los radios a partir de los perfiles estelares** fija los tres anillos a partir de las estrellas en las que hizo clic, como hacen otros programas con un perfil de seeing (AstroImageJ) o una curva de crecimiento (DAOPHOT):

1. La **FWHM** de las estrellas se mide en su perfil radial (ajuste de Moffat).
2. La **apertura** es el radio en el que la curva de luz tiene la mejor relación señal-ruido: sobre la curva de crecimiento del objetivo y de las estrellas de comparación se evalúa la ecuación del CCD (ruido fotónico de la estrella, ruido del cielo y de lectura en cada píxel) en cada radio (Howell 1989). Las estrellas débiles tienen su mejor S/R en una apertura pequeña y las brillantes en una mayor. Se mantiene entre 1 y 3 FWHM: las aperturas más pequeñas pierden una parte de la luz que depende del seeing y sufren errores de centrado.
3. El **radio interior del cielo** está donde la más brillante de las estrellas elegidas ha dado el 99,5 % de su luz, y a 3 FWHM como mínimo: las estrellas reales tienen alas y el seeing cambia durante la noche.
4. El **radio exterior del cielo** hace que el anillo tenga cuatro veces más píxeles que la apertura, de modo que el cielo solo añade un 25 % a su propio ruido en el resultado (Merline & Howell 1995).

El gráfico muestra el perfil de la estrella con la apertura (verde), el hueco que se deja fuera y el anillo de cielo (azul); la línea de debajo da los números. Puede seguir cambiando los radios a mano.

- **Los radios siguen al seeing:** en cada toma los tres radios se escalan con la FWHM de esa toma dividida por la de la primera (una «apertura variable» en AstroImageJ). Así la apertura contiene siempre la misma parte de la luz, lo que ayuda en noches en que el seeing cambia mucho o el enfoque deriva.
- Con estrellas desenfocadas (anillos o discos planos) revise el perfil: la FWHM mide entonces el disco y los radios lo siguen.
- Las estrellas se recentran en cada toma, y la deriva del campo durante la noche se sigue de toma en toma.
- Las plantillas de automatización eligen los radios así por sí solas.

## Tiempo y BJD
Los tiempos se toman de `DATE-OBS` y `EXPTIME` (la mitad de la exposición). Con **AR Dec del objeto** (u `OBJCTRA`/`OBJCTDEC` en la cabecera) y el lugar en la cabecera, los tiempos se convierten a **BJD_TDB**, el estándar para cronometrar eclipses y tránsitos.

## Medir la curva de luz
**Medir curva de luz** se ejecuta en segundo plano y dibuja el flujo relativo (objetivo / conjunto de comparación) frente al tiempo. Bajo el gráfico verá el número de puntos y la dispersión en porcentaje. Los puntos de tomas que no se pudieron medir (nubes, estrella fuera del campo) se omiten y se informa de ello.


**Centelleo:** el titilar de una estrella añade un ruido que la estadística de fotones no conoce; en estrellas brillantes y exposiciones cortas es el mayor error. Si se indica la **Apertura del telescopio (m)** (o la cabecera tiene APTDIA en mm) y se conocen el lugar y la posición del objetivo, cada error de flujo lo incluye — σ² = 10⁻⁵ · 1,5² · D^(−4/3) · t⁻¹ · X³ · e^(−2h/8000 m) (Osborn et al. 2015, la forma corregida de Young 1967; D apertura, t exposición, X masa de aire, h altura). La línea bajo el gráfico dice si se incluyó y cuánto valía (mmag por toma). Los flujos medidos no cambian, solo sus barras de error.

## Borrar puntos malos y separar las curvas
En la pestaña **Gráfico** marque **Pulse un punto para borrarlo** y pulse un punto de la curva de luz (una nube, un satélite, una toma en la que se perdió la estrella): esa toma queda fuera de la curva de luz, las magnitudes, la eliminación de tendencias, el instante del mínimo y la exportación. **Recuperar los puntos borrados** los devuelve todos. **Separación entre curvas** fija lo separadas que se dibujan las curvas en las vistas con varias (*todas las estrellas*, *estrellas de comparación frente a las demás*); 0 las superpone, por ejemplo para ver que dos estrellas estándar dan la misma línea plana.

Todos los gráficos de la aplicación tienen **Abrir en una ventana nueva** en su barra de herramientas: una copia del gráfico en su propia ventana, para verlo en grande (zoom, desplazamiento, guardar) mientras sigue trabajando.

## Eliminación de tendencias
Los cambios lentos que no son de la estrella — la extinción que cambia con la masa de aire, un cielo que deriva, el enfoque o la estrella moviéndose por el chip — pueden eliminarse dividiendo (como en AstroImageJ o EXOTIC). En la pestaña **Gráfico** marque frente a qué se eliminan (masa de aire, FWHM, cielo, x, y, tiempo), indique el inicio y el final del eclipse o tránsito en **Dejar fuera desde … hasta …** para que el propio evento no se ajuste, y pulse **Eliminar tendencia**: ln(flujo) se ajusta linealmente en las magnitudes marcadas con los puntos fuera de ese intervalo y se divide en todos los puntos. La línea bajo el gráfico da la dispersión antes y después. **Deshacer la eliminación de tendencias** vuelve a la curva medida. La FWHM está disponible si *Los radios siguen al seeing* estaba activado; la masa de aire necesita el lugar y la posición del objetivo. El instante del mínimo, la exportación y el informe AAVSO usan la curva sin tendencia.

El **grado de la tendencia** 1 elimina una dependencia lineal de cada magnitud marcada; 2 o 3 ajustan una curva (p. ej. una extinción no lineal con la masa de aire o una deriva lenta que se curva en el tiempo). Use el grado más bajo que elimine la tendencia: un grado alto también puede curvar un eclipse largo.

## Instante del mínimo
- Introduzca **Efemérides T0 (BJD)** y **Período (d)** si los conoce (opcional): entonces también se dan la época y O-C.
- En **¿Qué tipo de mínimo es?** elija **Binaria eclipsante: método de Kwee–van Woerden** (por defecto; Kwee y van Woerden 1956, el método de las bases de datos O−C) o **Tránsito de exoplaneta: ajuste de trapecio**, adecuado para caídas de fondo plano, que además da profundidad y duración.
- **Instante del mínimo** da el instante con su error (en KvW, el mayor entre el error de KvW y el de bootstrap), en días y minutos.
- Si la curva de luz abarca varios eclipses (TESS, varias noches), indique T0 y el período —tras una **Búsqueda de períodos** en esta curva se rellenan solos— y cada mínimo primario y secundario se mide en su propia ventana y se envía a la página O-C con su tipo; sin ellos la página los pide en lugar de dar un instante sin sentido.

## Magnitudes estándar
Con una primera imagen con reducción astrométrica (Imagen → Reducción astrométrica), elija el filtro de sus imágenes y pulse **Magnitudes estándar (APASS / Gaia)**. Las estrellas de comparación se consultan en internet: B, V, g′, r′, i′ vienen de APASS DR9; R e I (y V donde APASS no tiene valor) se calculan a partir de Gaia DR3 con las relaciones publicadas de Gaia a Johnson-Cousins (dispersión de unas 0,03 mag); G es la propia de Gaia. La curva de luz pasa entonces a magnitudes en el sistema estándar: un punto cero para cada toma a partir de todas las estrellas de comparación y, si tres o más de ellas tienen colores, un término de color ajustado para la noche. Una estrella de comparación que difiere del catálogo en más de 0,1 mag (variable, mezclada o con un mal valor de catálogo) se notifica y se deja fuera. Las magnitudes se dibujan (más brillante arriba), entran en la exportación CSV y rellenan las magnitudes de comparación del informe AAVSO.

## Exportar
- **Exportar CSV…** escribe el tiempo, el flujo relativo, Δm y sus errores, las magnitudes si se conocen, cada estrella de control y objetivo adicional, los flujos brutos, la masa de aire y la FWHM para otros programas.
- **Exportar informe AAVSO…** escribe el formato extendido de la AAVSO: nombre de la estrella (como en VSX), su código de observador, filtro, las magnitudes de catálogo de las estrellas de comparación, ID de la carta y notas; la primera estrella de control va a KNAME / KMAG, como pide la AAVSO para la fotometría de conjunto.

## Curva de luz en vivo
(en **Otras herramientas**) **En vivo: seguir una carpeta durante la noche…** vigila la carpeta en la que escribe la cámara. Cada toma nueva se calibra (con los másteres que elija, o sin ellos) y se mide al llegar, y la curva de luz crece sola. Haga clic en el objetivo y en las estrellas de comparación en la primera toma antes de empezar. Las tomas que no se pueden medir se saltan y se cuentan.

## Polarimetría (doble haz)
(en **Otras herramientas**) Para un polarímetro de doble haz (prisma de Wollaston + lámina de media onda): haga clic en la imagen **ordinaria** de la estrella como objetivo y en la imagen **extraordinaria** como primera comparación, y luego en **Polarimetría (doble haz)**. El ángulo de la lámina de media onda se lee de la cabecera. El resultado son los parámetros de Stokes q y u, el grado de polarización P (también corregido del sesgo) y el ángulo θ con sus errores.

## Fotometría PSF y búsqueda de variables
La **fotometría PSF** (márquela en la página Fotometría) ajusta a cada estrella una imagen estelar con la FWHM del cuadro en lugar de sumar una apertura; las estrellas a menos de 2,5 FWHM se ajustan juntas, de modo que una vecina mezclada no contamina al objeto. Úsela en campos densos (cúmulos, la Vía Láctea); en campos poco poblados la apertura es igual de buena.

**Curvas de luz y O-C → Búsqueda de variables** mide cada estrella del primer cuadro en todos los cuadros (apertura o PSF), lleva todos los cuadros a un punto cero común con las estrellas constantes (nubes y masa de aire se cancelan) y representa la dispersión de cada estrella frente a su brillo. Las constantes siguen una curva que sube hacia las débiles (ruido de fotones); las que quedan claramente por encima son **candidatas** (círculos rojos, listadas por índice). Un clic en un punto o fila muestra su curva de luz y **Enviar esta estrella a Búsqueda de periodo** halla su periodo. Es lo que hace *varfind* de Muniwin: compruebe las candidatas en VSX antes de anunciar un descubrimiento.

## Coeficientes de extinción y de transformación
**Imagen → Coeficientes fotométricos…**
- **Extinción de la noche:** a partir de las estrellas de comparación de la curva medida (los cuadros deben dar la posición en el cielo para conocer la masa de aire): la magnitud instrumental de cada estrella frente a la masa de aire, una pendiente k común (mag por masa de aire), con el gráfico de Bouguer. Valores típicos en V: 0,15–0,3 en un buen lugar.
- **Coeficientes de transformación:** dos imágenes resueltas de un campo estándar (p. ej. un campo de Landolt o M67) en dos filtros. Las estrellas se miden en ambas, sus magnitudes vienen de APASS (B, V, g′, r′, i′) o de Gaia (V, R, I) y los coeficientes se ajustan con la convención de la AAVSO: Tbv de (B−V) frente a (b−v), Tv y Tb de V−v y B−b frente a (B−V). Introdúzcalos en sus informes o en la herramienta de transformación de la AAVSO.
