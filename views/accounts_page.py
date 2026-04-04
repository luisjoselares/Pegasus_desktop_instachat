from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox)
from services.security_service import SecurityService
from services.database_service import LocalDBService
from PyQt6.QtCore import Qt

class AccountsPage(QWidget):
    def __init__(self, hwid):
        super().__init__()
        self.setObjectName("AccountsPage") # Para vinculación con QSS
        self.db = LocalDBService()
        self.cipher = SecurityService(hwid)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título de sección
        header = QLabel("GESTIÓN DE CUENTAS E IP (PROXIES)")
        header.setStyleSheet("font-size: 20px; color: #00E5FF; font-weight: bold;")
        layout.addWidget(header)

        # Formulario de entrada
        form_container = QVBoxLayout()
        form_container.setSpacing(10)
        
        row1 = QHBoxLayout()
        self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("Usuario de Instagram")
        self.txt_pass = QLineEdit(); self.txt_pass.setPlaceholderText("Contraseña")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        row1.addWidget(self.txt_user)
        row1.addWidget(self.txt_pass)

        row2 = QHBoxLayout()
        self.txt_proxy = QLineEdit()
        self.txt_proxy.setPlaceholderText("Proxy (Ej: usuario:pass@ip:puerto o ip:puerto)")
        btn_add = QPushButton("AÑADIR CUENTA")
        btn_add.clicked.connect(self.guardar_cuenta)
        row2.addWidget(self.txt_proxy, 3) # El campo proxy es más ancho
        row2.addWidget(btn_add, 1)
        
        form_container.addLayout(row1)
        form_container.addLayout(row2)
        layout.addLayout(form_container)

        # Tabla de Cuentas Configuradas
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["USUARIO", "SEGURIDAD", "PROXY / IP", "ACCIONES"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)
        
        self.cargar_tabla()

    def guardar_cuenta(self):
        user = self.txt_user.text().strip()
        password = self.txt_pass.text().strip()
        proxy = self.txt_proxy.text().strip()
        
        if not user or not password:
            QMessageBox.warning(self, "Error", "Usuario y contraseña son requeridos.")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Seguridad", "La contraseña debe tener al menos 6 caracteres.")
            return

        # Encriptamos la clave localmente antes de guardar
        pass_enc = self.cipher.encrypt(password)
        self.db.agregar_cuenta(user, pass_enc, proxy)
        
        # Limpieza y refresco
        self.txt_user.clear(); self.txt_pass.clear(); self.txt_proxy.clear()
        self.cargar_tabla()
        QMessageBox.information(self, "Pegasus", "Cuenta de Instagram vinculada localmente.")

    def cargar_tabla(self):
        cuentas = self.db.obtener_cuentas()
        self.tabla.setRowCount(len(cuentas))
        
        for i, (id_c, user, p_enc, proxy) in enumerate(cuentas):
            # Usuario
            self.tabla.setItem(i, 0, QTableWidgetItem(user))
            
            # Estado de seguridad
            item_sec = QTableWidgetItem("ENCRIPTADO 🔒")
            item_sec.setForeground(Qt.GlobalColor.green)
            self.tabla.setItem(i, 1, item_sec)
            
            # Proxy (si no hay, mostrar 'IP Local')
            proxy_display = proxy if proxy else "IP Local (Sin Proxy)"
            self.tabla.setItem(i, 2, QTableWidgetItem(proxy_display))
            
            # Botón para eliminar
            btn_del = QPushButton("ELIMINAR")
            btn_del.setStyleSheet("background-color: #C62828; font-size: 10px; padding: 5px;")
            btn_del.clicked.connect(lambda _, id=id_c: self.eliminar(id))
            self.tabla.setCellWidget(i, 3, btn_del)

    def eliminar(self, id_cuenta):
        confirm = QMessageBox.question(self, "Confirmar", "¿Eliminar esta cuenta de la base de datos local?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.eliminar_cuenta(id_cuenta)
            self.cargar_tabla()