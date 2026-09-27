"""hidraw HID feature-report sender (stdlib only: os + fcntl)."""
import array
import fcntl
import os


def _hidiocs_feature(length):
    # _IOC(READ|WRITE, 'H', 0x06, len)
    return (3 << 30) | (length << 16) | (ord("H") << 8) | 0x06


def send_feature_report(hidraw_path, data: bytes):
    """Send one HID SET_FEATURE report. data[0] must be the report ID."""
    if len(data) < 2 or data[0] == 0x00:
        raise ValueError("Payload must start with a non-zero report ID")
    buf = array.array("B", data)
    fd = os.open(hidraw_path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, _hidiocs_feature(len(buf)), buf, True)
    finally:
        os.close(fd)
