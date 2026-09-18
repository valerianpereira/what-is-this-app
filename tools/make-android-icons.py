#!/usr/bin/env python3
"""Generates the Android launcher icons and the splash from one mark: a tilted
white picture card, chunky shadow, big orange '?' in Fredoka — the same card
the child taps in the game, on the app's amber.

Run: python3 tools/make-android-icons.py
"""
import io
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "android/app/src/main/res"
AMBER, ORANGE, SHADOW, CREAM = "#FFD166", "#E0532F", "#B23A1B", "#FFFCF6"

# mdpi is the 1x baseline; every other bucket is a multiple of it.
BUCKETS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

# Fredoka ships as woff2 for the WebView; Pillow only reads ttf/otf.
_ttf = io.BytesIO()
_var = TTFont(ROOT / "app/fonts/fredoka-latin.woff2")
_var.flavor = None
_var.save(_ttf)


def fredoka(size, weight=700):
    font = ImageFont.truetype(io.BytesIO(_ttf.getvalue()), size)
    font.set_variation_by_axes([weight])
    return font


def card(img, cx, cy, size, shadow=True, angle=-7):
    """Tilted white card with a '?' on it, centred on (cx, cy)."""
    ss = 4  # supersample, then rotate and shrink — keeps the tilt clean
    n = int(size * ss * 1.5)
    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = size * ss
    x0 = y0 = (n - w) / 2
    r = w * 0.17
    if shadow:
        d.rounded_rectangle([x0, y0 + w * 0.075, x0 + w, y0 + w * 1.075], r, fill=SHADOW)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + w], r, fill="white")
    f = fredoka(int(w * 0.80))
    # Centre on the glyph's ink, not the font's line box.
    l, t, rt, b = d.textbbox((0, 0), "?", font=f)
    d.text((x0 + w / 2 - (l + rt) / 2, y0 + w / 2 - (t + b) / 2), "?", font=f, fill=ORANGE)
    layer = layer.rotate(angle, resample=Image.BICUBIC)
    layer = layer.resize((n // ss, n // ss), Image.LANCZOS)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


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
    card(fg, n / 2, n / 2, n * 0.42)
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
        card(legacy, n / 2, n / 2, n * 0.44)
        made.append(write(legacy, RES / f"mipmap-{bucket}/{name}.png"))

# Splash: the launcher theme stretches this behind the WebView while it boots.
# White on cream would vanish, so the card sits on an amber tile, as on the
# launcher.
for folder, size in [("drawable", (1080, 1920))] + \
        [(f"drawable-port-{b}", (1080, 1920)) for b in BUCKETS] + \
        [(f"drawable-land-{b}", (1920, 1080)) for b in BUCKETS]:
    splash = Image.new("RGBA", size, CREAM)
    d = ImageDraw.Draw(splash)
    tile = min(size) * 0.34
    cx, cy = size[0] / 2, size[1] / 2 - min(size) * 0.03
    d.rounded_rectangle([cx - tile, cy - tile, cx + tile, cy + tile], tile * 0.44, fill=AMBER)
    card(splash, cx, cy, tile * 0.88)
    made.append(write(splash.convert("RGB"), RES / folder / "splash.png"))

(RES / "values/ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<resources>\n"
    f'    <color name="ic_launcher_background">{AMBER}</color>\n'
    "</resources>\n"
)

print(f"wrote {len(made)} images + ic_launcher_background.xml")
