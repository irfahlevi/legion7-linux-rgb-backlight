#!/usr/bin/env python3
"""Regenerate assets/icon-*.png (needs Pillow; not required at runtime)."""
import colorsys
import os

from PIL import Image, ImageDraw, ImageFilter

SS = 4
N = 256 * SS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def hue(x):
    r, g, b = colorsys.hsv_to_rgb(x % 1.0, 0.85, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def s(v):
    return int(v * SS)


def main():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((s(8), s(8), s(248), s(248)), radius=s(52), fill=(22, 24, 30, 255))

    keys = []
    rows = [(0, 9), (1, 9), (2, 8), (3, 7)]
    top, kh, gap = 54, 22, 7
    for r, count in rows:
        width = 208 - r * 14
        kw = (width - gap * (count - 1)) / count
        x0 = 128 - width / 2
        y = top + r * (kh + gap)
        for i in range(count):
            x = x0 + i * (kw + gap)
            keys.append((x, y, x + kw, y + kh))
    y = top + 4 * (kh + gap)
    keys.append((74, y, 182, y + kh))

    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for x0, y0, x1, y1 in keys:
        c = hue(((x0 + x1) / 2 - 28) / 230 + (y0 - top) / 900)
        g.rounded_rectangle((s(x0 - 3), s(y0 - 3), s(x1 + 3), s(y1 + 3)), radius=s(7), fill=c + (200,))
    strip_y = 218
    for i in range(160):
        x = 48 + i
        g.line((s(x), s(strip_y), s(x + 1), s(strip_y)), fill=hue(i / 160) + (255,), width=s(10))
    glow = glow.filter(ImageFilter.GaussianBlur(s(9)))
    img.alpha_composite(glow)

    d = ImageDraw.Draw(img)
    for x0, y0, x1, y1 in keys:
        c = hue(((x0 + x1) / 2 - 28) / 230 + (y0 - top) / 900)
        d.rounded_rectangle((s(x0), s(y0), s(x1), s(y1)), radius=s(5), fill=(34, 37, 45, 255),
                            outline=c + (255,), width=s(2.2))
    for i in range(160):
        x = 48 + i
        d.line((s(x), s(strip_y), s(x + 1), s(strip_y)), fill=hue(i / 160) + (255,), width=s(5))

    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).rounded_rectangle((s(8), s(8), s(248), s(248)), radius=s(52), fill=255)
    img.putalpha(Image.composite(img.getchannel("A"), mask, mask))

    os.makedirs(OUT, exist_ok=True)
    for size in (256, 128, 64, 48):
        img.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"icon-{size}.png"))


if __name__ == "__main__":
    main()
