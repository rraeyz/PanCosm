# Exoplaneten
Das Fenster **Exoplaneten** passt ein exaktes Transitmodell an eine gespeicherte Lichtkurve an. Es öffnet sich über seinen Block auf der Startseite oder das Menü Fenster. Die Phasen stehen links in der Leiste: Daten, Stern, Planeten, Modell, Anpassung, Unsicherheit, Ergebnisse. Die Hauptansicht zeigt den Transit mit dem angepassten Modell und seinen Residuen, eine Tabelle der angepassten Parameter und eine Textzeile mit dem Ergebnis.

## Daten {#exoplanets-data}
**Lichtkurven öffnen…** nimmt eine oder mehrere Lichtkurvendateien: die `.lc.ecsv`-Dateien des Fensters Photometrie oder eine CSV- / Texttabelle aus Zeit, Fluss und Fehler (mindestens 10 Zeilen). Die Tabelle listet jede Datei mit Punktzahl, Zeitspanne in Tagen und Zeitskala; eine Zeile zu wählen wählt die anzupassende Lichtkurve und zeigt deren letzte Anpassung. Eine nicht lesbare Datei wird mit dem Grund im Text unter dem Diagramm genannt. Für die ExoClock-Datei werden Zeiten in BJD_TDB gebraucht (siehe Ergebnisse).

## Stern {#exoplanets-star}
Die Randverdunklung des Sterns folgt einem quadratischen Gesetz mit den Koeffizienten **u1** und **u2** (Vorgabe 0,4 und 0,2). Sie sind fest, solange **Randverdunklung anpassen** nicht angekreuzt ist; eine einzelne Nacht entscheidet sie selten, lassen Sie sie also fest und nehmen Sie die Werte für Temperatur und Filter aus einer Tabelle.

## Planeten {#exoplanets-planets}
Startwerte des Transits: **Periode (d)** (fest: ein Transit legt sie nicht fest), **Transitmitte** und **Rp/R★** (beide standardmäßig *auto*: die Mitte und die Wurzel der Tiefe der Delle der geglätteten Kurve), **a/R★** und der **Stoßparameter**. Die Anpassung verfeinert Transitmitte, Rp/R★, a/R★ und b ausgehend davon. Die Periode und eine erste Schätzung der übrigen lassen sich im Fenster Planung (**Mit Ephemeride hinzufügen**) oder im Fenster Photometrie aus dem NASA Exoplanet Archive holen; dieses Fenster fragt sie nicht ab.

## Modell {#exoplanets-model}
**Entzerren gegen** nennt die Größen, gegen die langsame, nicht vom Planeten stammende Trends zusammen mit dem Transit angepasst werden: airmass, fwhm, sky, x, y, durch Kommas getrennt (Vorgabe `airmass`; leer: keine). Die Lichtkurve muss diese Spalten enthalten; das Fenster Photometrie schreibt sie.

## Anpassung {#exoplanets-fit}
**Transit anpassen** passt die gewählte Lichtkurve im Hintergrund an; das Ergebnis ersetzt danach Diagramm, Tabelle und Text. Stopp steht in der Statusleiste.

## Unsicherheit {#exoplanets-uncertainty}
Die Fehler der kleinsten Quadrate können zu klein sein, wenn die Residuen zeitlich korreliert sind. **Rotes Rauschen berücksichtigen (Fehler × β)** multipliziert die Fehler mit β, dem Faktor, um den die Streuung der Residuen mit der Zeitklasse nicht wie erwartet abnimmt. **MCMC-Schritte** führt nach der Anpassung eine Posterior-Stichprobe aus (sie endet früher, sobald sie konvergiert; 0: keine) und liefert asymmetrische Fehler für Transitmitte, Rp/R★, a/R★ und b; steht im Text *not converged*, nehmen Sie mehr Schritte.

## Ergebnisse {#exoplanets-results}
Text und Tabelle geben die Transitmitte (BJD), die Tiefe (ppt und mmag), die Dauern T14 und T23, a/R★, b, die Inklination, die Sterndichte, das reduzierte χ², das RMS der Residuen und β an. **ExoClock-Datei…** schreibt die Upload-Datei des Transit-Timing-Projekts ExoClock (Zeit in BJD_TDB, normierter Fluss, Fehler), **ETD-Datei…** die Datei für die Exoplanet Transit Database (Julianisches Datum, Magnitude, Fehler). Eine Lichtkurve, deren Zeiten nicht in BJD_TDB sind, lässt sich nicht für ExoClock schreiben: geben Sie beim Messen die Position des Ziels an.
