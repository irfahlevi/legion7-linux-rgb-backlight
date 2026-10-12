"""Self-test for core logic (hardware-free; stubs Linux-only hid)."""
import sys
import types
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fake = types.ModuleType("legion_rgb.hid")
sent = []
fake.send_feature_report = lambda path, data: sent.append((path, data))
sys.modules["legion_rgb.hid"] = fake

from legion_rgb.protocol_direct import (
    build_frame, build_perkey_frame, GROUPS, ZONES, LegionDirect)
from legion_rgb.effects import build_frame_for_effect, EFFECTS, RainState
from legion_rgb import profiles

print("effects:", EFFECTS)
f = build_frame({g: (255, 0, 0) for g in GROUPS})
print("zone packets:", len(f), "len0:", len(f[0]))
assert all(len(p) == 192 and p[0] == 0x07 for p in f)

pk = {(0xA1, 0x01): (1, 2, 3), (0xA2, 1): (4, 5, 6)}
p2 = build_perkey_frame(pk)
print("perkey packets:", len(p2))
assert p2[0][1] in (0xA1, 0xA2)

fr = build_frame_for_effect("rainbow_wave", {g: (0, 180, 255) for g in GROUPS}, 100, 0.25, "ltr")
print("rainbow leds:", len(fr))
fr2 = build_frame_for_effect("visor", {g: (255, 0, 0) for g in GROUPS}, 100, 0.5, "ltr")
print("visor leds:", len(fr2))
for name in EFFECTS:
    build_frame_for_effect(name, {g: (10, 20, 30) for g in GROUPS}, 80, 0.3, "rtl")
print("all effects build OK")

rs = RainState(seed=1)
rfr = rs.step((0, 0, 255))
print("rain leds:", len(rfr))

d = profiles.validate({"effect": "color_wave", "colors": [[1, 2, 3]],
                       "brightness": 50, "speed": 3, "direction": "rtl"})
print("profile ok:", d["effect"], d["brightness"])
try:
    profiles.validate({"effect": "nope"})
    raise SystemExit("validate should have failed")
except ValueError:
    print("invalid effect correctly rejected")

# LegionDirect.set with stubbed HID
kb = LegionDirect("/dev/hidraw0")
kb.set({g: (1, 2, 3) for g in GROUPS})
kb.set_perkey({(0xA1, 0x01): (9, 9, 9)})
print("stubbed HID sends:", len(sent))
assert len(sent) > 0

print("ALL_LOGIC_OK")
