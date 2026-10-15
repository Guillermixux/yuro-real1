"""Vistas HTML de YOURO: tema oscuro, dorado, responsive y con identicones."""
import hashlib
import time

from . import config

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


def plantilla(titulo, contenido, activo="", usuario=None, stats=None, extra_js=""):
    nav_items = [
        ("panel", "/", "Panel"),
        ("enviar", "/enviar", "Enviar"),
        ("minar", "/minar", "Minar"),
        ("explorador", "/explorador", "Explorador"),
        ("ranking", "/ranking", "Ranking"),
    ]
    links = "".join(
        f'<a href="{href}" class="{"activo" if activo==clave else ""}">{etiqueta}</a>'
        for clave, href, etiqueta in nav_items
    )
    if usuario:
        links += (f'<a href="/u/{esc(usuario["nombre"])}">👤 {esc(usuario["nombre"])}</a>'
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
            f'<span>🎁 recompensa <b id="est-recompensa">{formatear(stats.get("recompensa", 0))}</b> ¥</span>'
            f'<span>🏦 suministro <b>{formatear(stats.get("suministro", 0))}</b> ¥</span>'
            f'<span class="{clase_val}">{texto_val}</span>'
            f"</div>"
        )

    js = COPIAR_JS
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
<meta name="apple-mobile-web-app-title" content="YOURO">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/icono.png">
<link rel="icon" href="/icono.png" type="image/png">
<title>YOURO · {esc(titulo)}</title>
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
    <a class="logo" href="/"><span class="moneda">¥</span>YOURO</a>
    <nav>{links}</nav>
  </header>
  {barra}
  {contenido}
  <p class="footer">YOURO (¥) es una moneda de juegos entre amigos · libro mayor público y transparente · <b>no vale dinero real</b></p>
</div>
<script>{js}</script>
</body>
</html>"""


# ======================================================================
#  Páginas
# ======================================================================

def pagina_login(error=None, usuario=None):
    if usuario:
        return None  # ya dentro
    msg = f'<div class="msg mal">{esc(error)}</div>' if error else ""
    contenido = f"""
    <div class="hero">
      <div class="logo-big">🪙</div>
      <h1>Tu moneda, tus amigos</h1>
      <p class="sub">Blockchain privada para tu grupo: regístrate, mina youros y paga a tus amigos.
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
        <a href="/registro">Regístrate gratis</a> y te regalamos <b class="oro">¥ {formatear(config.BIENVENIDA)}</b>.</p>
    </div>"""
    return plantilla("Entrar", contenido, "login")


def pagina_registro(error=None):
    msg = f'<div class="msg mal">{esc(error)}</div>' if error else ""
    contenido = f"""
    <div class="hero">
      <div class="logo-big">🪙</div>
      <h1>Crea tu cuenta YOURO</h1>
      <p class="sub">Al registrarte recibes <b class="oro">¥ {formatear(config.BIENVENIDA)}</b> de bienvenida.
      Después mina bloques y envíales youros a tus amigos.</p>
    </div>
    <div class="panel" style="max-width:430px;margin:0 auto">
      <h2>Crear cuenta</h2>{msg}
      <form method="post" action="/registro">
        <label>Elige un nombre de usuario (3-16 caracteres: letras, números o _)</label>
        <input type="text" name="nombre" pattern="[A-Za-z0-9_]{{3,16}}" autocomplete="username" required autofocus>
        <label>Contraseña (mínimo {config.MIN_CARACTERES_PASSWORD} caracteres)</label>
        <input type="password" name="password" minlength="{config.MIN_CARACTERES_PASSWORD}" autocomplete="new-password" required>
        <button type="submit">Crear cuenta y cobrar ¥ {formatear(config.BIENVENIDA)}</button>
      </form>
      <p class="sub" style="margin-top:14px">¿Ya tienes cuenta? <a href="/login">Entra aquí</a>.</p>
    </div>"""
    return plantilla("Crear cuenta", contenido, "registro")


def pagina_panel(usuario, saldo, movimientos, stats):
    dir_u = usuario["direccion"]
    filas = ""
    for m in movimientos:
        entrada = m["para"] == dir_u
        contra = m["contra_nombre"] or corta_dir(m["direccion_contra"])
        cantidad = f'{"+¥" if entrada else "−¥"}{formatear(m["cantidad"])}'
        concepto = f' <span class="sub">· {esc(m["concepto"])}</span>' if m.get("concepto") else ""
        bloque = f'#{m["bloque_num"]}' if m.get("bloque_num") is not None else '<span class="oro">pendiente</span>'
        enlace = (f"<a href='/u/{esc(m['contra_nombre'])}'>{esc(contra)}</a>"
                  if m.get("contra_nombre") else esc(contra))
        filas += (
            f"<tr><td>{bloque}</td>"
            f"<td>{icono_tipo(m['tipo'], entrada)} {'recibes' if entrada else 'envías'}</td>"
            f"<td class='{'ok' if entrada else 'mal'}' style='font-weight:700'>{cantidad}</td>"
            f"<td>{enlace}{concepto}</td>"
            f"<td class='sub'>{fecha(m['timestamp'])}</td></tr>"
        )
    if not filas:
        filas = ("<tr><td colspan=5 class='sub'>Sin movimientos todavía. "
                 "¡Regala a tus amigos tu dirección y mina tu primer bloque!</td></tr>")

    contenido = f"""
    <div class="grid">
      <div class="panel">
        <h2>Tu saldo</h2>
        <div class="saldo" id="est-saldo">¥ {formatear(saldo)}</div>
        <p class="sub">youros en tu cartera · visible para todos (libro mayor público)</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <a class="btn" href="/enviar">Enviar youros</a>
          <a class="btn sec" href="/minar">Minar bloque</a>
          <a class="btn sec" href="/u/{esc(usuario['nombre'])}">Mi perfil</a>
        </div>
      </div>
      <div class="panel">
        <h2>Tu dirección (para recibir)</h2>
        <div class="copiador">
          <span class="direccion" id="dir-mia">{esc(dir_u)}</span>
          <button class="btn mini" type="button" onclick="copiar('dir-mia', this)">Copiar</button>
        </div>
        <p class="sub" style="margin-top:10px">Comparte tu nombre o tu dirección con tus amigos para cobrar.</p>
      </div>
    </div>
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
      <h2>Enviar youros</h2>
      <p class="sub">Tu saldo: <b class="av">¥ {formatear(saldo)}</b> · como en un banco, el pago
      queda registrado para siempre en el libro mayor público.</p>
      {msg}
      <form method="post" action="/enviar">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <label>Para (nombre de usuario o dirección youro…)</label>
        <input type="text" name="destino" list="amigos" value="{esc(destino_previo)}"
               placeholder="ej: maria o youro1a3f…" required>
        <datalist id="amigos">{opciones}</datalist>
        <label>Cantidad (¥)</label>
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
          <div class="oro" style="font-size:26px;font-weight:900">¥ {formatear(stats['recompensa'])}</div>
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
      tu saldo: <b class="av">¥ {formatear(saldo)}</b></p>
      <form method="post" action="/minar">
        <input type="hidden" name="csrf" value="{esc(csrf)}">
        <button type="submit">Minar ahora (¥ {formatear(stats['recompensa'])})</button>
      </form>
    </div>"""
    return plantilla("Minar", contenido, "minar", usuario, stats)


def pagina_bloque_minado(usuario, bloque, stats):
    contenido = f"""
    <div class="panel" style="max-width:560px">
      <h2>⛏️ ¡Bloque minado!</h2>
      <div class="msg ok">Has minado el bloque <b>#{bloque['indice']}</b> con
      <b>{bloque['transacciones']}</b> transacciones y ganaste <b>¥ {formatear(bloque['recompensa'])}</b>.</div>
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
            f"<b>¥ {formatear(t['cantidad'])}</b>{concepto}</div>"
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
            f" → {esc(corta_dir(t['para'], 12))} <b>¥ {formatear(t['cantidad'])}</b>"
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
            f"<td class='oro' style='font-weight:800;text-align:right'>¥ {formatear(f['saldo'])}</td>"
            f"<td style='text-align:right'>{accion}</td>"
            f"</tr>"
        )
    if not filas_html:
        filas_html = "<tr><td colspan=5 class='sub'>Todavía no hay youros en circulación.</td></tr>"
    contenido = f"""
    <div class="panel">
      <h2>🏆 Ranking YOURO</h2>
      <p class="sub">Los saldos son públicos: aquí está todo el dinero que tiene cada uno,
      ordenado de mayor a menor. Transparencia total, como un libro mayor de verdad.</p>
      <table>
        <tr><th>#</th><th>Usuario</th><th>Dirección</th><th style="text-align:right">Saldo</th><th></th></tr>
        {filas_html}
      </table>
    </div>"""
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
            f"{'+¥' if entrada else '−¥'}{formatear(m['cantidad'])}</td>"
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
          <p class="sub" style="margin:4px 0">en YOURO desde el {fecha(publico['creado'])}</p>
          <div class="saldo" style="font-size:34px">¥ {formatear(perfil['saldo'])}</div>
        </div>
        <div>
          <button class="btn mini" type="button" onclick="copiar('dir-perfil', this)">Copiar dirección</button>
          {f'<a class="btn sec mini" href="/enviar?para={esc(publico["nombre"])}">Enviar ¥</a>' if usuario and not es_propio else ''}
        </div>
      </div>
      <span class="direccion" id="dir-perfil">{esc(dir_p)}</span>
      <div class="grid" style="margin-top:14px">
        <div class="panel" style="margin:0"><div class="sub">Recibido (lifetime)</div>
          <b class="ok" style="font-size:20px">+ ¥ {formatear(perfil['recibido'])}</b></div>
        <div class="panel" style="margin:0"><div class="sub">Enviado (lifetime)</div>
          <b class="mal" style="font-size:20px">− ¥ {formatear(perfil['enviado'])}</b></div>
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


def pagina_admin(usuario, impuesto, usuarios, stats, gobierno_saldo, ok=None, error=None):
    msg = f'<div class="msg ok">{esc(ok)}</div>' if ok else ""
    if error:
        msg = f'<div class="msg mal">{esc(error)}</div>'

    filas = ""
    for u in usuarios:
        badge = '<span class="chip" style="border-color:#f59e0b;color:#fbbf24">👑 GOBIERNO</span>' if u["es_admin"] else ""
        filas += (
            f"<tr><td><b>{esc(u['nombre'])}</b> {badge}</td>"
            f"<td class='hash'>{esc(corta_dir(u['direccion'], 22))}</td>"
            f"<td class='oro' style='font-weight:700;text-align:right'>¥ {formatear(u['saldo'])}</td>"
            f"<td class='sub'>{fecha(u['creado'])}</td></tr>"
        )

    opciones_usuarios = "".join(
        f'<option value="{esc(u["nombre"])}">{esc(u["nombre"])} (¥{formatear(u["saldo"])})</option>'
        for u in usuarios if not u["es_admin"]
    )

    contenido = f"""
    <div class="panel" style="border-color:#f59e0b">
      <h2>👑 Gobierno YOURO</h2>
      <p class="sub">Eres la autoridad monetaria. Controlas los impuestos, los saldos
      y ves todas las cuentas. El dinero del impuesto se acumula en la cuenta
      <b>GOBIERNO</b>.</p>
      {msg}
      <div class="grid" style="margin:12px 0">
        <div class="panel" style="margin:0">
          <div class="sub">Cuenta GOBIERNO</div>
          <div class="oro" style="font-size:26px;font-weight:900">¥ {formatear(gobierno_saldo)}</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Impuesto actual</div>
          <div style="font-size:26px;font-weight:900">{impuesto:.1f}%</div>
        </div>
        <div class="panel" style="margin:0">
          <div class="sub">Usuarios registrados</div>
          <div style="font-size:26px;font-weight:900">{len(usuarios)}</div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>💰 Ajustar impuesto</h2>
        <p class="sub">Porcentaje que se cobra en cada transacción (0-{config.IMPUESTO_MAX}%).
        Se aplica automáticamente al enviar youros.</p>
        <form method="post" action="/admin/impuesto">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Nuevo impuesto (%)</label>
          <input type="number" name="porcentaje" min="0" max="{config.IMPUESTO_MAX}"
                 step="0.5" value="{impuesto}" required>
          <button type="submit">Aplicar impuesto</button>
        </form>
      </div>

      <div class="panel">
        <h2>🏦 Ajustar saldo de un usuario</h2>
        <p class="sub">Crea o retira youros de cualquier cuenta (positivo = crear,
        negativo = retirar). Es tu poder de gobierno.</p>
        <form method="post" action="/admin/saldo">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Usuario</label>
          <select name="usuario" required>{opciones_usuarios}</select>
          <label>Cantidad (¥) — positivo crea, negativo retira</label>
          <input type="number" name="cantidad" step="0.01" required placeholder="ej: 100 o -50">
          <label>Concepto</label>
          <input type="text" name="concepto" maxlength="80" value="Ajuste del gobierno">
          <button type="submit">Aplicar ajuste</button>
        </form>
      </div>

      <div class="panel" style="border-color:#f87171">
        <h2>🗑️ Eliminar usuario</h2>
        <p class="sub">Borra la cuenta y cierra todas sus sesiones.
        <b>No se puede deshacer.</b> Su saldo se pierde.</p>
        <form method="post" action="/admin/eliminar"
              onsubmit="return confirm('¿Seguro que quieres eliminar este usuario? No se puede deshacer.')">
          <input type="hidden" name="csrf" value="{esc(usuario['csrf'])}">
          <label>Usuario a eliminar</label>
          <select name="usuario" required>{opciones_usuarios}</select>
          <button type="submit" style="background:linear-gradient(145deg,#f87171,#dc2626);color:#fff">Eliminar</button>
        </form>
      </div>
    </div>

    <div class="panel">
      <h2>📋 Todas las cuentas</h2>
      <table>
        <tr><th>Usuario</th><th>Dirección</th><th style="text-align:right">Saldo</th><th>Creado</th></tr>
        {filas}
      </table>
    </div>"""
    return plantilla("Gobierno", contenido, "admin", usuario, stats)


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
      <p class="sub">El equipo de YOURO (es decir, el ordenador del anfitrión) ha registrado el error.
      Tus youros están a salvo en la base de datos.</p>
      <a class="btn" href="/">Volver al panel</a>
    </div>"""
    return plantilla("Error", contenido, "", usuario, stats)
