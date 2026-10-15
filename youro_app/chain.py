"""La cadena de bloques de YOURO: prueba de trabajo, halving y libro mayor público."""
import hashlib
import json
import time

from . import config

CERO_HASH = "0" * 64


def _contenido_hash(indice, transacciones, hash_anterior, minero, nonce, timestamp):
    """Serialización canónica de un bloque (clave de su integridad)."""
    return json.dumps(
        {
            "indice": indice,
            "transacciones": transacciones,
            "hash_anterior": hash_anterior,
            "minero": minero,
            "nonce": nonce,
            "timestamp": timestamp,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


def calcular_hash_bloque(indice, transacciones, hash_anterior, minero, nonce, timestamp):
    return hashlib.sha256(
        _contenido_hash(indice, transacciones, hash_anterior, minero, nonce, timestamp)
    ).hexdigest()


def _tx_canonica(fila):
    """Dict de transacción tal y como entra en el hash del bloque."""
    return {
        "de": fila["de"],
        "para": fila["para"],
        "cantidad": round(fila["cantidad"], 2),
        "concepto": fila["concepto"],
        "tipo": fila["tipo"],
        "timestamp": fila["timestamp"],
    }


class Cadena:
    """Libro mayor: transacciones, bloques minados y saldos públicos."""

    def __init__(self, db):
        self.db = db
        self._asegurar_genesis()

    # ---------------------- génesis y carga ----------------------
    def _asegurar_genesis(self):
        if self.db.consultarUno("SELECT 1 FROM bloques LIMIT 1"):
            return
        timestamp = time.time()
        hash_genesis = calcular_hash_bloque(0, [], CERO_HASH, "GENESIS", 0, timestamp)
        with self.db.transaccion() as conn:
            conn.execute(
                "INSERT INTO bloques(indice, hash, hash_anterior, minero, nonce, timestamp, "
                "dificultad) VALUES(0, ?, ?, 'GENESIS', 0, ?, 0)",
                (hash_genesis, CERO_HASH, timestamp),
            )

    # ---------------------- consultas de saldo ----------------------
    def saldo(self, direccion):
        """Confirmado en la cadena + pendientes de minar."""
        fila = self.db.consultarUno(
            """
            SELECT
              COALESCE(SUM(CASE WHEN bloque IS NOT NULL AND para = ?  THEN cantidad END), 0)
            - COALESCE(SUM(CASE WHEN bloque IS NOT NULL AND de = ?     THEN cantidad END), 0)
            + COALESCE(SUM(CASE WHEN bloque IS NULL     AND para = ?  THEN cantidad END), 0)
            - COALESCE(SUM(CASE WHEN bloque IS NULL     AND de = ?     THEN cantidad END), 0)
              AS saldo
            FROM transacciones
            WHERE (para = ? OR de = ?)
            """,
            (direccion, direccion, direccion, direccion, direccion, direccion),
        )
        return round(fila["saldo"] or 0.0, 2)

    def transacciones_de(self, direccion, limite=50):
        filas = self.db.consultar(
            """
            SELECT t.*, b.indice AS bloque_num
            FROM transacciones t LEFT JOIN bloques b ON b.indice = t.bloque
            WHERE (t.para = ? OR t.de = ?)
            ORDER BY t.id DESC LIMIT ?
            """,
            (direccion, direccion, limite),
        )
        return [dict(f) for f in filas]

    def transacciones_bloque(self, indice):
        filas = self.db.consultar(
            "SELECT * FROM transacciones WHERE bloque = ? ORDER BY id ASC", (indice,)
        )
        return [dict(f) for f in filas]

    def pendientes(self):
        filas = self.db.consultar(
            "SELECT * FROM transacciones WHERE bloque IS NULL ORDER BY id ASC"
        )
        return [dict(f) for f in filas]

    def contar_pendientes(self):
        fila = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM transacciones WHERE bloque IS NULL"
        )
        return fila["n"]

    # ---------------------- escribir en el libro ----------------------
    def enviar(self, de, para, cantidad, concepto=None):
        """Añade una transacción al pool pendiente. Lanza ValueError si no se puede."""
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser un número positivo.")
        if de == para:
            raise ValueError("No puedes enviarte youros a ti mismo.")
        concepto = (concepto or "").strip()[: config.LIMITE_CONCEPTO] or None
        with self.db.transaccion() as conn:
            if self._saldo_en(conn, de) < cantidad:
                raise ValueError("No tienes suficientes youros.")
            conn.execute(
                "INSERT INTO transacciones(de, para, cantidad, concepto, tipo, timestamp) "
                "VALUES(?, ?, ?, ?, 'transfer', ?)",
                (de, para, cantidad, concepto, time.time()),
            )
        return cantidad

    def _saldo_en(self, conn, direccion):
        """Saldo consultando dentro de una transacción abierta (mismo visor)."""
        fila = conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN bloque IS NOT NULL AND para = ?  THEN cantidad END), 0)
            - COALESCE(SUM(CASE WHEN bloque IS NOT NULL AND de = ?     THEN cantidad END), 0)
            + COALESCE(SUM(CASE WHEN bloque IS NULL     AND para = ?  THEN cantidad END), 0)
            - COALESCE(SUM(CASE WHEN bloque IS NULL     AND de = ?     THEN cantidad END), 0)
              AS saldo
            FROM transacciones
            WHERE (para = ? OR de = ?)
            """,
            (direccion, direccion, direccion, direccion, direccion, direccion),
        ).fetchone()
        return round(fila["saldo"] or 0.0, 2)

    def dar(self, direccion, cantidad, tipo="faucet", de="FAUCET"):
        """Acuña monedas nuevas (regalo de bienvenida)."""
        cantidad = round(float(cantidad), 2)
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva.")
        if tipo not in ("faucet", "coinbase"):
            raise ValueError("Tipo de acuñación no válido.")
        with self.db.transaccion() as conn:
            conn.execute(
                "INSERT INTO transacciones(de, para, cantidad, concepto, tipo, timestamp) "
                "VALUES(?, ?, ?, NULL, ?, ?)",
                (de, direccion, cantidad, tipo, time.time()),
            )

    # ---------------------- minar ----------------------
    def recompensa_actual(self):
        hechos = self.contar_bloques() // config.HALVING_CADA
        return round(config.RECOMPENSA / (2 ** hechos), 2)

    def proximo_halving(self):
        hechos = self.contar_bloques() // config.HALVING_CADA
        return (hechos + 1) * config.HALVING_CADA

    def contar_bloques(self):
        fila = self.db.consultarUno("SELECT COUNT(*) AS n FROM bloques")
        return fila["n"]

    def ultimo_bloque(self):
        return self.db.consultarUno(
            "SELECT * FROM bloques ORDER BY indice DESC LIMIT 1"
        )

    def suministro_total(self):
        fila = self.db.consultarUno(
            "SELECT COALESCE(SUM(cantidad), 0) AS total FROM transacciones "
            "WHERE tipo IN ('coinbase', 'faucet')"
        )
        return round(fila["total"], 2)

    def minar(self, direccion_minero):
        """Crea, prueba de trabajo y encadena un bloque. Devuelve el dict del bloque."""
        recompensa = self.recompensa_actual()
        if recompensa <= 0:
            raise ValueError("La emisión de youros nuevos ya ha terminado (tope alcanzado).")

        with self.db.lock:
            ultimo = self.ultimo_bloque()
            transcurrido = max(time.time() - ultimo["timestamp"], 0)
            espera = config.MINIMO_ENTRE_BLOQUES - transcurrido
            if espera > 0:
                raise ValueError(
                    f"Espera {int(espera) + 1}s antes de minar: los bloques "
                    f"tardan al menos {config.MINIMO_ENTRE_BLOQUES}s entre sí."
                )

            dificultad = self._dificultad_siguiente()
            indice = ultimo["indice"] + 1
            pendientes = self.pendientes()
            txs_validas = self._filtrar_pendientes_invalidas(pendientes, recompensa, direccion_minero)

            timestamp = time.time()
            # Orden canónico del bloque: pendientes por id (ASC) y la recompensa
            # (coinbase) la última, igual que quedaría en la tabla por su id.
            coinbase = {
                "de": "COINBASE",
                "para": direccion_minero,
                "cantidad": recompensa,
                "concepto": None,
                "tipo": "coinbase",
                "timestamp": timestamp,
            }
            txs_bloque = [_tx_canonica(t) for t in txs_validas] + [coinbase]

            nonce = 0
            objetivo = "0" * dificultad
            while True:
                hash_actual = calcular_hash_bloque(
                    indice, txs_bloque, ultimo["hash"], direccion_minero, nonce, timestamp
                )
                if hash_actual.startswith(objetivo):
                    break
                nonce += 1

            with self.db.transaccion() as conn:
                conn.execute(
                    "INSERT INTO bloques(indice, hash, hash_anterior, minero, nonce, timestamp, "
                    "dificultad) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (indice, hash_actual, ultimo["hash"], direccion_minero, nonce,
                     timestamp, dificultad),
                )
                ids = ",".join("?" * len(txs_validas)) if txs_validas else None
                if ids:
                    conn.execute(
                        f"UPDATE transacciones SET bloque = ? WHERE id IN ({ids})",
                        (indice, *[t["id"] for t in txs_validas]),
                    )
                conn.execute(
                    "INSERT INTO transacciones(bloque, de, para, cantidad, concepto, tipo, "
                    "timestamp) VALUES(?, 'COINBASE', ?, ?, NULL, 'coinbase', ?)",
                    (indice, direccion_minero, recompensa, timestamp),
                )
            return {
                "indice": indice,
                "hash": hash_actual,
                "hash_anterior": ultimo["hash"],
                "minero": direccion_minero,
                "nonce": nonce,
                "timestamp": timestamp,
                "dificultad": dificultad,
                "recompensa": recompensa,
                "transacciones": len(txs_validas) + 1,
            }

    def _filtrar_pendientes_invalidas(self, pendientes, recompensa, direccion_minero):
        """Devuelve las transacciones que entran en el bloque, en orden canónico
        (id ASC). Descarta (y borra) cualquier pendiente que dejara saldo negativo
        por corrupción externa: así la cadena nunca se queda bloqueada."""
        saldos = {}
        validas = []
        invalidas = []
        for t in pendientes:
            # FAUCET/COINBASE acuñan dinero nuevo: nunca pueden quedarse sin saldo.
            if t["de"] not in ("FAUCET", "COINBASE"):
                saldos[t["de"]] = (
                    saldos.get(t["de"], self._saldo_actual_cached(t["de"])) - t["cantidad"]
                )
            saldos[t["para"]] = (
                saldos.get(t["para"], self._saldo_actual_cached(t["para"])) + t["cantidad"]
            )
            if t["de"] not in ("FAUCET", "COINBASE") and saldos[t["de"]] < -0.001:
                invalidas.append(t["id"])
                saldos[t["de"]] += t["cantidad"]
                saldos[t["para"]] -= t["cantidad"]
            else:
                validas.append(t)
        if invalidas:
            ids = ",".join("?" * len(invalidas))
            self.db.ejecutar(f"DELETE FROM transacciones WHERE id IN ({ids})", invalidas)
        return validas

    def _saldo_actual_cached(self, direccion):
        return self.saldo(direccion)

    def _dificultad_siguiente(self):
        """Dificultad que debería tener el próximo bloque (regla de ajuste)."""
        bloques = self.db.consultar("SELECT indice, timestamp FROM bloques ORDER BY indice")
        dificultad = config.DIFICULTAD
        n = config.AJUSTE_DIFICULTAD
        for i in range(1, len(bloques)):
            if i >= n:
                tiempo_real = max(bloques[i]["timestamp"] - bloques[i - n]["timestamp"], 0.001)
                ratio = tiempo_real / (config.BLOQUES_OBJETIVO * n)
                if ratio < 0.5:
                    dificultad = min(dificultad + 1, config.DIFICULTAD_MAX)
                elif ratio > 2.0:
                    dificultad = max(1, dificultad - 1)
        return dificultad

    # ---------------------- validación ----------------------
    def es_valida(self):
        try:
            self.validar_cadena()
            return True
        except ValueError:
            return False

    def validar_cadena(self):
        """Comprueba hashes, encadenado, prueba de trabajo y regla de dificultad."""
        bloques = self.db.consultar("SELECT * FROM bloques ORDER BY indice")
        if not bloques:
            raise ValueError("La cadena está vacía.")
        if bloques[0]["indice"] != 0 or bloques[0]["hash_anterior"] != CERO_HASH:
            raise ValueError("El bloque génesis no es válido.")
        dificultad = config.DIFICULTAD
        n = config.AJUSTE_DIFICULTAD
        for i, b in enumerate(bloques):
            txs = [_tx_canonica(f) for f in self.transacciones_bloque(b["indice"])]
            hash_calc = calcular_hash_bloque(
                b["indice"], txs, b["hash_anterior"], b["minero"], b["nonce"], b["timestamp"]
            )
            if hash_calc != b["hash"]:
                raise ValueError(f"El hash del bloque #{b['indice']} no coincide: la cadena ha sido alterada.")
            if i > 0:
                if b["hash_anterior"] != bloques[i - 1]["hash"]:
                    raise ValueError(f"El bloque #{b['indice']} no enlaza con el anterior.")
                if not b["hash"].startswith("0" * b["dificultad"]):
                    raise ValueError(f"El bloque #{b['indice']} no cumple la prueba de trabajo.")
                if b["dificultad"] != dificultad:
                    raise ValueError(f"El bloque #{b['indice']} usa una dificultad inesperada.")
            if i >= n:
                tiempo_real = max(bloques[i]["timestamp"] - bloques[i - n]["timestamp"], 0.001)
                ratio = tiempo_real / (config.BLOQUES_OBJETIVO * n)
                if ratio < 0.5:
                    dificultad = min(dificultad + 1, config.DIFICULTAD_MAX)
                elif ratio > 2.0:
                    dificultad = max(1, dificultad - 1)
        # El saldo nunca debe ser negativo (libro mayor coherente).
        filas = self.db.consultar(
            """
            SELECT direccion, SUM(monto) AS saldo FROM (
              SELECT para AS direccion,  cantidad AS monto FROM transacciones WHERE bloque IS NOT NULL
              UNION ALL
              SELECT de    AS direccion, -cantidad AS monto FROM transacciones WHERE bloque IS NOT NULL
            ) GROUP BY direccion HAVING saldo < -0.001 AND direccion NOT IN ('FAUCET','COINBASE')
            """
        )
        if filas:
            raise ValueError(
                "Hay saldos negativos en la cadena: "
                + ", ".join(f"{f['direccion'][:12]}…={f['saldo']:.2f}" for f in filas)
            )
        return True

    # ---------------------- estadísticas y directorio ----------------------
    def estadisticas(self):
        return {
            "bloques": self.contar_bloques(),
            "pendientes": self.contar_pendientes(),
            "dificultad": self._dificultad_siguiente(),
            "recompensa": self.recompensa_actual(),
            "suministro": self.suministro_total(),
            "proximo_halving": self.proximo_halving(),
            "valida": self.es_valida(),
        }

    def ranking(self, limite=50):
        """Saldos públicos de los usuarios normales (sin admins), de mayor a menor."""
        filas = self.db.consultar(
            """
            SELECT t.direccion, SUM(t.saldo) AS saldo FROM (
              SELECT para AS direccion,  cantidad AS saldo FROM transacciones
              UNION ALL
              SELECT de    AS direccion, -cantidad AS saldo FROM transacciones
            ) t
            LEFT JOIN usuarios u ON u.direccion = t.direccion
            WHERE ABS(t.saldo) > 0.00001
              AND t.direccion NOT IN ('FAUCET', 'COINBASE', 'GOBIERNO')
              AND (u.es_admin IS NULL OR u.es_admin = 0)
            GROUP BY t.direccion
            ORDER BY saldo DESC
            LIMIT ?
            """,
            (limite,),
        )
        return [dict(f) for f in filas]

    def perfil(self, direccion):
        """Datos públicos de una dirección para su página de perfil."""
        recibido = self.db.consultarUno(
            "SELECT COALESCE(SUM(cantidad),0) AS t FROM transacciones WHERE para=? AND tipo!='coinbase'",
            (direccion,),
        )["t"]
        enviado = self.db.consultarUno(
            "SELECT COALESCE(SUM(cantidad),0) AS t FROM transacciones WHERE de=? AND tipo!='coinbase'",
            (direccion,),
        )["t"]
        n_tx = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM transacciones WHERE para=? OR de=?",
            (direccion, direccion),
        )["n"]
        bloques_minados = self.db.consultarUno(
            "SELECT COUNT(*) AS n FROM bloques WHERE minero=?", (direccion,)
        )["n"]
        return {
            "direccion": direccion,
            "saldo": self.saldo(direccion),
            "recibido": round(recibido or 0.0, 2),
            "enviado": round(enviado or 0.0, 2),
            "transacciones": n_tx,
            "bloques_minados": bloques_minados,
        }

    def bloques_recientes(self, desde=None, limite=25):
        if desde is None:
            filas = self.db.consultar(
                "SELECT * FROM bloques ORDER BY indice DESC LIMIT ?", (limite,)
            )
        else:
            filas = self.db.consultar(
                "SELECT * FROM bloques WHERE indice < ? ORDER BY indice DESC LIMIT ?",
                (desde, limite),
            )
        return [dict(f) for f in filas]
