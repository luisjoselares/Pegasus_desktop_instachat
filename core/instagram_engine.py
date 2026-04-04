import sys
import os
import time
import random
import logging
from datetime import datetime

# Parche de compatibilidad MoviePy necesario para el escritorio
try:
    import moviepy
    import moviepy.video.io.VideoFileClip 
    sys.modules['moviepy.editor'] = moviepy
except ImportError:
    pass

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, FeedbackRequired
from core.database import db
from core.ai_engine import AIService

class InstagramService:
    def __init__(self):
        self.cl = Client()
        self.ai = AIService()
        self.is_running = False
        self.session_file = "sessions/insta_session.json"
        self.log_callback = None
        os.makedirs("sessions", exist_ok=True)

    def set_callback(self, callback_func):
        self.log_callback = callback_func

    def _ui_log(self, mensaje):
        logging.info(mensaje)
        if self.log_callback:
            self.log_callback(mensaje)

    def login(self, user, pw):
        """Lógica original de Flet adaptada a parámetros directos."""
        if not user or not pw:
            self._ui_log("❌ Error: Faltan credenciales en la interfaz.")
            return False

        # 1. Intentar cargar sesión existente (Igual que en Flet)
        if os.path.exists(self.session_file):
            try:
                self.cl.load_settings(self.session_file)
                # IMPORTANTE: Usamos la validación real que tenías en Flet
                self.cl.get_timeline_feed() 
                self._ui_log(f"✅ Sesión recuperada exitosamente para @{user}.")
                return True
            except Exception:
                self._ui_log("⚠️ Sesión antigua expirada. Intentando re-login...")
                if os.path.exists(self.session_file):
                    os.remove(self.session_file)
        
        # 2. Hard Login limpio sin alterar el User-Agent
        try:
            self._ui_log(f"🔑 Iniciando sesión formal para @{user}...")
            time.sleep(random.uniform(2, 5)) 
            self.cl.login(user, pw)
            self.cl.dump_settings(self.session_file)
            self._ui_log("✅ Nuevo login exitoso y sesión guardada.")
            return True
            
        except ChallengeRequired:
            self._ui_log("🚨 ¡DESAFÍO DETECTADO! Abre Instagram en tu móvil y aprueba el inicio.")
            return False
        except Exception as e:
            self._ui_log(f"❌ Error crítico en login: {str(e)}")
            return False

    def start_polling(self, user, pw):
        self.is_running = True
        
        if not self.login(user, pw):
            self._ui_log("❌ El motor se ha detenido. Revisa la configuración.")
            self.is_running = False
            return

        self._ui_log("🚀 Motor en línea. Iniciando monitoreo de bandeja de entrada...")
        ciclos_sin_mensajes = 0

        while self.is_running:
            try:
                hay_mensajes_nuevos = False
                hilos_a_procesar = []

                # Combinamos bandejas como lo hacías en tu código
                try:
                    hilos_a_procesar.extend(self.cl.direct_threads(amount=10))
                    pending = self.cl.direct_pending_inbox()
                    if pending:
                        hilos_a_procesar.extend(pending)
                except Exception as e:
                    logging.warning(f"Error al leer bandejas: {e}")

                for thread in hilos_a_procesar:
                    try:
                        if not thread.messages: continue
                        last_msg = thread.messages[0]
                        
                        if str(last_msg.user_id) == str(self.cl.user_id): continue
                        
                        hay_mensajes_nuevos = True
                        ciclos_sin_mensajes = 0
                        username = thread.users[0].username
                        
                        # Verificación de modo manual
                        if self._is_paused(thread.id): continue
                        if self._check_panic_keywords(last_msg.text):
                            self._handoff_to_human(thread.id, username)
                            continue

                        self._ui_log(f"📨 Recibiendo mensaje de @{username}...")
                        
                        respuesta = self.ai.generate_response(last_msg.text, thread.id)
                        
                        time.sleep(random.uniform(3, 6))
                        self.cl.direct_send(respuesta, thread_ids=[thread.id])
                        self.cl.direct_thread_mark_seen(thread.id)
                        
                        self._ui_log(f"🤖 Respuesta enviada a @{username}.")
                        self._log_interaction(thread.id, username, last_msg.text, respuesta)

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
            row = conn.execute("SELECT status FROM chat_status WHERE thread_id = ?", (tid,)).fetchone()
            return row and row['status'] == 'PAUSED'

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

    def _log_interaction(self, tid, user, msg, resp):
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (thread_id, username, mensaje_usuario, respuesta_ia) VALUES (?,?,?,?)", 
                (tid, user, msg, resp)
            )
            conn.commit()