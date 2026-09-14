#!/usr/bin/env python3
"""Draws the cards that have no photograph: shapes and colours.

Wikipedia's shape articles lead with annotated geometry diagrams and its colour
articles lead with an object of that colour (Red -> strawberries), which would
teach a two-year-old the wrong word. So these two categories are rendered here
instead of downloaded, and marked "drawn": true in cards.json so
tools/fetch-images.mjs leaves them alone. Output matches the fetcher's: one
720px .webp per slot in photos/, plus a credit in app/data/credits.json.
"""
import json, math, os, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'photos')
CREDITS = os.path.join(ROOT, 'app', 'data', 'credits.json')
SIZE, SS = 720, 4              # render at 4x, downscale -> cheap antialiasing
INK, PAPER, FIELD = '#241C15', '#FFFCF6', '#F3ECE1'

COLOURS = {
    'Red': '#E23B2E', 'Blue': '#2E6FD8', 'Yellow': '#F5C518', 'Green': '#3CA34D',
    'Orange': '#EF7C1B', 'Purple': '#7B3FA0', 'Pink': '#F07CAE', 'Brown': '#8B5A2B',
    'Black': '#1B1B1B', 'White': '#FFFFFF', 'Grey': '#9AA0A6', 'Gold': '#D4AF37',
}

def poly(n, r, rot=-90.0, cx=0.5, cy=0.5):
    return [(cx + r * math.cos(math.radians(rot + i * 360.0 / n)),
             cy + r * math.sin(math.radians(rot + i * 360.0 / n))) for i in range(n)]

def star(points=5, outer=0.44, inner=0.18):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(-90 + i * 180.0 / points)
        pts.append((0.5 + r * math.cos(a), 0.5 + r * math.sin(a)))
    return pts

def heart():
    # parametric heart, normalised into the card
    pts = []
    for i in range(181):
        t = math.radians(i * 2)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((0.5 + x / 40.0, 0.47 - y / 40.0))
    return pts

def arrow():
    return [(0.16, 0.42), (0.56, 0.42), (0.56, 0.26), (0.86, 0.5),
            (0.56, 0.74), (0.56, 0.58), (0.16, 0.58)]

def cross(arm=0.11, reach=0.36):
    a, r = arm, reach
    return [(0.5 - a, 0.5 - r), (0.5 + a, 0.5 - r), (0.5 + a, 0.5 - a), (0.5 + r, 0.5 - a),
            (0.5 + r, 0.5 + a), (0.5 + a, 0.5 + a), (0.5 + a, 0.5 + r), (0.5 - a, 0.5 + r),
            (0.5 - a, 0.5 + a), (0.5 - r, 0.5 + a), (0.5 - r, 0.5 - a), (0.5 - a, 0.5 - a)]

def draw_shape(d, name, px):
    """px() maps 0..1 card coordinates to pixels."""
    box = lambda x0, y0, x1, y1: [px(x0), px(y0), px(x1), px(y1)]
    if name == 'Circle':      d.ellipse(box(.12, .12, .88, .88), fill=INK)
    elif name == 'Square':    d.rectangle(box(.14, .14, .86, .86), fill=INK)
    elif name == 'Rectangle': d.rectangle(box(.08, .26, .92, .74), fill=INK)
    elif name == 'Oval':      d.ellipse(box(.08, .24, .92, .76), fill=INK)
    elif name == 'Triangle':  d.polygon([(px(x), px(y)) for x, y in
                                         [(.5, .13), (.9, .83), (.1, .83)]], fill=INK)
    elif name == 'Diamond':   d.polygon([(px(x), px(y)) for x, y in
                                         [(.5, .1), (.85, .5), (.5, .9), (.15, .5)]], fill=INK)
    elif name == 'Pentagon':  d.polygon([(px(x), px(y)) for x, y in poly(5, .4)], fill=INK)
    elif name == 'Hexagon':   d.polygon([(px(x), px(y)) for x, y in poly(6, .4, rot=0)], fill=INK)
    elif name == 'Star':      d.polygon([(px(x), px(y)) for x, y in star()], fill=INK)
    elif name == 'Heart':     d.polygon([(px(x), px(y)) for x, y in heart()], fill=INK)
    elif name == 'Arrow':     d.polygon([(px(x), px(y)) for x, y in arrow()], fill=INK)
    elif name == 'Cross':     d.polygon([(px(x), px(y)) for x, y in cross()], fill=INK)
    elif name == 'Ring':
        d.ellipse(box(.1, .1, .9, .9), fill=INK)
        d.ellipse(box(.28, .28, .72, .72), fill=PAPER)
    elif name == 'Crescent':
        d.ellipse(box(.14, .12, .86, .88), fill=INK)
        d.ellipse(box(.34, .06, 1.06, .94), fill=PAPER)   # bite out of the right side
    elif name == 'Semicircle':
        d.pieslice(box(.1, .22, .9, 1.02), 180, 360, fill=INK)
    else:
        raise SystemExit('no recipe for shape ' + name)

def canvas(bg):
    img = Image.new('RGB', (SIZE * SS, SIZE * SS), bg)
    return img, ImageDraw.Draw(img), (lambda v: v * SIZE * SS)

def save(img, slot):
    small = img.resize((SIZE, SIZE), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
        small.save(t.name)
        subprocess.run(['cwebp', '-q', '90', '-quiet', t.name,
                        '-o', os.path.join(OUT, slot + '.webp')], check=True)
    os.unlink(t.name)

def main():
    cards = json.load(open(os.path.join(ROOT, 'app', 'data', 'cards.json')))
    drawn = {c['id']: c for c in cards['categories'] if c.get('drawn')}
    for want in ('shapes', 'colors'):
        if want not in drawn:
            raise SystemExit('cards.json has no drawn category "%s"' % want)
    os.makedirs(OUT, exist_ok=True)
    credits = json.load(open(CREDITS)) if os.path.exists(CREDITS) else {}
    made = []

    def emit(slot, label, img):
        save(img, slot)
        credits[slot] = {'name': label, 'article': 'drawn for this app',
                         'author': 'What is this?', 'licence': 'CC0',
                         'source': 'https://github.com/valerianpereira/what-is-this-app'}
        made.append(slot)

    for it in drawn['shapes']['items']:
        img, d, px = canvas(PAPER)
        draw_shape(d, it['name'], px)
        emit('obj-shapes-' + it['name'].lower(), it['name'], img)

    for it in drawn['colors']['items']:
        hexv = COLOURS.get(it['name'])
        if not hexv:
            raise SystemExit('no hex for colour ' + it['name'])
        img, d, px = canvas(FIELD)
        d.ellipse([px(.06), px(.06), px(.94), px(.94)], fill=hexv)
        emit('obj-colors-' + it['name'].lower(), it['name'], img)

    # group tiles. The home grid frame is wide and object-fit:cover crops these
    # to a middle band, so both tiles stay in a horizontal strip.
    img, d, px = canvas(PAPER)
    d.ellipse([px(.07), px(.34), px(.35), px(.66)], fill=INK)
    d.rectangle([px(.38), px(.34), px(.62), px(.66)], fill=INK)
    d.polygon([(px(.79), px(.32)), (px(.94), px(.66)), (px(.64), px(.66))], fill=INK)
    emit('cat-shapes', 'Shapes (group tile)', img)

    img, d, px = canvas(FIELD)
    row = [COLOURS[i['name']] for i in drawn['colors']['items']][:6]
    for i, hexv in enumerate(row):
        cx, r = .09 + .82 * i / (len(row) - 1), 0.068
        d.ellipse([px(cx - r), px(.5 - r), px(cx + r), px(.5 + r)], fill=hexv)
    emit('cat-colors', 'Colours (group tile)', img)

    json.dump(credits, open(CREDITS, 'w'), ensure_ascii=False, indent=1)
    print('drew %d cards' % len(made))

if __name__ == '__main__':
    main()
