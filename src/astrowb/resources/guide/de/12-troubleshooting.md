# Fehlersuche
Häufige Probleme und was zu tun ist.

## Eine Aufgabe ist fehlgeschlagen
Der Aufgabenbereich zeigt *fehlgeschlagen*, und ein Fenster nennt den Fehler. Typische Ursachen: eine unlesbare Datei, eine fehlende Eingabe (die Meldung nennt sie), zu wenige Sterne oder Aufnahmen. Das Fenster bleibt benutzbar; korrigieren Sie die Eingabe und führen Sie den Schritt erneut aus. Der Projektverlauf behält den fehlgeschlagenen Lauf mit seinen Einstellungen.

Das Fehlerfenster zeigt den Fehler selbst; **Details anzeigen…** enthält den vollständigen Bericht. Um die Installation und jeden Webdienst der Anwendung (SIMBAD, VizieR, MAST, ZTF, AAVSO, SkyBoT, …) zu prüfen, starten Sie sie einmal im Terminal mit `--check-online`: jede Zeile sagt OK oder FAIL und warum. Ein FAIL bei einem Dienst liegt meist am Dienst oder am Netz; ein FAIL in den ersten Zeilen bedeutet, dass ein Teil der Installation fehlt — bitte melden.

## Die Kalibrierung meldet fehlende Aufnahmen
„no flat for filter …“, „no dark for … s“, „no bias“ — diese Lights werden trotzdem kalibriert, nur ohne diese Korrektur. Nehmen Sie die fehlenden Aufnahmen auf (gleicher Filter, gleiches Binning, gleiche Belichtung und Temperatur) oder akzeptieren Sie das Ergebnis. Darks anderer Belichtung lassen sich nur zusammen mit Bias-Aufnahmen verwenden.

## Sterne werden nicht gefunden oder die Lichtkurve springt
- Stellen Sie sicher, dass die Bilder kalibriert sind und von einem einzigen Filter stammen.
- Vergrößern Sie die Blende bei defokussierten oder strichförmigen Sternen; rücken Sie den Himmelsring von Nachbarn weg.
- Driftet das Feld stark, prüfen Sie, ob das Ziel in jeder Aufnahme liegt; Aufnahmen, in denen es fehlt, werden übersprungen.
- Wählen Sie andere Vergleichssterne: Einer davon könnte veränderlich oder gesättigt sein.

## Die Zeiten sehen falsch aus
Prüfen Sie `DATE-OBS` (es muss der UTC-Beginn der Belichtung sein) und `EXPTIME` im Header. Für BJD müssen Zielkoordinaten und Standort bekannt sein (im Header oder in den Feldern der Seite).

## Die astrometrische Lösung tut nichts
Installieren Sie ASTAP mit einer Sterndatenbank (oder astrometry.net mit Indexdateien) und versuchen Sie es erneut. Ungefähre Koordinaten im Header machen es viel schneller. Sehr kleine Felder brauchen eine tiefere Datenbank.

## Das Observatorium meldet NICHT SICHER
Die Gründe werden aufgeführt: Sonne über dem Horizont, Ziel zu tief, Feuchte, Wind, Regen, ein Gerät antwortet nicht… Beheben Sie die Ursache und drücken Sie dann **Fortsetzen**. Solange noch etwas unsicher ist, wird Fortsetzen verweigert — das ist beabsichtigt.

## Keine Verbindung zum Observatorium
Prüfen Sie, ob der Observatoriumsprozess läuft (starten Sie ihn erneut mit **Observatorium auf diesem Computer starten…**), die Adresse und das Token. Auf einem entfernten Rechner kann eine Firewall den Port sperren.

## Die Grafikkarte wird nicht benutzt
**Einstellungen → Recheneinheit** zeigt den Modus; die Statusleiste nennt das Gerät. Mit *Automatisch* wird die Karte nur benutzt, wenn sie schneller ist. Aktualisieren Sie den Grafiktreiber, wenn keine Karte gefunden wird; alles funktioniert auch auf dem Prozessor.

## Wo sind meine Einstellungen und Dateien?
Einstellungen, Plugins und Automatisierungen liegen im Benutzer-Einstellungsordner (unter Linux `~/.config/…`, unter Windows `%LOCALAPPDATA%\…`, unter macOS `~/Library/Application Support/…`). Projekte und Ergebnisse liegen dort, wo Sie sie speichern.

## Updates
**Hilfe → Nach Updates suchen…** fragt die Release-Seite des Projekts, ob es eine neuere Version gibt, und verlinkt deren Download. Die Anwendung sucht nie von selbst. Installieren Sie die neue Version über die alte; Einstellungen, Plugins und Automatisierungen bleiben erhalten.

## Ein Problem melden
Notieren Sie, was Sie getan haben, und den Fehlertext, und hängen Sie wenn möglich eine kleine Datei an, die das Problem zeigt. Die Projektdatei enthält die genauen Einstellungen jedes Laufs, was beim Nachstellen hilft.
