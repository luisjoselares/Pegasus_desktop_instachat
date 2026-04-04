import qtawesome as qta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame, 
                             QLineEdit, QTextEdit, QLabel, QScrollArea, 
                             QHBoxLayout, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize

class AddAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Configuración de Cuenta")
        self.setFixedWidth(450)
        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel("<b>Usuario / Correo de Instagram:</b>"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("ejemplo_user")
        self.layout.addWidget(self.user_input)

        self.layout.addWidget(QLabel("<b>Contraseña:</b>"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.pass_input)

        self.layout.addWidget(QLabel("<b>Contexto de IA (System Prompt):</b>"))
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("Ej: Eres un vendedor amable especializado en repuestos...")
        self.layout.addWidget(self.context_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        return {
            "user": self.user_input.text(),
            "pass": self.pass_input.text(),
            "prompt": self.context_input.toPlainText()
        }

class AccountCard(QFrame):
    def __init__(self, data, controller):
        super().__init__()
        self.account_id = data[0]
        self.controller = controller
        self.setObjectName("AccountCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- CABECERA ---
        self.header_btn = QPushButton()
        self.header_btn.setObjectName("HeaderBtn")
        self.header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_btn.clicked.connect(self.toggle_content)
        
        # Layout interno para la cabecera (Icono + Texto + Descripción)
        header_layout = QHBoxLayout(self.header_btn)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.user-circle', color='#00d4ff').pixmap(QSize(24, 24)))
        
        text_container = QVBoxLayout()
        self.lbl_user = QLabel(f"<b>{data[1]}</b>")
        self.lbl_user.setStyleSheet("color: white; font-size: 14px; border: none;")
        
        # Descripción corta basada en el prompt
        prompt_snippet = data[4][:60] + "..." if data[4] else "Sin contexto de IA configurado"
        self.lbl_desc = QLabel(prompt_snippet)
        self.lbl_desc.setStyleSheet("color: #888; font-size: 11px; border: none;")
        
        text_container.addWidget(self.lbl_user)
        text_container.addWidget(self.lbl_desc)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_container)
        header_layout.addStretch()
        
        # Icono de flecha para indicar que es expandible
        self.arrow_label = QLabel()
        self.arrow_label.setPixmap(qta.icon('fa5s.chevron-down', color='#444').pixmap(QSize(12, 12)))
        header_layout.addWidget(self.arrow_label)
        
        layout.addWidget(self.header_btn)

        # --- CUERPO (ACORDEÓN) ---
        self.content_frame = QFrame()
        self.content_frame.setObjectName("ContentFrame")
        self.content_frame.setVisible(False)
        c_layout = QVBoxLayout(self.content_frame)

        # Campos de edición
        c_layout.addWidget(QLabel("<b>Configuración de IA para esta cuenta:</b>"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setText(data[4])
        self.prompt_edit.setMinimumHeight(120)
        c_layout.addWidget(self.prompt_edit)

        # Botones de Acción
        actions = QHBoxLayout()
        
        btn_save = QPushButton(qta.icon('fa5s.save', color='white'), " Guardar Cambios")
        btn_save.clicked.connect(self.save_data)
        
        btn_del = QPushButton(qta.icon('fa5s.trash-alt', color='white'), " Eliminar")
        btn_del.setObjectName("DeleteBtn")
        btn_del.clicked.connect(lambda: self.controller.delete_account(self.account_id))
        
        actions.addWidget(btn_save)
        actions.addStretch()
        actions.addWidget(btn_del)
        c_layout.addLayout(actions)

        layout.addWidget(self.content_frame)

    def toggle_content(self):
        is_visible = self.content_frame.isVisible()
        self.content_frame.setVisible(not is_visible)
        # Cambiar icono de flecha
        icon_name = 'fa5s.chevron-up' if not is_visible else 'fa5s.chevron-down'
        self.arrow_label.setPixmap(qta.icon(icon_name, color='#00d4ff').pixmap(QSize(12, 12)))

    def save_data(self):
        new_prompt = self.prompt_edit.toPlainText()
        self.controller.update_account_context(self.account_id, new_prompt)

class InstagramAccountsPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Header de la página
        top_bar = QHBoxLayout()
        lbl_title = QLabel("<h2>Gestión de Cuentas</h2>")
        
        self.btn_add = QPushButton(qta.icon('fa5s.plus-circle', color='black'), " Nueva Cuenta")
        self.btn_add.setObjectName("AddButton")
        self.btn_add.setFixedWidth(160)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.open_add_dialog)
        
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_add)
        self.main_layout.addLayout(top_bar)

        # Scroll Area para las tarjetas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        
        self.main_layout.addWidget(self.scroll)

    def open_add_dialog(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            d = dialog.get_data()
            if d["user"]: # Validación simple
                self.controller.add_account(d["user"], d["pass"], d["prompt"])

    def load_accounts(self, accounts):
        # Limpiar Layout de forma segura
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if not accounts:
            empty_lbl = QLabel("No hay cuentas configuradas.\nPresiona el botón superior para agregar una.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #555; font-size: 14px; margin-top: 100px;")
            self.cards_layout.addWidget(empty_lbl)
            return

        for acc in accounts:
            card = AccountCard(acc, self.controller)
            self.cards_layout.addWidget(card)