"""Detect the Legion 7 16ACHg6 ITE RGB controller (048d:c968)."""
import glob
import os
import re

VID = 0x048D
PID = 0xC968


class LegionKeyboardNotFound(Exception):
    pass


def find_keyboard():
    """Return (hidraw_path, vid, pid). Raises LegionKeyboardNotFound."""
    for uevent in sorted(glob.glob("/sys/class/hidraw/hidraw*/device/uevent")):
        try:
            with open(uevent) as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r"HID_ID=[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)", text)
        if not m or (int(m.group(1), 16), int(m.group(2), 16)) != (VID, PID):
            continue
        dev = "/dev/" + re.search(r"(hidraw\d+)", uevent).group(1)
        if os.path.exists(dev):
            return dev, VID, PID
    raise LegionKeyboardNotFound(
        "No ITE 048d:c968 controller found under /dev/hidraw*. "
        "Check lsusb | grep 048d.")
