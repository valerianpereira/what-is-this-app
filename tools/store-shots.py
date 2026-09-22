#!/usr/bin/env python3
"""Frames the raw app screenshots into Play Store phone screenshots.

store/screenshots/raw-NN.png are 900x1800 captures of the app (a 360x720 CSS
viewport at 2.5x). Each becomes store/screenshots/NN.png: 1080x1920, a caption
in Fredoka above the app in a dark phone frame, on one of the app's own card
colours.

Run: python3 tools/store-shots.py
"""
import io
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "store/screenshots"
INK = "#241C15"

# (raw file, background, caption lines)
SLIDES = [
    ("raw-01.png", "#FFD166", ("Look. Say it.", "Hear it back.")),
    ("raw-02.png", "#8ED2A8", ("22 groups,", "325 real photos")),
    ("raw-03.png", "#9CC6F5", ("Five seconds", "to think…")),
    ("raw-04.png", "#FFA98A", ("…then the app", "says the word")),
    ("raw-05.png", "#C9B6F0", ("Ten pictures,", "then a cheer")),
]

_ttf = io.BytesIO()
_var = TTFont(ROOT / "app/fonts/fredoka-latin.woff2")
_var.flavor = None
_var.save(_ttf)


def fredoka(size, weight=700):
    font = ImageFont.truetype(io.BytesIO(_ttf.getvalue()), size)
    font.set_variation_by_axes([weight])
    return font


W, H = 1080, 1920
PHONE_W = 800
BEZEL = 16
RADIUS = 72

for i, (raw, bg, lines) in enumerate(SLIDES, 1):
    src = SHOTS / raw
    if not src.exists():
        print(f"skip {raw}: missing")
        continue
    canvas = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(canvas)

    font = fredoka(92)
    y = 110
    for line in lines:
        l, t, r, b = d.textbbox((0, 0), line, font=font)
        d.text(((W - (r - l)) / 2 - l, y), line, font=font, fill=INK)
        y += 108

    shot = Image.open(src).convert("RGBA")
    inner_w = PHONE_W - 2 * BEZEL
    shot = shot.resize((inner_w, int(shot.height * inner_w / shot.width)), Image.LANCZOS)
    # Round the screen's corners.
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, shot.width - 1, shot.height - 1], RADIUS - BEZEL, fill=255)
    shot.putalpha(mask)

    x0 = (W - PHONE_W) // 2
    y0 = 400
    # Soft shadow, then bezel, then screen. The phone runs off the bottom edge.
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x0, y0 + 30, x0 + PHONE_W, y0 + shot.height + 2 * BEZEL + 30], RADIUS, fill=(36, 28, 21, 110))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)))
    d.rounded_rectangle([x0, y0, x0 + PHONE_W, y0 + shot.height + 2 * BEZEL], RADIUS, fill=INK)
    canvas.alpha_composite(shot, (x0 + BEZEL, y0 + BEZEL))

    out = SHOTS / f"{i:02d}.png"
    out.unlink(missing_ok=True)
    canvas.convert("RGB").save(out)
    print("wrote", out.relative_to(ROOT))
