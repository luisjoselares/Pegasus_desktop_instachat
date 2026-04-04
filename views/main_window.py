import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# Importación de tus nuevos módulos
from views.instagram_accounts_page import InstagramAccountsPage
from controllers.instagram_controller import InstagramController
from services.database_service import LocalDBService

class MainWindow(QMainWindow):
    # Se agregan argumentos opcionales para evitar el error de "positional arguments"
    def __init__(self, controller=None, user_data=None):
        super().__init__()
        
        # Guardamos las referencias del sistema original
        self.main_controller = controller
        self.user_data = user_data
        
        self.setWindowTitle("Pegasus Desktop - Instagram Chat")
        self.resize(1100, 700)
        
        # 1. Inicializar Servicios y Controladores del módulo de Instagram
        self.db_service = LocalDBService()
        self.insta_controller = InstagramController(self.db_service)
        
        # 2. Configurar Interfaz Principal
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout_principal = QHBoxLayout(self.main_widget)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)

        # 3. Sidebar (Navegación)
        self.setup_sidebar()

        # 4. Contenedor de Páginas (Stacked Widget)
        self.pages_container = QStackedWidget()
        
        # --- Instanciar Páginas ---
        # Aquí puedes poner tu vista de Dashboard actual si la tienes
        self.home_page = QWidget() 
        layout_home = QVBoxLayout(self.home_page)
        layout_home.addWidget(QLabel("<h1>Bienvenido a Pegasus</h1>"), alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nueva página de cuentas de Instagram
        self.accounts_page = InstagramAccountsPage(self.insta_controller)
        
        # Conectar el controlador con su vista para refrescar datos
        self.insta_controller.set_view(self.accounts_page)
        
        # Añadir páginas al stack
        self.pages_container.addWidget(self.home_page)      # Índice 0
        self.pages_container.addWidget(self.accounts_page)  # Índice 1
        
        self.layout_principal.addWidget(self.pages_container)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_layout.setSpacing(10)

        # Logo / Título
        lbl_logo = QLabel("PEGASUS")
        lbl_logo.setObjectName("SidebarLogo")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #00d4ff; margin: 20px 0;")
        self.sidebar_layout.addWidget(lbl_logo)

        # Botones de Navegación
        self.btn_home = QPushButton(" Inicio")
        self.btn_home.setHeight = 45
        self.btn_home.clicked.connect(lambda: self.pages_container.setCurrentIndex(0))
        
        self.btn_accounts = QPushButton(" Cuentas IG")
        self.btn_accounts.clicked.connect(lambda: self.pages_container.setCurrentIndex(1))

        self.sidebar_layout.addWidget(self.btn_home)
        self.sidebar_layout.addWidget(self.btn_accounts)
        
        self.layout_principal.addWidget(self.sidebar)