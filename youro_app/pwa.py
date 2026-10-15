"""PWA de Yuro: manifest, service worker e icono PNG (puro Python, sin PIL)."""
import struct
import zlib

MANIFEST = {
    "name": "Yuro · la moneda de tus amigos",
    "short_name": "Yuro",
    "description": "Blockchain privada para tu grupo de amigos (no vale dinero real).",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#0a0c11",
    "theme_color": "#f59e0b",
    "lang": "es",
    "icons": [
        {"src": "/icono.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icono.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    ],
}

SERVICE_WORKER = r"""
// Yuro service worker: abre rápido y funciona con mala conexión.
const CACHE = 'yuro-v2';
const BASICOS = ['/', '/manifest.json', '/icono.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(BASICOS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(k =>
    Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        const copia = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copia));
        return r;
      })
      .catch(() => caches.match(e.request))
  );
});
"""

# ======================================================================
#  Generador de icono PNG (moneda dorada con Y de Yuro) sin dependencias
# ======================================================================

_n = 512
_cache_png = None

_ORO = (245, 158, 11, 255)
_ORO_CLARO = (251, 191, 36, 255)
_ORO_OSCURO = (180, 100, 5, 255)
_BORDE = (202, 120, 8, 255)
_OSCURO = (17, 19, 26, 255)
_TRANSP = (0, 0, 0, 0)


def _dist_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = x1 + t * dx, y1 + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _png(ancho, alto, rgba):
    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0)
    filas = b"".join(
        b"\x00" + bytes(rgba[y * ancho * 4:(y + 1) * ancho * 4]) for y in range(alto)
    )
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(filas, 9))
            + chunk(b"IEND", b""))


def _pintar(lienzo, x, y, color):
    if 0 <= x < _n and 0 <= y < _n:
        i = (y * _n + x) * 4
        lienzo[i:i + 4] = bytes(color)


def icono_png():
    """PNG 512x512: moneda dorada con Y de Yuro (generado una vez y cacheado)."""
    global _cache_png
    if _cache_png is not None:
        return _cache_png

    lienzo = bytearray(_n * _n * 4)
    cx = cy = _n / 2
    radio = 220
    grosor_y = 32

    # Rayos de sol detrás de la moneda (como en el cartel)
    import math
    rayos = 12
    for ang_i in range(rayos * 2):
        ang = ang_i * math.pi / rayos
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        # Dibujar rayo como línea gruesa desde el centro hacia fuera
        for r in range(radio, _n // 2):
            x = int(cx + cos_a * r)
            y = int(cy + sin_a * r)
            # Alternar rayos visibles
            if ang_i % 2 == 0:
                # Gradiente del rayo: se desvanece hacia fuera
                alpha = max(0, 80 - r // 4)
                if alpha > 10:
                    color = (245, 158, 11, alpha)
                    # Pintar con transparencia (mezclar con fondo)
                    i = (y * _n + x) * 4
                    if 0 <= x < _n and 0 <= y < _n:
                        r_act, g_act, b_act, a_act = lienzo[i:i+4]
                        # Alpha blending simple
                        a_nuevo = min(255, a_act + alpha)
                        lienzo[i:i+4] = bytes((245, 158, 11, a_nuevo))

    # Símbolo Y: trazos (x1,y1)-(x2,y2)
    trazos_y = [
        (175, 155, 256, 265),   # diagonal izquierda
        (337, 155, 256, 265),   # diagonal derecha
        (256, 265, 256, 400),   # asta vertical
    ]

    # Símbolos pequeños a los lados (€ y ¢ como en el cartel)
    # Euro simplificado: C con dos barras
    trazos_euro = [
        # C del euro
        (100, 230, 105, 210), (105, 210, 120, 200), (120, 200, 140, 200),
        (140, 200, 155, 210), (155, 210, 160, 230), (160, 230, 160, 280),
        (160, 280, 155, 300), (155, 300, 140, 310), (140, 310, 120, 310),
        (120, 310, 105, 300), (105, 300, 100, 280),
        # barras del euro
        (95, 245, 175, 245), (95, 265, 175, 265),
    ]

    # Cent symbol simplificado
    trazos_cent = [
        (352, 260, 360, 240), (360, 240, 375, 232), (375, 232, 395, 232),
        (395, 232, 410, 240), (410, 240, 417, 260), (417, 260, 417, 275),
        (417, 275, 410, 295), (410, 295, 395, 303), (395, 303, 375, 303),
        (375, 303, 360, 295), (360, 295, 352, 275),
        # barra vertical
        (385, 220, 385, 315),
    ]

    r2 = radio * radio
    for y in range(_n):
        for x in range(_n):
            dx, dy = x - cx + 0.5, y - cy + 0.5
            d2 = dx * dx + dy * dy
            if d2 > (radio + 6) ** 2:
                continue

            # Borde exterior grueso
            if d2 >= (radio - 14) ** 2:
                _pintar(lienzo, x, y, _BORDE)
                continue

            # Borde interior más fino
            if d2 >= (radio - 20) ** 2:
                _pintar(lienzo, x, y, _ORO_OSCURO)
                continue

            # ¿Está en algún trazo del símbolo?
            en_simbolo = False

            # Y principal (grande, oscura)
            for x1, y1, x2, y2 in trazos_y:
                if _dist_seg(x, y, x1, y1, x2, y2) <= grosor_y / 2:
                    en_simbolo = True
                    break

            # Euro (izquierda, más pequeño)
            if not en_simbolo:
                for x1, y1, x2, y2 in trazos_euro:
                    if _dist_seg(x, y, x1, y1, x2, y2) <= 8:
                        en_simbolo = True
                        break

            # Cent (derecha, más pequeño)
            if not en_simbolo:
                for x1, y1, x2, y2 in trazos_cent:
                    if _dist_seg(x, y, x1, y1, x2, y2) <= 8:
                        en_simbolo = True
                        break

            if en_simbolo:
                _pintar(lienzo, x, y, _OSCURO)
            else:
                # Degradado vertical: brillo arriba, sombra abajo
                brillo = (1 - (dy + radio) / (2 * radio))
                if brillo > 0.7:
                    _pintar(lienzo, x, y, (255, 210, 80, 255))  # brillo máximo
                elif brillo > 0.55:
                    _pintar(lienzo, x, y, _ORO_CLARO)
                elif brillo < 0.25:
                    _pintar(lienzo, x, y, _ORO_OSCURO)
                else:
                    _pintar(lienzo, x, y, _ORO)

    _cache_png = _png(_n, _n, lienzo)
    return _cache_png
