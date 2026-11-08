# Teledetección
La página **Teledetección** analiza imágenes de satélite y aéreas (Landsat, Sentinel-2, drones) y cualquier imagen multibanda. Se abre en una ventana propia (su bloque en la página de inicio o el menú Ventana), con sus propios menús: **Archivo → Abrir…** (Ctrl+O, o arrastre los archivos) abre una imagen y **Analizar** tiene Calcular la fórmula de bandas, Clasificar (k-medias) y Componentes principales; los iconos bajo los menús hacen lo mismo.

## Abrir una imagen
**Abrir imagen…** abre un GeoTIFF multibanda (incluido Cloud-Optimised GeoTIFF), FITS, JPEG2000 (p. ej. archivos de banda de Sentinel-2), NetCDF (3 y 4) o HDF5. En NetCDF / HDF5 cada variable 2-D de la malla principal es una banda, los valores de relleno quedan en blanco y las coordenadas CF de latitud / longitud dan la posición en el mapa (los productos se escriben entonces como GeoTIFF con esa posición). Los archivos JPEG2000 se leen sin su posición en el mapa. La línea bajo el botón da el número de bandas, el tamaño y la proyección cartográfica. **Mostrar** elige la banda que se ve; al hacer clic en un píxel se muestran los valores de todas las bandas en ese punto y sus coordenadas en el mapa. Los archivos de banda de un producto Sentinel-2 de la ESA (dentro de su carpeta .SAFE) se convierten en reflectancia con el desplazamiento y la escala de su MTD_MSIL2A.xml / MTD_MSIL1C.xml: desde la línea de procesamiento 04.00 (2022) los números guardados llevan +1000 y los índices como el NDVI calculados sobre ellos serían erróneos. Los COG de Sentinel-2 de Element84 / AWS ya tienen el desplazamiento quitado y se leen tal cual. Una escena GeoTIFF demasiado grande para la memoria libre del ordenador no se carga entera: la página la muestra banda a banda y las operaciones de abajo la leen en franjas de filas (mismos resultados, algo más lento).

## Papel de las bandas e índices
Indique en **Papel de cada banda** cuál es **BLUE, GREEN, RED, NIR** (azul, verde, rojo, infrarrojo cercano) y **SWIR** (infrarrojo de onda corta). Después **Índice…** ofrece:

- **NDVI** (NIR − RED) / (NIR + RED) — vegetación;
- **NDWI** (GREEN − NIR) / (GREEN + NIR) — agua libre;
- **EVI** — vegetación, corregido del suelo y la atmósfera;
- **SAVI** — vegetación sobre suelo claro (L = 0,5);
- **NDBI** (SWIR − NIR) / (SWIR + NIR) — zonas edificadas.

## Álgebra de bandas
Escriba cualquier expresión con los nombres de banda de la lista **Mostrar** (p. ej. `B1`, `B2`, …) y pulse **Calcular**, p. ej. `(B4 - B3) / (B4 + B3)`. Se permiten + − × / y potencias, comparaciones, y `sqrt`, `log`, `log10`, `exp`, `abs`, `min`, `max`, `where`. Las expresiones se analizan de forma segura y nunca se ejecutan como código. Se muestran las estadísticas del resultado (mínimo, mediana, máximo, media ± desviación típica).

## Clasificación y componentes principales
- **Clasificar (k-medias)** agrupa los píxeles en el número de **clases** indicado según sus valores de banda (sin supervisión): agua, bosque, campos y poblaciones suelen separarse bien.
- **Componentes principales** comprime bandas correlacionadas en unas pocas nuevas; se lista la varianza explicada de cada una.

Cada producto se guarda como GeoTIFF con la georreferenciación de la entrada, así que se abre en QGIS en el lugar correcto.
