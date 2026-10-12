"""Detect Legion ITE RGB controllers (048d:c968 / c967)."""
import glob
import os
import re

VID = 0x048D
# c968 = Legion 7 16ACHg6 (tested). c967 = Legion 7S / Slim 7 Gen 6
# (same protocol, reported working in OpenRGB; treated as supported).
SUPPORTED_PIDS = (0xC968, 0xC967)
PID_NAMES = {
    0xC968: "Legion 7 16ACHg6",
    0xC967: "Legion 7S / Slim 7 Gen 6",
}


class LegionKeyboardNotFound(Exception):
    pass


def _pid_override():
    """Allow LEGION_RGB_PID=c967 for testing/quirks."""
    raw = os.environ.get("LEGION_RGB_PID", "").strip().lower().lstrip("0x")
    if not raw:
        return None
    try:
        return int(raw, 16)
    except ValueError:
        return None


def find_all():
    """Return [(hidraw_path, vid, pid)] for all supported controllers."""
    extra = _pid_override()
    pids = set(SUPPORTED_PIDS)
    if extra:
        pids.add(extra)
    found = []
    for uevent in sorted(glob.glob("/sys/class/hidraw/hidraw*/device/uevent")):
        try:
            with open(uevent) as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r"HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)", text)
        if not m:
            continue
        vid, pid = int(m.group(1), 16), int(m.group(2), 16)
        if vid != VID or pid not in pids:
            continue
        dm = re.search(r"(hidraw\d+)", uevent)
        if not dm:
            continue
        dev = "/dev/" + dm.group(1)
        if os.path.exists(dev):
            found.append((dev, vid, pid))
    return found


def find_keyboard():
    """Return (hidraw_path, vid, pid). Raises LegionKeyboardNotFound."""
    found = find_all()
    if found:
        return found[0]
    raise LegionKeyboardNotFound(
        "No supported ITE controller found (048d:c968/c967) under /dev/hidraw*. "
        "Check lsusb | grep 048d.")
