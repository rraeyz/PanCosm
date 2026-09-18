# Fernerkundung
Das Fenster **Fernerkundung** analysiert Satelliten- und Luftbilder (Landsat, Sentinel-2, Drohnen) und jedes mehrkanalige Bild. Es öffnet sich über seinen Block auf der Startseite oder das Menü Fenster und hat eigene Menüs: **Datei → Öffnen…** (Strg+O, oder die Dateien hineinziehen) öffnet ein Bild, und **Analyse** enthält Bandformel berechnen, Klassifizieren (k-Means) und Hauptkomponenten; die Symbole unter den Menüs tun dasselbe.

![Das Fenster Fernerkundung](images/de/window-remotesensing.jpg)

## Ein Bild öffnen
**Bild öffnen…** öffnet ein mehrkanaliges GeoTIFF (auch Cloud-Optimised GeoTIFF), FITS, JPEG2000 (z. B. Sentinel-2-Banddateien), NetCDF (3 und 4) oder HDF5. In NetCDF / HDF5 ist jede 2-D-Variable des Hauptgitters ein Band, Füllwerte werden leer, und CF-Breiten- / Längenkoordinaten liefern die Kartenposition (Produkte werden dann mit dieser Position als GeoTIFF geschrieben). JPEG2000-Dateien werden ohne ihre Kartenposition gelesen. Die Zeile unter der Schaltfläche nennt Zahl der Bänder, Größe und Kartenprojektion. **Zeigen** wählt das angezeigte Band; ein Klick auf ein Pixel zeigt die Werte aller Bänder dort und seine Kartenkoordinaten. Banddateien eines ESA-Sentinel-2-Produkts (in seinem .SAFE-Ordner) werden mit Offset und Skala aus MTD_MSIL2A.xml / MTD_MSIL1C.xml des Produkts in Reflektanz umgerechnet: seit Prozessierungsstand 04.00 (2022) tragen die gespeicherten Zahlen +1000, und Indizes wie NDVI wären darauf falsch. Die Sentinel-2-COGs von Element84 / AWS haben den Offset bereits entfernt und werden unverändert gelesen. Eine GeoTIFF-Szene, die zu groß für den freien Arbeitsspeicher ist, wird nicht ganz geladen: das Fenster zeigt sie Kanal für Kanal, und die Operationen unten lesen sie in Zeilenstreifen (gleiche Ergebnisse, etwas langsamer).

## Bandrollen und Indizes
Geben Sie unter **Bandrollen** an, welches Band **BLUE, GREEN, RED, NIR** (Blau, Grün, Rot, nahes Infrarot) und **SWIR** (kurzwelliges Infrarot) ist. Dann bietet **Index…**:

- **NDVI** (NIR − RED) / (NIR + RED) — Vegetation;
- **NDWI** (GREEN − NIR) / (GREEN + NIR) — offenes Wasser;
- **EVI** — Vegetation, um Boden und Atmosphäre korrigiert;
- **SAVI** — Vegetation über hellem Boden (L = 0,5);
- **NDBI** (SWIR − NIR) / (SWIR + NIR) — bebaute Flächen.

## Bandrechnung
Geben Sie einen beliebigen Ausdruck mit den Bandnamen aus der Liste **Zeigen** ein (z. B. `B1`, `B2`, …) und drücken Sie **Berechnen**, z. B. `(B4 - B3) / (B4 + B3)`. Erlaubt sind + − × / und Potenzen, Vergleiche sowie `sqrt`, `log`, `log10`, `exp`, `abs`, `min`, `max`, `where`. Ausdrücke werden sicher eingelesen und nie als Code ausgeführt. Die Statistik des Ergebnisses (Minimum, Median, Maximum, Mittelwert ± Standardabweichung) wird angezeigt.

## Klassifikation und Hauptkomponenten
- **Klassifizieren (k-Means)** teilt die Pixel nach ihren Bandwerten in die angegebene Zahl von **Klassen** ein (unüberwacht): Wasser, Wald, Felder und Ortschaften trennen sich meist gut.
- **Hauptkomponenten** verdichtet korrelierte Bänder zu wenigen neuen; die erklärte Varianz jeder Komponente wird aufgelistet.

Jedes Produkt wird als GeoTIFF mit der Georeferenzierung der Eingabe gespeichert und öffnet sich daher in QGIS an der richtigen Stelle.
