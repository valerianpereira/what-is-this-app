#!/usr/bin/env node
// Downloads one photo per card from Wikipedia/Commons into photos/, and records
// author + licence into app/data/credits.json (CC-BY requires attribution).
// photos/ is deliberately outside app/ so the images stay out of the APK — they
// are uploaded to a CDN by tools/upload-cloudinary.mjs and fetched on first run.
// Cards come from app/data/cards.json — the app reads the same file.
// Re-run safe: skips cards that already have a photo and a credit.
import { mkdir, writeFile, readFile, access } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const sh = promisify(execFile);

// Wikimedia's UA policy wants a contact; the repo URL satisfies it without
// putting a personal address in a public repository.
const UA = 'WhatIsThisKidsApp/1.0 (offline kids learning app; https://github.com/valerianpereira/what-is-this-app)';
const APP = new URL('../app/', import.meta.url).pathname;
const OUT = new URL('../photos/', import.meta.url).pathname;

const slug = (s) => s.toLowerCase().replace(/\s+/g, '-');
const nap = (ms) => new Promise((r) => setTimeout(r, ms));
const get = async (url) => {
  const r = await fetch(url, { headers: { 'User-Agent': UA, 'Api-User-Agent': UA } });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r;
};
const stripTags = (s) => (s || '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();

// Lead image of an article -> { file: 'Name.jpg', wiki: 'commons'|'en' }
async function leadImage(title) {
  const j = await (await get(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`)).json();
  const src = (j.originalimage?.source || j.thumbnail?.source || '').split('?')[0];
  if (!src) throw new Error(`no lead image for ${title}`);
  // .../wikipedia/<commons|en>/[thumb/]a/ab/File_Name.jpg[/640px-...]
  const m = src.match(/\/wikipedia\/(commons|en)\/(?:thumb\/)?[0-9a-f]\/[0-9a-f]{2}\/([^/]+)/);
  if (!m) throw new Error(`unparseable image url ${src}`);
  return { file: decodeURIComponent(m[2]), wiki: m[1] };
}

async function licence({ file, wiki }) {
  const host = wiki === 'commons' ? 'commons.wikimedia.org' : 'en.wikipedia.org';
  const u = `https://${host}/w/api.php?action=query&format=json&prop=imageinfo&iiprop=extmetadata&titles=${encodeURIComponent('File:' + file)}`;
  const j = await (await get(u)).json();
  const page = Object.values(j.query?.pages || {})[0] || {};
  const meta = page.imageinfo?.[0]?.extmetadata || {};
  return {
    author: stripTags(meta.Artist?.value) || 'Unknown',
    licence: stripTags(meta.LicenseShortName?.value) || 'see source',
    source: `https://${host}/wiki/${encodeURIComponent('File:' + file)}`,
  };
}

async function exists(p) { try { await access(p); return true; } catch { return false; } }

async function download({ file, wiki }, dest) {
  const host = wiki === 'commons' ? 'commons.wikimedia.org' : 'en.wikipedia.org';
  // Commons resizes server-side, so we never downscale a large original ourselves.
  // 720px matches the round card at 3x on a 1080p phone.
  const url = `https://${host}/wiki/Special:FilePath/${encodeURIComponent(file)}?width=720`;
  const buf = Buffer.from(await (await get(url)).arrayBuffer());
  const tmp = dest + '.orig';
  await writeFile(tmp, buf);
  // sips normalises anything (png, svg-rendered-png, tif) to jpeg; cwebp then
  // halves it. Android's WebView has handled WebP since 4.2.
  const mid = dest + '.mid.jpg';
  await sh('sips', ['-s', 'format', 'jpeg', '-s', 'formatOptions', '92', '-Z', '720', tmp, '--out', mid]);
  await sh('cwebp', ['-q', '78', '-quiet', mid, '-o', dest]);
  await sh('rm', ['-f', tmp, mid]);
}

const { categories } = JSON.parse(await readFile(APP + 'data/cards.json', 'utf8'));
const targets = [];
for (const c of categories) {
  targets.push({ slot: `cat-${c.id}`, title: c.tile, label: `${c.name} (group tile)` });
  for (const it of c.items) targets.push({ slot: `obj-${c.id}-${slug(it.name)}`, title: it.wiki, label: it.name });
}

await mkdir(OUT, { recursive: true });
const creditsPath = APP + 'data/credits.json';
const credits = await exists(creditsPath) ? JSON.parse(await readFile(creditsPath, 'utf8')) : {};
const failed = [];

for (const t of targets) {
  const dest = `${OUT}${t.slot}.webp`;
  if (await exists(dest) && credits[t.slot]) { process.stdout.write('.'); continue; }
  try {
    // 'File:Foo.jpg' pins one exact Commons file, for cards whose article lead
    // image is a painting, a collage or a botanical diagram.
    const img = t.title.startsWith('File:')
      ? { file: t.title.slice(5), wiki: 'commons' }
      : await leadImage(t.title);
    await download(img, dest);
    credits[t.slot] = { name: t.label, article: t.title, ...(await licence(img)) };
    process.stdout.write('#');
  } catch (e) {
    failed.push(`${t.slot} (${t.title}): ${e.message}`);
    process.stdout.write('!');
  }
  await writeFile(creditsPath, JSON.stringify(credits, null, 1));
  await nap(120); // stay polite to the Wikimedia APIs
}

console.log(`\n${Object.keys(credits).length}/${targets.length} images ready`);
if (failed.length) { console.log('FAILED:'); failed.forEach((f) => console.log('  ' + f)); process.exitCode = 1; }
