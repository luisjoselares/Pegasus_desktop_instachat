import os
import qtawesome as qta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt, QSize
from views.accounts_page import AccountsPage

class MainWindow(QMainWindow):
    def __init__(self, cliente_data, hwid):
        super().__init__()
        self.setObjectName("MainWindow")
        self.cliente_data = cliente_data
        self.hwid = hwid
        
        # Título dinámico con el nombre del cliente
        nombre_cliente = cliente_data.get('nombre_completo', 'Usuario')
        self.setWindowTitle(f"Pegasus ERP - {nombre_cliente}")
        self.setMinimumSize(1100, 750)

        # Layout Principal (Horizontal: Sidebar + Contenido)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        self.init_sidebar()
        main_layout.addWidget(self.sidebar)

        # --- 2. ÁREA DE CONTENIDO (PÁGINAS) ---
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("content_area")
        
        # Inicialización de Páginas
        self.page_accounts = AccountsPage(self.hwid)
        # Aquí podrías inicializar las otras páginas cuando las tengas:
        # self.page_bot = BotManagerPage() 
        # self.page_logs = LogsPage()

        self.content_area.addWidget(self.page_accounts) # Índice 0
        
        main_layout.addWidget(self.content_area)

        # Conectar botones a la navegación
        self.btn_acc.clicked.connect(lambda: self.cambiar_pagina(0, self.btn_acc))
        # self.btn_bot.clicked.connect(lambda: self.cambiar_pagina(1, self.btn_bot))
        # self.btn_log.clicked.connect(lambda: self.cambiar_pagina(2, self.btn_log))

    def init_sidebar(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 40, 0, 20) # Margen 0 a los lados para el border-left del CSS
        layout.setSpacing(5)

        # Header Sidebar
        lbl_logo = QLabel("PEGASUS")
        lbl_logo.setStyleSheet("font-size: 28px; font-weight: bold; color: #00E5FF; padding-left: 25px;")
        layout.addWidget(lbl_logo)
        
        lbl_ver = QLabel("SISTEMA DE AUTOMATIZACIÓN")
        lbl_ver.setStyleSheet("color: #555; font-size: 9px; letter-spacing: 1px; padding-left: 25px; margin-bottom: 40px;")
        layout.addWidget(lbl_ver)

        # Botones de Navegación con QtAwesome
        # Usamos el prefijo 'fa5s' para FontAwesome 5 Solid
        self.btn_acc = self.crear_nav_btn("Cuentas Instagram", "fa5s.users", True)
        self.btn_bot = self.crear_nav_btn("Bot Manager", "fa5s.robot", False)
        self.btn_log = self.crear_nav_btn("Historial / Logs", "fa5s.clipboard-list", False)
        
        layout.addWidget(self.btn_acc)
        layout.addWidget(self.btn_bot)
        layout.addWidget(self.btn_log)

        layout.addStretch()

        # Footer Sidebar: Info del Usuario
        user_container = QFrame()
        user_container.setStyleSheet("background-color: #151515; border-top: 1px solid #252525; padding: 15px;")
        user_layout = QVBoxLayout(user_container)
        
        primer_nombre = self.cliente_data['nombre_completo'].split()[0]
        user_info = QLabel(f"Conectado como:\n{primer_nombre}")
        user_info.setStyleSheet("color: #00E5FF; font-size: 11px; border: none;")
        user_layout.addWidget(user_info)

        self.btn_logout = QPushButton(" SALIR")
        self.btn_logout.setIcon(qta.icon("fa5s.sign-out-alt", color="#FF5252"))
        self.btn_logout.setObjectName("logout_btn")
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.close)
        user_layout.addWidget(self.btn_logout)
        
        layout.addWidget(user_container)

    def crear_nav_btn(self, texto, icon_name, activo):
        # Creamos el icono con el color cian corporativo de Pegasus
        icon = qta.icon(icon_name, color="#BBBBBB", color_active="#00E5FF")
        
        btn = QPushButton(texto)
        btn.setObjectName("nav_btn")
        btn.setIcon(icon)
        btn.setIconSize(QSize(18, 18))
        btn.setCheckable(True)
        btn.setAutoExclusive(True) # Solo uno puede estar marcado a la vez
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(50)
        
        if activo:
            btn.setChecked(True)
        
        return btn

    def cambiar_pagina(self, index, boton_activo):
        self.content_area.setCurrentIndex(index)
        # El resto de botones se desmarcan solos gracias a setAutoExclusive(True)