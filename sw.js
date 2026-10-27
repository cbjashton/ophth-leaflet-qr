// EyeLeaflets offline support.
// Bump VERSION whenever index.html changes so phones pick up the new app.
// Every app on cbjashton.github.io shares one Cache Storage, so this app only ever
// reads or deletes caches whose name starts with PREFIX. Other apps (e.g. GOSH Eye
// Leaflets) must use a prefix that does NOT start with "leaflet-qr-".
const PREFIX = "leaflet-qr-";
const VERSION = PREFIX + "v31";
const FILES = ["./", "index.html", "pilot.js", "leaflets.json", "manifest.webmanifest", "icon.svg", "icon-180.png", "icon-192.png", "icon-512.png", "pdfjs/pdfjs-5.min.js", "pdfjs/pdfjs-5.worker.min.js"];
const SCOPE = new URL("./", self.location).pathname;   // "/ophth-leaflet-qr/"

// Look things up in this version's cache only, never in another app's.
const fromCache = (req, opts) => caches.open(VERSION).then(c => c.match(req, opts));
const keep = (req, res) => caches.open(VERSION).then(c => c.put(req, res));

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
      .then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  // Only this app's own files: other sites, and other apps on the same address, go straight to the network.
  if (e.request.method !== "GET" || url.origin !== location.origin || !url.pathname.startsWith(SCOPE)) return;

  // Leaflet list: try the network first so edits reach staff, fall back to the saved copy.
  if (url.pathname.endsWith("leaflets.json")) {
    e.respondWith(
      fetch(e.request).then(r => {
        if (r.ok) keep("leaflets.json", r.clone());
        return r;
      }).catch(() => fromCache("leaflets.json"))
    );
    return;
  }

  // Front-page pictures and leaflet copies: saved copy first, otherwise fetch and keep,
  // so a leaflet viewed once can be viewed again offline.
  if (url.pathname.includes("/thumbs/") || url.pathname.includes("/pdfs/")) {
    e.respondWith(fromCache(e.request).then(hit => hit || fetch(e.request).then(r => {
      if (r.ok) keep(e.request, r.clone());
      return r;
    })));
    return;
  }

  // Everything else: saved copy first, so the app opens instantly with no signal.
  // With no copy and no signal, a page load gets the app itself; anything else fails normally.
  e.respondWith(
    fromCache(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).catch(err => {
      if (e.request.mode === "navigate") return fromCache("index.html");
      throw err;
    }))
  );
});
