import os
import random
import subprocess
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QApplication, QStackedWidget)
from PyQt6.QtCore import Qt
from services.cloud_service import registrar_nuevo_usuario, sincronizar_aplicacion

class RegisterWizard(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.hwid = self.obtener_hwid()
        self.generated_otp = None
        self.user_pending_data = {} 
        
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QLabel#MainTitle {
                font-size: 28px;
                font-weight: 900;
                color: #FFFFFF;
                margin-bottom: 5px;
            }
            QLabel#SubTitle {
                font-size: 14px;
                color: #777777;
                margin-bottom: 25px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.03);
                color: #FFFFFF;
                font-size: 15px;
                padding: 14px 10px;
                border: none;
                border-bottom: 1px solid #333333;
                border-radius: 4px 4px 0 0;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                background-color: rgba(0, 229, 255, 0.05);
                border-bottom: 2px solid #00E5FF;
            }
            QPushButton#PrimaryPill {
                background-color: #00E5FF;
                color: #000000;
                font-weight: 800;
                font-size: 15px;
                padding: 16px;
                border-radius: 24px;
                border: none;
                margin-top: 15px;
            }
            QPushButton#PrimaryPill:hover {
                background-color: #00B3CC;
            }
            QPushButton#FlatLink {
                background-color: transparent;
                color: #777777;
                font-size: 13px;
                border: none;
                margin-top: 10px;
            }
            QPushButton#FlatLink:hover {
                color: #FFFFFF;
                text-decoration: underline;
            }
            QLineEdit#OtpBigField {
                font-size: 32px;
                letter-spacing: 15px;
                text-align: center;
                font-weight: bold;
                padding: 20px;
                border-bottom: 2px solid #555555;
            }
            QLineEdit#OtpBigField:focus {
                border-bottom: 2px solid #00E5FF;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 60, 40, 60)
        self.layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        self.page_form = QWidget()
        form_layout = QVBoxLayout(self.page_form)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Inicia tu imperio.")
        title.setObjectName("MainTitle")
        form_layout.addWidget(title)

        subtitle = QLabel("Crea tu cuenta de administrador.")
        subtitle.setObjectName("SubTitle")
        form_layout.addWidget(subtitle)

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre Completo")
        form_layout.addWidget(self.txt_nombre)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Correo Electrónico")
        form_layout.addWidget(self.txt_email)

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Contraseña (mín. 6 caracteres)")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.txt_pass)

        self.txt_pass_confirm = QLineEdit()
        self.txt_pass_confirm.setPlaceholderText("Confirmar Contraseña")
        self.txt_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.txt_pass_confirm)

        self.btn_continuar = QPushButton("Continuar")
        self.btn_continuar.setObjectName("PrimaryPill")
        self.btn_continuar.clicked.connect(self.enviar_codigo_registro)
        form_layout.addWidget(self.btn_continuar)

        self.btn_volver_form = QPushButton("Ya tengo cuenta. Iniciar sesión")
        self.btn_volver_form.setObjectName("FlatLink")
        self.btn_volver_form.clicked.connect(self.limpiar_y_volver)
        form_layout.addWidget(self.btn_volver_form)

        form_layout.addStretch()
        self.stacked_widget.addWidget(self.page_form)

        self.page_otp = QWidget()
        otp_layout = QVBoxLayout(self.page_otp)
        otp_layout.setSpacing(16)
        otp_layout.setContentsMargins(0, 0, 0, 0)

        otp_title = QLabel("Revisa tu bandeja.")
        otp_title.setObjectName("MainTitle")
        otp_layout.addWidget(otp_title)

        otp_subtitle = QLabel("Ingresa el código maestro enviado a tu correo.")
        otp_subtitle.setObjectName("SubTitle")
        otp_layout.addWidget(otp_subtitle)

        self.txt_otp = QLineEdit()
        self.txt_otp.setObjectName("OtpBigField")
        self.txt_otp.setPlaceholderText("000000")
        self.txt_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        otp_layout.addWidget(self.txt_otp)

        self.btn_validar = QPushButton("Activar Cuenta")
        self.btn_validar.setObjectName("PrimaryPill")
        self.btn_validar.clicked.connect(self.validar_codigo_registro)
        otp_layout.addWidget(self.btn_validar)

        self.btn_reenviar = QPushButton("¿No llegó? Reenviar código")
        self.btn_reenviar.setObjectName("FlatLink")
        self.btn_reenviar.clicked.connect(self.reenviar_codigo)
        otp_layout.addWidget(self.btn_reenviar)

        self.btn_volver_otp = QPushButton("Ya tengo cuenta. Iniciar sesión")
        self.btn_volver_otp.setObjectName("FlatLink")
        self.btn_volver_otp.clicked.connect(self.limpiar_y_volver)
        otp_layout.addWidget(self.btn_volver_otp)

        otp_layout.addStretch()
        self.stacked_widget.addWidget(self.page_otp)

        self.setLayout(self.layout)

    def obtener_hwid(self):
        try:
            cmd = 'wmic baseboard get serialnumber'
            return subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        except: 
            return "ID-DESCONOCIDO"

    def enviar_codigo_registro(self):
        nombre = self.txt_nombre.text().strip()
        email = self.txt_email.text().strip().lower()
        pw = self.txt_pass.text()
        pw_c = self.txt_pass_confirm.text()

        if not all([nombre, email, pw, pw_c]):
            QMessageBox.warning(self, "Campos Vacíos", "Todos los campos son obligatorios.")
            return

        if len(pw) < 6:
            QMessageBox.warning(self, "Contraseña Corta", "La contraseña debe tener al menos 6 caracteres.")
            return

        if pw != pw_c:
            QMessageBox.warning(self, "Error de Clave", "Las contraseñas no coinciden.")
            return

        self.btn_continuar.setText("ENVIANDO...")
        self.btn_continuar.setEnabled(False)
        QApplication.processEvents()

        otp = self.parent.enviar_email(
            email,
            "Verificación de Cuenta",
            f"Hola {nombre}, bienvenido a Pegasus. Usa este código para completar tu registro:"
        )

        if otp:
            self.generated_otp = otp
            self.otp_expiracion = datetime.now() + timedelta(minutes=5)
            self.user_pending_data = {"nombre": nombre, "email": email, "pw": pw}
            self.btn_reenviar.setVisible(True)
            self.btn_continuar.setText("Continuar")
            self.btn_continuar.setEnabled(True)
            self.stacked_widget.setCurrentIndex(1)
        else:
            self.btn_continuar.setText("Continuar")
            self.btn_continuar.setEnabled(True)

    def validar_codigo_registro(self):
        if getattr(self, 'otp_expiracion', None) and datetime.now() > self.otp_expiracion:
            QMessageBox.warning(self, "Código vencido", "Código vencido. Por favor, solicita un nuevo código de verificación.")
            return

        if self.txt_otp.text().strip() == self.generated_otp:
            self.registrar_en_supabase()
        else:
            QMessageBox.warning(self, "Error", "Código de verificación incorrecto.")

    def registrar_en_supabase(self):
        app_id = sincronizar_aplicacion("Bot_Instagram", "1.0.0")
        if not app_id:
            QMessageBox.critical(self, "Error de Sistema", "No se pudo sincronizar la aplicación con el servidor central.")
            return

        exp_str = self.otp_expiracion.isoformat() if getattr(self, 'otp_expiracion', None) else datetime.now().isoformat()
        resultado = registrar_nuevo_usuario(self.user_pending_data, self.hwid, app_id, exp_str)

        if not resultado.get("exito"):
            QMessageBox.critical(self, "Error DB", resultado.get("mensaje", "Error al registrar el usuario."))
            return

        QMessageBox.information(self, "Éxito", "¡Cuenta creada con éxito!")
        self.limpiar_y_volver()

    def reenviar_codigo(self):
        if not self.user_pending_data.get("email"):
            return

        nuevo_otp = f"{random.randint(0, 999999):06d}"
        self.generated_otp = nuevo_otp
        self.otp_expiracion = datetime.now() + timedelta(minutes=5)

        self.parent.enviar_email(
            self.user_pending_data["email"],
            "Reenvío de Código de Verificación Pegasus",
            f"Tu nuevo código de verificación es: {nuevo_otp}. Tienes 5 minutos para ingresarlo."
        )

        QMessageBox.information(self, "Código Enviado", "Se ha enviado un nuevo código a tu correo. Tienes 5 minutos para ingresarlo.")

    def limpiar_y_volver(self):
        self.txt_nombre.clear()
        self.txt_email.clear()
        self.txt_pass.clear()
        self.txt_pass_confirm.clear()
        self.txt_otp.clear()
        self.user_pending_data = {}
        self.generated_otp = None
        self.otp_expiracion = None

        self.btn_reenviar.setVisible(False)
        self.btn_continuar.setText("Continuar")
        self.btn_continuar.setEnabled(True)
        self.stacked_widget.setCurrentIndex(0)

        self.parent.mostrar_login()
