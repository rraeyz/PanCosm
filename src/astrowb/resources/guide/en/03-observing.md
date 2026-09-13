# Observing and safety
The **Observe** page controls the telescope, camera, focuser, filter wheel, dome and guider. The devices are owned by a separate **observatory process** with a safety supervisor, so the telescope stays protected even if the window is closed or crashes. It opens in a window of its own (its block on the Start page or the Window menu), with its own menus.

## Configuring the observatory
**Set up observatory…** opens a dialog for everything below: the site, the devices (**Find Alpaca devices on the network** lists every ASCOM Alpaca device that answers; INDI devices are added by hand with the server address and the INDI device name), the safety limits, PHD2 and whether other computers may connect. It warns about risky choices, for example a mount without a weather sensor. **Save and start** writes the file and starts the observatory on this computer; **Open…** edits an existing file.

The file it writes is plain JSON and can also be edited by hand:

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

- Each device is either **ASCOM Alpaca** (`"alpaca": "host:port"` and the device number) or **INDI** (`"indi": "host:port"` and the INDI device name). Classic ASCOM drivers on Windows are reached through ASCOM Remote (Alpaca).
- `monitor` is a safety monitor (cloud/rain sensor), `conditions` an observing-conditions device (humidity, wind, rain, clouds).
- `listen` is the address of the observatory's API. Keep it on `127.0.0.1` unless you want to control it from another computer.

## Starting and connecting
- **Start observatory on this computer…** asks for the configuration file, starts the observatory process in the background and connects. A secret **token** is created and written into the file the first time.
- To control a remote observatory, start it there with `--observatory config.json`, then type its **Observatory address** and **Token** here and press **Connect**.
- **HTTPS:** tick *Encrypt the connection* in the set-up (it is ticked for you when other computers may connect). The observatory then makes its own certificate and prints its **fingerprint** when it starts; type it into *Certificate fingerprint* on the computer you control it from, and use an `https://` address. The application only talks to the observatory with exactly that certificate, so nobody in between can read the token or the commands. On the local computer the fingerprint is filled in for you.
- The coloured line shows the state: **Safe** (green), **NOT SAFE** with the reasons (red), or **No connection**.

## The safety supervisor
Every few seconds the supervisor checks the rules. When anything is unsafe it **aborts the exposure, stops the sequence, parks the mount and closes the dome**. It also refuses slews to unsafe positions. The rules (in `"rules"` of the configuration):

- `min_alt` (15°) and an optional `horizon` profile `[[az, alt], …]`;
- `sun_max_alt` (−6°): above it, it is day — at sunrise the telescope is parked and the dome closed;
- `sun_min_sep` (30°) between the target and the Sun;
- `max_humidity` (90 %), `max_wind` (12 m/s), `max_rain_rate` (any rain), `max_cloud_cover`;
- `link_timeout_s` (30 s): a device that stops answering counts as unsafe.

After an unsafe period nothing restarts by itself: check the telescope and press **Resume** (refused while still unsafe).

## Moving the telescope
Type coordinates (`02:04:10 +46:41:16`) and press **Slew**. **Park**, **Abort** (stops everything at once), **Resume** and **Autofocus** are next to it. The mount line shows altitude, azimuth and whether it is tracking or parked.

**Centre** puts the target exactly in the middle: the observatory slews, takes a short frame, plate-solves it, tells the mount where it really points (sync) and slews again, until the target is within 30″. This needs ASTAP or astrometry.net on the observatory computer.

**Polar alignment** measures how far the RA axis of an equatorial mount is from the celestial pole: point roughly north (south in the southern hemisphere) at declination 60–80°, press the button; three solved frames are taken while only the RA axis turns by 30° steps. The result says how much to raise or lower the axis and how far to turn it east or west, in arcminutes. Adjust and measure again until the error is a few arcminutes.

## Camera, focuser and filter
- **Preview:** one exposure of the given length with the chosen filter, saved in the `preview` sub-folder of the output folder, and opened in the viewer at once (framing and focusing). When the observatory runs on another computer the frame is first copied here, into `observations/preview` in your home folder.
- **Cooler:** **Cool to** sets the camera temperature and switches the cooler on; **Off** switches it off. Cool down slowly before the night and warm up before switching the camera off.
- **Focuser:** **Move** sends the focuser to an absolute position.
- **Filter:** the list is read from the filter wheel; **Change** turns the wheel.
- The grey line shows the camera temperature and cooler state, the focuser position and the current filter.

## Autofocus
**Autofocus** takes frames at several focuser positions, measures the stars' half-flux radius (HFR) and fits a V-curve; the focuser is moved to the best position. Point at a field with stars first.

## Sequences
On the right:

- **Target name** and **RA Dec** (leave the coordinates empty for darks and bias: no slew).
- **Dither every N frames (PHD2):** shifts the pointing slightly between frames through PHD2, which averages out hot pixels and fixed patterns.
- **Start:** empty for now, `dusk`, or a UTC time such as `2026-11-15T21:30`. **End:** empty to stop after the counts, `dawn`, or a UTC time — with an end the exposure list **repeats until then** (time series through an eclipse or a whole night).
- **Save to:** the folder on the observatory computer.
- The exposure table: **Type** (light, dark, bias, flat), **Filter**, **Exposure (s)**, **Count**, **Binning**. **Add exposure row** / **Remove row**.
- **Start sequence.** Progress and the number of frames written appear under the table; the log on the left lists every event.

When the observatory runs on another computer, the frames of a finished sequence are copied to this one, into `observations/<last part of the Save to folder>` in your home folder. The observatory only hands out frames it has saved itself; no other file on that computer can be read over the network.

Every frame is saved as FITS with the headers the later steps need: type, exposure, start time (UTC), filter, binning, temperature, gain, object and coordinates, site.

## Meridian flips and guiding
German equatorial mounts are flipped automatically when the target crosses the meridian; guiding is stopped and restarted around it. Guiding and dithering use **PHD2** (configure `"phd2"`).

## Sky flats
Select the row with the filter and count you want, point the telescope at the flat spot (tracking off) and press **Sky flats**. In twilight the exposure time follows the sky brightness so every flat reaches a good level.

## An unattended night
Give the targets `dusk` as start and `dawn` as end. The sequence waits for darkness, repeats until dawn, and the supervisor parks the telescope at sunrise or when the weather turns. The *Eclipsing binary night* and *End-of-night calibration* automation templates fill the sequence for you.

## Test with simulators first
Before using real hardware, run the same configuration against simulators (ASCOM Alpaca simulators, or `indiserver` with the INDI simulator drivers). Check that unsafe conditions park the mount and close the dome.

## Camera settings, focus offsets, rotator and flat panel
Each exposure row has **Gain**, **Offset**, **Read-out mode** (its number in the camera's list) and a **Sub-frame** `x, y, width, height` in binned pixels. Empty cells keep the camera's own setting and the full frame. The values go into every FITS header (GAIN, OFFSET, READOUTM, XORGSUBF/YORGSUBF). Take darks, bias and flats with the same gain, offset and sub-frame as the lights, or calibration will not match them.

**Filter focus offsets** and **temperature compensation** are set in *Set up the observatory…*: offsets as `L=0, B=-30, V=15` (focuser steps; the focuser moves by the difference when the filter changes), and a coefficient in steps per °C (measure it by focusing at two temperatures). During a sequence the focuser follows its own temperature whenever it has changed by 0.5 °C.

A **rotator** (ASCOM Alpaca) turns to the **Rotator angle** of the target before the slew; the angle is written as ROTATANG.

**Panel flats** use an Alpaca *CoverCalibrator* (flip-flat or light panel): the cover closes, the panel lights up, the exposure time is adjusted until the frames reach the target level, and the panel is switched off at the end. The selected row gives the filter and the number of flats.
