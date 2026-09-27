"""Legion 7 16ACHg6 RGB backend (stdlib only)."""
from .detector import find_keyboard, LegionKeyboardNotFound
from .protocol_direct import LegionDirect, GROUPS, ZONES, parse_hex_color

__all__ = ["find_keyboard", "LegionKeyboardNotFound", "LegionDirect",
           "GROUPS", "ZONES", "parse_hex_color"]
