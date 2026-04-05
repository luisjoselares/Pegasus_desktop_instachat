from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime
import json
from services.database_service import db
from services.instagram_service import InstagramService

class BotThread(QThread):
    status_signal = pyqtSignal(str)
    handoff_signal = pyqtSignal(str, str)
    rescue_signal = pyqtSignal(str, str)

    def __init__(self, engine, user, pw, skip_login=False):
        super().__init__()
        self.engine = engine
        self.user = user
        self.pw = pw
        self.skip_login = skip_login

    def run(self):
        self.engine.set_callback(lambda msg: self.status_signal.emit(msg))
        self.engine.set_handoff_callback(lambda tid, username: self.handoff_signal.emit(tid, username))
        self.engine.set_rescue_callback(lambda tid, username: self.rescue_signal.emit(tid, username))
        self.engine.start_polling(self.user, self.pw, skip_login=self.skip_login)

class MainController:
    def __init__(self, view, cliente_data=None, licencia_data=None, engine=None, cliente_id=None, security_service=None, db_service=None):
        self.view = view
        self.engine = engine if engine is not None else InstagramService()
        self.thread = None
        self.cliente_id = cliente_id
        self.security_service = security_service
        self.db_service = db_service

        if licencia_data and hasattr(self.engine, 'set_licencia_id'):
            self.engine.set_licencia_id(licencia_data.get('id'))
        if cliente_id and hasattr(self.engine, 'set_cliente_id'):
            self.engine.set_cliente_id(cliente_id)

        if hasattr(self.engine, 'set_trial_status_callback'):
            self.engine.set_trial_status_callback(self._on_trial_status)

        if cliente_data and licencia_data:
            self.cargar_datos_usuario(cliente_data, licencia_data)

        if hasattr(self.view, 'btn_start') and hasattr(self.view, 'btn_stop'):
            self.view.btn_start.clicked.connect(self.iniciar_bot)
            self.view.btn_stop.clicked.connect(self.detener_bot)

    def cargar_datos_usuario(self, cliente, licencia):
        """Inyecta los datos de Supabase en la vista y calcula vencimiento."""
        nombre_pila = cliente.get("nombre_completo", "Usuario").split()[0]
        self.view.lbl_welcome.setText(f"Bienvenido, {nombre_pila}")
        
        estado = licencia.get("estado", "INACTIVO")
        vencimiento_str = licencia.get("fecha_vencimiento")
        
        if estado == "ACTIVO" and vencimiento_str:
            vence = datetime.strptime(vencimiento_str, "%Y-%m-%d")
            dias_restantes = (vence - datetime.now()).days
            
            if dias_restantes > 0:
                self.view.lbl_license_status.setText(f"Licencia: ACTIVA ({dias_restantes} días)")
                self.view.lbl_license_status.setObjectName("licenciaActiva")
            else:
                self.view.lbl_license_status.setText("Licencia: VENCIDA")
                self.view.lbl_license_status.setObjectName("licenciaVencida")
                if hasattr(self.view, 'btn_start'):
                    self.view.btn_start.setEnabled(False) # Bloqueo duro
                if hasattr(self.view, 'log_console'):
                    self.view.log_console.append("❌ TU LICENCIA HA EXPIRADO. Por favor, renueva tu plan.")
        else:
            self.view.lbl_license_status.setText(f"Licencia: {estado}")
            self.view.lbl_license_status.setObjectName("licenciaInactiva")
            if hasattr(self.view, 'btn_start'):
                self.view.btn_start.setEnabled(False) # Bloqueo duro
            
        # Forzar recarga de estilos
        self.view.lbl_license_status.style().unpolish(self.view.lbl_license_status)
        self.view.lbl_license_status.style().polish(self.view.lbl_license_status)

    def iniciar_bot(self):
        user = self.view.txt_user.text().strip() if hasattr(self.view, 'txt_user') else ""
        pw = self.view.txt_pass.text().strip() if hasattr(self.view, 'txt_pass') else ""
        account = None

        if not user or not pw:
            cuentas = db.obtener_cuentas(self.cliente_id)
            if cuentas:
                account = cuentas[0]
                user = account.get('insta_user', '').strip()
                pw = account.get('insta_pass', '').strip()
                if self.security_service:
                    decrypted_pw = self.security_service.decrypt(pw)
                    if decrypted_pw:
                        pw = decrypted_pw
                if hasattr(self.view, 'log_console'):
                    self.view.log_console.append(f"🔐 Usando credenciales guardadas para @{user}.")
        else:
            account = db.get_account_by_username(user.strip(), self.cliente_id)

        if not user or not pw:
            if hasattr(self.view, 'log_console'):
                self.view.log_console.append("❌ Error: Falta usuario o contraseña de Instagram.")
            return

        if self.thread and self.thread.isRunning():
            if hasattr(self.view, 'log_console'):
                self.view.log_console.append("❌ El motor ya está ejecutándose.")
            return

        if hasattr(self.view, 'btn_start'):
            self.view.btn_start.setEnabled(False)
        if hasattr(self.view, 'btn_stop'):
            self.view.btn_stop.setEnabled(True)
        
        if hasattr(self.view, 'log_console'):
            self.view.log_console.append(f"🚀 Iniciando bot con @{user}...")

        # Intentamos el login antes de arrancar el hilo para poder persistir la sesión.
        session_data = self.engine.login(
            user,
            pw,
            session_data_encrypted=account.get('session_data') if account else None,
            security_service=self.security_service
        )

        if not session_data:
            if hasattr(self.view, 'log_console'):
                self.view.log_console.append("❌ No se pudo iniciar sesión en Instagram. Revisa las credenciales o el estado de la sesión.")
            if hasattr(self.view, 'btn_start'):
                self.view.btn_start.setEnabled(True)
            if hasattr(self.view, 'btn_stop'):
                self.view.btn_stop.setEnabled(False)
            return

        try:
            session_json = session_data if isinstance(session_data, str) else json.dumps(session_data)
        except Exception:
            session_json = str(session_data)

        if self.security_service:
            username_key = user.strip().lstrip('@')
            session_encrypted = self.security_service.encrypt(session_json)
            self.db_service.update_session_data(username_key, session_encrypted, self.cliente_id)

        self.thread = BotThread(self.engine, user, pw, skip_login=True)
        self.thread.status_signal.connect(self.actualizar_log)
        self.thread.handoff_signal.connect(self.handle_handoff_signal)
        self.thread.rescue_signal.connect(self.handle_rescue_signal)
        self.thread.start()

    def handle_handoff_signal(self, thread_id, username):
        if hasattr(self.view, 'log_console'):
            self.view.log_console.append(f"[HANDOFF] Intervención humana detectada en @{username}. Bot silenciado 12h.")
        if hasattr(self.view, 'mark_handoff_thread'):
            self.view.mark_handoff_thread(thread_id)

    def handle_rescue_signal(self, thread_id, username):
        if hasattr(self.view, 'log_console'):
            self.view.log_console.append(f"[RESCATE] Inactividad humana detectada, bot reactivado para @{username}.")
        if hasattr(self.view, 'mark_rescue_thread'):
            self.view.mark_rescue_thread(thread_id)

    def _on_trial_status(self, restantes):
        if hasattr(self.view, 'log_console'):
            if isinstance(restantes, dict):
                mensajes = restantes.get('mensajes', 'N/A')
                tokens = restantes.get('tokens', 'N/A')
                self.view.log_console.append(f"[TRIAL] Mensajes restantes: {mensajes} | Tokens restantes: {tokens}")
            else:
                self.view.log_console.append(f"[TRIAL] Mensajes restantes: {restantes}")

    def auto_start_if_enabled(self):
        cuentas = db.obtener_cuentas(self.cliente_id)
        cuenta_activa = next((c for c in cuentas if c.get('bot_enabled') == 1), None)
        if cuenta_activa and not self.thread:
            if hasattr(self.view, 'log_console'):
                self.view.log_console.append("🔄 Se detectó una cuenta habilitada. Iniciando bot automáticamente...")
            self.iniciar_bot()

    def _enabled_account_count(self):
        with db.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as total FROM settings WHERE bot_enabled = 1").fetchone()
            return row["total"] if row else 0

    def detener_bot(self):
        if self.thread and self.thread.isRunning():
            self.engine.stop()
            self.thread.quit()
            self.thread.wait()
            
        if hasattr(self.view, 'btn_start'):
            self.view.btn_start.setEnabled(True)
        if hasattr(self.view, 'btn_stop'):
            self.view.btn_stop.setEnabled(False)
        if hasattr(self.view, 'log_console'):
            self.view.log_console.append("🛑 Motor detenido manualmente.")

    def actualizar_log(self, mensaje):
        if hasattr(self.view, 'append_log_message'):
            self.view.append_log_message(mensaje)
        elif hasattr(self.view, 'log_console'):
            self.view.log_console.append(mensaje)