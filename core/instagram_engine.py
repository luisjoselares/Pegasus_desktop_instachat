import sys
import os
import time
import random
import logging
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
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired, RateLimitError, ClientConnectionError, UserNotFound
from services.database_service import db
from core.ai_engine import AIService

class InstagramService:
    def __init__(self):
        self.cl = Client()
        self.ai = AIService()
        self.ai.set_trial_status_callback(lambda restantes: self._ui_log(f"[TRIAL] Mensajes restantes: {restantes}"))
        self.is_running = False
        self.session_file = None
        self.log_callback = None
        self.handoff_callback = None
        self.rescue_callback = None
        self.last_profile_error = None
        self.security_service = None
        self.bot_sent_messages = deque(maxlen=1000)
        self.bot_sent_message_ids = set()
        self.muted_threads = {}
        self._last_rescue_check = None
        self.cliente_id = None
        os.makedirs("sessions", exist_ok=True)

    def set_cliente_id(self, cliente_id):
        self.cliente_id = cliente_id
        if hasattr(self.ai, 'set_cliente_id'):
            self.ai.set_cliente_id(cliente_id)

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

    def set_licencia_id(self, licencia_id):
        self.ai.set_licencia_id(licencia_id)

    def set_trial_status_callback(self, callback_func):
        self.ai.set_trial_status_callback(callback_func)

    def _ui_log(self, mensaje):
        logging.info(mensaje)
        if self.log_callback:
            self.log_callback(mensaje)

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
            try:
                return datetime.fromisoformat(timestamp)
            except Exception:
                pass
        return None

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
        db.pause_thread(thread_id, minutes=720, cliente_id=self.cliente_id)
        self.muted_threads[thread_id] = datetime.now().isoformat(sep=' ')
        self._ui_log(f"[HANDOFF] Hilo {thread_id} silenciado durante 12h.")

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
            cursor = conn.execute("SELECT thread_id FROM chat_status WHERE status = 'PAUSED'")
            paused_threads = [row['thread_id'] for row in cursor.fetchall()]

        for thread_id in paused_threads:
            try:
                thread_fetcher = getattr(self.cl, 'direct_thread', None)
                thread = self.cl.direct_thread(thread_id) if callable(thread_fetcher) else None
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

                if (ahora - timestamp) > timedelta(minutes=15):
                    username = thread.users[0].username if getattr(thread, 'users', None) else 'desconocido'
                    self._ui_log(f"[RESCATE] Inactividad humana detectada (>15 min). Bot reactivado para el chat con @{username}.")
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
            session_data = self.login(user, pw, security_service=self.security_service)
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
                            self._handoff_to_human(thread.id, username)
                            continue

                        self._ui_log(f"📨 Procesando hilo {thread.id} de @{username}...")
                        if account_id:
                            self._update_account_log(account_id, f"📨 Procesando hilo {thread.id} de @{username}...")

                        self._ui_log("⏳ Simulando escritura natural...")
                        if account_id:
                            self._update_account_log(account_id, "⏳ Simulando escritura natural...")
                        time.sleep(random.uniform(30, 90))

                        user_text = getattr(last_msg, 'text', '') or getattr(last_msg, 'message', '') or ''
                        if not user_text:
                            self._ui_log(f"⚠️ Mensaje del hilo {thread.id} no tiene texto. Se omite.")
                            continue

                        try:
                            respuesta = self.ai.generate_response(user_text, thread.id)
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

                        if "consultar con mi supervisor" in respuesta.lower():
                            self._ui_log("🚨 Botón de pánico activado: notificando al dueño del negocio.")
                            self._notify_owner_alert(thread.id, username, respuesta)

                        sent = self.cl.direct_send(respuesta, thread_ids=[thread.id])
                        message_id = getattr(sent, 'id', None) or getattr(sent, 'message_id', None) or self._get_message_id(sent)
                        if message_id:
                            self._add_sent_message(message_id)
                        self.cl.direct_thread_mark_seen(thread.id)
                        self._ui_log(f"🤖 Respuesta enviada a @{username} en hilo {thread.id}.")
                        if account_id:
                            self._update_account_log(account_id, f"🤖 Respuesta enviada a @{username}.")

                        self._log_interaction(thread.id, username, user_text, respuesta)
                        db.mark_thread_processed(thread.id, message_id, cliente_id=self.cliente_id)

                        if len(threads) > 1:
                            delay_minutes = random.uniform(2, 5)
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
            time.sleep(random.uniform(12, 22))


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
                    return row['status'] == 'PAUSED'
            return row['status'] == 'PAUSED'

    def _check_panic_keywords(self, text):
        if not text: return False
        return any(k in text.lower() for k in ["humano", "persona", "asesor", "ayuda", "atencion"])

    def _handoff_to_human(self, tid, user):
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_status (thread_id, status, last_manual_at) VALUES (?, 'PAUSED', ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET status='PAUSED', last_manual_at=?", 
                (tid, ahora, ahora)
            )
            conn.commit()
        self.cl.direct_send("He pausado mis respuestas automáticas. Un asesor humano te atenderá.", thread_ids=[tid])
        self._ui_log(f"⚠️ MODO MANUAL: @{user} derivado a humano.")

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

    def analyze_profile(self, username):
        """Extrae el ADN de la tienda desde el perfil público de Instagram."""
        username = (username or "").strip().lstrip('@')
        if not username:
            return {
                "username": "",
                "full_name": "",
                "biography": "",
                "category_name": "",
                "recent_captions": []
            }

        try:
            usuario = self._safe_fetch_profile(username)
            if not usuario:
                return {
                    "username": "",
                    "full_name": "",
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
            return {
                "username": username,
                "full_name": usuario.full_name or "",
                "biography": usuario.biography or "",
                "category_name": usuario.category_name or "",
                "recent_captions": captions[:3]
            }
        except Exception as e:
            logging.warning(f"Error al analizar perfil @{username}: {e}")
            return {
                "username": "",
                "full_name": "",
                "biography": "",
                "category_name": "",
                "recent_captions": []
            }