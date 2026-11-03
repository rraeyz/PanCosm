"""In-process ASCOM-like devices for tests (same attribute names as alpyca's clients)."""

import numpy as np


class Fail:
    """Mixin: set .broken = True to make every access raise like a dead network link."""

    broken = False

    def __getattribute__(self, name):
        if not name.startswith("_") and name != "broken" and object.__getattribute__(self, "broken"):
            raise ConnectionError("device not answering")
        return object.__getattribute__(self, name)


class FakeMount(Fail):
    def __init__(self):
        self.Connected = True
        self.RightAscension, self.Declination = 0.0, 90.0
        self.Tracking, self.AtPark, self.Slewing = False, True, False
        self.EquatorialSystem = 1
        self.parks = 0

    def Unpark(self):
        self.AtPark = False

    def SlewToCoordinatesAsync(self, ra, dec):
        if self.AtPark:
            raise RuntimeError("parked")
        self.RightAscension, self.Declination = ra, dec

    def AbortSlew(self):
        self.Slewing = False

    def Park(self):
        self.AtPark, self.Tracking = True, False
        self.parks += 1


class FakeDome(Fail):
    def __init__(self):
        self.Connected, self.ShutterStatus, self.closed = True, 0, 0

    def CloseShutter(self):
        self.ShutterStatus, self.closed = 1, self.closed + 1

    def Park(self):
        pass


class FakeMonitor(Fail):
    def __init__(self):
        self.Connected, self.IsSafe = True, True


class FakeCamera(Fail):
    def __init__(self, shape=(40, 50)):
        self.Connected, self.ImageReady, self.CCDTemperature = True, False, -10.0
        self.BinX = self.BinY = 1
        self.shape, self.aborted, self.exposures = shape, 0, []
        self.Gain = 100

    def StartExposure(self, duration, light):
        self.exposures.append((duration, light))
        self.ImageReady = True

    @property
    def ImageArray(self):
        rng = np.random.default_rng(len(self.exposures))
        return (1000 + rng.normal(0, 5, self.shape)).astype(np.int32).T  # ASCOM arrays are [x][y]

    def AbortExposure(self):
        self.aborted += 1
        self.ImageReady = False


class FakeFilterWheel(Fail):
    def __init__(self):
        self.Connected, self.Names, self.Position = True, ["L", "B", "V", "R"], 0


class FakeFocuser(Fail):
    def __init__(self, position=5000):
        self.Connected, self.Position, self.IsMoving = True, position, False

    def Move(self, p):
        self.Position = p


class FocusCamera(FakeCamera):
    """Stars whose size follows a hyperbola in focuser position (best focus at `best`)."""

    def __init__(self, focuser, best=5130, shape=(120, 160)):
        super().__init__(shape)
        self.focuser, self.best = focuser, best
        rng = np.random.default_rng(1)
        self.stars = [
            (rng.uniform(15, shape[1] - 15), rng.uniform(15, shape[0] - 15), rng.uniform(3e4, 1e5)) for _ in range(25)
        ]

    @property
    def ImageArray(self):
        sigma = np.sqrt(1.2**2 + ((self.focuser.Position - self.best) / 60.0) ** 2)
        y, x = np.mgrid[: self.shape[0], : self.shape[1]]
        img = np.full(self.shape, 500.0)
        for sx, sy, f in self.stars:
            img += f / (2 * np.pi * sigma**2) * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / (2 * sigma**2))
        img += np.random.default_rng(len(self.exposures)).normal(0, 5, self.shape)
        return img.astype(np.int32).T


class FakeRotator(Fail):
    def __init__(self):
        self.Connected, self.Position, self.IsMoving, self.moves = True, 0.0, False, []

    def MoveAbsolute(self, angle):
        self.moves.append(angle)
        self.Position = angle % 360

    def Halt(self):
        pass


class FakePanel(Fail):
    """Alpaca CoverCalibrator: CoverState 1 closed / 3 open, CalibratorState 1 off / 3 ready."""

    def __init__(self):
        self.Connected, self.CoverState, self.CalibratorState, self.MaxBrightness = True, 3, 1, 255
        self.Brightness, self.log = 0, []

    def CloseCover(self):
        self.CoverState = 1
        self.log.append("close")

    def OpenCover(self):
        self.CoverState = 3
        self.log.append("open")

    def CalibratorOn(self, brightness):
        self.Brightness, self.CalibratorState = brightness, 3
        self.log.append(f"on {brightness}")

    def CalibratorOff(self):
        self.Brightness, self.CalibratorState = 0, 1
        self.log.append("off")
