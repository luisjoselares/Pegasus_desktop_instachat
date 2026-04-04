import sqlite3

class LocalDBService:
    def __init__(self):
        self.db_name = "monitor_pegasus.db"
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cuentas_ig (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    password_enc TEXT NOT NULL,
                    proxy TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def agregar_cuenta(self, usuario, password_enc, proxy=""):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("INSERT INTO cuentas_ig (usuario, password_enc, proxy) VALUES (?, ?, ?)",
                         (usuario, password_enc, proxy))

    def obtener_cuentas(self):
        with sqlite3.connect(self.db_name) as conn:
            # Traemos todos los campos incluyendo el proxy
            return conn.execute("SELECT id, usuario, password_enc, proxy FROM cuentas_ig").fetchall()

    def eliminar_cuenta(self, id_cuenta):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("DELETE FROM cuentas_ig WHERE id = ?", (id_cuenta,))