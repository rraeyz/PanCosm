# Bahnen und Modelle
Die Seite **Bahnen & Modelle** passt ein physikalisches Modell an die Lichtkurve eines getrennten Bedeckungsveränderlichen oder eines Transitplaneten an und kombiniert es mit einer spektroskopischen Bahn zu absoluten Dimensionen.

## Das Modell
Zwei randverdunkelte Kugeln auf einer Keplerbahn. Es eignet sich für getrennte Doppelsterne und Transits. Enge, verformte oder Kontaktsysteme brauchen ein Roche-Modell: Exportieren Sie dann nach PHOEBE oder WD.

## Eine Lichtkurve anpassen
1. Die **Lichtkurve** wählen (CSV von der Seite Photometrie oder aus einer anderen Quelle; eine Zeitspalte und relativer Fluss oder Helligkeiten).
2. **Periode (d)** und **Hauptminimum (BJD)** angeben (von der Seite O-C).
3. Startwerte: **r1 + r2** (Summe der Radien als Anteil der Bahnhalbachse a), **k = r2 / r1**, **Inklination (°)**, **Flächenhelligkeitsverhältnis J**, **Drittlicht**, Exzentrizitätsterme und die Randverdunkelung **u1, u2** jedes Sterns. Die anzupassenden Parameter ankreuzen.
4. **Anpassen**: Das Ergebnis liefert i, r1, r2, das Lichtverhältnis L2/L1 und e mit Fehlern, den rms und χ²ᵣ. Das Diagramm zeigt Daten, Modell und Residuen (O−C) über der Phase.

## MCMC-Unsicherheiten
Die Fehler einer Kleinste-Quadrate-Anpassung setzen voneinander unabhängige Parameter voraus; bei Bedeckungsveränderlichen und Transits sind sie es nicht (Inklination, Radien und Randverdunkelung gleichen einander aus). Kreuzen Sie **MCMC-Unsicherheiten** an, um die Posterior-Verteilung rund um die Anpassung abzutasten (affin-invarianter Ensemble-Sampler, emcee), mit der gewählten Zahl an **Schritten**: Das Ergebnis gibt jeden freien Parameter als Median −/+ seine 16./84. Perzentile an, und **Posterior…** zeigt das Corner-Diagramm (Histogramme und Paare), in dem Korrelationen sofort zu sehen sind. Es dauert etwa eine Minute pro 1000 Punkte bei 2000 Schritten; es läuft im Hintergrund und kann abgebrochen werden.

## Absolute Dimensionen
Wenn die Seite Spektroskopie eine doppellinige Bahn (K1, K2) hat, kreuzen Sie **Absolute Dimensionen mit der doppellinigen Bahn** an: Massen M1, M2, Radien R1, R2 (Sonneneinheiten), die Bahnhalbachse a und log g beider Sterne werden mit fortgepflanzten Fehlern berechnet.

## PHOEBE und andere Modelle
- **Anpassen und für PHOEBE exportieren…** schreibt die Lichtkurve (`lc.txt`), die Radialgeschwindigkeiten, falls vorhanden (`rv1.txt`, `rv2.txt`), und die angepassten Parameter unter PHOEBEs Namen (`start.json`) als Ausgangspunkt für ein Roche-Modell.
- **Anpassen und für WD exportieren…** schreibt die Beobachtungen in den Spalten des Wilson-Devinney-Programms (`lc.dat`: Zeit, Fluss, Gewicht) und `wd_parameters.txt` mit den angepassten Werten unter WDs Namen: PERIOD, HJD0, XINCL, E, PERR0 (Radiant), EL3 und — mit einer doppellinigen Bahn — RM (q), die aus den Radien berechneten Oberflächenpotentiale PHSV und PCSV, VGA und A. Tragen Sie sie in die Eingabedatei Ihrer WD-Version ein; Temperaturen, Albedos und Schwerkraftverdunkelung legen Sie selbst fest.
- **Anpassen und für ExoClock / ETD exportieren…** (Transits) schreibt die Upload-Dateien der beiden Transit-Timing-Projekte — `<Name>_ExoClock.txt` (BJD_TDB, relativer Fluss, Fehler) und `<Name>_ETD.txt` (BJD_TDB, Helligkeit, Fehler) — und `<Name>_summary.txt` mit der Mitte dieses Transits Tc ± Fehler (Epoche nahe den Daten, aus angepasstem T0 und Periode), Tiefe, Dauer T14, Rp/R*, a/R* und Inklination. T0 und Periode aus der Ephemeridenabfrage der Plan-Seite eintragen, T0 (und die Form) anpassen, dann hochladen; Beobachtungsangaben (Beobachter, Filter, Belichtung) werden in den Formularen der Projekte eingegeben.
- **Mit einer Modellkurve vergleichen…** zeichnet eine anderswo berechnete Kurve (zwei Spalten: Phase oder Zeit und Fluss) über Ihre Daten.

## Bahn eines visuellen Doppelsterns
Der Reiter **Bahn eines visuellen Doppelsterns** passt die sieben Bahnelemente eines aufgelösten Doppelsterns an Positionsmessungen des Begleiters an.
1. Die Messungen eingeben oder **laden**, eine pro Zeile in der WDS-Reihenfolge: Epoche (Jahr), Positionswinkel θ (Grad, von Nord über Ost), Abstand ρ (Bogensekunden) und wahlweise der Fehler von ρ (″) und von θ (°). Zeilen mit `#` am Anfang werden übersprungen. Mindestens 7 Messungen sind nötig (sieben Elemente); deutlich mehr sind besser.
2. Wahlweise die **kürzeste** und **längste Periode** (Jahre) begrenzen; standardmäßig wird das 0,5- bis 10-Fache der von den Messungen überdeckten Zeit durchsucht.
3. Die **Parallaxe** (mas) angeben, um die Gesamtmasse M1 + M2 = a³ / (ϖ³ P²) aus Keplers drittem Gesetz zu erhalten.
4. **Bahn anpassen**: Jede Periode im Bereich, jede Periastronphase und Exzentrizitäten von 0 bis 0,95 werden mit der linearen Thiele–Innes-Lösung probiert, dann werden alle sieben Elemente gemeinsam verfeinert (Levenberg–Marquardt). Die Tabelle gibt P, T, e, a, i, Ω, ω mit 1σ-Fehlern aus der Kovarianz der Anpassung (mit dem reduzierten χ² skaliert), den rms der Abstände und die Masse. Das Diagramm zeigt die scheinbare Bahn (Ost links, wie am Himmel), die Messungen und ihre O−C-Linien.

Ohne Radialgeschwindigkeiten können Ω und ω beide um 180° gedreht werden: Das Programm gibt Ω zwischen 0 und 180° an. Prüfen Sie, ob ein kurzer Periodenbereich eine längere wahre Periode verdeckt: χ²ᵣ für verschiedene Bereiche vergleichen. Methode: Heintz (1978), *Double Stars*; Konventionen der USNO-Bahnkataloge (Fifth Catalog: Hartkopf, Mason & Worley 2001, AJ 122, 3472; fortgeführt als Sixth Catalog, ORB6).
