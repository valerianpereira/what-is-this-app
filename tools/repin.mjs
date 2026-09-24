#!/usr/bin/env node
// Points cards at a different photo and forgets the old one, so
// tools/fetch-images.mjs downloads it again on the next run.
//   node tools/repin.mjs vehicles:Truck="File:Tata Truck India.jpg" ...
import { readFile, writeFile, rm } from 'node:fs/promises';
const APP = new URL('../app/', import.meta.url).pathname;
const PHOTOS = new URL('../photos/', import.meta.url).pathname;
const slug = (s) => s.toLowerCase().replace(/\s+/g, '-');

const cards = JSON.parse(await readFile(APP + 'data/cards.json', 'utf8'));
const credits = JSON.parse(await readFile(APP + 'data/credits.json', 'utf8'));

for (const arg of process.argv.slice(2)) {
  const m = arg.match(/^([^:]+):([^=]+)=(.+)$/);
  if (!m) throw new Error(`cannot parse ${arg}`);
  const [, catId, name, wiki] = m;
  const cat = cards.categories.find((c) => c.id === catId);
  if (!cat) throw new Error(`no group ${catId}`);
  const item = cat.items.find((i) => i.name === name);
  if (!item) throw new Error(`no card ${catId}:${name}`);
  item.wiki = wiki;
  const slot = `obj-${catId}-${slug(name)}`;
  delete credits[slot];
  await rm(`${PHOTOS}${slot}.webp`, { force: true });
  console.log(`${slot} -> ${wiki}`);
}

await writeFile(APP + 'data/cards.json', JSON.stringify(cards, null, 2) + '\n');
await writeFile(APP + 'data/credits.json', JSON.stringify(credits, null, 1) + '\n');
