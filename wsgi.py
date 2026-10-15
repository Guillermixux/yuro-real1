"""Adaptador WSGI para PythonAnywhere."""
import io, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youro_app.mundo import Mundo
from youro_app.server import crear_handler

_ruta_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youro.db")
_mundo = Mundo(_ruta_db)
_Handler = crear_handler(_mundo)


class _Captura:
    def __init__(self):
        self.codigo = 200
        self.cabeceras = []
        self._cuerpo = bytearray()

    def send_response(self, codigo, *a):
        self.codigo = codigo

    def send_header(self, k, v):
        self.cabeceras.append((k, v))

    def end_headers(self):
        pass

    @property
    def wfile(self):
        return self

    def write(self, datos):
        self._cuerpo.extend(datos)


class _Cabeceras(dict):
    def get(self, k, defecto=None):
        for kk, v in self.items():
            if kk.lower() == k.lower():
                return v
        return defecto


def application(environ, start_response):
    metodo = environ.get("REQUEST_METHOD", "GET")
    ruta = environ.get("PATH_INFO", "/")
    consulta = environ.get("QUERY_STRING", "")
    if consulta:
        ruta += "?" + consulta

    cab = _Cabeceras()
    for k, v in environ.items():
        if k.startswith("HTTP_"):
            cab[k[5:].replace("_", "-").title()] = v
    if "CONTENT_TYPE" in environ:
        cab["Content-Type"] = environ["CONTENT_TYPE"]
    if "CONTENT_LENGTH" in environ:
        cab["Content-Length"] = environ["CONTENT_LENGTH"]

    try:
        largo = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        largo = 0
    cuerpo = environ["wsgi.input"].read(largo) if largo else b""

    h = _Handler.__new__(_Handler)
    h.path = ruta
    h.headers = cab
    h.rfile = io.BytesIO(cuerpo)
    cap = _Captura()
    h.wfile = cap
    h.send_response = cap.send_response
    h.send_header = cap.send_header
    h.end_headers = cap.end_headers

    if metodo == "GET":
        h.do_GET()
    elif metodo == "POST":
        h.do_POST()
    else:
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"Method not allowed"]

    textos = {200: "OK", 302: "Found", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
    estado = f"{cap.codigo} {textos.get(cap.codigo, '')}".strip()
    start_response(estado, cap.cabeceras)
    return [bytes(cap._cuerpo)]
