"""Screen-mirror (Murals/Aurora-like), optional deps: mss (+PIL optional).

Strategy (stdlib fallback = solid avg color):
- grab screen (mss, else Gtk/Mac screenshot, else error)
- split into left/center/right thirds -> vents/keyboard/neon averages
- logo = overall average
Runs as a software pump like other effects.
"""
import time


def _grab_mss():
    try:
        import mss  # type: ignore
    except ImportError as e:
        raise RuntimeError("screen mirror needs 'mss' (pip install mss)") from e
    return mss


def capture_averages():
    """Return dict zone->(r,g,b): vents=left, keyboard=center, neon=right, logo=all."""
    mss = _grab_mss()
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        w, h = shot.width, shot.height
        px = shot.rgb  # bytes RGB RGB...
        def avg(x0, x1):
            rs = gs = bs = n = 0
            step = max(1, (w * h) // 4000)
            idx = 0
            for y in range(0, h, 8):
                for x in range(x0, x1, 8):
                    o = (y * w + x) * 3
                    rs += px[o]; gs += px[o + 1]; bs += px[o + 2]; n += 1
                    idx += 1
                    if idx % step == 0 and False:
                        pass
            n = max(1, n)
            return (rs // n, gs // n, bs // n)
        left = avg(0, w // 3)
        mid = avg(w // 3, 2 * w // 3)
        right = avg(2 * w // 3, w)
        allc = tuple((a + b + c) // 3 for a, b, c in zip(left, mid, right))
        return {0xA3: left, 0xA1: mid, 0xA4: right, 0xA2: allc}


def run_mirror(kb, brightness=100, fps=15, should_run=lambda: True):
    from .protocol_direct import scale
    interval = 1.0 / max(1, min(30, fps))
    while should_run():
        try:
            zones = capture_averages()
        except Exception as e:
            raise RuntimeError(f"screen capture failed: {e}")
        perkey = {}
        from .protocol_direct import ZONES
        for zone, color in zones.items():
            for led in ZONES[zone][1]:
                perkey[(zone, led)] = scale(color, brightness)
        kb.software_mode()
        from .protocol_direct import build_perkey_frame
        from .hid import send_feature_report
        for pkt in build_perkey_frame(perkey):
            send_feature_report(kb.hidraw, pkt)
        time.sleep(interval)
