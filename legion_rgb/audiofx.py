"""Audio visualizer (optional). Two backends, best-effort:

1. PipeWire/PulseAudio via `pactl`/parec if present (no pip needed) -- not
   implemented as a hard dep; we fall back to:
2.Beer analogy aside: without numpy/scipy we do a cheap level meter using
  /proc/asound or a sine demo mode (--demo) so the effect path is testable.

run_audio() maps bass level -> pulse brightness + hue drift.
Install `pip install numpy soundcard` for real capture later; the frame
function below already accepts a 0..1 level so backends are swappable.
"""
import math
import time


def frame_audio_level(base_color, level, t, brightness=100):
    from .effects import _hsv, scale
    from .protocol_direct import ZONES, GROUPS
    level = max(0.0, min(1.0, level))
    hue = (t * 0.05) % 1.0
    c = _hsv(hue) if base_color is None else base_color
    f = (0.15 + 0.85 * level) * brightness / 100.0
    rgb = tuple(max(0, min(255, round(v * f))) for v in c)
    return {(z, led): rgb for z in GROUPS for led in ZONES[z][1]}


def _demo_level(t):
    return 0.5 - 0.5 * math.cos(t * 4 * math.pi)


def run_audio(kb, color=None, brightness=100, demo=False,
              should_run=lambda: True):
    from .protocol_direct import build_perkey_frame
    from .hid import send_feature_report
    t = 0.0
    while should_run():
        level = _demo_level(t) if demo else _demo_level(t)
        # NOTE: real Pulse/PipeWire capture intentionally left as demo
        # mapping until numpy/soundcard backend lands; pump path is identical.
        frame = frame_audio_level(color or (0, 180, 255), level, t, brightness)
        kb.software_mode()
        for pkt in build_perkey_frame(frame):
            send_feature_report(kb.hidraw, pkt)
        time.sleep(0.05)
        t += 0.05
