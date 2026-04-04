import sqlite3
import os
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_name="data/pegasus_bot.db"):
        # Crea la carpeta data/ si no existe
        os.makedirs(os.path.dirname(db_name), exist_ok=True)
        self.db_name = db_name
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Manejador de contexto para conexiones seguras a SQLite."""
        conn = sqlite3.connect(self.db_name)
        # Esto nos permite acceder a las columnas por nombre (ej: row['status'])
        conn.row_factory = sqlite3.Row 
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Crea las tablas necesarias si es la primera vez que se abre el programa."""
        with self.get_connection() as conn:
            # 1. Tabla de Estado de los Chats (Modo IA vs Modo Humano)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_status (
                    thread_id TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'ACTIVE',
                    last_manual_at TEXT
                )
            """)

            # 2. Tabla de Historial (Para saber qué respondió la IA)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    username TEXT,
                    mensaje_usuario TEXT,
                    respuesta_ia TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Tabla de Configuraciones Locales (Las credenciales que escribes en PyQt6)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY,
                    insta_user TEXT,
                    insta_pass TEXT,
                    groq_api_key TEXT,
                    system_prompt TEXT
                )
            """)
            
            # Insertamos una fila vacía de configuración si no existe ninguna
            count = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
            if count == 0:
                conn.execute("INSERT INTO settings (insta_user, insta_pass) VALUES ('', '')")
                
            conn.commit()

# Creamos la instancia global (Esta es la 'db' que se importa en instagram_engine.py)
db = DatabaseManager()