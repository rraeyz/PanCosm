# Solución de problemas
Problemas frecuentes y qué hacer.

## Una tarea ha fallado
El panel de tareas muestra *fallida* y una ventana da el error. Causas típicas: un archivo que no se puede leer, una entrada que falta (el mensaje la nombra), demasiadas pocas estrellas o tomas. La ventana sigue siendo usable; corrija la entrada y ejecute el paso de nuevo. El historial del proyecto conserva la ejecución fallida con sus ajustes.

## La calibración dice que faltan tomas
«no flat for filter …», «no dark for … s», «no bias» — esos lights se calibran igualmente, sin esa corrección. Tome las tomas que faltan (mismo filtro, agrupamiento, exposición y temperatura) o acepte el resultado. Los darks de otra exposición solo pueden usarse si hay tomas bias.

## No se encuentran estrellas o la curva de luz salta
- Asegúrese de que las imágenes están calibradas y son de un solo filtro.
- Aumente la apertura para estrellas desenfocadas o con trazo; aleje el anillo de cielo de las vecinas.
- Si el campo deriva mucho, compruebe que el objetivo está dentro de cada toma; las tomas en las que no está se saltan.
- Elija otras estrellas de comparación: una de ellas puede ser variable o estar saturada.

## Los tiempos parecen incorrectos
Compruebe `DATE-OBS` (debe ser el inicio de la exposición en UTC) y `EXPTIME` en la cabecera. Para BJD hay que conocer las coordenadas del objetivo y el lugar (en la cabecera o en los campos de la página).

## La reducción astrométrica no hace nada
Instale ASTAP con una base de datos de estrellas (o astrometry.net con archivos de índice) e inténtelo de nuevo. Unas coordenadas aproximadas en la cabecera lo aceleran mucho. Los campos muy pequeños necesitan una base de datos más profunda.

## El observatorio dice NO SEGURO
Se listan los motivos: Sol sobre el horizonte, objetivo demasiado bajo, humedad, viento, lluvia, un dispositivo que no responde… Corrija la causa y pulse **Reanudar**. Mientras algo siga siendo inseguro, Reanudar se rechaza — es intencionado.

## Sin conexión con el observatorio
Compruebe que el proceso del observatorio está en marcha (inícielo de nuevo con **Iniciar el observatorio en este ordenador…**), la dirección y el token. En un ordenador remoto, un cortafuegos puede bloquear el puerto.

## No se usa la tarjeta gráfica
**Configuración → Unidad de cálculo** muestra el modo; la barra de estado nombra el dispositivo. Con *Automático* la tarjeta solo se usa cuando es más rápida. Actualice el controlador gráfico si no se encuentra ninguna tarjeta; todo funciona también en el procesador.

## ¿Dónde están mi configuración y mis archivos?
La configuración, los complementos y las automatizaciones están en la carpeta de configuración del usuario (en Linux `~/.config/…`, en Windows `%LOCALAPPDATA%\…`, en macOS `~/Library/Application Support/…`). Los proyectos y resultados están donde usted los guarde.

## Actualizaciones
**Ayuda → Buscar actualizaciones…** pregunta a la página de versiones del proyecto si existe una versión más nueva y enlaza a su descarga. La aplicación nunca lo comprueba por su cuenta. Instale la versión nueva encima de la antigua; la configuración, los complementos y las automatizaciones se conservan.

## Informar de un problema
Anote lo que hizo y el texto del error y, si es posible, adjunte un archivo pequeño que muestre el problema. El archivo del proyecto contiene los ajustes exactos de cada ejecución, lo que ayuda a reproducirlo.
