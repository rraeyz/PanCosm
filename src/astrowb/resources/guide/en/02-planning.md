# Planning
The **Plan** page tells you when your targets can be observed tonight and which eclipses or transits happen during the night. It opens in a window of its own (its block on the Start page or the Window menu), with its own menus: **Targets** (add a target, add it with its ephemeris, remove the selected one) and **Night** (plan the night, exposure time, make a schedule, send it to the Observing window). The icons under the menus do the same; **View → Toolbar text** shows their names.

## Your site
Enter the **latitude** (degrees, north positive), **longitude** (degrees, east positive) and **height** (metres) of the observatory. These are remembered. They are also used for the barycentric correction of radial velocities and for twilight times.

Type the name of a known observatory in **Site** (for example *TUG*, *Roque de los Muchachos*, *Kitt Peak*): a list of about 380 observatories appears while you type, and choosing one fills in the latitude, longitude and height. The list comes from astropy and works offline.

## The night and the altitude limit
- **Night starting on:** the date of the evening the night begins.
- **Lowest altitude (°):** below this a target counts as not observable (trees, buildings, thick air). 20–30° is typical.

## Adding targets
Type a **name** (looked up in SIMBAD, e.g. `HAT-P-32`, `V523 Cas`, `M 42`) or **coordinates** (`02:04:10 +46:41:16` or decimal degrees) and press **Add**.

**Add with ephemeris** looks the name up in the AAVSO **VSX** catalogue (variable stars) or the **NASA Exoplanet Archive** (planets such as `HAT-P-32 b`) and fills in the coordinates, period, epoch and duration, so the night's eclipses or transits are listed at once. For eclipsing binaries the epoch is VSX's time of primary minimum (HJD; it differs from BJD by seconds) and *Secondary* is ticked; for pulsating stars only the period is shown. Needs the internet.

- Names that were found once are cached, so planning also works without internet later.
- **Remove selected** removes rows from the table.

## Eclipses and transits
For eclipsing binaries and exoplanets fill in the columns of the target table:

- **T0 (BJD):** a time of primary minimum or mid-transit (BJD_TDB).
- **Period (d)** and **Duration (d)** of the eclipse or transit.
- **Secondary:** tick it to also list secondary minima (at phase 0.5).

The plan then lists every event of the night with its start, middle and end in UTC and whether it is **observable** (*yes*, *partly* or not at all) given the altitude limit and darkness.

## Reading the plot
**Plan the night** draws the altitude of each target against UTC time for the whole night, with the local time on the top axis (**Local time (hours from UTC)**: *Auto* takes this computer's time zone on that date, summer time included; type the offset for an observatory elsewhere, e.g. 1 for La Palma in summer). The chart's texts are in English whatever the interface language, so it can go into a paper or report as it is:

- the blue shading darkens step by step from sunset through civil (−6°), nautical (−12°) and astronomical (−18°) twilight; the darkest part is the astronomical night;
- the dashed grey curve is the **Moon**, with its illuminated fraction in the legend;
- the dotted red line is your lowest altitude;
- the right axis gives the **airmass**; photometry is best below airmass 2 (altitude above 30°);
- red triangles mark the middle of each eclipse or transit on the target's curve.

The line under the plot gives the start and end of the astronomical night in UTC and in local time, and the number of events; the events table also gives each middle in local time. Near the poles in summer there may be **no astronomical night**.

## From the plan to observing
**Make a schedule** (after *Plan the night*) turns the night into a programme for several targets: every observable eclipse or transit first, with 30 minutes of baseline before and after (when two overlap, the target higher in your list wins); the rest of the dark time in one-hour blocks, each going to the target that stays highest above your altitude limit. **Send to the Observe page** gives every block to the sequence, with its start and end; the exposure rows you set there are used for every target.

Use the times of the plan as **Start** and **End** of a sequence on the Observe page (or type `dusk` and `dawn`), or start from an automation template such as *Eclipsing binary night* or *Exoplanet transit*.

**Exposure time…** works out how long to expose for a wanted signal-to-noise from the CCD equation: give the star's magnitude, your system's zero point (the magnitude that gives one electron per second; measure it once on a star of known magnitude), the sky, read noise, dark current and aperture. It also says after how many seconds the star's brightest pixel saturates, and suggests several shorter frames when the exposure would be too long. The values are remembered.
