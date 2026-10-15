"""Capa de base de datos SQLite de Yuro (WAL, transaccional, a prueba de cortes)."""
import os
import shutil
import sqlite3
import threading
import time

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    nombre       TEXT PRIMARY KEY,
    nombre_lower TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    sal          TEXT NOT NULL,
    direccion    TEXT NOT NULL UNIQUE,
    csrf         TEXT NOT NULL,
    ip           TEXT,
    es_admin     INTEGER NOT NULL DEFAULT 0,
    congelado    INTEGER NOT NULL DEFAULT 0,
    creado       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    token  TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    csrf   TEXT NOT NULL,
    creado REAL NOT NULL,
    expira REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS bloques (
    indice       INTEGER PRIMARY KEY,
    hash         TEXT NOT NULL UNIQUE,
    hash_anterior TEXT NOT NULL,
    minero       TEXT NOT NULL,
    nonce        INTEGER NOT NULL,
    timestamp    REAL NOT NULL,
    dificultad   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transacciones (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    bloque    INTEGER REFERENCES bloques(indice),
    de        TEXT NOT NULL,
    para      TEXT NOT NULL,
    cantidad  REAL NOT NULL,
    concepto  TEXT,
    tipo      TEXT NOT NULL,
    timestamp REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_bloque ON transacciones(bloque);
CREATE INDEX IF NOT EXISTS idx_tx_de ON transacciones(de);
CREATE INDEX IF NOT EXISTS idx_tx_para ON transacciones(para);

CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anuncios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    autor     TEXT NOT NULL,
    mensaje   TEXT NOT NULL,
    timestamp REAL NOT NULL,
    activo    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tablon (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    autor     TEXT NOT NULL,
    titulo    TEXT NOT NULL,
    contenido TEXT,
    archivo   TEXT,
    tipo_archivo TEXT,
    timestamp REAL NOT NULL,
    activo    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS log_gobierno (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    admin     TEXT NOT NULL,
    accion    TEXT NOT NULL,
    detalle   TEXT,
    timestamp REAL NOT NULL
);
"""


class BaseDatos:
    """Conexiones SQLite por hilo + esquema + copias de seguridad."""

    def __init__(self, ruta=None):
        self.ruta = ruta or config.ARCHIVO_DB
        self._local = threading.local()
        self._lock = threading.RLock()
        self._conns = []
        self._inicializar()

    @property
    def lock(self):
        """Bloqueo global de escritura (threading.RLock reentrante)."""
        return self._lock

    def _conexion(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.ruta, timeout=10, check_same_thread=False)
            conn.isolation_level = None  # autocommit: transacciones explícitas
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=10000")
            self._local.conn = conn
            with self._lock:
                self._conns.append(conn)
        return conn

    def _inicializar(self):
        os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)
        self.respaldar_si_existe()
        conn = self._conexion()
        conn.executescript(ESQUEMA)
        # Migraciones para bases de datos antiguas
        migraciones = [
            "ALTER TABLE usuarios ADD COLUMN es_admin INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE usuarios ADD COLUMN congelado INTEGER NOT NULL DEFAULT 0",
        ]
        for sql in migraciones:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # ya existe
        conn.commit()

    def respaldar_si_existe(self):
        """Crea una copia de seguridad del .db al arrancar (máx. 5 copias)."""
        if not os.path.exists(self.ruta):
            return
        try:
            os.makedirs(config.CARPETA_BACKUPS, exist_ok=True)
            nombre = f"yuro_{time.strftime('%Y%m%d_%H%M%S')}.db"
            destino = os.path.join(config.CARPETA_BACKUPS, nombre)
            shutil.copy2(self.ruta, destino)
            copias = sorted(os.listdir(config.CARPETA_BACKUPS))
            while len(copias) > 5:
                os.remove(os.path.join(config.CARPETA_BACKUPS, copias.pop(0)))
        except Exception:
            pass  # un fallo de backup nunca debe impedir arrancar

    def ejecutar(self, sql, params=()):
        """Ejecuta una sentencia con escritura (con bloqueo global)."""
        with self._lock:
            conn = self._conexion()
            cur = conn.execute(sql, params)
            conn.commit()
            return cur

    def consultar(self, sql, params=()):
        conn = self._conexion()
        return conn.execute(sql, params).fetchall()

    def consultarUno(self, sql, params=()):
        conn = self._conexion()
        return conn.execute(sql, params).fetchone()

    def transaccion(self):
        """Context manager: varias escrituras atómicas (todo o nada)."""
        return _Transaccion(self)

    def get_config(self, clave, defecto=None):
        fila = self.consultarUno("SELECT valor FROM config WHERE clave=?", (clave,))
        return fila["valor"] if fila else defecto

    def set_config(self, clave, valor):
        self.ejecutar(
            "INSERT INTO config(clave, valor) VALUES(?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (clave, str(valor)),
        )

    def cerrar(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def cerrar_todas(self):
        """Cierra todas las conexiones (también las creadas por otros hilos)."""
        with self._lock:
            for conn in self._conns:
                try:
                    conn.close()
                except Exception:
                    pass
            self._conns.clear()
        self._local.conn = None


class _Transaccion:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db._lock.acquire()
        self.conn = self.db._conexion()
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.db._lock.release()
        return False
