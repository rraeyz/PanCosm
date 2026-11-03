# Planen
Die Seite **Planen** zeigt, wann Ihre Ziele heute Nacht beobachtbar sind und welche Bedeckungen oder Transits in die Nacht fallen.

## Ihr Standort
Geben Sie **Breite** (Grad, Nord positiv), **Länge** (Grad, Ost positiv) und **Höhe** (Meter) der Sternwarte ein. Die Werte werden gespeichert. Sie dienen auch der baryzentrischen Korrektur von Radialgeschwindigkeiten und den Dämmerungszeiten.

## Die Nacht und die Höhengrenze
- **Nacht beginnend am:** das Datum des Abends, an dem die Nacht beginnt.
- **Niedrigste Höhe (°):** Darunter gilt ein Ziel als nicht beobachtbar (Bäume, Gebäude, dicke Luft). Üblich sind 20–30°.

## Ziele hinzufügen
Geben Sie einen **Namen** ein (wird in SIMBAD nachgeschlagen, z. B. `HAT-P-32`, `V523 Cas`, `M 42`) oder **Koordinaten** (`02:04:10 +46:41:16` oder Dezimalgrad) und drücken Sie **Hinzufügen**.

**Mit Ephemeride hinzufügen** sucht den Namen im AAVSO-Katalog **VSX** (Veränderliche) oder im **NASA Exoplanet Archive** (Planeten wie `HAT-P-32 b`) und füllt Koordinaten, Periode, Epoche und Dauer aus, sodass die Bedeckungen oder Transits der Nacht sofort erscheinen. Bei Bedeckungsveränderlichen ist die Epoche das VSX-Hauptminimum (HJD; weicht von BJD um Sekunden ab) und *Sekundär* ist angekreuzt; bei Pulsationsveränderlichen wird nur die Periode gezeigt. Braucht Internet.

- Einmal gefundene Namen werden zwischengespeichert, sodass die Planung später auch ohne Internet funktioniert.
- **Auswahl entfernen** löscht Zeilen aus der Tabelle.

## Bedeckungen und Transits
Für Bedeckungsveränderliche und Exoplaneten füllen Sie die Spalten der Zieltabelle aus:

- **T0 (BJD):** eine Zeit des Hauptminimums oder der Transitmitte (BJD_TDB).
- **Periode (d)** und **Dauer (d)** der Bedeckung oder des Transits.
- **Nebenminimum:** ankreuzen, um auch die Nebenminima (bei Phase 0,5) aufzulisten.

Der Plan listet dann jedes Ereignis der Nacht mit Beginn, Mitte und Ende in UTC und ob es angesichts von Höhengrenze und Dunkelheit **beobachtbar** ist (*ja*, *teilweise* oder gar nicht).

## Das Diagramm lesen
**Die Nacht planen** zeichnet die Höhe jedes Ziels über der UTC-Zeit für die ganze Nacht:

- die blaue Schattierung wird von Sonnenuntergang über bürgerliche (−6°), nautische (−12°) und astronomische (−18°) Dämmerung schrittweise dunkler; der dunkelste Teil ist die astronomische Nacht;
- die gestrichelte graue Kurve ist der **Mond**, mit seinem beleuchteten Anteil in der Legende;
- die gepunktete rote Linie ist Ihre niedrigste Höhe;
- die rechte Achse zeigt die **Luftmasse**; Photometrie gelingt am besten unter Luftmasse 2 (Höhe über 30°);
- rote Dreiecke markieren die Mitte jeder Bedeckung oder jedes Transits auf der Kurve des Ziels.

Die Zeile unter dem Diagramm nennt Beginn und Ende der astronomischen Nacht in UTC und die Zahl der Ereignisse. In Polnähe gibt es im Sommer womöglich **keine astronomische Nacht**.

## Vom Plan zur Beobachtung
**Zeitplan erstellen** (nach *Die Nacht planen*) macht aus der Nacht ein Programm für mehrere Ziele: zuerst jede beobachtbare Bedeckung oder jeder Transit mit 30 Minuten Grundlinie davor und danach (überschneiden sich zwei, gewinnt das Ziel, das in Ihrer Liste weiter oben steht); der Rest der dunklen Zeit in Blöcken von einer Stunde, jeder für das Ziel, das am höchsten über Ihrer Höhengrenze bleibt. **An die Seite Beobachten senden** übergibt jeden Block mit Beginn und Ende an die Sequenz; die dort eingestellten Belichtungszeilen gelten für jedes Ziel.

Verwenden Sie die Zeiten des Plans als **Start** und **Ende** einer Sequenz auf der Seite Beobachten (oder tippen Sie `dusk` und `dawn`), oder beginnen Sie mit einer Automatisierungsvorlage wie *Nacht eines Bedeckungsveränderlichen* oder *Exoplaneten-Transit*.
