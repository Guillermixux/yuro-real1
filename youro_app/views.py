"""Vistas HTML de Yuro: tema oscuro, dorado, responsive y con identicones."""
import hashlib
import time

from . import config
from . import charts
from .notify import tema_de_usuario

# ======================================================================
#  Utilidades
# ======================================================================

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def formatear(n):
    """Formato de dinero en español: 1.234,56"""
    n = round(float(n or 0), 2)
    signo = "−" if n < 0 else ""
    ent, dec = f"{abs(n):.2f}".split(".")
    ent = f"{int(ent):,}".replace(",", ".")
    return f"{signo}{ent},{dec}"


def fecha(ts):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(ts))


def corta_dir(direccion, n=18):
    d = str(direccion)
    return d if len(d) <= n else d[:n] + "…"


def identicon_svg(direccion, tam=72):
    """Identicon determinista (SVG) a partir de la dirección."""
    h = hashlib.sha256(str(direccion).encode("utf-8")).digest()
    matiz = h[0] * 360 // 255
    color = f"hsl({matiz},72%,58%)"
    celdas = []
    lado = 5
    bit = 8
    for fila in range(lado):
        for col in range((lado + 1) // 2):
            activo = (h[(fila * 3 + col) % len(h)] >> (bit % 8)) & 1
            if activo:
                for c in (col, lado - 1 - col):
                    celdas.append(
                        f'<rect x="{c}" y="{fila}" width="1" height="1" rx="0.18"/>'
                    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}" '
        f'width="{tam}" height="{tam}" role="img" aria-label="identicon">'
        f'<rect width="{lado}" height="{lado}" fill="#0b0e14" rx="1"/>'
        f'<g fill="{color}">{"".join(celdas)}</g></svg>'
    )


def chip(texto, clase=""):
    return f'<span class="chip {clase}">{esc(texto)}</span>'


def icono_tipo(tipo, es_entrada):
    return {"coinbase": "⛏️", "faucet": "🎁"}.get(
        tipo, "➡️" if not es_entrada else "⬅️"
    )


# ======================================================================
#  Estilos y plantilla base
# ======================================================================

CSS = r"""
*{box-sizing:border-box}
:root{
  --bg:#0a0c11; --panel:#12161f; --borde:#232a3a; --texto:#e8ebf2; --sub:#8b94a8;
  --oro:#f59e0b; --oro2:#fbbf24; --ok:#34d399; --mal:#f87171; --azul:#7dd3fc;
}
html{scroll-behavior:smooth}
body{margin:0;background:
  radial-gradient(1200px 500px at 80% -10%, rgba(245,158,11,.10), transparent 60%),
  radial-gradient(900px 400px at -10% 110%, rgba(125,211,252,.06), transparent 60%),
  var(--bg);
  color:var(--texto);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  min-height:100vh;padding-bottom:40px}
a{color:var(--azul)}
.cont{max-width:980px;margin:0 auto;padding:16px}
header.top{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:10px}
.logo{font-size:26px;font-weight:900;letter-spacing:.5px;color:var(--oro);
  text-decoration:none;display:flex;align-items:center;gap:8px}
.logo .moneda{display:inline-flex;align-items:center;justify-content:center;
  width:34px;height:34px;border-radius:50%;
  background:linear-gradient(145deg,#fbbf24,#d97706);color:#14161c;font-size:19px;
  box-shadow:0 0 18px rgba(245,158,11,.35)}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
nav a{background:rgba(255,255,255,.03);color:var(--texto);border:1px solid var(--borde);
  padding:8px 14px;border-radius:999px;text-decoration:none;font-size:14px;white-space:nowrap}
nav a:hover{border-color:var(--oro);color:var(--oro2)}
nav a.activo{background:linear-gradient(145deg,#fbbf24,#f59e0b);color:#14161c;font-weight:700;
  border-color:transparent}
nav a.salir{border-style:dashed;color:var(--sub)}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px}
.stats span{background:rgba(255,255,255,.03);border:1px solid var(--borde);
  border-radius:999px;padding:5px 12px;font-size:12px;color:var(--sub)}
.stats b{color:var(--texto);font-weight:600}
.stats .ok{color:var(--ok)}.stats .mal{color:var(--mal)}
.panel{background:linear-gradient(180deg,rgba(255,255,255,.02),transparent 40%),var(--panel);
  border:1px solid var(--borde);border-radius:16px;padding:18px;margin-bottom:14px;
  box-shadow:0 8px 30px rgba(0,0,0,.35)}
h1{font-size:24px;margin:6px 0 2px}
h2{font-size:16px;margin:0 0 10px;color:var(--oro2);display:flex;align-items:center;gap:8px}
.sub{color:var(--sub);font-size:13px;margin:4px 0 12px;line-height:1.5}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.saldo{font-size:42px;font-weight:900;letter-spacing:-1px;
  background:linear-gradient(90deg,#fbbf24,#f59e0b,#fde68a);-webkit-background-clip:text;
  background-clip:text;color:transparent;font-variant-numeric:tabular-nums}
.direccion{font-family:Consolas,"Courier New",monospace;font-size:12px;color:var(--azul);
  word-break:break-all;background:#0a0d13;padding:10px 12px;border-radius:10px;
  border:1px solid #1d2b3d;display:block;margin:6px 0}
button,.btn{background:linear-gradient(145deg,#fbbf24,#f59e0b);color:#14161c;border:none;
  padding:10px 18px;border-radius:10px;font-size:14px;font-weight:800;cursor:pointer;
  text-decoration:none;display:inline-block;transition:filter .15s, transform .05s}
button:hover,.btn:hover{filter:brightness(1.08)}
button:active{transform:translateY(1px)}
button:disabled{opacity:.5;cursor:not-allowed}
.btn.sec{background:transparent;color:var(--texto);border:1px solid var(--borde);font-weight:500}
.btn.mini{padding:5px 10px;font-size:12px;border-radius:8px}
input,select{background:#0a0d13;color:var(--texto);border:1px solid var(--borde);
  padding:11px 13px;border-radius:10px;font-size:15px;width:100%;margin-bottom:12px}
input:focus,select:focus{outline:none;border-color:var(--oro);box-shadow:0 0 0 3px rgba(245,158,11,.15)}
label{font-size:13px;color:var(--sub);display:block;margin-bottom:5px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 8px;border-bottom:1px solid rgba(255,255,255,.05);text-align:left;
  vertical-align:middle}
th{color:var(--oro2);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
tr:last-child td{border-bottom:none}
.ok{color:var(--ok)}.mal{color:var(--mal)}.av{color:var(--azul)}.oro{color:var(--oro2)}
.hash{font-family:Consolas,"Courier New",monospace;font-size:11px;color:#6b7488;
  word-break:break-all}
.mina{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--ok);
  margin-right:6px;box-shadow:0 0 8px rgba(52,211,153,.8)}
.msg{padding:12px 14px;border-radius:10px;margin-bottom:14px;font-size:14px;line-height:1.45}
.msg.ok{background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.5);color:#a7f3d0}
.msg.mal{background:rgba(248,113,113,.10);border:1px solid rgba(248,113,113,.5);color:#fecaca}
.chip{display:inline-block;background:rgba(255,255,255,.04);border:1px solid var(--borde);
  border-radius:999px;padding:3px 11px;font-size:12px;color:#c6cddc;margin:2px}
.chip.mono{font-family:Consolas,monospace;font-size:11px}
.footer{color:#596174;font-size:11.5px;margin-top:26px;text-align:center;line-height:1.6}
.medalla{font-size:18px}
.rank-pos{font-weight:900;color:var(--sub);width:34px}
.perfil-cab{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.perfil-cab svg{border-radius:12px;border:1px solid var(--borde)}
.copiador{display:flex;gap:8px;align-items:stretch}
.copiador .direccion{margin:0;flex:1}
.hero{text-align:center;padding:26px 10px 6px}
.hero .logo-big{font-size:56px}
.hero h1{font-size:30px;margin:8px 0}
@media (max-width:640px){
  .cont{padding:12px}
  nav{width:100%;margin-left:0;overflow-x:auto;padding-bottom:4px}
  .saldo{font-size:34px}
  th,td{padding:7px 5px;font-size:12.5px}
}
"""

COPIAR_JS = r"""
function copiar(id, btn){
  const t = document.getElementById(id).textContent.trim();
  (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject())
    .then(()=>{ const o=btn.textContent; btn.textContent='¡Copiado!'; setTimeout(()=>btn.textContent=o,1200); })
    .catch(()=>{ const r=document.createRange(); r.selectNode(document.getElementById(id));
      getSelection().removeAllRanges(); getSelection().addRange(r); });
}
"""

ESTADO_JS = r"""
async function refrescar(){
  try{
    const r = await fetch('/api/estado');
    if(!r.ok) return;
    const d = await r.json();
    const set=(id,v)=>{const e=document.getElementById(id); if(e) e.textContent=v;};
    set('est-saldo', d.saldo);
    set('est-bloques', d.bloques);
    set('est-pendientes', d.pendientes);
    set('est-dificultad', d.dificultad);
    set('est-recompensa', d.recompensa);
  }catch(e){}
}
setInterval(refrescar, 8000);
"""

NOTIF_JS = r"""
// ===== Notificaciones Yuro (bonitas, sin apps externas) =====
(function(){
  // Estilos CSS para las notificaciones
  var css = `
  .youro-notif-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-width: 360px;
    pointer-events: none;
  }
  .youro-notif {
    background: linear-gradient(135deg, #1a1f2e 0%, #12161f 100%);
    border: 1px solid #2a3142;
    border-radius: 14px;
    padding: 14px 16px;
    color: #e8ebf2;
    font-family: system-ui, -apple-system, sans-serif;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05) inset;
    cursor: pointer;
    pointer-events: auto;
    animation: youro-slide-in 0.4s cubic-bezier(0.21, 1.02, 0.73, 1);
    transition: transform 0.2s, opacity 0.2s;
    position: relative;
    overflow: hidden;
  }
  .youro-notif::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: var(--notif-color, #f59e0b);
    border-radius: 4px 0 0 4px;
  }
  .youro-notif:hover {
    transform: translateX(-4px);
  }
  .youro-notif.exiting {
    animation: youro-slide-out 0.3s ease-in forwards;
  }
  .youro-notif-icon {
    font-size: 24px;
    margin-right: 12px;
    flex-shrink: 0;
  }
  .youro-notif-content {
    flex: 1;
    min-width: 0;
  }
  .youro-notif-title {
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 4px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .youro-notif-badge {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .youro-notif-msg {
    font-size: 13px;
    color: #8b94a8;
    line-height: 1.4;
    word-break: break-word;
  }
  .youro-notif-close {
    position: absolute;
    top: 8px;
    right: 8px;
    background: none;
    border: none;
    color: #596174;
    font-size: 18px;
    cursor: pointer;
    padding: 4px;
    line-height: 1;
    transition: color 0.2s;
  }
  .youro-notif-close:hover {
    color: #e8ebf2;
  }
  .youro-notif-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 2px;
    background: var(--notif-color, #f59e0b);
    animation: youro-progress linear forwards;
    opacity: 0.6;
  }
  @keyframes youro-slide-in {
    from { transform: translateX(120%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes youro-slide-out {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(120%); opacity: 0; }
  }
  @keyframes youro-progress {
    from { width: 100%; }
    to { width: 0%; }
  }
  @keyframes youro-pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
  }
  .youro-notif-icon.pulse {
    animation: youro-pulse 0.5s ease-in-out;
  }
  @media (max-width: 480px) {
    .youro-notif-container {
      left: 12px;
      right: 12px;
      max-width: none;
    }
  }
  `;
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // Contenedor de notificaciones
  var container = document.createElement('div');
  container.className = 'youro-notif-container';
  document.body.appendChild(container);

  // Colores por tipo
  var COLORES = {
    dinero: '#34d399',
    anuncio: '#f59e0b',
    emergencia: '#f87171',
    congelado: '#7dd3fc',
    descongelado: '#fbbf24',
    multa: '#f87171',
    info: '#8b94a8',
    exito: '#34d399'
  };

  // Sonido de notificación (oscilador simple)
  function sonar(tipo) {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      if (tipo === 'emergencia' || tipo === 'multa') {
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        osc.frequency.setValueAtTime(330, ctx.currentTime + 0.1);
        osc.frequency.setValueAtTime(440, ctx.currentTime + 0.2);
      } else if (tipo === 'dinero') {
        osc.frequency.setValueAtTime(523, ctx.currentTime);
        osc.frequency.setValueAtTime(659, ctx.currentTime + 0.1);
        osc.frequency.setValueAtTime(784, ctx.currentTime + 0.2);
      } else {
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        osc.frequency.setValueAtTime(800, ctx.currentTime + 0.1);
      }

      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    } catch(e) {}
  }

  // Mostrar notificación
  window.youroNotif = function(titulo, mensaje, tipo, duracion) {
    tipo = tipo || 'info';
    duracion = duracion || 6000;
    var color = COLORES[tipo] || COLORES.info;
    var icono = {
      dinero: '💰',
      anuncio: '📢',
      emergencia: '🚨',
      congelado: '🧊',
      descongelado: '☀️',
      multa: '🔨',
      info: 'ℹ️',
      exito: '✅'
    }[tipo] || 'ℹ️';

    var el = document.createElement('div');
    el.className = 'youro-notif';
    el.style.setProperty('--notif-color', color);
    el.innerHTML = `
      <div class="youro-notif-icon pulse">${icono}</div>
      <div class="youro-notif-content">
        <div class="youro-notif-title">
          ${titulo}
          <span class="youro-notif-badge">${tipo}</span>
        </div>
        <div class="youro-notif-msg">${mensaje}</div>
      </div>
      <button class="youro-notif-close">&times;</button>
      <div class="youro-notif-progress" style="animation-duration:${duracion}ms"></div>
    `;

    // Cerrar al hacer clic
    function cerrar() {
      el.classList.add('exiting');
      setTimeout(function(){ el.remove(); }, 300);
    }
    el.querySelector('.youro-notif-close').addEventListener('click', function(e){
      e.stopPropagation();
      cerrar();
    });
    el.addEventListener('click', cerrar);

    // Auto-cerrar
    var timer = setTimeout(cerrar, duracion);

    // Añadir al contenedor (arriba del todo)
    container.insertBefore(el, container.firstChild);

    // Mantener máximo 4 notificaciones visibles
    var notifs = container.querySelectorAll('.youro-notif');
    if (notifs.length > 4) {
      notifs[notifs.length - 1].remove();
    }

    // Sonar
    sonar(tipo);

    // También notificación del navegador si está permitido
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        var n = new Notification(titulo, {
          body: mensaje,
          icon: '/icono.png',
          tag: 'youro-' + Date.now()
        });
        n.onclick = function(){ window.focus(); n.close(); };
      } catch(e) {}
    }

    return el;
  };

  // Pedir permiso de notificaciones
  if ('Notification' in window && Notification.permission === 'default') {
    setTimeout(function(){
      Notification.requestPermission();
    }, 3000);
  }

  // Conectar a SSE
  function conectarSSE() {
    if (!window.EventSource) return;
    var es = new EventSource('/api/notificaciones');
    es.onmessage = function(ev) {
      try {
        var d = JSON.parse(ev.data);
        var tipoMap = {
          'dinero': 'dinero',
          'anuncio': 'anuncio',
          'emergencia': 'emergencia',
          'congelado': 'congelado',
          'descongelado': 'descongelado',
          'multa': 'multa'
        };
        window.youroNotif(d.titulo, d.mensaje, d.tipo || 'info', 8000);
      } catch(e) {}
    };
    es.onerror = function(){
      es.close();
      setTimeout(conectarSSE, 5000);
    };
  }

  // Solo conectar si hay sesión
  if (document.querySelector('nav a[href="/salir"]')) {
    conectarSSE();
  }
})();
"""


def plantilla(titulo, contenido, activo="", usuario=None, stats=None, extra_js=""):
    nav_items = [
        ("panel", "/", "Panel"),
        ("enviar", "/enviar", "Enviar"),
        ("minar", "/minar", "Minar"),
        ("tablon", "/tablon", "📋 Tablón"),
        ("explorador", "/explorador", "Explorador"),
        ("ranking", "/ranking", "Ranking"),
    ]
    links = "".join(
        f'<a href="{href}" class="{"activo" if activo==clave else ""}">{etiqueta}</a>'
        for clave, href, etiqueta in nav_items
    )
    if usuario:
        links += (f'<a href="/u/{esc(usuario["nombre"])}">👤 {esc(usuario["nombre"])}</a>'
                  f'<a href="/cuenta" class="{"activo" if activo=="cuenta" else ""}">⚙️</a>'
                  f'<a href="/salir" class="salir">Salir</a>')
        if usuario["es_admin"]:
            links = ('<a href="/admin" class="' + ("activo" if activo == "admin" else "") + '">👑 Gobierno</a>') + links
    else:
        links += ('<a href="/login" class="' + ("activo" if activo == "login" else "") + '">Entrar</a>'
                  '<a href="/registro" class="' + ("activo" if activo == "registro" else "") + '">Crear cuenta</a>')

    barra = ""
    if stats:
        clase_val = "ok" if stats.get("valida") else "mal"
        texto_val = "cadena íntegra ✓" if stats.get("valida") else "cadena ALTERADA ✗"
        barra = (
            f'<div class="stats">'
            f'<span>⛏️ bloques <b id="est-bloques">{stats.get("bloques", 0)}</b></span>'
            f'<span>⏳ pendientes <b id="est-pendientes">{stats.get("pendientes", 0)}</b></span>'
            f'<span>⚒ dificultad <b id="est-dificultad">{stats.get("dificultad", 0)}</b> ceros</span>'
            f'<span>🎁 recompensa <b id="est-recompensa">{formatear(stats.get("recompensa", 0))}</b> Y</span>'
            f'<span>🏦 suministro <b>{formatear(stats.get("suministro", 0))}</b> Y</span>'
            f'<span class="{clase_val}">{texto_val}</span>'
            f"</div>"
        )

    js = COPIAR_JS
    if usuario:
        js += NOTIF_JS
    if extra_js == "estado":
        js += ESTADO_JS
    elif extra_js:
        js += extra_js
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f59e0b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Yuro">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/icono.png">
<link rel="icon" href="/icono.png" type="image/png">
<title>Yuro · {esc(titulo)}</title>
<style>{CSS}</style>
<script>
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(()=>{{}}));
}}
</script>
</head>
<body>
<div class="cont">
  <header class="top">
    <a class="logo" href="/"><span class="moneda">Y</span>Yuro</a>
    <nav>{links}</nav>
  </header>
  {barra}
  {contenido}
  <p class="footer">Yuro (Y) es una moneda de juegos entre amigos · libro mayor público y transparente · <b>no vale dinero real</b></p>
</div>
<script>{js}</script>
</body>
</html>"""


# ======================================================================
#  Páginas
# ======================================================================

def pagina_login(error=None, ok=None):
    msg = f'<div class="msg mal">{esc(error)}</div>' if error else ""
    if ok:
        msg = f'<div class="msg ok">{esc(ok)}</div>'
    contenido = f"""
    <div class="hero">
      <div class="logo-big">🪙</div>
      <h1>Tu moneda, tus amigos</h1>
      <p class="sub">Blockchain privada para tu grupo: regístrate, mina yuros y paga a tus amigos.
      Todos los saldos son públicos y transparentes.</p>
    </div>
    <div class="panel" style="max-width:430px;margin:0 auto">
      <h2>Entrar</h2>{msg}
      <form method="post" action="/login">
        <label>Nombre de usuario</label>
        <input type="text" name="nombre" autocomplete="username" required autofocus>
        <label>Contraseña</label>
        <input type="password" name="password" autocomplete="current-password" required>
        <button type="submit">Entrar</button>
      </form>
      <p class="sub" style="margin-top:14px">¿No tienes cuenta?
        <a href="/registro">Regístrate gratis</a> y te regalamos <b class="oro">Y {formatear(config.BIENVENIDA)}</b>.</p>
    </div>"""
    return plantilla("Entrar", contenido, "login")


def pagina_registro(error=None):
    msg = f'<div class="msg mal">{esc(error)}</div>' if error else ""
    contenido = f"""
    <div class="hero">
      <div class="logo-big">🪙</div>
      <h1>Crea tu cuenta Yuro</h1>
      <p class="sub">Al registrarte recibes <b class="oro">Y {formatear(config.BIENVENIDA)}</b> de bienvenida.
      Después mina bloques y envíales yuros a tus amigos.</p>
    </div>
    <div class="panel" style="max-width:430px;margin:0 auto">
      <h2>Crear cuenta</h2>{msg}
      <form method="post" action="/registro">
        <label>Elige un nombre de usuario (3-16 caracteres: letras, números o _)</label>
        <input type="text" name="nombre" pattern="[A-Za-z0-9_]{{3,16}}" autocomplete="username" required autofocus>
        <label>Contraseña (mínimo {config.MIN_CARACTERES_PASSWORD} caracteres)</label>
        <input type="password" name="password" minlength="{config.MIN_CARACTERES_PASSWORD}" autocomplete="new-password" required>
        <button type="submit">Crear cuenta y cobrar Y {formatear(config.BIENVENIDA)}</button>
      </form>
      <p class="sub" style="margin-top:14px">¿Ya tienes cuenta? <a href="/login">Entra aquí</a>.</p>
    </div>"""
    return plantilla("Crear cuenta", contenido, "registro")


def pagina_panel(usuario, saldo, movimientos, stats, anuncios=None, datos_grafica=None, actividad=None):
    dir_u = usuario["direccion"]
    filas = ""
    for m in movimientos:
        entrada = m["para"] == dir_u
        contra = m["contra_nombre"] or corta_dir(m["direccion_contra"])
        cantidad = f'{"+Y" if entrada else "−Y"}{formatear(m["cantidad"])}'
        concepto = f' <span class="sub">· {esc(m["concepto"])}</span>' if m.get("concepto") else ""
        bloque = f'#{m["bloque_num"]}' if m.get("bloque_num") is not None else '<span class="oro">pendiente</span>'
        enlace = (f"<a href='/u/{esc(m['contra_nombre'])}'>{esc(contra)}</a>"
                  if m.get("contra_nombre") else esc(contra))
        icono = "🟢" if entrada else "🔴"
        filas += (
            f"<tr><td>{bloque}</td>"
            f"<td>{icono} {'recibes' if entrada else 'envías'}</td>"
            f"<td class='{'ok' if entrada else 'mal'}' style='font-weight:700'>{cantidad}</td>"
            f"<td>{enlace}{concepto}</td>"
            f"<td class='sub'>{fecha(m['timestamp'])}</td></tr>"
        )
    if not filas:
        filas = ("<tr><td colspan=5 class='sub'>Sin movimientos todavía. "
                 "¡Regala a tus amigos tu dirección y mina tu primer bloque!</td></tr>")

    html_anuncios = ""
    if anuncios:
        for a in anuncios:
            html_anuncios += (
                f"<div class='panel' style='border-color:#f59e0b;margin-bottom:10px'>"
                f"<b>📢 Anuncio del gobierno</b> "
                f"<span class='sub'>{fecha(a['timestamp'])}</span><br>"
                f"{esc(a['mensaje'])}</div>"
            )

    # Estadísticas rápidas
    recibido_total = sum(m["cantidad"] for m in movimientos if m["para"] == dir_u)
    enviado_total = sum(m["cantidad"] for m in movimientos if m["de"] == dir_u)
    n_recibidos = sum(1 for m in movimientos if m["para"] == dir_u)
    n_enviados = sum(1 for m in movimientos if m["de"] == dir_u)

    # Gráfica de historial
    grafica_html = ""
    if datos_grafica and len(datos_grafica) > 1:
        valores = [d[1] for d in datos_grafica]
        etiquetas = [d[0] for d in datos_grafica]
        grafica_html = f'''
        <div class="panel">
          <h2>📈 Historial de saldo</h2>
          <p class="sub">Evolución de tu saldo en las últimas transacciones</p>
          {charts.grafica_lineas(valores, etiquetas, color="#f59e0b", alto=180)}
        </div>'''

    # Heatmap de actividad
    heatmap_html = ""
    if actividad:
        heatmap_html = f'''
        <div class="panel">
          <h2>🔥 Actividad de la red</h2>
          <p class="sub">Cuándo se mueven más yuros (más brillante = más actividad)</p>
          {charts.heatmap_actividad(actividad, alto=100)}
        </div>'''

    contenido = f"""
    {html_anuncios}

    <!-- Tarjetas de estadísticas -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px">
      {charts.stat_card(f"Y{formatear(recibido_total)}", "Recibido", "📥", "#34d399", 
                       ((recibido_total - enviado_total) / enviado_total * 100 if enviado_total else None))}
      {charts.stat_card(f"Y{formatear(enviado_total)}", "Enviado", "📤", "#f87171")}
      {charts.stat_card(str(n_recibidos + n_enviados), "Movimientos", "🔄", "#7dd3fc")}
      {charts.stat_card(str(stats.get('bloques', 0)), "Bloques", "⛏️", "#f59e0b")}
    </div>

    <div class="grid">
      <div class="panel" style="position:relative;overflow:hidden">
        <div style="position:absolute;top:-20px;right:-20px;font-size:100px;opacity:0.05">💰</div>
        <h2>Tu saldo</h2>
        <div class="saldo" id="est-saldo">Y {formatear(saldo)}</div>
        <p class="sub">yuros en tu cartera · visible para todos</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
          <a class="btn" href="/enviar">💸 Enviar</a>
          <a class="btn sec" href="/minar">⛏️ Minar</a>
          <a class="btn sec" href="/u/{esc(usuario['nombre'])}">👤 Mi perfil</a>
        </div>
      </div>
      <div class="panel">
        <h2>Tu dirección</h2>
        <div class="copiador">
          <span class="direccion" id="dir-mia">{esc(dir_u)}</span>
          <button class="btn mini" type="button" onclick="copiar('dir-mia', this)">Copiar</button>
        </div>
        <p class="sub" style="margin-top:10px">Comparte tu nombre o dirección para cobrar.</p>
      </div>
    </div>

    {grafica_html}
    {heatmap_html}

    <div class="panel">
      <h2>Últimos movimientos</h2>
      <table>
        <tr><th>Bloque</th><th>Tipo</th><th>Cantidad</th><th>Con</th><th>Fecha</th></tr>
        {filas}
      </table>
    </div>"""
    return plantilla("Panel", contenido, "panel", usuario, stats, extra_js="estado")


def pagina_enviar(usuario, saldo, nombres_amigos, mensaje=None, error=None, destino_previo="", cantidad_previa="", concepto_previo="", csrf=""):
    msg = f'<div class="msg ok">{esc(mensaje)}</div>' if mensaje else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'
    opciones = "".join(
        f'<option value="{esc(n)}">{esc(n)}</option>' for n in nombres_amigos
        if n != usuario["nombre"]
    )
    contenido = f"""
    <div class="panel" style="max-width:480px">
      <h2>Enviar yuros</h2>
      <p class="sub">Tu saldo: <b class="av">Y {formatear(saldo)}</b> · como en un banco, el pago
      queda registrado para siempre en el libro mayor público.</p>
      {msg}
      <form method="post" action="/enviar">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <label>Para (nombre de usuario o dirección yuro…)</label>
        <input type="text" name="destino" list="amigos" value="{esc(destino_previo)}"
               placeholder="ej: maria o yuro1a3f…" required>
        <datalist id="amigos">{opciones}</datalist>
        <label>Cantidad (Y)</label>
        <input type="number" name="cantidad" min="0.01" step="0.01" max="100000000"
               value="{esc(cantidad_previa)}" required>
        <label>Concepto del pago (opcional, máx. {config.LIMITE_CONCEPTO} caracteres)</label>
        <input type="text" name="concepto" maxlength="{config.LIMITE_CONCEPTO}"
               value="{esc(concepto_previo)}" placeholder="ej: pizza del viernes">
        <button type="submit">Enviar</button>
      </form>
      <p class="sub" style="margin-top:12px">La transacción entra en la cola pendiente y se confirma
      cuando alguien mine el siguiente bloque.</p>
    </div>"""
    return plantilla("Enviar", contenido, "enviar", usuario, None)


def pagina_minar(usuario, stats, saldo, mensaje=None, error=None, csrf=""):
    msg = f'<div class="msg ok">{esc(mensaje)}</div>' if mensaje else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'
    halvings = stats["bloques"] // config.HALVING_CADA
    contenido = f"""
    <div class="panel" style="max-width:560px">
      <h2>⛏️ Minar un bloque</h2>
      <p class="sub">Minar valida las transacciones pendientes, las encadena y te da la recompensa.
      Es <b>prueba de trabajo real</b>: cuesta CPU, por eso el dinero nuevo no se puede inflar.
      </p>
      {msg}
      <div class="grid" style="margin:12px 0">
        <div class="panel" style="margin:0">
          <div class="sub">Recompensa actual</div>
          <div class="oro" style="font-size:26px;font-weight:900">Y {formatear(stats['recompensa'])}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Dificultad (próximo bloque)</div>
          <div class="av" style="font-size:26px;font-weight:900">{stats['dificultad']} ceros</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Transacciones esperando</div>
          <div style="font-size:26px;font-weight:900">{stats['pendientes']}</div>
        </div>
      </div>
      <p class="sub">Halvings hechos: <b>{halvings}</b> ·
      próximo halving en <b>{max(stats['proximo_halving'] - stats['bloques'], 0)}</b> bloques ·
      mínimo entre bloques: <b>{config.MINIMO_ENTRE_BLOQUES}s</b> ·
      tu saldo: <b class="av">Y {formatear(saldo)}</b></p>
      <form method="post" action="/minar">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <button type="submit">Minar ahora (Y {formatear(stats['recompensa'])})</button>
      </form>
    </div>"""
    return plantilla("Minar", contenido, "minar", usuario, stats)


def pagina_bloque_minado(usuario, bloque, stats):
    contenido = f"""
    <div class="panel" style="max-width:560px">
      <h2>⛏️ ¡Bloque minado!</h2>
      <div class="msg ok">Has minado el bloque <b>#{bloque['indice']}</b> con
      <b>{bloque['transacciones']}</b> transacciones y ganaste <b>Y {formatear(bloque['recompensa'])}</b>.</div>
      <p class="sub">Hash del bloque:</p>
      <span class="direccion">{esc(bloque['hash'])}</span>
      <p class="sub" style="margin-top:10px">Nonce: <b>{bloque['nonce']}</b> ·
      dificultad: <b>{bloque['dificultad']} ceros</b> ·
      enlaza con <span class="hash">{esc(corta_dir(bloque['hash_anterior'], 30))}</span></p>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <a class="btn" href="/">Volver al panel</a>
        <a class="btn sec" href="/minar">Minar otro</a>
        <a class="btn sec" href="/explorador">Ver en el explorador</a>
      </div>
    </div>"""
    return plantilla("Bloque minado", contenido, "minar", usuario, stats)


def pagina_explorador(usuario, bloques, pendientes, stats, transacciones_func):
    filas_pend = ""
    for t in pendientes:
        concepto = f' <span class="sub">· {esc(t["concepto"])}</span>' if t.get("concepto") else ""
        filas_pend += (
            f"<div class='chip'>⏳ {esc(corta_dir(t['de'], 14))} → {esc(corta_dir(t['para'], 14))} "
            f"<b>Y {formatear(t['cantidad'])}</b>{concepto}</div>"
        )
    pend_html = ""
    if filas_pend:
        pend_html = f'<div class="panel"><h2>⏳ Transacciones pendientes de minar</h2>{filas_pend}</div>'

    bloques_html = ""
    for b in bloques:
        txs = transacciones_func(b["indice"])
        chips = "".join(
            f"<div class='chip'>"
            f"{'⛏️ recompensa' if t['tipo']=='coinbase' else ('🎁 regalo' if t['tipo']=='faucet' else esc(corta_dir(t['de'], 12)))}"
            f" → {esc(corta_dir(t['para'], 12))} <b>Y {formatear(t['cantidad'])}</b>"
            f"{' · ' + esc(t['concepto']) if t.get('concepto') else ''}</div>"
            for t in txs
        ) or "<span class='sub'>(sin transacciones)</span>"
        bloques_html += f"""
        <div class="panel">
          <span class="mina"></span><b>Bloque #{b['indice']}</b>
          <span class="sub">· minado por {esc(b['minero_nombre'] or corta_dir(b['minero']))} · {fecha(b['timestamp'])}</span>
          <div style="margin:8px 0">{chips}</div>
          <div class="hash">hash: {esc(b['hash'])}</div>
          <div class="hash">anterior: {esc(corta_dir(b['hash_anterior'], 40))} · nonce: {b['nonce']} · dificultad: {b['dificultad']}</div>
        </div>"""

    siguiente = f'<a class="btn sec" href="/explorador?desde={bloques[-1]["indice"]}">Bloques anteriores →</a>' if bloques else ""
    contenido = f"""
    <div class="panel">
      <h2>Explorador de bloques</h2>
      <p class="sub">Cada bloque encadena un hash del anterior: si alguien toca un bloque viejo se rompe
      toda la cadena y la validación lo detecta. Esa es la magia de Bitcoin, aquí en tu grupo.</p>
    </div>{pend_html}{bloques_html}
    <p style="text-align:center">{siguiente}</p>"""
    return plantilla("Explorador", contenido, "explorador", usuario, stats)


def pagina_ranking(usuario, filas, stats):
    medallas = ["🥇", "🥈", "🥉"]
    filas_html = ""
    for i, f in enumerate(filas):
        pos = i + 1
        nombre = f["nombre"] or corta_dir(f["direccion"], 14)
        propio = usuario and f["direccion"] == usuario["direccion"]
        accion = ("<span class=oro>(tú)</span>" if propio else
                  (f"<a class='btn sec mini' href='/enviar?para={esc(nombre)}'>Enviar</a>"
                   if usuario else ""))
        filas_html += (
            f"<tr{' style=background:rgba(245,158,11,.06)' if propio else ''}>"
            f"<td class='rank-pos'>{medallas[pos-1] if pos<=3 else pos}</td>"
            f"<td>{identicon_svg(f['direccion'], 28)} <a href='/u/{esc(nombre)}'><b>{esc(nombre)}</b></a></td>"
            f"<td class='hash' style='max-width:120px'>{esc(corta_dir(f['direccion'], 20))}</td>"
            f"<td class='oro' style='font-weight:800;text-align:right'>Y {formatear(f['saldo'])}</td>"
            f"<td style='text-align:right'>{accion}</td>"
            f"</tr>"
        )
    if not filas_html:
        filas_html = "<tr><td colspan=5 class='sub'>Todavía no hay yuros en circulación.</td></tr>"

    # Gráfica de barras con top 10
    grafica_html = ""
    if filas:
        top10 = [(f["nombre"] or corta_dir(f["direccion"], 10), f["saldo"]) for f in filas[:10]]
        if len(top10) > 1:
            total = sum(s for _, s in filas)
            # Donut con distribución
            top5_pcts = [(f["saldo"], f["nombre"] or corta_dir(f["direccion"], 8)) for f in filas[:5]]
            resto = total - sum(s for s, _ in top5_pcts)
            if resto > 0:
                top5_pcts.append((resto, "Resto"))
            porcentajes = [(s / total * 100, n) for s, n in top5_pcts]

            grafica_html = f'''
            <div class="grid" style="margin-top:14px">
              <div class="panel">
                <h2>📊 Top 10 por saldo</h2>
                {charts.grafica_barras(top10, color="#f59e0b", alto=280)}
              </div>
              <div class="panel">
                <h2>🥧 Distribución de riqueza</h2>
                <p class="sub">Quién tiene qué porcentaje del total</p>
                {charts.grafica_donut(porcentajes, centro_texto="Total", centro_valor=f"Y{formatear(total)}")}
              </div>
            </div>'''

    contenido = f"""
    <div class="panel">
      <h2>🏆 Ranking Yuro</h2>
      <p class="sub">Los saldos son públicos: aquí está todo el dinero que tiene cada uno,
      ordenado de mayor a menor. Transparencia total.</p>
      <table>
        <tr><th>#</th><th>Usuario</th><th>Dirección</th><th style="text-align:right">Saldo</th><th></th></tr>
        {filas_html}
      </table>
    </div>
    {grafica_html}"""
    return plantilla("Ranking", contenido, "ranking", usuario, stats)


def pagina_perfil(usuario, publico, perfil, movimientos, stats, es_propio=False):
    dir_p = publico["direccion"]
    filas = ""
    for m in movimientos:
        entrada = m["para"] == dir_p
        contra = m["contra_nombre"] or corta_dir(m["direccion_contra"])
        bloque = f'#{m["bloque_num"]}' if m.get("bloque_num") is not None else '<span class="oro">pendiente</span>'
        enlace = (f"<a href='/u/{esc(m['contra_nombre'])}'>{esc(contra)}</a>"
                  if m.get("contra_nombre") else esc(contra))
        filas += (
            f"<tr><td>{bloque}</td>"
            f"<td>{icono_tipo(m['tipo'], entrada)} {'recibes' if entrada else 'envías'}</td>"
            f"<td class='{'ok' if entrada else 'mal'}' style='font-weight:700'>"
            f"{'+Y' if entrada else '−Y'}{formatear(m['cantidad'])}</td>"
            f"<td>{enlace}{' · ' + esc(m['concepto']) if m.get('concepto') else ''}</td>"
            f"<td class='sub'>{fecha(m['timestamp'])}</td></tr>"
        )
    if not filas:
        filas = "<tr><td colspan=5 class='sub'>Sin movimientos todavía.</td></tr>"

    contenido = f"""
    <div class="panel">
      <div class="perfil-cab">
        {identicon_svg(dir_p, 84)}
        <div style="flex:1;min-width:200px">
          <h1 style="margin:0">{esc(publico['nombre'])}
            <span class="chip">{'tú' if es_propio else 'usuario'}</span></h1>
          <p class="sub" style="margin:4px 0">en Yuro desde el {fecha(publico['creado'])}</p>
          <div class="saldo" style="font-size:34px">Y {formatear(perfil['saldo'])}</div>
        </div>
        <div>
          <button class="btn mini" type="button" onclick="copiar('dir-perfil', this)">Copiar dirección</button>
          {f'<a class="btn sec mini" href="/enviar?para={esc(publico["nombre"])}">Enviar Y</a>' if usuario and not es_propio else ''}
        </div>
      </div>
      <span class="direccion" id="dir-perfil">{esc(dir_p)}</span>
      <div class="grid" style="margin-top:14px">
        <div class="panel" style="margin:0"><div class="sub">Recibido (lifetime)</div>
          <b class="ok" style="font-size:20px">+ Y {formatear(perfil['recibido'])}</b></div>
        <div class="panel" style="margin:0"><div class="sub">Enviado (lifetime)</div>
          <b class="mal" style="font-size:20px">− Y {formatear(perfil['enviado'])}</b></div>
        <div class="panel" style="margin:0"><div class="sub">Transacciones</div>
          <b style="font-size:20px">{perfil['transacciones']}</b></div>
        <div class="panel" style="margin:0"><div class="sub">Bloques minados</div>
          <b style="font-size:20px">⛏️ {perfil['bloques_minados']}</b></div>
      </div>
    </div>
    <div class="panel">
      <h2>Movimientos públicos</h2>
      <table>
        <tr><th>Bloque</th><th>Tipo</th><th>Cantidad</th><th>Contra</th><th>Fecha</th></tr>
        {filas}
      </table>
    </div>"""
    return plantilla(f"Perfil de {publico['nombre']}", contenido, "", usuario, stats)


def pagina_admin(usuario, gobierno, usuarios, anuncios, log, stats, ok=None, error=None):
    msg = f'<div class="msg ok">{esc(ok)}</div>' if ok else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'

    filas = ""
    for u in usuarios:
        badge = '<span class="chip" style="border-color:#f59e0b;color:#fbbf24">👑</span>' if u["es_admin"] else ""
        estado = ""
        if u["congelado"]:
            estado = ' <span class="chip" style="border-color:#f87171;color:#f87171">🧊 CONGELADO</span>'
        filas += (
            f"<tr><td><b>{esc(u['nombre'])}</b> {badge}{estado}</td>"
            f"<td class='hash'>{esc(corta_dir(u['direccion'], 22))}</td>"
            f"<td class='oro' style='font-weight:700;text-align:right'>Y {formatear(u['saldo'])}</td>"
            f"<td class='sub'>{fecha(u['creado'])}</td></tr>"
        )

    opciones_usuarios = "".join(
        f'<option value="{esc(u["nombre"])}">{esc(u["nombre"])} (Y{formatear(u["saldo"])})'
        f'{" 🧊" if u["congelado"] else ""}</option>'
        for u in usuarios if not u["es_admin"]
    )

    opciones_congelar = "".join(
        f'<option value="{esc(u["nombre"])}">{esc(u["nombre"])}'
        f'{" — 🧊 congelado" if u["congelado"] else ""}</option>'
        for u in usuarios if not u["es_admin"]
    )

    filas_anuncios = ""
    for a in anuncios:
        filas_anuncios += (
            f"<div style='margin:8px 0;padding:10px;background:rgba(245,158,11,.06);"
            f"border:1px solid rgba(245,158,11,.3);border-radius:10px'>"
            f"<b>{esc(a['autor'])}</b> <span class='sub'>{fecha(a['timestamp'])}</span><br>"
            f"{esc(a['mensaje'])}"
            f" <form method='post' action='/admin/anuncio/quitar' style='display:inline'>"
            f"<input type='hidden' name='csrf' value='{esc(usuario['csrf'])}'>"
            f"<input type='hidden' name='id' value='{a['id']}'>"
            f"<button class='btn mini sec' style='margin-left:8px'>✕</button></form></div>"
        )
    if not filas_anuncios:
        filas_anuncios = '<p class="sub">No hay anuncios activos.</p>'

    filas_log = ""
    for e in log:
        filas_log += (
            f"<tr><td class='sub'>{fecha(e['timestamp'])}</td>"
            f"<td><b>{esc(e['admin'])}</b></td>"
            f"<td>{esc(e['accion'])}</td>"
            f"<td class='sub'>{esc(e['detalle'] or '')}</td></tr>"
        )
    if not filas_log:
        filas_log = '<tr><td colspan="4" class="sub">Sin acciones registradas.</td></tr>'

    emergencia_btn = (
        f'<form method="post" action="/admin/emergencia" style="display:inline">'
        f'<input type="hidden" name="csrf" value="{esc(usuario["csrf"])}">'
        f'<input type="hidden" name="accion" value="desactivar">'
        f'<button style="background:#dc2626;color:#fff">🔴 Desactivar emergencia</button></form>'
        if gobierno["emergencia"] else
        f'<form method="post" action="/admin/emergencia" style="display:inline">'
        f'<input type="hidden" name="csrf" value="{esc(usuario["csrf"])}">'
        f'<input type="hidden" name="accion" value="activar">'
        f'<button style="background:#dc2626;color:#fff">🚨 Activar emergencia</button></form>'
    )

    contenido = f"""
    <div class="panel" style="border-color:#f59e0b">
      <h2>👑 Gobierno Yuro</h2>
      <p class="sub">Eres la autoridad monetaria. Controlas impuestos, saldos,
      congelaciones, multas, anuncios y más.</p>
      {msg}
      <div class="grid" style="margin:12px 0">
        <div class="panel" style="margin:0">
          <div class="sub">Cuenta GOBIERNO</div>
          <div class="oro" style="font-size:26px;font-weight:900">Y {formatear(gobierno["saldo_gobierno"])}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Impuesto</div>
          <div style="font-size:26px;font-weight:900">{gobierno["impuesto"]:.1f}%</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Usuarios</div>
          <div style="font-size:26px;font-weight:900">{gobierno["total_usuarios"]}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Congelados</div>
          <div style="font-size:26px;font-weight:900;color:{'#f87171' if gobierno['congelados'] else 'inherit'}">{gobierno["congelados"]}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Recompensa minería</div>
          <div style="font-size:26px;font-weight:900">Y {formatear(gobierno["recompensa"])}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Estado</div>
          <div style="font-size:18px;font-weight:900;color:{'#f87171' if gobierno['emergencia'] else '#34d399'}">
            {'🚨 EMERGENCIA' if gobierno['emergencia'] else '✅ Normal'}
          </div>
          <div style="margin-top:8px">{emergencia_btn}</div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>💰 Impuesto</h2>
        <p class="sub">Se cobra en cada transacción (0-{config.IMPUESTO_MAX}%).</p>
        <form method="post" action="/admin/impuesto">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Impuesto (%)</label>
          <input type="number" name="porcentaje" min="0" max="{config.IMPUESTO_MAX}"
                 step="0.5" value="{gobierno['impuesto']}" required>
          <button type="submit">Aplicar</button>
        </form>
      </div>

      <div class="panel">
        <h2>⛏️ Recompensa minería</h2>
        <p class="sub">Youros que gana quien mina un bloque.</p>
        <form method="post" action="/admin/recompensa">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Recompensa (Y)</label>
          <input type="number" name="cantidad" min="{config.RECOMPENSA_MIN}" max="{config.RECOMPENSA_MAX}"
                 step="0.01" value="{gobierno['recompensa']}" required>
          <button type="submit">Aplicar</button>
        </form>
      </div>

      <div class="panel">
        <h2>🏦 Ajustar saldo</h2>
        <p class="sub">Crea o retira yuros (positivo = crear, negativo = retirar).</p>
        <form method="post" action="/admin/saldo">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Usuario</label>
          <select name="usuario" required>{opciones_usuarios}</select>
          <label>Cantidad (Y)</label>
          <input type="number" name="cantidad" step="0.01" required placeholder="100 o -50">
          <label>Concepto</label>
          <input type="text" name="concepto" maxlength="80" value="Ajuste del gobierno">
          <button type="submit">Aplicar</button>
        </form>
      </div>

      <div class="panel" style="border-color:#f87171">
        <h2>🔨 Multa</h2>
        <p class="sub">Quita yuros a un usuario como castigo. Van al GOBIERNO.</p>
        <form method="post" action="/admin/multa">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Usuario</label>
          <select name="usuario" required>{opciones_usuarios}</select>
          <label>Cantidad de la multa (Y)</label>
          <input type="number" name="cantidad" min="0.01" step="0.01" required placeholder="50">
          <label>Motivo</label>
          <input type="text" name="motivo" maxlength="120" placeholder="ej: spam">
          <button type="submit" style="background:linear-gradient(145deg,#f87171,#dc2626);color:#fff">Imponer multa</button>
        </form>
      </div>

      <div class="panel" style="border-color:#7dd3fc">
        <h2>🧊 Congelar / Descongelar</h2>
        <p class="sub">Una cuenta congelada no puede enviar ni recibir yuros.</p>
        <form method="post" action="/admin/congelar" style="margin-bottom:10px">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Usuario</label>
          <select name="usuario" required>{opciones_congelar}</select>
          <label>Motivo (opcional)</label>
          <input type="text" name="motivo" maxlength="120" placeholder="ej: comportamiento sospechoso">
          <button type="submit" style="background:linear-gradient(145deg,#7dd3fc,#0284c7);color:#fff">🧊 Congelar</button>
        </form>
        <form method="post" action="/admin/descongelar">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Descongelar a</label>
          <select name="usuario" required>{opciones_congelar}</select>
          <button type="submit" class="btn sec">☀️ Descongelar</button>
        </form>
      </div>

      <div class="panel">
        <h2>📢 Anuncios</h2>
        <p class="sub">Mensaje visible para todos los usuarios.</p>
        <form method="post" action="/admin/anuncio" style="margin-bottom:12px">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Anuncio</label>
          <textarea name="mensaje" maxlength="{config.ANUNCIO_MAX}" rows="3" required
                    style="width:100%;background:#0a0d13;color:var(--texto);border:1px solid var(--borde);padding:10px;border-radius:10px;font-size:14px"
                    placeholder="ej: Este fin de semana hay evento especial..."></textarea>
          <button type="submit" style="margin-top:8px">📢 Publicar</button>
        </form>
        {filas_anuncios}
      </div>
    </div>

    <div class="panel">
      <h2>📋 Todas las cuentas</h2>
      <table>
        <tr><th>Usuario</th><th>Dirección</th><th style="text-align:right">Saldo</th><th>Creado</th></tr>
        {filas}
      </table>
    </div>

    <div class="panel">
      <h2>📜 Registro de acciones</h2>
      <p class="sub">Últimas {len(log)} acciones del gobierno.</p>
      <table>
        <tr><th>Fecha</th><th>Admin</th><th>Acción</th><th>Detalle</th></tr>
        {filas_log}
      </table>
    </div>"""
    return plantilla("Gobierno", contenido, "admin", usuario, stats)


def pagina_cuenta(usuario, stats, ok=None, error=None):
    msg = f'<div class="msg ok">{esc(ok)}</div>' if ok else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'

    tema = tema_de_usuario(usuario["nombre"])
    ntfy_link = f"https://ntfy.sh/{tema}"

    contenido = f"""
    <div class="panel">
      <h2>⚙️ Mi cuenta</h2>
      <p class="sub">Gestiona los datos de tu cuenta Yuro.</p>
      {msg}

      <div class="grid" style="margin:14px 0">
        <div class="panel" style="margin:0">
          <div class="sub">Tu usuario</div>
          <div style="font-size:22px;font-weight:900">{esc(usuario['nombre'])}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Tu dirección</div>
          <div class="direccion" style="font-size:11px">{esc(usuario['direccion'])}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Miembro desde</div>
          <div style="font-size:18px;font-weight:700">{fecha(usuario['creado'])}</div>
        </div>
      </div>
    </div>

    <div class="panel" style="border-color:#7dd3fc">
      <h2>🔔 Notificaciones push</h2>
      <p class="sub">Recibe avisos en tu móvil o PC cuando te lleguen yuros,
      haya anuncios del gobierno o emergencias.</p>

      <div style="background:#0a0d13;padding:14px;border-radius:10px;border:1px solid #1d2b3d;margin:10px 0">
        <div class="sub">Tu tema personal de notificaciones:</div>
        <div class="direccion" style="margin:6px 0">{esc(tema)}</div>
      </div>

      <h3 style="font-size:15px;margin:16px 0 8px">📱 Cómo activarlas (gratis):</h3>
      <ol style="color:var(--sub);font-size:13.5px;line-height:1.8;padding-left:20px">
        <li>Instala la app <b style="color:var(--texto)">ntfy</b>
          (<a href="https://ntfy.sh/#install-app" target="_blank">Google Play</a>,
          <a href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank">App Store</a>
          o <a href="https://f-droid.org/packages/io.heckel.ntfy/" target="_blank">F-Droid</a>)</li>
        <li>Abre la app y toca <b style="color:var(--texto)">+ Subscribe to topic</b></li>
        <li>Escribe exactamente: <b style="color:var(--azul)">{esc(tema)}</b></li>
        <li>¡Listo! Recibirás avisos al instante</li>
      </ol>

      <div style="margin-top:14px">
        <a class="btn" href="{esc(ntfy_link)}" target="_blank">🔓 Probar enviándote una prueba</a>
      </div>
      <p class="sub" style="margin-top:8px">
        Al hacer clic se abrirá ntfy.sh y te llegará una notificación de prueba.
      </p>
    </div>

    <div class="panel">
      <h2>🔒 Cambiar contraseña</h2>
      <p class="sub">Al cambiarla se cierran todas las sesiones y tendrás que volver a entrar.</p>
      <form method="post" action="/cuenta/password" style="max-width:400px">
        <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
        <label>Contraseña actual</label>
        <input type="password" name="actual" required autocomplete="current-password">
        <label>Nueva contraseña (mínimo {config.MIN_CARACTERES_PASSWORD} caracteres)</label>
        <input type="password" name="nueva" required minlength="{config.MIN_CARACTERES_PASSWORD}" autocomplete="new-password">
        <button type="submit">🔒 Cambiar contraseña</button>
      </form>
    </div>"""
    return plantilla("Mi cuenta", contenido, "cuenta", usuario, stats)


def pagina_tablon(usuario, publicaciones, stats, ok=None, error=None):
    msg = f'<div class="msg ok">{esc(ok)}</div>' if ok else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'

    # Formulario de publicación
    form_html = ""
    if usuario and not usuario["congelado"]:
        form_html = f"""
    <div class="panel" style="border-color:#f59e0b">
      <h2>📝 Nueva publicación</h2>
      <form method="post" action="/tablon/publicar" enctype="multipart/form-data">
        <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
        <label>Título</label>
        <input type="text" name="titulo" maxlength="100" required
               placeholder="ej: Vendo espada legendaria">
        <label>Contenido (opcional)</label>
        <textarea name="contenido" maxlength="{config.TABLON_CONTENIDO_MAX}" rows="4"
                  style="width:100%;background:#0a0d13;color:var(--texto);border:1px solid var(--borde);padding:10px;border-radius:10px;font-size:14px"
                  placeholder="Describe tu publicación..."></textarea>
        <label>📎 Adjuntar archivo (imagen o documento, máx. 5MB)</label>
        <input type="file" name="archivo"
               accept="{','.join('.'+t for t in config.TABLON_TIPOS_OK)}"
               style="color:var(--sub);font-size:13px">
        <p class="sub" style="font-size:11px;margin:4px 0 10px">
          Formatos: imágenes (JPG, PNG, GIF, WebP) · documentos (PDF, TXT, DOC, CSV)
        </p>
        <button type="submit">📤 Publicar</button>
      </form>
    </div>"""

    # Publicaciones
    pubs_html = ""
    for p in publicaciones:
        # Avatar/identicon
        icono = identicon_svg(p["autor"], 36)

        # Archivo adjunto
        archivo_html = ""
        if p["archivo"]:
            tipo = (p["tipo_archivo"] or "").lower()
            ruta = f"/archivos/{p['archivo']}"
            if tipo in ("jpg", "jpeg", "png", "gif", "webp", "svg"):
                archivo_html = f'''
                <div style="margin-top:10px">
                  <a href="{ruta}" target="_blank">
                    <img src="{ruta}" alt="Adjunto"
                         style="max-width:100%;max-height:400px;border-radius:10px;border:1px solid var(--borde)">
                  </a>
                </div>'''
            else:
                icono_archivo = "📄"
                if tipo == "pdf":
                    icono_archivo = "📕"
                elif tipo in ("zip",):
                    icono_archivo = "📦"
                elif tipo in ("doc", "docx"):
                    icono_archivo = "📝"
                archivo_html = f'''
                <div style="margin-top:10px">
                  <a href="{ruta}" target="_blank" class="btn sec"
                     style="display:inline-flex;align-items:center;gap:8px">
                    {icono_archivo} Descargar adjunto ({esc(p['archivo'])})
                  </a>
                </div>'''

        # Contenido con saltos de línea
        contenido = esc(p["contenido"] or "").replace("\n", "<br>")

        # Botón eliminar (autor o admin)
        btn_eliminar = ""
        if usuario and (p["autor"] == usuario["nombre"] or usuario["es_admin"]):
            btn_eliminar = f'''
            <form method="post" action="/tablon/eliminar" style="display:inline"
                  onsubmit="return confirm('¿Eliminar esta publicación?')">
              <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
              <input type="hidden" name="id" value="{p['id']}">
              <button class="btn mini sec" style="color:#f87171">🗑️</button>
            </form>'''

        # Badge de admin
        badge = ""
        if p["autor"] == "hacienda" or (usuario and p["autor"] == usuario["nombre"] and usuario["es_admin"]):
            badge = ' <span class="chip" style="border-color:#f59e0b;color:#f59e0b">👑</span>'

        pubs_html += f'''
        <div class="panel" style="margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            {icono}
            <div style="flex:1">
              <b>{esc(p['autor'])}</b>{badge}
              <span class="sub" style="font-size:12px"> · {fecha(p['timestamp'])}</span>
            </div>
            {btn_eliminar}
          </div>
          <h3 style="font-size:18px;margin:8px 0;color:var(--oro2)">{esc(p['titulo'])}</h3>
          {f'<div style="color:var(--sub);font-size:14px;line-height:1.6">{contenido}</div>' if contenido else ''}
          {archivo_html}
        </div>'''

    if not pubs_html:
        pubs_html = '''
        <div class="panel" style="text-align:center;padding:40px">
          <div style="font-size:48px">📋</div>
          <h3 style="justify-content:center">Tablón vacío</h3>
          <p class="sub">Sé el primero en publicar algo</p>
        </div>'''

    contenido = f"""
    <div class="panel" style="border-color:#f59e0b">
      <h2>📋 Tablón de anuncios</h2>
      <p class="sub">Comparte fotos, documentos, ideas o lo que quieras con la comunidad.
      Todo el mundo puede publicar y ver las publicaciones.</p>
      {msg}
    </div>
    {form_html}
    <h2 style="margin:16px 0 10px">📌 Publicaciones ({len(publicaciones)})</h2>
    {pubs_html}"""
    return plantilla("Tablón", contenido, "tablon", usuario, stats)


def pagina_no_encontrado(usuario=None, stats=None):
    contenido = """
    <div class="panel" style="text-align:center;padding:40px">
      <div style="font-size:48px">🪙</div>
      <h2 style="justify-content:center">404 · Esa página no existe</h2>
      <a class="btn" href="/">Volver al panel</a>
    </div>"""
    return plantilla("No encontrado", contenido, "", usuario, stats)


def pagina_error(usuario=None, stats=None):
    contenido = """
    <div class="panel" style="text-align:center;padding:40px">
      <div style="font-size:48px">⚠️</div>
      <h2 style="justify-content:center">Algo salió mal</h2>
      <p class="sub">El equipo de Yuro (es decir, el ordenador del anfitrión) ha registrado el error.
      Tus yuros están a salvo en la base de datos.</p>
      <a class="btn" href="/">Volver al panel</a>
    </div>"""
    return plantilla("Error", contenido, "", usuario, stats)
