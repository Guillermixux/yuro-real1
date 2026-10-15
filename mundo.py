"""Mundo YOURO: orquesta base de datos, cadena e identidad (casos de uso)."""
import re

from .auth import Identidad
from .chain import Cadena
from .config import BIENVENIDA, MAX_REGISTROS_POR_IP
from .db import BaseDatos
from . import config

ES_DIRECCION = re.compile(r"^youro[0-9a-f]{40}$")


class Mundo:
    def __init__(self, ruta_db=None):
        self.db = BaseDatos(ruta_db)
        self.cadena = Cadena(self.db)
        self.identidad = Identidad(self.db)
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
        """Acepta nombre de usuario o dirección youro…; devuelve el usuario."""
        destino = (destino or "").strip()
        if not destino:
            raise ValueError("Indica a quién quieres enviar los youros.")
        if ES_DIRECCION.match(destino):
            usuario = self.identidad.por_direccion(destino)
            if not usuario:
                raise ValueError("Esa dirección no pertenece a ninguna cuenta de YOURO.")
            return usuario
        usuario = self.identidad.buscar(destino)
        if not usuario:
            raise ValueError("No existe ningún usuario con ese nombre.")
        return usuario

    def enviar(self, nombre, destino, cantidad, concepto=None):
        emisor = self.identidad.buscar(nombre)
        if not emisor:
            raise ValueError("Sesión no válida. Vuelve a entrar.")
        receptor = self.resolver_destino(destino)
        cantidad = round(float(cantidad), 2)

        # Calcular impuesto si está activo
        impuesto_pct = self.impuesto_actual()
        if impuesto_pct > 0:
            impuesto = round(cantidad * impuesto_pct / 100.0, 2)
            neto = round(cantidad - impuesto, 2)
            if neto <= 0:
                raise ValueError("El impuesto se come toda la cantidad. Reduce el importe.")
            # El emisor paga: neto al receptor + impuesto al GOBIERNO
            self.cadena.enviar(emisor["direccion"], receptor["direccion"],
                               neto, concepto)
            if impuesto > 0:
                self.cadena.enviar(emisor["direccion"], config.DIRECCION_GOBIERNO,
                                   impuesto, f"Impuesto ({impuesto_pct:.1f}%)")
            return neto, receptor["nombre"], impuesto
        else:
            self.cadena.enviar(emisor["direccion"], receptor["direccion"],
                               cantidad, concepto)
            return cantidad, receptor["nombre"], 0.0

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
            "SELECT nombre, direccion, es_admin, creado FROM usuarios ORDER BY nombre_lower"
        )
        resultado = []
        for f in filas:
            resultado.append({
                "nombre": f["nombre"],
                "direccion": f["direccion"],
                "es_admin": bool(f["es_admin"]),
                "creado": f["creado"],
                "saldo": self.cadena.saldo(f["direccion"]),
            })
        return resultado

    def ajustar_saldo(self, nombre_admin, nombre_objetivo, cantidad, concepto="Ajuste del gobierno"):
        """El gobierno puede crear o retirar youros de cualquier cuenta."""
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
                raise ValueError(f"Esa cuenta solo tiene ¥{saldo:.2f}.")
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
        return nombre_objetivo
