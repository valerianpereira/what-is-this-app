// Commons search -> candidate sheet, so bad lead images can be replaced by hand.
import { writeFile } from 'node:fs/promises';
const UA = 'WhatIsThisKidsApp/1.0 (offline learning app)';
const QUERIES = process.argv.slice(2);
let html = '<style>body{font:12px system-ui;margin:8px}h3{margin:14px 0 4px}main{display:flex;gap:4px;flex-wrap:wrap}figure{margin:0;width:150px}img{width:150px;height:150px;object-fit:cover;border-radius:6px}figcaption{font-size:9px;word-break:break-all}</style>';
const nap = (ms) => new Promise((r) => setTimeout(r, ms));
for (const q of QUERIES) {
  await nap(2500); // Commons search API rate-limits anonymous bursts
  const u = `https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=${encodeURIComponent(q + ' filetype:bitmap')}&gsrnamespace=6&gsrlimit=6&prop=imageinfo&iiprop=url&iiurlwidth=300`;
  const j = await (await fetch(u, { headers: { 'User-Agent': UA } })).json();
  const pages = Object.values(j.query?.pages || {}).sort((a, b) => a.index - b.index);
  html += `<h3>${q}</h3><main>`;
  for (const p of pages) {
    const f = p.title.replace(/^File:/, '');
    html += `<figure><img src="${p.imageinfo[0].thumburl}"><figcaption>${f}</figcaption></figure>`;
  }
  html += '</main>';
}
await writeFile(new URL('../app/img/_cands.html', import.meta.url).pathname, html);
console.log('ok');
