# Lichtkurven und O-C
Die Seite **Lichtkurven & O-C** hat drei Reiter: **Periodensuche**, **Frequenzanalyse** und **O-C-Diagramm**. Diese Reiter öffnen sich gemeinsam in einem eigenen Fenster (der Block Lichtkurven auf der Startseite oder das Menü Fenster); Bearbeiten → Rückgängig / Wiederholen wirkt dort auf den gezeigten Reiter.

## Periodensuche
Die auf der Seite Photometrie gemessene Lichtkurve wird automatisch verwendet; oder **CSV laden (Zeit, Fluss)…**.

- **Lomb–Scargle** — passt bei jeder Testperiode eine Sinuswelle an und wählt die, die den größten Teil der Änderung erklärt. Für sinusförmige Änderungen: pulsierende Sterne, Rotation und Flecken.
- **BLS** (Box Least Squares) — passt bei jeder Testperiode einen kurzen, kastenförmigen Einbruch an. Für Planetentransits und Bedeckungen vom Algol-Typ.
- **PDM** (Phasendispersionsminimierung) — setzt keine Form voraus: faltet die Daten mit jeder Testperiode und wählt die, bei der die Punkte am saubersten übereinanderliegen. Für jede Form der Lichtkurve, z. B. Bedeckungsveränderliche mit zwei Minima.
- **ANOVA** (mehrharmonische Varianzanalyse) — passt bei jeder Testperiode eine Kurve aus zwei Harmonischen an und prüft sie statistisch. Für glatte, nicht sinusförmige Formen wie RR Lyrae und Cepheiden.

Wie jede Methode arbeitet, mit Formeln und Quellen: **Mathematik der Methoden** (das letzte Kapitel dieser Anleitung). Fährt man mit der Maus über die Methodenliste, erscheint zu jeder eine einzeilige Zusammenfassung.

**TESS und Kepler:** einen Sternnamen (oder eine TIC-/KIC-Nummer) eintippen, TESS, Kepler oder K2 wählen und **Herunterladen** drücken. Die eigenen Lichtkurven der Mission (PDCSAP-Fluss, um instrumentelle Trends korrigiert) kommen aus dem MAST-Archiv; markierte Punkte werden verworfen, jeder Sektor oder jedes Quartal wird normiert, und alle werden zusammengefügt, mit Zeiten in BJD_TDB. Sie werden im Einstellungsordner aufbewahrt, sodass ein zweiter Abruf sofort geht. Dann die Periode wie unten suchen.

**ZTF und AAVSO:** ZTF (Lichtkurven der Zwicky Transient Facility von IRSA, über die Sternposition gefunden) oder AAVSO (Beobachtungen der AAVSO International Database) wählen und **Herunterladen** drücken. Von AAVSO, ZTF oder dem ASAS-SN Sky Patrol exportierte Dateien lassen sich auch mit **CSV laden…** öffnen. Ein Band wird behalten (das mit den meisten Punkten), obere Grenzen und markierte Punkte werden verworfen, Helligkeiten in relativen Fluss und Zeiten in BJD_TDB umgerechnet, sodass die Daten mit TESS oder eigenen Daten kombiniert werden können.

Stellen Sie **Kürzeste Periode** und **Längste Periode** ein (die längste ist voreingestellt auf die halbe Zeitspanne) und drücken Sie **Suchen**. Das Periodogramm und die mit der besten Periode gefaltete Lichtkurve werden gezeigt. Prüfen Sie die gefaltete Kurve: die halbe oder doppelte Periode ist ein häufiger Alias, besonders bei Bedeckungsveränderlichen mit gleich tiefen Minima. Eine ⚠-Zeile unter dem Ergebnis sagt, wann ihm nicht zu trauen ist: die Lichtkurve ist kürzer als zwei Zyklen der gesuchten Perioden (länger beobachten), die beste Periode ist länger als die halbe Zeitspanne, oder das Periodogramm ist am Rand des Bereichs am höchsten (den Bereich erweitern).

**Phasenintervalle** zeichnet die mittlere Kurve über die gefalteten Punkte. **Lichtkurve bearbeiten:** *Ausreißer entfernen (σ)*, *Zeitlich mitteln (min)*, *Punkte per Klick löschen* (dann einen Punkt in der Grafik anklicken), *Fluss ↔ Magnitude* und *Bearbeitungen rückgängig*. Periodensuche und Frequenzanalyse verwenden die bearbeitete Kurve. *Ausreißer entfernen* vergleicht jeden Punkt mit seinen zeitlichen Nachbarn (und, sobald eine Periode gefunden ist, mit seinen Nachbarn in der gefalteten Kurve); Bedeckungen und Pulsationen bleiben erhalten. **Fehler:** hat die Lichtkurve welche (von der Seite Photometrie, aus TESS- / Kepler- / ZTF- / AAVSO-Downloads oder einer dritten Spalte der CSV-Datei), werden sie als Fehlerbalken gezeichnet, folgen jeder Bearbeitung (Ausreißer, Binning — der Fehler jedes Mittels —, gelöschte Punkte, Fluss ↔ Helligkeit) und gewichten die Lomb–Scargle- und BLS-Suche mit 1/σ²; **Speichern** schreibt sie als dritte Spalte.

## Frequenzanalyse
Für pulsierende Sterne mit mehreren Moden (δ Scuti, γ Dor, β Cep), wie Period04. Geben Sie die **höchste Frequenz** (Zyklen pro Tag) ein und drücken Sie **Frequenzen analysieren**:

1. Das Amplitudenspektrum (Deeming-Fouriertransformation für ungleichmäßige Abtastung) wird berechnet.
2. Der höchste Peak wird als Sinus angepasst, entfernt (**Prewhitening**) und die Residuen erneut durchsucht.
3. Jede neue Frequenz wird zusammen mit den früheren angepasst (Frequenzen, Amplituden, Phasen alle frei).
4. Es endet, wenn das **S/N** des nächsten Peaks (Amplitude / mittlere Restamplitude innerhalb ±1 c/d) unter der Grenze liegt; Bregers Kriterium ist 4.

Die Tabelle nennt Frequenz, Periode, Amplitude und Phase mit Fehlern (Montgomery & O'Donoghue 1999) und S/N. Die Grafiken zeigen das ursprüngliche Spektrum, das Restspektrum mit der S/N-Grenze und das **Spektralfenster**: Ein Fensterpeak bei 1 c/d bedeutet, dass die täglichen Lücken Aliase bei ±1 c/d jeder echten Frequenz erzeugen; prüfen Sie eine Frequenz gegen ihren Alias. Mit **Auch das CLEAN-Spektrum zeigen** wird das Spektrum ohne diese Aliase gezeichnet (CLEAN, Roberts, Lehár & Dreher 1987): eine echte Frequenz bleibt, ihre Aliase verschwinden.

**Maximumszeiten** werden für jeden abgedeckten Zyklus gemessen (Parabel um jedes Maximum der angepassten Kurve); kreuzen Sie *Werte sind Magnituden* an, wenn die Lichtkurve in Magnituden ist. **Maxima an das O-C-Diagramm senden** fügt sie der O-C-Liste hinzu.

## O-C-Diagramm
O-C (beobachtet minus berechnet) zeigt, wie die Minimumszeiten von einer konstanten Periode abweichen.

1. Die **Minimumszeiten** eintippen oder einfügen, eine pro Zeile: `Zeit [Fehler] [I/II] [Quelle]` — z. B. `2459876.43215 0.00021 I TESS`. Oder **Datei laden…**. Zeiten in BJD oder HJD; nicht mischen.
2. Ein **Referenz-T0** und die **Periode (d)** angeben: Daraus wird die Epoche jedes Minimums berechnet.
   Oder den Namen des Sterns in **Stern** eingeben und **Nachschlagen** drücken: T0 und Periode kommen aus AAVSO VSX. Ein leeres T0 ist das erste Hauptminimum.
3. **Lineare Ephemeride** oder **Quadratisch (Periodenänderung)** wählen und **Anpassen und O-C zeichnen** drücken. **Ergebnisse exportieren (CSV / LaTeX)…** schreibt die angepassten Werte mit 1σ-Fehlern, gerundet wie in einer Veröffentlichung, mit einer Tabellenunterschrift, die das Modell nennt.

Das Ergebnis liefert neues T0 und P mit Fehlern; die quadratische Anpassung liefert zusätzlich die Periodenänderungsrate dP/dt in Sekunden pro Jahr und das reduzierte χ². Hauptminima werden als Kreise, Nebenminima als Quadrate gezeichnet; das untere Diagramm zeigt die Residuen.

## Dritter Körper und Apsidendrehung
- **Dritter Körper (Lichtlaufzeit):** Das bedeckende Paar umläuft mit einem dritten Stern den gemeinsamen Schwerpunkt, sodass seine Bedeckungen entlang einer Bahn zu früh und zu spät kommen (Irwin 1952). Die Anpassung liefert die Periode des dritten Körpers P3 (Jahre), die Halbamplitude A (Minuten), die Exzentrizität e, das Argument ω und die Massenfunktion f(m3), die Untergrenze der Masse des dritten Sterns. Sie braucht mindestens 8 Minima, verteilt über mehr als ein P3.
- **Apsidendrehung:** In einer exzentrischen Bahn dreht sich die Apsidenlinie, sodass Haupt- und Nebenminima gegenläufig pendeln. Geben Sie beide Arten an (I und II); die Anpassung liefert e, ω zur Epoche 0, dω/dE (Grad pro Zyklus) und die Apsidenperiode U (Jahre). Das Modell ist erster Ordnung in e (gut für e ≲ 0,1).
- **MCMC-Unsicherheiten:** Bei diesen beiden Modellen startet das Kästchen nach der Anpassung eine Markow-Kette (emcee): 68-%-Intervalle jedes Parameters, e und ω eingeschlossen, sowie von f(m3) und U — ehrlich, wenn die Parameter voneinander abhängen (wie in OCFit). Es dauert einige Sekunden; mehr Schritte geben stabilere Fehler. Lineare und quadratische Ephemeriden sind lineare Probleme, ihre Fehler aus kleinsten Quadraten sind bereits exakt; das Kästchen ist dort aus.

## Ein O-C-Diagramm lesen
- Eine gerade, geneigte Linie: Die Periode ist leicht falsch — die Anpassung korrigiert sie.
- Eine Parabel: Die Periode ändert sich (Massentransfer, magnetische Aktivität, Drehimpulsverlust).
- Eine Welle: Lichtlaufzeiteffekt eines dritten Körpers oder Apsidendrehung (Haupt- und Nebenminima bewegen sich in exzentrischen Systemen gegeneinander).
- Fehler zählen: Minima ohne Fehler erhalten gleiches Gewicht.
