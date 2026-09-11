#!/usr/bin/env node
// Uploads photos/*.webp to Cloudinary, one asset per card, then prints the
// imageBase value to paste into app/data/cards.json.
//
//   export CLOUDINARY_URL='cloudinary://<api_key>:<api_secret>@<cloud_name>'
//   node tools/upload-cloudinary.mjs            # skips assets already there
//   node tools/upload-cloudinary.mjs --force    # re-uploads and overwrites
//
// Credentials come from the environment only — never commit them. Signed
// uploads are used so no unsigned upload preset has to be left open.
import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const PHOTOS = new URL('../photos/', import.meta.url).pathname;
const FOLDER = 'what-is-this';
const FORCE = process.argv.includes('--force');

function credentials() {
  const url = process.env.CLOUDINARY_URL;
  if (url) {
    const m = url.match(/^cloudinary:\/\/([^:]+):([^@]+)@(.+)$/);
    if (!m) throw new Error('CLOUDINARY_URL must look like cloudinary://key:secret@cloud_name');
    return { apiKey: m[1], apiSecret: m[2], cloudName: m[3] };
  }
  const { CLOUDINARY_CLOUD_NAME: cloudName, CLOUDINARY_API_KEY: apiKey, CLOUDINARY_API_SECRET: apiSecret } = process.env;
  if (!cloudName || !apiKey || !apiSecret) {
    throw new Error('set CLOUDINARY_URL, or CLOUDINARY_CLOUD_NAME + CLOUDINARY_API_KEY + CLOUDINARY_API_SECRET');
  }
  return { cloudName, apiKey, apiSecret };
}

// Cloudinary signs the alphabetically-sorted params, secret appended, SHA-1.
const sign = (params, apiSecret) =>
  createHash('sha1').update(
    Object.keys(params).sort().map((k) => `${k}=${params[k]}`).join('&') + apiSecret
  ).digest('hex');

const { cloudName, apiKey, apiSecret } = credentials();
const base = `https://api.cloudinary.com/v1_1/${cloudName}`;

// What is already up there? One listing beats 272 conditional uploads.
async function existing() {
  const found = new Set();
  let cursor;
  do {
    const ts = Math.floor(Date.now() / 1000);
    const params = { max_results: 500, prefix: FOLDER + '/', timestamp: ts, type: 'upload' };
    const q = new URLSearchParams({ ...params, api_key: apiKey, signature: sign(params, apiSecret) });
    if (cursor) q.set('next_cursor', cursor);
    const r = await fetch(`${base}/resources/image?${q}`);
    if (!r.ok) throw new Error(`listing failed: ${r.status} ${await r.text()}`);
    const j = await r.json();
    j.resources.forEach((x) => found.add(x.public_id));
    cursor = j.next_cursor;
  } while (cursor);
  return found;
}

async function upload(slot) {
  const ts = Math.floor(Date.now() / 1000);
  // public_id carries the folder, so the delivery URL is .../what-is-this/<slot>
  const params = { overwrite: FORCE ? 'true' : 'false', public_id: `${FOLDER}/${slot}`, timestamp: ts };
  const form = new FormData();
  for (const [k, v] of Object.entries(params)) form.set(k, String(v));
  form.set('api_key', apiKey);
  form.set('signature', sign(params, apiSecret));
  form.set('file', new Blob([await readFile(PHOTOS + slot + '.webp')], { type: 'image/webp' }), slot + '.webp');
  const r = await fetch(`${base}/image/upload`, { method: 'POST', body: form });
  if (!r.ok) throw new Error(`${slot}: ${r.status} ${await r.text()}`);
  return r.json();
}

const slots = (await readdir(PHOTOS)).filter((f) => f.endsWith('.webp')).map((f) => f.replace(/\.webp$/, '')).sort();
console.log(`${slots.length} photos, cloud "${cloudName}", folder "${FOLDER}"${FORCE ? ', forcing overwrite' : ''}`);

const already = FORCE ? new Set() : await existing();
const todo = slots.filter((s) => !already.has(`${FOLDER}/${s}`));
console.log(`${already.size} already uploaded, ${todo.length} to go`);

const failed = [];
let done = 0;
// Six at a time: fast enough, and gentle on the free tier's rate limits.
const workers = Array.from({ length: 6 }, async () => {
  for (;;) {
    const slot = todo.shift();
    if (!slot) return;
    try {
      await upload(slot);
      process.stdout.write('#');
    } catch (e) {
      failed.push(e.message);
      process.stdout.write('!');
    }
    if (++done % 60 === 0) process.stdout.write(` ${done}/${todo.length + done}\n`);
  }
});
await Promise.all(workers);

console.log(`\n${slots.length - failed.length}/${slots.length} available on Cloudinary`);
if (failed.length) {
  console.log('FAILED:');
  failed.forEach((f) => console.log('  ' + f));
  process.exitCode = 1;
}
console.log(`\nSet this in app/data/cards.json:\n  "imageBase": "https://res.cloudinary.com/${cloudName}/image/upload/${FOLDER}"`);
