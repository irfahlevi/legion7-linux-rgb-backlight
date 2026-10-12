"""Shared state helpers: load/apply last.json + profile docs."""
import json
import os

from .effects import run_effect
from .protocol_direct import GROUPS, ZONES, scale


def load_doc(path):
    with open(path) as f:
        return json.load(f)


def apply_doc(kb, doc, run_animated=True):
    """Apply doc (last.json/profile). Returns 'animated' if loop ran."""
    effect = (doc.get("effect") or "static").lower()
    brightness = int(doc.get("brightness", 100))
    speed = int(doc.get("speed", 2))
    direction = doc.get("direction", "ltr")
    colors = [tuple(c) for c in doc.get("colors", [[0, 180, 255]] * 4)]
    if len(colors) == 1:
        colors = colors * 4
    groups = {g: c for g, c in zip(GROUPS, colors)}
    perkey = doc.get("perkey")
    if perkey and effect == "static":
        led_colors = {}
        for k, v in perkey.items():
            zm, lm = str(k).split(":")
            led_colors[(int(zm, 0), int(lm, 0))] = scale(tuple(v), brightness)
        kb.set_perkey(led_colors)
        return "static"
    if effect in ("hardware",):
        kb.hardware_mode()
        return "hardware"
    if effect in ("mirror", "reactive", "audio"):
        # No screen/input at login-restore time: fall back to static base.
        kb.set(groups, brightness)
        return "static-fallback"
    if effect in ("static", "off"):
        kb.set(groups, brightness)
        return "static"
    if effect == "breath" and hasattr(kb, "breathe"):
        if run_animated:
            kb.breathe(groups, brightness, speed)
            return "animated"
        kb.set(groups, brightness)
        return "static"
    if run_animated:
        run_effect(kb, effect, groups, brightness, speed, direction)
        return "animated"
    kb.set(groups, brightness)
    return "static"
