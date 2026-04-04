import sqlite3
import os

class LocalDBService:
    def __init__(self):
        # Buscamos la base de datos en la raíz o en data/
        self.db_path = "pegasus_bot.db"
        if not os.path.exists(self.db_path):
            self.db_path = os.path.join("data", "pegasus_bot.db")
        self._migrate()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _migrate(self):
        """Asegura que la tabla y la columna de contexto existan."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insta_user TEXT,
                    insta_pass TEXT,
                    groq_api_key TEXT,
                    system_prompt TEXT DEFAULT ''
                )
            """)
            # Verificación de columna por si acaso
            cursor = conn.execute("PRAGMA table_info(settings)")
            columns = [c[1] for c in cursor.fetchall()]
            if "system_prompt" not in columns:
                conn.execute("ALTER TABLE settings ADD COLUMN system_prompt TEXT DEFAULT ''")

    def agregar_cuenta(self, user, password, system_prompt=""):
        """ESTA ES LA FUNCIÓN QUE FALTABA"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO settings (insta_user, insta_pass, system_prompt) 
                VALUES (?, ?, ?)
            """, (user, password, system_prompt))
            conn.commit()

    def obtener_cuentas(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT id, insta_user, insta_pass, groq_api_key, system_prompt FROM settings")
            return cursor.fetchall()

    def actualizar_contexto(self, account_id, prompt):
        with self._get_connection() as conn:
            conn.execute("UPDATE settings SET system_prompt = ? WHERE id = ?", (prompt, account_id))
            conn.commit()

    def eliminar_cuenta(self, account_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE id = ?", (account_id,))
            conn.commit()