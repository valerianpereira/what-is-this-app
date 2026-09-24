#!/usr/bin/env python3
"""Finds Commons photos whose subject fits whole in a square, for cards whose
current photo's subject does not (tools/square.py lists them).

  python3 tools/find-square.py /tmp/cands 'vehicles:Motorcycle=motorcycle side view' ...

Searches Commons, downloads the candidates, asks tools/salient.swift where the
subject is, keeps only pictures whose subject fits a square with room to spare
and fills a fair part of it, and writes a sheet of those squares (so what you
see is the card as it would be) plus index.json for tools/repin.mjs:
  node tools/repin.mjs "vehicles:Motorcycle=File:<name from the sheet>"
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from square import salient, crop

UA = 'WhatIsThisKidsApp/1.0 (offline kids learning app; https://github.com/valerianpereira/what-is-this-app)'
PER_QUERY, KEEP, MIN_FILL = 20, 6, 0.10   # subject must cover >=10% of the square
LICENCE_OK = ('CC', 'Public domain', 'PD', 'CC0')

def search(q):
    u = ('https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search'
         f'&gsrsearch={urllib.parse.quote(q + " filetype:bitmap")}&gsrnamespace=6&gsrlimit={PER_QUERY}'
         '&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=900')
    req = urllib.request.Request(u, headers={'User-Agent': UA})
    j = json.load(urllib.request.urlopen(req, timeout=60))
    pages = sorted(j.get('query', {}).get('pages', {}).values(), key=lambda p: p['index'])
    out = []
    for p in pages:
        i = p['imageinfo'][0]
        lic = (i.get('extmetadata', {}).get('LicenseShortName') or {}).get('value', '')
        if not lic.startswith(LICENCE_OK): continue
        if i['width'] < 600 or i['height'] < 600: continue
        out.append({'file': p['title'][5:], 'thumb': i['thumburl'], 'licence': lic})
    return out

def fetch(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest + '.tmp', 'wb') as f:
        f.write(r.read())
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-Z', '900', dest + '.tmp', '--out', dest],
                   check=True, capture_output=True)
    os.unlink(dest + '.tmp')

def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 11)
    CELL, LAB = 200, 26
    rows, index = [], []
    for spec in sys.argv[2:]:
        card, q = spec.split('=', 1)
        time.sleep(1.5)
        try: cands = search(q)
        except Exception as e:
            print(f'{card}: search failed: {e}'); continue
        paths = []
        for n, c in enumerate(cands):
            dest = os.path.join(outdir, f'{card.replace(":", "_")}_{n}.jpg')
            try: fetch(c['thumb'], dest); paths.append((dest, c))
            except Exception: pass
        if not paths: print(f'{card}: nothing usable'); continue
        boxes = salient([p for p, _ in paths])
        kept = []
        for p, c in paths:
            info = boxes.get(p)
            if not info: continue
            im, fits, _ = crop(p, info)
            side = min(info['w'], info['h'])
            fill = (info['box'][2] * info['box'][3]) / (side * side)
            if fits and fill >= MIN_FILL: kept.append((im, c))
            if len(kept) == KEEP: break
        print(f'{card}: {len(kept)} of {len(paths)} fit')
        if kept:
            rows.append((card, kept))
            for i, (_, c) in enumerate(kept): index.append({'card': card, 'i': i, 'file': c['file'], 'licence': c['licence']})
    if not rows: return
    sheet = Image.new('RGB', (KEEP * (CELL + 6) + 6, len(rows) * (CELL + LAB + 6) + 6), 'white')
    d = ImageDraw.Draw(sheet)
    for r, (card, kept) in enumerate(rows):
        y = 6 + r * (CELL + LAB + 6)
        for i, (im, c) in enumerate(kept):
            x = 6 + i * (CELL + 6)
            sheet.paste(im.resize((CELL, CELL), Image.LANCZOS), (x, y))
            d.text((x + 2, y + CELL + 2), f'{card} #{i}', font=font, fill='black')
            d.text((x + 2, y + CELL + 13), c['file'][:36], font=font, fill='#666')
    sheet.save(os.path.join(outdir, 'sheet.jpg'), quality=88)
    json.dump(index, open(os.path.join(outdir, 'index.json'), 'w'), indent=1)
    print('sheet:', os.path.join(outdir, 'sheet.jpg'))

if __name__ == '__main__':
    main()
