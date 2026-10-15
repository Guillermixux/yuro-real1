"""Servidor web de Yuro: rutas, cookies, CSRF y páginas."""
import json
import logging
import os
import secrets
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse, unquote

from . import config, pwa, views
from . import notify
from .mundo import Mundo

MAX_CUERPO = 64 * 1024  # 64 KB: suficiente para cualquier formulario

log = logging.getLogger("yuro")


def fecha_corta(ts):
    """Fecha corta para gráficas: HH:MM"""
    t = time.localtime(ts)
    return f"{t.tm_hour:02d}:{t.tm_min:02d}"


def crear_handler(mundo: Mundo):
    """Crea la clase Handler ligada a una instancia de Mundo (para tests)."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "Yuro/" + config.VERSION

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
            return mundo.usuario_de_token(self._cookie("yuro_token"))

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

        def _json(self, datos, codigo=200):
            """Responde con JSON (convierte sqlite3.Row a dict)."""
            class Encoder(json.JSONEncoder):
                def default(self, o):
                    if hasattr(o, "keys"):
                        return {k: o[k] for k in o.keys()}
                    return super().default(o)
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            cuerpo = json.dumps(datos, ensure_ascii=False, cls=Encoder).encode("utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _redirigir(self, destino, limpiar_cookie=False):
            self.send_response(302)
            self.send_header("Location", destino)
            if limpiar_cookie:
                self.send_header(
                    "Set-Cookie",
                    "yuro_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax",
                )
            self.end_headers()

        def _establecer_sesion(self, token):
            max_edad = config.DURACION_SESION_DIAS * 86400
            self.send_header(
                "Set-Cookie",
                f"yuro_token={token}; Path=/; Max-Age={max_edad}; HttpOnly; SameSite=Lax",
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
            content_type = self.headers.get("Content-Type", "")
            largo = int(self.headers.get("Content-Length") or 0)

            # Multipart (con archivos)
            if "multipart/form-data" in content_type:
                if largo > 10 * 1024 * 1024:  # 10 MB máximo
                    raise ValueError("Archivo demasiado grande.")
                cuerpo = self.rfile.read(largo)
                return self._parse_multipart(cuerpo, content_type)

            # Formulario normal
            if largo > MAX_CUERPO:
                raise ValueError("Formulario demasiado grande.")
            cuerpo = self.rfile.read(largo).decode("utf-8", errors="replace") if largo else ""
            return {k: v[0] for k, v in parse_qs(cuerpo, keep_blank_values=True).items()}

        def _parse_multipart(self, cuerpo, content_type):
            """Parsea multipart/form-data manualmente."""
            import os
            import re as re_mod

            # Obtener boundary
            match = re_mod.search(r'boundary=([^;]+)', content_type)
            if not match:
                return {}
            boundary = match.group(1).strip('"')
            boundary_bytes = boundary.encode()

            campos = {}
            archivos = {}

            # Separar por boundary
            partes = cuerpo.split(b"--" + boundary_bytes)
            for parte in partes:
                parte = parte.strip(b"\r\n")
                if not parte or parte == b"--":
                    continue

                # Separar headers del contenido
                if b"\r\n\r\n" not in parte:
                    continue
                headers_raw, contenido = parte.split(b"\r\n\r\n", 1)
                headers_str = headers_raw.decode("utf-8", errors="replace")

                # Obtener nombre del campo
                name_match = re_mod.search(r'name="([^"]+)"', headers_str)
                if not name_match:
                    continue
                nombre_campo = name_match.group(1)

                # ¿Es archivo?
                filename_match = re_mod.search(r'filename="([^"]*)"', headers_str)
                if filename_match:
                    nombre_archivo = filename_match.group(1)
                    if nombre_archivo:  # solo si hay archivo seleccionado
                        # Obtener Content-Type del archivo
                        ct_match = re_mod.search(r'Content-Type:\s*([^\r\n]+)', headers_str)
                        tipo_archivo = ct_match.group(1).strip() if ct_match else ""
                        archivos[nombre_campo] = (nombre_archivo, contenido, tipo_archivo)
                else:
                    # Campo de texto
                    try:
                        campos[nombre_campo] = contenido.decode("utf-8")
                    except Exception:
                        campos[nombre_campo] = ""

            # Guardar archivos en disco
            import secrets as secrets_mod
            for campo, (nombre_original, datos, tipo) in archivos.items():
                # Validar extensión
                ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else ""
                if ext not in config.TABLON_TIPOS_OK:
                    raise ValueError(f"Tipo de archivo no permitido: .{ext}")
                # Validar tamaño
                if len(datos) > config.TABLON_ARCHIVO_MAX:
                    raise ValueError("El archivo supera los 5MB.")

                # Nombre único
                nombre_unico = f"{secrets_mod.token_hex(8)}.{ext}"
                os.makedirs(config.CARPETA_ARCHIVOS, exist_ok=True)
                ruta_guardar = os.path.join(config.CARPETA_ARCHIVOS, nombre_unico)
                with open(ruta_guardar, "wb") as f:
                    f.write(datos)

                # Devolver nombre del archivo guardado
                campos[campo] = nombre_unico
                campos[f"{campo}_tipo"] = ext
                campos[f"{campo}_original"] = nombre_original

            return campos

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

            # Rutas públicas (solo login/registro sin sesión)
            rutas_publicas = {"/login", "/registro", "/manifest.json", "/sw.js", "/icono.png"}
            if not usuario and ruta not in rutas_publicas:
                return self._redirigir("/login")

            if ruta == "/":
                if not usuario:
                    return self._redirigir("/login")
                dir_u = usuario["direccion"]
                movs = mundo.cadena.transacciones_de(dir_u, limite=10)
                movs = self._enriquecer_movs(movs, dir_u)
                anuncios = mundo.anuncios_activos()

                # Preparar datos para gráficas
                saldo_actual = mundo.cadena.saldo(dir_u)
                datos_grafica = self._datos_grafica_saldo(dir_u, movs, saldo_actual)
                actividad = self._datos_actividad()

                return self._responder(
                    views.pagina_panel(
                        usuario, saldo_actual, movs, self._stats(),
                        anuncios=anuncios,
                        datos_grafica=datos_grafica,
                        actividad=actividad
                    )
                )

            if ruta == "/login":
                if usuario:
                    return self._redirigir("/")
                return self._responder(views.pagina_login(consulta.get("error"),
                                                         ok=consulta.get("ok")))

            if ruta == "/registro":
                if usuario:
                    return self._redirigir("/")
                return self._responder(views.pagina_registro(consulta.get("error")))

            if ruta == "/salir":
                token = self._cookie("yuro_token")
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
                        destino_previo=consulta.get("destino", ""),
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
                stats = self._stats()
                gobierno = mundo.estadisticas_gobierno()
                usuarios = mundo.todos_los_usuarios()
                anuncios = mundo.anuncios_activos()
                log = mundo.log_gobierno()
                return self._responder(
                    views.pagina_admin(usuario, gobierno, usuarios, anuncios, log, stats,
                                       consulta.get("ok"), consulta.get("error"))
                )

            if ruta == "/cuenta":
                if not usuario:
                    return self._redirigir("/login")
                return self._responder(
                    views.pagina_cuenta(usuario, self._stats(),
                                        consulta.get("ok"), consulta.get("error"))
                )

            if ruta == "/tablon":
                publicaciones = mundo.publicaciones_tablon()
                return self._responder(
                    views.pagina_tablon(usuario, publicaciones, self._stats(),
                                        consulta.get("ok"), consulta.get("error"))
                )

            if ruta.startswith("/archivos/"):
                # Servir archivos del tablón
                nombre_archivo = ruta[10:]  # quitar /archivos/
                # Validar nombre (evitar path traversal)
                if "/" in nombre_archivo or "\\" in nombre_archivo or ".." in nombre_archivo:
                    return self._responder("No encontrado", 404)
                ruta_archivo = os.path.join(config.CARPETA_ARCHIVOS, nombre_archivo)
                if not os.path.exists(ruta_archivo):
                    return self._responder("No encontrado", 404)
                # Determinar Content-Type
                ext = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
                tipos = {
                    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml",
                    "pdf": "application/pdf", "txt": "text/plain",
                    "csv": "text/csv", "zip": "application/zip",
                }
                content_type = tipos.get(ext, "application/octet-stream")
                with open(ruta_archivo, "rb") as f:
                    datos = f.read()
                return self._responder_bytes(datos, content_type)

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

            if ruta == "/api/notificaciones":
                # SSE: stream de notificaciones en tiempo real
                if not usuario:
                    return self._responder("No autorizado", 401)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                try:
                    for evento in notify.stream_sse(usuario["nombre"]):
                        self.wfile.write(evento.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

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
                    ok = (f"¡Enviado Y {views.formatear(cantidad_neta)} a {receptor}! "
                          f"(impuesto Y{impuesto:.2f} al gobierno)")
                else:
                    ok = (f"¡Enviado Y {views.formatear(cantidad_neta)} a {receptor}! "
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
                        f"/admin?ok=Saldo%20ajustado%20en%20Y{cantidad:.2f}"
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

            if ruta == "/admin/congelar":
                try:
                    nombre = datos.get("usuario", "")
                    motivo = datos.get("motivo", "")
                    mundo.congelar_usuario(usuario["nombre"], nombre, motivo)
                    return self._redirigir(f"/admin?ok={nombre}%20congelado")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/descongelar":
                try:
                    nombre = datos.get("usuario", "")
                    mundo.descongelar_usuario(usuario["nombre"], nombre)
                    return self._redirigir(f"/admin?ok={nombre}%20descongelado")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/multa":
                try:
                    cantidad = mundo.multar_usuario(
                        usuario["nombre"],
                        datos.get("usuario", ""),
                        datos.get("cantidad", "0"),
                        datos.get("motivo", ""),
                    )
                    return self._redirigir(
                        f"/admin?ok=Multa%20de%20Y{cantidad:.2f}%20aplicada"
                    )
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/anuncio":
                try:
                    mundo.publicar_anuncio(usuario["nombre"], datos.get("mensaje", ""))
                    return self._redirigir("/admin?ok=Anuncio%20publicado")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/anuncio/quitar":
                try:
                    mundo.quitar_anuncio(usuario["nombre"], datos.get("id", "0"))
                    return self._redirigir("/admin?ok=Anuncio%20quitado")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/emergencia":
                try:
                    activar = datos.get("accion", "") == "activar"
                    mundo.activar_emergencia(usuario["nombre"], activar)
                    estado = "activado" if activar else "desactivado"
                    return self._redirigir(f"/admin?ok=Emergencia%20{estado}")
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/admin/recompensa":
                try:
                    nueva = mundo.ajustar_recompensa(
                        usuario["nombre"], datos.get("cantidad", "0")
                    )
                    return self._redirigir(
                        f"/admin?ok=Recompensa%20ajustada%20a%20Y{nueva:.2f}"
                    )
                except ValueError as e:
                    return self._redirigir(f"/admin?error={quote(str(e))}")

            if ruta == "/cuenta/password":
                try:
                    mundo.identidad.cambiar_password(
                        usuario["nombre"],
                        datos.get("actual", ""),
                        datos.get("nueva", ""),
                    )
                    return self._redirigir(
                        "/login?ok=Contraseña%20cambiada.%20Vuelve%20a%20entrar."
                    )
                except ValueError as e:
                    return self._redirigir(f"/cuenta?error={quote(str(e))}")

            if ruta == "/tablon/publicar":
                if not usuario:
                    return self._redirigir("/login")
                try:
                    archivo = datos.get("archivo", "")
                    tipo_archivo = datos.get("archivo_tipo", "")
                    mundo.publicar_tablon(
                        usuario["nombre"],
                        datos.get("titulo", ""),
                        datos.get("contenido", ""),
                        archivo or None,
                        tipo_archivo or None,
                    )
                    return self._redirigir("/tablon?ok=Publicación%20compartida")
                except ValueError as e:
                    return self._redirigir(f"/tablon?error={quote(str(e))}")

            if ruta == "/tablon/eliminar":
                if not usuario:
                    return self._redirigir("/login")
                try:
                    pid = datos.get("id", "0")
                    mundo.quitar_publicacion_tablon(usuario["nombre"], int(pid))
                    return self._redirigir("/tablon?ok=Publicación%20eliminada")
                except (ValueError, TypeError) as e:
                    return self._redirigir(f"/tablon?error={quote(str(e))}")

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

        def _datos_grafica_saldo(self, dir_u, movs, saldo_actual):
            """Genera datos para gráfica de historial de saldo."""
            if not movs:
                return None
            # Calcular saldo histórico (del más reciente al más antiguo)
            historial = []
            saldo = saldo_actual
            for m in movs:
                if m["para"] == dir_u:
                    etiqueta = fecha_corta(m["timestamp"])
                    historial.append((etiqueta, round(saldo, 2)))
                    saldo -= m["cantidad"]
                elif m["de"] == dir_u:
                    etiqueta = fecha_corta(m["timestamp"])
                    historial.append((etiqueta, round(saldo, 2)))
                    saldo += m["cantidad"]
            # Invertir para que sea del más antiguo al más reciente
            historial.reverse()
            return historial if len(historial) > 1 else None

        def _datos_actividad(self):
            """Genera datos de actividad por hora y día."""
            filas = mundo.db.consultar(
                "SELECT timestamp FROM transacciones ORDER BY timestamp DESC LIMIT 500"
            )
            if not filas:
                return None
            # Contar por día (0=lunes) y hora
            actividad = {}
            for f in filas:
                t = time.localtime(f["timestamp"])
                dia = (t.tm_wday)  # 0=lunes
                hora = t.tm_hour
                clave = (dia, hora)
                actividad[clave] = actividad.get(clave, 0) + 1
            # Convertir a lista
            resultado = []
            for (dia, hora), count in actividad.items():
                resultado.append((hora, dia, count))
            return resultado if resultado else None
            for f in filas:
                f["nombre"] = mapa.get(f["direccion"])

    return Handler


def arrancar(mundo: Mundo, host="127.0.0.1", puerto=None):
    """Devuelve un ThreadingHTTPServer ya configurado (sin serve_forever)."""
    handler = crear_handler(mundo)
    servidor = ThreadingHTTPServer((host, puerto or config.PUERTO), handler)
    servidor.daemon_threads = True
    return servidor
