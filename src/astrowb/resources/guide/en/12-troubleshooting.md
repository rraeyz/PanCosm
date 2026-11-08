# Troubleshooting
Common problems and what to do.

## A task failed
The Tasks panel shows *failed* and a window gives the error. Typical causes: a file that cannot be read, a missing input (the message names it), too few stars or frames. The window stays usable; correct the input and run the step again. The project's history keeps the failed run with its settings.

The error window shows the error itself; **Show Details…** has the full report. To check the installation and every web service the application uses (SIMBAD, VizieR, MAST, ZTF, AAVSO, SkyBoT, …), choose **Help → Check the installation and internet services** (or run the application from a terminal with `--check-online`): each line says OK or FAIL and why. A FAIL for one service is usually that service or your network; a FAIL in the first lines means part of the installation is missing — please report it.

## The calibration says frames are missing
"no flat for filter …", "no dark for … s", "no bias" — those lights are still calibrated without that correction. Take the missing frames (same filter, binning, exposure and temperature) or accept the result. Darks of another exposure can be used only with bias frames.

## Stars are not found or the light curve jumps
- Make sure the images are calibrated and of one filter.
- Increase the aperture for defocused or trailed stars; move the sky annulus away from neighbours.
- If the field drifts a lot, check that the target is inside every frame; frames where it is not are skipped.
- Choose other comparison stars: one of them may be variable or saturated.

## Times look wrong
Check `DATE-OBS` (it must be the UTC start of the exposure) and `EXPTIME` in the header. For BJD the target coordinates and the site must be known (header or the fields in the window).

## Plate solving does nothing
Install ASTAP with a star database (or astrometry.net with index files) and try again. Approximate coordinates in the header make it much faster. Very small fields need a deeper database.

## The observatory says NOT SAFE
The reasons are listed: Sun up, target too low, humidity, wind, rain, a device not answering… Fix the cause, then press **Resume**. While anything is still unsafe, Resume is refused — that is intended.

## No connection to the observatory
Check that the observatory process is running (start it again with **Start observatory on this computer…**), the address and the token. A firewall may block the port on a remote computer.

## The graphics card is not used
**Settings → Processing device** shows the mode; the status bar names the device. With *Automatic* the card is used only when it is faster. Update the graphics driver if no card is found; everything also works on the processor.

## Where are my settings and files?
Settings, plugins and automations are in the user settings folder (on Linux `~/.config/…`, on Windows `%LOCALAPPDATA%\…`, on macOS `~/Library/Application Support/…`). Projects and results are where you save them.

## Updates
**Help → Check for updates…** asks the project's release page whether a newer version exists and links to its download. The application never checks on its own. Install the new version over the old one; settings, plugins and automations are kept.

## Reporting a problem
Note what you did, the error text, and if possible attach a small file that shows the problem. The project file contains the exact settings of every run, which helps reproduce it.
