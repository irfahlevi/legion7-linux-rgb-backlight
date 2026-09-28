"""Per-LED protocol for Legion 7 16ACHg6 (ITE 048d:c968), as in OpenRGB's
LenovoUSBController ("Lenovo Legion 7 Gen 6" / Y760).

All packets are HID SET_FEATURE, report ID 0x07, 192 bytes:
  [07 B2]                      software mode: firmware obeys host frames
  [07 B1]                      hardware mode: back to firmware effects
  [07 zone N 00 (id R G B)*N]  set LEDs, N <= 47 per packet

Zones: A1 keyboard, A2 logo, A3 vents, A4 neon strip.
"""
import time

from .hid import send_feature_report

REPORT_ID = 0x07
REPORT_LEN = 192
MAX_LEDS_PER_PACKET = 0x2F
SOFTWARE_MODE = 0xB2
HARDWARE_MODE = 0xB1

# Union of OpenRGB's ANSI/ISO/JP Y760 keyboard LED ids.
_KEYBOARD_IDS = (
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c,
    0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x16, 0x17, 0x18, 0x19,
    0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x25, 0x26,
    0x27, 0x28, 0x29, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33,
    0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x40, 0x42, 0x43, 0x44,
    0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50,
    0x51, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f,
    0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x6a, 0x6b, 0x6c,
    0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
    0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x85, 0x86,
    0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92,
    0x93, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0,
    0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8,
)

ZONES = {
    0xA1: ("Keyboard", _KEYBOARD_IDS),
    0xA2: ("Logo", tuple(range(1, 14))),
    0xA3: ("Vents", tuple(range(1, 107))),
    0xA4: ("Neon strip", tuple(range(1, 100))),
}
GROUPS = tuple(ZONES)


def parse_hex_color(s):
    s = s.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"Bad color {s!r}: expected RRGGBB hex")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def scale(color, brightness_pct):
    """Software brightness: scale (r,g,b) by 0-100%."""
    f = max(0, min(100, brightness_pct)) / 100.0
    return tuple(max(0, min(255, round(c * f))) for c in color)


def _command(op):
    pkt = bytearray(REPORT_LEN)
    pkt[0] = REPORT_ID
    pkt[1] = op
    return bytes(pkt)


def build_frame(group_colors, brightness=100):
    """group_colors: {0xA1: (r,g,b), ...}; returns list of packets."""
    packets = []
    for zone, (_name, ids) in ZONES.items():
        if zone not in group_colors:
            continue
        r, g, b = scale(group_colors[zone], brightness)
        for start in range(0, len(ids), MAX_LEDS_PER_PACKET):
            chunk = ids[start:start + MAX_LEDS_PER_PACKET]
            pkt = bytearray(REPORT_LEN)
            pkt[0] = REPORT_ID
            pkt[1] = zone
            pkt[2] = len(chunk)
            for i, led in enumerate(chunk):
                pkt[4 + i * 4:8 + i * 4] = bytes((led, r, g, b))
            packets.append(bytes(pkt))
    return packets


class LegionDirect:
    def __init__(self, hidraw_path):
        self.hidraw = hidraw_path

    def software_mode(self):
        send_feature_report(self.hidraw, _command(SOFTWARE_MODE))

    def hardware_mode(self):
        send_feature_report(self.hidraw, _command(HARDWARE_MODE))

    def set(self, group_colors, brightness=100):
        if not 0 <= brightness <= 100:
            raise ValueError("brightness must be 0-100")
        self.software_mode()
        for pkt in build_frame(group_colors, brightness):
            send_feature_report(self.hidraw, pkt)

    def off(self):
        self.set({g: (0, 0, 0) for g in GROUPS})

    def breathe(self, group_colors, brightness=100, speed=2, should_run=lambda: True):
        """Software breathing loop; returns when should_run() is False.

        Re-asserts software mode (07 B2) every frame: on the 16ACHg6,
        Fn+Space is handled by the EC and forces the keyboard zone back
        to firmware effects (B1). Without this, LED frames sent after
        an Fn+Space press are ignored until the next Apply.
        """
        steps = max(4, 24 // speed)
        while should_run():
            for phase in list(range(steps)) + list(range(steps, 0, -1)):
                if not should_run():
                    return
                f = 0.05 + 0.95 * (phase / steps)
                self.software_mode()
                for pkt in build_frame(group_colors, f * brightness):
                    send_feature_report(self.hidraw, pkt)
                time.sleep(0.05)
