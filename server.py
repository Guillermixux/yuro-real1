"""Servidor web de YOURO: rutas, cookies, CSRF y páginas."""
import json
import logging
import secrets
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse, unquote

from . import config, pwa, views
from .mundo import Mundo

MAX_CUERPO = 64 * 1024  # 64 KB: suficiente para cualquier formulario

log = logging.getLogger("youro")


def crear_handler(mundo: Mundo):
    """Crea la clase Handler ligada a una instancia de Mundo (para tests)."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "YOURO/" + config.VERSION

        # ---------------- utilidades ----------------
        def log_message(self, *a):
            pass

        def _cookie(self, nombre):
            cab = self.headers.get("Cookie", "") or ""
            for par in cab.split(";"):
                k, _, v = par.strip().partition("=")
                if k == nombre:
                    return v
            return None

        def _usuario(self):
            return mundo.usuario_de_token(self._cookie("youro_token"))

        def _ip(self):
            xf = self.headers.get("X-Forwarded-For", "")
            if xf:
                return xf.split(",")[0].strip()
            return self.client_address[0] if self.client_address else None

        def _responder(self, html, codigo=200):
            datos = html.encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                "manifest-src 'self'; worker-src 'self'",
            )
            self.end_headers()
            self.wfile.write(datos)

        def _responder_bytes(self, datos, contenido_tipo):
            self.send_response(200)
            self.send_header("Content-Type", contenido_tipo)
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(datos)

        def _redirigir(self, destino, limpiar_cookie=False):
            self.send_response(302)
            self.send_header("Location", destino)
            if limpiar_cookie:
                self.send_header(
                    "Set-Cookie",
                    "youro_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax",
                )
            self.end_headers()

        def _establecer_sesion(self, token):
            max_edad = config.DURACION_SESION_DIAS * 86400
            self.send_header(
                "Set-Cookie",
                f"youro_token={token}; Path=/; Max-Age={max_edad}; HttpOnly; SameSite=Lax",
            )

        def _mensaje(self, tipo, texto):
            return f'<div class="msg {tipo}">{views.esc(texto)}</div>'

        def _stats(self):
            try:
                return mundo.cadena.estadisticas()
            except Exception:
                return {}

        def _origen_ok(self):
            """POST solo desde nuestro propio origen (anti CSRF externo)."""
            origen = self.headers.get("Origin")
            if origen:
                return self._mismo_origen(origen)
            referer = self.headers.get("Referer")
            if referer:
                return self._mismo_origen(urlparse(referer).scheme + "://" + urlparse(referer).netloc)
            return True  # sin cabeceras (cliente manual): lo frenan el resto de controles

        def _mismo_origen(self, origen):
            host = self.headers.get("Host", "")
            return urlparse(origen).netloc == host

        def _csrf_ok(self, usuario, datos):
            token = (datos.get("csrf") or "").strip()
            esperado = usuario["csrf"] if usuario else ""
            if not token or not esperado:
                return False
            return secrets.compare_digest(token, esperado)

        def _leer_post(self):
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > MAX_CUERPO:
                raise ValueError("Formulario demasiado grande.")
            cuerpo = self.rfile.read(largo).decode("utf-8", errors="replace") if largo else ""
            return {k: v[0] for k, v in parse_qs(cuerpo, keep_blank_values=True).items()}

        def _nombre(self, usuario):
            return usuario["nombre"] if usuario else None

        # ---------------- GET ----------------
        def do_GET(self):
            try:
                self._get()
            except Exception:
                log.error("Error GET %s\n%s", self.path, traceback.format_exc())
                self._responder(views.pagina_error(self._usuario(), self._stats()), 500)

        def _get(self):
            url = urlparse(self.path)
            ruta = unquote(url.path)
            consulta = {k: v[0] for k, v in parse_qs(url.query).items()}
            usuario = self._usuario()

            if ruta == "/":
                if not usuario:
                    return self._redirigir("/login")
                dir_u = usuario["direccion"]
                movs = mundo.cadena.transacciones_de(dir_u, limite=10)
                movs = self._enriquecer_movs(movs, dir_u)
                return self._responder(
                    views.pagina_panel(
                        usuario, mundo.cadena.saldo(dir_u), movs, self._stats()
                    )
                )

            if ruta == "/login":
                if usuario:
                    return self._redirigir("/")
                return self._responder(views.pagina_login(consulta.get("error")))

            if ruta == "/registro":
                if usuario:
                    return self._redirigir("/")
                return self._responder(views.pagina_registro(consulta.get("error")))

            if ruta == "/salir":
                token = self._cookie("youro_token")
                if token:
                    mundo.salir(token)
                return self._redirigir("/login", limpiar_cookie=True)

            if ruta == "/enviar":
                if not usuario:
                    return self._redirigir("/login")
                dir_u = usuario["direccion"]
                return self._responder(
                    views.pagina_enviar(
                        usuario,
                        mundo.cadena.saldo(dir_u),
                        mundo.identidad.lista_nombres(),
                        mensaje=consulta.get("ok"),
                        destino_previo=consulta.get("para", ""),
                        cantidad_previa=consulta.get("cantidad", ""),
                        concepto_previo=consulta.get("concepto", ""),
                        csrf=usuario["csrf"],
                    )
                )

            if ruta == "/minar":
                if not usuario:
                    return self._redirigir("/login")
                return self._responder(
                    views.pagina_minar(
                        usuario, self._stats(), mundo.saldo_de(usuario["nombre"]),
                        mensaje=consulta.get("ok"), csrf=usuario["csrf"],
                    )
                )

            if ruta == "/explorador":
                desde = consulta.get("desde")
                desde = int(desde) if desde and desde.isdigit() else None
                bloques = mundo.cadena.bloques_recientes(desde=desde)
                self._resolver_mineros(bloques)
                return self._responder(
                    views.pagina_explorador(
                        usuario,
                        bloques,
                        mundo.cadena.pendientes(),
                        self._stats(),
                        mundo.cadena.transacciones_bloque,
                    )
                )

            if ruta == "/ranking":
                filas = mundo.cadena.ranking()
                self._resolver_nombres_ranking(filas)
                return self._responder(views.pagina_ranking(usuario, filas, self._stats()))

            if ruta == "/admin":
                if not usuario or not mundo.es_admin(usuario["nombre"]):
                    return self._responder(views.pagina_no_encontrado(usuario, self._stats()), 404)
                impuesto = mundo.impuesto_actual()
                usuarios = mundo.todos_los_usuarios()
                stats = self._stats()
                gobierno_saldo = mundo.cadena.saldo(config.DIRECCION_GOBIERNO)
                return self._responder(
                    views.pagina_admin(usuario, impuesto, usuarios, stats, gobierno_saldo,
                                       consulta.get("ok"), consulta.get("error"))
                )

            if ruta.startswith("/u/"):
                nombre = ruta[3:].strip()
                publico = mundo.identidad.buscar(nombre)
                if not publico:
                    return self._responder(views.pagina_no_encontrado(usuario, self._stats()), 404)
                dir_p = publico["direccion"]
                movs = mundo.cadena.transacciones_de(dir_p, limite=30)
                movs = self._enriquecer_movs(movs, dir_p)
                return self._responder(
                    views.pagina_perfil(
                        usuario,
                        publico,
                        mundo.cadena.perfil(dir_p),
                        movs,
                        self._stats(),
                        es_propio=bool(usuario and usuario["direccion"] == dir_p),
                    )
                )

            if ruta == "/api/estado":
                stats = self._stats()
                cuerpo = {
                    "bloques": stats.get("bloques", 0),
                    "pendientes": stats.get("pendientes", 0),
                    "dificultad": stats.get("dificultad", 0),
                    "recompensa": stats.get("recompensa", 0),
                    "suministro": stats.get("suministro", 0),
                    "saldo": (
                        round(mundo.cadena.saldo(usuario["direccion"]), 2) if usuario else None
                    ),
                }
                datos = json.dumps(cuerpo).encode("utf-8")
                return self._responder_bytes(datos, "application/json; charset=utf-8")

            if ruta == "/manifest.json":
                return self._responder_bytes(
                    json.dumps(pwa.MANIFEST, ensure_ascii=False).encode("utf-8"),
                    "application/manifest+json; charset=utf-8",
                )
            if ruta == "/sw.js":
                return self._responder_bytes(
                    pwa.SERVICE_WORKER.encode("utf-8"), "text/javascript; charset=utf-8"
                )
            if ruta == "/icono.png":
                return self._responder_bytes(pwa.icono_png(), "image/png")

            self._responder(views.pagina_no_encontrado(usuario, self._stats()), 404)

        # ---------------- POST ----------------
        def do_POST(self):
            try:
                self._post()
            except ValueError as e:
                # Errores de negocio controlados: se reenvían al formulario.
                self._responder(str(e), 400)
            except Exception:
                log.error("Error POST %s\n%s", self.path, traceback.format_exc())
                self._responder(views.pagina_error(self._usuario(), self._stats()), 500)

        def _post(self):
            if not self._origen_ok():
                return self._responder(
                    views.pagina_error(self._usuario(), self._stats()), 403
                )
            url = urlparse(self.path)
            ruta = unquote(url.path)
            datos = self._leer_post()
            usuario = self._usuario()

            if ruta == "/registro":
                try:
                    mundo.registrar(
                        datos.get("nombre", ""), datos.get("password", ""), self._ip()
                    )
                    token, fila = mundo.entrar(datos.get("nombre", ""), datos.get("password", ""), self._ip())
                except ValueError as e:
                    return self._responder(views.pagina_registro(str(e)), 400)
                self.send_response(302)
                self.send_header("Location", "/")
                self._establecer_sesion(token)
                self.end_headers()
                return

            if ruta == "/login":
                try:
                    token, fila = mundo.entrar(
                        datos.get("nombre", ""), datos.get("password", ""), self._ip()
                    )
                except ValueError as e:
                    return self._responder(views.pagina_login(str(e)), 400)
                self.send_response(302)
                self.send_header("Location", "/")
                self._establecer_sesion(token)
                self.end_headers()
                return

            if not usuario:
                return self._redirigir("/login")

            if not self._csrf_ok(usuario, datos):
                return self._responder(
                    views.pagina_error(usuario, self._stats()), 403
                )

            if ruta == "/enviar":
                try:
                    resultado = mundo.enviar(
                        usuario["nombre"],
                        datos.get("destino", ""),
                        datos.get("cantidad", "0"),
                        datos.get("concepto", ""),
                    )
                    if len(resultado) == 3:
                        cantidad_neta, receptor, impuesto = resultado
                    else:
                        cantidad_neta, receptor = resultado
                        impuesto = 0.0
                except ValueError as e:
                    return self._responder(
                        views.pagina_enviar(
                            usuario,
                            mundo.cadena.saldo(usuario["direccion"]),
                            mundo.identidad.lista_nombres(),
                            error=str(e),
                            destino_previo=datos.get("destino", ""),
                            cantidad_previa=datos.get("cantidad", ""),
                            concepto_previo=datos.get("concepto", ""),
                            csrf=usuario["csrf"],
                        ),
                        400,
                    )
                if impuesto > 0:
                    ok = (f"¡Enviado ¥ {views.formatear(cantidad_neta)} a {receptor}! "
                          f"(impuesto ¥{impuesto:.2f} al gobierno)")
                else:
                    ok = (f"¡Enviado ¥ {views.formatear(cantidad_neta)} a {receptor}! "
                          f"Se confirma cuando alguien mine el siguiente bloque.")
                return self._redirigir("/enviar?ok=" + quote(ok))

            if ruta == "/minar":
                try:
                    bloque = mundo.minar(usuario["nombre"])
                except ValueError as e:
                    return self._responder(
                        views.pagina_minar(usuario, self._stats(),
                                           mundo.saldo_de(usuario["nombre"]), error=str(e),
                                           csrf=usuario["csrf"]),
                        400,
                    )
                return self._responder(views.pagina_bloque_minado(usuario, bloque, self._stats()))

            if ruta == "/admin/impuesto":
                try:
                    nuevo = mundo.ajustar_impuesto(usuario["nombre"], datos.get("porcentaje", "0"))
                    return self._redirigir(f"/admin?ok=Impuesto%20ajustado%20a%20{nuevo}%25")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/saldo":
                try:
                    cantidad = mundo.ajustar_saldo(
                        usuario["nombre"],
                        datos.get("usuario", ""),
                        datos.get("cantidad", "0"),
                        datos.get("concepto", "Ajuste del gobierno"),
                    )
                    return self._redirigir(
                        f"/admin?ok=Saldo%20ajustado%20en%20¥{cantidad:.2f}"
                    )
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/eliminar":
                try:
                    eliminado = mundo.eliminar_usuario(
                        usuario["nombre"],
                        datos.get("usuario", ""),
                    )
                    return self._redirigir(
                        f"/admin?ok=Usuario%20{eliminado}%20eliminado"
                    )
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            self._responder(views.pagina_no_encontrado(usuario, self._stats()), 404)

        # ---------------- helpers de datos ----------------
        def _nombres_por_direccion(self, direcciones):
            limpio = [d for d in direcciones if d and d not in ("COINBASE", "FAUCET")]
            if not limpio:
                return {}
            placeholders = ",".join("?" * len(limpio))
            filas = mundo.db.consultar(
                f"SELECT nombre, direccion FROM usuarios WHERE direccion IN ({placeholders})",
                limpio,
            )
            return {f["direccion"]: f["nombre"] for f in filas}

        def _enriquecer_movs(self, movs, dir_propia):
            dirs = set()
            for m in movs:
                dirs.add(m["de"] if m["para"] == dir_propia else m["para"])
            mapa = self._nombres_por_direccion(dirs)
            for m in movs:
                m["direccion_contra"] = m["de"] if m["para"] == dir_propia else m["para"]
                m["contra_nombre"] = mapa.get(m["direccion_contra"])
            return movs

        def _resolver_mineros(self, bloques):
            dirs = {b["minero"] for b in bloques}
            mapa = self._nombres_por_direccion(dirs)
            for b in bloques:
                b["minero_nombre"] = mapa.get(b["minero"])

        def _resolver_nombres_ranking(self, filas):
            mapa = self._nombres_por_direccion({f["direccion"] for f in filas})
            for f in filas:
                f["nombre"] = mapa.get(f["direccion"])

    return Handler


def arrancar(mundo: Mundo, host="127.0.0.1", puerto=None):
    """Devuelve un ThreadingHTTPServer ya configurado (sin serve_forever)."""
    handler = crear_handler(mundo)
    servidor = ThreadingHTTPServer((host, puerto or config.PUERTO), handler)
    servidor.daemon_threads = True
    return servidor
