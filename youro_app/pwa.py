"""PWA: manifest, service worker e icono."""
import base64

MANIFEST = {
    "name": "Yuro",
    "short_name": "Yuro",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0c11",
    "theme_color": "#f59e0b",
    "icons": [{"src": "/icono.png", "sizes": "512x512", "type": "image/png"}],
}

SERVICE_WORKER = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {
  e.respondWith(caches.open('yuro-v2').then(c =>
    c.match(e.request).then(r => r || fetch(e.request).then(res => {
      if (e.request.method === 'GET') c.put(e.request, res.clone());
      return res;
    }).catch(() => r))
  ));
});
"""

# PNG 1x1 dorado (placeholder)
_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
    "YGBgAAAABQABh6FO1AAAAABJRU5ErkJggg=="
)


def icono_png():
    return base64.b64decode(_PNG_BASE64)
