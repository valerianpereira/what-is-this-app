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
from PIL import Image

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

def centred():
    """slots of groups marked "crop": "center" — flags, whose whole frame is the subject"""
    cards = json.load(open(os.path.join(ROOT, 'app', 'data', 'cards.json')))
    return tuple(f"obj-{c['id']}-" for c in cards['categories'] if c.get('crop') == 'center')

def main():
    want = set(sys.argv[1:])
    centre = centred()
    files = sorted(f for f in os.listdir(SRC) if f.endswith('.jpg') and (not want or f[:-4] in want))
    paths = [os.path.join(SRC, f) for f in files]
    boxes = salient(paths)
    os.makedirs(OUT, exist_ok=True)
    bad = []
    for p in paths:
        slot = os.path.basename(p)[:-4]
        info = boxes[p]
        if slot.startswith(centre):
            info = {'w': info['w'], 'h': info['h'], 'box': [0, 0, info['w'], info['h']]}
        im, fits, cov = crop(p, info)
        fits = fits or slot.startswith(centre)
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
