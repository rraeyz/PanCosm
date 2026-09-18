# Automatisierung und Plugins
Eine **Automatisierung** verkettet Schritte zu Ihrer eigenen Pipeline — „die Aufnahmen eines Ordners kalibrieren → die Lichtkurve messen → das Minimum bestimmen → O-C“ — und führt sie in einem Durchgang aus. **Plugins** fügen eigene Schritte hinzu. Das Fenster Automatisierung öffnet sich über seinen Block auf der Startseite oder das Menü Fenster und hat eigene Menüs: **Datei → Neue Automatisierung** und **Automatisierung speichern unter…**, **Schritte** (hinzufügen, entfernen, nach oben oder unten) und **Ausführen** (die Automatisierung ausführen, ihre Sequenz an das Fenster Beobachten senden, nach der Sequenz auswerten).

![Das Fenster Automatisierung](images/de/window-automation.jpg)

## Fertige Vorlagen
Das Fenster **Automatisierung** listet fertige Vorlagen (markiert mit „Vorlage“) und Ihre eigenen Automatisierungen:

- **Nacht eines Bedeckungsveränderlichen** — eine Sequenz von der Abend- bis zur Morgendämmerung, dann Kalibrierung, Vergleichssterne, Lichtkurve, Minimumszeit (Kwee–van Woerden) und O-C.
- **Exoplaneten-Transit** — dasselbe mit der Trapez-Anpassung für die Transitmitte.
- **Kalibrierung und Stacking am Ende der Nacht** — Darks und Bias in der Morgendämmerung, dann Master, Kalibrierung und ein gestapeltes Bild.
- **Spektroskopie-Nacht → RV → Bahn** — jede Langspalt-Aufnahme mit dem Vergleichsspektrum reduziert, Radialgeschwindigkeiten gegen eine Vorlage und eine einlinige Bahn.
- **Veränderlicher Stern: Lichtkurve → Periode** — Lichtkurve und eine Periodensuche nach Lomb–Scargle.

Wählen Sie eine aus, um ihre Beschreibung und ihre Schritte zu sehen.

## Eine Automatisierung ausführen
1. Rechts die **Eingaben** ausfüllen (Ordner und Dateien haben eine Schaltfläche **…**). Gefragt wird nur, was kein Schritt erzeugen kann: zum Beispiel der Ordner mit den Rohaufnahmen und die Zielposition.
2. **Ausführen** drücken. Jeder Schritt läuft als normale Aufgabe im Aufgabenbereich und wird im Projekt festgehalten; der nächste beginnt, wenn der vorige fertig ist. Die Zeile unter der Schaltfläche zeigt, welcher Schritt läuft.
3. Am Ende werden darunter die Ergebnisse des letzten Schritts gezeigt (z. B. Minimumszeit und O-C). Schlägt ein Schritt fehl, hält die Automatisierung dort an und zeigt den Fehler.

## Der Beobachtungsteil
Vorlagen mit einer Beobachtungssequenz haben **Zum Fenster Beobachten**: Das trägt Ziel, Start und Ende (z. B. dusk und dawn) und die Belichtungszeilen ein. Ergänzen Sie die Koordinaten, prüfen Sie die Belichtungszeiten und starten Sie dort. Kreuzen Sie vor dem Senden **Nach der Sequenz auswerten** an: Endet die Sequenz (auch wenn das Wetter sie vorzeitig beendet, sofern Aufnahmen entstanden sind), läuft die Automatisierung von selbst auf dem Ordner der Sequenz. Bei einem entfernten Observatorium werden die Aufnahmen zuerst auf diesen Rechner kopiert und dann ausgewertet.

## Eigene Automatisierungen bauen
1. **Neu** beginnt eine leere Automatisierung (oder beginnen Sie mit einer Vorlage und ändern Sie sie).
2. Einen Schritt in der Liste unter **Schritte, der Reihe nach** wählen und **Schritt hinzufügen** drücken. **Entfernen**, **Auf** und **Ab** ändern die Reihenfolge.
3. Einen Schritt auswählen, um seine **Einstellungen** zu sehen:
   - Zeilen, die mit **←** beginnen, sind seine Eingaben. Standardmäßig nimmt eine Eingabe die gleichnamigen Daten, die ein früherer Schritt erzeugt hat (oder die unter Eingaben eingetragen wurden). Geben Sie einen anderen Namen ein, um sie zu verknüpfen, z. B. `images` ← `calibrated` beim Stapel-Schritt;
   - `name.field` nimmt ein Feld eines Ergebnisses, oder dieses Feld aus jeder Zeile: z. B. `time` ← `rvs.bjd` bei der Bahn;
   - Text mit geschweiften Klammern bildet einen Dateinamen, z. B. `{output_dir}/{item}_1d.fits`;
   - die übrigen Zeilen sind die Parameter des Schritts; geben Sie Zahlen, `true`/`false`, `null`, Listen wie `[1, 2]` oder Text ein.
4. **Speichern unter…** legt sie unter einem Namen in Ihrem Einstellungsordner ab (`automations`), wo sie beim nächsten Mal in der Liste erscheint.

Automatisierungen sind einfache JSON-Dateien und lassen sich daher weitergeben: Kopieren Sie die Datei in den Ordner `automations` eines anderen Benutzers.

## Plugins
**Was sie sind:** Ein Plugin ist ein kleines Zusatzwerkzeug, das Sie selbst zur Anwendung hinzufügen — für eine Rechnung, die die Anwendung nicht hat, oder die nur Ihre Gruppe braucht. Es ist eine einzige Python-Datei. Liegt sie im Plugin-Ordner, erscheint sie im Menü **Plugins**, öffnet ein kleines Formular für ihre Eingaben, läuft wie jeder eingebaute Schritt (im Hintergrund, mit Fortschritt und Abbrechen, im Projekt protokolliert) und kann als Schritt einer Automatisierung dienen.

**Zum Ausprobieren müssen Sie nicht programmieren.** **Plugins → Beispiel-Plugins installieren** fügt drei fertige hinzu:
- **plugin.exposure_time** — wie viele Sekunden für ein gewünschtes Signal-Rausch-Verhältnis zu belichten ist, aus der Helligkeit des Sterns, Ihrem Nullpunkt, Himmel, Ausleserauschen und Apertur (CCD-Gleichung). Nur Zahlen, keine Datei.
- **plugin.sky_level** — Himmelshintergrund und sein Rauschen in einem FITS-Bild (um Nächte zu vergleichen oder Flats zu prüfen).
- **plugin.light_curve_summary** — Punktzahl, Zeitspanne, Streuung in Millimagnituden und tiefster Punkt einer Lichtkurven-CSV.

Wählen Sie eines im Menü **Plugins**, füllen Sie das Formular aus und drücken Sie OK; das Ergebnis öffnet sich in einem Fenster. Ein fehlerhaftes Plugin wird mit Grund als „Laden fehlgeschlagen“ gelistet; es hält die Anwendung nie an. Plugins laufen mit Ihren Rechten wie jedes installierte Programm: nur vertrauenswürdige Dateien verwenden.

## Ein eigenes Plugin schreiben
Öffnen Sie **Plugins → Plugin-Ordner öffnen**, kopieren Sie ein Beispiel, benennen Sie es um und ändern Sie es. So sieht das ganze Himmels-Beispiel aus:

```python
from astrowb.engine.steps import step


@step("plugin.sky_level", inputs=("image",), outputs=("sky",), sigma=3.0)
def sky_level(inputs, params, ctx):
    """Median sky level and noise of a FITS image (stars clipped)."""
    from astropy.io import fits
    from astropy.stats import sigma_clipped_stats

    data = fits.getdata(inputs["image"])
    _, median, std = sigma_clipped_stats(data, sigma=params["sigma"])
    return {"sky": {"median": float(median), "noise": float(std)}}
```

- Der Text in Anführungszeichen nach `@step` ist der Name des Werkzeugs; er muss mit `plugin.` beginnen.
- `inputs` fragt das Formular ab (Dateipfade oder Zahlen); die Wörter danach (`sigma=3.0`) sind Einstellungen mit ihren Vorgabewerten.
- Die Funktion erhält sie als `inputs["image"]` und `params["sigma"]` und gibt ein Wörterbuch mit Ergebnissen zurück (Zahlen, Text, Listen).
- Bei langer Arbeit ab und zu `ctx.progress(0.5, "Meldung")` und in Schleifen `ctx.check()` aufrufen, damit Abbrechen funktioniert.
- numpy, scipy, astropy, photutils und matplotlib sind immer vorhanden. Datei speichern; das Plugins-Menü findet sie beim nächsten Öffnen.
