"""Reactive typing effects (optional: needs `evdev` + read access to /dev/input).

Without evdev installed, run_reactive() raises a clear error and the CLI
suggests `pip install evdev`. Nothing here is imported at startup.
"""
import time

from .protocol_direct import ZONES


def _load_evdev():
    try:
        import evdev  # type: ignore
    except ImportError as e:
        raise RuntimeError("reactive typing needs the 'evdev' package "
                           "(pip install evdev) + permission to /dev/input/event*") from e
    return evdev


class TypeRipple:
    """Expanding-ring state over keyboard LED order."""

    def __init__(self, color=(0, 180, 255), brightness=100):
        self.color = tuple(color)
        self.brightness = brightness
        self.waves = []  # [(origin_x, age)]

    def press(self, origin_x=0.5):
        self.waves.append([float(origin_x), 0.0])

    def frame(self):
        from .effects import ORDER, scale
        waves = []
        for ox, age in self.waves:
            age += 0.09
            if age < 1.2:
                waves.append([ox, age])
        self.waves = waves
        out = {}
        for (zone, ids) in [(0xA1, ZONES[0xA1][1])]:
            for led in ids:
                x = ORDER[zone][led]
                v = 0.10  # idle glow
                for ox, age in waves:
                    r = age * 0.9
                    d = abs(x - ox)
                    band = max(0.0, 1.0 - abs(d - r) / 0.08) * max(0.0, 1.0 - age)
                    v = min(1.0, v + band)
                f = self.brightness / 100.0 * min(1.0, v)
                out[(zone, led)] = tuple(max(0, min(255, round(c * f)))
                                         for c in self.color)
        # Other zones hold steady at 40%.
        for zone in (0xA2, 0xA3, 0xA4):
            for led in ZONES[zone][1]:
                out[(zone, led)] = scale(self.color, self.brightness * 0.4)
        return out


def run_reactive(kb, color=(0, 180, 255), brightness=100,
                 should_run=lambda: True):
    """Pump TypeRipple frames, feeding every key-press from all keyboards."""
    from .protocol_direct import build_perkey_frame
    from .hid import send_feature_report
    evdev = _load_evdev()
    import glob
    devs = []
    for path in glob.glob("/dev/input/event*"):
        try:
            d = evdev.InputDevice(path)
            caps = d.capabilities()
            if evdev.ecodes.EV_KEY in caps and evdev.ecodes.KEY_A in caps.get(evdev.ecodes.EV_KEY, []):
                devs.append(d)
        except OSError:
            continue
    if not devs:
        raise RuntimeError("no readable keyboards under /dev/input/event* "
                           "(add user to 'input' group or run with sudo)")
    ripple = TypeRipple(color, brightness)
    import select
    fdmap = {d.fd: d for d in devs}
    while should_run():
        r, _, _ = select.select(list(fdmap), [], [], 0.05)
        for fd in r:
            for ev in fdmap[fd].read():
                if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                    ripple.press(origin_x=0.5)
        kb.software_mode()
        for pkt in build_perkey_frame(ripple.frame()):
            send_feature_report(kb.hidraw, pkt)
        time.sleep(0.03)
