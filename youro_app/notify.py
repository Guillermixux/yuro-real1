"""Notificaciones push gratuitas vía ntfy.sh + navegador (SSE)."""
import json
import queue
import threading
import time
import urllib.request
import urllib.error

from . import config


# Colas de notificaciones por usuario (para SSE)
_colas = {}
_lock = threading.Lock()


def tema_de_usuario(nombre):
    """Tema único por usuario para ntfy.sh (solo letras y números)."""
    limpio = "".join(c for c in nombre.lower() if c.isalnum())
    return f"{config.NTFY_PREFIJO}{limpio}"


def _enviar_push_hilo(tema, titulo, mensaje, prioridad, etiqueta):
    """Envía push en un hilo separado (no bloquea)."""
    def _enviar():
        url = f"{config.NTFY_URL}/{tema}"
        datos = json.dumps({
            "title": titulo,
            "message": mensaje,
            "priority": prioridad,
            "tags": [etiqueta],
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=datos,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=config.NTFY_TIMEOUT) as resp:
                pass
        except Exception:
            pass  # las notificaciones nunca deben romper el programa

    # Lanzar en hilo separado (no bloquea la respuesta)
    threading.Thread(target=_enviar, daemon=True).start()


def obtener_cola(nombre):
    """Obtiene (o crea) la cola de notificaciones de un usuario."""
    with _lock:
        if nombre not in _colas:
            _colas[nombre] = queue.Queue(maxsize=50)
        return _colas[nombre]


def notificar_usuario(nombre, titulo, mensaje, prioridad=3, tipo="info"):
    """Envía notificación por SSE (navegador) + ntfy.sh (móvil)."""
    # 1. Enviar por SSE (navegador abierto) - instantáneo
    notif = {
        "titulo": titulo,
        "mensaje": mensaje,
        "prioridad": prioridad,
        "tipo": tipo,
        "timestamp": time.time(),
    }
    try:
        cola = obtener_cola(nombre)
        cola.put_nowait(notif)
    except queue.Full:
        pass

    # 2. Enviar por ntfy.sh en segundo plano (no bloquea)
    tema = tema_de_usuario(nombre)
    etiqueta = {
        "dinero": "💰", "anuncio": "📢", "emergencia": "🚨",
        "congelado": "🧊", "descongelado": "☀️", "multa": "🔨",
        "info": "ℹ️", "exito": "✅"
    }.get(tipo, "🪙")
    _enviar_push_hilo(tema, titulo, mensaje, prioridad, etiqueta)


def notificar_todos(usuarios, titulo, mensaje, prioridad=3, tipo="info"):
    """Envía notificación a una lista de nombres de usuario."""
    for nombre in usuarios:
        notificar_usuario(nombre, titulo, mensaje, prioridad, tipo)


def nombres_todos(db):
    """Obtiene todos los nombres de usuario de la BD."""
    filas = db.consultar("SELECT nombre FROM usuarios")
    return [f["nombre"] for f in filas]


def stream_sse(nombre):
    """Genera eventos SSE para un usuario (se queda esperando)."""
    cola = obtener_cola(nombre)
    try:
        while True:
            try:
                notif = cola.get(timeout=config.SSE_TIMEOUT)
                data = json.dumps(notif, ensure_ascii=False)
                yield f"data: {data}\n\n"
            except queue.Empty:
                # Enviar keep-alive para mantener la conexión
                yield ": keepalive\n\n"
    except GeneratorExit:
        pass
