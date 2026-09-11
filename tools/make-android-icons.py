#!/usr/bin/env python3
"""Generates the Android launcher icons and splash from the same marks as the
PWA icon: amber field, orange rounded square, white question mark.

Run: python3 tools/make-android-icons.py
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "android/app/src/main/res"
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
AMBER, ORANGE, SHADOW, CREAM = "#FFD166", "#E0532F", "#B23A1B", "#FFFCF6"

# mdpi is the 1x baseline; every other bucket is a multiple of it.
BUCKETS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def question(img, box, radius_frac=0.29, shadow=True):
    """Orange rounded square with a white '?', drawn inside a square box."""
    d = ImageDraw.Draw(img)
    x0, y0, size = box
    r = int(size * radius_frac)
    if shadow:
        d.rounded_rectangle([x0, y0 + size * 0.055, x0 + size, y0 + size * 1.055], r, fill=SHADOW)
    d.rounded_rectangle([x0, y0, x0 + size, y0 + size], r, fill=ORANGE)
    f = ImageFont.truetype(FONT, int(size * 0.72))
    # Centre on the glyph's ink, not the font's line box.
    l, t, rt, b = d.textbbox((0, 0), "?", font=f)
    d.text((x0 + size / 2 - (l + rt) / 2, y0 + size / 2 - (t + b) / 2), "?", font=f, fill="white")


def write(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


made = []
for bucket, scale in BUCKETS.items():
    # Adaptive foreground: 108dp canvas, artwork kept inside the 72dp safe zone
    # so no launcher mask can clip it.
    n = int(108 * scale)
    fg = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    art = int(n * 0.62)
    question(fg, ((n - art) // 2, int((n - art) / 2 - art * 0.03), art))
    made.append(write(fg, RES / f"mipmap-{bucket}/ic_launcher_foreground.png"))

    # Legacy icons for pre-Android-8 launchers: full-bleed, no mask applied.
    n = int(48 * scale)
    for name, mask_round in (("ic_launcher", False), ("ic_launcher_round", True)):
        legacy = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(legacy)
        if mask_round:
            d.ellipse([0, 0, n - 1, n - 1], fill=AMBER)
        else:
            d.rounded_rectangle([0, 0, n - 1, n - 1], int(n * 0.18), fill=AMBER)
        art = int(n * 0.58)
        question(legacy, ((n - art) // 2, int((n - art) / 2 - art * 0.03), art), shadow=False)
        made.append(write(legacy, RES / f"mipmap-{bucket}/{name}.png"))

# Splash: the launcher theme stretches this behind the WebView while it boots.
splash = Image.new("RGB", (1080, 1920), CREAM)
art = 420
question(splash, ((1080 - art) // 2, (1920 - art) // 2 - 40, art))
for folder in ["drawable"] + [f"drawable-port-{b}" for b in BUCKETS]:
    made.append(write(splash, RES / folder / "splash.png"))

(RES / "values/ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<resources>\n"
    f'    <color name="ic_launcher_background">{AMBER}</color>\n'
    "</resources>\n"
)

print(f"wrote {len(made)} images + ic_launcher_background.xml")
