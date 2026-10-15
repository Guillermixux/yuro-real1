r"""
YOURO (¥) · Moneda blockchain privada para ti y tus amigos
==========================================================
Plataforma de moneda tipo Bitcoin, con:
  · Base de datos real (SQLite) para registro, login y saldos
  · Cartera con dirección única estilo cripto (youro1a3f9c…)
  · Envío de youros con concepto de pago (como un banco de verdad)
  · Minería con prueba de trabajo real y recompensa con halving
  · Ranking público y perfil público de cada usuario
  · Explorador de toda la cadena de bloques
  · Instalable como app en el móvil (PWA)

AVISO:
  Es una moneda de JUGUETE / EDUCATIVA entre amigos.
  No vale dinero real. Diviértete y aprende cómo funciona una blockchain.

Cómo usarla:
  1. Doble clic en iniciar-youro.bat         (solo en tu PC)
  2. Doble clic en iniciar-youro-online.bat  (¡online para tus amigos!)
  3. Regístrate, mina youros y envíaselos a tus amigos

Modos:
  python youro.py            solo en tu PC (localhost)
  python youro.py --red      en tu red de wifi (amigos de casa)
  python youro.py --online   ¡en internet! (túnel gratis con cloudflared)
  python youro.py --servidor en un VPS (escucha en 0.0.0.0, para systemd)

Solo usa la biblioteca estándar de Python (sin pip install).
"""
import sys
import threading
import time
import webbrowser

from youro_app import config, tunnel
from youro_app.mundo import Mundo
from youro_app.server import arrancar


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    online = "--online" in sys.argv
    red = "--red" in sys.argv
    servidor_mode = "--servidor" in sys.argv

    if servidor_mode or red:
        host = "0.0.0.0"
    else:
        host = "127.0.0.1"

    print("=" * 62)
    print("  YOURO (¥) · moneda blockchain de tu grupo de amigos")
    print(f"  Versión {config.VERSION} · base de datos: {config.ARCHIVO_DB}")

    try:
        mundo = Mundo()
    except ValueError as e:
        print("\n  [ERROR CRÍTICO] La cadena de bloques no es válida:")
        print("   ", e)
        print("  Hay copias de seguridad en la carpeta 'backups'.")
        print("  No se arranca para no mezclar datos con una cadena alterada.")
        sys.exit(1)

    url_local = f"http://localhost:{config.PUERTO}"
    print(f"  Local: {url_local}")

    if servidor_mode:
        print("  Modo SERVIDOR: escuchando en 0.0.0.0 (accesible desde internet)")
    elif online:
        print("  Modo ONLINE: preparando túnel de Cloudflare (gratis)…")
    elif red:
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "TU_IP"
        print(f"  Modo RED: tus amigos pueden entrar en http://{ip}:{config.PUERTO}")
        print("  (solo si están en tu misma red de wifi)")
    print("  Para cerrar: Ctrl+C")
    print("=" * 62)

    servidor = arrancar(mundo, host=host, puerto=config.PUERTO)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    tunnel_proc = None
    if online:
        tunnel_proc, url_publica = tunnel.iniciar_tunnel(config.PUERTO)
        if url_publica:
            print("\n" + "=" * 62)
            print("  ¡ONLINE! Tus amigos (y tú, desde el móvil) pueden entrar en:")
            print(f"\n     {url_publica}\n")
            print("  Comparte esa URL. Mientras esta ventana esté abierta,")
            print("  la moneda está online.")
            print("  MÓVIL: ábrela en el teléfono → menú →")
            print("        \"Añadir a pantalla de inicio\" (queda como app).")
            print("=" * 62)
        else:
            print("\n  [AVISO] No se pudo abrir el túnel online.")
            print("  El servidor local sigue funcionando en", url_local)

    if not servidor_mode:
        threading.Timer(0.8, lambda: webbrowser.open(url_local)).start()

    try:
        if online and tunnel_proc:
            while True:
                time.sleep(1)
                if tunnel_proc.poll() is not None:
                    print("\nEl túnel online se ha cerrado.")
                    break
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nAdiós. Tus youros siguen guardados en la base de datos youro.db.")
    finally:
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
            except Exception:
                pass
        servidor.shutdown()


if __name__ == "__main__":
    main()
