"""
Economía de Yuro: Bancos, Bolsa de Valores y Banco Central.
Simula una economía real con bancos, préstamos, acciones y regulación.
"""
import time
import random
import json
from . import config


class Economia:
    """Gestiona la economía simulada: bancos, bolsa y banco central."""

    def __init__(self, db):
        self.db = db
        self._crear_tablas()

    def _crear_tablas(self):
        """Crea las tablas de la economía si no existen."""
        with self.db.transaccion() as conn:
            # Bancos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bancos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    dueno TEXT NOT NULL,
                    saldo REAL DEFAULT 0,
                    interes_deposito REAL DEFAULT 3.0,
                    interes_prestamo REAL DEFAULT 10.0,
                    total_depositos REAL DEFAULT 0,
                    total_prestamos REAL DEFAULT 0,
                    perdidas REAL DEFAULT 0,
                    activo INTEGER DEFAULT 1,
                    creado REAL
                )
            """)
            # Depósitos en bancos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS depositos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    banco_id INTEGER NOT NULL,
                    usuario TEXT NOT NULL,
                    cantidad REAL NOT NULL,
                    interes REAL DEFAULT 0,
                    depositado REAL,
                    ultimo_pago REAL,
                    activo INTEGER DEFAULT 1,
                    FOREIGN KEY (banco_id) REFERENCES bancos(id)
                )
            """)
            # Préstamos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prestamos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    banco_id INTEGER NOT NULL,
                    usuario TEXT NOT NULL,
                    cantidad REAL NOT NULL,
                    interes REAL NOT NULL,
                    pagado REAL DEFAULT 0,
                    deuda REAL NOT NULL,
                    garantia REAL DEFAULT 0,
                    estado TEXT DEFAULT 'activo',
                    solicitado REAL,
                    vence REAL,
                    FOREIGN KEY (banco_id) REFERENCES bancos(id)
                )
            """)
            # Acciones (bolsa)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS acciones(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simbolo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    sector TEXT,
                    precio REAL NOT NULL,
                    precio_anterior REAL DEFAULT 0,
                    precio_min REAL DEFAULT 0,
                    precio_max REAL DEFAULT 0,
                    volumen REAL DEFAULT 0,
                    capitalizacion REAL DEFAULT 0,
                    dividendo REAL DEFAULT 0,
                    activo INTEGER DEFAULT 1,
                    ultimo_update REAL
                )
            """)
            # Cartera de acciones de usuarios
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cartera_acciones(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    accion_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_compra REAL NOT NULL,
                    comprado REAL,
                    FOREIGN KEY (accion_id) REFERENCES acciones(id),
                    UNIQUE(usuario, accion_id)
                )
            """)
            # Historial de operaciones bursátiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operaciones_bolsa(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    accion_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio REAL NOT NULL,
                    comision REAL DEFAULT 0,
                    beneficio REAL DEFAULT 0,
                    timestamp REAL,
                    FOREIGN KEY (accion_id) REFERENCES acciones(id)
                )
            """)
            # Reserva del banco central
            conn.execute("""
                CREATE TABLE IF NOT EXISTS banco_central(
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    reserva_oro REAL DEFAULT 1000000,
                    dinero_circulante REAL DEFAULT 0,
                    tasa_interes REAL DEFAULT 5.0,
                    inflacion REAL DEFAULT 0.0,
                    ultimo_update REAL
                )
            """)
            # Inicializar banco central si no existe
            existe = conn.execute("SELECT id FROM banco_central WHERE id = 1").fetchone()
            if not existe:
                conn.execute(
                    "INSERT INTO banco_central(id, reserva_oro, tasa_interes, ultimo_update) VALUES(1, ?, ?, ?)",
                    (config.RESERVA_ORO, config.TASA_INTERES_BASE, time.time())
                )
            # Inicializar acciones si no existen
            acciones = conn.execute("SELECT COUNT(*) as n FROM acciones").fetchone()
            if acciones["n"] == 0:
                for a in config.BOLSA_ACCIONES_INICIALES:
                    conn.execute(
                        "INSERT INTO acciones(simbolo, nombre, sector, precio, precio_anterior, precio_min, precio_max, capitalizacion, activo, ultimo_update) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                        (a["simbolo"], a["nombre"], a["sector"], a["precio_base"], a["precio_base"], a["precio_base"], a["precio_base"], a["precio_base"] * 1000000, time.time())
                    )

    # ==================== BANCO CENTRAL ====================

    def banco_central(self):
        """Obtiene datos del banco central."""
        return self.db.consultarUno("SELECT * FROM banco_central WHERE id = 1")

    def ajustar_tasa_interes(self, nueva_tasa):
        """El gobierno ajusta la tasa de interés base."""
        nueva_tasa = max(0.0, min(30.0, float(nueva_tasa)))
        self.db.ejecutar(
            "UPDATE banco_central SET tasa_interes = ?, ultimo_update = ? WHERE id = 1",
            (nueva_tasa, time.time())
        )
        return nueva_tasa

    def imprimir_dinero(self, cantidad, concepto="Impresión monetaria"):
        """El gobierno imprime dinero (con límite diario)."""
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        if cantidad > config.CAPACIDAD_IMPRESION:
            raise ValueError(f"Máximo {config.CAPACIDAD_IMPRESION} por impresión.")
        # Verificar límite diario
        hace_24h = time.time() - 86400
        impreso_hoy = self.db.consultarUno(
            "SELECT COALESCE(SUM(cantidad), 0) as total FROM transacciones WHERE de = 'BANCO_CENTRAL' AND timestamp > ?",
            (hace_24h,)
        )
        if impreso_hoy["total"] + cantidad > config.CAPACIDAD_IMPRESION:
            raise ValueError("Límite diario de impresión alcanzado.")
        # Registrar impresión
        self.db.ejecutar(
            "INSERT INTO transacciones(de, para, cantidad, concepto, tipo, timestamp) VALUES('BANCO_CENTRAL', 'GOBIERNO', ?, ?, 'impresion', ?)",
            (cantidad, concepto, time.time())
        )
        # Actualizar circulante
        self.db.ejecutar(
            "UPDATE banco_central SET dinero_circulante = dinero_circulante + ?, ultimo_update = ? WHERE id = 1",
            (cantidad, time.time())
        )
        return cantidad

    # ==================== BANCOS ====================

    def crear_banco(self, nombre_banco, dueno):
        """Crea un banco nuevo."""
        nombre_banco = (nombre_banco or "").strip()
        if len(nombre_banco) < 3 or len(nombre_banco) > 30:
            raise ValueError("Nombre del banco entre 3 y 30 caracteres.")
        existe = self.db.consultarUno("SELECT id FROM bancos WHERE nombre = ?", (nombre_banco,))
        if existe:
            raise ValueError("Ya existe un banco con ese nombre.")
        self.db.ejecutar(
            "INSERT INTO bancos(nombre, dueno, creado) VALUES(?, ?, ?)",
            (nombre_banco, dueno, time.time())
        )
        return self.db.consultarUno("SELECT * FROM bancos WHERE nombre = ?", (nombre_banco,))

    def listar_bancos(self):
        """Lista todos los bancos activos."""
        return self.db.consultar("SELECT * FROM bancos WHERE activo = 1 ORDER BY total_depositos DESC")

    def buscar_banco(self, nombre):
        """Busca banco por nombre o ID."""
        banco = self.db.consultarUno("SELECT * FROM bancos WHERE nombre = ? OR id = ?", (nombre, nombre))
        if not banco:
            raise ValueError("Banco no encontrado.")
        return banco

    def depositar(self, nombre_banco, usuario, cantidad):
        """Deposita yuros en un banco."""
        banco = self.buscar_banco(nombre_banco)
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        if cantidad > config.BANCO_MAXIMO_DEPOSITO:
            raise ValueError(f"Máximo {config.BANCO_MAXIMO_DEPOSITO} por depósito.")
        # Verificar saldo del usuario (esto se haría en mundo.py)
        self.db.ejecutar(
            "INSERT INTO depositos(banco_id, usuario, cantidad, depositado, ultimo_pago) VALUES(?, ?, ?, ?, ?)",
            (banco["id"], usuario, cantidad, time.time(), time.time())
        )
        self.db.ejecutar(
            "UPDATE bancos SET total_depositos = total_depositos + ? WHERE id = ?",
            (cantidad, banco["id"])
        )
        return cantidad

    def retirar(self, nombre_banco, usuario, cantidad):
        """Retira yuros de un banco."""
        banco = self.buscar_banco(nombre_banco)
        cantidad = round(float(cantidad), 2)
        deposito = self.db.consultarUno(
            "SELECT * FROM depositos WHERE banco_id = ? AND usuario = ? AND activo = 1 ORDER BY id DESC",
            (banco["id"], usuario)
        )
        if not deposito:
            raise ValueError("No tienes depósitos en este banco.")
        if deposito["cantidad"] < cantidad:
            raise ValueError("Saldo insuficiente en el banco.")
        self.db.ejecutar(
            "UPDATE depositos SET cantidad = cantidad - ?, activo = CASE WHEN cantidad <= 0 THEN 0 ELSE activo END WHERE id = ?",
            (cantidad, deposito["id"])
        )
        self.db.ejecutar(
            "UPDATE bancos SET total_depositos = total_depositos - ? WHERE id = ?",
            (cantidad, banco["id"])
        )
        return cantidad

    def mis_depositos(self, usuario):
        """Lista los depósitos de un usuario."""
        return self.db.consultar(
            """SELECT d.*, b.nombre as banco_nombre, b.interes_deposito 
               FROM depositos d JOIN bancos b ON d.banco_id = b.id 
               WHERE d.usuario = ? AND d.activo = 1""",
            (usuario,)
        )

    def solicitar_prestamo(self, nombre_banco, usuario, cantidad, garantia):
        """Solicita un préstamo en un banco."""
        banco = self.buscar_banco(nombre_banco)
        cantidad = round(float(cantidad), 2)
        garantia = round(float(garantia), 2)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        if cantidad > config.BANCO_PRESTAMO_MAX:
            raise ValueError(f"Máximo {config.BANCO_PRESTAMO_MAX} por préstamo.")
        # Verificar garantía
        garantia_min = cantidad * (config.BANCO_GARANTIA_PCT / 100.0)
        if garantia < garantia_min:
            raise ValueError(f"Garantía insuficiente. Necesitas al menos Y{garantia_min:.2f}.")
        # Calcular deuda con interés
        interes = banco["interes_prestamo"]
        deuda = round(cantidad * (1 + interes / 100.0), 2)
        vence = time.time() + (365 * 86400)  # 1 año
        self.db.ejecutar(
            "INSERT INTO prestamos(banco_id, usuario, cantidad, interes, deuda, garantia, solicitado, vence) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (banco["id"], usuario, cantidad, interes, deuda, garantia, time.time(), vence)
        )
        self.db.ejecutar(
            "UPDATE bancos SET total_prestamos = total_prestamos + ? WHERE id = ?",
            (cantidad, banco["id"])
        )
        return {"cantidad": cantidad, "interes": interes, "deuda": deuda}

    def pagar_prestamo(self, prestamo_id, usuario, cantidad):
        """Paga parte de un préstamo."""
        prestamo = self.db.consultarUno(
            "SELECT * FROM prestamos WHERE id = ? AND usuario = ? AND estado = 'activo'",
            (prestamo_id, usuario)
        )
        if not prestamo:
            raise ValueError("Préstamo no encontrado.")
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        if cantidad > prestamo["deuda"]:
            cantidad = prestamo["deuda"]
        nueva_deuda = round(prestamo["deuda"] - cantidad, 2)
        estado = "pagado" if nueva_deuda <= 0 else "activo"
        self.db.ejecutar(
            "UPDATE prestamos SET deuda = ?, pagado = pagado + ?, estado = ? WHERE id = ?",
            (nueva_deuda, cantidad, estado, prestamo_id)
        )
        return {"pagado": cantidad, "deuda_restante": nueva_deuda, "estado": estado}

    def mis_prestamos(self, usuario):
        """Lista los préstamos de un usuario."""
        return self.db.consultar(
            """SELECT p.*, b.nombre as banco_nombre 
               FROM prestamos p JOIN bancos b ON p.banco_id = b.id 
               WHERE p.usuario = ? AND p.estado = 'activo'""",
            (usuario,)
        )

    # ==================== BOLSA DE VALORES ====================

    def listar_acciones(self):
        """Lista todas las acciones disponibles."""
        return self.db.consultar("SELECT * FROM acciones WHERE activo = 1 ORDER BY capitalizacion DESC")

    def buscar_accion(self, simbolo):
        """Busca acción por símbolo."""
        accion = self.db.consultarUno("SELECT * FROM acciones WHERE simbolo = ?", (simbolo,))
        if not accion:
            raise ValueError(f"Acción {simbolo} no encontrada.")
        return accion

    def comprar_accion(self, usuario, simbolo, cantidad):
        """Compra acciones."""
        accion = self.buscar_accion(simbolo)
        cantidad = int(cantidad)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        # Actualizar precio antes de comprar
        self._actualizar_precio_accion(accion["id"])
        accion = self.buscar_accion(simbolo)
        # Calcular coste
        coste = round(accion["precio"] * cantidad, 2)
        comision = round(coste * config.BOLSA_COMISION_PCT / 100.0, 2)
        total = round(coste + comision, 2)
        # Actualizar cartera
        existente = self.db.consultarUno(
            "SELECT * FROM cartera_acciones WHERE usuario = ? AND accion_id = ?",
            (usuario, accion["id"])
        )
        if existente:
            nuevo_total = existente["cantidad"] + cantidad
            nuevo_precio = round((existente["precio_compra"] * existente["cantidad"] + accion["precio"] * cantidad) / nuevo_total, 2)
            self.db.ejecutar(
                "UPDATE cartera_acciones SET cantidad = ?, precio_compra = ? WHERE id = ?",
                (nuevo_total, nuevo_precio, existente["id"])
            )
        else:
            self.db.ejecutar(
                "INSERT INTO cartera_acciones(usuario, accion_id, cantidad, precio_compra, comprado) VALUES(?, ?, ?, ?, ?)",
                (usuario, accion["id"], cantidad, accion["precio"], time.time())
            )
        # Registrar operación
        self.db.ejecutar(
            "INSERT INTO operaciones_bolsa(usuario, accion_id, tipo, cantidad, precio, comision, timestamp) VALUES(?, ?, 'compra', ?, ?, ?, ?)",
            (usuario, accion["id"], cantidad, accion["precio"], comision, time.time())
        )
        # Actualizar volumen
        self.db.ejecutar(
            "UPDATE acciones SET volumen = volumen + ?, ultimo_update = ? WHERE id = ?",
            (cantidad, time.time(), accion["id"])
        )
        return {"coste": coste, "comision": comision, "total": total, "precio": accion["precio"]}

    def vender_accion(self, usuario, simbolo, cantidad):
        """Vende acciones."""
        accion = self.buscar_accion(simbolo)
        cantidad = int(cantidad)
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser positiva.")
        cartera = self.db.consultarUno(
            "SELECT * FROM cartera_acciones WHERE usuario = ? AND accion_id = ?",
            (usuario, accion["id"])
        )
        if not cartera or cartera["cantidad"] < cantidad:
            raise ValueError("No tienes suficientes acciones.")
        # Actualizar precio antes de vender
        self._actualizar_precio_accion(accion["id"])
        accion = self.buscar_accion(simbolo)
        # Calcular venta
        venta = round(accion["precio"] * cantidad, 2)
        comision = round(venta * config.BOLSA_COMISION_PCT / 100.0, 2)
        neto = round(venta - comision, 2)
        beneficio = round((accion["precio"] - cartera["precio_compra"]) * cantidad, 2)
        # Actualizar cartera
        nueva_cantidad = cartera["cantidad"] - cantidad
        if nueva_cantidad <= 0:
            self.db.ejecutar("DELETE FROM cartera_acciones WHERE id = ?", (cartera["id"],))
        else:
            self.db.ejecutar("UPDATE cartera_acciones SET cantidad = ? WHERE id = ?", (nueva_cantidad, cartera["id"]))
        # Registrar operación
        self.db.ejecutar(
            "INSERT INTO operaciones_bolsa(usuario, accion_id, tipo, cantidad, precio, comision, beneficio, timestamp) VALUES(?, ?, 'venta', ?, ?, ?, ?, ?)",
            (usuario, accion["id"], cantidad, accion["precio"], comision, beneficio, time.time())
        )
        return {"venta": venta, "comision": comision, "neto": neto, "beneficio": beneficio, "precio": accion["precio"]}

    def mi_cartera(self, usuario):
        """Obtiene la cartera de acciones de un usuario."""
        return self.db.consultar(
            """SELECT c.*, a.simbolo, a.nombre, a.precio, a.sector
               FROM cartera_acciones c JOIN acciones a ON c.accion_id = a.id
               WHERE c.usuario = ? ORDER BY c.cantidad * a.precio DESC""",
            (usuario,)
        )

    def historial_bolsa(self, usuario, limite=50):
        """Historial de operaciones bursátiles."""
        return self.db.consultar(
            """SELECT o.*, a.simbolo, a.nombre
               FROM operaciones_bolsa o JOIN acciones a ON o.accion_id = a.id
               WHERE o.usuario = ? ORDER BY o.timestamp DESC LIMIT ?""",
            (usuario, limite)
        )

    def mercado_bolsa(self):
        """Resumen del mercado bursátil."""
        acciones = self.listar_acciones()
        total_cap = sum(a["capitalizacion"] for a in acciones)
        total_vol = sum(a["volumen"] for a in acciones)
        return {
            "acciones": acciones,
            "capitalizacion_total": total_cap,
            "volumen_total": total_vol,
            "numero_empresas": len(acciones),
            "abierto": self._mercado_abierto()
        }

    def _mercado_abierto(self):
        """Verifica si el mercado está abierto."""
        hora = time.gmtime().tm_hour
        return config.BOLSA_HORA_APERTURA <= hora < config.BOLSA_HORA_CIERRE

    def _actualizar_precio_accion(self, accion_id):
        """Actualiza el precio de una acción con volatilidad."""
        accion = self.db.consultarUno("SELECT * FROM acciones WHERE id = ?", (accion_id,))
        if not accion:
            return
        # Solo actualizar cada 5 minutos
        if accion["ultimo_update"] and time.time() - accion["ultimo_update"] < 300:
            return
        # Calcular nuevo precio con volatilidad
        variacion = random.uniform(-config.BOLSA_VOLATILIDAD, config.BOLSA_VOLATILIDAD)
        nuevo_precio = max(1.0, round(accion["precio"] * (1 + variacion), 2))
        # Actualizar
        precio_min = min(accion["precio_min"], nuevo_precio) if accion["precio_min"] > 0 else nuevo_precio
        precio_max = max(accion["precio_max"], nuevo_precio)
        self.db.ejecutar(
            "UPDATE acciones SET precio_anterior = precio, precio = ?, precio_min = ?, precio_max = ?, ultimo_update = ? WHERE id = ?",
            (accion["precio"], nuevo_precio, precio_min, precio_max, time.time(), accion_id)
        )

    def actualizar_todos_precios(self):
        """Actualiza todos los precios de acciones."""
        acciones = self.listar_acciones()
        for a in acciones:
            self._actualizar_precio_accion(a["id"])

    def estadisticas_economia(self):
        """Estadísticas generales de la economía."""
        bancos = self.db.consultarUno("SELECT COUNT(*) as n, COALESCE(SUM(total_depositos), 0) as depositos, COALESCE(SUM(total_prestamos), 0) as prestamos FROM bancos WHERE activo = 1")
        prestamos = self.db.consultarUno("SELECT COUNT(*) as n, COALESCE(SUM(deuda), 0) as deuda FROM prestamos WHERE estado = 'activo'")
        bolsa = self.db.consultarUno("SELECT COUNT(*) as n, COALESCE(SUM(capitalizacion), 0) as capital FROM acciones WHERE activo = 1")
        bc = self.banco_central()
        return {
            "bancos_activos": bancos["n"],
            "depositos_totales": bancos["depositos"],
            "prestamos_totales": bancos["prestamos"],
            "deuda_pendiente": prestamos["deuda"],
            "prestamos_activos": prestamos["n"],
            "empresas_bolsa": bolsa["n"],
            "capitalizacion_bolsa": bolsa["capital"],
            "tasa_interes": bc["tasa_interes"] if bc else 0,
            "reserva_oro": bc["reserva_oro"] if bc else 0,
            "dinero_circulante": bc["dinero_circulante"] if bc else 0,
        }
