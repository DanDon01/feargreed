"""Display HAT Mini wrapper, with a mock fallback for desktop development."""

from PIL import Image

from theme import WIDTH, HEIGHT

try:
    from displayhatmini import DisplayHATMini
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class Buttons:
    A, B, X, Y = "A", "B", "X", "Y"


# When the screen is flipped 180, the buttons swap corners: the top-left
# button (A) ends up where Y was, and so on. Remap so a logical press
# still matches its on-screen position.
_FLIP_MAP = {Buttons.A: Buttons.Y, Buttons.B: Buttons.X,
             Buttons.X: Buttons.B, Buttons.Y: Buttons.A}


class PiDisplay:
    def __init__(self):
        self.buffer = Image.new("RGB", (WIDTH, HEIGHT))
        self.dhm = DisplayHATMini(self.buffer, backlight_pwm=True)
        self.flipped = False
        self._pins = {
            Buttons.A: self.dhm.BUTTON_A,
            Buttons.B: self.dhm.BUTTON_B,
            Buttons.X: self.dhm.BUTTON_X,
            Buttons.Y: self.dhm.BUTTON_Y,
        }

    def set_flip(self, flipped):
        self.flipped = bool(flipped)

    def show(self, image):
        if self.flipped:
            image = image.transpose(Image.Transpose.ROTATE_180)
        self.dhm.st7789.display(image)

    def set_backlight(self, level):
        self.dhm.set_backlight(level)

    def set_led(self, r, g, b):
        self.dhm.set_led(r, g, b)

    def pressed(self, name):
        if self.flipped:
            name = _FLIP_MAP[name]
        return self.dhm.read_button(self._pins[name])

    def close(self):
        self.set_led(0, 0, 0)
        self.set_backlight(0)


class MockDisplay:
    """Headless stand-in: counts frames and can save them for preview."""

    def __init__(self, save_dir=None, save_every=0):
        self.save_dir = save_dir
        self.save_every = save_every
        self.frames = 0
        self.flipped = False

    def set_flip(self, flipped):
        self.flipped = bool(flipped)

    def show(self, image):
        self.frames += 1
        if self.save_dir and self.save_every and self.frames % self.save_every == 0:
            image.save(f"{self.save_dir}/frame_{self.frames:05d}.png")

    def set_backlight(self, level):
        pass

    def set_led(self, r, g, b):
        pass

    def pressed(self, name):
        return False

    def close(self):
        pass


def make_display():
    return PiDisplay() if HAVE_HARDWARE else MockDisplay()
