"""Mundo Yuro: orquesta base de datos, cadena e identidad (casos de uso)."""
import re
import time

from .auth import Identidad
from .chain import Cadena
from .economia import Economia
from .config import BIENVENIDA, MAX_REGISTROS_POR_IP
from .db import BaseDatos
from . import config
from .notify import notificar_usuario, notificar_todos, nombres_todos

ES_DIRECCION = re.compile(r"^yuro[0-9a-f]{40}$")


class Mundo:
    def __init__(self, ruta_db=None):
        self.db = BaseDatos(ruta_db)
        self.cadena = Cadena(self.db)
        self.identidad = Identidad(self.db)
        self.economia = Economia(self.db)
        self.identidad.limpiar_sesiones()
        self.cadena.validar_cadena()

    # ---------------------- cuentas ----------------------
    def registrar(self, nombre, password, ip=None):
        with self.db.lock:
            if self.identidad.contar_por_ip(ip) >= MAX_REGISTROS_POR_IP:
                raise ValueError(
                    "Hay demasiadas cuentas creadas desde esta conexión. "
                    "Prueba más tarde o desde otra red."
                )
            # El PRIMER usuario registrado es el gobierno (admin)
            total = self.db.consultarUno("SELECT COUNT(*) AS n FROM usuarios")["n"]
            es_admin = (total == 0)
            usuario = self.identidad.registrar(nombre, password, ip, es_admin=es_admin)
            self.cadena.dar(usuario["direccion"], BIENVENIDA, tipo="faucet")
            return usuario

    def entrar(self, nombre, password, ip=None):
        return self.identidad.entrar(nombre, password, ip)

    def salir(self, token):
        self.identidad.salir(token)

    def usuario_de_token(self, token):
        return self.identidad.usuario_de_token(token)

    # ---------------------- dinero ----------------------
    def resolver_destino(self, destino):
        """Acepta nombre de usuario o dirección yuro…; devuelve el usuario."""
        destino = (destino or "").strip()
        if not destino:
            raise ValueError("Indica a quién quieres enviar los yuros.")
        if ES_DIRECCION.match(destino):
            usuario = self.identidad.por_direccion(destino)
            if not usuario:
                raise ValueError("Esa dirección no pertenece a ninguna cuenta de Yuro.")
            return usuario
        usuario = self.identidad.buscar(destino)
        if not usuario:
            raise ValueError("No existe ningún usuario con ese nombre.")
        return usuario

    def enviar(self, nombre, destino, cantidad, concepto=None):
        emisor = self.identidad.buscar(nombre)
        if not emisor:
            raise ValueError("Sesión no válida. Vuelve a entrar.")
        # Comprobar si está congelado
        if emisor["congelado"]:
            raise ValueError("Tu cuenta está congelada por el gobierno. No puedes enviar yuros.")
        # Comprobar modo emergencia
        if self.modo_emergencia():
            raise ValueError("Modo emergencia activo: las transacciones están pausadas.")
        receptor = self.resolver_destino(destino)
        if receptor["congelado"]:
            raise ValueError("La cuenta destino está congelada por el gobierno.")
        cantidad = round(float(cantidad), 2)

        # Calcular quema (burn) - se destruye para crear escasez
        quemar = round(cantidad * config.QUEMA_ENVIO_PCT / 100.0, 2)
        if quemar < config.QUEMA_MINIMA:
            quemar = config.QUEMA_MINIMA
        if quemar >= cantidad:
            raise ValueError("La cantidad es demasiado pequeña (la quema se la come).")
        cantidad_neta = round(cantidad - quemar, 2)

        # Calcular impuesto si está activo
        impuesto_pct = self.impuesto_actual()
        if impuesto_pct > 0:
            impuesto = round(cantidad_neta * impuesto_pct / 100.0, 2)
            neto = round(cantidad_neta - impuesto, 2)
            if neto <= 0:
                raise ValueError("El impuesto se come toda la cantidad. Reduce el importe.")
            # El emisor paga: neto al receptor + impuesto al GOBIERNO
            self.cadena.enviar(emisor["direccion"], receptor["direccion"],
                               neto, concepto)
            if impuesto > 0:
                self.cadena.enviar(emisor["direccion"], config.DIRECCION_GOBIERNO,
                                   impuesto, f"Impuesto ({impuesto_pct:.1f}%)")
            # Quema: enviar a dirección quemada (0xQUEMA)
            self.cadena.enviar(emisor["direccion"], "QUEMA",
                               quemar, f"Quema ({config.QUEMA_ENVIO_PCT}%)")
            # Notificar al receptor
            notificar_usuario(
                receptor["nombre"],
                f"💰 +Y{neto:.2f} recibidos",
                f"Has recibido Y{neto:.2f} de {emisor['nombre']}"
                + (f"\nConcepto: {concepto}" if concepto else ""),
                prioridad=4, tipo="dinero"
            )
            return neto, receptor["nombre"], impuesto
        else:
            self.cadena.enviar(emisor["direccion"], receptor["direccion"],
                               cantidad_neta, concepto)
            # Quema
            self.cadena.enviar(emisor["direccion"], "QUEMA",
                               quemar, f"Quema ({config.QUEMA_ENVIO_PCT}%)")
            # Notificar al receptor
            notificar_usuario(
                receptor["nombre"],
                f"💰 +Y{cantidad_neta:.2f} recibidos",
                f"Has recibido Y{cantidad_neta:.2f} de {emisor['nombre']}"
                + (f"\nConcepto: {concepto}" if concepto else ""),
                prioridad=4, tipo="dinero"
            )
            return cantidad_neta, receptor["nombre"], 0.0

    def minar(self, nombre):
        usuario = self.identidad.buscar(nombre)
        if not usuario:
            raise ValueError("Sesión no válida. Vuelve a entrar.")
        return self.cadena.minar(usuario["direccion"])

    def saldo_de(self, nombre):
        usuario = self.identidad.buscar(nombre)
        return self.cadena.saldo(usuario["direccion"]) if usuario else 0.0

    # ---------------------- GOBIERNO / ADMIN ----------------------
    def es_admin(self, nombre):
        usuario = self.identidad.buscar(nombre)
        return bool(usuario and usuario["es_admin"])

    def impuesto_actual(self):
        """Porcentaje de impuesto vigente (0-50)."""
        valor = self.db.get_config("impuesto", str(config.IMPUESTO_DEFECTO))
        try:
            return max(0.0, min(config.IMPUESTO_MAX, float(valor)))
        except ValueError:
            return config.IMPUESTO_DEFECTO

    def ajustar_impuesto(self, nombre, porcentaje):
        """Solo el gobierno puede cambiar el % de impuesto."""
        if not self.es_admin(nombre):
            raise ValueError("Solo el gobierno puede cambiar los impuestos.")
        porcentaje = float(porcentaje)
        if porcentaje < 0 or porcentaje > config.IMPUESTO_MAX:
            raise ValueError(f"El impuesto debe estar entre 0 y {config.IMPUESTO_MAX}%.")
        self.db.set_config("impuesto", str(porcentaje))
        return porcentaje

    def todos_los_usuarios(self):
        """Lista completa de cuentas con saldo (solo admin)."""
        filas = self.db.consultar(
            "SELECT nombre, direccion, es_admin, congelado, creado FROM usuarios ORDER BY nombre_lower"
        )
        resultado = []
        for f in filas:
            resultado.append({
                "nombre": f["nombre"],
                "direccion": f["direccion"],
                "es_admin": bool(f["es_admin"]),
                "congelado": bool(f["congelado"]),
                "creado": f["creado"],
                "saldo": self.cadena.saldo(f["direccion"]),
            })
        return resultado

    def ajustar_saldo(self, nombre_admin, nombre_objetivo, cantidad, concepto="Ajuste del gobierno"):
        """El gobierno puede crear o retirar yuros de cualquier cuenta."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede ajustar saldos.")
        objetivo = self.identidad.buscar(nombre_objetivo)
        if not objetivo:
            raise ValueError("Ese usuario no existe.")
        cantidad = round(float(cantidad), 2)
        if cantidad == 0:
            raise ValueError("La cantidad no puede ser 0.")
        if cantidad > 0:
            self.cadena.dar(objetivo["direccion"], cantidad, tipo="faucet", de="GOBIERNO")
        else:
            saldo = self.cadena.saldo(objetivo["direccion"])
            if saldo < abs(cantidad):
                raise ValueError(f"Esa cuenta solo tiene Y{saldo:.2f}.")
            self.cadena.enviar(objetivo["direccion"], config.DIRECCION_GOBIERNO,
                               abs(cantidad), concepto)
        return cantidad

    def eliminar_usuario(self, nombre_admin, nombre_objetivo):
        """El gobierno puede eliminar una cuenta de usuario."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede eliminar usuarios.")
        if nombre_admin == nombre_objetivo:
            raise ValueError("No puedes eliminarte a ti mismo.")
        objetivo = self.identidad.buscar(nombre_objetivo)
        if not objetivo:
            raise ValueError("Ese usuario no existe.")
        if objetivo["es_admin"]:
            raise ValueError("No puedes eliminar a otro admin.")
        # Eliminar sesiones y usuario
        self.db.ejecutar("DELETE FROM sesiones WHERE nombre=?", (nombre_objetivo,))
        self.db.ejecutar("DELETE FROM usuarios WHERE nombre=?", (nombre_objetivo,))
        self._log_gobierno(nombre_admin, "eliminar", f"Usuario {nombre_objetivo}")
        return nombre_objetivo

    # ---------------------- Nuevas capacidades de gobierno ----------------------
    def _log_gobierno(self, admin, accion, detalle=""):
        """Registra una acción del gobierno."""
        self.db.ejecutar(
            "INSERT INTO log_gobierno(admin, accion, detalle, timestamp) VALUES(?, ?, ?, ?)",
            (admin, accion, detalle, time.time()),
        )
        # Mantener solo los últimos N registros
        self.db.ejecutar(
            "DELETE FROM log_gobierno WHERE id NOT IN "
            "(SELECT id FROM log_gobierno ORDER BY id DESC LIMIT ?)",
            (config.LOG_ACCIONES_MAX,),
        )

    def log_gobierno(self, limite=50):
        """Últimas acciones del gobierno."""
        filas = self.db.consultar(
            "SELECT * FROM log_gobierno ORDER BY id DESC LIMIT ?", (limite,)
        )
        return [dict(f) for f in filas]

    def congelar_usuario(self, nombre_admin, nombre_objetivo, motivo=""):
        """El gobierno congela una cuenta (no puede enviar ni recibir)."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede congelar cuentas.")
        objetivo = self.identidad.buscar(nombre_objetivo)
        if not objetivo:
            raise ValueError("Ese usuario no existe.")
        if objetivo["es_admin"]:
            raise ValueError("No puedes congelar a otro admin.")
        self.db.ejecutar(
            "UPDATE usuarios SET congelado=1 WHERE nombre=?", (nombre_objetivo,)
        )
        self._log_gobierno(nombre_admin, "congelar",
                          f"{nombre_objetivo}" + (f" — {motivo}" if motivo else ""))
        # Notificar al usuario congelado
        notificar_usuario(
            nombre_objetivo,
            "🧊 Tu cuenta ha sido congelada",
            f"El gobierno ha congelado tu cuenta."
            + (f"\nMotivo: {motivo}" if motivo else ""),
            prioridad=5, tipo="congelado"
        )
        return nombre_objetivo

    def descongelar_usuario(self, nombre_admin, nombre_objetivo):
        """El gobierno descongela una cuenta."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede descongelar cuentas.")
        objetivo = self.identidad.buscar(nombre_objetivo)
        if not objetivo:
            raise ValueError("Ese usuario no existe.")
        self.db.ejecutar(
            "UPDATE usuarios SET congelado=0 WHERE nombre=?", (nombre_objetivo,)
        )
        self._log_gobierno(nombre_admin, "descongelar", nombre_objetivo)
        # Notificar al usuario
        notificar_usuario(
            nombre_objetivo,
            "☀️ Tu cuenta ha sido descongelada",
            "Ya puedes volver a usar tu cuenta Yuro normalmente.",
            prioridad=4, tipo="descongelado"
        )
        return nombre_objetivo

    def multar_usuario(self, nombre_admin, nombre_objetivo, cantidad, motivo=""):
        """El gobierno impone una multa: quita yuros y lo registra."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede multar.")
        objetivo = self.identidad.buscar(nombre_objetivo)
        if not objetivo:
            raise ValueError("Ese usuario no existe.")
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("La multa debe ser positiva.")
        saldo = self.cadena.saldo(objetivo["direccion"])
        if saldo < cantidad:
            raise ValueError(f"Esa cuenta solo tiene Y{saldo:.2f}. La multa es mayor.")
        # Quitar los yuros (van al GOBIERNO)
        self.cadena.enviar(objetivo["direccion"], config.DIRECCION_GOBIERNO,
                           cantidad, f"MULTA: {motivo or 'sin motivo'}")
        self._log_gobierno(nombre_admin, "multa",
                          f"{nombre_objetivo} Y{cantidad:.2f}" + (f" — {motivo}" if motivo else ""))
        # Notificar al multado
        notificar_usuario(
            nombre_objetivo,
            f"🔨 Multa de Y{cantidad:.2f}",
            f"El gobierno te ha impuesto una multa de Y{cantidad:.2f}."
            + (f"\nMotivo: {motivo}" if motivo else ""),
            prioridad=5, tipo="multa"
        )
        return cantidad

    def publicar_anuncio(self, nombre_admin, mensaje):
        """El gobierno publica un anuncio para toda la comunidad."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede publicar anuncios.")
        mensaje = mensaje.strip()
        if not mensaje:
            raise ValueError("El anuncio no puede estar vacío.")
        if len(mensaje) > config.ANUNCIO_MAX:
            raise ValueError(f"El anuncio no puede superar {config.ANUNCIO_MAX} caracteres.")
        self.db.ejecutar(
            "INSERT INTO anuncios(autor, mensaje, timestamp, activo) VALUES(?, ?, ?, 1)",
            (nombre_admin, mensaje, time.time()),
        )
        self._log_gobierno(nombre_admin, "anuncio", mensaje[:80])
        # Notificar a todos los usuarios
        todos = nombres_todos(self.db)
        notificar_todos(
            todos,
            f"📢 Anuncio del gobierno",
            mensaje,
            prioridad=4, tipo="anuncio"
        )
        return True

    def anuncios_activos(self, limite=5):
        """Últimos anuncios activos del gobierno."""
        filas = self.db.consultar(
            "SELECT * FROM anuncios WHERE activo=1 ORDER BY id DESC LIMIT ?", (limite,)
        )
        return [dict(f) for f in filas]

    def quitar_anuncio(self, nombre_admin, anuncio_id):
        """El gobierno desactiva un anuncio."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede quitar anuncios.")
        self.db.ejecutar("UPDATE anuncios SET activo=0 WHERE id=?", (anuncio_id,))
        self._log_gobierno(nombre_admin, "quitar_anuncio", f"ID {anuncio_id}")
        return True

    def modo_emergencia(self):
        """Comprueba si el modo emergencia está activo."""
        return self.db.get_config("emergencia", "0") == "1"

    def activar_emergencia(self, nombre_admin, activar=True):
        """El gobierno activa/desactiva el modo emergencia (pausa transacciones)."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede activar el modo emergencia.")
        self.db.set_config("emergencia", "1" if activar else "0")
        estado = "ACTIVADO" if activar else "DESACTIVADO"
        self._log_gobierno(nombre_admin, "emergencia", estado)
        # Notificar a todos los usuarios
        todos = nombres_todos(self.db)
        if activar:
            notificar_todos(
                todos,
                "🚨 MODO EMERGENCIA ACTIVADO",
                "El gobierno ha pausado todas las transacciones temporalmente.",
                prioridad=5, tipo="emergencia"
            )
        else:
            notificar_todos(
                todos,
                "✅ Emergencia desactivada",
                "El gobierno ha reactivado las transacciones. Ya todo funciona normal.",
                prioridad=4, tipo="exito"
            )
        return activar

    def recompensa_actual(self):
        """Recompensa de minería actual (permite ajuste del gobierno)."""
        valor = self.db.get_config("recompensa_mineria", "")
        if valor:
            try:
                return float(valor)
            except ValueError:
                pass
        return config.RECOMPENSA

    def ajustar_recompensa(self, nombre_admin, nueva):
        """El gobierno ajusta la recompensa de minería."""
        if not self.es_admin(nombre_admin):
            raise ValueError("Solo el gobierno puede ajustar la recompensa.")
        nueva = round(float(nueva), 2)
        if nueva < config.RECOMPENSA_MIN or nueva > config.RECOMPENSA_MAX:
            raise ValueError(
                f"La recompensa debe estar entre {config.RECOMPENSA_MIN} "
                f"y {config.RECOMPENSA_MAX}."
            )
        self.db.set_config("recompensa_mineria", nueva)
        self._log_gobierno(nombre_admin, "recompensa", f"Y{nueva:.2f}")
        return nueva

    def estadisticas_gobierno(self):
        """Resumen para el panel de gobierno."""
        total_usuarios = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM usuarios"
        )["n"]
        congelados = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM usuarios WHERE congelado=1"
        )["n"]
        anuncios = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM anuncios WHERE activo=1"
        )["n"]
        saldo_gobierno = self.cadena.saldo(config.DIRECCION_GOBIERNO)
        return {
            "total_usuarios": total_usuarios,
            "congelados": congelados,
            "anuncios_activos": anuncios,
            "saldo_gobierno": saldo_gobierno,
            "emergencia": self.modo_emergencia(),
            "impuesto": self.impuesto_actual(),
            "recompensa": self.recompensa_actual(),
        }

    # ---------------------- Tablón de anuncios ----------------------
    def publicar_tablon(self, nombre, titulo, contenido="", archivo=None, tipo_archivo=None):
        """Publica un mensaje en el tablón (con archivo opcional)."""
        usuario = self.identidad.buscar(nombre)
        if not usuario:
            raise ValueError("Debes iniciar sesión para publicar.")
        if usuario["congelado"]:
            raise ValueError("Tu cuenta está congelada. No puedes publicar.")
        titulo = (titulo or "").strip()
        if not titulo:
            raise ValueError("El título no puede estar vacío.")
        if len(titulo) > 100:
            raise ValueError("El título no puede superar 100 caracteres.")
        contenido = (contenido or "").strip()
        if len(contenido) > config.TABLON_CONTENIDO_MAX:
            raise ValueError(f"El contenido no puede superar {config.TABLON_CONTENIDO_MAX} caracteres.")
        if not titulo and not contenido and not archivo:
            raise ValueError("La publicación no puede estar vacía.")

        self.db.ejecutar(
            "INSERT INTO tablon(autor, titulo, contenido, archivo, tipo_archivo, timestamp, activo) "
            "VALUES(?, ?, ?, ?, ?, ?, 1)",
            (nombre, titulo, contenido, archivo, tipo_archivo, time.time()),
        )
        return True

    def publicaciones_tablon(self, limite=50):
        """Obtiene las publicaciones del tablón."""
        filas = self.db.consultar(
            "SELECT * FROM tablon WHERE activo=1 ORDER BY id DESC LIMIT ?",
            (limite,),
        )
        return [dict(f) for f in filas]

    def quitar_publicacion_tablon(self, nombre, publicacion_id):
        """Elimina una publicación (autor o admin)."""
        usuario = self.identidad.buscar(nombre)
        if not usuario:
            raise ValueError("No autorizado.")
        pub = self.db.consultarUno(
            "SELECT * FROM tablon WHERE id=?", (publicacion_id,)
        )
        if not pub:
            raise ValueError("Publicación no encontrada.")
        # Solo el autor o un admin pueden eliminar
        if pub["autor"] != nombre and not usuario["es_admin"]:
            raise ValueError("Solo puedes eliminar tus propias publicaciones.")
        self.db.ejecutar("UPDATE tablon SET activo=0 WHERE id=?", (publicacion_id,))
        # Eliminar archivo si existe
        if pub["archivo"]:
            import os
            ruta_archivo = os.path.join(config.CARPETA_ARCHIVOS, pub["archivo"])
            try:
                if os.path.exists(ruta_archivo):
                    os.remove(ruta_archivo)
            except Exception:
                pass

    # ==================== ECONOMÍA: BANCOS ====================
    def crear_banco(self, nombre_banco, usuario):
        """Crea un banco (cualquier usuario puede)."""
        if not self.identidad.buscar(usuario):
            raise ValueError("No autorizado.")
        return self.economia.crear_banco(nombre_banco, usuario)

    def listar_bancos(self):
        return self.economia.listar_bancos()

    def depositar_en_banco(self, nombre_banco, usuario, cantidad):
        """Deposita yuros en un banco (primero envía al banco)."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        cantidad = round(float(cantidad), 2)
        saldo = self.cadena.saldo(u["direccion"])
        if saldo < cantidad:
            raise ValueError(f"No tienes suficientes yuros. Saldo: Y{saldo:.2f}")
        # Enviar al banco (dirección del dueño)
        banco = self.economia.buscar_banco(nombre_banco)
        self.cadena.enviar(u["direccion"], banco["dueno"], cantidad, f"Depósito en {banco['nombre']}")
        # Registrar depósito
        return self.economia.depositar(nombre_banco, usuario, cantidad)

    def retirar_del_banco(self, nombre_banco, usuario, cantidad):
        """Retira yuros de un banco."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        banco = self.economia.buscar_banco(nombre_banco)
        cantidad = round(float(cantidad), 2)
        # Verificar que el banco tiene saldo
        dueno = self.identidad.buscar(banco["dueno"])
        if dueno:
            saldo_banco = self.cadena.saldo(dueno["direccion"])
            if saldo_banco < cantidad:
                raise ValueError("El banco no tiene suficiente liquidez.")
            # Enviar del banco al usuario
            self.cadena.enviar(dueno["direccion"], u["direccion"], cantidad, f"Retiro de {banco['nombre']}")
        return self.economia.retirar(nombre_banco, usuario, cantidad)

    def mis_depositos(self, usuario):
        return self.economia.mis_depositos(usuario)

    def solicitar_prestamo(self, nombre_banco, usuario, cantidad, garantia):
        """Solicita préstamo (el banco aprueba automáticamente si hay fondos)."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        banco = self.economia.buscar_banco(nombre_banco)
        resultado = self.economia.solicitar_prestamo(nombre_banco, usuario, cantidad, garantia)
        # El banco envía el préstamo al usuario
        dueno = self.identidad.buscar(banco["dueno"])
        if dueno:
            self.cadena.enviar(dueno["direccion"], u["direccion"], cantidad, f"Préstamo de {banco['nombre']}")
        return resultado

    def pagar_prestamo(self, prestamo_id, usuario, cantidad):
        """Paga un préstamo."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        prestamo = self.db.consultarUno("SELECT * FROM prestamos WHERE id = ? AND usuario = ?", (prestamo_id, usuario))
        if not prestamo:
            raise ValueError("Préstamo no encontrado.")
        banco = self.economia.buscar_banco(str(prestamo["banco_id"]))
        dueno = self.identidad.buscar(banco["dueno"])
        saldo = self.cadena.saldo(u["direccion"])
        if saldo < cantidad:
            raise ValueError(f"No tienes suficientes yuros. Saldo: Y{saldo:.2f}")
        # Enviar al banco
        if dueno:
            self.cadena.enviar(u["direccion"], dueno["direccion"], cantidad, f"Pago préstamo #{prestamo_id}")
        return self.economia.pagar_prestamo(prestamo_id, usuario, cantidad)

    def mis_prestamos(self, usuario):
        return self.economia.mis_prestamos(usuario)

    # ==================== ECONOMÍA: BOLSA ====================
    def comprar_accion(self, usuario, simbolo, cantidad):
        """Compra acciones en la bolsa."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        resultado = self.economia.comprar_accion(usuario, simbolo, cantidad)
        # Enviar dinero a la bolsa
        self.cadena.enviar(u["direccion"], config.DIRECCION_BOLSA, resultado["total"], f"Compra {cantidad}x {simbolo}")
        return resultado

    def vender_accion(self, usuario, simbolo, cantidad):
        """Vende acciones en la bolsa."""
        u = self.identidad.buscar(usuario)
        if not u:
            raise ValueError("No autorizado.")
        resultado = self.economia.vender_accion(usuario, simbolo, cantidad)
        # La bolsa envía dinero al usuario
        self.cadena.enviar(config.DIRECCION_BOLSA, u["direccion"], resultado["neto"], f"Venta {cantidad}x {simbolo}")
        return resultado

    def mi_cartera(self, usuario):
        return self.economia.mi_cartera(usuario)

    def historial_bolsa(self, usuario):
        return self.economia.historial_bolsa(usuario)

    def mercado_bolsa(self):
        return self.economia.mercado_bolsa()

    # ==================== ECONOMÍA: GOBIERNO ====================
    def banco_central(self):
        return self.economia.banco_central()

    def ajustar_tasa_interes(self, usuario, nueva_tasa):
        """Solo el gobierno ajusta la tasa de interés."""
        if not self.es_admin(usuario):
            raise ValueError("Solo el gobierno puede ajustar tasas.")
        return self.economia.ajustar_tasa_interes(nueva_tasa)

    def imprimir_dinero(self, usuario, cantidad, concepto="Impresión monetaria"):
        """Solo el gobierno imprime dinero."""
        if not self.es_admin(usuario):
            raise ValueError("Solo el gobierno puede imprimir dinero.")
        return self.economia.imprimir_dinero(cantidad, concepto)

    def estadisticas_economia(self):
        return self.economia.estadisticas_economia()
        return True
