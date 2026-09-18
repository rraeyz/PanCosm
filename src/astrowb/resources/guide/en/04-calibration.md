# Calibration
The **Calibration** window turns raw frames into calibrated images: it recognises bias, dark, flat and light frames, builds master frames, matches the right masters to every light frame and applies them. Optionally it aligns and stacks the result. Calibration opens in a window of its own (its block on the Start page or the Window menu), with its own menus; the progress of a scan, a calibration or a stack shows in its status bar, with Cancel. Its menus hold every button in the order of the work: **Frames** (lights folder, calibration frames folder, add folder, scan, remove, clear), **Masters** (the options), **Process** (calibrate, stack, drizzle) and **Send** (to Photometry); the toolbar has the main ones.

![The Calibration window](images/en/window-calibrate.jpg)

## 1. Scan the raw frames
**Two folders, as a night is usually kept:** put the light frames (your data) in **Lights** and the bias, dark and flat frames in **BDF**. Every frame in the light folder is a light whatever its name — science frames are usually named after the star (`nsvs01286630_017.fits`); only a frame whose header states bias, dark or flat counts as that. The BDF folder is sorted into bias, dark and flat. Everything in one folder? Give it as **BDF** only and leave **Lights** empty: the frames are then sorted by header and name as below.

Choose the folder with your raw frames (lights, bias, darks and flats may be mixed, sub-folders included) and press **Scan**. The table lists every file with its **type**, **exposure**, **filter**, **temperature** and **binning**.

A folder chosen with **Browse…** or **Add folder…** is scanned at once; **Scan** reads a typed folder.

- The type comes from the `IMAGETYP` / `FRAME` header (Light Frame, Bias, Dark, Flat Field…) and, when it is missing, from the file name. Words in the name: bias / zero / offset, dark, flat / twilight, arc / lamp; a frame of 0 s is a bias. Every other frame is a **light** — science frames are usually named after the star (`nsvs01286630_017.fits`, `NY_Vir_R_003.fit`) and say nothing of a type; only a type the header states that the program does not know (FOCUS, TEST…) is **unknown** and left out (listed below the table). **Double-click a type** in the table to change it; the files are not changed. A frame that does not belong (a master from an earlier run, a test frame) is taken out with **Remove from the list** or the Delete key; **Clear** empties the folders and the list to choose them again. Ctrl+Z brings either back.
- Files that cannot be read and files of unknown type are listed under the table and ignored.
- The same list says which calibration frames are **missing**, for example "no flat for filter 'R'" — those lights are still calibrated, without that correction, and you are told so.

Sub-folders are read too. If the lights and the calibration frames are in separate folders (for example *Light* and *BDF*), choose the folder that holds both. Frames kept somewhere else, such as a calibration library, are added with **Add folder…** (several folders are separated by `;`). When no light frame is found the list below the table says so, and **Calibrate** stays off until there is one.

Archive raw frames work as they come: ESO's `.fits.Z` files (Unix compress) are decompressed into fits_from_raw, ESO frame types (DPR TYPE: BIAS, FLAT, STD, WAVE, OBJECT) are recognised, and the grism or grating of a spectrograph is part of the filter, so a flat taken with another grism is never used.

## How masters are matched
- **Bias:** same binning and size.
- **Dark:** same binning, the same exposure time and a temperature within 2 °C. A dark of another exposure is scaled to the light's exposure only when bias frames exist (dark current is proportional to time once the bias is removed).
- **Flat:** same filter and binning; flats are bias/dark-subtracted and normalised to a median of 1.
- Each master is the sigma-clipped mean of its frames; **Rejection (sigma)** (default 3) removes satellites, cosmic rays and hot pixels that appear in only some frames.

## 2. Output folder and options
Choose where master frames and calibrated images are written. Raw files are never changed.

- **Remove cosmic rays from lights** cleans single-pixel hits with the L.A.Cosmic method (astroscrappy). Use it for long exposures; it is not needed for short photometric series.

- **Scale the dark to each light (dark optimisation):** finds, for every light, the dark scale that leaves the least noise (least squares: hot pixels must vanish; stars and sky do not correlate with the dark), as MaxIm DL's auto-optimise. Use it when the camera temperature drifted or darks were taken at another temperature; the scale is written to the header (DARKSCAL).
- **Repair hot and dead pixels (defect map from the masters):** pixels far above the master dark's level (hot) or below half of the master flat's (dead, dust shadows too deep to correct) are replaced in every calibrated light by the median of their good neighbours. The map is saved next to the masters (`defects_00.fits`) and named in the header (CALDEF).
- **Overscan and trimming** happen by themselves when the frames' headers have BIASSEC (the overscan strip: its level is fitted row by row — a cubic along the readout with clipping, as IRAF's overscan fit — and subtracted, so bias structure along the readout goes too) and TRIMSEC or DATASEC (only that part is kept), as IRAF ccdproc does for professional CCDs.
- **Linearity correction** (in More calibration options): type the coefficients c0 c1 c2 … of your camera's non-linearity, e.g. `0 1 4e-6`; every raw value v becomes c0 + c1·v + c2·v² + … before overscan, bias, dark and flat, as in AstroImageJ. Take them from the maker's sheet or from flats of rising exposure (the counts per second must stay constant). Leave it empty for a linear camera. Corrected frames carry LINCORR in the header.

- **Spectra: do not divide by the flat:** tick it for echelle and long-slit frames. Their flat is near zero between the orders, so dividing by it would blow up the noise (IRAF users normalise such a flat first with apflatten / apnormalize). Bias and dark are still subtracted; the master flat is still made — give it to the Spectroscopy window, which traces the orders on it and divides by its blaze. The defect map then comes from the dark only.

## 3. Calibrate
Press **Calibrate**. The task runs in the background; when it finishes you see how many images were calibrated and how many masters were written. Each calibrated image records in its header which masters were used (`CALB`, `CALD`, `CALF`), so you can always check. **4. Measure them in the Photometry window →** then sends the calibrated lights there and opens it (with several filters you choose one: a light curve is measured in one filter). The right-click menu of the Images window has the same: **Send the open images to Photometry**.

## 4. Align and stack
**Stacking…** aligns the calibrated images on the stars (translation found by cross-correlation) and combines them with a sigma-clipped mean into one deep image. A coverage map, saved as a second extension of the file, tells how many frames contributed to each pixel. Stack only frames of the same filter. Stacking is optional and **not for a light curve**: a stack has one time only, while photometry measures every single image. Stack for a deep picture, astrometry of faint objects or a colour image.

## Stacking options
The choices next to the stack button work as in Siril, PixInsight or MaxIm DL:

- **Combine:** *mean* (lowest noise), *median* (robust, about 25 % noisier) or *sum* (the mean times the number of frames, so the level is that of a long exposure even where a frame does not cover the pixel).
- **Reject** values that do not belong (satellites, planes, cosmic rays, hot pixels) before combining: *sigma clipping* (IRAF imcombine's sigclip: outside median ± σ × the rms about the median, repeated, where ten or more frames cover the pixel; with fewer frames one outlier can never be 3 σ off that rms, so there the median / MAD spread is used), *sigma clipping, median / MAD spread* (the robust spread for every pixel), *winsorized sigma clipping* (the spread is measured with outliers pulled in, better with few frames), *min / max* (drops the **Low** lowest and **High** highest values of every pixel) or *percentile clipping* (outside median × (1 − low) … median × (1 + high), given in percent; for 3–6 frames). *none* keeps everything. **Rejection (sigma)** above sets σ.
- **Normalise** frames taken through changing sky before combining: *multiplicative* scales each frame's sky to the first frame's (thin clouds, airmass), *additive* shifts it (Moon, twilight gradient level).
- **Weights:** *by noise* gives each frame the weight 1 / σ² of its sky noise, so poor frames count less.

- **Align:** *shift only* (cross-correlation, fast) for frames from one night with one mount orientation; *star patterns* when frames are turned or scaled — after a meridian flip, from an alt-az mount or a rotator, or from another telescope. Triangles of the brightest stars are matched (their side ratios do not change with rotation or scale; Groth 1986, Valdes et al. 1995) and each frame's rotation, scale and shift are fitted; the history in the header lists them.

The header of the stack records the choices (STACKMTH, STACKNRM, STACKWGT) and the weight of every frame.

## Drizzle
For undersampled images (stars only one or two pixels wide) taken with small dithers between frames, tick **Drizzle onto a 2× finer grid** before stacking. Each pixel is shrunk to 60 % of its size and laid on a grid with twice as many pixels at its aligned position (Fruchter & Hook 2002); with eight or more dithered frames the stars come out sharper than in a normal stack. The flux is kept, the sky coordinates (WCS) are scaled, and the weight of every output pixel is saved as the second extension. Remove cosmic rays during calibration first: drizzle does not reject outliers.

## Colour cameras and DSLR raw files
- **Camera raw files** (CR2, CR3, NEF, ARW, DNG, ORF, RW2, RAF, PEF…) in the chosen folder are converted when you press **Scan**: each becomes a FITS file in the sub-folder `fits_from_raw`, with the sensor values untouched (no white balance, no gamma, no interpolation). Put them in folders named like `bias`, `darks`, `flats`, `lights`: the folder name gives the frame type. Exposure time, ISO, black and white level are read from the file. Fujifilm X-Trans and Foveon sensors are not 2 × 2 Bayer sensors and are refused.
- **Time**: a DSLR stores its own clock, often local time and minutes off. Set **DSLR clock − UTC** (e.g. 3 for a clock on Turkish time) before scanning, and compare the camera clock with a time signal: a timing error goes straight into minima and O−C. The original reading is kept as DATE-CAM. Until you set it, the computer's own offset from UTC is used (a camera on the same local time as the computer). The value is remembered and used for every camera raw file and phone picture opened in any window (Photometry, Images, Variable star search…); the Photometry window shows which offset its frames have.
- **Colour (one-shot-colour) cameras** write BAYERPAT; DSLR files get it from the raw file. With **Colour camera: each colour as its own image** (on by default) the mosaic is calibrated as it is, then each light is written as three half-size images `_R`, `_G`, `_B` (filters TR, TG, TB): one value per 2 × 2 cell, the green being the mean of the two green pixels, with no interpolation that would mix pixels and change the star profiles. Hot and dead pixels are repaired from pixels of the same colour. This is the method of the AAVSO DSLR Observing Manual; the green channel (TG) is closest to Johnson V, so it goes to the Photometry window.
- **Stacks are made per filter**: `stack_TR.fits`, `stack_TG.fits`, `stack_TB.fits` (and for monochrome cameras, one per filter). Combine them into a colour picture with **Colour → Colour image from three filters…** in the Images window.

## Tips
- Take at least 20 bias and 10–20 darks at the same temperature as the lights; 10–20 flats per filter, with the mean around half of the full well.
- Do not move the focuser or rotate the camera between flats and lights: dust rings move with them.
- The *End-of-night calibration and stack* automation does scanning, calibration and stacking in one go.
