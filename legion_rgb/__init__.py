"""Legion 7 RGB backend (stdlib only for core)."""
from .detector import find_keyboard, find_all, LegionKeyboardNotFound, SUPPORTED_PIDS, PID_NAMES
from .protocol_direct import LegionDirect, GROUPS, ZONES, parse_hex_color, build_perkey_frame, build_frame

__all__ = ["find_keyboard", "find_all", "LegionKeyboardNotFound", "LegionDirect",
           "GROUPS", "ZONES", "parse_hex_color", "SUPPORTED_PIDS", "PID_NAMES",
           "build_perkey_frame", "build_frame"]
