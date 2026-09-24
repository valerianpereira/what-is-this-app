#!/usr/bin/env node
// Every card the game can deal must have a photo and a credit line. Adding an
// item to cards.json without re-running fetch-images.mjs is the way this breaks.
// Run: node tools/check.mjs
import { readFile, access } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import assert from 'node:assert/strict';
const sh = promisify(execFile);

const root = new URL('../app/', import.meta.url).pathname;
const photos = new URL('../photos/', import.meta.url).pathname;
const { categories, imageBase } = JSON.parse(await readFile(root + 'data/cards.json', 'utf8'));
const credits = JSON.parse(await readFile(root + 'data/credits.json', 'utf8'));
const slug = (s) => s.toLowerCase().replace(/\s+/g, '-');

const slots = [];
const seenNames = new Map();
for (const c of categories) {
  for (const key of ['id', 'name', 'color', 'shadow', 'tile']) assert.ok(c[key], `category is missing ${key}`);
  assert.ok(c.items.length >= 4, `${c.id} needs at least 4 items to fill a round`);
  assert.equal(new Set(c.items.map((i) => i.name)).size, c.items.length, `${c.id} has duplicate items`);
  slots.push('cat-' + c.id);
  for (const it of c.items) {
    assert.ok(it.name && it.wiki, `${c.id} has an item missing name or wiki`);
    // Slugs collide if two names in one group differ only by case or spacing.
    const slotKey = `obj-${c.id}-${slug(it.name)}`;
    assert.ok(!slots.includes(slotKey), `${slotKey} is not unique`);
    slots.push(slotKey);
    seenNames.set(it.name, (seenNames.get(it.name) || 0) + 1);
  }
}

// The card frame is square and shows the photo edge to edge, so every photo
// must be a 720px square — tools/square.py is what makes them so.
const size = async (file) => {
  const { stdout } = await sh('sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', file]);
  return (stdout.match(/pixel(?:Width|Height): (\d+)/g) || []).map((m) => Number(m.split(': ')[1]));
};
const missing = [], notSquare = [];
for (const s of slots) {
  try {
    await access(`${photos}${s}.webp`);
    const [w, h] = await size(`${photos}${s}.webp`);
    if (w !== 720 || h !== 720) notSquare.push(`${s} ${w}x${h}`);
  } catch { missing.push(s + '.webp'); }
  if (!credits[s]) missing.push(s + ' (credit)');
  else assert.ok(credits[s].licence && credits[s].source, `${s} credit is incomplete`);
}
assert.deepEqual(missing, [], 'missing assets');
assert.deepEqual(notSquare, [], 'photos that are not 720x720 — run npm run square');

// A credit with no card behind it means a leftover photo is still being served
// from the CDN and listed in the app's credits screen.
const extra = Object.keys(credits).filter((k) => !slots.includes(k));
assert.deepEqual(extra, [], 'credits.json has entries with no matching card');

// A word appearing in two groups shows up twice in a "Surprise me" round.
const dupes = [...seenNames].filter(([, n]) => n > 1).map(([n]) => n);
assert.deepEqual(dupes, [], 'the same word appears in more than one group');

assert.ok(/^https:\/\/\S+[^/]$/.test(imageBase || ''), 'cards.json needs an https imageBase with no trailing slash');

console.log(`ok — ${categories.length} groups, ${slots.length} cards, all photos and credits present`);
console.log(`   images served from ${imageBase}`);
