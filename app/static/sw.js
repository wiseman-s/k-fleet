// K-FLEET Service Worker
// Caches the gate page and its assets so the app works when the network drops.

const CACHE_NAME = "kfleet-v1";
const OFFLINE_URLS = [
    "/gate",
    "/static/manifest.json",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png"
];

// Install: pre-cache the important pages
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
    );
    self.skipWaiting();
});

// Activate: remove old caches
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k !== CACHE_NAME)
                    .map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// Fetch: network-first for navigation, cache-first for static
self.addEventListener("fetch", (event) => {
    const req = event.request;

    // Only handle GET requests
    if (req.method !== "GET") return;

    // Don't cache API lookups or form submissions
    if (req.url.includes("/gate/lookup") || req.url.includes("/api/")) return;

    event.respondWith(
        fetch(req)
            .then((response) => {
                // Cache a copy of successful responses for static assets
                if (response.ok && req.url.match(/\/static\//)) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
                }
                return response;
            })
            .catch(() => {
                // If network fails, try the cache
                return caches.match(req).then((cached) => {
                    if (cached) return cached;
                    // If it's a navigation request, fall back to the cached gate page
                    if (req.mode === "navigate") {
                        return caches.match("/gate");
                    }
                });
            })
    );
});