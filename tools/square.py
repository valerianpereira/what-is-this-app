#!/usr/bin/env python3
"""Makes every card photo square, with its subject whole.

Reads the full frames tools/fetch-images.mjs leaves in photos-src/, asks
tools/salient.swift where the subject is, and cuts the largest square the
photo allows around it, into photos/<slot>.webp at 720px. The card frame is
square, so this is what stops wheels, heads and flag ends being cropped off.

  python3 tools/square.py            # every frame in photos-src/
  python3 tools/square.py obj-wild-zebra ...

A subject wider or taller than that square cannot be shown whole from this
photo; the card is still written (best crop) and listed at the end so a
better-framed photo can be found for it.
"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageOps, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, 'photos-src'), os.path.join(ROOT, 'photos')
SIZE, MARGIN = 720, 0.02       # 2% of the square kept clear around the subject
KEEP, FILLS = 0.97, 0.80       # subject kept >=97% counts as whole; a subject that is
                               # >=80% of the frame is a close-up, and cropping it is scaling

def salient(paths):
    exe = os.path.join(tempfile.gettempdir(), 'wit-salient')
    src = os.path.join(ROOT, 'tools', 'salient.swift')
    if not os.path.exists(exe) or os.path.getmtime(exe) < os.path.getmtime(src):
        subprocess.run(['swiftc', '-O', src, '-o', exe], check=True, capture_output=True)
    return json.loads(subprocess.run([exe] + paths, check=True, capture_output=True).stdout)

def crop(path, info):
    w, h, (bx, by, bw, bh) = info['w'], info['h'], info['box']
    side = min(w, h)
    m = int(side * MARGIN)
    # square centred on the subject, then pushed back inside the frame
    cx, cy = bx + bw / 2, by + bh / 2
    x0 = int(min(max(cx - side / 2, 0), w - side))
    y0 = int(min(max(cy - side / 2, 0), h - side))
    ix = max(0, min(bx + bw, x0 + side - m) - max(bx, x0 + m))
    iy = max(0, min(by + bh, y0 + side - m) - max(by, y0 + m))
    coverage = (ix * iy) / (bw * bh) if bw and bh else 1.0
    fits = coverage >= KEEP or bw * bh >= FILLS * w * h
    im = Image.open(path).convert('RGB').crop((x0, y0, x0 + side, y0 + side))
    return im.resize((SIZE, SIZE), Image.LANCZOS), fits, coverage

def points():
    """slot -> [x, y] for cards with a "point": the spot (fractions of the square) an
    arrow is drawn to, for body parts a photo alone leaves ambiguous"""
    cards = json.load(open(os.path.join(ROOT, 'app', 'data', 'cards.json')))
    return {f"obj-{c['id']}-{i['name'].lower().replace(' ', '-')}": i['point']
            for c in cards['categories'] for i in c['items'] if 'point' in i}

def arrow(im, x, y):
    """a fat arrow whose tip is at (x, y), coming in level from the nearer side so the
    shaft stays off the subject"""
    d, s = ImageDraw.Draw(im), SIZE
    tx, ty = x * s, y * s
    k = 1 if x >= 0.5 else -1                 # tail to the right of the tip, or the left
    L, H, T = s * 0.30, s * 0.11, s * 0.045   # length, head half-height, shaft half-height
    hx = tx + k * s * 0.12                    # where the head meets the shaft
    shape = [(tx, ty), (hx, ty - H), (hx, ty - T), (tx + k * L, ty - T),
             (tx + k * L, ty + T), (hx, ty + T), (hx, ty + H)]
    d.polygon(shape, fill='#FF4D2E', outline='white', width=8)
    return im

def contained():
    """slots shown whole on white rather than cut square: every card of a group marked
    "crop": "contain" (flags, whose whole frame is the subject), with a grey rim so white
    flags keep an edge, and single cards marked so (a trumpet on white is long and thin,
    and no square of it holds the whole instrument), without one. A card's "frame":
    [left, top, right, bottom] (fractions) trims the photo first, to keep one of two
    views. slot -> (rim, frame)"""
    cards = json.load(open(os.path.join(ROOT, 'app', 'data', 'cards.json')))
    return {f"obj-{c['id']}-{i['name'].lower().replace(' ', '-')}": (c.get('crop') == 'contain', i.get('frame'))
            for c in cards['categories'] for i in c['items']
            if c.get('crop') == 'contain' or i.get('crop') == 'contain'}

def plain_edge(im):
    """the photo's border colour, and whether the border is plain (a product shot on
    white, a planet on black) - only then can it be padded out to a square without the
    padding showing as a box"""
    w, h = im.size
    px = [im.getpixel((x, y)) for x in range(0, w, max(1, w // 60)) for y in (0, h - 1)]
    px += [im.getpixel((x, y)) for y in range(0, h, max(1, h // 60)) for x in (0, w - 1)]
    mid = tuple(sorted(p[i] for p in px)[len(px) // 2] for i in range(3))
    near = sum(max(abs(p[i] - mid[i]) for i in range(3)) < 20 for p in px) / len(px)
    return mid, near > 0.8     # ponytail: hand-picked; a subject touching the edge stays under 20%

def contain(path, rim, frame=None):
    """the whole frame fitted inside a square: flags on white with a grey rim, a single
    card a little smaller on its own plain backdrop. Returns (image, plain?) - a single
    card on a busy backdrop shows as a box, so it is listed for a better photo"""
    im = Image.open(path).convert('RGB')
    if frame:
        w, h = im.size
        im = im.crop((int(frame[0] * w), int(frame[1] * h), int(frame[2] * w), int(frame[3] * h)))
    bg, plain = ('white', True) if rim else plain_edge(im)
    out = Image.new('RGB', (SIZE, SIZE), bg)
    # flags all fit one 3:2 box, so a square flag (Switzerland) or a pennant (Nepal)
    # sits at the same height as the rest instead of towering over them
    # a hand-trimmed frame is already the card (a caption cut off), so it fills the square
    box = (int(SIZE * 0.88), int(SIZE * 0.88 * 2 / 3)) if rim else (int(SIZE * (1.0 if frame else 0.80)),) * 2
    im = ImageOps.contain(im, box, Image.LANCZOS)
    if rim:
        im = ImageOps.expand(im, border=2, fill='#D0D0D0')
    out.paste(im, ((SIZE - im.width) // 2, (SIZE - im.height) // 2))
    return out, plain

def main():
    want = set(sys.argv[1:])
    centre = contained()
    pts = points()
    files = sorted(f for f in os.listdir(SRC) if f.endswith('.jpg') and (not want or f[:-4] in want))
    paths = [os.path.join(SRC, f) for f in files]
    framed = [p for p in paths if os.path.basename(p)[:-4] not in centre]
    boxes = salient(framed) if framed else {}
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for p in paths:
        slot = os.path.basename(p)[:-4]
        if slot in centre:
            im, fits = contain(p, *centre[slot])
            cov = 1.0 if fits else 0.0     # busy backdrop: listed below like a cut subject
        else:
            im, fits, cov = crop(p, boxes[p])
        if slot in pts:
            im = arrow(im, *pts[slot])
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
            im.save(t.name)
            subprocess.run(['cwebp', '-q', '78', '-quiet', t.name, '-o', os.path.join(OUT, slot + '.webp')], check=True)
        os.unlink(t.name)
        if not fits:
            bad.append((cov, slot))
        print('#' if fits else '!', end='', flush=True)
    print(f'\n{len(paths) - len(bad)}/{len(paths)} squares hold the whole subject')
    if bad:
        print('subject does not fit a square of this photo (coverage):')
        for cov, slot in sorted(bad):
            print(f'  {slot}  {cov:.0%}')

if __name__ == '__main__':
    main()
