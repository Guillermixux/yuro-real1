"""Configuración y parámetros económicos de Yuro."""
import os

VERSION = "3.1"
NOMBRE_MONEDA = "Yuro"
NOMBRE_MONEDA_PLURAL = "Yuros"
SIMBOLO = "Y"

RUTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_DB = os.path.join(RUTA_APP, "yuro.db")
CARPETA_BACKUPS = os.path.join(RUTA_APP, "backups")
CARPETA_ARCHIVOS = os.path.join(RUTA_APP, "archivos")
PUERTO = int(os.environ.get("PORT") or os.environ.get("YURO_PUERTO") or "8080")

# ---------------- Modelo económico (estilo Bitcoin) -------------------------
DIFICULTAD = 5
DIFICULTAD_MAX = 8
RECOMPENSA = 15.0
RECOMPENSA_MIN = 0.1
BIENVENIDA = 25.0
BLOQUES_OBJETIVO = 60
AJUSTE_DIFICULTAD = 15
HALVING_CADA = 210
MINIMO_ENTRE_BLOQUES = 45

# ---------------- Límite de suministro --------------------------------------
SUMINISTRO_MAXIMO = 21_000_000.0
SUMINISTRO_OBJETIVO = 20_000_000.0

# ---------------- Quema / Burn ----------------------------------------------
QUEMA_ENVIO_PCT = 1.0
QUEMA_MINIMA = 0.01

# ---------------- Seguridad ---------------------------------------------------
SALTO_PBKDF2 = 50_000
DURACION_SESION_DIAS = 30
MAX_FALLOS_LOGIN = 5
BLOQUEO_LOGIN_SEG = 300
MAX_REGISTROS_POR_IP = 5
LIMITE_CONCEPTO = 80
MIN_CARACTERES_PASSWORD = 6

NOMBRE_MIN = 3
NOMBRE_MAX = 16

# ---------------- Gobierno ---------------------------------------------------
IMPUESTO_DEFECTO = 0.0
IMPUESTO_MAX = 50.0
DIRECCION_GOBIERNO = "GOBIERNO"
DIRECCION_BANCO_CENTRAL = "BANCO_CENTRAL"
DIRECCION_BOLSA = "BOLSA"

ANUNCIO_MAX = 300
RECOMPENSA_MIN = 0.5
RECOMPENSA_MAX = 100.0
LOG_ACCIONES_MAX = 200

# ---------------- Notificaciones ---------------------------------------------
NTFY_URL = "https://ntfy.sh"
NTFY_PREFIJO = "yuro-"
NTFY_TIMEOUT = 5
SSE_TIMEOUT = 30

# ---------------- Tablón -------------------------------------------------------
TABLON_ARCHIVO_MAX = 5 * 1024 * 1024
TABLON_TIPOS_OK = {"jpg","jpeg","png","gif","webp","svg","pdf","txt","md","doc","docx","csv","zip"}
TABLON_CONTENIDO_MAX = 5000
