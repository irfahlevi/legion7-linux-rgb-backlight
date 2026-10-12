"""Software effects engine (stdlib only, no hardware needed for frames).

Each effect is a pure function of phase t in [0,1) -> {(zone, led): (r,g,b)}.
run_effect() pumps frames via LegionDirect, re-asserting 07 B2 every frame
so Fn+Space EC takeovers are retaken within ~50ms.
"""
import colorsys
import math
import random
import time

from .protocol_direct import GROUPS, ZONES, scale

EFFECTS = (
    "static",
    "breath",
    "rainbow_wave",
    "rainbow_screw",
    "color_wave",
    "color_pulse",
    "color_shift",
    "visor",
    "rain",
    "smooth",
    "ripple",
)
DIRECTIONS = ("ltr", "rtl")

FRAME_DT = 0.05


def _hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _order_fractions():
    """{zone: {led_id: x in [0,1)}} using sorted-ID order as X axis."""
    out = {}
    for zone, (_name, ids) in ZONES.items():
        s = sorted(ids)
        n = max(1, len(s))
        out[zone] = {led: i / n for i, led in enumerate(s)}
    return out


ORDER = _order_fractions()


def _dir(x, direction):
    return 1.0 - x if direction == "rtl" else x


def frame_static(group_colors, brightness=100):
    return {(z, led): scale(c, brightness)
            for z, c in group_colors.items() for led in ZONES[z][1]}


def frame_breath(group_colors, brightness, t):
    f = 0.05 + 0.95 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))
    return {(z, led): scale(c, f * brightness)
            for z, c in group_colors.items() for led in ZONES[z][1]}


def frame_rainbow_wave(t, brightness=100, direction="ltr", zones=GROUPS):
    out = {}
    for zone in zones:
        for led, x in ORDER[zone].items():
            out[(zone, led)] = scale(_hsv((_dir(x, direction) + t) % 1.0), brightness)
    return out


def frame_rainbow_screw(t, brightness=100, direction="ltr", zones=GROUPS):
    # Diagonal-ish: offset each zone differently for a "screw" feel.
    offsets = {0xA1: 0.0, 0xA2: 0.25, 0xA3: 0.5, 0xA4: 0.75}
    out = {}
    for zone in zones:
        for led, x in ORDER[zone].items():
            h = (_dir(x, direction) + t + offsets.get(zone, 0.0)) % 1.0
            out[(zone, led)] = scale(_hsv(h), brightness)
    return out


def frame_color_wave(group_colors, t, brightness=100, direction="ltr"):
    """Two-color gradient sweeping: base color <-> white across X."""
    out = {}
    for zone, base in group_colors.items():
        if zone not in ZONES:
            continue
        for led, x in ORDER[zone].items():
            w = 0.5 - 0.5 * math.cos(((_dir(x, direction) + t) % 1.0) * 2 * math.pi)
            r = int(round(base[0] + (255 - base[0]) * w))
            g = int(round(base[1] + (255 - base[1]) * w))
            b = int(round(base[2] + (255 - base[2]) * w))
            out[(zone, led)] = scale((r, g, b), brightness)
    return out


def frame_color_pulse(group_colors, t, brightness=100):
    f = 0.5 - 0.5 * math.cos(t * 2 * math.pi)
    return {(z, led): scale(c, f * brightness)
            for z, c in group_colors.items() for led in ZONES[z][1]}


def frame_color_shift(t, brightness=100, zones=GROUPS):
    c = _hsv(t)
    return {(z, led): scale(c, brightness) for z in zones for led in ZONES[z][1]}


def frame_visor(color, t, brightness=100, direction="ltr", width=0.12,
                zones=(0xA1, 0xA3, 0xA4)):
    """Scanner bar bouncing left-right (Knight-Rider)."""
    tri = 1.0 - abs(1.0 - 2.0 * (t % 1.0))  # 0->1->0
    pos = 1.0 - tri if direction == "rtl" else tri
    out = {}
    for zone in zones:
        if zone not in ZONES:
            continue
        for led, x in ORDER[zone].items():
            d = abs(x - pos) / max(1e-6, width)
            f = max(0.0, 1.0 - d)
            f = f * f
            out[(zone, led)] = scale(color, f * brightness)
    # Logo holds steady.
    if 0xA2 in ZONES and 0xA2 not in zones:
        for led in ZONES[0xA2][1]:
            out[(0xA2, led)] = scale(color, brightness * 0.35)
    return out


def frame_smooth(group_colors, t, brightness=100):
    """Slow crossfade between the given zone colors (all zones -> blend)."""
    colors = [group_colors.get(z, (0, 0, 0)) for z in GROUPS]
    n = max(1, len(colors))
    ft = (t % 1.0) * n
    i = int(ft) % n
    j = (i + 1) % n
    f = ft - int(ft)
    a, b = colors[i], colors[j]
    c = (int(round(a[0] + (b[0] - a[0]) * f)),
         int(round(a[1] + (b[1] - a[1]) * f)),
         int(round(a[2] + (b[2] - a[2]) * f)))
    return {(z, led): scale(c, brightness) for z in GROUPS for led in ZONES[z][1]}


class RainState:
    """Fading droplets; call step() each frame."""

    def __init__(self, zones=GROUPS, seed=None):
        self.zones = tuple(z for z in zones if z in ZONES)
        self.rng = random.Random(seed)
        self.drops = []  # [(zone, led, color, life 1->0)]

    def step(self, base_color, brightness=100, spawn=0.25):
        if self.rng.random() < spawn and self.zones:
            zone = self.rng.choice(self.zones)
            led = self.rng.choice(ZONES[zone][1])
            self.drops.append([zone, led, base_color, 1.0])
        out = {}
        alive = []
        for zone, led, color, life in self.drops:
            life -= 0.08
            if life > 0:
                alive.append([zone, led, color, life])
                out[(zone, led)] = scale(color, life * brightness)
        self.drops = alive
        # Background: dim base color at 8%.
        for zone in self.zones:
            for led in ZONES[zone][1]:
                out.setdefault((zone, led), scale(base_color, brightness * 0.08))
        return out


def build_frame_for_effect(name, group_colors, brightness, t, direction="ltr",
                           rain_state=None):
    base = next(iter(group_colors.values())) if group_colors else (0, 180, 255)
    if name == "static":
        return frame_static(group_colors, brightness)
    if name == "breath":
        return frame_breath(group_colors, brightness, t)
    if name == "rainbow_wave":
        return frame_rainbow_wave(t, brightness, direction)
    if name == "rainbow_screw":
        return frame_rainbow_screw(t, brightness, direction)
    if name == "color_wave":
        return frame_color_wave(group_colors, t, brightness, direction)
    if name == "color_pulse":
        return frame_color_pulse(group_colors, t, brightness)
    if name == "color_shift":
        return frame_color_shift(t, brightness)
    if name == "visor":
        return frame_visor(base, t, brightness, direction)
    if name == "smooth":
        return frame_smooth(group_colors, t, brightness)
    if name == "rain":
        st = rain_state or RainState()
        return st.step(base, brightness)
    if name == "ripple":
        # Without key events, ripple degrades to an expanding ring loop.
        return frame_visor(base, t, brightness, direction, width=0.25,
                           zones=GROUPS)
    raise ValueError(f"unknown effect {name!r}; pick from {EFFECTS}")


def run_effect(kb, name, group_colors, brightness=100, speed=2,
               direction="ltr", should_run=lambda: True):
    """Pump frames until should_run() is False. Static = single apply."""
    from .protocol_direct import build_perkey_frame
    from .hid import send_feature_report
    if name == "static":
        kb.set(group_colors, brightness)
        return
    rain = RainState() if name == "rain" else None
    # speed 1..4 -> cycles per second approx 0.12..0.6
    cps = {1: 0.12, 2: 0.25, 3: 0.45, 4: 0.7}.get(int(speed), 0.25)
    t = 0.0
    while should_run():
        frame = build_frame_for_effect(name, group_colors, brightness, t,
                                       direction, rain)
        kb.software_mode()
        for pkt in build_perkey_frame(frame):
            send_feature_report(kb.hidraw, pkt)
        time.sleep(FRAME_DT)
        t = (t + FRAME_DT * cps) % 1.0
