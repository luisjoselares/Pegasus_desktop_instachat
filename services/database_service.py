import sqlite3
import os
import json
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
                    bot_role TEXT DEFAULT '',
                    business_name TEXT DEFAULT '',
                    business_data TEXT DEFAULT '',
                    operating_hours TEXT DEFAULT '',
                    inventory_path TEXT DEFAULT '',
                    structured_identity TEXT DEFAULT '',
                    country TEXT DEFAULT 'Venezuela',
                    language TEXT DEFAULT 'es',
                    currency_symbol TEXT DEFAULT 'Bs',
                    location TEXT DEFAULT '',
                    website TEXT DEFAULT '',
                    exchange_rate TEXT DEFAULT '',
                    proxy TEXT DEFAULT 'Auto',
                    schedule_start TEXT DEFAULT '08:00',
                    schedule_end TEXT DEFAULT '18:00',
                    context_type TEXT DEFAULT 'Vendedor de tienda',
                    payment_methods TEXT DEFAULT '[]',
                    payment_method_details TEXT DEFAULT '{}',
                    session_data TEXT DEFAULT '',
                    last_log TEXT DEFAULT 'Sistema listo'
                )
            """)
            try:
                conn.execute("ALTER TABLE settings ADD COLUMN payment_methods TEXT DEFAULT '[]'")
                conn.execute("ALTER TABLE settings ADD COLUMN payment_method_details TEXT DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass  # Las columnas ya existen, continuamos normal

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

            # 4. Tabla de Estado de Conversación por usuario
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_states (
                    ig_user_id TEXT PRIMARY KEY,
                    current_state TEXT DEFAULT 'CONSULTA',
                    temporal_context TEXT DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Tabla de Pedidos / Ventas Pendientes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id TEXT,
                    producto TEXT,
                    monto REAL,
                    referencia_pago TEXT,
                    datos_envio TEXT,
                    status TEXT DEFAULT 'PENDING_VALIDATION',
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS global_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Tabla de Auditoría de Ventas y Pagos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cuenta_id INTEGER,
                    cliente_nombre TEXT,
                    referencia TEXT,
                    banco TEXT,
                    monto_usd REAL,
                    estado TEXT DEFAULT 'PENDIENTE',
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. Tabla de Citas / Appointments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id TEXT,
                    nombre TEXT,
                    telefono TEXT,
                    fecha TEXT,
                    hora TEXT,
                    detalles TEXT,
                    status TEXT DEFAULT 'PENDING_VALIDATION',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. Tabla de Leads
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id TEXT,
                    nombre TEXT,
                    telefono TEXT,
                    email TEXT,
                    interes TEXT,
                    status TEXT DEFAULT 'PENDING_VALIDATION',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # --- MIGRACIÓN DE COLUMNAS (Para no perder datos existentes) ---
            cursor = conn.execute("PRAGMA table_info(settings)")
            columns = [c[1] for c in cursor.fetchall()]
            
            required_cols = {
                "cliente_id": "TEXT DEFAULT ''",
                "store_name": "TEXT DEFAULT ''",
                "description": "TEXT DEFAULT ''",
                "system_prompt": "TEXT DEFAULT ''",
                "bot_enabled": "INTEGER DEFAULT 0",
                "bot_role": "TEXT DEFAULT ''",
                "business_name": "TEXT DEFAULT ''",
                "business_data": "TEXT DEFAULT ''",
                "operating_hours": "TEXT DEFAULT ''",
                "inventory_path": "TEXT DEFAULT ''",
                "structured_identity": "TEXT DEFAULT ''",
                "country": "TEXT DEFAULT 'Venezuela'",
                "language": "TEXT DEFAULT 'es'",
                "currency_symbol": "TEXT DEFAULT 'Bs'",
                "location": "TEXT DEFAULT ''",
                "website": "TEXT DEFAULT ''",
                "exchange_rate": "TEXT DEFAULT ''",
                "payment_methods": "TEXT DEFAULT '[]'",
                "payment_method_details": "TEXT DEFAULT ''",
                "info_eventos": "TEXT DEFAULT ''",
                "proxy": "TEXT DEFAULT 'Auto'",
                "schedule_start": "TEXT DEFAULT '08:00'",
                "schedule_end": "TEXT DEFAULT '18:00'",
                "context_type": "TEXT DEFAULT 'Vendedor de tienda'",
                "bot_mission": "TEXT DEFAULT 'Ventas'",
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

    def get_global_setting(self, key, default=""):
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM global_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def set_global_setting(self, key, value):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO global_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()

    def insert_sale(self, cuenta_id, cliente_nombre, referencia, banco, monto_usd, estado="PENDIENTE"):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO sales (cuenta_id, cliente_nombre, referencia, banco, monto_usd, estado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cuenta_id, cliente_nombre, referencia, banco, monto_usd, estado))
            conn.commit()

    def get_sales(self):
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sales ORDER BY fecha DESC")
            return [dict(row) for row in cursor.fetchall()]

    # --- MÉTODOS DE OPERACIÓN ---


    def _normalize_role_key(self, role):
        if not role:
            return 'GENERICO'
        role_key = role.strip().upper()
        if role_key.startswith('VENDEDOR'):
            return 'VENDEDOR'
        if 'CREATIVO' in role_key:
            return 'CREATIVO'
        if 'SOPORTE' in role_key:
            return 'SOPORTE'
        if 'CONCILIADOR' in role_key:
            return 'CONCILIADOR'
        return 'GENERICO'

    def _normalize_account_role(self, account):
        if not account:
            return account
        raw_role = account.get('bot_role') or account.get('context_type') or ''
        normalized_role = self._normalize_role_key(raw_role)
        account['bot_role'] = normalized_role
        account['context_type'] = account.get('context_type') or raw_role or normalized_role

        raw_payment_methods = account.get('payment_methods', '[]')
        if isinstance(raw_payment_methods, str):
            try:
                account['payment_methods'] = json.loads(raw_payment_methods)
            except Exception:
                account['payment_methods'] = [item.strip() for item in raw_payment_methods.split(',') if item.strip()]

        raw_payment_details = account.get('payment_method_details', '')
        if isinstance(raw_payment_details, str):
            try:
                account['payment_method_details'] = json.loads(raw_payment_details)
            except Exception:
                account['payment_method_details'] = {}
        return account

    def obtener_cuentas(self, cliente_id=None):
        """Retorna las cuentas como dicts para que funcione .get() en la vista."""
        with self.get_connection() as conn:
            if cliente_id is not None:
                cursor = conn.execute("SELECT * FROM settings WHERE cliente_id = ?", (cliente_id,))
            else:
                cursor = conn.execute("SELECT * FROM settings")
            return [self._normalize_account_role(dict(row)) for row in cursor.fetchall()]

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

    def obtener_ultimos_mensajes(self, thread_id, cliente_id=None, limit=10):
        """Retorna los últimos mensajes de un hilo específico para usar en el contexto de la IA."""
        if not thread_id:
            return []
        with self.get_connection() as conn:
            if cliente_id is not None:
                cursor = conn.execute(
                    "SELECT username, mensaje_usuario, respuesta_ia, fecha FROM chat_history "
                    "WHERE thread_id = ? AND cliente_id = ? ORDER BY fecha DESC LIMIT ?",
                    (thread_id, cliente_id, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT username, mensaje_usuario, respuesta_ia, fecha FROM chat_history "
                    "WHERE thread_id = ? ORDER BY fecha DESC LIMIT ?",
                    (thread_id, limit)
                )
            return [
                {
                    "username": row["username"],
                    "mensaje_usuario": row["mensaje_usuario"],
                    "respuesta_ia": row["respuesta_ia"],
                    "fecha": row["fecha"],
                }
                for row in cursor.fetchall()
            ]

    def obtener_chats_activos(self, cliente_id=None, limit=10):
        """Retorna los chats activos que el bot ha detectado, con su estado actual."""
        with self.get_connection() as conn:
            if cliente_id is not None:
                query = (
                    "SELECT ch.thread_id, ch.username, ch.mensaje_usuario, ch.respuesta_ia, ch.fecha, "
                    "COALESCE(cs.status, 'ACTIVE') as status, cs.paused_until "
                    "FROM chat_history ch "
                    "LEFT JOIN chat_status cs ON ch.thread_id = cs.thread_id AND cs.cliente_id = ? "
                    "WHERE ch.cliente_id = ? AND ch.fecha IN ("
                    "  SELECT MAX(fecha) FROM chat_history WHERE cliente_id = ? GROUP BY thread_id"
                    ") "
                    "ORDER BY ch.fecha DESC LIMIT ?"
                )
                params = (cliente_id, cliente_id, cliente_id, limit)
            else:
                query = (
                    "SELECT ch.thread_id, ch.username, ch.mensaje_usuario, ch.respuesta_ia, ch.fecha, "
                    "COALESCE(cs.status, 'ACTIVE') as status, cs.paused_until "
                    "FROM chat_history ch "
                    "LEFT JOIN chat_status cs ON ch.thread_id = cs.thread_id "
                    "WHERE ch.fecha IN ("
                    "  SELECT MAX(fecha) FROM chat_history GROUP BY thread_id"
                    ") "
                    "ORDER BY ch.fecha DESC LIMIT ?"
                )
                params = (limit,)
            cursor = conn.execute(query, params)
            return [
                {
                    "thread_id": row["thread_id"],
                    "title": row["username"],
                    "status": "Manual" if row["status"] == "PAUSED" else "Activa",
                    "current_state": row["status"] != "PAUSED",
                    "last_message": row["mensaje_usuario"],
                    "timestamp": row["fecha"],
                    "paused_until": row["paused_until"],
                }
                for row in cursor.fetchall()
            ]

    def agregar_cuenta(self, data, cliente_id=None):
        with self.get_connection() as conn:
            structured_identity = data.get('structured_identity', '')
            if isinstance(structured_identity, dict):
                structured_identity = json.dumps(structured_identity)

            columns = [
                'insta_user', 'insta_pass', 'store_name', 'description', 'system_prompt',
                'bot_role', 'bot_mission', 'business_name', 'business_data', 'operating_hours', 'inventory_path', 'structured_identity',
                'country', 'language', 'currency_symbol',
                'payment_methods', 'payment_method_details', 'info_eventos',
                'location', 'website', 'exchange_rate',
                'context_type', 'schedule_start', 'schedule_end', 'proxy', 'session_data'
            ]
            inventory_path = data.get('inventory_path', '') or ''
            if inventory_path:
                inventory_path = os.path.abspath(inventory_path)

            values = [
                data['user'], data['pass'], data.get('store_name', ''), data.get('description', ''),
                data['prompt'], data.get('bot_role', ''), data.get('bot_mission', 'Ventas'), data.get('business_name', ''), data.get('business_data', ''),
                data.get('operating_hours', ''), inventory_path, structured_identity,
                data.get('country', 'Venezuela'), data.get('language', 'es'), data.get('currency_symbol', 'Bs'),
                json.dumps(data.get('payment_methods', [])), json.dumps(data.get('payment_method_details', {})), data.get('info_eventos', ''),
                data.get('location', ''), data.get('website', ''), data.get('exchange_rate', ''),
                data['type'], data['start'], data['end'], data['proxy'], data.get('session_data', '')
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

    def actualizar_estado_bot(self, account_id, estado, cliente_id=None):
        self.update_settings(account_id, {'bot_enabled': 1 if estado else 0}, cliente_id)

    def actualizar_contexto(self, account_id, prompt, cliente_id=None):
        self.update_settings(account_id, {'system_prompt': prompt}, cliente_id)

    def update_settings(self, account_id, changes, cliente_id=None):
        if not changes:
            return 0

        payload = dict(changes)
        if 'structured_identity' in payload and isinstance(payload['structured_identity'], dict):
            payload['structured_identity'] = json.dumps(payload['structured_identity'])
        if 'payment_methods' in payload and isinstance(payload['payment_methods'], list):
            payload['payment_methods'] = json.dumps(payload['payment_methods'])
        if 'payment_method_details' in payload and isinstance(payload['payment_method_details'], dict):
            payload['payment_method_details'] = json.dumps(payload['payment_method_details'])

        allowed = {
            'bot_enabled', 'system_prompt', 'insta_pass', 'store_name',
            'description', 'bot_role', 'bot_mission', 'business_name', 'business_data',
            'operating_hours', 'inventory_path', 'structured_identity',
            'country', 'language', 'currency_symbol',
            'payment_methods', 'payment_method_details', 'info_eventos',
            'location', 'website', 'exchange_rate',
            'context_type', 'schedule_start', 'schedule_end',
            'proxy', 'session_data', 'last_log'
        }
        entries = [(col, payload[col]) for col in payload if col in allowed]
        if not entries:
            return 0

        columns = ', '.join(f"{col} = ?" for col, _ in entries)
        values = [1 if col == 'bot_enabled' and isinstance(val, bool) else val for col, val in entries]

        if cliente_id is not None:
            sql = f"UPDATE settings SET {columns} WHERE id = ? AND cliente_id = ?"
            values.extend([account_id, cliente_id])
        else:
            sql = f"UPDATE settings SET {columns} WHERE id = ?"
            values.append(account_id)

        with self.get_connection() as conn:
            cursor = conn.execute(sql, tuple(values))
            conn.commit()
            return cursor.rowcount

    def get_settings(self, account_id=None, cliente_id=None):
        """Retorna la configuración de cuenta, incluyendo los campos nuevos.

        Si no existen los campos nuevos en una cuenta antigua, se devuelven valores por defecto.
        """
        if account_id is not None:
            account = self.get_account_by_id(account_id, cliente_id)
            if account is None:
                return None
            account.setdefault('bot_role', '')
            account.setdefault('bot_mission', 'Ventas')
            account.setdefault('business_name', '')
            account.setdefault('business_data', '')
            account.setdefault('operating_hours', '')
            account.setdefault('inventory_path', '')
            account.setdefault('structured_identity', '')
            account.setdefault('country', 'Venezuela')
            account.setdefault('language', 'es')
            account.setdefault('currency_symbol', 'Bs')
            account.setdefault('payment_methods', [])
            account.setdefault('payment_method_details', {})
            account.setdefault('info_eventos', '')
            account.setdefault('location', '')
            account.setdefault('website', '')
            account.setdefault('exchange_rate', '')
            return account

        cuentas = self.obtener_cuentas(cliente_id)
        for cuenta in cuentas:
            cuenta.setdefault('bot_role', '')
            cuenta.setdefault('bot_mission', 'Ventas')
            cuenta.setdefault('business_name', '')
            cuenta.setdefault('business_data', '')
            cuenta.setdefault('operating_hours', '')
            cuenta.setdefault('inventory_path', '')
            cuenta.setdefault('structured_identity', '')
            cuenta.setdefault('country', 'Venezuela')
            cuenta.setdefault('language', 'es')
            cuenta.setdefault('currency_symbol', 'Bs')
            cuenta.setdefault('payment_methods', [])
            cuenta.setdefault('payment_method_details', {})
            cuenta.setdefault('info_eventos', '')
            cuenta.setdefault('location', '')
            cuenta.setdefault('website', '')
            cuenta.setdefault('exchange_rate', '')
        return cuentas

    def save_settings(self, account_id, changes, cliente_id=None):
        """Guarda cambios en la configuración de cuenta, respetando campos nuevos y antiguos."""
        return self.update_settings(account_id, changes, cliente_id)

    def save_account(self, account_id, data, cliente_id=None):
        """Inserta o actualiza una cuenta según si account_id ya existe."""
        if account_id:
            return self.update_settings(account_id, data, cliente_id)
        self.agregar_cuenta(data, cliente_id)
        return 1

    def get_account_by_id(self, account_id, cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                row = conn.execute(
                    "SELECT * FROM settings WHERE id = ? AND cliente_id = ?",
                    (account_id, cliente_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM settings WHERE id = ?",
                    (account_id,)
                ).fetchone()
            account = dict(row) if row else None
            return self._normalize_account_role(account)

    def get_account_state(self, account_id, cliente_id=None):
        account = self.get_account_by_id(account_id, cliente_id)
        if not account:
            return None

        target_cliente_id = cliente_id if cliente_id is not None else account.get('cliente_id', '')
        now = datetime.now()
        paused_threads = []

        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT status, paused_until FROM chat_status WHERE cliente_id = ?",
                (target_cliente_id,)
            ).fetchall()

        for row in rows:
            status = row['status']
            paused_until = row['paused_until']
            active = False
            if paused_until:
                try:
                    until = datetime.fromisoformat(paused_until)
                    if now < until:
                        active = True
                except Exception:
                    active = status in ('PAUSED', 'MANUAL')
            elif status in ('PAUSED', 'MANUAL'):
                active = True

            if active:
                paused_threads.append({
                    'status': status,
                    'paused_until': paused_until,
                })

        return {
            'bot_enabled': bool(account.get('bot_enabled')),
            'pause_active': bool(paused_threads),
            'paused_threads': paused_threads,
            'cliente_id': target_cliente_id,
        }

    def clear_account_pauses(self, account_id, cliente_id=None):
        account = self.get_account_by_id(account_id, cliente_id)
        if not account:
            return 0

        target_cliente_id = cliente_id if cliente_id is not None else account.get('cliente_id', '')
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE chat_status SET status = 'ACTIVE', paused_until = NULL "
                "WHERE cliente_id = ? AND status IN ('PAUSED', 'MANUAL')",
                (target_cliente_id,)
            )
            conn.commit()
            return cursor.rowcount

    def actualizar_log(self, account_id, mensaje):
        """Actualiza la línea de log en cian de la tarjeta."""
        with self.get_connection() as conn:
            conn.execute("UPDATE settings SET last_log = ? WHERE id = ?", (mensaje, account_id))
            conn.commit()

    def eliminar_cuenta(self, account_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE id = ?", (account_id,))
            conn.commit()

    def limpiar_cuentas_huerfanas(self, cliente_id=None):
        """Elimina cuentas locales sin cliente válido o sin cliente_id asignado."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM settings WHERE cliente_id IS NULL OR cliente_id = ''")
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
            account = dict(row) if row else None
            return self._normalize_account_role(account)

    def get_user_state(self, ig_user_id):
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_states WHERE ig_user_id = ?",
                (ig_user_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_user_state(self, ig_user_id, state, context):
        temporal_context = json.dumps(context) if isinstance(context, (dict, list)) else str(context or '{}')
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO conversation_states (ig_user_id, current_state, temporal_context, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(ig_user_id) DO UPDATE SET current_state = excluded.current_state, temporal_context = excluded.temporal_context, updated_at = CURRENT_TIMESTAMP",
                (ig_user_id, state or 'CONSULTA', temporal_context)
            )
            conn.commit()
            return cursor.rowcount

    def insert_order(self, cliente_id, producto, monto, ref, envio):
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO orders (cliente_id, producto, monto, referencia_pago, datos_envio, status) VALUES (?, ?, ?, ?, ?, 'PENDING_VALIDATION')",
                (cliente_id, producto, monto, ref, envio)
            )
            conn.commit()
            return cursor.lastrowid

    def insert_appointment(self, cliente_id, nombre, telefono, fecha, hora, detalles=''):
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO appointments (cliente_id, nombre, telefono, fecha, hora, detalles, status) VALUES (?, ?, ?, ?, ?, ?, 'PENDING_VALIDATION')",
                (cliente_id, nombre, telefono, fecha, hora, detalles)
            )
            conn.commit()
            return cursor.lastrowid

    def insert_lead(self, cliente_id, nombre, telefono, email, interes=''):
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO leads (cliente_id, nombre, telefono, email, interes, status) VALUES (?, ?, ?, ?, ?, 'PENDING_VALIDATION')",
                (cliente_id, nombre, telefono, email, interes)
            )
            conn.commit()
            return cursor.lastrowid

    def get_pending_orders(self):
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM orders WHERE status = 'PENDING_VALIDATION' ORDER BY fecha ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_order_status(self, order_id, status):
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id)
            )
            conn.commit()
            return cursor.rowcount

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

    def pause_thread(self, thread_id, minutes=60, cliente_id=None, status='PAUSED'):
        until = (datetime.now() + timedelta(minutes=minutes)).isoformat(sep=' ')
        with self.get_connection() as conn:
            if cliente_id is not None:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, cliente_id, status, paused_until) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status = excluded.status, paused_until = excluded.paused_until",
                    (thread_id, cliente_id, status, until)
                )
            else:
                conn.execute(
                    "INSERT INTO chat_status (thread_id, status, paused_until) VALUES (?, ?, ?) "
                    "ON CONFLICT(thread_id) DO UPDATE SET status = excluded.status, paused_until = excluded.paused_until",
                    (thread_id, status, until)
                )
            conn.commit()

    def update_thread_status(self, thread_id, status='ACTIVE', cliente_id=None):
        with self.get_connection() as conn:
            if cliente_id is not None:
                if status == 'ACTIVE':
                    conn.execute(
                        "INSERT INTO chat_status (thread_id, cliente_id, status, paused_until) VALUES (?, ?, ?, NULL) "
                        "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status = excluded.status, paused_until = NULL",
                        (thread_id, cliente_id, status)
                    )
                else:
                    conn.execute(
                        "INSERT INTO chat_status (thread_id, cliente_id, status) VALUES (?, ?, ?) "
                        "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status = excluded.status",
                        (thread_id, cliente_id, status)
                    )
            else:
                if status == 'ACTIVE':
                    conn.execute(
                        "INSERT INTO chat_status (thread_id, status, paused_until) VALUES (?, ?, NULL) "
                        "ON CONFLICT(thread_id) DO UPDATE SET status = excluded.status, paused_until = NULL",
                        (thread_id, status)
                    )
                else:
                    conn.execute(
                        "INSERT INTO chat_status (thread_id, status) VALUES (?, ?) "
                        "ON CONFLICT(thread_id) DO UPDATE SET status = excluded.status",
                        (thread_id, status)
                    )
            conn.commit()

db = LocalDBService()