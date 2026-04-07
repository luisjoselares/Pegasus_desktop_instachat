# controllers/instagram_controller.py
from os import path
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from services.instagram_service import InstagramService

class InstagramController(QObject):
    configuration_updated = pyqtSignal()
    handoff_alert = pyqtSignal(str, str)
    signal_handoff_alert = pyqtSignal(str)
    """
    Controlador Senior para la gestión de cuentas de Instagram.
    Actúa como puente entre LocalDBService y la interfaz modernizada de Pegasus.
    """
    def __init__(self, db_service, engine=None, security_service=None, cliente_id=None):
        super().__init__()
        self.db = db_service
        self.view = None
        self.engine = engine if engine is not None else InstagramService(db_service=db_service)
        self.security_service = security_service
        self.cliente_id = cliente_id
        self.main_controller = None
        self.active_handoff_timers = {}
        self.alerta_venta = QSoundEffect()
        sound_file = path.join(path.dirname(__file__), '..', 'assets', 'sounds', 'alerta_venta.wav')
        if path.exists(sound_file):
            self.alerta_venta.setSource(QUrl.fromLocalFile(path.abspath(sound_file)))
            self.alerta_venta.setVolume(0.8)

        if cliente_id and hasattr(self.engine, 'set_cliente_id'):
            self.engine.set_cliente_id(cliente_id)

    def set_main_controller(self, controller):
        self.main_controller = controller

    def set_licencia_id(self, licencia_id):
        self.engine.set_licencia_id(licencia_id)

    def set_trial_status_callback(self, callback):
        self.engine.set_trial_status_callback(callback)

    def set_view(self, view, cliente_id=None):
        """Vincula la página de cuentas y realiza la carga inicial."""
        self.view = view
        if cliente_id is not None:
            self.cliente_id = cliente_id
            if hasattr(self.engine, 'set_cliente_id'):
                self.engine.set_cliente_id(cliente_id)
        self.refresh(cliente_id)

    def refresh(self, cliente_id=None):
        """Actualiza la lista de tarjetas obteniendo los datos reales de la DB."""
        if self.view:
            current_id = cliente_id if cliente_id is not None else self.cliente_id
            accounts = self.db.obtener_cuentas(current_id)
            active_chats = self.db.obtener_chats_activos(current_id)
            avg_delay = None
            if hasattr(self.engine, 'get_average_next_chat_delay'):
                try:
                    avg_delay = self.engine.get_average_next_chat_delay()
                except Exception:
                    avg_delay = None

            for account in accounts:
                account["conversations"] = active_chats
                account["active_chat_count"] = len(active_chats)
                account["next_chat_avg"] = f"{avg_delay:.1f} min" if avg_delay is not None else "N/A"
                account["current_task"] = account.get('last_log', 'Esperando actividad...')
            self.view.load_accounts(accounts)

    def add_account(self, data, cliente_id=None):
        """
        Procesa el alta de una cuenta desde el AddAccountDialog.
        'data' contiene: user, pass, type, start, end, proxy, prompt.
        """
        if not data.get('user') or not data.get('pass'):
            print("⚠️ Error: Intento de agregar cuenta con campos obligatorios vacíos.")
            return

        account_data = data.copy()
        if self.security_service and account_data.get('pass'):
            account_data['pass'] = self.security_service.encrypt(account_data['pass'])

        # Guardamos en la base de datos
        self.db.agregar_cuenta(account_data, cliente_id or self.cliente_id)
        self.refresh(cliente_id)
        self.configuration_updated.emit()
        print(f"Controlador: Cuenta {data['user']} añadida correctamente.")

    def edit_account(self, account_id, data):
        if not account_id or not data:
            return 0

        changes = {}
        if data.get('user'):
            changes['insta_user'] = data['user']
        if data.get('store_name') is not None:
            changes['store_name'] = data['store_name']
        if data.get('description') is not None:
            changes['description'] = data['description']
        if data.get('business_name') is not None:
            changes['business_name'] = data['business_name']
        if data.get('business_data') is not None:
            changes['business_data'] = data['business_data']
        if data.get('bot_role') is not None:
            changes['bot_role'] = data['bot_role']
        if data.get('structured_identity') is not None:
            changes['structured_identity'] = data['structured_identity']
        if data.get('prompt') is not None:
            changes['system_prompt'] = data['prompt']
        if data.get('type') is not None:
            changes['context_type'] = data['type']
        if data.get('start') is not None:
            changes['schedule_start'] = data['start']
        if data.get('end') is not None:
            changes['schedule_end'] = data['end']
        if data.get('proxy') is not None:
            changes['proxy'] = data['proxy']

        if data.get('pass'):
            if self.security_service and hasattr(self.security_service, 'encrypt'):
                changes['insta_pass'] = self.security_service.encrypt(data['pass'])
            else:
                changes['insta_pass'] = data['pass']

        updated = self.update_account_settings(account_id, changes)
        if updated:
            self.refresh(self.cliente_id)
            self.configuration_updated.emit()
            print(f"Controlador: Cuenta {account_id} actualizada correctamente.")
        return updated

    def toggle_bot(self, account_id, state):
        """
        Activa o desactiva la operación de la IA para una cuenta específica.
        Sincroniza con la DB y actualiza el log visual (Cyan).
        """
        self.update_account_settings(account_id, {'bot_enabled': 1 if state else 0})
        
        status_text = "ENCENDIDO" if state else "APAGADO"
        log_msg = f"Bot {status_text} - El sistema está en modo {'automático' if state else 'manual'}."
        self.db.actualizar_log(account_id, log_msg)
        
        print(f"Controlador: Switch de Bot ID {account_id} movido a {status_text}")

        if self.main_controller:
            if state:
                self.main_controller.iniciar_bot()
            else:
                self.main_controller.detener_bot()

    def update_account_settings(self, account_id, changes):
        if not changes:
            return 0
        if hasattr(self.db, 'save_settings'):
            return self.db.save_settings(account_id, changes, self.cliente_id)
        return self.db.update_settings(account_id, changes, self.cliente_id)

    def force_activate_account(self, account_id):
        if not hasattr(self.db, 'clear_account_pauses'):
            print("⚠️ Servicio DB no soporta reactivo forzado de hilos.")
            return 0

        restored = self.db.clear_account_pauses(account_id, self.cliente_id)
        if restored:
            self.db.actualizar_log(account_id, f"✅ Fuerza activación: {restored} hilo(s) reactivado(s).")
        print(f"Controlador: Fuerza activación para cuenta {account_id}, {restored} hilos reactivados.")
        return restored

    def toggle_manual_thread(self, thread_id, enable):
        if not thread_id:
            return
        if enable:
            self.db.pause_thread(thread_id, minutes=720, cliente_id=self.cliente_id, status='MANUAL')
            print(f"Controlador: Hilo {thread_id} pausado manualmente durante 12h.")
        else:
            self.db.update_thread_status(thread_id, status='ACTIVE', cliente_id=self.cliente_id)
            print(f"Controlador: Hilo {thread_id} reactivado manualmente.")

    def schedule_handoff(self, thread_id, username, response, whatsapp_contacto=""):
        if not thread_id or not username:
            return
        self.mark_waiting_for_human(thread_id)
        self._play_alert_sound()
        self._append_handoff_log(thread_id, username, response)
        self.signal_handoff_alert.emit(username)
        self.handoff_alert.emit(thread_id, username)
        if username in self.active_handoff_timers:
            self.active_handoff_timers[username]['timer'].stop()
            del self.active_handoff_timers[username]

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda tid=thread_id, user=username, resp=response, wa=whatsapp_contacto: self.execute_delayed_handoff(tid, user, resp, wa))
        timer.start(180000)
        self.active_handoff_timers[username] = {
            'timer': timer,
            'thread_id': thread_id,
        }

    def cancel_handoff_timer(self, username):
        entry = self.active_handoff_timers.get(username)
        if entry:
            entry['timer'].stop()
            thread_id = entry.get('thread_id')
            del self.active_handoff_timers[username]
            if thread_id:
                self.db.update_thread_status(thread_id, status='ACTIVE', cliente_id=self.cliente_id)
            print(f"Controlador: Temporizador de handoff cancelado para @{username}.")

    def manual_send_occurred(self, username):
        if username:
            self.cancel_handoff_timer(username)
            print(f"Controlador: Intervención humana detectada para @{username}, handoff cancelado.")

    def execute_delayed_handoff(self, thread_id, username, response, whatsapp_contacto=""):
        if username in self.active_handoff_timers:
            del self.active_handoff_timers[username]

        if not thread_id:
            return

        handoff_text = response or (
            f"Ese detalle específico no lo tengo a la mano. Por favor escríbenos por WhatsApp: {whatsapp_contacto}."
        )
        if hasattr(self.engine, 'cl'):
            try:
                self.engine.cl.direct_send(handoff_text, thread_ids=[thread_id])
            except Exception as exc:
                print(f"Controlador: Error enviando handoff retrasado: {exc}")

        self.db.pause_thread(thread_id, minutes=720, cliente_id=self.cliente_id, status='MANUAL')
        print(f"Controlador: Handoff enviado tras 3 min de cortesía para @{username}. Bot en modo MANUAL.")
        if self.view and hasattr(self.view, 'log_console'):
            self.view.log_console.append(f"[HANDOFF] Handoff enviado tras 3 min de cortesía para @{username}. Bot en modo MANUAL.")
        self.notify_owner_via_whatsapp(handoff_text)

    def mark_waiting_for_human(self, thread_id):
        self.db.update_thread_status(thread_id, status='WAITING_HUMAN', cliente_id=self.cliente_id)

    def notify_owner_via_whatsapp(self, message):
        # TODO: Integrar con API de WhatsApp para alertar al dueño del negocio.
        pass

    def _play_alert_sound(self):
        if self.sound_effect and self.sound_effect.isAvailable():
            self.sound_effect.play()

    def _append_handoff_log(self, thread_id, username, response):
        print(f"Controlador: Handoff detectado para @{username}. Se espera 3 minutos antes de redirigir.")
        if self.view and hasattr(self.view, 'log_console'):
            self.view.log_console.append(f"[HANDOFF] @{username} en WAITING_HUMAN. Redirección en 3 min si no hay intervención.")

    def get_conversation_history(self, thread_id):
        if not thread_id:
            return []
        if hasattr(self.db, 'obtener_conversacion_completa'):
            return self.db.obtener_conversacion_completa(thread_id)
        return []

    def update_account_context(self, account_id, prompt):
        """
        Actualiza el System Prompt (Personalidad) de la cuenta.
        """
        self.update_account_settings(account_id, {'system_prompt': prompt})
        self.db.actualizar_log(account_id, "Contexto de IA actualizado con éxito.")
        print(f"Controlador: Prompt actualizado para cuenta {account_id}")

    def delete_account(self, account_id):
        """Elimina la cuenta y refresca la vista inmediatamente."""
        self.db.eliminar_cuenta(account_id)
        self.refresh()
        print(f"Controlador: Cuenta {account_id} eliminada físicamente de la DB.")