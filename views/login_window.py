import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QInputDialog, QApplication, QStackedWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from supabase import create_client, Client
from dotenv import load_dotenv
from services.cloud_service import validar_licencia_cliente, sincronizar_aplicacion

# Importación de Servicios y Vistas
from services.mailer_service import MailerService
from views.register_wizard import RegisterWizard
# Asegúrate de que este archivo exista en views/
from views.forgot_password_page import ForgotPasswordPage

class LoginPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        # Crucial para el styles.qss
        self.setObjectName("LoginPage")
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)

        # Encabezado Visual
        lbl_title = QLabel("PEGASUS")
        lbl_title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00E5FF; margin-bottom: 5px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("SISTEMA DE GESTIÓN DE CUENTAS")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet("color: #666666; font-size: 10px; letter-spacing: 2px; margin-bottom: 20px;")
        layout.addWidget(lbl_subtitle)

        # Campos de entrada
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Correo electrónico")
        layout.addWidget(self.txt_email)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Contraseña")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.txt_password)

        # Botón de Acción Principal
        self.btn_login = QPushButton("INICIAR SESIÓN")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.ejecutar_login)
        layout.addWidget(self.btn_login)

        # Enlaces secundarios
        self.btn_forgot = QPushButton("¿Olvidaste tu contraseña?")
        self.btn_forgot.setObjectName("link_btn") 
        self.btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forgot.setStyleSheet("background: transparent; color: #888; font-size: 11px; border: none;")
        self.btn_forgot.clicked.connect(self.parent.mostrar_recuperacion)
        layout.addWidget(self.btn_forgot)

        self.btn_goto_register = QPushButton("¿No tienes licencia? Regístrate aquí")
        self.btn_goto_register.setObjectName("link_btn")
        self.btn_goto_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_goto_register.setStyleSheet("color: #00E5FF; text-decoration: underline; background: transparent; border: none;")
        self.btn_goto_register.clicked.connect(self.parent.mostrar_registro)
        layout.addWidget(self.btn_goto_register)

        self.setLayout(layout)

    def ejecutar_login(self):
        email = self.txt_email.text().strip().lower()
        password = self.txt_password.text().strip()
        
        # Obtenemos el HWID para validar el equipo
        current_hwid = self.parent.register_page.obtener_hwid()

        if not email or not password:
            QMessageBox.warning(self, "Error", "Ingresa tus credenciales.")
            return

        self.btn_login.setText("VERIFICANDO...")
        self.btn_login.setEnabled(False)
        QApplication.processEvents()

        try:
            load_dotenv()
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            if not supabase_url or not supabase_key:
                raise Exception("Variables de entorno SUPABASE_URL o SUPABASE_KEY no configuradas.")

            supabase: Client = create_client(supabase_url, supabase_key)

            # 1. Validar Credenciales (correo insensible a mayúsculas/minúsculas)
            res = supabase.table("clientes").select("*").ilike("email", email).execute()
            if not getattr(res, 'data', None) or res.data[0].get("password") != password:
                respuesta = QMessageBox.question(
                    self,
                    "Acceso Denegado",
                    "El correo o la contraseña son incorrectos, o el usuario no existe.\n\n¿Deseas crear una cuenta nueva en Pegasus?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if respuesta == QMessageBox.StandardButton.Yes:
                    self.txt_password.clear()
                    self.parent.stack.setCurrentIndex(1)
                else:
                    self.txt_password.clear()
                    self.txt_email.setFocus()
                return

            cliente_data = res.data[0]

            # 1. Auto-Registro Dinámico de la App
            app_id_dinamico = sincronizar_aplicacion(nombre_app="Bot_Instagram", version_app="1.0.0")
            if not app_id_dinamico:
                QMessageBox.critical(self, "Error de Sistema", "No se pudo sincronizar la aplicación con el servidor central.")
                return

            # 2. Obtener el HWID de la PC
            hwid = self.parent.register_page.obtener_hwid()

            # 3. Validar Licencia usando el ID dinámico
            check_licencia = validar_licencia_cliente(
                cliente_id=cliente_data["id"],
                app_id=app_id_dinamico,
                hwid_actual=hwid
            )

            if not check_licencia.get("valido"):
                QMessageBox.critical(self, "Licencia Requerida", check_licencia.get("mensaje", "Licencia no válida."))
                return

            # Si todo sale bien, damos acceso:
            self.parent.cliente_autorizado = cliente_data
            self.parent.licencia_autorizada = check_licencia.get("datos") or check_licencia.get("datos_licencia")
            self.parent.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error de Red", f"Fallo al conectar con el servidor: {e}")
        finally:
            self.btn_login.setText("INICIAR SESIÓN")
            self.btn_login.setEnabled(True)

    def gestionar_migracion(self, supabase, licencia, cliente, current_hwid):
        """Maneja la transferencia de licencia a una nueva PC."""
        ultimo_cambio_str = licencia.get("ultimo_cambio_hwid")
        if ultimo_cambio_str:
            ultimo_cambio = datetime.fromisoformat(ultimo_cambio_str.replace('Z', '+00:00'))
            if datetime.now(ultimo_cambio.tzinfo) - ultimo_cambio < timedelta(days=30):
                QMessageBox.critical(self, "Bloqueo de Seguridad", 
                    "Has cambiado de dispositivo recientemente.\nSolo se permite un cambio cada 30 días.")
                return

        preg = QMessageBox.question(self, "Nueva PC Detectada", 
            "Este equipo no está autorizado para tu licencia.\n¿Deseas transferirla a esta PC?\nSe enviará un código a tu correo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if preg == QMessageBox.StandardButton.Yes:
            otp = self.parent.enviar_email(
                cliente['email'], 
                "Autorización de Dispositivo", 
                "Se ha detectado un inicio de sesión desde un nuevo equipo. Código de autorización:"
            )
            if otp:
                codigo, ok = QInputDialog.getText(self, "Verificación", "Ingresa el código enviado:")
                if ok and codigo == otp:
                    supabase.table("licencias").update({
                        "hwid_pc": current_hwid,
                        "ultimo_cambio_hwid": datetime.now().isoformat()
                    }).eq("id", licencia["id"]).execute()
                    
                    QMessageBox.information(self, "Éxito", "Dispositivo actualizado con éxito.")
                    self.parent.accept()
                elif ok:
                    QMessageBox.warning(self, "Error", "Código de verificación inválido.")

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setObjectName("LoginWindow")
        self.setWindowTitle("Pegasus - Gestión de Acceso")
        self.setFixedSize(400, 550)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        # Variables para transferir datos al MainWindow
        self.cliente_autorizado = None
        self.licencia_autorizada = None

        # Inicialización de Servicios
        self.mailer = MailerService()

        # Configuración de Vistas (Stack)
        self.stack = QStackedWidget()
        self.login_page = LoginPage(self)
        self.register_page = RegisterWizard(self)
        self.forgot_page = ForgotPasswordPage(self)

        # Identificadores para QSS en las otras páginas
        self.register_page.setObjectName("RegisterWizard")
        self.forgot_page.setObjectName("ForgotPasswordPage")

        self.stack.addWidget(self.login_page)    # 0
        self.stack.addWidget(self.register_page) # 1
        self.stack.addWidget(self.forgot_page)   # 2

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    def enviar_email(self, email, asunto, texto):
        return self.mailer.enviar_otp(email, asunto, texto)

    def mostrar_registro(self): self.stack.setCurrentIndex(1)
    def mostrar_login(self): self.stack.setCurrentIndex(0)
    def mostrar_recuperacion(self): self.stack.setCurrentIndex(2)