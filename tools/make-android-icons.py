#!/usr/bin/env python3
"""Draws the app's one mark everywhere it appears: a fan of three picture
cards — mint and sky behind, a white one in front with a big orange '?' in
Fredoka — the cards the child flips through in the game, on the app's amber.

Writes the Android launcher icons (adaptive + legacy + monochrome), the splash,
and the Play Store art: store/icon-512.png and store/feature-1024x500.png.

Run: python3 tools/make-android-icons.py   (or npm run brand)
"""
import io
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "android/app/src/main/res"
STORE = ROOT / "store"
AMBER, ORANGE, SHADOW, CREAM, INK = "#FFD166", "#E0532F", "#B23A1B", "#FFFCF6", "#241C15"
MINT, MINT_SHADOW = "#8ED2A8", "#5FAE7E"
SKY, SKY_SHADOW = "#9CC6F5", "#6A9BD4"

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


def _card(size, fill, shadow, angle, glyph=None, mono=False):
    """One tilted rounded card as an RGBA layer, drawn supersampled and shrunk
    so the tilt stays clean. glyph draws a '?' on it; mono punches it out."""
    ss = 4
    n = int(size * ss * 1.6)
    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = size * ss
    x0 = y0 = (n - w) / 2
    r = w * 0.17
    if shadow and not mono:
        d.rounded_rectangle([x0, y0 + w * 0.075, x0 + w, y0 + w * 1.075], r, fill=shadow)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + w], r, fill="white" if mono else fill)
    if glyph:
        g = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        f = fredoka(int(w * 0.80))
        l, t, rt, b = gd.textbbox((0, 0), "?", font=f)   # centre on ink, not line box
        gd.text((x0 + w / 2 - (l + rt) / 2, y0 + w / 2 - (t + b) / 2), "?", font=f, fill=ORANGE)
        if mono:
            layer.putalpha(ImageChops.subtract(layer.getchannel("A"), g.getchannel("A")))
        else:
            layer.alpha_composite(g)
    layer = layer.rotate(angle, resample=Image.BICUBIC)
    return layer.resize((n // ss, n // ss), Image.LANCZOS)


def mark(img, cx, cy, size, mono=False):
    """The fan of three cards, centred on (cx, cy). size = front card width."""
    back = size * 0.86
    for fill, shadow, angle, dx, dy in (
        (MINT, MINT_SHADOW, -22, -0.30, 0.06),
        (SKY, SKY_SHADOW, 19, 0.30, 0.06),
    ):
        layer = _card(back, fill, shadow, angle, mono=mono)
        img.alpha_composite(layer, (int(cx + dx * size - layer.width / 2), int(cy + dy * size - layer.height / 2)))
    layer = _card(size, "white", SHADOW, -6, glyph=True, mono=mono)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def write(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)  # macOS refuses to overwrite some existing PNGs in place
    img.save(path)
    return path


made = []
for bucket, scale in BUCKETS.items():
    # Adaptive layers: 108dp canvas, artwork inside the 66dp safe circle so no
    # launcher mask clips it. The fan is wider than it is tall, so size by width.
    n = int(108 * scale)
    fg = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    mark(fg, n / 2, n / 2, n * 0.34)
    made.append(write(fg, RES / f"mipmap-{bucket}/ic_launcher_foreground.png"))
    mono = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    mark(mono, n / 2, n / 2, n * 0.34, mono=True)
    made.append(write(mono, RES / f"mipmap-{bucket}/ic_launcher_monochrome.png"))

    # Legacy icons for pre-Android-8 launchers: full-bleed, no mask applied.
    n = int(48 * scale)
    for name, mask_round in (("ic_launcher", False), ("ic_launcher_round", True)):
        legacy = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(legacy)
        if mask_round:
            d.ellipse([0, 0, n - 1, n - 1], fill=AMBER)
        else:
            d.rounded_rectangle([0, 0, n - 1, n - 1], int(n * 0.18), fill=AMBER)
        mark(legacy, n / 2, n / 2, n * (0.40 if mask_round else 0.44))
        made.append(write(legacy, RES / f"mipmap-{bucket}/{name}.png"))

# Splash: the launcher theme stretches this behind the WebView while it boots.
# The mark sits on an amber tile, as on the launcher, so the white card reads
# against the cream page.
for folder, size in [("drawable", (1080, 1920))] + \
        [(f"drawable-port-{b}", (1080, 1920)) for b in BUCKETS] + \
        [(f"drawable-land-{b}", (1920, 1080)) for b in BUCKETS]:
    splash = Image.new("RGBA", size, CREAM)
    d = ImageDraw.Draw(splash)
    tile = min(size) * 0.34
    cx, cy = size[0] / 2, size[1] / 2 - min(size) * 0.03
    d.rounded_rectangle([cx - tile, cy - tile, cx + tile, cy + tile], tile * 0.44, fill=AMBER)
    mark(splash, cx, cy, tile * 0.82)
    made.append(write(splash.convert("RGB"), RES / folder / "splash.png"))

(RES / "values/ic_launcher_background.xml").write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    "<resources>\n"
    f'    <color name="ic_launcher_background">{AMBER}</color>\n'
    "</resources>\n"
)

# Play Store: 512x512 hi-res icon (Play rounds the corners itself) and the
# 1024x500 feature graphic shown above the listing.
icon = Image.new("RGBA", (512, 512), AMBER)
mark(icon, 256, 256, 512 * 0.44)
made.append(write(icon.convert("RGB"), STORE / "icon-512.png"))

feat = Image.new("RGBA", (1024, 500), AMBER)
d = ImageDraw.Draw(feat)
# Soft cream disc behind the mark so it lifts off the amber.
d.ellipse([70, 40, 490, 460], fill="#FFE7B8")
mark(feat, 280, 250, 200)
title = fredoka(104)
d.text((530, 112), "What", font=title, fill=INK)
d.text((530, 212), "is this?", font=title, fill=INK)
d.text((534, 348), "Picture words for 2–4 year olds", font=fredoka(31, 500), fill="#6B4A1E")
made.append(write(feat.convert("RGB"), STORE / "feature-1024x500.png"))

print(f"wrote {len(made)} images + ic_launcher_background.xml")
