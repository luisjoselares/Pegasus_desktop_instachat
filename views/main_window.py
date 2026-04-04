import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt, QSize
import qtawesome as qta # Asegúrate de tenerlo instalado: pip install qtawesome

from views.instagram_accounts_page import InstagramAccountsPage
from controllers.instagram_controller import InstagramController
from services.database_service import LocalDBService

class MainWindow(QMainWindow):
    def __init__(self, controller=None, user_data=None):
        super().__init__()
        self.main_controller = controller
        self.user_data = user_data
        
        self.setWindowTitle("Pegasus Desktop - Instagram Chat")
        self.resize(1100, 700)
        
        # 1. Inicializar Servicios
        self.db_service = LocalDBService()
        self.insta_controller = InstagramController(self.db_service)
        
        # 2. Configurar Layout Base (Horizontal)
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout_principal = QHBoxLayout(self.main_widget)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)

        # 3. PRIMERO: Crear el contenedor de páginas
        self.pages_container = QStackedWidget()
        
        # 4. SEGUNDO: Configurar el Sidebar (Ahora ya puede ver a pages_container)
        self.setup_sidebar()

        # 5. TERCERO: Configurar las páginas
        self.home_page = QWidget() 
        # (Aquí podrías poner tu contenido de inicio)
        
        self.accounts_page = InstagramAccountsPage(self.insta_controller)
        self.insta_controller.set_view(self.accounts_page)
        
        # Añadir al stack
        self.pages_container.addWidget(self.home_page)      # Índice 0
        self.pages_container.addWidget(self.accounts_page)  # Índice 1
        
        # 6. CUARTO: Añadir el stack al layout principal (a la derecha del sidebar)
        self.layout_principal.addWidget(self.pages_container)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 10)

        # Logo
        lbl_logo = QLabel("PEGASUS")
        lbl_logo.setObjectName("SidebarLogo")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("font-size: 22px; font-weight: bold; color: #00d4ff; margin-bottom: 30px;")
        self.sidebar_layout.addWidget(lbl_logo)

        # Botones con Iconos corregidos
        icon_home = qta.icon('fa5s.home', color='#e0e0e0')
        self.btn_home = QPushButton(icon_home, "  Inicio")
        self.btn_home.setIconSize(QSize(18, 18))
        self.btn_home.setFixedHeight(45)
        self.btn_home.clicked.connect(lambda: self.pages_container.setCurrentIndex(0))
        
        icon_insta = qta.icon('fa5b.instagram', color='#e0e0e0')
        self.btn_accounts = QPushButton(icon_insta, "  Cuentas IG")
        self.btn_accounts.setIconSize(QSize(18, 18))
        self.btn_accounts.setFixedHeight(45)
        self.btn_accounts.clicked.connect(lambda: self.pages_container.setCurrentIndex(1))

        self.sidebar_layout.addWidget(self.btn_home)
        self.sidebar_layout.addWidget(self.btn_accounts)
        
        # IMPORTANTE: Añadir el sidebar al layout principal
        self.layout_principal.addWidget(self.sidebar)