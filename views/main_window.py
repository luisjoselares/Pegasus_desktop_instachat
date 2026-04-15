import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QStackedWidget, QLabel, QFrame,
                             QDialog, QLineEdit, QDialogButtonBox, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
import qtawesome as qta # Asegúrate de tenerlo instalado: pip install qtawesome

from views.instagram_accounts_page import InstagramAccountsPage
from views.home_page import HomePage
from views.sales_page import SalesPage
from views.agenda_page import AgendaPage
from views.log_dialog import LogDialog
from views.components import PegasusTitleBar
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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1100, 700)
        
        # 1. Inicializar Servicios
        self.db_service = LocalDBService()
        self.db_service.limpiar_cuentas_huerfanas(self.current_cliente_id)
        self.shared_engine = InstagramService()
        if self.licencia_data and hasattr(self.shared_engine, 'set_licencia_id'):
            self.shared_engine.set_licencia_id(self.licencia_data.get('id'))
        if hasattr(self.shared_engine, 'set_cliente_id'):
            self.shared_engine.set_cliente_id(self.current_cliente_id)

        # 2. Configurar Layout Base
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        shadow = QGraphicsDropShadowEffect(self.main_widget)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 0)
        self.main_widget.setGraphicsEffect(shadow)

        self.title_bar = PegasusTitleBar(self)
        self.title_bar.btn_min.clicked.connect(self.showMinimized)
        self.title_bar.btn_max.clicked.connect(self.toggle_maximize)
        self.title_bar.btn_close.clicked.connect(self.close)
        self.main_layout.addWidget(self.title_bar)

        self.content_widget = QWidget()
        self.layout_principal = QHBoxLayout(self.content_widget)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(0)

        # 3. PRIMERO: Crear el contenedor de páginas
        self.pages_container = QStackedWidget()
        
        # 4. SEGUNDO: Configurar el Sidebar (Ahora ya puede ver a pages_container)
        self.log_dialog = LogDialog(self)
        self.setup_sidebar()

        # 5. TERCERO: Configurar las páginas
        self.home_page = HomePage(self)
        self.lbl_welcome = self.home_page.lbl_welcome
        self.lbl_license_status = self.home_page.lbl_license_status

        self.sales_page = SalesPage(self.db_service, parent=self)

        self.insta_controller = InstagramController(
            self.db_service,
            engine=self.shared_engine,
            security_service=self.security_service,
            cliente_id=self.current_cliente_id
        )
        if self.cliente_data and self.cliente_data.get('email'):
            self.insta_controller.set_owner_email(self.cliente_data.get('email'))
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
        self.main_controller.set_instagram_controller(self.insta_controller)
        self.insta_controller.handoff_alert.connect(self.show_handoff_alert)
        if hasattr(self.insta_controller, 'security_alert'):
            self.insta_controller.security_alert.connect(self.show_security_alert)

        self.accounts_page = InstagramAccountsPage(self.insta_controller, main_window=self)
        self.insta_controller.set_view(self.accounts_page, self.current_cliente_id)
        self.agenda_page = AgendaPage(db_service=self.db_service, parent=self)

        # Añadir al stack
        self.pages_container.addWidget(self.home_page)      # Índice 0
        self.pages_container.addWidget(self.accounts_page)  # Índice 1
        self.pages_container.addWidget(self.sales_page)     # Índice 2
        self.pages_container.addWidget(self.agenda_page)    # Índice 3

        self.pages_container.currentChanged.connect(self.on_page_changed)

        # 6. CUARTO: Añadir el stack al layout principal (a la derecha del sidebar)
        self.layout_principal.addWidget(self.pages_container)
        self.main_layout.addWidget(self.content_widget)

        # Si existe una cuenta con bot habilitado, intenta iniciar automáticamente.
        self.main_controller.auto_start_if_enabled()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def view_order_details(self, order_id):
        order = None
        if hasattr(self.db_service, 'get_order_by_id'):
            order = self.db_service.get_order_by_id(order_id)
        else:
            orders = self.db_service.get_pending_orders() if hasattr(self.db_service, 'get_pending_orders') else []
            order = next((o for o in orders if o.get('id') == order_id), None)

        if not order:
            QMessageBox.information(self, "Detalle de venta", "No se encontró la orden o no hay datos disponibles.")
            return

        detalles = [
            f"Cliente: {order.get('cliente_id', 'N/A')}",
            f"Producto: {order.get('producto', 'N/A')}",
            f"Monto: {order.get('monto', 'N/A')}",
            f"Referencia: {order.get('referencia_pago', order.get('ref', 'N/A'))}",
            f"Dirección: {order.get('datos_envio', order.get('envio', 'N/A'))}",
            f"Estado: {order.get('status', 'Pendiente')}",
        ]
        QMessageBox.information(self, "Pago capturado", "\n".join(detalles))

    def approve_order(self, order_id):
        if order_id and hasattr(self.db_service, 'update_order_status'):
            self.db_service.update_order_status(order_id, 'VALIDATED')
            if hasattr(self, 'sales_page'):
                self.sales_page.refresh_pending_orders()
            QMessageBox.information(self, "Venta validada", "La venta ha sido validada y el sistema ha actualizado el estado.")

    def reject_order(self, order_id):
        if not order_id or not hasattr(self.db_service, 'update_order_status'):
            return
        motivo, ok = QInputDialog.getText(self, "Rechazar venta", "Motivo del rechazo (rápido):")
        motivo = motivo.strip() if ok else "Rechazo manual"
        self.db_service.update_order_status(order_id, 'REJECTED')
        if hasattr(self, 'sales_page'):
            self.sales_page.refresh_pending_orders()
        QMessageBox.information(self, "Venta rechazada", f"La venta fue rechazada. Motivo: {motivo}")

    def show_handoff_alert(self, thread_id, username):
        if hasattr(self, 'log_dialog') and self.log_dialog:
            self.log_dialog.log_console.append(f"[ALERTA VISUAL] Handoff detectado para @{username}. Se activará redirección en 3 min.")
        QMessageBox.information(self, "Handoff detectado", f"Handoff detectado en @{username}. El mensaje esperará 3 minutos antes de la redirección.")

    def show_security_alert(self, thread_id, username, message):
        if hasattr(self, 'log_dialog') and self.log_dialog:
            self.log_dialog.log_console.append(f"[ALERTA DE SEGURIDAD] @{username}. Se notificó por correo y se registró la alerta.")
        QMessageBox.warning(
            self,
            "Alerta de seguridad",
            f"Se detectó una alerta crítica para @{username}. Se intentó notificar al dueño por correo."
        )

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

        icon_orders = qta.icon('fa5s.clipboard-list', color='#e0e0e0')
        self.btn_orders = QPushButton(icon_orders, "  Ventas por Validar")
        self.btn_orders.setIconSize(QSize(18, 18))
        self.btn_orders.setFixedHeight(45)
        self.btn_orders.setCheckable(True)
        self.btn_orders.clicked.connect(lambda: self.show_page(2))
        self.sidebar_layout.addWidget(self.btn_orders)

        icon_agenda = qta.icon('fa5s.calendar', color='#e0e0e0')
        self.btn_agenda = QPushButton(icon_agenda, "  Agenda")
        self.btn_agenda.setIconSize(QSize(18, 18))
        self.btn_agenda.setFixedHeight(45)
        self.btn_agenda.setCheckable(True)
        self.btn_agenda.clicked.connect(lambda: self.show_page(3))
        self.sidebar_layout.addWidget(self.btn_agenda)

        icon_logs = qta.icon('fa5s.stream', color='#e0e0e0')
        self.btn_logs = QPushButton(icon_logs, "  Logs")
        self.btn_logs.setIconSize(QSize(18, 18))
        self.btn_logs.setFixedHeight(45)
        self.btn_logs.clicked.connect(self.log_dialog.show)
        self.sidebar_layout.addWidget(self.btn_logs)

        self.sidebar_layout.addStretch()

        self.btn_home.setCheckable(True)
        self.btn_accounts.setCheckable(True)
        self.btn_orders.setCheckable(True)
        self.btn_agenda.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.setProperty("active", True)
        self.btn_accounts.setProperty("active", False)
        self.btn_orders.setProperty("active", False)
        self.btn_agenda.setProperty("active", False)
        self.btn_home.style().unpolish(self.btn_home)
        self.btn_home.style().polish(self.btn_home)
        self.btn_accounts.style().unpolish(self.btn_accounts)
        self.btn_accounts.style().polish(self.btn_accounts)
        self.btn_orders.style().unpolish(self.btn_orders)
        self.btn_orders.style().polish(self.btn_orders)
        self.btn_agenda.style().unpolish(self.btn_agenda)
        self.btn_agenda.style().polish(self.btn_agenda)

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
        if index == 2 and hasattr(self, 'sales_page'):
            self.sales_page.refresh_pending_orders()
        if index == 3 and hasattr(self, 'agenda_page'):
            self.agenda_page.load_citas()
        self.pages_container.setCurrentIndex(index)

    def append_log_message(self, message):
        if hasattr(self, 'log_dialog'):
            self.log_dialog.append_message(message)

    def on_page_changed(self, index):
        self.btn_home.setChecked(index == 0)
        self.btn_accounts.setChecked(index == 1)
        self.btn_orders.setChecked(index == 2)
        self.btn_agenda.setChecked(index == 3)
        self.btn_home.setProperty("active", index == 0)
        self.btn_accounts.setProperty("active", index == 1)
        self.btn_orders.setProperty("active", index == 2)
        self.btn_agenda.setProperty("active", index == 3)
        self.btn_home.style().unpolish(self.btn_home)
        self.btn_home.style().polish(self.btn_home)
        self.btn_accounts.style().unpolish(self.btn_accounts)
        self.btn_accounts.style().polish(self.btn_accounts)
        self.btn_orders.style().unpolish(self.btn_orders)
        self.btn_orders.style().polish(self.btn_orders)
        self.btn_agenda.style().unpolish(self.btn_agenda)
        self.btn_agenda.style().polish(self.btn_agenda)


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
