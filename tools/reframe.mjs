#!/usr/bin/env node
// Sets how a card's photo sits in the app's square frame, for pictures whose
// subject a centre crop cuts into. No re-download: this is display only.
//   node tools/reframe.mjs 'fruits:Cherry=contain' 'farm:Donkey=left center'
// A value of "contain" or "cover" sets object-fit; anything else is an
// object-position. "cover" clears both, putting the card back to the default.
import { readFile, writeFile } from 'node:fs/promises';
const APP = new URL('../app/', import.meta.url).pathname;
const cards = JSON.parse(await readFile(APP + 'data/cards.json', 'utf8'));

for (const arg of process.argv.slice(2)) {
  const m = arg.match(/^([^:]+):([^=]+)=(.*)$/);
  if (!m) throw new Error(`cannot parse ${arg}`);
  const [, catId, name, value] = m;
  const cat = cards.categories.find((c) => c.id === catId);
  if (!cat) throw new Error(`no group ${catId}`);
  const item = cat.items.find((i) => i.name === name);
  if (!item) throw new Error(`no card ${catId}:${name}`);
  delete item.fit; delete item.focus;
  if (value === 'contain') item.fit = 'contain';
  else if (value && value !== 'cover') item.focus = value;
  console.log(`${catId}:${name} -> ${value || 'cover'}`);
}

await writeFile(APP + 'data/cards.json', JSON.stringify(cards, null, 2) + '\n');
