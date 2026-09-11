#!/usr/bin/env python3
"""Composes a labelled contact sheet of the card photos, for eyeballing whether
any of them are engravings, collages or the wrong subject.

  python3 tools/contact-sheet.py out.jpg            # every card
  python3 tools/contact-sheet.py out.jpg obj-food-rice cat-home ...
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).resolve().parent.parent / "app"
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
CELL, LABEL, COLS, PAD = 150, 18, 6, 6

out = Path(sys.argv[1])
slots = sys.argv[2:]
if not slots:
    slug = lambda s: s.lower().replace(" ", "-")
    slots = []
    for c in json.loads((APP / "data/cards.json").read_text())["categories"]:
        slots.append(f"cat-{c['id']}")
        slots += [f"obj-{c['id']}-{slug(i['name'])}" for i in c["items"]]

credits = json.loads((APP / "img/credits.json").read_text())
rows = (len(slots) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (CELL + PAD) + PAD, rows * (CELL + LABEL + PAD) + PAD), "white")
draw = ImageDraw.Draw(sheet)

for i, slot in enumerate(slots):
    x = PAD + (i % COLS) * (CELL + PAD)
    y = PAD + (i // COLS) * (CELL + LABEL + PAD)
    im = Image.open(APP / "img" / f"{slot}.webp").convert("RGB")
    # Square centre crop, so the sheet shows what the app's square frame shows.
    side = min(im.size)
    im = im.crop((
        (im.width - side) // 2, (im.height - side) // 2,
        (im.width + side) // 2, (im.height + side) // 2,
    )).resize((CELL, CELL), Image.LANCZOS)
    sheet.paste(im, (x, y))
    name = credits.get(slot, {}).get("name", slot)
    draw.text((x + CELL / 2, y + CELL + 3), name, font=FONT, fill="black", anchor="ma")

sheet.save(out, quality=88)
print(f"{out}  {len(slots)} cards  {sheet.width}x{sheet.height}")
