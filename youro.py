"""Yuro - servidor principal (para Render y local)."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youro_app import config
from youro_app.mundo import Mundo
from youro_app.server import arrancar


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    host = "0.0.0.0"

    print("=" * 60)
    print("  Yuro (Y) - moneda blockchain de tu grupo")
    print(f"  Puerto: {config.PUERTO} | DB: {config.ARCHIVO_DB}")

    try:
        mundo = Mundo()
    except ValueError as e:
        print(f"\n  [ERROR] Cadena invalida: {e}")
        sys.exit(1)

    servidor = arrancar(mundo, host=host, puerto=config.PUERTO)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"  Servidor escuchando en {host}:{config.PUERTO}")
    print("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
