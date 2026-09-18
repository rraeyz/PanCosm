# Beobachten und Sicherheit
Die Seite **Beobachten** steuert Teleskop, Kamera, Fokussierer, Filterrad, Kuppel und Nachführung. Die Geräte gehören einem eigenen **Observatoriumsprozess** mit einer Sicherheitsüberwachung, sodass das Teleskop geschützt bleibt, auch wenn das Fenster geschlossen wird oder abstürzt. Er öffnet sich in einem eigenen Fenster (über seinen Block auf der Startseite oder das Menü Fenster) mit eigenen Menüs, gruppiert wie in N.I.N.A. und MaxIm DL: **Geräte** (Observatorium einrichten, verbinden, Observatorium auf diesem Computer starten), **Teleskop** (schwenken, zentrieren, Polausrichtung, parken), **Kamera** (Vorschau aufnehmen, Kamera kühlen, Kühlung aus, Filter wechseln), **Fokus** (Autofokus, Fokussierer bewegen), **Flats** (Himmelsflats, Panel-Flats) und **Sequenz** (Belichtungszeile hinzufügen / entfernen, starten, abbrechen, fortsetzen, Nachtplan löschen). Die Symbole unter den Menüs sind die nachts meistgenutzten Befehle: verbinden, schwenken, zentrieren, parken, Vorschau, Autofokus, starten und abbrechen.

## Das Observatorium einrichten
**Observatorium einrichten…** öffnet einen Dialog für alles Folgende: den Standort, die Geräte (**Alpaca-Geräte im Netzwerk suchen** listet jedes antwortende ASCOM-Alpaca-Gerät; INDI-Geräte werden von Hand mit Serveradresse und INDI-Gerätenamen eingetragen), die Sicherheitsgrenzen, PHD2 und ob andere Rechner sich verbinden dürfen. Er warnt vor riskanten Entscheidungen, zum Beispiel einer Montierung ohne Wettersensor. **Speichern und starten** schreibt die Datei und startet das Observatorium auf diesem Computer; **Öffnen…** bearbeitet eine vorhandene Datei.

Die geschriebene Datei ist einfaches JSON und kann auch von Hand bearbeitet werden:

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

- Jedes Gerät ist entweder **ASCOM Alpaca** (`"alpaca": "host:port"` und die Gerätenummer) oder **INDI** (`"indi": "host:port"` und der INDI-Gerätename). Klassische ASCOM-Treiber unter Windows werden über ASCOM Remote (Alpaca) erreicht.
- `monitor` ist ein Sicherheitsmonitor (Wolken-/Regensensor), `conditions` ein Gerät für Beobachtungsbedingungen (Feuchte, Wind, Regen, Wolken).
- `listen` ist die Adresse der Observatoriums-API. Lassen Sie sie auf `127.0.0.1`, außer Sie wollen es von einem anderen Rechner steuern.

## Starten und verbinden
- **Observatorium auf diesem Computer starten…** fragt nach der Konfigurationsdatei, startet den Observatoriumsprozess im Hintergrund und verbindet sich. Beim ersten Mal wird ein geheimes **Token** erzeugt und in die Datei geschrieben.
- Um ein entferntes Observatorium zu steuern, starten Sie es dort mit `--observatory config.json`, tragen hier seine **Adresse des Observatoriums** und das **Token** ein und drücken **Verbinden**.
- **HTTPS:** Kreuzen Sie in der Einrichtung *Verbindung verschlüsseln* an (es ist schon angekreuzt, wenn andere Rechner sich verbinden dürfen). Das Observatorium erzeugt dann ein eigenes Zertifikat und gibt beim Start seinen **Fingerabdruck** aus; tragen Sie ihn auf dem steuernden Rechner unter *Zertifikats-Fingerabdruck* ein und verwenden Sie eine `https://`-Adresse. Die Anwendung spricht nur mit genau diesem Zertifikat mit dem Observatorium, sodass niemand dazwischen Token oder Befehle lesen kann. Auf dem eigenen Rechner wird der Fingerabdruck automatisch eingetragen.
- Die farbige Zeile zeigt den Zustand: **Sicher** (grün), **NICHT SICHER** mit den Gründen (rot) oder **Keine Verbindung**.

## Die Sicherheitsüberwachung
Alle paar Sekunden prüft die Überwachung die Regeln. Ist etwas unsicher, **bricht sie die Belichtung ab, stoppt die Sequenz, parkt die Montierung und schließt die Kuppel**. Sie verweigert auch Schwenks zu unsicheren Positionen. Die Regeln (unter `"rules"` in der Konfiguration):

- `min_alt` (15°) und ein optionales `horizon`-Profil `[[az, alt], …]`;
- `sun_max_alt` (−6°): darüber ist Tag — bei Sonnenaufgang wird das Teleskop geparkt und die Kuppel geschlossen;
- `sun_min_sep` (30°) zwischen Ziel und Sonne;
- `max_humidity` (90 %), `max_wind` (12 m/s), `max_rain_rate` (jeder Regen), `max_cloud_cover`;
- `link_timeout_s` (30 s): Ein Gerät, das nicht mehr antwortet, gilt als unsicher.

Nach einer unsicheren Phase startet nichts von selbst neu: Prüfen Sie das Teleskop und drücken Sie **Fortsetzen** (wird verweigert, solange es noch unsicher ist).

## Das Teleskop bewegen
Koordinaten eintippen (`02:04:10 +46:41:16`) und **Schwenken** drücken. **Parken**, **Abbrechen** (stoppt sofort alles), **Fortsetzen** und **Autofokus** liegen daneben. Die Montierungszeile zeigt Höhe, Azimut und ob sie nachführt oder geparkt ist.

**Zentrieren** bringt das Ziel genau in die Mitte: Das Observatorium schwenkt, macht eine kurze Aufnahme, löst sie astrometrisch, teilt der Montierung mit, wohin sie wirklich zeigt (Sync), und schwenkt erneut, bis das Ziel innerhalb von 30″ liegt. Dafür braucht der Observatoriumsrechner ASTAP oder astrometry.net.

**Polausrichtung** misst, wie weit die RA-Achse einer parallaktischen Montierung vom Himmelspol entfernt ist: grob nach Norden (auf der Südhalbkugel nach Süden) bei Deklination 60–80° zeigen und die Schaltfläche drücken; es werden drei gelöste Aufnahmen gemacht, während sich nur die RA-Achse in 30°-Schritten dreht. Das Ergebnis sagt in Bogenminuten, wie weit die Achse zu heben oder zu senken und wie weit sie nach Osten oder Westen zu drehen ist. Justieren und erneut messen, bis der Fehler nur noch wenige Bogenminuten beträgt.

## Kamera, Fokussierer und Filter
- **Vorschau:** eine Belichtung der angegebenen Dauer mit dem gewählten Filter, gespeichert im Unterordner `preview` des Ausgabeordners und sofort im Betrachter geöffnet (Bildausschnitt und Fokussieren). Läuft das Observatorium auf einem anderen Rechner, wird die Aufnahme zuerst hierher kopiert, nach `observations/preview` in Ihrem Benutzerordner.
- **Kühlung:** **Kühlen auf** stellt die Kameratemperatur ein und schaltet die Kühlung ein; **Aus** schaltet sie aus. Vor der Nacht langsam abkühlen und vor dem Ausschalten der Kamera wieder aufwärmen.
- **Fokussierer:** **Fahren** schickt den Fokussierer auf eine absolute Position.
- **Filter:** Die Liste wird aus dem Filterrad gelesen; **Wechseln** dreht das Rad.
- Die graue Zeile zeigt Kameratemperatur und Kühlzustand, Fokussiererposition und aktuellen Filter.

## Autofokus
**Autofokus** macht Aufnahmen bei mehreren Fokussiererpositionen, misst den Halbflussradius (HFR) der Sterne und passt eine V-Kurve an; der Fokussierer fährt auf die beste Position. Vorher auf ein Feld mit Sternen zeigen.

## Sequenzen
Auf der rechten Seite:

- **Zielname** und **RA Dek** (für Darks und Bias die Koordinaten leer lassen: kein Schwenk).
- **Alle N Bilder dithern (PHD2):** verschiebt die Ausrichtung zwischen den Aufnahmen über PHD2 ein wenig, wodurch Hotpixel und feste Muster herausgemittelt werden.
- **Start:** leer für sofort, `dusk` oder eine UTC-Zeit wie `2026-11-15T21:30`. **Ende:** leer, um nach den Anzahlen aufzuhören, `dawn` oder eine UTC-Zeit — mit einem Ende **wiederholt sich die Belichtungsliste bis dahin** (Zeitreihe durch eine Bedeckung oder eine ganze Nacht).
- **Speichern in:** der Ordner auf dem Observatoriumsrechner.
- Die Belichtungstabelle: **Typ** (light, dark, bias, flat), **Filter**, **Belichtung (s)**, **Anzahl**, **Binning**. **Belichtungszeile hinzufügen** / **Zeile entfernen**.
- **Sequenz starten**. Fortschritt und Zahl der geschriebenen Aufnahmen erscheinen unter der Tabelle; das Protokoll links listet jedes Ereignis.

Läuft das Observatorium auf einem anderen Rechner, werden die Aufnahmen einer beendeten Sequenz auf diesen kopiert, nach `observations/<letzter Teil des Speichern-in-Ordners>` in Ihrem Benutzerordner. Das Observatorium gibt nur Aufnahmen heraus, die es selbst gespeichert hat; keine andere Datei auf jenem Rechner kann über das Netz gelesen werden.

Jede Aufnahme wird als FITS mit den Headern gespeichert, die die späteren Schritte brauchen: Typ, Belichtung, Startzeit (UTC), Filter, Binning, Temperatur, Gain, Objekt und Koordinaten, Standort.

## Meridian-Flips und Nachführung
Deutsche Montierungen werden automatisch umgeschlagen, wenn das Ziel den Meridian überquert; die Nachführkontrolle wird dabei gestoppt und danach neu gestartet. Nachführkontrolle und Dithern nutzen **PHD2** (`"phd2"` konfigurieren).

## Himmelsflats
Wählen Sie die Zeile mit gewünschtem Filter und gewünschter Anzahl, richten Sie das Teleskop auf die Flat-Stelle (Nachführung aus) und drücken Sie **Himmelsflats**. In der Dämmerung folgt die Belichtungszeit der Himmelshelligkeit, sodass jedes Flat einen guten Pegel erreicht.

## Eine unbeaufsichtigte Nacht
Geben Sie den Zielen `dusk` als Start und `dawn` als Ende. Die Sequenz wartet auf Dunkelheit, wiederholt sich bis zur Morgendämmerung, und die Überwachung parkt das Teleskop bei Sonnenaufgang oder wenn das Wetter umschlägt. Die Automatisierungsvorlagen *Nacht eines Bedeckungsveränderlichen* und *Kalibrierung und Stacking am Ende der Nacht* füllen die Sequenz für Sie.

## Zuerst mit Simulatoren testen
Bevor Sie echte Hardware verwenden, lassen Sie dieselbe Konfiguration gegen Simulatoren laufen (ASCOM-Alpaca-Simulatoren oder `indiserver` mit den INDI-Simulatortreibern). Prüfen Sie, dass unsichere Bedingungen die Montierung parken und die Kuppel schließen.

## Kameraeinstellungen, Fokusversätze, Rotator und Flatpanel
Jede Belichtungszeile hat **Gain**, **Offset**, **Auslesemodus** (seine Nummer in der Liste der Kamera) und ein **Teilbild** `x, y, Breite, Höhe` in gebinnten Pixeln. Leere Zellen behalten die Einstellung der Kamera und das volle Bild. Die Werte stehen in jedem FITS-Header (GAIN, OFFSET, READOUTM, XORGSUBF/YORGSUBF). Nehmen Sie Darks, Bias und Flats mit demselben Gain, Offset und Teilbild wie die Lights auf, sonst kann die Kalibrierung sie nicht zuordnen.

**Filter-Fokusversätze** und **Temperaturkompensation** werden in *Observatorium einrichten…* eingestellt: Versätze als `L=0, B=-30, V=15` (Fokussiererschritte; beim Filterwechsel fährt der Fokussierer um die Differenz) und ein Koeffizient in Schritten pro °C (durch Fokussieren bei zwei Temperaturen messen). Während einer Sequenz folgt der Fokussierer seiner eigenen Temperatur, sobald sie sich um 0,5 °C geändert hat.

Ein **Rotator** (ASCOM Alpaca) dreht vor dem Schwenk auf den **Rotatorwinkel** des Ziels; der Winkel wird als ROTATANG geschrieben.

**Panel-Flats** verwenden einen Alpaca-*CoverCalibrator* (Flip-Flat oder Leuchtfolie): Die Abdeckung schließt, das Panel leuchtet, die Belichtungszeit wird bis zum Zielpegel geregelt, und am Ende wird das Panel ausgeschaltet. Filter und Anzahl kommen aus der gewählten Zeile.
