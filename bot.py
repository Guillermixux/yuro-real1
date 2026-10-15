"""Bot que mantiene despierto el servicio de Render haciendo ping automático."""
import time
import urllib.request
import urllib.error

URL = "https://yuro-py.onrender.com"
INTERVALO = 840  # 14 minutos (Render se duerme a los 15)

def ping():
    try:
        req = urllib.request.Request(URL, method="GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"[{time.strftime('%H:%M:%S')}] OK - Status {r.status}")
    except urllib.error.HTTPError as e:
        print(f"[{time.strftime('%H:%M:%S')}] HTTP {e.code}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")

def main():
    print(f"Bot activo. Ping cada {INTERVALO//60} min a {URL}")
    while True:
        ping()
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()
