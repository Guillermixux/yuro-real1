"""Identidad: usuarios, contraseñas (PBKDF2), sesiones y límites de seguridad."""
import hashlib
import re
import secrets
import time

from . import config

NOMBRE_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")
IBAN_RE = re.compile(r"^YU[0-9A-Z]{38}$")

# Fallos de login por IP (en memoria: se reinicia con el servidor)
_fallos_login = {}


def hash_password(password, sal=None, iteraciones=None):
    """PBKDF2-HMAC-SHA256 con sal: lento a propósito para resistir ataques."""
    iteraciones = iteraciones or config.SALTO_PBKDF2
    sal = sal or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             bytes.fromhex(sal), iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal}${dk.hex()}", sal


def verificar_password(password, almacenado):
    try:
        algoritmo, iteraciones, sal, resumen = almacenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(sal), int(iteraciones))
        return secrets.compare_digest(dk.hex(), resumen)
    except Exception:
        return False


def direccion_aleatoria():
    """Genera IBAN YU + 38 caracteres alfanuméricos."""
    cuerpo = secrets.token_hex(19).upper()  # 38 hex chars
    return f"YU{cuerpo}"


def formatear_iban(direccion):
    """Formatea IBAN en grupos de 4: YU00 XXXX XXXX ..."""
    if not direccion or len(direccion) < 4:
        return direccion
    grupos = [direccion[i:i+4] for i in range(0, len(direccion), 4)]
    return " ".join(grupos)


def validar_iban(direccion):
    """Valida formato IBAN YU."""
    if not direccion:
        return False
    return IBAN_RE.match(direccion.upper().replace(" ", "")) is not None


class Identidad:
    def __init__(self, db):
        self.db = db

    # ---------------------- usuarios ----------------------
    def registrar(self, nombre, password, ip=None, es_admin=False):
        nombre = (nombre or "").strip()
        if not NOMBRE_RE.match(nombre):
            raise ValueError(
                "El nombre debe tener 3-16 caracteres: letras, números o guion bajo."
            )
        if len(password or "") < config.MIN_CARACTERES_PASSWORD:
            raise ValueError(
                f"La contraseña debe tener al menos {config.MIN_CARACTERES_PASSWORD} caracteres."
            )
        existe = self.db.consultarUno(
            "SELECT 1 FROM usuarios WHERE nombre_lower = ?", (nombre.lower(),)
        )
        if existe:
            raise ValueError("Ese nombre ya está cogido.")
        ph, sal = hash_password(password)
        csrf = secrets.token_urlsafe(24)
        direccion = direccion_aleatoria()
        while self.db.consultarUno("SELECT 1 FROM usuarios WHERE direccion=?", (direccion,)):
            direccion = direccion_aleatoria()
        self.db.ejecutar(
            "INSERT INTO usuarios(nombre, nombre_lower, password_hash, sal, direccion, csrf, "
            "ip, es_admin, creado) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nombre, nombre.lower(), ph, sal, direccion, csrf, ip, 1 if es_admin else 0, time.time()),
        )
        return self.buscar(nombre)

    def buscar(self, nombre):
        return self.db.consultarUno(
            "SELECT * FROM usuarios WHERE nombre_lower = ?", ((nombre or "").strip().lower(),)
        )

    def por_direccion(self, direccion):
        return self.db.consultarUno(
            "SELECT * FROM usuarios WHERE direccion = ?", (direccion,)
        )

    def lista_nombres(self):
        filas = self.db.consultar("SELECT nombre FROM usuarios ORDER BY nombre_lower")
        return [f["nombre"] for f in filas]

    def contar_por_ip(self, ip):
        if not ip:
            return 0
        fila = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM usuarios WHERE ip = ?", (ip,)
        )
        return fila["n"]

    # ---------------------- sesiones ----------------------
    def entrar(self, nombre, password, ip=None):
        if not self._puede_login(ip):
            raise ValueError(
                "Demasiados intentos fallidos. Espera unos minutos y prueba otra vez."
            )
        usuario = self.buscar(nombre)
        if not usuario or not verificar_password(password, usuario["password_hash"]):
            self._registrar_fallo(ip)
            raise ValueError("Nombre o contraseña incorrectos.")
        self._borrar_fallos(ip)
        token = secrets.token_urlsafe(32)
        ahora = time.time()
        self.db.ejecutar(
            "INSERT INTO sesiones(token, nombre, csrf, creado, expira) VALUES(?, ?, ?, ?, ?)",
            (token, usuario["nombre"], usuario["csrf"], ahora,
             ahora + config.DURACION_SESION_DIAS * 86400),
        )
        return token, usuario

    def salir(self, token):
        if token:
            self.db.ejecutar("DELETE FROM sesiones WHERE token = ?", (token,))

    def usuario_de_token(self, token):
        if not token:
            return None
        fila = self.db.consultarUno(
            "SELECT u.* FROM sesiones s JOIN usuarios u ON u.nombre = s.nombre "
            "WHERE s.token = ? AND s.expira > ?",
            (token, time.time()),
        )
        return fila

    def limpiar_sesiones(self):
        self.db.ejecutar("DELETE FROM sesiones WHERE expira <= ?", (time.time(),))

    def cambiar_password(self, nombre, password_actual, password_nuevo):
        """Cambia la contraseña de un usuario verificando la actual."""
        usuario = self.buscar(nombre)
        if not usuario:
            raise ValueError("Usuario no encontrado.")
        if not verificar_password(password_actual, usuario["password_hash"]):
            raise ValueError("La contraseña actual es incorrecta.")
        if len(password_nuevo) < config.MIN_CARACTERES_PASSWORD:
            raise ValueError(
                f"La contraseña nueva debe tener al menos "
                f"{config.MIN_CARACTERES_PASSWORD} caracteres."
            )
        hash_nuevo, sal = hash_password(password_nuevo)
        self.db.ejecutar(
            "UPDATE usuarios SET password_hash=?, sal=? WHERE nombre=?",
            (hash_nuevo, sal, nombre),
        )
        # Cerrar todas las sesiones excepto la actual (se reconecta después)
        self.db.ejecutar("DELETE FROM sesiones WHERE nombre=?", (nombre,))
        return True

    def es_congelado(self, nombre):
        """Comprueba si una cuenta está congelada."""
        usuario = self.buscar(nombre)
        return bool(usuario and usuario["congelado"])

    # ---------------------- límites en memoria ----------------------
    def _puede_login(self, ip):
        if not ip:
            return True
        ahora = time.time()
        recientes = [t for t in _fallos_login.get(ip, []) if ahora - t < config.BLOQUEO_LOGIN_SEG]
        _fallos_login[ip] = recientes
        return len(recientes) < config.MAX_FALLOS_LOGIN

    def _registrar_fallo(self, ip):
        if ip:
            _fallos_login.setdefault(ip, []).append(time.time())

    def _borrar_fallos(self, ip):
        _fallos_login.pop(ip, None)
