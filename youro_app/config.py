"""Configuración y parámetros económicos de Yuro."""
import os

VERSION = "3.0"
NOMBRE_MONEDA = "Yuro"
NOMBRE_MONEDA_PLURAL = "Yuros"
SIMBOLO = "Y"

RUTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_DB = os.path.join(RUTA_APP, "yuro.db")
CARPETA_BACKUPS = os.path.join(RUTA_APP, "backups")
CARPETA_ARCHIVOS = os.path.join(RUTA_APP, "archivos")
PUERTO = int(os.environ.get("PORT") or os.environ.get("YURO_PUERTO") or "8080")

# ---------------- Modelo económico (estilo Bitcoin) -------------------------
DIFICULTAD = 4
DIFICULTAD_MAX = 6
RECOMPENSA = 25.0
RECOMPENSA_MIN = 0.5
BIENVENIDA = 50.0
BLOQUES_OBJETIVO = 60
AJUSTE_DIFICULTAD = 20
HALVING_CADA = 210
MINIMO_ENTRE_BLOQUES = 30

# ---------------- Límite de suministro --------------------------------------
SUMINISTRO_MAXIMO = 21_000_000.0
SUMINISTRO_OBJETIVO = 20_000_000.0

# ---------------- Quema / Burn ----------------------------------------------
QUEMA_ENVIO_PCT = 0.5
QUEMA_MINIMA = 0.01

# ---------------- Banco Central (Gobierno) ----------------------------------
# El gobierno controla la economía como un banco central real
TASA_INTERES_BASE = 5.0        # tasa de interés base (% anual)
TASA_INFLACION_OBJETIVO = 2.0  # objetivo de inflación (%)
CAPACIDAD_IMPRESION = 100000.0 # máximo que el gobierno puede imprimir por día
RESERVA_ORO = 1000000.0        # reserva de "oro" del banco central

# ---------------- Bancos -----------------------------------------------------
BANCOS_HABILITADOS = True
BANCO_MAXIMO_DEPOSITO = 1_000_000.0
BANCO_INTERES_MIN = 0.5        # interés mínimo que un banco puede dar
BANCO_INTERES_MAX = 15.0       # interés máximo que un banco puede dar
BANCO_PRESTAMO_MAX = 500000.0
BANCO_PRESTAMO_INTERES_MIN = 5.0
BANCO_PRESTAMO_INTERES_MAX = 30.0
BANCO_GARANTIA_PCT = 150.      # garantía necesaria para préstamo (%)
COMISION_BANCO_PCT = 2.0       # comisión del banco por transacción

# ---------------- Bolsa de Valores (Simulador) ------------------------------
BOLSA_HABILITADA = True
BOLSA_ACCIONES_INICIALES = [    # empresas simuladas
    {"simbolo": "YURO", "nombre": "Yuro Corp", "precio_base": 100.0, "sector": "Tecnología"},
    {"simbolo": "BNCO", "nombre": "Banco Nacional", "precio_base": 85.0, "sector": "Financiero"},
    {"simbolo": "ENER", "nombre": "Energía Solar", "precio_base": 60.0, "sector": "Energía"},
    {"simbolo": "MINE", "nombre": "Minería del Yuro", "precio_base": 45.0, "sector": "Minería"},
    {"simbolo": "AGRO", "nombre": "AgroYuro", "precio_base": 30.0, "sector": "Agricultura"},
    {"simbolo": "TECH", "nombre": "TechMineros", "precio_base": 120.0, "sector": "Tecnología"},
    {"simbolo": "BANK", "nombre": "Banco Amigo", "precio_base": 75.0, "sector": "Financiero"},
    {"simbolo": "SHOP", "nombre": "Tienda Yuro", "precio_base": 40.0, "sector": "Comercio"},
]
BOLSA_COMISION_PCT = 1.0       # comisión por compra/venta
BOLSA_VOLATILIDAD = 0.05       # volatilidad máxima (%)
BOLSA_DIVIDENDO_PCT = 2.0      # dividendo anual (%)
BOLSA_HORA_APERTURA = 8        # hora apertura (UTC)
BOLSA_HORA_CIERRE = 20         # hora cierre (UTC)

# ---------------- Staking -----------------------------------------------------
STAKING_HABILITADO = True
STAKING_APY = 2.0
STAKING_MINIMO = 100.0
STAKING_PAGO_DIARIO = True

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
