from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime
from core.instagram_engine import InstagramService

class BotThread(QThread):
    status_signal = pyqtSignal(str)

    def __init__(self, engine, user, pw):
        super().__init__()
        self.engine = engine
        self.user = user
        self.pw = pw

    def run(self):
        self.engine.set_callback(lambda msg: self.status_signal.emit(msg))
        self.engine.start_polling(self.user, self.pw)

class MainController:
    # NUEVO: Ahora recibe cliente_data y licencia_data
    def __init__(self, view, cliente_data=None, licencia_data=None):
        self.view = view
        self.engine = InstagramService() 
        self.thread = None

        if cliente_data and licencia_data:
            self.cargar_datos_usuario(cliente_data, licencia_data)

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
                self.view.btn_start.setEnabled(False) # Bloqueo duro
                self.view.log_console.append("❌ TU LICENCIA HA EXPIRADO. Por favor, renueva tu plan.")
        else:
            self.view.lbl_license_status.setText(f"Licencia: {estado}")
            self.view.lbl_license_status.setObjectName("licenciaInactiva")
            self.view.btn_start.setEnabled(False) # Bloqueo duro
            
        # Forzar recarga de estilos
        self.view.lbl_license_status.style().unpolish(self.view.lbl_license_status)
        self.view.lbl_license_status.style().polish(self.view.lbl_license_status)

    def iniciar_bot(self):
        user = self.view.txt_user.text()
        pw = self.view.txt_pass.text()
        
        if not user or not pw:
            self.view.log_console.append("❌ Error: Falta usuario o contraseña")
            return

        self.view.btn_start.setEnabled(False)
        self.view.btn_stop.setEnabled(True)
        
        self.thread = BotThread(self.engine, user, pw)
        self.thread.status_signal.connect(self.actualizar_log)
        self.thread.start()

    def detener_bot(self):
        if self.thread and self.thread.isRunning():
            self.engine.stop()
            self.thread.quit()
            self.thread.wait()
            
        self.view.btn_start.setEnabled(True)
        self.view.btn_stop.setEnabled(False)
        self.view.log_console.append("🛑 Motor detenido manualmente.")

    def actualizar_log(self, mensaje):
        self.view.log_console.append(mensaje)