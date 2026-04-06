import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QStackedWidget, QLabel, QFrame,
                             QDialog, QLineEdit, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt, QSize
import qtawesome as qta # Asegúrate de tenerlo instalado: pip install qtawesome

from views.instagram_accounts_page import InstagramAccountsPage
from views.log_dialog import LogDialog
from controllers.instagram_controller import InstagramController
from controllers.main_controller import MainController
from services.database_service import LocalDBService
from services.instagram_service import InstagramService
from services.security_service import SecurityService

class MainWindow(QMainWindow):
    def __init__(self, cliente_data=None, licencia_data=None, hwid=None):
        super().__init__()
        self.cliente_data = cliente_data
        self.licencia_data = licencia_data
        self.hwid = hwid
        self.user_data = None
        self.security_service = SecurityService(self.hwid)
        self.current_cliente_id = self.cliente_data.get('id') if self.cliente_data else None
        self.last_admin_unlock = None
        self.admin_session_duration = timedelta(minutes=5)
        
        self.setWindowTitle("Pegasus Desktop - Instagram Chat")
        self.resize(1100, 700)
        
        # 1. Inicializar Servicios
        self.db_service = LocalDBService()
        self.db_service.limpiar_cuentas_huerfanas(self.current_cliente_id)
        self.shared_engine = InstagramService()
        if self.licencia_data and hasattr(self.shared_engine, 'set_licencia_id'):
            self.shared_engine.set_licencia_id(self.licencia_data.get('id'))
        if hasattr(self.shared_engine, 'set_cliente_id'):
            self.shared_engine.set_cliente_id(self.current_cliente_id)

        # 2. Configurar Layout Base (Horizontal)
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout_principal = QHBoxLayout(self.main_widget)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)

        # 3. PRIMERO: Crear el contenedor de páginas
        self.pages_container = QStackedWidget()
        
        # 4. SEGUNDO: Configurar el Sidebar (Ahora ya puede ver a pages_container)
        self.log_dialog = LogDialog(self)
        self.setup_sidebar()

        # 5. TERCERO: Configurar las páginas
        self.home_page = QWidget()
        self._build_home_page()

        self.insta_controller = InstagramController(
            self.db_service,
            engine=self.shared_engine,
            security_service=self.security_service,
            cliente_id=self.current_cliente_id
        )
        self.main_controller = MainController(
            self,
            cliente_data,
            licencia_data,
            engine=self.shared_engine,
            cliente_id=self.current_cliente_id,
            security_service=self.security_service,
            db_service=self.db_service
        )
        self.insta_controller.set_main_controller(self.main_controller)

        self.accounts_page = InstagramAccountsPage(self.insta_controller, main_window=self)
        self.insta_controller.set_view(self.accounts_page, self.current_cliente_id)

        # Añadir al stack
        self.pages_container.addWidget(self.home_page)      # Índice 0
        self.pages_container.addWidget(self.accounts_page)  # Índice 1

        self.pages_container.currentChanged.connect(self.on_page_changed)

        # 6. CUARTO: Añadir el stack al layout principal (a la derecha del sidebar)
        self.layout_principal.addWidget(self.pages_container)

        # Si existe una cuenta con bot habilitado, intenta iniciar automáticamente.
        self.main_controller.auto_start_if_enabled()

    def _build_home_page(self):
        layout = QVBoxLayout(self.home_page)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(18)

        self.lbl_welcome = QLabel("Bienvenido, nuestro agente Pegasus")
        self.lbl_welcome.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: 800;")
        layout.addWidget(self.lbl_welcome)

        self.lbl_license_status = QLabel("Licencia: Cargando datos...")
        self.lbl_license_status.setStyleSheet("color: #00E5FF; font-size: 13px; margin-bottom: 20px;")
        layout.addWidget(self.lbl_license_status)

        self.tx_info = QLabel(
            "Usa el panel de Cuentas IG para añadir una cuenta, luego pulsa Iniciar Bot para comenzar a atender mensajes automáticos."
        )
        self.tx_info.setWordWrap(True)
        self.tx_info.setStyleSheet("color: #AAAAAA; font-size: 12px; margin-bottom: 20px;")
        layout.addWidget(self.tx_info)

        self.tx_info = QLabel(
            "En esta pantalla verás el estado de tu licencia. Navega a Cuentas IG para administrar agentes y activar el bot."
        )
        self.tx_info.setWordWrap(True)
        self.tx_info.setStyleSheet("color: #AAAAAA; font-size: 12px; margin-bottom: 20px;")
        layout.addWidget(self.tx_info)

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
        self.btn_home.setCheckable(True)
        self.btn_home.clicked.connect(lambda: self.show_page(0))
        
        icon_insta = qta.icon('fa5b.instagram', color='#e0e0e0')
        self.btn_accounts = QPushButton(icon_insta, "  Cuentas IG")
        self.btn_accounts.setIconSize(QSize(18, 18))
        self.btn_accounts.setFixedHeight(45)
        self.btn_accounts.setCheckable(True)
        self.btn_accounts.clicked.connect(lambda: self.show_page(1))

        self.sidebar_layout.addWidget(self.btn_home)
        self.sidebar_layout.addWidget(self.btn_accounts)

        icon_logs = qta.icon('fa5s.stream', color='#e0e0e0')
        self.btn_logs = QPushButton(icon_logs, "  Logs")
        self.btn_logs.setIconSize(QSize(18, 18))
        self.btn_logs.setFixedHeight(45)
        self.btn_logs.clicked.connect(self.log_dialog.show)
        self.sidebar_layout.addWidget(self.btn_logs)

        self.sidebar_layout.addStretch()

        self.btn_home.setCheckable(True)
        self.btn_accounts.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.setProperty("active", True)
        self.btn_accounts.setProperty("active", False)
        self.btn_home.style().unpolish(self.btn_home)
        self.btn_home.style().polish(self.btn_home)
        self.btn_accounts.style().unpolish(self.btn_accounts)
        self.btn_accounts.style().polish(self.btn_accounts)

        # IMPORTANTE: Añadir el sidebar al layout principal
        self.layout_principal.addWidget(self.sidebar)

    def is_admin_clearance_active(self):
        if not self.last_admin_unlock:
            return False
        return (datetime.now() - self.last_admin_unlock) < self.admin_session_duration

    def request_admin_clearance(self, parent=None):
        if self.is_admin_clearance_active():
            return True

        expected_password = self.cliente_data.get('password') if self.cliente_data else ''
        if not expected_password:
            QMessageBox.warning(self, "Acceso restringido", "No hay una contraseña de sesión válida configurada.")
            return False

        dialog = SecurityGate(parent or self, expected_password)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.last_admin_unlock = datetime.now()
            return True

        return False

    def show_page(self, index):
        if index == 1 and hasattr(self, 'accounts_page'):
            self.accounts_page.controller.refresh(self.current_cliente_id)
        self.pages_container.setCurrentIndex(index)

    def append_log_message(self, message):
        if hasattr(self, 'log_dialog'):
            self.log_dialog.append_message(message)

    def on_page_changed(self, index):
        self.btn_home.setChecked(index == 0)
        self.btn_accounts.setChecked(index == 1)
        self.btn_home.setProperty("active", index == 0)
        self.btn_accounts.setProperty("active", index == 1)
        self.btn_home.style().unpolish(self.btn_home)
        self.btn_home.style().polish(self.btn_home)
        self.btn_accounts.style().unpolish(self.btn_accounts)
        self.btn_accounts.style().polish(self.btn_accounts)


class SecurityGate(QDialog):
    def __init__(self, parent=None, expected_password=''):
        super().__init__(parent)
        self.expected_password = expected_password
        self.setWindowTitle("Verificación Administrativa")
        self.setFixedSize(380, 180)
        self.setObjectName("ModernDialog")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 18, 18, 18)
        self.layout.setSpacing(12)

        self.title = QLabel("Contraseña requerida")
        self.title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 800;")
        self.layout.addWidget(self.title)

        self.description = QLabel("Para modificar la configuración, ingresa la contraseña de Pegasus.")
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        self.layout.addWidget(self.description)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Contraseña de Pegasus")
        self.password_input.setStyleSheet(
            "background-color: #161616; color: #FFFFFF; border: 1px solid #333; padding: 10px; border-radius: 6px;"
        )
        self.layout.addWidget(self.password_input)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: #FF6666; font-size: 11px;")
        self.layout.addWidget(self.message_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_password)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def _validate_password(self):
        candidate = self.password_input.text().strip()
        if candidate and candidate == self.expected_password:
            self.accept()
        else:
            self.message_label.setText("Contraseña incorrecta. Intenta nuevamente.")
            self.password_input.clear()
            self.password_input.setFocus()
