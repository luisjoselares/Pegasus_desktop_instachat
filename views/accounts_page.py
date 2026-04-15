import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QAbstractItemView)
from services.security_service import SecurityService
from views.components import PegasusPrimaryButton
from services.database_service import LocalDBService
from views.dialogs.alerts_dialog import AlertsDialog
from PyQt6.QtCore import Qt

class AccountsPage(QWidget):
    def __init__(self, hwid):
        super().__init__()
        self.setObjectName("AccountsPage") # Para vinculación con QSS
        self.db = LocalDBService()
        self.cipher = SecurityService(hwid)
        self.account_ids = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Título de sección
        header = QLabel("GESTIÓN DE CUENTAS E IP (PROXIES)")
        header.setStyleSheet("font-size: 20px; color: #00E5FF; font-weight: bold;")
        layout.addWidget(header)

        tasa_layout = QHBoxLayout()
        tasa_layout.setContentsMargins(0, 0, 0, 0)
        tasa_layout.setSpacing(10)

        tasa_label = QLabel("Tasa de Cambio Global (Bs por USD):")
        tasa_label.setStyleSheet("color: #A0A0A0;")
        tasa_layout.addWidget(tasa_label)

        self.txt_tasa = QLineEdit()
        self.txt_tasa.setPlaceholderText("Ej: 38.5")
        self.txt_tasa.setStyleSheet(
            "QLineEdit { background-color: #121212; color: #FFFFFF; border: 1px solid #333333; border-radius: 8px; padding: 8px; }"
            "QLineEdit:focus { border: 1px solid #00E5FF; }"
        )
        self.txt_tasa.setFixedWidth(160)
        tasa_layout.addWidget(self.txt_tasa)

        btn_save_tasa = QPushButton("Actualizar Tasa")
        btn_save_tasa.setObjectName("PrimaryBtn")
        btn_save_tasa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_tasa.clicked.connect(self._guardar_tasa_global)
        tasa_layout.addWidget(btn_save_tasa)

        self.btn_ver_alertas = QPushButton("Ver alertas")
        self.btn_ver_alertas.setObjectName("PrimaryBtn")
        self.btn_ver_alertas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ver_alertas.clicked.connect(self.mostrar_alertas)
        tasa_layout.addWidget(self.btn_ver_alertas)

        current_tasa = self.db.get_global_setting('tasa_cambio', '')
        if current_tasa:
            self.txt_tasa.setText(current_tasa)

        layout.addLayout(tasa_layout)

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
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.empty_state_container = QWidget()
        self.empty_state_container.setObjectName("emptyStateContainer")
        empty_layout = QVBoxLayout(self.empty_state_container)
        empty_layout.setContentsMargins(0, 60, 0, 60)
        empty_layout.setSpacing(18)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.inbox', color='rgba(255,255,255,0.30)').pixmap(72, 72))
        icon_label.setStyleSheet("background: transparent; border: none;")
        empty_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        empty_text = QLabel("Aún no hay cuentas registradas")
        empty_text.setStyleSheet("color: #B0B0B0; font-size: 18px; font-weight: 700;")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)

        self.empty_action_btn = PegasusPrimaryButton("Añadir Cuenta")
        self.empty_action_btn.clicked.connect(self.open_add_dialog)
        self.empty_action_btn.setFixedWidth(180)
        empty_layout.addWidget(self.empty_action_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(self.empty_state_container)
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
        self.db.agregar_cuenta({
            'user': user,
            'pass': pass_enc,
            'proxy': proxy,
            'prompt': '',
            'type': 'Vendedor de tienda',
            'start': '08:00',
            'end': '18:00'
        })
        
        # Limpieza y refresco
        self.txt_user.clear(); self.txt_pass.clear(); self.txt_proxy.clear()
        self.cargar_tabla()
        QMessageBox.information(self, "Pegasus", "Cuenta de Instagram vinculada localmente.")

    def cargar_tabla(self):
        cuentas = self.db.obtener_cuentas()
        self.account_ids = []
        self.tabla.setRowCount(len(cuentas))

        if len(cuentas) > 0:
            self.empty_state_container.hide()
            self.tabla.show()
        else:
            self.empty_state_container.show()
            self.tabla.hide()
        
        for i, cuenta in enumerate(cuentas):
            id_c = cuenta.get('id')
            self.account_ids.append(id_c)
            user = cuenta.get('insta_user', '')
            proxy = cuenta.get('proxy', '')

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

    def _guardar_tasa_global(self):
        value = self.txt_tasa.text().strip()
        if not value:
            QMessageBox.warning(self, "Error", "Ingresa un valor válido para la tasa.")
            return

        self.db.set_global_setting('tasa_cambio', value)
        QMessageBox.information(
            self,
            "Pegasus",
            f"La tasa global se ha actualizado a {value} y se aplicará a todos los bots."
        )

    def mostrar_alertas(self):
        selected_row = self.tabla.currentRow()
        account_id = None
        account_name = None
        if selected_row >= 0 and selected_row < len(self.account_ids):
            account_id = self.account_ids[selected_row]
            account_name = self.tabla.item(selected_row, 0).text() if self.tabla.item(selected_row, 0) else None
        elif len(self.account_ids) == 1:
            account_id = self.account_ids[0]
            account_name = self.tabla.item(0, 0).text() if self.tabla.item(0, 0) else None

        dialog = AlertsDialog(self, account_id=account_id, account_name=account_name)
        dialog.exec()
