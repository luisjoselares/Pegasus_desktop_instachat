import os
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QApplication)
from PyQt6.QtCore import Qt
from supabase import create_client, Client
from dotenv import load_dotenv

class RegisterWizard(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.hwid = self.obtener_hwid()
        self.generated_otp = None
        self.user_pending_data = {} 
        
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(30, 40, 30, 40)

        title = QLabel("CREAR CUENTA PEGASUS")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00E5FF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)

        # Campos de Datos
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre Completo")
        self.layout.addWidget(self.txt_nombre)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Correo Electrónico")
        self.layout.addWidget(self.txt_email)

        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Contraseña (mín. 6 caracteres)")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.txt_pass)

        self.txt_pass_confirm = QLineEdit()
        self.txt_pass_confirm.setPlaceholderText("Confirmar Contraseña")
        self.txt_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.txt_pass_confirm)

        # Sección OTP
        self.otp_container = QWidget()
        otp_layout = QVBoxLayout(self.otp_container)
        otp_layout.setContentsMargins(0, 10, 0, 10)
        
        lbl_info = QLabel("Introduce el código enviado a tu correo:")
        lbl_info.setStyleSheet("color: #00E5FF; font-size: 11px;")
        self.txt_otp = QLineEdit()
        self.txt_otp.setPlaceholderText("Código de 6 dígitos")
        self.txt_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_otp.setStyleSheet("font-size: 18px; letter-spacing: 5px;")
        
        otp_layout.addWidget(lbl_info)
        otp_layout.addWidget(self.txt_otp)
        self.otp_container.setVisible(False)
        self.layout.addWidget(self.otp_container)

        # Botones
        self.btn_main = QPushButton("ENVIAR CÓDIGO DE VERIFICACIÓN")
        self.btn_main.clicked.connect(self.gestionar_flujo_registro)
        self.layout.addWidget(self.btn_main)

        btn_back = QPushButton("Volver al Login")
        btn_back.setStyleSheet("background: transparent; color: #888888; border: none;")
        btn_back.clicked.connect(self.parent.mostrar_login)
        self.layout.addWidget(btn_back)

        self.setLayout(self.layout)

    def obtener_hwid(self):
        try:
            cmd = 'wmic baseboard get serialnumber'
            return subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        except: 
            return "ID-DESCONOCIDO"

    def gestionar_flujo_registro(self):
        if not self.generated_otp:
            nombre = self.txt_nombre.text().strip()
            email = self.txt_email.text().strip()
            pw = self.txt_pass.text()
            pw_c = self.txt_pass_confirm.text()

            # Validaciones de entrada
            if not all([nombre, email, pw, pw_c]):
                QMessageBox.warning(self, "Campos Vacíos", "Todos los campos son obligatorios.")
                return
            
            if len(pw) < 6:
                QMessageBox.warning(self, "Contraseña Corta", "La contraseña debe tener al menos 6 caracteres.")
                return

            if pw != pw_c:
                QMessageBox.warning(self, "Error de Clave", "Las contraseñas no coinciden.")
                return

            self.btn_main.setText("ENVIANDO...")
            self.btn_main.setEnabled(False)
            QApplication.processEvents()

            # Llamamos al servicio central
            otp = self.parent.enviar_email(
                email, 
                "Verificación de Cuenta", 
                f"Hola {nombre}, bienvenido a Pegasus. Usa este código para completar tu registro:"
            )

            if otp:
                self.generated_otp = otp
                self.user_pending_data = {"nombre": nombre, "email": email, "pw": pw}
                
                self.txt_nombre.setEnabled(False)
                self.txt_email.setEnabled(False)
                self.txt_pass.setVisible(False)
                self.txt_pass_confirm.setVisible(False)
                self.otp_container.setVisible(True)
                self.btn_main.setText("FINALIZAR REGISTRO")
                self.btn_main.setEnabled(True)
            else:
                self.btn_main.setText("ENVIAR CÓDIGO DE VERIFICACIÓN")
                self.btn_main.setEnabled(True)
        else:
            if self.txt_otp.text().strip() == self.generated_otp:
                self.registrar_en_supabase()
            else:
                QMessageBox.warning(self, "Error", "Código de verificación incorrecto.")

    def registrar_en_supabase(self):
        try:
            load_dotenv()
            supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            
            d = self.user_pending_data
            
            c_res = supabase.table("clientes").insert({
                "nombre_completo": d["nombre"],
                "email": d["email"],
                "password": d["pw"]
            }).execute()
            
            cid = c_res.data[0]["id"]

            l_res = supabase.table("licencias").insert({
                "cliente_id": cid,
                "app_id": 1, 
                "fecha_vencimiento": "2026-12-31",
                "estado": "ACTIVO",
                "hwid_pc": self.hwid
            }).execute()

            supabase.table("pagos").insert({
                "cliente_id": cid,
                "licencia_id": l_res.data[0]["id"],
                "monto": 0,
                "metodo_pago": "REGISTRO_WEB",
                "referencia": "VERIFICADO",
                "fecha_transferencia": "2026-04-03"
            }).execute()

            QMessageBox.information(self, "Éxito", "¡Cuenta creada con éxito!")
            self.parent.mostrar_login()
            
        except Exception as e:
            QMessageBox.critical(self, "Error DB", str(e))