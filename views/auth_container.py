from PyQt6.QtWidgets import QDialog, QVBoxLayout, QStackedWidget, QWidget, QApplication
from PyQt6.QtCore import Qt
from views.login_page import LoginPage # Separaremos la lógica de login
from views.register_wizard import RegisterWizard # El nuevo Wizard

class AuthWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pegasus - Autenticación")
        self.setFixedSize(400, 550) # Un poco más alto para el Wizard
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        # El "Cerebro" que cambia las vistas
        self.stack = QStackedWidget()
        
        # Instanciamos las páginas
        self.login_page = LoginPage(self)
        self.register_wizard = RegisterWizard(self)
        
        # Las añadimos al stack
        self.stack.addWidget(self.login_page)    # Índice 0
        self.stack.addWidget(self.register_wizard) # Índice 1
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def mostrar_registro(self):
        """Cambia a la vista del Wizard."""
        self.stack.setCurrentIndex(1)

    def mostrar_login(self):
        """Vuelve a la vista de Login."""
        self.stack.setCurrentIndex(0)