// Leaflet QR offline support.
// Bump VERSION whenever index.html changes so phones pick up the new app.
const VERSION = "leaflet-qr-v26";
const FILES = ["./", "index.html", "leaflets.json", "manifest.webmanifest", "icon.svg", "icon-180.png", "icon-192.png", "icon-512.png", "pdfjs/pdfjs-5.min.js", "pdfjs/pdfjs-5.worker.min.js"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(VERSION).then(async c => {
      await c.addAll(FILES);
      // front-page pictures, if the site has made them: saved so previews work offline
      try {
        const r = await fetch("thumbs/index.json", { cache: "no-store" });
        if (r.ok) await c.addAll(Object.keys(await r.json()).map(id => "thumbs/" + id + ".webp"));
      } catch (err) {}
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // Leaflet list: try the network first so edits reach staff, fall back to the saved copy.
  if (url.pathname.endsWith("leaflets.json")) {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(VERSION).then(c => c.put("leaflets.json", copy));
        return r;
      }).catch(() => caches.match("leaflets.json"))
    );
    return;
  }

  // Front-page pictures and leaflet copies: saved copy first, otherwise fetch and keep,
  // so a leaflet viewed once can be viewed again offline.
  if (url.pathname.includes("/thumbs/") || url.pathname.includes("/pdfs/")) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); }
      return r;
    })));
    return;
  }

  // Everything else: saved copy first, so the app opens instantly with no signal.
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).catch(() => caches.match("index.html")))
  );
});
