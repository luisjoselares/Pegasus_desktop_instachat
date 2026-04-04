import sqlite3

class LocalDBService:
    def __init__(self):
        # 1. Usar el nombre correcto del archivo que subiste
        self.db_name = "pegasus_bot.db" 
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _create_table(self):
        with self._get_connection() as conn:
            # Aseguramos que la tabla settings exista con la estructura de tu DB
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insta_user TEXT,
                    insta_pass TEXT,
                    groq_api_key TEXT,
                    system_prompt TEXT DEFAULT ''
                )
            """)

    def obtener_cuentas(self):
        with self._get_connection() as conn:
            # Seleccionamos las columnas EXACTAS que tiene pegasus_bot.db
            cursor = conn.execute("SELECT id, insta_user, insta_pass, groq_api_key, system_prompt FROM settings")
            return cursor.fetchall()

    def actualizar_contexto(self, account_id, prompt):
        # Este es el método que tu controlador estaba pidiendo
        with self._get_connection() as conn:
            conn.execute("UPDATE settings SET system_prompt = ? WHERE id = ?", (prompt, account_id))
            conn.commit()

    def eliminar_cuenta(self, id_cuenta):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE id = ?", (id_cuenta,))