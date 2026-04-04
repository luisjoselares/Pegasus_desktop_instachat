from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame, 
                             QLineEdit, QTextEdit, QLabel, QScrollArea, QHBoxLayout)
from PyQt6.QtCore import Qt

class AccountCard(QFrame):
    def __init__(self, data, parent_controller):
        super().__init__()
        self.account_id = data[0]
        self.controller = parent_controller
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("AccountCard")
        
        self.main_layout = QVBoxLayout(self)
        
        # --- Cabecera del Acordeón ---
        self.header = QPushButton(f"👤 {data[1]}")
        self.header.clicked.connect(self.toggle_content)
        self.main_layout.addWidget(self.header)
        
        # --- Contenido Expandible ---
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        
        # Login y Password
        self.content_layout.addWidget(QLabel("Usuario:"))
        self.user_input = QLineEdit(data[1])
        
        self.content_layout.addWidget(QLabel("Contraseña:"))
        self.pass_input = QLineEdit(data[2])
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Lógica de Contexto para Groq
        self.content_layout.addWidget(QLabel("Contexto de IA (System Prompt):"))
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("Ej: Eres un vendedor amable especializado en repuestos...")
        self.context_input.setText(data[4] if data[4] else "")
        
        # Botones de Acción
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Guardar Cambios")
        self.save_btn.clicked.connect(self.save_data)
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.setObjectName("DeleteBtn")
        self.delete_btn.clicked.connect(lambda: self.controller.delete_account(self.account_id))
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        self.content_layout.addLayout(btn_layout)
        
        self.main_layout.addWidget(self.content_frame)
        self.content_frame.setVisible(False) # Oculto por defecto

    def toggle_content(self):
        visible = self.content_frame.isVisible()
        self.content_frame.setVisible(not visible)

    def save_data(self):
        # Aquí llamarías al controlador para actualizar
        self.controller.update_account_context(self.account_id, self.context_input.toPlainText())

class InstagramAccountsPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.layout = QVBoxLayout(self)
        
        # Área de Scroll para las tarjetas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(QLabel("<h2>Gestión de Cuentas</h2>"))
        self.layout.addWidget(self.scroll)
        
        # Botón para añadir nueva cuenta
        self.add_btn = QPushButton("+ Agregar Nueva Cuenta")
        self.layout.addWidget(self.add_btn)

    def load_accounts(self, accounts):
        # Limpiar layout
        for i in reversed(range(self.cards_layout.count())): 
            self.cards_layout.itemAt(i).widget().setParent(None)
        
        # Crear tarjetas
        for acc in accounts:
            card = AccountCard(acc, self.controller)
            self.cards_layout.addWidget(card)