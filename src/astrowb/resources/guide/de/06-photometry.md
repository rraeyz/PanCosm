# Photometrie
Die Seite **Photometrie** misst auf einer Reihe kalibrierter Bilder die Helligkeit eines Zielsterns relativ zu Vergleichssternen und liefert Lichtkurve, Minimumszeiten und Berichte.

## Bilder und Sterne wählen
1. **Bilder wählen…** — kalibrierte Aufnahmen eines Feldes und eines Filters. Sie werden nach der Zeit sortiert.
2. Im ersten Bild **den Zielstern anklicken**, dann **einen oder mehrere Vergleichssterne**. Klicks rasten auf die Sternmitte ein. **Sterne löschen** beginnt von vorn.
3. Oder **Vergleichssterne vorschlagen** drücken: Es wählt Sterne ähnlicher Helligkeit, nicht gesättigt, ohne helle Nachbarn und in jedem Bild innerhalb des Feldes. Prüfen Sie sie vor dem Messen.

Gute Vergleichssterne haben eine ähnliche Farbe und Helligkeit wie das Ziel und sind nicht veränderlich. Verwenden Sie mehrere: Ihre Summe (ein Ensemble) rauscht weniger als ein einzelner Stern.

Über dem Bild ist der Zeiger ein Kreuz, und die Blenden- und Himmelsringe, die der nächste Klick setzt, folgen ihm in der Farbe des Sterns, den er markiert (grün Ziel, rot Vergleich, orange Prüfstern). Ein Klick auf einen schon markierten Stern entfernt ihn. Ziehen verschiebt das Bild, das Mausrad zoomt.

**Jedes Bild:** Die Pfeile und der Schieberegler unter der Bildanzahl gehen die Bilder in zeitlicher Reihenfolge durch, mit Namen und Zeit jedes Bildes. Markieren Sie die Sterne auf dem Bild, das am besten aussieht: Es hält die Positionen, und die Messung überträgt sie auf die anderen (die Verschiebung zwischen den Bildern wird gemessen, jeder Stern neu zentriert). Die markierten Sterne werden nur auf diesem Bild gezeichnet. Entfernen Sie das Häkchen bei **Dieses Bild verwenden**, um ein Bild wegzulassen (Wolken, eine Satellitenspur, schlechter Fokus).

TESS- und Kepler/K2-Target-Pixel-Dateien, auch TESScut-Ausschnitte von MAST, können unverändert gewählt werden: jede Kadenz wird eine Aufnahme (Kadenzen, die die Mission als unbrauchbar markiert, bleiben weg) mit der BJD_TDB des Archivs. Ohne Atmosphäre, die herauszurechnen wäre, kann das Ziel **ohne Vergleichssterne** gemessen werden: der relative Fluss ist dann der eigene Fluss des Ziels durch seinen Median.

## Differentielle Photometrie: Ziele, Vergleichs- und Prüfsterne
**Klicks fügen hinzu** wählt, was die nächsten Klicks sind: *Ziel, dann Vergleichssterne* (der erste Klick ist das Ziel T1, die nächsten die Vergleichssterne C1, C2…), *Prüfsterne* (K1, K2…) oder *weitere Ziele* (T2, T3…). Prüfsterne und weitere Ziele werden auf jeder Aufnahme gegen dieselben Vergleichssterne gemessen, gehören aber nicht dazu — wie der Prüfstern in MaxIm DL, VPhot oder AIJ. Ein konstanter Prüfstern zeigt, wie gut die Photometrie wirklich ist: seine Streuung (in mmag) steht unter dem Diagramm.

Der Reiter **Sterne** listet jeden Stern mit Rolle und Position. Tragen Sie die **bekannten Helligkeiten** der Vergleichssterne (aus einer AAVSO-Karte, einem Katalog oder Ihrer eigenen Kalibrierung) in die letzte Spalte ein: Ziel, weitere Ziele und Prüfsterne erhalten dann Bild für Bild **Helligkeiten** (jeder Vergleichsstern liefert einen Nullpunkt; ein Vergleichsstern, der um mehr als 0,1 mag abweicht, wird weggelassen und genannt). **Standardhelligkeiten (APASS / Gaia)** füllt dieselbe Spalte aus den Katalogen.

**Vergleichssterne nach ihrer Streuung gewichten:** Jeder Vergleichsstern wird gegen die Summe der anderen gemessen und mit dem Kehrwert seiner Varianz gewichtet (wiederholt, damit ein veränderlicher Vergleichsstern die Streuung der anderen nicht verdirbt). Ein veränderlicher oder gestörter Vergleichsstern zählt dann kaum noch.

Der Reiter **Diagramm** wählt, was gezeichnet wird: relativer Fluss von T1, seine differentielle Helligkeit Δm = −2,5 log(Ziel / Ensemble), seine Helligkeit, jedes weitere Ziel und jeder Prüfstern, **die Vergleichssterne gegen die anderen** (ein veränderlicher fällt auf), **alle Sterne normiert und versetzt** oder Luftmasse, Himmel, FWHM und Position über der Zeit. Aufnahmen, in denen ein Stern die Sättigungsgrenze erreicht, werden rot eingekreist und gezählt.

## Bildqualität
**Bildqualität prüfen** vermisst jede gewählte Aufnahme: die Größe der Sterne (FWHM), wie viele Sterne zu sehen sind und den Himmelshintergrund. Das Diagramm zeigt alle drei über die Nacht; Aufnahmen, die deutlich schlechter als die typische Aufnahme der Nacht sind, werden rot markiert, mit dem Grund — *Sterne unscharf* (Wind, Fokus, Seeing), *wenige Sterne* oder *keine Sterne* (Wolken, Tau), *heller Himmel* (Dämmerung, Mond). **Schlechte Bilder weglassen** entfernt sie vor dem Messen. Die Automatisierungen *Nacht eines Bedeckungsveränderlichen* und *Exoplaneten-Transit* tun das von selbst.

## Blenden
Jeder Stern bekommt drei Ringe, die auf dem Bild gezeichnet werden: die **Blende** (durchgezogen) sowie den inneren und äußeren Rand des **Himmelsrings** (gestrichelt). Die Radien sind in Bildpixeln, die Ringe wachsen und schrumpfen also mit dem Zoom: Zoomen Sie hinein, um zu sehen, ob der Stern in Ring 1 liegt und zwischen Ring 2 und 3 nur Himmel. **Umschalt + Mausrad** auf dem Bild macht alle drei Ringe größer oder kleiner (um 0,5 px); die Felder rechts zeigen die Zahlen. Auf einem weit herausgezoomten Bild, wo die Ringe kleiner als ein paar Bildschirmpixel wären, markiert stattdessen ein kleines Kreuz jeden Stern.

- **Ring 1, die Blende:** der Kreis, in dem das Sternlicht aufsummiert wird.
- **Zwischen Ring 1 und 2:** absichtlich ausgelassen. Hier liegen die Flügel des Sterns, die den Himmel heller erscheinen ließen, als er ist.
- **Zwischen Ring 2 und 3, der Himmelsring:** Hier wird der Himmelshintergrund gemessen (sigma-geclippter Median, sodass schwache Nachbarn und Hotpixel nicht zählen) und von jedem Blendenpixel abgezogen.

**Radien aus den Sternprofilen wählen** legt die drei Ringe anhand der angeklickten Sterne fest, wie andere Programme es mit einem Seeing-Profil (AstroImageJ) oder einer Wachstumskurve (DAOPHOT) tun:

1. Die **FWHM** der Sterne wird aus ihrem radialen Profil gemessen (Moffat-Anpassung).
2. Die **Blende** ist der Radius, bei dem die Lichtkurve das beste Signal-Rausch-Verhältnis hat: Auf der Wachstumskurve von Ziel- und Vergleichssternen wird die CCD-Gleichung (Photonenrauschen des Sterns, Himmels- und Ausleserauschen in jedem Pixel) bei jedem Radius ausgewertet (Howell 1989). Schwache Sterne haben ihr bestes S/R in einer kleinen Blende, helle in einer größeren. Sie bleibt zwischen 1 und 3 FWHM: Kleinere Blenden verlieren einen seeingabhängigen Teil des Lichts und leiden unter Zentrierfehlern.
3. Der **innere Himmelsradius** ist dort, wo der hellste der gewählten Sterne 99,5 % seines Lichts abgegeben hat, und mindestens 3 FWHM: Echte Sterne haben Flügel, und das Seeing ändert sich während der Nacht.
4. Der **äußere Himmelsradius** macht den Ring in Pixeln viermal so groß wie die Blende, sodass der Himmel nur 25 % zu seinem eigenen Rauschen im Ergebnis beiträgt (Merline & Howell 1995).

Das Diagramm zeigt das Sternprofil mit Blende (grün), ausgelassener Lücke und Himmelsring (blau); die Zeile darunter nennt die Zahlen. Sie können die Radien weiterhin von Hand ändern.

- **Radien folgen dem Seeing:** Auf jedem Bild werden alle drei Radien mit der FWHM dieses Bildes geteilt durch die des ersten Bildes skaliert (eine „variable Blende“ in AstroImageJ). Die Blende enthält dann immer denselben Teil des Lichts, was in Nächten mit stark wechselndem Seeing oder driftendem Fokus hilft.
- Bei defokussierten Sternen (Ringe oder flache Scheiben) das Profil prüfen: Die FWHM misst dann die Scheibe, und die Radien folgen ihr.
- Die Sterne werden auf jeder Aufnahme neu zentriert, und die Drift des Feldes während der Nacht wird von Aufnahme zu Aufnahme verfolgt.
- Die Automatisierungsvorlagen wählen die Radien von selbst auf diese Weise.

## Zeit und BJD
Die Zeiten stammen aus `DATE-OBS` und `EXPTIME` (Mitte der Belichtung). Mit **Ziel RA Dek** (oder `OBJCTRA`/`OBJCTDEC` im Header) und dem Standort im Header werden die Zeiten in **BJD_TDB** umgerechnet, den Standard für die Zeitbestimmung von Bedeckungen und Transits.

## Die Lichtkurve messen
**Lichtkurve messen** läuft im Hintergrund und zeichnet den relativen Fluss (Ziel / Vergleichsensemble) über der Zeit. Unter dem Diagramm stehen die Zahl der Punkte und die Streuung in Prozent. Punkte aus Aufnahmen, die nicht gemessen werden konnten (Wolken, Stern außerhalb), werden weggelassen und gemeldet.


**Szintillation:** Das Funkeln eines Sterns fügt ein Rauschen hinzu, das die Photonenstatistik nicht kennt; bei hellen Sternen und kurzen Belichtungen ist es der größte Fehler. Ist die **Teleskopöffnung (m)** angegeben (oder steht APTDIA in mm im Header) und sind Standort und Zielposition bekannt, enthält jeder Flussfehler sie — σ² = 10⁻⁵ · 1,5² · D^(−4/3) · t⁻¹ · X³ · e^(−2h/8000 m) (Osborn et al. 2015, die korrigierte Form von Young 1967; D Öffnung, t Belichtung, X Luftmasse, h Höhe). Die Zeile unter dem Diagramm sagt, ob sie einbezogen wurde und wie groß sie war (mmag pro Bild). Die gemessenen Flüsse ändern sich nicht, nur ihre Fehlerbalken.

## Schlechte Punkte löschen und Kurven abstufen
Im Reiter **Diagramm** **Zum Löschen auf einen Punkt klicken** ankreuzen und einen Punkt der Lichtkurve anklicken (Wolke, Satellit, ein Bild, in dem der Stern verloren ging): Dieses Bild fehlt dann in Lichtkurve, Helligkeiten, Trendbereinigung, Minimumszeit und Export. **Gelöschte Punkte wiederherstellen** holt alle zurück. **Abstand zwischen den Kurven** legt fest, wie weit die Kurven in Ansichten mit mehreren Kurven (*alle Sterne*, *Vergleichssterne gegen die anderen*) auseinander gezeichnet werden; 0 legt sie übereinander, etwa um zu sehen, dass zwei Standardsterne dieselbe flache Linie ergeben.

Jedes Diagramm der Anwendung hat in seiner Werkzeugleiste **In neuem Fenster öffnen**: eine Kopie des Diagramms in einem eigenen Fenster, um es groß anzusehen (Zoom, Verschieben, Speichern), während Sie weiterarbeiten.

## Trendbereinigung
Langsame Änderungen, die nicht vom Stern stammen — Extinktion, die sich mit der Luftmasse ändert, ein driftender Himmel, der Fokus oder ein über den Chip wandernder Stern — lassen sich herausdividieren (wie in AstroImageJ oder EXOTIC). Im Reiter **Diagramm** ankreuzen, wogegen bereinigt wird (Luftmasse, FWHM, Himmel, x, y, Zeit), Beginn und Ende der Bedeckung oder des Transits unter **Auslassen von … bis …** angeben, damit das Ereignis selbst nicht angepasst wird, und **Trend entfernen** drücken: ln(Fluss) wird auf den Punkten außerhalb dieses Bereichs linear in den angekreuzten Größen angepasst und aus allen Punkten herausdividiert. Die Zeile unter dem Diagramm nennt die Streuung vorher und nachher. **Trendbereinigung rückgängig** kehrt zur gemessenen Kurve zurück. FWHM gibt es, wenn *Radien folgen dem Seeing* eingeschaltet war; die Luftmasse braucht Standort und Position des Ziels. Minimumszeit, Export und AAVSO-Bericht verwenden die bereinigte Kurve.

**Trendgrad** 1 teilt eine lineare Abhängigkeit von jeder angekreuzten Größe heraus; 2 oder 3 passt eine Kurve an (z. B. eine in der Luftmasse nicht lineare Extinktion oder eine sich biegende langsame Drift in der Zeit). Nehmen Sie den kleinsten Grad, der den Trend entfernt: ein höherer Grad kann auch eine lange Bedeckung verbiegen.

## Minimumszeit
- Tragen Sie **Ephemeride T0 (BJD)** und **Periode (d)** ein, wenn Sie sie kennen (optional): Dann werden auch Epoche und O-C angegeben.
- Unter **Welche Art von Minimum ist es?** wählen Sie **Bedeckungsveränderlicher: Methode von Kwee–van Woerden** (Voreinstellung; Kwee & van Woerden 1956, die Methode der O−C-Datenbanken) oder **Exoplanetentransit: Trapezanpassung**, die zu Einbrüchen mit flachem Boden passt und auch Tiefe und Dauer liefert.
- **Minimumszeit** gibt die Zeit mit ihrem Fehler (bei KvW der größere von KvW- und Bootstrap-Fehler) in Tagen und Minuten an.
- Umfasst die Lichtkurve mehrere Bedeckungen (TESS, mehrere Nächte), T0 und die Periode angeben — nach einer **Periodensuche** auf dieser Lichtkurve werden sie eingetragen —, dann wird jedes Haupt- und Nebenminimum in seinem eigenen Fenster bestimmt und mit seiner Art auf die O-C-Seite geschickt; ohne sie fragt die Seite danach, statt eine sinnlose Zeit zu geben.

## Standardhelligkeiten
Mit einem astrometrisch gelösten ersten Bild (Bild → Astrometrische Lösung) wählen Sie den Filter Ihrer Bilder und drücken **Standardhelligkeiten (APASS / Gaia)**. Die Vergleichssterne werden im Internet nachgeschlagen: B, V, g′, r′, i′ stammen aus APASS DR9; R und I (und V, wo APASS keinen Wert hat) werden mit den veröffentlichten Gaia-zu-Johnson-Cousins-Beziehungen aus Gaia DR3 berechnet (etwa 0,03 mag Streuung); G ist Gaias eigenes. Die Lichtkurve wird dann zu Helligkeiten im Standardsystem: ein Nullpunkt für jede Aufnahme aus allen Vergleichssternen und, wenn drei oder mehr Vergleichssterne Farben haben, ein für die Nacht angepasster Farbterm. Ein Vergleichsstern, der um mehr als 0,1 mag vom Katalog abweicht (veränderlich, verschmolzen oder ein schlechter Katalogwert), wird gemeldet und weggelassen. Die Helligkeiten werden gezeichnet (heller nach oben), gehen in den CSV-Export ein und füllen die Vergleichshelligkeiten des AAVSO-Berichts.

## Exportieren
- **CSV exportieren…** schreibt Zeit, relativen Fluss, Δm und ihre Fehler, die Helligkeiten, wenn bekannt, jeden Prüfstern und jedes weitere Ziel, die Rohflüsse, Luftmasse und FWHM für andere Programme.
- **AAVSO-Bericht exportieren…** schreibt das erweiterte AAVSO-Format: Sternname (wie in VSX), Ihr Beobachtercode, Filter, die Katalogwerte der Vergleichssterne, Karten-ID und Anmerkungen; der erste Prüfstern kommt, wie die AAVSO es für Ensemble-Photometrie verlangt, in KNAME / KMAG.

## Live-Lichtkurve
(unter **Weitere Werkzeuge**) **Live: einem Ordner während der Nacht folgen…** beobachtet den Ordner, in den die Kamera schreibt. Jede neue Aufnahme wird beim Eintreffen kalibriert (mit den gewählten Mastern oder ohne) und gemessen, und die Lichtkurve wächst von selbst. Klicken Sie vor dem Start Ziel- und Vergleichssterne auf der ersten Aufnahme an. Nicht messbare Aufnahmen werden übersprungen und gezählt.

## Polarimetrie (Zweistrahl)
(unter **Weitere Werkzeuge**) Für ein Zweistrahl-Polarimeter (Wollaston-Prisma + Halbwellenplatte): das **ordentliche** Bild des Sterns als Ziel und das **außerordentliche** Bild als ersten Vergleichsstern anklicken, dann **Polarimetrie (Zweistrahl)**. Der Winkel der Halbwellenplatte wird aus dem Header gelesen. Das Ergebnis sind die Stokes-Parameter q und u, der Polarisationsgrad P (auch biaskorrigiert) und der Winkel θ mit ihren Fehlern.

## PSF-Photometrie und Suche nach Veränderlichen
**PSF-Photometrie** (auf der Photometrie-Seite ankreuzen) passt jedem Stern ein Sternbild mit der FWHM des Bildes an, statt eine Apertur zu summieren; Sterne näher als 2,5 FWHM werden gemeinsam angepasst, sodass ein verschmolzener Nachbar nicht in das Ziel einfließt. Für dichte Felder (Haufen, Milchstraße); in lockeren Feldern sind Aperturen ebenso gut.

**Lichtkurven & O-C → Suche nach Veränderlichen** misst jeden Stern des ersten Bildes auf allen Bildern (Apertur oder PSF), bringt alle Bilder über die konstanten Sterne auf einen gemeinsamen Nullpunkt (Wolken und Luftmasse heben sich auf) und trägt die Streuung jedes Sterns gegen seine Helligkeit auf. Konstante Sterne folgen einer zu schwachen Helligkeiten ansteigenden Kurve (Photonenrauschen); Sterne deutlich darüber sind **Kandidaten** (rote Kreise, nach Index gelistet). Ein Klick auf Punkt oder Zeile zeigt die Lichtkurve, **Diesen Stern an die Periodensuche senden** findet die Periode. So arbeitet Muniwins *varfind*: Kandidaten vor einer Entdeckungsmeldung in VSX prüfen.

## Extinktions- und Transformationskoeffizienten
**Bild → Photometrische Koeffizienten…**
- **Extinktion der Nacht:** aus den Vergleichssternen der gemessenen Lichtkurve (die Bilder müssen die Himmelsposition angeben, damit die Luftmasse bekannt ist): instrumentelle Helligkeit jedes Sterns gegen die Luftmasse, eine Steigung k für alle (mag pro Luftmasse), mit Bouguer-Diagramm. Typisch in V: 0,15–0,3 an einem guten Standort.
- **Transformationskoeffizienten:** zwei astrometrisch gelöste Bilder eines Standardfelds (z. B. ein Landolt-Feld oder M67) in zwei Filtern. Die Sterne werden auf beiden gemessen, ihre Helligkeiten kommen aus APASS (B, V, g′, r′, i′) oder Gaia (V, R, I), und die Koeffizienten werden nach AAVSO-Konvention angepasst: Tbv aus (B−V) gegen (b−v), Tv und Tb aus V−v und B−b gegen (B−V). Tragen Sie sie in Ihre Berichte oder in das Transformationswerkzeug der AAVSO ein.
