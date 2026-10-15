"""Configuración y parámetros económicos de Yuro."""
import os

VERSION = "2.0"
NOMBRE_MONEDA = "Yuro"
NOMBRE_MONEDA_PLURAL = "Yuros"
SIMBOLO = "Y"

RUTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_DB = os.path.join(RUTA_APP, "yuro.db")
CARPETA_BACKUPS = os.path.join(RUTA_APP, "backups")
CARPETA_ARCHIVOS = os.path.join(RUTA_APP, "archivos")  # para el tablón
PUERTO = int(os.environ.get("YURO_PUERTO", "8080"))

# ---------------- Modelo económico (anti-inflación, tipo Bitcoin) ----------
DIFICULTAD = 3             # ceros iniciales en el hash
DIFICULTAD_MAX = 5         # tope de dificultad (protege el servidor)
RECOMPENSA = 50.0          # yuros por minar el bloque 1 (luego halving)
BIENVENIDA = 100.0         # regalo único al registrarte (faucet)
BLOQUES_OBJETIVO = 20      # segundos ideales entre bloques
AJUSTE_DIFICULTAD = 10     # se reajusta la dificultad cada N bloques
HALVING_CADA = 50          # la recompensa baja a la mitad cada N bloques
MINIMO_ENTRE_BLOQUES = 5   # segundos mínimos entre bloques

# ---------------- Seguridad y límites -------------------------------------
SALTO_PBKDF2 = 50_000        # iteraciones PBKDF2 (bajado de 200k para velocidad)
DURACION_SESION_DIAS = 30
MAX_FALLOS_LOGIN = 5       # fallos antes de bloquear temporalmente
BLOQUEO_LOGIN_SEG = 300    # segundos de bloqueo tras demasiados fallos
MAX_REGISTROS_POR_IP = 5   # registros permitidos por dirección IP
LIMITE_CONCEPTO = 80       # caracteres máximos del concepto de pago
MIN_CARACTERES_PASSWORD = 6

NOMBRE_MIN = 3
NOMBRE_MAX = 16

# ---------------- Gobierno / Impuestos -----------------------------------
IMPUESTO_DEFECTO = 0.0     # % de impuesto por transacción (0 = sin impuestos)
IMPUESTO_MAX = 50.0        # tope máximo de impuesto (50%)
DIRECCION_GOBIERNO = "GOBIERNO"  # dirección especial que recoge impuestos

# ---------------- Nuevas capacidades de gobierno ---------------------------
ANUNCIO_MAX = 300          # caracteres máximos del anuncio
RECOMPENSA_MIN = 1.0       # recompensa mínima de minería
RECOMPENSA_MAX = 500.0     # recompensa máxima de minería
LOG_ACCIONES_MAX = 200     # registros de acciones del gobierno que se guardan

# ---------------- Notificaciones push (ntfy.sh) -----------------------------
NTFY_URL = "https://ntfy.sh"          # servidor gratuito
NTFY_PREFIJO = "yuro-"                # prefijo de los temas
NTFY_TIMEOUT = 5                      # segundos de timeout HTTP

# ---------------- Notificaciones del navegador (SSE) -------------------------
SSE_TIMEOUT = 30                      # segundos de timeout SSE

# ---------------- Tablón de anuncios ----------------------------------------
TABLON_ARCHIVO_MAX = 5 * 1024 * 1024  # 5 MB máximo por archivo
TABLON_TIPOS_OK = {                   # extensiones permitidas
    # Imágenes
    "jpg", "jpeg", "png", "gif", "webp", "svg",
    # Documentos
    "pdf", "txt", "md", "doc", "docx", "csv",
    # Otros
    "zip",
}
TABLON_CONTENIDO_MAX = 5000           # caracteres máximo del texto
