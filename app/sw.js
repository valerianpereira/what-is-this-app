// Serves the card photos from the cache the first-run download filled, so
// <img src="https://…/obj-wild-lion.webp"> keeps working with no network.
// The app shell itself is not cached here — it ships inside the APK.
const IMG_CACHE = 'wit-img-v2';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {
  // the URL carries a ?v= cache-buster, so match on the path, not the whole URL
  if (e.request.method !== 'GET' || !new URL(e.request.url).pathname.endsWith('.webp')) return;
  e.respondWith((async () => {
    const cache = await caches.open(IMG_CACHE);
    const hit = await cache.match(e.request);
    if (hit) return hit;
    // Not downloaded yet: fetch it and keep it, so a photo the first run
    // missed still lands in the cache the first time it is shown.
    const res = await fetch(e.request);
    if (res.ok || res.type === 'opaque') await cache.put(e.request, res.clone());
    return res;
  })());
});
