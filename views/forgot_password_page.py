import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QApplication)
from PyQt6.QtCore import Qt
from supabase import create_client, Client
from dotenv import load_dotenv

class ForgotPasswordPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.generated_otp = None
        self.user_email = None
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 40, 30, 40)

        title = QLabel("RECUPERAR ACCESO")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00E5FF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Tu correo registrado")
        layout.addWidget(self.txt_email)

        self.txt_otp = QLineEdit()
        self.txt_otp.setPlaceholderText("Código de 6 dígitos")
        self.txt_otp.setVisible(False)
        layout.addWidget(self.txt_otp)

        self.txt_new_pass = QLineEdit()
        self.txt_new_pass.setPlaceholderText("Nueva Contraseña (mín. 6 caracteres)")
        self.txt_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_pass.setVisible(False)
        layout.addWidget(self.txt_new_pass)

        self.btn_action = QPushButton("ENVIAR CÓDIGO")
        self.btn_action.clicked.connect(self.gestionar_recuperacion)
        layout.addWidget(self.btn_action)

        btn_back = QPushButton("Cancelar")
        btn_back.setStyleSheet("background: transparent; color: #888888; border: none;")
        btn_back.clicked.connect(self.parent.mostrar_login)
        layout.addWidget(btn_back)

        self.setLayout(layout)

    def gestionar_recuperacion(self):
        load_dotenv()
        supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        if not self.generated_otp:
            email = self.txt_email.text().strip()
            if not email: return
            
            self.btn_action.setText("BUSCANDO...")
            self.btn_action.setEnabled(False)
            QApplication.processEvents()

            try:
                res = supabase.table("clientes").select("id").eq("email", email).execute()
                if not res.data:
                    QMessageBox.warning(self, "Error", "Este correo no está registrado.")
                    return

                otp = self.parent.enviar_email(
                    email,
                    "Recuperación de Contraseña",
                    "Usa el siguiente código para restablecer tu contraseña en Pegasus:"
                )

                if otp:
                    self.user_email = email
                    self.generated_otp = otp
                    self.txt_email.setEnabled(False)
                    self.txt_otp.setVisible(True)
                    self.txt_new_pass.setVisible(True)
                    self.btn_action.setText("RESTABLECER CONTRASEÑA")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                self.btn_action.setEnabled(True)
                if not self.generated_otp: self.btn_action.setText("ENVIAR CÓDIGO")
            
        else:
            if self.txt_otp.text().strip() == self.generated_otp:
                new_pw = self.txt_new_pass.text()
                
                if len(new_pw) < 6:
                    QMessageBox.warning(self, "Contraseña Corta", "La nueva contraseña debe tener al menos 6 caracteres.")
                    return
                
                try:
                    supabase.table("clientes").update({"password": new_pw}).eq("email", self.user_email).execute()
                    QMessageBox.information(self, "Éxito", "Contraseña actualizada correctamente.")
                    self.parent.mostrar_login()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo actualizar: {e}")
            else:
                QMessageBox.warning(self, "Error", "Código incorrecto.")