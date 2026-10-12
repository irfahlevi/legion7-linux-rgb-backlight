"""Named profiles: JSON store under ~/.config/legion-rgb/profiles/."""
import json
import os
import re

from .effects import DIRECTIONS, EFFECTS
from .privilege import config_dir

VALID_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,47}$")


def profiles_dir():
    return os.path.join(config_dir(), "profiles")


def _path(name):
    return os.path.join(profiles_dir(), name + ".json")


def validate(doc):
    if doc.get("effect", "static") not in EFFECTS:
        raise ValueError(f"bad effect {doc.get('effect')!r}")
    if doc.get("direction", "ltr") not in DIRECTIONS:
        raise ValueError(f"bad direction {doc.get('direction')!r}")
    b = int(doc.get("brightness", 100))
    if not 0 <= b <= 100:
        raise ValueError("brightness must be 0-100")
    s = int(doc.get("speed", 2))
    if s not in (1, 2, 3, 4):
        raise ValueError("speed must be 1-4")
    colors = doc.get("colors")
    if colors is not None:
        if not isinstance(colors, list) or len(colors) not in (1, 4):
            raise ValueError("colors must be a list of 1 or 4 [r,g,b]")
        for c in colors:
            if (not isinstance(c, (list, tuple)) or len(c) != 3
                    or not all(isinstance(v, int) and 0 <= v <= 255 for v in c)):
                raise ValueError(f"bad color {c!r}")
    perkey = doc.get("perkey")
    if perkey is not None:
        if not isinstance(perkey, dict):
            raise ValueError("perkey must be {\"A1:0x01\": [r,g,b]}")
        for k, v in perkey.items():
            if not re.match(r"^[A-Fa-f0-9]{2}:[0-9A-Fa-fxX]+$", str(k)):
                raise ValueError(f"bad perkey key {k!r}")
            if (not isinstance(v, (list, tuple)) or len(v) != 3
                    or not all(isinstance(x, int) and 0 <= x <= 255 for x in v)):
                raise ValueError(f"bad perkey color {k}={v!r}")
    return {
        "effect": doc.get("effect", "static"),
        "colors": [list(c) for c in colors] if colors else [[0, 180, 255]] * 4,
        "brightness": b,
        "speed": s,
        "direction": doc.get("direction", "ltr"),
        **({"perkey": {k: list(v) for k, v in perkey.items()}} if perkey else {}),
    }


def check_name(name):
    if not VALID_NAME.match(name or ""):
        raise ValueError("profile name: 1-48 chars, letters/digits/space/_/-")
    return name


def save(name, doc):
    check_name(name)
    clean = validate(doc)
    os.makedirs(profiles_dir(), exist_ok=True)
    with open(_path(name), "w") as f:
        json.dump(clean, f, indent=2)
    return clean


def load(name):
    with open(_path(check_name(name))) as f:
        return validate(json.load(f))


def delete(name):
    os.remove(_path(check_name(name)))


def list_names():
    try:
        files = os.listdir(profiles_dir())
    except OSError:
        return []
    return sorted(f[:-5] for f in files if f.endswith(".json"))
