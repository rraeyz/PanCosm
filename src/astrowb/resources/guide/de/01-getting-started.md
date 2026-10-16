# Erste Schritte
Die Anwendung deckt den ganzen Beobachtungsablauf in einem Fenster ab: Ziele wählen, die Nacht planen, beobachten, kalibrieren, messen, modellieren und berichten. Sie können bei jedem Schritt mit den Daten einsteigen, die Sie schon haben.

Jede Arbeitsseite und jeder Reiter hat oben eine eingeklappte Zeile **Arbeitsablauf**, die den nächsten Schritt nennt. Ein Klick zeigt die übliche Arbeitsreihenfolge (die IRAF-Aufgabe in Klammern, wo es eine gibt), jeder Schritt als erledigt (✓), übersprungen (–) oder nächster (▶) markiert, und was für den nächsten Schritt zu tun ist. Sie ist eine Hilfe, nie eine Sperre: Beginnen Sie bei dem Schritt, an dem Ihre Daten stehen — ein bereits extrahiertes Spektrum braucht nur seine Wellenlängen, eine Lichtkurve aus einem Archiv keine Photometrie — und überspringen Sie, was Ihre Daten nicht brauchen.

## Der erste Start {#getting-started-first-start}
Beim ersten Öffnen zeigt die Anwendung ein kurzes Willkommensfenster auf Englisch mit drei Auswahlmöglichkeiten:

- **Language** (Sprache) — die Sprache der Oberfläche. Sie gilt sofort; später ändern Sie sie unter **Einstellungen → Sprache**.
- **Computations run on** (Rechnen auf) — *Automatic* nutzt die Grafikkarte, wenn sie schneller als der Prozessor ist (empfohlen), *Graphics card* nutzt sie immer, *Processor (CPU) only* nie.
- **Look** (Aussehen) — *Dark* (Blauschwarz, die Voreinstellung) oder *Light* (Hell).

Drücken Sie **Start**. Die Auswahl wird gespeichert und nicht wieder abgefragt. Danach folgt eine einminütige **Kurze Tour**; Sie können sie überspringen und später über **Hilfe → Kurze Tour** wieder öffnen.

## Ihre erste Nacht (Übungsdaten) {#getting-started-your-first-night-practice}
Eine vollständige Übung mit simulierten Daten, deren Lösung bekannt ist: von den Rohbildern bis zur Minimumszeit eines Bedeckungsveränderlichen.

1. **Hilfe → Übungsdaten für eine erste Nacht…** und einen leeren Ordner wählen. Es entsteht ein Ordner `raw` mit 7 Bias-, 7 Dark- (60 s), 7 V-Flat- und 48 V-Light-Aufnahmen eines Doppelsterns während eines Hauptminimums sowie `truth.json` mit den richtigen Antworten.
2. **Kalibrieren:** den Ordner `raw` wählen und **Einlesen** drücken: Die Tabelle zeigt 7 Bias, 7 Dark, 7 Flat und 48 Lights, nichts fehlt. Einen Ausgabeordner wählen (z. B. `cal`) und **Kalibrieren** drücken.

![Das Fenster Kalibrierung nach dem Einlesen](images/de/first-night-calibrate.png)

3. **Photometrie:** **Bilder wählen…** und die kalibrierten `light_V_*.fits` auswählen. **Schlechte Bilder finden (Wolken, Fokus, Spuren)** drücken: Alle Aufnahmen sind gut. Den Stern in der Bildmitte anklicken (den Doppelstern bei x = 100, y = 80), dann **Vergleichssterne vorschlagen** (oder die drei anderen Sterne anklicken). Die Position `02:04:10.3 +46:41:16` in *Ziel RA Dek* eintragen, damit die Zeiten in BJD_TDB sind, und **Lichtkurve messen** drücken: Eine etwa 45 % tiefe Bedeckung erscheint.
4. **Bedeckungsveränderlicher: Methode von Kwee–van Woerden** (die Voreinstellung) lassen und **Minimumszeit** drücken. Mit `t_min_bjd_tdb` in `truth.json` vergleichen: Beide stimmen auf ein bis zwei Minuten überein.

![Das Fenster Photometrie mit Lichtkurve und Minimumszeit](images/de/first-night-photometry.png)

5. **Alles in einem Durchgang:** Im Fenster **Automatisierung** *Nacht eines Bedeckungsveränderlichen* wählen, den Ordner `raw`, einen neuen Ausgabeordner und die Zielposition `100 80` angeben und **Ausführen** drücken. Kalibrierung, Bildqualität, Vergleichssterne, Lichtkurve und Minimum laufen nacheinander; das Ergebnis erscheint unten.

![Die Automatisierung „Nacht eines Bedeckungsveränderlichen“, bereit zum Start](images/de/first-night-automation.png)

6. Weiter geht es so: das Minimum mit Ihrem eigenen Referenz-T0 und Ihrer Periode in den Reiter **O-C** einfügen, die Lichtkurve exportieren (**CSV exportieren…**) oder sie im Fenster **Modelle** anpassen.

## Das Fenster {#getting-started-window}
- **Bereichsblöcke:** jeder Bereich, in der Reihenfolge einer Beobachtungsnacht, öffnet sich in einem eigenen Fenster; das Menü **Fenster** jedes Fensters listet sie ebenfalls auf, mit Start, Projekt und dieser Anleitung.
- **Aufgabenbereich (unten):** Jede lange Arbeit (Kalibrierung, Photometrie, Anpassungen, Spektren…) läuft im Hintergrund in einem eigenen Prozess. Der Bereich zeigt Fortschritt und Zustand (wartend, läuft, fertig, fehlgeschlagen, abgebrochen). Sie können weiterarbeiten, während Aufgaben laufen, und eine abstürzende Aufgabe reißt nie das Fenster mit.
- **Statusleiste:** Pixelwert und Himmelskoordinaten unter der Maus, wenn ein Bild offen ist, und ein Fortschrittsbalken, während Aufgaben laufen.
- **Menüs:** Datei (Projekte, FITS), Ansicht (Zoom und Darstellungsstreckung), Bild (astrometrische Lösung, Bearbeitung), Plugins, Einstellungen und Hilfe.
- **Rückgängig und Wiederholen:** Bearbeiten → Rückgängig (Strg+Z) nimmt die letzte Änderung im Fenster zurück — ein markierter oder entfernter Stern, gelöschte Punkte, eine Trendbereinigung, entfernte Ausreißer, eine Bildoperation, eine Header-Änderung, eine identifizierte oder ausgelassene Bogenlinie — und Bearbeiten → Wiederholen (Strg+Y oder Strg+Umschalt+Z) stellt sie Schritt für Schritt wieder her. Das Menü nennt den Schritt. In einem Textfeld macht Strg+Z die Eingabe in diesem Feld rückgängig.

## Die Startseite {#getting-started-start-page}
Die Startseite ist ein Menü der Arbeitsbereiche:

- **Dort weitermachen, wo Sie aufgehört haben** (wenn es etwas fortzusetzen gibt): die letzten Projekte und die letzten Dateien jedes Bereichs; ein Doppelklick öffnet sie wieder.
- **Neues Projekt / Projekt öffnen…** halten Aufnahmen, Einstellungen und Ergebnisse zusammen. **Ein FITS-Bild öffnen**, um ein Bild und seinen Header anzusehen.
- **Wählen Sie, was Sie tun möchten:** ein Block je Bereich — Planung, Beobachten, Kalibrierung, Bilder, Photometrie, Lichtkurven und Periode, O−C, Spektroskopie, Modelle, Fernerkundung, Automatisierung — jeder mit einer Zeile, was er tut. Ein Klick öffnet den Bereich. Die Bereiche ziehen in eigene Fenster mit eigenen Menüs, Werkzeugleiste und Feldern; ein Bereich, der schon in seinem Fenster ist, wird nach vorn geholt, nie zweimal geöffnet.
- Menü **Fenster**: das Hauptfenster und jedes offene Bereichsfenster. **Hilfe → Problem melden…** erstellt eine Zip-Datei (Fehlerprotokoll, Version, System, Einstellungen, letzte Schritte; keine Datendateien und keine Ordnernamen) für den Entwickler. **Ansicht → Text größer / kleiner / Normale Textgröße** in einem Bereichsfenster (**Einstellungen → Textgröße** im Hauptfenster) macht den Text in jedem Fenster größer oder kleiner (Strg+Umschalt++ / − / 0). Die Werkzeugleiste eines Bereichsfensters zeigt kleine Symbole (der Name jedes einzelnen im Tooltip); **Ansicht → Werkzeugleistentext** schreibt die Namen daneben. Jedes Bereichsfenster hat außerdem **Bearbeiten → Kopieren** und die **Einstellungen** (Sprache, Aussehen, Rechengerät, Textgröße), und unter **Hilfe** die Tour, **Nach Updates suchen…** und **Über**.

## Projekte {#getting-started-projects}
Ein Projekt ist eine einzige Datei mit der Endung `.astroproj`. Sie hält jede hinzugefügte Datei und jeden ausgeführten Schritt fest: welcher Schritt, seine Einstellungen, wann er begann, ob er gelang, und seine Ergebnisse, zusammen mit den Versionen der verwendeten Bibliotheken. So ist die Arbeit nachvollziehbar: Noch Monate später sehen Sie genau, wie eine Zahl entstanden ist.

- **Datei → Neues Projekt…** legt die Datei an; **Datei → Projekt öffnen…** setzt frühere Arbeit fort.
- Dateipfade werden relativ zur Projektdatei gespeichert, sodass Sie den Projektordner samt Daten auf einen anderen Rechner mitnehmen können.
- Die Seite **Projekt** listet die Dateien (mit ihrem Typ) und den Verlauf der Läufe mit ihren Einstellungen.
- Wählen Sie eine Zeile des Verlaufs, um alles über diesen Lauf zu sehen: Eingaben, Einstellungen, Ergebnisse (oder Fehler) und die Versionen der Bibliotheken. **Mit denselben Eingaben und Einstellungen erneut ausführen** wiederholt ihn genau; die Wiederholung wird als neuer Lauf festgehalten.
- Ohne Projekt können Sie ebenfalls arbeiten; dann wird nichts festgehalten.

## Einstellungen {#getting-started-settings}
- **Einfach oder Experte** (auf der Startseite oder **Einstellungen → Expertenmodus**): Im einfachen Modus sind selten geänderte Optionen (weitere Kalibrier- und Stapeloptionen, die Seeing- / PSF- / Szintillationsoptionen der Photometrie, weitere Werkzeuge) eingeklappt — ein Klick öffnet sie, nichts wird entfernt — und das Fenster Spektroskopie zeigt die Reihenfolge ihrer Reiter; im Expertenmodus ist jeder Abschnitt offen.
- **Einstellungen → Sprache:** Englisch, Türkisch, Deutsch oder Spanisch. Damit sich jeder Text ändert, kann ein Neustart nötig sein.
- **Einstellungen → Aussehen:** Dunkel oder Hell. Bereits angezeigte Diagramme übernehmen die neuen Farben. **Publikationsgrafik…** in der Werkzeugleiste jedes Diagramms speichert es schwarz auf weiß (PDF, SVG, EPS oder PNG mit 300 dpi), unabhängig vom Aussehen; mit einem Rechtsklick auf eine Tabelle exportieren Sie sie als CSV oder LaTeX.
- **Einstellungen → Recheneinheit:** Automatisch, nur CPU oder GPU. Die Statusleiste zeigt, welche Einheit benutzt wird. Starten Sie die Anwendung mit `--benchmark`, um die GPU zu prüfen: Sie meldet, ob eine gefunden wurde, führt jede GPU-Aufgabe (Stapeln, k-means-Klassen, Entfaltung, BLS- und PDM-Periodensuche) auf beiden Einheiten aus und zeigt, ob die Ergebnisse übereinstimmen und wie lange jede dauerte (auch als `gpu-check.txt` im Einstellungsordner gespeichert).
- Die Einstellungen liegen in einer kleinen JSON-Datei in Ihrem Benutzer-Einstellungsordner; Plugins und Ihre eigenen Automatisierungen liegen daneben.

## Grafikkarte (GPU) {#getting-started-graphics-card-gpu}
Schwere Arrayrechnungen (zum Beispiel Stacking mit Sigma-Clipping) können über Vulkan, Metal oder DirectX 12 auf der Grafikkarte laufen. Jede GPU-Rechnung hat ein CPU-Gegenstück mit demselben Ergebnis, und *Automatisch* nutzt die Karte nur, wenn sie wirklich schneller ist. Wird kein brauchbarer Grafiktreiber gefunden, rechnet der Prozessor, und sonst ändert sich nichts.
