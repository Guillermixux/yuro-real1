"""Túnel online gratis con cloudflared (Cloudflare) para Yuro."""
import os
import re
import shutil
import subprocess
import threading
import time

URL_CLOUDFLARED = ("https://github.com/cloudflare/cloudflared/releases/"
                   "latest/download/cloudflared-windows-amd64.exe")
RUTA_CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CLOUDFLARED = os.path.join(RUTA_CARPETA, "cloudflared.exe")


def encontrar_cloudflared():
    exe = shutil.which("cloudflared")
    if exe:
        return exe
    if os.path.exists(RUTA_CLOUDFLARED):
        return RUTA_CLOUDFLARED
    return None


def descargar_cloudflared():
    print("  Descargando cloudflared.exe (~50 MB, solo la primera vez)…")
    try:
        import urllib.request
        urllib.request.urlretrieve(URL_CLOUDFLARED, RUTA_CLOUDFLARED)
        print("  [OK] cloudflared.exe descargado en la carpeta yuro.")
        return RUTA_CLOUDFLARED
    except Exception as e:
        print("  [ERROR] No se pudo descargar:", e)
        return None


def iniciar_tunnel(puerto_local, pedir_permiso=True):
    """Arranca cloudflared y devuelve (proceso, url_publica)."""
    exe = encontrar_cloudflared()
    if not exe:
        print("\n  No se encontró cloudflared (necesario para el modo online).")
        if pedir_permiso:
            try:
                respuesta = input("  ¿Descargarlo ahora? [s/n]: ").strip().lower()
            except EOFError:
                respuesta = "n"
            if respuesta != "s":
                print("  Cancelado. Para jugar online, instálalo y vuelve a ejecutar.")
                return None, None
        else:
            return None, None
        exe = descargar_cloudflared()
        if not exe:
            return None, None

    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"http://localhost:{puerto_local}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    resultado = {"url": None}

    def leer_salida():
        for linea in proc.stdout:
            print("   tunnel|", linea.rstrip())
            if resultado["url"] is None:
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linea)
                if m:
                    resultado["url"] = m.group(0)

    threading.Thread(target=leer_salida, daemon=True).start()

    limite = time.time() + 45
    while resultado["url"] is None and time.time() < limite:
        if proc.poll() is not None:
            break
        time.sleep(0.3)
    return proc, resultado["url"]
