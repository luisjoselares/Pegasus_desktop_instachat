import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timedelta

class LocalDBService:
    def __init__(self):
        # Centralizamos la ruta en la raíz del proyecto para evitar confusiones
        self.db_path = "pegasus_bot.db"
        self._migrate()

    @contextmanager
    def get_connection(self):
        """
        Manejador de contexto profesional. 
        SOLUCIONA EL ERROR: 'has no attribute get_connection'
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # Permite acceder como row['columna']
        try:
            yield conn
        finally:
            conn.close()

    def _migrate(self):
        """Crea todas las tablas necesarias y asegura las columnas del diseño moderno."""
        with self.get_connection() as conn:
            # 1. Tabla de Configuración de Cuentas (Para el diseño elegante)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id TEXT DEFAULT '',
                    insta_user TEXT NOT NULL,
                    insta_pass TEXT NOT NULL,
                    store_name TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    system_prompt TEXT DEFAULT '',
                    bot_enabled INTEGER DEFAULT 0,
                    proxy TEXT DEFAULT 'Auto',
                    schedule_start TEXT DEFAULT '08:00',
                    schedule_end TEXT DEFAULT '18:00',
                    context_type TEXT DEFAULT 'Vendedor de tienda',                    session_data TEXT DEFAULT '',                    last_log TEXT DEFAULT 'Sistema listo'
                )
            """)

            # 2. Tabla de Historial (Requerida por el motor de chat)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id TEXT DEFAULT '',
                    thread_id TEXT,
                    username TEXT,
                    mensaje_usuario TEXT,
                    respuesta_ia TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Tabla de Estado de Chats (Activo/Manual y Procesamiento)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_status (
                    thread_id TEXT PRIMARY KEY,
                    cliente_id TEXT DEFAULT '',
                    status TEXT DEFAULT 'ACTIVE',
                    last_manual_at TEXT,
                    last_processed_at TEXT,
                    last_message_id TEXT,
                    paused_until TEXT
                )
            """)

            # --- MIGRACIÓN DE COLUMNAS (Para no perder datos existentes) ---
            cursor = conn.execute("PRAGMA table_info(settings)")
            columns = [c[1] for c in cursor.fetchall()]
            
            required_cols = {
                "cliente_id": "TEXT DEFAULT ''",
                "store_name": "TEXT DEFAULT ''",
                "description": "TEXT DEFAULT ''",
                "bot_enabled": "INTEGER DEFAULT 0",
                "proxy": "TEXT DEFAULT 'Auto'",
                "schedule_start": "TEXT DEFAULT '08:00'",
                "schedule_end": "TEXT DEFAULT '18:00'",
                "context_type": "TEXT DEFAULT 'Vendedor de tienda'",
                "session_data": "TEXT DEFAULT ''",
                "last_log": "TEXT DEFAULT 'Sistema listo'"
            }

            for col, definition in required_cols.items():
                if col not in columns:
                    conn.execute(f"ALTER TABLE settings ADD COLUMN {col} {definition}")

            cursor = conn.execute("PRAGMA table_info(chat_history)")
            history_columns = [c[1] for c in cursor.fetchall()]
            if "cliente_id" not in history_columns:
                conn.execute("ALTER TABLE chat_history ADD COLUMN cliente_id TEXT DEFAULT ''")

            cursor = conn.execute("PRAGMA table_info(chat_status)")
            status_columns = [c[1] for c in cursor.fetchall()]
            status_required = {
                "cliente_id": "TEXT DEFAULT ''",
                "last_processed_at": "TEXT",
                "last_message_id": "TEXT",
                "paused_until": "TEXT"
            }
            for col, definition in status_required.items():
                if col not in status_columns:
                    conn.execute(f"ALTER TABLE chat_status ADD COLUMN {col} {definition}")
            
            conn.commit()

    # --- MÉTODOS DE OPERACIÓN ---

    def obtener_cuentas(self, cliente_id=None):
        """Retorna las cuentas como dicts para que funcione .get() en la vista."""
        with self.get_connection() as conn:
            if cliente_id is not None:
                cursor = conn.execute("SELECT * FROM settings WHERE cliente_id = ?", (cliente_id,))
            else:
                cursor = conn.execute("SELECT * FROM settings")
            return [dict(row) for row in cursor.fetchall()]

    def obtener_conversaciones_recientes(self, cliente_id=None, limit=3):
        """Retorna las conversaciones recientes para mostrar en el dashboard."""
        with self.get_connection() as conn:
            query = (
                "SELECT ch.thread_id, ch.username, ch.mensaje_usuario, ch.respuesta_ia, ch.fecha, "
                "COALESCE(cs.status, 'ACTIVE') as status "
                "FROM chat_history ch "
                "LEFT JOIN chat_status cs ON ch.thread_id = cs.thread_id "
                "WHERE ch.fecha IN ("
                "  SELECT MAX(fecha) FROM chat_history GROUP BY thread_id"
                ") "
            )
            params = []
            if cliente_id is not None:
                query = (
                    "SELECT ch.thread_id, ch.username, ch.mensaje_usuario, ch.respuesta_ia, ch.fecha, "
                    "COALESCE(cs.status, 'ACTIVE') as status "
                    "FROM chat_history ch "
                    "LEFT JOIN chat_status cs ON ch.thread_id = cs.thread_id AND cs.cliente_id = ? "
                    "WHERE ch.cliente_id = ? AND ch.fecha IN ("
                    "  SELECT MAX(fecha) FROM chat_history WHERE cliente_id = ? GROUP BY thread_id"
                    ") "
                )
                params.extend([cliente_id, cliente_id, cliente_id])
            query += " ORDER BY ch.fecha DESC LIMIT ?"
            params.append(limit)
            cursor = conn.execute(query, tuple(params))
            return [
                {
                    "thread_id": row["thread_id"],
                    "title": row["username"],
                    "status": "Manual" if row["status"] == "PAUSED" else "Activa",
                    "last_message": row["mensaje_usuario"],
                    "timestamp": row["fecha"],
                }
                for row in cursor.fetchall()
            ]

    def obtener_conversacion_completa(self, thread_id, cliente_id=None):
        """Retorna todo el historial de una conversación por thread_id."""
        with self.get_connection() as conn:
            if cliente_id is not None:
                cursor = conn.execute(
                    "SELECT username, mensaje_usuario, respuesta_ia, fecha FROM chat_history "
                    "WHERE thread_id = ? AND cliente_id = ? ORDER BY fecha ASC",
                    (thread_id, cliente_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT username, mensaje_usuario, respuesta_ia, fecha FROM chat_history "
                    "WHERE thread_id = ? ORDER BY fecha ASC",
                    (thread_id,)
                )
            return [
                {
                    "title": row["username"],
                    "last_message": row["mensaje_usuario"],
                    "response": row["respuesta_ia"],
                    "timestamp": row["fecha"],
                }
                for row in cursor.fetchall()
            ]

    def agregar_cuenta(self, data, cliente_id=None):
        with self.get_connection() as conn:
            columns = [
                'insta_user', 'insta_pass', 'store_name', 'description', 'system_prompt',
                'context_type', 'schedule_start', 'schedule_end', 'proxy', 'session_data'
            ]
            values = [
                data['user'], data['pass'], data.get('store_name', ''), data.get('description', ''),
                data['prompt'], data['type'], data['start'], data['end'], data['proxy'], data.get('session_data', '')
            ]
            if cliente_id is not None:
                columns.insert(0, 'cliente_id')
                values.insert(0, cliente_id)
            columns_sql = ', '.join(columns)
            placeholders = ', '.join(['?'] * len(values))
            conn.execute(
                f"INSERT INTO settings ({columns_sql}) VALUES ({placeholders})",
                tuple(values)
            )
            conn.commit()

    def actualizar_estado_bot(self, account_id, estado):
        with self.get_connection() as conn:
            conn.execute("UPDATE settings SET bot_enabled = ? WHERE id = ?", (1 if estado else 0, account_id))
            conn.commit()

    def actualizar_log(self, account_id, mensaje):
        """Actualiza la línea de log en cian de la tarjeta."""
        with self.get_connection() as conn:
            conn.execute("UPDATE settings SET last_log = ? WHERE id = ?", (mensaje, account_id))
            conn.commit()

    def eliminar_cuenta(self, account_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE id = ?", (account_id,))
            conn.commit()

    def update_session_data(self, username, session_data, cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                conn.execute(
                    "UPDATE settings SET session_data = ? WHERE insta_user = ? AND cliente_id = ?",
                    (session_data, username, cliente_id)
                )
            else:
                conn.execute(
                    "UPDATE settings SET session_data = ? WHERE insta_user = ?",
                    (session_data, username)
                )
            conn.commit()

    def get_account_by_username(self, insta_user, cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                row = conn.execute(
                    "SELECT * FROM settings WHERE insta_user = ? AND cliente_id = ?",
                    (insta_user, cliente_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM settings WHERE insta_user = ?",
                    (insta_user,)
                ).fetchone()
            return dict(row) if row else None

    def get_thread_status(self, thread_id, cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                row = conn.execute(
                    "SELECT * FROM chat_status WHERE thread_id = ? AND cliente_id = ?",
                    (thread_id, cliente_id)
                ).fetchone()
            else:
                row = conn.execute("SELECT * FROM chat_status WHERE thread_id = ?", (thread_id,)).fetchone()
            return dict(row) if row else None

    def mark_thread_processed(self, thread_id, message_id, cliente_id=None):
        ahora = datetime.now().isoformat(sep=' ')
        with self.get_connection() as conn:
            if cliente_id is not None:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, cliente_id, status, last_processed_at, last_message_id) VALUES (?, ?, 'ACTIVE', ?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, last_processed_at = excluded.last_processed_at, last_message_id = excluded.last_message_id, status='ACTIVE'",
                    (thread_id, cliente_id, ahora, message_id)
                )
            else:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, status, last_processed_at, last_message_id) VALUES (?, 'ACTIVE', ?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET last_processed_at = excluded.last_processed_at, last_message_id = excluded.last_message_id, status='ACTIVE'",
                    (thread_id, ahora, message_id)
                )
            conn.commit()

    def pause_thread(self, thread_id, minutes=60, cliente_id=None):
        until = (datetime.now() + timedelta(minutes=minutes)).isoformat(sep=' ')
        with self.get_connection() as conn:
            if cliente_id is not None:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, cliente_id, status, paused_until) VALUES (?, ?, 'PAUSED', ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status='PAUSED', paused_until = excluded.paused_until",
                    (thread_id, cliente_id, until)
                )
            else:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, status, paused_until) VALUES (?, 'PAUSED', ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET status='PAUSED', paused_until = excluded.paused_until",
                    (thread_id, until)
                )
            conn.commit()

    def update_thread_status(self, thread_id, status='ACTIVE', cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, cliente_id, status) VALUES (?, ?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status = excluded.status",
                    (thread_id, cliente_id, status)
                )
            else:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, status) VALUES (?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET status = excluded.status",
                    (thread_id, status)
                )
            conn.commit()

db = LocalDBService()