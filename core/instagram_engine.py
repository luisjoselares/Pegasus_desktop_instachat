import sys
import os
import time
import random
import logging
import json
import requests
from collections import deque
from datetime import datetime, timedelta
from types import SimpleNamespace
from urllib3.exceptions import MaxRetryError, ResponseError

# Parche de compatibilidad MoviePy necesario para el escritorio
try:
    import moviepy
    import moviepy.video.io.VideoFileClip 
    sys.modules['moviepy.editor'] = moviepy
except ImportError:
    pass

from instagrapi import Client
import instagrapi.extractors as extractors
import instagrapi.mixins.direct as direct_mixin
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired, RateLimitError, ClientConnectionError, UserNotFound, DirectThreadNotFound
from services.database_service import db
from core.ai_engine import AIService, HANDOFF_PHRASE

class InstagramService:
    def __init__(self):
        self.cl = Client()
        self.ai = AIService()
        self.ai.set_trial_status_callback(self._on_trial_status)
        self.is_running = False
        self.session_file = None
        self.log_callback = None
        self.handoff_callback = None
        self.rescue_callback = None
        self.last_profile_error = None
        self.security_service = None
        self.initial_session_data = None
        self.bot_sent_messages = deque(maxlen=1000)
        self.bot_sent_message_ids = set()
        self.muted_threads = {}
        self._last_rescue_check = None
        self.cliente_id = None
        self.session_ready_callback = None
        self._chat_switch_delay = (1.0, 3.0)
        self._response_delay = (10.0, 18.0)
        self._idle_cycle_delay = (6.0, 12.0)
        os.makedirs("sessions", exist_ok=True)
        self._patch_instagrapi_direct_thread_extractor()

    def _patch_instagrapi_direct_thread_extractor(self):
        try:
            original_extract_direct_thread = extractors.extract_direct_thread

            def safe_extract_direct_thread(data):
                if isinstance(data, dict):
                    defaults = {
                        "admin_user_ids": data.get("admin_user_ids", []),
                        "muted": data.get("muted", False),
                        "named": data.get("named", False),
                        "canonical": data.get("canonical", False),
                        "pending": data.get("pending", False),
                        "archived": data.get("archived", False),
                        "thread_type": data.get("thread_type", ""),
                        "thread_title": data.get("thread_title", ""),
                        "folder": data.get("folder", 0),
                        "vc_muted": data.get("vc_muted", False),
                        "is_group": data.get("is_group", False),
                        "mentions_muted": data.get("mentions_muted", False),
                        "approval_required_for_new_members": data.get("approval_required_for_new_members", False),
                        "input_mode": data.get("input_mode", 0),
                        "business_thread_folder": data.get("business_thread_folder", 0),
                        "read_state": data.get("read_state", 0),
                        "is_close_friend_thread": data.get("is_close_friend_thread", False),
                        "assigned_admin_id": data.get("assigned_admin_id", 0),
                        "shh_mode_enabled": data.get("shh_mode_enabled", False),
                        "last_seen_at": data.get("last_seen_at", {}),
                    }
                    for key, value in defaults.items():
                        if key not in data:
                            data[key] = value
                return original_extract_direct_thread(data)

            if getattr(extractors.extract_direct_thread, "_pegasus_patched", False) is not True:
                safe_extract_direct_thread._pegasus_patched = True
                extractors.extract_direct_thread = safe_extract_direct_thread

            if getattr(direct_mixin.extract_direct_thread, "_pegasus_patched", False) is not True:
                direct_mixin.extract_direct_thread = safe_extract_direct_thread
        except Exception:
            pass

    def set_cliente_id(self, cliente_id):
        self.cliente_id = cliente_id
        if hasattr(self.ai, 'set_cliente_id'):
            self.ai.set_cliente_id(cliente_id)

    def get_average_next_chat_delay(self):
        return (self._chat_switch_delay[0] + self._chat_switch_delay[1]) / 2

    def get_next_chat_delay_range(self):
        return self._chat_switch_delay

    def _session_file_for_user(self, user):
        safe_user = "".join(c for c in user if c.isalnum() or c in "_-.").lower()
        if not safe_user:
            safe_user = "default"
        return f"sessions/insta_session_{safe_user}.json"

    def set_callback(self, callback_func):
        self.log_callback = callback_func

    def set_handoff_callback(self, callback_func):
        self.handoff_callback = callback_func

    def set_rescue_callback(self, callback_func):
        self.rescue_callback = callback_func

    def set_session_ready_callback(self, callback_func):
        self.session_ready_callback = callback_func

    def set_licencia_id(self, licencia_id):
        self.ai.set_licencia_id(licencia_id)

    def set_trial_status_callback(self, callback_func):
        self.ai.set_trial_status_callback(callback_func)

    def _ui_log(self, mensaje):
        logging.info(mensaje)
        if self.log_callback:
            self.log_callback(mensaje)

    def _on_trial_status(self, restantes):
        if isinstance(restantes, dict):
            mensajes = restantes.get('mensajes', 'N/A')
            tokens = restantes.get('tokens', 'N/A')
            self._ui_log(f"[TRIAL] Mensajes restantes: {mensajes} | Tokens restantes: {tokens}")
        else:
            self._ui_log(f"[TRIAL] Mensajes restantes: {restantes}")

    def _parse_time_string(self, value):
        if not value:
            return None
        try:
            text = str(value).strip()
            if text == "24:00":
                return datetime.strptime("00:00", "%H:%M").time()
            return datetime.strptime(text, "%H:%M").time()
        except Exception:
            return None

    def _parse_structured_identity(self, raw_value):
        if not raw_value:
            return {}
        if isinstance(raw_value, dict):
            return raw_value
        try:
            return json.loads(raw_value)
        except Exception:
            return {}

    def _build_account_system_prompt(self, account_settings):
        prompt_parts = []
        if account_settings is None:
            return None

        base = account_settings.get('system_prompt')
        if base:
            prompt_parts.append(base)
        else:
            prompt_parts.append(
                "Eres Pegasus, un asistente profesional de ventas y atención al cliente. "
                "Responde como el encargado digital de la tienda y no admitas ser un bot."
            )

        role = account_settings.get('bot_role')
        if role:
            prompt_parts.append(f"Tu rol asignado es: {role}.")

        business_name = account_settings.get('business_name')
        if business_name:
            prompt_parts.append(f"Representas a la tienda: {business_name}.")

        bot_name = account_settings.get('assistant_name') or account_settings.get('bot_name')
        if bot_name:
            prompt_parts.append(f"El asistente se presenta como {bot_name}.")

        whatsapp_number = account_settings.get('whatsapp_number') or account_settings.get('whatsapp_contacto')
        if whatsapp_number:
            prompt_parts.append(f"Contacto de WhatsApp de la tienda: {whatsapp_number}.")

        business_data = account_settings.get('business_data')
        if business_data:
            prompt_parts.append(f"Información operativa relevante: {business_data}.")

        location = account_settings.get('location') or account_settings.get('ubicacion', '')
        if location:
            prompt_parts.append(f"Ubicación física o zona de atención: {location}.")
        else:
            if whatsapp_number:
                prompt_parts.append(
                    f"Si el cliente pregunta por la ubicación física, responde: No tenemos tienda física por ahora, pero atendemos de forma digital por WhatsApp {whatsapp_number}."
                )
            else:
                prompt_parts.append(
                    "Si el cliente pregunta por la ubicación física, responde: No tenemos tienda física por ahora, pero atendemos de forma digital por WhatsApp."
                )

        website = account_settings.get('website', '')
        if website:
            prompt_parts.append(f"Sitio web o catálogo online: {website}.")

        structured = self._parse_structured_identity(account_settings.get('structured_identity'))
        if structured:
            if structured.get('name'):
                prompt_parts.append(f"Nombre de la ficha: {structured.get('name')}." )
            if structured.get('bio'):
                prompt_parts.append(f"Bio resumida: {structured.get('bio')}." )
            if structured.get('style'):
                prompt_parts.append(f"Estilo de comunicación: {structured.get('style')}." )

        operating_hours = account_settings.get('operating_hours')
        if operating_hours:
            prompt_parts.append(f"Horario operativo registrado: {operating_hours}.")

        if account_settings.get('schedule_start') and account_settings.get('schedule_end'):
            prompt_parts.append(
                f"El horario de atención oficial es de {account_settings.get('schedule_start')} a {account_settings.get('schedule_end')}.")

        proxy = account_settings.get('proxy')
        if proxy and proxy != 'Auto':
            prompt_parts.append(f"Configuración de proxy: {proxy}.")

        return "\n".join(prompt_parts)

    def _in_business_hours(self, start_time, end_time):
        start = self._parse_time_string(start_time)
        end = self._parse_time_string(end_time)
        now = datetime.now().time()
        if not start or not end:
            return True
        if start == end:
            return True
        if start < end:
            return start <= now < end
        return now >= start or now < end

    def _get_message_timestamp(self, msg):
        timestamp = getattr(msg, 'timestamp', None) or getattr(msg, 'client_timestamp', None) or getattr(msg, 'created_at', None)
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        if isinstance(timestamp, str):
            text = timestamp.strip()
            if text.isdigit():
                try:
                    value = int(text)
                    if value > 1_000_000_000_000_000:
                        value /= 1_000_000
                    elif value > 1_000_000_000_000:
                        value /= 1_000
                    return datetime.fromtimestamp(value)
                except Exception:
                    pass
            try:
                value = float(text)
                return datetime.fromtimestamp(value)
            except Exception:
                pass
            try:
                return datetime.fromisoformat(text)
            except Exception:
                try:
                    return datetime.fromisoformat(text.replace('Z', '+00:00'))
                except Exception:
                    pass
        return None

    def _get_time_context(self, thread_status):
        if not thread_status:
            return "NEW_SESSION"
        last_processed = thread_status.get('last_processed_at')
        if not last_processed:
            return "NEW_SESSION"
        try:
            last_time = datetime.fromisoformat(str(last_processed))
        except Exception:
            try:
                last_time = datetime.fromisoformat(str(last_processed).replace('Z', '+00:00'))
            except Exception:
                return "NEW_SESSION"
        delta = datetime.now() - last_time
        if delta < timedelta(hours=4):
            return "CONTINUOUS"
        if delta <= timedelta(days=7):
            return "RE_ENCOUNTER"
        return "NEW_SESSION"

    def _get_message_id(self, msg):
        return getattr(msg, 'id', None) or getattr(msg, 'item_id', None) or getattr(msg, 'client_context', None) or str(getattr(msg, 'timestamp', ''))

    def _add_sent_message(self, message_id):
        if not message_id:
            return
        if len(self.bot_sent_messages) >= self.bot_sent_messages.maxlen:
            oldest = self.bot_sent_messages.popleft()
            self.bot_sent_message_ids.discard(oldest)
        self.bot_sent_messages.append(message_id)
        self.bot_sent_message_ids.add(message_id)

    def _was_bot_message(self, message_id):
        return message_id in self.bot_sent_message_ids

    def _detect_implicit_handoff(self, thread, username):
        last_msg = thread.messages[0] if getattr(thread, 'messages', None) else None
        if not last_msg:
            return False
        if str(getattr(last_msg, 'user_id', '')) != str(self.cl.user_id):
            return False
        message_id = self._get_message_id(last_msg)
        if not message_id:
            return False

        thread_status = db.get_thread_status(thread.id, self.cliente_id)
        if thread_status and thread_status.get('last_message_id') == message_id:
            return False

        if not self._was_bot_message(message_id):
            self._ui_log(f"[HANDOFF] Intervención humana detectada en el chat con @{username}. Bot silenciado por 12h.")
            if self.handoff_callback:
                self.handoff_callback(thread.id, username)
            self._pause_thread(thread.id, username)
            return True
        return False

    def _pause_thread(self, thread_id, username=None):
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_status (thread_id, cliente_id, status, last_manual_at) VALUES (?, ?, 'PAUSED', ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET cliente_id = excluded.cliente_id, status='PAUSED', last_manual_at=excluded.last_manual_at",
                (thread_id, self.cliente_id, ahora)
            )
            conn.commit()
        self.muted_threads[thread_id] = ahora
        self._ui_log(f"[HANDOFF] Hilo {thread_id} silenciado mientras el humano participa.")

    def _reactivate_thread(self, thread_id):
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE chat_status SET status='ACTIVE', paused_until=NULL WHERE thread_id = ?",
                (thread_id,)
            )
            conn.commit()

    def _verificar_abandono_humano(self):
        ahora = datetime.now()
        if self._last_rescue_check and (ahora - self._last_rescue_check) < timedelta(minutes=5):
            return
        self._last_rescue_check = ahora

        with db.get_connection() as conn:
            if self.cliente_id is not None:
                cursor = conn.execute(
                    "SELECT thread_id, last_manual_at, paused_until FROM chat_status WHERE status = 'PAUSED' AND cliente_id = ?",
                    (self.cliente_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT thread_id, last_manual_at, paused_until FROM chat_status WHERE status = 'PAUSED'"
                )
            paused_rows = cursor.fetchall()

        for row in paused_rows:
            thread_id = row['thread_id']
            last_manual_at = row['last_manual_at'] if 'last_manual_at' in row.keys() else None
            try:
                thread_fetcher = getattr(self.cl, 'direct_thread', None)
                if callable(thread_fetcher):
                    try:
                        thread = self.cl.direct_thread(thread_id)
                    except DirectThreadNotFound as e:
                        logging.warning(f"[RESCATE] Hilo {thread_id} no encontrado al verificar abandono humano: {e}")
                        continue
                    except Exception as e:
                        logging.warning(f"[RESCATE] Error al obtener hilo {thread_id}: {e}")
                        continue
                else:
                    thread = None

                if not thread:
                    continue

                last_msg = thread.messages[0] if getattr(thread, 'messages', None) else None
                if not last_msg:
                    continue

                sender_id = str(getattr(last_msg, 'user_id', ''))
                if sender_id == str(self.cl.user_id):
                    continue

                timestamp = self._get_message_timestamp(last_msg)
                if not timestamp:
                    continue

                human_inactive = False
                if last_manual_at:
                    try:
                        manual_ts = datetime.fromisoformat(last_manual_at)
                        if (ahora - manual_ts) > timedelta(minutes=10):
                            human_inactive = True
                    except Exception:
                        pass

                if not human_inactive and sender_id != str(self.cl.user_id):
                    if (ahora - timestamp) > timedelta(minutes=10):
                        human_inactive = True

                if human_inactive:
                    username = thread.users[0].username if getattr(thread, 'users', None) else 'desconocido'
                    self._ui_log(f"[RESCATE] Inactividad humana detectada (>10 min). Bot reactivado para el chat con @{username}.")
                    self._reactivate_thread(thread_id)
                    self.muted_threads.pop(thread_id, None)
                    if self.rescue_callback:
                        self.rescue_callback(thread_id, username)
            except Exception as e:
                logging.warning(f"Error en verificación de abandono humano para hilo {thread_id}: {e}")

    def _should_skip_thread(self, thread, last_msg, account_settings, thread_status):
        message_ts = self._get_message_timestamp(last_msg)
        if message_ts:
            age = datetime.now() - message_ts
            if age > timedelta(hours=24):
                days = age.days
                if thread.id and last_msg:
                    db.mark_thread_processed(thread.id, self._get_message_id(last_msg), cliente_id=self.cliente_id)
                self._ui_log(f"🧹 Ignorando mensaje antiguo ({days} días de antigüedad).")
                if account_settings:
                    db.actualizar_log(account_settings['id'], f"🧹 Ignorando mensaje antiguo ({days} días).")
                return True

        if thread_status and thread_status.get('last_message_id') == self._get_message_id(last_msg):
            self._ui_log("⏳ El hilo ya fue procesado para este mensaje. Esperando actualización de lectura.")
            return True

        return False

    def _is_manual_intervention(self, thread, last_msg, thread_status):
        if not thread_status or not thread_status.get('last_processed_at'):
            return False
        if thread_status.get('paused_until'):
            try:
                until = datetime.fromisoformat(thread_status['paused_until'])
                if datetime.now() < until:
                    return True
            except Exception:
                pass
        return False

    def _check_local_ip_security(self, account_settings):
        if not account_settings:
            return True
        proxy = account_settings.get('proxy', 'Auto')
        if proxy and proxy.lower() != 'auto':
            self._ui_log(f"🔒 Seguridad de IP: usando proxy personalizado ({proxy}).")
        else:
            self._ui_log("🔒 Seguridad de IP local confirmada: no se fuerza salida a través de proxy.")
        return True

    def _update_account_log(self, account_id, mensaje):
        if account_id:
            db.actualizar_log(account_id, mensaje)

    def login(self, user, pw, session_data_encrypted=None, security_service=None):
        """Lógica de login con soporte de sesión cifrada y fallback a login normal."""
        if not user or not pw:
            self._ui_log("❌ Error: Faltan credenciales en la interfaz.")
            return None

        self.session_file = self._session_file_for_user(user)
        security = security_service or self.security_service

        def validate_session():
            try:
                self.cl.get_timeline_feed()
                self._ui_log(f"✅ Sesión activa validada para @{user}.")
                return True
            except Exception as e:
                self._ui_log(f"⚠️ Sesión no válida o expirada: {e}")
                return False

        # 1. Intentar cargar sesión en memoria desde session_data_encrypted
        if session_data_encrypted and security:
            decrypted = security.decrypt(session_data_encrypted)
            if decrypted:
                try:
                    self.cl.set_settings(decrypted)
                    try:
                        self.cl.login_by_sessionid()
                    except Exception:
                        pass
                    if validate_session():
                        session_data = self.cl.get_settings()
                        self._ui_log(f"✅ Sesión restaurada desde datos cifrados para @{user}.")
                        if self.session_ready_callback:
                            try:
                                self.session_ready_callback(session_data)
                            except Exception:
                                pass
                        return session_data
                except Exception as e:
                    self._ui_log(f"⚠️ No se pudo restaurar la sesión cifrada: {e}")

        # 2. Intentar cargar sesión desde archivo local como respaldo
        if os.path.exists(self.session_file):
            try:
                self.cl.load_settings(self.session_file)
                if validate_session():
                    session_data = self.cl.get_settings()
                    self._ui_log(f"✅ Sesión recuperada exitosamente desde archivo para @{user}.")
                    if self.session_ready_callback:
                        try:
                            self.session_ready_callback(session_data)
                        except Exception:
                            pass
                    return session_data
                self._ui_log("⚠️ Sesión antigua expirada. Intentando re-login...")
                os.remove(self.session_file)
            except Exception as e:
                self._ui_log(f"⚠️ Error cargando sesión local: {e}")
                if os.path.exists(self.session_file):
                    os.remove(self.session_file)

        # 3. Login normal
        try:
            self._ui_log(f"🔑 Iniciando login formal para @{user}...")
            time.sleep(random.uniform(2, 5))
            self.cl.login(user, pw)
            self.cl.dump_settings(self.session_file)
            session_data = self.cl.get_settings()
            self._ui_log("✅ Nuevo login exitoso y sesión guardada.")
            if self.session_ready_callback:
                try:
                    self.session_ready_callback(session_data)
                except Exception:
                    pass
            return session_data
        except ChallengeRequired:
            self._ui_log("🚨 ¡DESAFÍO DETECTADO! Abre Instagram en tu móvil y aprueba el inicio.")
            return None
        except Exception as e:
            self._ui_log(f"❌ Error crítico en login: {str(e)}")
            return None

    def _validate_active_session(self):
        try:
            self.cl.get_timeline_feed()
            return True
        except Exception as e:
            self._ui_log(f"⚠️ Validación de sesión fallida: {e}")
            return False

    def start_polling(self, user, pw, skip_login=False):
        self.is_running = True
        login_user = user.strip().lstrip('@')
        account_settings = db.get_account_by_username(login_user, self.cliente_id)
        if not account_settings:
            account_settings = db.get_account_by_username(user.strip(), self.cliente_id)

        if not skip_login:
            session_data = self.login(
                user,
                pw,
                session_data_encrypted=self.initial_session_data,
                security_service=self.security_service,
            )
            if not session_data:
                self._ui_log("❌ El motor se ha detenido. Revisa la configuración.")
                self.is_running = False
                return
        else:
            if not self._validate_active_session():
                self._ui_log("❌ La sesión activa no es válida. El motor se ha detenido.")
                self.is_running = False
                return

        self._ui_log("🚀 Motor en línea. Iniciando monitoreo de bandeja de entrada...")
        if account_settings:
            self._ui_log(f"🔎 Cuenta encontrada en DB: {account_settings.get('insta_user')}")
        else:
            self._ui_log("⚠️ No se encontró configuración de cuenta para el usuario de login. El bot continuará sin ajustes específicos.")

        self.account_system_prompt = self._build_account_system_prompt(account_settings)
        self._check_local_ip_security(account_settings)
        self._apply_proxy_logic(None)
        ciclos_sin_mensajes = 0
        batch_size = 8

        while self.is_running:
            try:
                if account_settings and not self._in_business_hours(account_settings.get('schedule_start'), account_settings.get('schedule_end')):
                    self._ui_log("🌙 Fuera de horario: Modo sueño activo.")
                    self._update_account_log(account_settings['id'], "🌙 Fuera de horario: Modo sueño activo.")
                    time.sleep(random.uniform(60, 120))
                    continue

                hay_mensajes_nuevos = False
                threads_map = {}

                try:
                    inbox_threads = self.cl.direct_threads(amount=10) or []
                    pending_threads = self.cl.direct_pending_inbox() or []
                    for thread in inbox_threads:
                        threads_map[thread.id] = thread
                    for thread in pending_threads:
                        threads_map[thread.id] = thread
                except Exception as e:
                    self._ui_log(f"⚠️ Error leyendo bandejas: {e}")
                    threads_map = {}

                threads = list(threads_map.values())
                self._ui_log(f"📥 Hilos encontrados: {len(threads)}")
                self._verificar_abandono_humano()
                if len(threads) > batch_size:
                    self._ui_log(f"📥 Hay {len(threads)} chats pendientes; procesando máximo {batch_size} por ciclo.")
                    threads = threads[:batch_size]

                for thread in threads:
                    if not self.is_running:
                        break
                    try:
                        msg_list = getattr(thread, 'messages', None)
                        if not msg_list:
                            self._ui_log(f"⚠️ Hilo {thread.id} sin mensajes. Se omite.")
                            continue
                        last_msg = msg_list[0]
                        if not last_msg:
                            self._ui_log(f"⚠️ Hilo {thread.id} tiene mensaje vacío. Se omite.")
                            continue

                        username = thread.users[0].username if getattr(thread, 'users', None) else 'desconocido'
                        sender_id = str(getattr(last_msg, 'user_id', ''))
                        if sender_id == str(self.cl.user_id):
                            if self._detect_implicit_handoff(thread, username):
                                continue
                            self._ui_log(f"ℹ️ Hilo {thread.id} es propio, se omite.")
                            continue

                        thread_status = db.get_thread_status(thread.id, self.cliente_id)
                        if self._is_paused(thread.id):
                            self._ui_log(f"⏸️ Hilo {thread.id} en pausa. Se omite.")
                            continue

                        if self._is_manual_intervention(thread, last_msg, thread_status):
                            self._ui_log(f"⚠️ Hilo {thread.id} detenido por intervención manual.")
                            db.pause_thread(thread.id, minutes=60, cliente_id=self.cliente_id)
                            continue

                        message_id = self._get_message_id(last_msg)
                        account_id = account_settings['id'] if account_settings else None
                        if self._should_skip_thread(thread, last_msg, account_settings, thread_status):
                            self._ui_log(f"⏹️ Hilo {thread.id} ignorado por reglas de antigüedad/duplicado.")
                            continue

                        hay_mensajes_nuevos = True
                        ciclos_sin_mensajes = 0
                        username = thread.users[0].username if getattr(thread, 'users', None) else 'desconocido'

                        if self._check_panic_keywords(getattr(last_msg, 'text', '')):
                            self._handoff_to_human(thread.id, username, account_settings)
                            continue

                        self._ui_log(f"📨 Procesando hilo {thread.id} de @{username}...")
                        if account_id:
                            self._update_account_log(account_id, f"📨 Procesando hilo {thread.id} de @{username}...")

                        self._ui_log("⏳ Simulando escritura natural...")
                        if account_id:
                            self._update_account_log(account_id, "⏳ Simulando escritura natural...")
                        time.sleep(random.uniform(*self._response_delay))

                        user_text = getattr(last_msg, 'text', '') or getattr(last_msg, 'message', '') or ''
                        if not user_text:
                            self._ui_log(f"⚠️ Mensaje del hilo {thread.id} no tiene texto. Se omite.")
                            continue

                        if account_id:
                            latest_settings = db.get_account_by_id(account_id, self.cliente_id)
                            if latest_settings:
                                account_settings = latest_settings
                                self.account_system_prompt = self._build_account_system_prompt(account_settings)

                        account_settings = account_settings or {}
                        time_context = self._get_time_context(thread_status)
                        bot_name = account_settings.get('assistant_name') or account_settings.get('bot_name') or account_settings.get('business_name') or "Alex"
                        whatsapp_contacto = account_settings.get('whatsapp_number') or account_settings.get('whatsapp_contacto') or ""

                        try:
                            respuesta = self.ai.generate_response(
                                user_text,
                                self.account_system_prompt,
                                bot_role=account_settings.get('bot_role') or account_settings.get('context_type'),
                                business_profile=account_settings.get('business_data') or account_settings.get('description') or account_settings.get('store_name'),
                                inventory_path=account_settings.get('inventory_path'),
                                bot_name=bot_name,
                                whatsapp_contacto=whatsapp_contacto,
                                time_context=time_context,
                                location=account_settings.get('location') or account_settings.get('ubicacion', ''),
                                website=account_settings.get('website', ''),
                            )
                        except RuntimeError as e:
                            self._ui_log(f"🚫 No se puede generar respuesta para hilo {thread.id}: {e}")
                            if account_id:
                                self._update_account_log(account_id, f"🚫 No se puede generar respuesta: {e}")
                            continue

                        if respuesta is None:
                            self._ui_log(f"⛔ El bot detuvo la respuesta para hilo {thread.id} por límite de prueba.")
                            if account_id:
                                self._update_account_log(account_id, "⛔ El bot detuvo la respuesta por límite de prueba.")
                            continue

                        self._ui_log(f"💬 Respuesta generada para hilo {thread.id}.")

                        is_handoff = False
                        try:
                            normalized = respuesta.lower() if isinstance(respuesta, str) else ''
                            whatsapp_check = whatsapp_contacto.lower() if whatsapp_contacto else ''
                            if whatsapp_check and whatsapp_check in normalized:
                                is_handoff = True
                            elif 'whatsapp' in normalized:
                                is_handoff = True
                            elif 'escríbenos' in normalized or 'nota al encargado' in normalized or 'te voy ayudando' in normalized:
                                is_handoff = True
                        except Exception:
                            is_handoff = False

                        if is_handoff and self.handoff_callback:
                            self._ui_log("🕒 Handoff detectado. Reteniendo respuesta y esperando tiempo de cortesía.")
                            self.handoff_callback(thread.id, username, respuesta)
                            continue

                        if "consultar con mi supervisor" in respuesta.lower():
                            self._ui_log("🚨 Botón de pánico activado: notificando al dueño del negocio.")
                            self._notify_owner_alert(thread.id, username, respuesta)

                        sent = self.cl.direct_send(respuesta, thread_ids=[thread.id])
                        message_id = getattr(sent, 'id', None) or getattr(sent, 'message_id', None) or self._get_message_id(sent)
                        if message_id:
                            self._add_sent_message(message_id)
                        if hasattr(self.cl, 'direct_send_seen'):
                            self.cl.direct_send_seen(thread.id)
                        elif hasattr(self.cl, 'direct_thread_mark_unread'):
                            # Si el cliente no soporta marcar como visto directamente, omitimos.
                            pass
                        self._ui_log(f"🤖 Respuesta enviada a @{username} en hilo {thread.id}.")
                        if account_id:
                            self._update_account_log(account_id, f"🤖 Respuesta enviada a @{username}.")

                        self._log_interaction(thread.id, username, user_text, respuesta)
                        db.mark_thread_processed(thread.id, message_id, cliente_id=self.cliente_id)

                        if len(threads) > 1:
                            delay_minutes = random.uniform(*self._chat_switch_delay)
                            self._ui_log(f"🚶 Saltando al siguiente cliente en {int(delay_minutes)} minutos...")
                            if account_id:
                                self._update_account_log(account_id, f"🚶 Saltando al siguiente cliente en {int(delay_minutes)} minutos...")
                            time.sleep(delay_minutes * 60)

                    except Exception as thread_error:
                        logging.error(f"Error aislado en chat {thread.id}: {thread_error}")
                        continue

                if not hay_mensajes_nuevos:
                    ciclos_sin_mensajes += 1
                    if ciclos_sin_mensajes % 3 == 0:
                        self._ui_log("👀 Monitoreando... (Sin mensajes nuevos)")

            except FeedbackRequired:
                self._ui_log("🛑 ¡Feedback Required! Instagram detectó mucha actividad. Pausando 5 min...")
                time.sleep(300)
            except Exception as e:
                logging.error(f"Error crítico en motor principal: {e}")
            time.sleep(random.uniform(*self._idle_cycle_delay))


    def stop(self):
        self.is_running = False
        self._ui_log("🛑 Secuencia de apagado iniciada.")

    def _is_paused(self, tid):
        with db.get_connection() as conn:
            if self.cliente_id is not None:
                row = conn.execute(
                    "SELECT status, paused_until FROM chat_status WHERE thread_id = ? AND cliente_id = ?",
                    (tid, self.cliente_id)
                ).fetchone()
            else:
                row = conn.execute("SELECT status, paused_until FROM chat_status WHERE thread_id = ?", (tid,)).fetchone()
            if not row:
                return False
            if row['paused_until']:
                try:
                    until = datetime.fromisoformat(row['paused_until'])
                    if datetime.now() < until:
                        return True
                    if self.cliente_id is not None:
                        conn.execute(
                            "UPDATE chat_status SET status = 'ACTIVE', paused_until = NULL WHERE thread_id = ? AND cliente_id = ?",
                            (tid, self.cliente_id)
                        )
                    else:
                        conn.execute("UPDATE chat_status SET status = 'ACTIVE', paused_until = NULL WHERE thread_id = ?", (tid,))
                    conn.commit()
                    return False
                except Exception:
                    return row['status'] in ('PAUSED', 'MANUAL', 'WAITING_HUMAN')
            return row['status'] in ('PAUSED', 'MANUAL', 'WAITING_HUMAN')

    def _check_panic_keywords(self, text):
        if not text: return False
        return any(k in text.lower() for k in ["humano", "persona", "asesor", "ayuda", "atencion"])

    def _handoff_to_human(self, tid, user, account_settings=None):
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_status (thread_id, status, last_manual_at) VALUES (?, 'WAITING_HUMAN', ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET status='WAITING_HUMAN', last_manual_at=?", 
                (tid, ahora, ahora)
            )
            conn.commit()

        whatsapp_contacto = ''
        if account_settings:
            whatsapp_contacto = account_settings.get('whatsapp_number') or account_settings.get('whatsapp_contacto') or ''

        handoff_message = HANDOFF_PHRASE.replace('{whatsapp_contacto}', whatsapp_contacto)
        if self.handoff_callback:
            self.handoff_callback(tid, user, handoff_message)
        else:
            try:
                self.cl.direct_send(handoff_message, thread_ids=[tid])
            except Exception:
                pass

        self._ui_log(f"⚠️ MODO DE ESPERA: @{user} marcado como WAITING_HUMAN.")

    def _notify_owner_alert(self, tid, user, respuesta):
        mensaje = (
            f"Alerta de seguridad: la respuesta generada para @{user} activó el botón de pánico."
            f" Contenido: {respuesta}"
        )
        self._ui_log(f"🚨 NOTIFICACIÓN: {mensaje}")
        # TODO: Implementar notificaciones reales de Pegasus (correo/enviar alerta al dashboard)

    def _apply_proxy_logic(self, account_id):
        # TODO: Implementar Smartproxy/Webshare cuando el usuario exceda las 2 cuentas en la Fase 2
        return None

    def _log_interaction(self, tid, user, msg, resp):
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (thread_id, username, mensaje_usuario, respuesta_ia) VALUES (?,?,?,?)", 
                (tid, user, msg, resp)
            )
            conn.commit()

    def _fetch_public_profile(self, username):
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                user = data.get("graphql", {}).get("user", {})
                if user:
                    return SimpleNamespace(
                        full_name=user.get("full_name", ""),
                        biography=user.get("biography", ""),
                        category_name=user.get("category_name", ""),
                        pk=user.get("id") or user.get("pk"),
                    )
        except Exception as e:
            logging.warning(f"Fallback público falló para perfil @{username}: {e}")
        return None

    def _safe_fetch_profile(self, username):
        self.last_profile_error = None
        retries = 3
        delay = 5
        for attempt in range(retries):
            try:
                return self.cl.user_info_by_username(username)
            except (requests.exceptions.RequestException, requests.exceptions.RetryError, MaxRetryError, ResponseError, RateLimitError, ClientConnectionError) as e:
                self.last_profile_error = "rate_limit"
                logging.warning(f"Rate limit / request error al obtener perfil @{username}: {e}")
                if attempt + 1 < retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break
            except UserNotFound:
                self.last_profile_error = "not_found"
                logging.debug(f"Usuario no encontrado @{username}.")
                return None
            except Exception as e:
                self.last_profile_error = "unknown"
                logging.warning(f"Error inesperado al obtener perfil @{username}: {e}")
                return None

        fallback = self._fetch_public_profile(username)
        if fallback:
            return fallback
        return None

    def _safe_fetch_medias(self, user_id, amount=3):
        if not user_id:
            return []
        retries = 2
        delay = 5
        for attempt in range(retries):
            try:
                return self.cl.user_medias(user_id, amount=amount)
            except (requests.exceptions.RequestException, requests.exceptions.RetryError, MaxRetryError, ResponseError, RateLimitError, ClientConnectionError) as e:
                logging.warning(f"Rate limit / request error al obtener medias del usuario {user_id}: {e}")
                if attempt + 1 < retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return []
            except Exception as e:
                logging.warning(f"Error inesperado al obtener medias del usuario {user_id}: {e}")
                return []

    def _extract_brand_name(self, username, full_name, biography):
        if full_name:
            return full_name.strip()
        if biography:
            first_line = biography.strip().split('\n')[0]
            if len(first_line) < 60 and any(word in first_line.lower() for word in ['tienda', 'store', 'brand', 'shop', 'salon', 'café', 'cafe', 'restaurante', 'boutique']):
                return first_line
        return username.capitalize() if username else ''

    def _extract_value_proposition(self, biography, captions):
        text = ' '.join([biography or ''] + captions).lower()
        if not text.strip():
            return "Ofrece soluciones prácticas a sus clientes con un enfoque profesional."

        if any(k in text for k in ['comida', 'delivery', 'restaurante', 'café', 'cafe', 'bar']):
            return "Ofrece comida y experiencias gastronómicas rápidas y sabrosas."
        if any(k in text for k in ['moda', 'ropa', 'fashion', 'estilo', 'look']):
            return "Vende moda y estilo para quienes buscan una propuesta actualizada."
        if any(k in text for k in ['belleza', 'spa', 'maquillaje', 'estética', 'cuidados']):
            return "Brinda servicios de belleza y cuidado personal con un enfoque elegante."
        if any(k in text for k in ['digital', 'marketing', 'branding', 'social media', 'consultor']):
            return "Ayuda a negocios a crecer con servicios digitales y de marketing estratégico."
        if any(k in text for k in ['decoración', 'muebles', 'interiores', 'hogar']):
            return "Diseña espacios y productos para el hogar con buen gusto y funcionalidad."
        if any(k in text for k in ['handmade', 'artesanal', 'hecho a mano', 'artesanía']):
            return "Ofrece productos artesanales hechos con dedicación y estilo propio."
        if any(k in text for k in ['consultoría', 'asesoría', 'servicios', 'coaching', 'planificación']):
            return "Brinda servicios profesionales diseñados para resolver necesidades específicas."
        if any(k in text for k in ['entrenamiento', 'fitness', 'bienestar', 'salud', 'yoga']):
            return "Ofrece entrenamientos y programas de bienestar para mejorar la calidad de vida."

        return "Comparte y ofrece productos o servicios relevantes para su público con un estilo claro y cercano."

    def _detect_tone(self, biography, captions):
        text = ' '.join([biography or ''] + captions).lower()
        if not text.strip():
            return "Profesional y directo"

        if any(k in text for k in ['urgente', 'oferta', 'ahora', 'última', 'solo hoy', 'promoción', 'descuento']):
            return "Urgente y comercial"
        if any(k in text for k in ['exclusivo', 'lujo', 'premium', 'elite', 'elegante']):
            return "Premium y elegante"
        if any(k in text for k in ['amigable', 'cariño', 'nos encanta', 'sonríe', 'divertido', 'alegre']):
            return "Cálido y cercano"
        if any(k in text for k in ['creativo', 'inspirador', 'arte', 'diseño', 'innovador']):
            return "Creativo y moderno"
        if any(k in text for k in ['rápido', 'fácil', 'confiable', 'eficaz']):
            return "Ágil y confiable"

        return "Profesional y conversacional"

    def analyze_profile(self, username):
        """Extrae el ADN de la tienda desde el perfil público de Instagram."""
        username = (username or "").strip().lstrip('@')
        if not username:
            return {
                "username": "",
                "brand_name": "",
                "value_proposition": "",
                "tone_detected": "",
                "biography": "",
                "category_name": "",
                "recent_captions": [],
                "error": "missing_username"
            }

        try:
            usuario = self._safe_fetch_profile(username)
            if not usuario:
                return {
                    "username": username,
                    "brand_name": username.capitalize(),
                    "value_proposition": "",
                    "tone_detected": "",
                    "biography": "",
                    "category_name": "",
                    "recent_captions": [],
                    "error": self.last_profile_error or "unknown"
                }

            medias = self._safe_fetch_medias(usuario.pk, amount=3)
            captions = []
            for media in medias:
                caption = getattr(media, "caption_text", None) or getattr(media, "caption", None) or ""
                if caption:
                    captions.append(caption)

            biography = usuario.biography or ""
            brand_name = self._extract_brand_name(username, usuario.full_name or "", biography)
            value_proposition = self._extract_value_proposition(biography, captions)
            tone_detected = self._detect_tone(biography, captions)

            return {
                "username": username,
                "brand_name": brand_name,
                "value_proposition": value_proposition,
                "tone_detected": tone_detected,
                "biography": biography,
                "category_name": usuario.category_name or "",
                "recent_captions": captions[:3]
            }
        except Exception as e:
            logging.warning(f"Error al analizar perfil @{username}: {e}")
            return {
                "username": username,
                "brand_name": username.capitalize(),
                "value_proposition": "",
                "tone_detected": "",
                "biography": "",
                "category_name": "",
                "recent_captions": []
            }
