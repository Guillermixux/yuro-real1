"""Configuración y parámetros económicos de YOURO."""
import os

VERSION = "2.0"

RUTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_DB = os.path.join(RUTA_APP, "youro.db")
CARPETA_BACKUPS = os.path.join(RUTA_APP, "backups")
PUERTO = int(os.environ.get("YOURO_PUERTO", "8080"))

# ---------------- Modelo económico (anti-inflación, tipo Bitcoin) ----------
DIFICULTAD = 3             # ceros iniciales en el hash
DIFICULTAD_MAX = 5         # tope de dificultad (protege el servidor)
RECOMPENSA = 50.0          # youros por minar el bloque 1 (luego halving)
BIENVENIDA = 100.0         # regalo único al registrarte (faucet)
BLOQUES_OBJETIVO = 20      # segundos ideales entre bloques
AJUSTE_DIFICULTAD = 10     # se reajusta la dificultad cada N bloques
HALVING_CADA = 50          # la recompensa baja a la mitad cada N bloques
MINIMO_ENTRE_BLOQUES = 5   # segundos mínimos entre bloques

# ---------------- Seguridad y límites -------------------------------------
SALTO_PBKDF2 = 200_000     # iteraciones PBKDF2 (lento a propósito)
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
