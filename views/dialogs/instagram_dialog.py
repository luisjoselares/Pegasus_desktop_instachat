import csv
import importlib
import json
import os
import random
import qtawesome as qta
from PyQt6.QtWidgets import (
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QTimeEdit,
    QStackedWidget,
    QWidget,
    QFileDialog,
    QScrollArea,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QFrame,
    QInputDialog,
    QGridLayout,
    QCheckBox,
    QLayout,
    QMessageBox,
)
from PyQt6.QtGui import QTransform, QColor
from PyQt6.QtCore import Qt, QTime, QThread, pyqtSignal, QTimer, QPropertyAnimation, QPoint
from core.ai_engine import AIService
from services.instagram_service import InstagramService


class LoginWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, service, username, password):
        super().__init__()
        self.service = service
        self.username = username
        self.password = password

    def run(self):
        if self.isInterruptionRequested():
            self.finished.emit(False, "Login cancelado.")
            return
        try:
            result = self.service.login(self.username, self.password)
            success = result is not None
            self.finished.emit(success, "" if success else "No se pudo validar la cuenta.")
        except Exception as e:
            self.finished.emit(False, str(e))


class ProfileScanWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, service, username):
        super().__init__()
        self.service = service
        self.username = username

    def run(self):
        if self.isInterruptionRequested():
            self.finished.emit(None)
            return
        try:
            profile = self.service.analyze_profile(self.username)
            self.finished.emit(profile)
        except Exception as e:
            self.error.emit(str(e))


class AddAccountDialog(QDialog):
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        if account_data is not None and hasattr(account_data, 'keys'):
            self.account_data = dict(account_data)
        else:
            self.account_data = account_data or {}
        self.current_state = {
            "id": self.account_data.get("id") if self.account_data else None,
            "insta_user": self.account_data.get("insta_user", ""),
            "insta_pass": self.account_data.get("insta_pass", ""),
            "store_name": self.account_data.get("store_name", ""),
            "description": self.account_data.get("description", ""),
            "system_prompt": self.account_data.get("system_prompt", ""),
            "system_prompt_final": self.account_data.get("system_prompt", ""),
            "bot_enabled": self.account_data.get("bot_enabled", 0),
            "bot_role": self.account_data.get("bot_role", "VENDEDOR"),
            "bot_name": self.account_data.get("bot_name", "Pegasus"),
            "inventory_path": self.account_data.get("inventory_path", ""),
            "start_time": self.account_data.get("start_time", "08:00"),
            "end_time": self.account_data.get("end_time", "18:00"),
            "proxy": self.account_data.get("proxy", "Auto"),
            "security_level": self.account_data.get("security_level", "High"),
            "whatsapp_number": self.account_data.get("whatsapp_number", ""),
            "country": self.account_data.get("country", "Venezuela"),
            "language": self.account_data.get("language", "Español"),
            "currency_symbol": self.account_data.get("currency_symbol", "$"),
            "currency_code": self.account_data.get("currency_code", ""),
            "currency_name": self.account_data.get("currency_name", ""),
            "rag_context": self.account_data.get("rag_context", ""),
            "location": self.account_data.get("location", ""),
            "website": self.account_data.get("website", ""),
            "envios": self.account_data.get("envios", ""),
            "bot_mission": self.account_data.get("bot_mission", "Ventas"),
            "payment_methods": self.account_data.get("payment_methods", []),
            "payment_method_details": self.account_data.get("payment_method_details", {}),
            "payment_methods_text": self.account_data.get("payment_methods_text", ""),
            "info_eventos": self.account_data.get("info_eventos", self.account_data.get("config_faq", "")),
        }
        self.is_edit_mode = bool(account_data)
        self.account_id = self.account_data.get('id') if self.is_edit_mode else None
        self.setWindowTitle("Configuración de Agente Pegasus" if not self.is_edit_mode else "Configuración de Cuenta")
        self.setMinimumSize(1000, 700)
        self.setObjectName("ModernDialog")

        self.insta_service = InstagramService()
        self.login_worker = None
        self.profile_worker = None
        self.csv_path = ""
        self.inventory_connected = False
        self.inventory_headers = []
        self.inventory_rows = 0
        self.inventory_type = ""
        self.inventory_headers = []
        self.inventory_rows = 0
        self.hidden_prompt = ""
        self.config_country = "Venezuela"
        self.config_language = "es"
        self.config_payments = ""
        self.payment_method_details = {}
        self.config_faq = ""
        self.digested_context_data = {}
        self.ai_service = AIService()
        self.setStyleSheet("""
            QDialog#ModernDialog {
                background-color: #080808;
            }
            *:focus {
                outline: none;
            }
            QLabel#StepTitle {
                font-size: 24px;
                font-weight: bold;
                color: #FFFFFF;
                margin-bottom: 5px;
            }
            QLabel#StepSubtitle {
                font-size: 13px;
                color: #777777;
                margin-bottom: 20px;
            }
            QLineEdit, QTextEdit {
                background: #1A1A1A;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 10px;
                border: none;
                border-bottom: 1px solid #444444;
                border-radius: 4px 4px 0 0;
                margin-bottom: 15px;
            }
            QLineEdit:focus, QTextEdit:focus {
                background-color: rgba(0, 229, 255, 0.05);
                border-bottom: 1px solid #00E5FF;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton#MissionChip {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #333333;
                border-radius: 12px;
                color: #A0A0A0;
                padding: 10px 15px;
                font-size: 13px;
            }
            QPushButton#MissionChip:hover {
                border: 1px solid #00E5FF;
                background-color: rgba(0, 229, 255, 0.05);
            }
            QPushButton#MissionChip[selected="true"] {
                border: 1px solid #00E5FF;
                background-color: rgba(0, 229, 255, 0.1);
                color: #FFFFFF;
            }
            QPushButton#PrimaryBtn {
                background-color: #00E5FF;
                color: #000000;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 20px;
                border: none;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #00B3CC;
            }
            QPushButton#FlatBtn {
                background-color: transparent;
                color: #777777;
                border: none;
            }
            QPushButton#FlatBtn:hover {
                color: #FFFFFF;
            }            QLabel.QuestionLabel {
                color: #A0A0A0;
                font-size: 13px;
                margin-top: 10px;
                margin-bottom: 2px;
            }
            QPushButton.PaymentTag {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 12px;
                color: #777777;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton.PaymentTag:checked {
                border-color: #00E5FF;
                color: #FFFFFF;
                background-color: rgba(0, 229, 255, 0.1);
            }
            QPushButton#AspectCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid #333333;
                border-radius: 16px;
                color: #FFFFFF;
                padding: 10px 14px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton#AspectCard:hover {
                border-color: #00E5FF;
                background-color: rgba(0, 229, 255, 0.08);
            }
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(18, 18, 18, 18)
        self.main_layout.setSpacing(20)
        # Esto es la magia del Shrink-Wrap: La ventana se ajustará al panel
        self.main_layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)

        self.wizard_container = QFrame()
        self.wizard_container.setMinimumSize(520, 650)
        self.wizard_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.wizard_container.setObjectName("WizardContainer")
        self.wizard_container.setStyleSheet(
            "QFrame#WizardContainer{background-color:#0B0B0B; border-radius:24px;}"
        )

        wizard_shadow = QGraphicsDropShadowEffect(self.wizard_container)
        wizard_shadow.setBlurRadius(30)
        wizard_shadow.setOffset(0, 12)
        wizard_shadow.setColor(QColor(0, 0, 0, 200))
        self.wizard_container.setGraphicsEffect(wizard_shadow)

        self.layout = QVBoxLayout(self.wizard_container)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(0)

        self.stacked = QStackedWidget()
        self.page1 = QWidget()
        self.page2 = QWidget()
        self.page3 = QWidget()
        self.page4 = QWidget()
        self.page5 = QWidget()
        self.page6 = QWidget()

        for page in [self.page1, self.page2, self.page3, self.page4, self.page5, self.page6]:
            page.setStyleSheet("background: transparent;")
        self.stacked.setStyleSheet("background: transparent;")

        self.schedule_warning = QLabel("")

        self._build_page1()
        self._build_page2()
        self._build_page3()
        self._build_page4()
        self._build_side_panel()
        self._build_page6()

        self.stacked.addWidget(self.page1)
        self.stacked.addWidget(self.page2)
        self.stacked.addWidget(self.page3)
        self.stacked.addWidget(self.page4)
        self.stacked.addWidget(self.page6)
        self.stacked.currentChanged.connect(self.on_page_changed)

        self.layout.addWidget(self.stacked)

        self.footer = QWidget()
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        footer_layout.setSpacing(12)
        self.footer_prev = QPushButton("ATRÁS")
        self.footer_prev.setObjectName("FlatBtn")
        self.footer_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.footer_prev.clicked.connect(self.prev_step)
        self.footer_next = QPushButton("SIGUIENTE")
        self.footer_next.setObjectName("PrimaryBtn")
        self.footer_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.footer_next.clicked.connect(self.next_step)
        footer_layout.addWidget(self.footer_prev)
        footer_layout.addStretch()
        footer_layout.addWidget(self.footer_next)
        self.layout.addWidget(self.footer)

        self.main_layout.addWidget(self.wizard_container, 1)
        self._build_side_panel()

        self.on_page_changed(self.stacked.currentIndex())
        self._create_loading_overlay()
        self._create_side_panel_animation()
        self.main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.update_role_logic()

        if self.is_edit_mode:
            self._load_account_data(self.account_data)
            self.stacked.setCurrentIndex(1)

    def _create_loading_overlay(self):
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(12)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel()
        self.spinner_label.setFixedSize(48, 48)
        self.spinner_label.setScaledContents(True)
        self.spinner_label.setStyleSheet("background: transparent;")
        self.spinner_pixmap = qta.icon('fa5s.spinner', color='#00E5FF').pixmap(48, 48)
        self.spinner_label.setPixmap(self.spinner_pixmap)
        overlay_layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.spinner_text = QLabel("Procesando...")
        self.spinner_text.setStyleSheet("color: #FFFFFF; font-size: 14px; background: transparent;")
        overlay_layout.addWidget(self.spinner_text, alignment=Qt.AlignmentFlag.AlignCenter)

        self.loading_overlay.hide()
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._rotate_spinner)
        self.spinner_timer.setInterval(120)
        self.spinner_angle = 0

    def _build_side_panel(self):
        self.side_panel_container = QFrame()
        self.side_panel_container.setObjectName("SidePanelContainer")
        self.side_panel_container.setMinimumWidth(0)
        self.side_panel_container.setMaximumWidth(360)
        self.side_panel_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.side_panel_container.setStyleSheet(
            "QFrame#SidePanelContainer{background-color:#101010; border-radius:20px;}"
        )

        panel_shadow = QGraphicsDropShadowEffect(self.side_panel_container)
        panel_shadow.setBlurRadius(16)
        panel_shadow.setOffset(0, 8)
        panel_shadow.setColor(QColor(0, 0, 0, 120))
        self.side_panel_container.setGraphicsEffect(panel_shadow)

        side_panel_layout = QVBoxLayout(self.side_panel_container)
        side_panel_layout.setContentsMargins(14, 14, 14, 14)
        side_panel_layout.setSpacing(0)

        self.side_panel_stack = QStackedWidget()

        self.side_panel_scroll = QScrollArea()
        self.side_panel_scroll.setWidgetResizable(True)
        self.side_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.side_panel_scroll.setStyleSheet(
            "QScrollArea{background: transparent; border: none;}"
            "QScrollBar:vertical{width: 8px; background: transparent; margin: 0 0 0 0;}"
            "QScrollBar::handle:vertical{background: rgba(255,255,255,0.15); border-radius: 4px;}"
            "QScrollBar::handle:vertical:hover{background: rgba(255,255,255,0.25); }"
            "QScrollBar::add-line, QScrollBar::sub-line{height: 0;}"
            "QScrollBar::add-page, QScrollBar::sub-page{background: transparent;}"
        )

        self.side_panel_content = QWidget()
        self.side_panel_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.side_panel_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.side_panel_stack)
        content_layout.addStretch()

        self.side_panel_scroll.setWidget(self.side_panel_content)
        side_panel_layout.addWidget(self.side_panel_scroll)

        self.side_panel_stack.addWidget(self._create_finance_panel_page())
        self.side_panel_stack.addWidget(self._create_catalog_panel_page())
        self.side_panel_stack.addWidget(self._create_info_panel_page())
        self.side_panel_stack.addWidget(self._create_attention_panel_page())
        self.side_panel_stack.addWidget(self._create_faq_panel_page())

        self.side_panel_container.setVisible(False)
        self.main_layout.addWidget(self.side_panel_container)

    def _create_side_panel_page_header(self, title, description):
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        close_button = QPushButton(qta.icon('fa5s.arrow-left', color='#00E5FF'), "Atrás")
        close_button.setObjectName("FlatBtn")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self._close_side_panel)
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)

        label = QLabel(title)
        label.setObjectName("StepTitle")
        header_layout.addWidget(label)

        subtitle = QLabel(description)
        subtitle.setWordWrap(True)
        subtitle.setObjectName("StepSubtitle")
        header_layout.addWidget(subtitle)

        return header_frame

    def _create_finance_panel_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._create_side_panel_page_header(
            "Finanzas", "Ajusta país e idioma."))

        self.side_country_combo = QComboBox()
        self.side_country_combo.addItems(["Venezuela", "México", "Colombia", "Argentina", "Chile", "Perú"])
        self.side_country_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_country_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.side_country_combo.setMaximumWidth(300)
        self.side_country_combo.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("País de operación"))
        layout.addWidget(self.side_country_combo)

        self.side_language_input = QLineEdit()
        self.side_language_input.setPlaceholderText("Ej: es")
        self.side_language_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.side_language_input.setMaximumWidth(300)
        self.side_language_input.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("Idioma principal"))
        layout.addWidget(self.side_language_input)

        payment_title = QLabel("Métodos de pago aceptados:")
        payment_title.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        payment_title.setWordWrap(True)
        layout.addWidget(payment_title)

        add_payment_layout = QHBoxLayout()
        add_payment_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.cmb_payment = QComboBox()
        self.cmb_payment.setEditable(True)
        self.cmb_payment.addItems(["Efectivo", "Pago Móvil", "Binance Pay", "Zelle", "Transferencia", "PayPal"])
        self.cmb_payment.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.cmb_payment.setMaximumWidth(180)
        self.cmb_payment.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.cmb_payment.currentTextChanged.connect(self._on_payment_type_changed)

        btn_add_payment = QPushButton("Añadir")
        btn_add_payment.setStyleSheet("background-color: #00E5FF; color: black; font-weight: bold; padding: 8px 10px; border-radius: 4px;")
        btn_add_payment.setMaximumWidth(80)
        btn_add_payment.clicked.connect(self._add_payment_chip)

        self.payment_stack = QStackedWidget()
        self.payment_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.payment_stack.setMaximumWidth(300)

        self.txt_pm_banco = QLineEdit()
        self.txt_pm_banco.setPlaceholderText("Banco")
        self.txt_pm_banco.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.txt_pm_ci = QLineEdit()
        self.txt_pm_ci.setPlaceholderText("Cédula")
        self.txt_pm_ci.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.txt_pm_telf = QLineEdit()
        self.txt_pm_telf.setPlaceholderText("Teléfono")
        self.txt_pm_telf.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        pm_page = QWidget()
        pm_layout = QHBoxLayout(pm_page)
        pm_layout.setContentsMargins(0, 0, 0, 0)
        pm_layout.setSpacing(8)
        pm_layout.addWidget(self.txt_pm_banco)
        pm_layout.addWidget(self.txt_pm_ci)
        pm_layout.addWidget(self.txt_pm_telf)
        self.payment_stack.addWidget(pm_page)

        self.txt_zelle_correo = QLineEdit()
        self.txt_zelle_correo.setPlaceholderText("Correo Zelle")
        self.txt_zelle_correo.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.txt_zelle_nombre = QLineEdit()
        self.txt_zelle_nombre.setPlaceholderText("Titular")
        self.txt_zelle_nombre.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        zelle_page = QWidget()
        zelle_layout = QHBoxLayout(zelle_page)
        zelle_layout.setContentsMargins(0, 0, 0, 0)
        zelle_layout.setSpacing(8)
        zelle_layout.addWidget(self.txt_zelle_correo)
        zelle_layout.addWidget(self.txt_zelle_nombre)
        self.payment_stack.addWidget(zelle_page)

        self.txt_transf_banco = QLineEdit()
        self.txt_transf_banco.setPlaceholderText("Banco")
        self.txt_transf_banco.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.txt_transf_cuenta = QLineEdit()
        self.txt_transf_cuenta.setPlaceholderText("N° Cuenta")
        self.txt_transf_cuenta.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        self.txt_transf_ci = QLineEdit()
        self.txt_transf_ci.setPlaceholderText("CI/RIF")
        self.txt_transf_ci.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        transf_page = QWidget()
        transf_layout = QHBoxLayout(transf_page)
        transf_layout.setContentsMargins(0, 0, 0, 0)
        transf_layout.setSpacing(8)
        transf_layout.addWidget(self.txt_transf_banco)
        transf_layout.addWidget(self.txt_transf_cuenta)
        transf_layout.addWidget(self.txt_transf_ci)
        self.payment_stack.addWidget(transf_page)

        self.txt_pago_generico = QLineEdit()
        self.txt_pago_generico.setPlaceholderText("Correo, ID o Detalle")
        self.txt_pago_generico.setStyleSheet("background-color: #1A1A1A; color: white; padding: 8px; border-radius: 4px;")
        generic_page = QWidget()
        generic_layout = QHBoxLayout(generic_page)
        generic_layout.setContentsMargins(0, 0, 0, 0)
        generic_layout.setSpacing(8)
        generic_layout.addWidget(self.txt_pago_generico)
        self.payment_stack.addWidget(generic_page)
        self.payment_stack.setCurrentIndex(3)

        add_payment_layout.addWidget(self.cmb_payment, 1)
        add_payment_layout.addWidget(btn_add_payment)
        layout.addLayout(add_payment_layout)
        layout.addWidget(self.payment_stack)

        self.chips_layout = QHBoxLayout()
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.chips_layout)

        self.payment_methods_data = []
        raw_methods = self.account_data.get('payment_methods', '[]') if self.account_data else '[]'
        raw_details = self.account_data.get('payment_method_details', '{}') if self.account_data else '{}'
        try:
            existing_payments = json.loads(raw_methods) if isinstance(raw_methods, str) else (raw_methods or [])
            existing_details = json.loads(raw_details) if isinstance(raw_details, str) else (raw_details or {})
        except Exception:
            existing_payments, existing_details = [], {}

        for method in existing_payments:
            self._create_chip(method, existing_details.get(method, ""))

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(lambda: self._save_finance_panel())
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return page

    def _on_payment_type_changed(self, text):
        text_lower = text.lower()
        if "móvil" in text_lower or "movil" in text_lower:
            self.payment_stack.setCurrentIndex(0)
        elif "zelle" in text_lower:
            self.payment_stack.setCurrentIndex(1)
        elif "transferencia" in text_lower:
            self.payment_stack.setCurrentIndex(2)
        else:
            self.payment_stack.setCurrentIndex(3)

    def _create_faq_panel_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._create_side_panel_page_header(
            "FAQ / Lives", "Pega aquí todo el contenido extra que el asistente debe conocer."))

        self.side_faq_text = QTextEdit()
        self.side_faq_text.setPlaceholderText("Ej: Lives los viernes, promociones especiales, preguntas frecuentes, detalles de eventos...")
        self.side_faq_text.setStyleSheet("background: #1A1A1A; color: #FFFFFF; border: none; border-bottom: 1px solid #444444; border-radius: 10px; padding: 10px;")
        self.side_faq_text.setMinimumHeight(260)
        self.side_faq_text.setMaximumWidth(250)
        layout.addWidget(self.side_faq_text)

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(lambda: self._save_faq_panel())
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return page

    def _create_catalog_panel_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._create_side_panel_page_header(
            "Catálogo", "Adjunta tu catálogo o inventario y revisa el archivo cargado."))

        btn_attach_catalog = QPushButton(qta.icon('fa5s.upload', color='#00E5FF'), "  Adjuntar catálogo / inventario")
        btn_attach_catalog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_attach_catalog.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255,255,255,0.04);"
            "color: #FFFFFF;"
            "border: 1px solid rgba(255,255,255,0.08);"
            "border-radius: 20px;"
            "padding: 18px 22px;"
            "text-align: left;"
            "font-size: 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(0, 229, 255, 0.08);"
            "border-color: rgba(0,229,255,0.25);"
            "}"
        )
        btn_attach_catalog.clicked.connect(self.browse_inventory_file)
        layout.addWidget(btn_attach_catalog, alignment=Qt.AlignmentFlag.AlignLeft)

        self.side_catalog_info = QLabel()
        self.side_catalog_info.setStyleSheet("color: #A0A0A0; font-size: 13px;")
        self.side_catalog_info.setWordWrap(True)
        layout.addWidget(self.side_catalog_info)

        self.lbl_file_path = QLabel()
        self.lbl_file_path.setStyleSheet("color: #A0E5FF; font-size: 12px;")
        self.lbl_file_path.setWordWrap(True)
        layout.addWidget(self.lbl_file_path)

        self._refresh_side_catalog_info()

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_catalog_panel)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return page

    def _create_attention_panel_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._create_side_panel_page_header(
            "Atención", "Define el horario en el que trabajará el bot y ajusta su estado activo."))

        self.side_attention_info = QLabel()
        self.side_attention_info.setStyleSheet("color: #A0A0A0; font-size: 13px;")
        self.side_attention_info.setWordWrap(True)
        layout.addWidget(self.side_attention_info)

        section_label = QLabel("Encendido Automático del Bot")
        section_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        layout.addWidget(section_label)

        bot_time_frame = QFrame()
        bot_time_frame.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid #222222; border-radius: 12px;")
        bot_time_layout = QHBoxLayout(bot_time_frame)
        bot_time_layout.setContentsMargins(10, 10, 10, 10)
        bot_time_layout.setSpacing(8)

        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(8, 0))
        self.start_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_time.setMaximumWidth(96)
        self.start_time.setStyleSheet("background: transparent; color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 9px;")
        bot_time_layout.addWidget(self.start_time)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime(20, 0))
        self.end_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.end_time.setMaximumWidth(96)
        self.end_time.setStyleSheet("background: transparent; color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 9px;")
        bot_time_layout.addWidget(self.end_time)

        layout.addWidget(bot_time_frame)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("color: rgba(255,255,255,0.12);")
        layout.addWidget(divider)

        company_label = QLabel("Horario de Operación de la Empresa")
        company_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        layout.addWidget(company_label)

        business_days = self.account_data.get('business_days', {}) if isinstance(self.account_data, dict) else {}
        if isinstance(business_days, list):
            business_days = {day: day in business_days for day in ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]}
        elif not isinstance(business_days, dict):
            business_days = {}

        self.business_day_checkboxes = {}
        days_widget = QWidget()
        days_layout = QHBoxLayout(days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(6)

        day_names = [
            ("Dom", "#FF5555"),
            ("Lun", "#FFFFFF"),
            ("Mar", "#FFFFFF"),
            ("Mié", "#FFFFFF"),
            ("Jue", "#FFFFFF"),
            ("Vie", "#FFFFFF"),
            ("Sáb", "#FFFFFF"),
        ]

        for day, color in day_names:
            day_box = QWidget()
            day_box_layout = QVBoxLayout(day_box)
            day_box_layout.setContentsMargins(0, 0, 0, 0)
            day_box_layout.setSpacing(4)
            day_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            day_label = QLabel(day)
            day_label.setStyleSheet(f"color: {color}; font-size: 12px;")
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_checkbox = QCheckBox()
            day_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            day_checkbox.setChecked(bool(business_days.get(day, False)))

            self.business_day_checkboxes[day] = day_checkbox
            day_box_layout.addWidget(day_label, alignment=Qt.AlignmentFlag.AlignCenter)
            day_box_layout.addWidget(day_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            days_layout.addWidget(day_box)

        layout.addWidget(days_widget)

        self.business_hours_text_input = QLineEdit()
        self.business_hours_text_input.setPlaceholderText("8:00 AM - 6:00 PM (Corrido)")
        self.business_hours_text_input.setMaximumWidth(260)
        self.business_hours_text_input.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        self.business_hours_text_input.setText(self.account_data.get('business_hours_text', '') if isinstance(self.account_data, dict) else "")
        layout.addWidget(self.business_hours_text_input)

        self._refresh_side_attention_info()

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_attention_panel)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return page

    def _refresh_side_catalog_info(self):
        csv_name = os.path.basename(self.csv_path) if self.csv_path else 'Sin catálogo cargado'
        self.side_catalog_info.setText(f"Archivo actual: {csv_name}")

    def _save_catalog_panel(self):
        self.current_state['inventory_path'] = self.csv_path
        self._refresh_side_catalog_info()
        self._update_status_cards()
        self._close_side_panel()
        self._show_save_notification()

    def _refresh_side_attention_info(self):
        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            self.side_attention_info.setText(f"Horario de trabajo del bot: {self.start_time.time().toString('HH:mm')} - {self.end_time.time().toString('HH:mm')}")
        else:
            self.side_attention_info.setText("Activo 24/7")

    def _save_finance_panel(self):
        methods = [p['method'] for p in self.payment_methods_data]
        details = {p['method']: p['detail'] for p in self.payment_methods_data}

        # Serializar a texto para que SQLite lo acepte
        self.current_state['payment_methods'] = json.dumps(methods)
        self.current_state['payment_method_details'] = json.dumps(details)
        if hasattr(self, 'txt_currency_symbol'):
            self.current_state['currency_symbol'] = self.txt_currency_symbol.text().strip()

        self._update_status_cards()
        self._close_side_panel()
        self._show_save_notification()

    def _add_payment_chip(self):
        method = self.cmb_payment.currentText().strip()
        if not method or any(p['method'] == method for p in self.payment_methods_data):
            return

        idx = self.payment_stack.currentIndex()
        detail = ""

        if idx == 0:  # Pago Móvil
            detail = f"Banco: {self.txt_pm_banco.text().strip()} | CI: {self.txt_pm_ci.text().strip()} | Telf: {self.txt_pm_telf.text().strip()}"
            self.txt_pm_banco.clear(); self.txt_pm_ci.clear(); self.txt_pm_telf.clear()
        elif idx == 1:  # Zelle
            detail = f"Correo: {self.txt_zelle_correo.text().strip()} | Titular: {self.txt_zelle_nombre.text().strip()}"
            self.txt_zelle_correo.clear(); self.txt_zelle_nombre.clear()
        elif idx == 2:  # Transferencia
            detail = f"Banco: {self.txt_transf_banco.text().strip()} | Cta: {self.txt_transf_cuenta.text().strip()} | CI/RIF: {self.txt_transf_ci.text().strip()}"
            self.txt_transf_banco.clear(); self.txt_transf_cuenta.clear(); self.txt_transf_ci.clear()
        else:  # Genérico
            detail = self.txt_pago_generico.text().strip()
            self.txt_pago_generico.clear()

        self._create_chip(method, detail)
        self.cmb_payment.clearEditText()

    def _create_chip(self, method, detail):
        self.payment_methods_data.append({'method': method, 'detail': detail})
        chip = QWidget()
        chip.setMaximumWidth(300)
        chip.setStyleSheet("background-color: rgba(0, 229, 255, 0.1); border: 1px solid #00E5FF; border-radius: 12px;")
        clayout = QHBoxLayout(chip)
        clayout.setContentsMargins(10, 4, 10, 4)
        
        lbl = QLabel(f"{method}: {detail}" if detail else method)
        lbl.setStyleSheet("color: #00E5FF; font-size: 11px; border: none; background: transparent;")
        
        btn_rm = QPushButton("✕")
        btn_rm.setStyleSheet("color: #FF5555; font-weight: bold; border: none; background: transparent;")
        btn_rm.clicked.connect(lambda _, w=chip, m=method: self._remove_chip(w, m))
        
        clayout.addWidget(lbl)
        clayout.addWidget(btn_rm)
        self.chips_layout.addWidget(chip)

    def _remove_chip(self, widget, method):
        self.chips_layout.removeWidget(widget)
        widget.deleteLater()
        self.payment_methods_data = [p for p in self.payment_methods_data if p['method'] != method]

    def _save_faq_panel(self):
        self.config_faq = self.side_faq_text.toPlainText().strip()
        self.side_faq_text.setPlainText(self.config_faq)
        self.current_state['info_eventos'] = self.config_faq
        self._update_status_cards()
        self._close_side_panel()
        self._show_save_notification()

    def _save_attention_panel(self):
        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            self.current_state['start_time'] = self.start_time.time().toString('HH:mm')
            self.current_state['end_time'] = self.end_time.time().toString('HH:mm')
        if hasattr(self, 'business_hours_text_input'):
            self.current_state['business_hours_text'] = self.business_hours_text_input.text().strip()
        if hasattr(self, 'business_day_checkboxes'):
            self.current_state['business_days'] = [day for day, chk in self.business_day_checkboxes.items() if chk.isChecked()]
        self._refresh_side_attention_info()
        self._update_status_cards()
        self._close_side_panel()
        self._show_save_notification()

    def _save_info_panel(self):
        self.current_state['whatsapp_number'] = self.txt_whatsapp.text().strip() if hasattr(self, 'txt_whatsapp') else self.current_state.get('whatsapp_number', '')
        self.current_state['location'] = self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else self.current_state.get('location', '')
        self.current_state['website'] = self.txt_website.text().strip() if hasattr(self, 'txt_website') else self.current_state.get('website', '')
        self.current_state['envios'] = self.txt_envios.text().strip() if hasattr(self, 'txt_envios') else self.current_state.get('envios', '')
        self._update_status_cards()
        self._close_side_panel()
        self._show_save_notification()

    def _create_status_card(self, title, status_label, button_text, callback):
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.03); border: 1px solid #222222; border-radius: 18px;"
        )
        frame.setMinimumHeight(70)
        card_layout = QHBoxLayout(frame)
        card_layout.setContentsMargins(14, 8, 14, 8)
        card_layout.setSpacing(12)

        text_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #FFFFFF; background: transparent; font-weight: bold; font-size: 14px;")
        text_layout.addWidget(title_label)

        status_label.setStyleSheet("color: #A0A0A0; background: transparent; font-size: 13px;")
        status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        status_label.setWordWrap(False)
        text_layout.addWidget(status_label)

        card_layout.addLayout(text_layout)
        card_layout.addStretch()

        button = QPushButton(button_text)
        button.setObjectName("PrimaryBtn")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)
        button.setMinimumWidth(110)
        card_layout.addWidget(button)

        return frame

    def _open_side_panel_section(self, section):
        mapping = {
            "Finanzas": 0,
            "Catálogo": 1,
            "Información": 2,
            "Atención": 3,
            "Conocimiento": 4,
        }
        if section == "Finanzas":
            self.side_country_combo.setCurrentText(self.config_country)
            self.side_language_input.setText(self.config_language)
        elif section == "Información":
            if hasattr(self, 'txt_whatsapp'):
                self.txt_whatsapp.setText(self.txt_whatsapp.text().strip())
            if hasattr(self, 'txt_ubicacion'):
                self.txt_ubicacion.setText(self.txt_ubicacion.text().strip())
            if hasattr(self, 'txt_website'):
                self.txt_website.setText(self.txt_website.text().strip())
            if hasattr(self, 'txt_envios'):
                self.txt_envios.setText(self.txt_envios.text().strip())
        elif section == "Conocimiento":
            self.side_faq_text.setPlainText(self.config_faq)
        elif section == "Catálogo":
            self._refresh_side_catalog_info()
        elif section == "Atención":
            if hasattr(self, 'start_time') and hasattr(self, 'side_attention_info'):
                self.side_attention_info.setText(f"Horario actual: {self.start_time.time().toString('HH:mm')} - {self.end_time.time().toString('HH:mm')}")
        index = mapping.get(section, 0)
        self.side_panel_stack.setCurrentIndex(index)
        self.toggle_side_panel(True)

    def _truncate_status_text(self, text, max_length=48):
        if len(text) <= max_length:
            return text
        return text[:max_length - 3].rstrip() + '...'

    def _update_status_cards(self):
        if hasattr(self, 'finance_status_label'):
            self.finance_status_label.setText(
                self._truncate_status_text(
                    f"{self.config_country} - {self.config_language}",
                    max_length=52
                )
            )

        csv_name = os.path.basename(self.csv_path) if self.csv_path else 'Sin catálogo cargado'
        if hasattr(self, 'catalog_status_label'):
            self.catalog_status_label.setText(self._truncate_status_text(f"{csv_name}", max_length=52))

        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            start = self.start_time.time().toString('HH:mm')
            end = self.end_time.time().toString('HH:mm')
            if hasattr(self, 'attention_status_label'):
                self.attention_status_label.setText(self._truncate_status_text(f"Horario: {start} - {end}", max_length=52))
        else:
            if hasattr(self, 'attention_status_label'):
                self.attention_status_label.setText("Activo 24/7")

        if hasattr(self, 'info_status_label'):
            whatsapp = self.txt_whatsapp.text().strip() if hasattr(self, 'txt_whatsapp') else ''
            location = self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else ''
            website = self.txt_website.text().strip() if hasattr(self, 'txt_website') else ''
            shipping = self.txt_envios.text().strip() if hasattr(self, 'txt_envios') else ''
            info_summary = whatsapp or location or website or shipping or 'Sin información configurada'
            self.info_status_label.setText(self._truncate_status_text(info_summary, max_length=52))

        rules = len([line for line in self.config_faq.splitlines() if line.strip()])
        if hasattr(self, 'faq_status_label'):
            self.faq_status_label.setText(self._truncate_status_text(f"{rules} reglas configuradas", max_length=52))

    def _create_side_panel_animation(self):
        self.side_panel_animation = QPropertyAnimation(self.side_panel_container, b"fixedWidth", self)
        self.side_panel_animation.setDuration(260)
        self.side_panel_animation.finished.connect(self._on_side_panel_animation_finished)

    def _on_side_panel_animation_finished(self):
        if self.side_panel_container.width() == 0:
            self.side_panel_container.setVisible(False)

    def _refresh_wizard_buttons(self):
        index = self.stacked.currentIndex()
        self.footer_prev.setEnabled(index > 0 and not (self.is_edit_mode and index == 1))
        self.footer.setVisible(index != 0)
        self.footer_next.setText("Finalizar Configuración" if index == self.stacked.count() - 1 else "Siguiente")

    def toggle_side_panel(self, show=True):
        if show:
            if hasattr(self, 'stacked'):
                self.stacked.setEnabled(False)
            self.side_panel_container.setVisible(True)
            self.side_panel_animation.stop()
            self.side_panel_animation.setStartValue(self.side_panel_container.width())
            self.side_panel_animation.setEndValue(360)
            self.side_panel_animation.start()
        else:
            if self.side_panel_container.width() == 0:
                self.side_panel_container.setVisible(False)
                return
            self.side_panel_animation.stop()
            self.side_panel_animation.setStartValue(self.side_panel_container.width())
            self.side_panel_animation.setEndValue(0)
            self.side_panel_animation.start()

    def _close_side_panel(self):
        self.side_panel_animation.stop()
        self.side_panel_container.setVisible(False)
        self.side_panel_container.setMinimumWidth(0)
        if hasattr(self, 'stacked'):
            self.stacked.setEnabled(True)
            self.stacked.setFocus()
        self._refresh_wizard_buttons()

    def _show_save_notification(self):
        QMessageBox.information(self, "Datos guardados", "Se guardaron los datos correctamente.")

    def _rotate_spinner(self):
        self.spinner_angle = (self.spinner_angle + 12) % 360
        transform = QTransform().rotate(self.spinner_angle)
        rotated = self.spinner_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        rotated = rotated.scaled(self.spinner_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.spinner_label.setPixmap(rotated)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def _build_page1(self):
        layout = QVBoxLayout(self.page1)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Login de Instagram")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Ingresa tus credenciales para iniciar la configuración del asistente.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Usuario de Instagram")
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Contraseña de Instagram")
        layout.addWidget(self.pass_input)

        self.page1_status = QLabel("Introduce tus credenciales y valida para continuar.")
        self.page1_status.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.page1_status)

        self.btn_validate = QPushButton(qta.icon('fa5s.check', color='#00E5FF'), "VALIDAR Y CONTINUAR")
        self.btn_validate.setObjectName("PrimaryBtn")
        self.btn_validate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate.clicked.connect(self.validate_credentials)
        layout.addWidget(self.btn_validate)
        layout.addStretch()

        if self.is_edit_mode:
            self.btn_validate.setVisible(False)
            self.page1_status.setText("Modo edición: valida no es necesario.")

    def _toggle_password_visibility(self):
        if self.pass_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_eye.setText("🔒")
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_eye.setText("👁️")

    def _build_page2(self):
        layout = QVBoxLayout(self.page2)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Identidad de la tienda")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Revisa y personaliza el nombre y la propuesta de valor de tu negocio.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.store_input = QLineEdit()
        self.store_input.setPlaceholderText("Nombre del negocio")
        layout.addWidget(self.store_input)

        assistant_group = QWidget()
        assistant_group_layout = QHBoxLayout(assistant_group)
        assistant_group_layout.setContentsMargins(0, 0, 0, 0)
        assistant_group_layout.setSpacing(14)
        assistant_group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        assistant_field = QWidget()
        assistant_field_layout = QVBoxLayout(assistant_field)
        assistant_field_layout.setContentsMargins(0, 0, 0, 0)
        assistant_field_layout.setSpacing(4)
        assistant_field_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        assistant_label = QLabel("¿Cómo se llama tu asistente?")
        assistant_label.setProperty("class", "QuestionLabel")
        assistant_label.setStyleSheet("margin-top: 4px; margin-bottom: 4px; color: #8ea1b8; font-size: 12px;")
        assistant_field_layout.addWidget(assistant_label)

        self.assistant_name_input = QLineEdit()
        self.assistant_name_input.setPlaceholderText("Ej: Carlos, Sofía")
        self.assistant_name_input.setStyleSheet("background: #1A1A1A; color: #FFFFFF; font-size: 14px; padding: 10px 10px; border: none; border-bottom: 1px solid #444444; border-radius: 4px 4px 0 0;")
        self.assistant_name_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.assistant_name_input.setMinimumHeight(46)
        self.assistant_name_input.setFixedHeight(46)
        assistant_field_layout.addWidget(self.assistant_name_input)

        business_field = QWidget()
        business_field_layout = QVBoxLayout(business_field)
        business_field_layout.setContentsMargins(0, 0, 0, 0)
        business_field_layout.setSpacing(4)
        business_field_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.business_type_label = QLabel("Tipo de negocio")
        self.business_type_label.setProperty("class", "QuestionLabel")
        self.business_type_label.setStyleSheet("margin-top: 4px; margin-bottom: 4px; color: #8ea1b8; font-size: 12px;")
        business_field_layout.addWidget(self.business_type_label)

        self.business_type_combo = QComboBox()
        self.business_type_combo.setObjectName("BusinessTypeCombo")
        self.business_type_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.business_type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.business_type_combo.setMinimumHeight(46)
        self.business_type_combo.setFixedHeight(46)
        self.business_type_combo.addItems(["Comercio", "Profesional", "Reservas", "Marca Personal", "Corporativo"])
        self.business_type_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px 12px 10px 10px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox:focus { outline: none; }"
        )
        business_field_layout.addWidget(self.business_type_combo)

        assistant_group_layout.addWidget(assistant_field)
        assistant_group_layout.addWidget(business_field)
        layout.addWidget(assistant_group)

        mission_label = QLabel("Misión del bot")
        mission_label.setProperty("class", "QuestionLabel")
        mission_label.setStyleSheet("margin-top: 4px; margin-bottom: 4px; color: #8ea1b8; font-size: 12px;")
        layout.addWidget(mission_label)

        self.mission_buttons = []
        self.mission_selected = "Ventas"
        mission_layout = QGridLayout()
        mission_layout.setSpacing(10)

        mission_names = ["Ventas", "Agendador", "Captación", "Soporte"]
        for index, name in enumerate(mission_names):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setObjectName("MissionChip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked, key=name: self.select_mission_card(key))
            button.setMinimumHeight(38)
            self.mission_buttons.append(button)
            row = index // 2
            col = index % 2
            mission_layout.addWidget(button, row, col)

        layout.addLayout(mission_layout)

        self.select_mission_card(self.mission_selected)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Propuesta de valor de tu tienda")
        self.description_input.setMinimumHeight(100)
        self.description_input.setMaximumHeight(140)
        layout.addWidget(self.description_input)

        self.page2_status = QLabel("Estos campos alimentarán la personalidad del asistente.")
        self.page2_status.setStyleSheet("color: #a5b1c2;")
        layout.addWidget(self.page2_status)
        layout.addStretch()

    def _build_page3(self):
        layout = QVBoxLayout(self.page3)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Personalidad del asistente")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Elige el tono que deseas para las respuestas automáticas.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        personality_layout = QVBoxLayout()
        personality_layout.setSpacing(10)

        self.personality_buttons = []
        self.personality_selected = "Vendedor Quirúrgico"

        personality_names = ["Vendedor Quirúrgico", "Asistente Creativo", "Soporte Profesional"]
        for name in personality_names:
            button = QPushButton(name)
            button.setCheckable(True)
            button.setObjectName("MissionChip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked, key=name: self.select_personality_card(key))
            button.setMinimumHeight(38)
            self.personality_buttons.append(button)
            personality_layout.addWidget(button)

        layout.addLayout(personality_layout)

        self.personality_description = QLabel(
            "Escoge un estilo de comunicación y el asistente ajustará su tono al cliente."
        )
        self.personality_description.setWordWrap(True)
        self.personality_description.setStyleSheet("color: #FFFFFF; background-color: transparent; padding: 12px 0;")
        layout.addWidget(self.personality_description)

        self.page3_status = QLabel("")
        self.page3_status.setStyleSheet("color: #a5b1c2;")
        layout.addWidget(self.page3_status)
        layout.addStretch()

        self.select_personality_card(self.personality_selected)

    def _build_page4(self):
        layout = QVBoxLayout(self.page4)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.page4.setMaximumHeight(600)

        title = QLabel("Operaciones")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Revisa los estados clave y abre el panel lateral para ajustar cada área.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.finance_status_label = QLabel("")
        self.catalog_status_label = QLabel("")
        self.attention_status_label = QLabel("")
        self.faq_status_label = QLabel("")
        self.info_status_label = QLabel("")

        layout.addWidget(self._create_status_card(
            "Finanzas y Moneda",
            self.finance_status_label,
            "Editar",
            lambda: self._open_side_panel_section("Finanzas")
        ))
        layout.addWidget(self._create_status_card(
            "Catálogo e Inventario",
            self.catalog_status_label,
            "Gestionar",
            lambda: self._open_side_panel_section("Catálogo")
        ))
        layout.addWidget(self._create_status_card(
            "Información y Direcciones",
            self.info_status_label,
            "Editar",
            lambda: self._open_side_panel_section("Información")
        ))
        layout.addWidget(self._create_status_card(
            "Atención y Horarios",
            self.attention_status_label,
            "Editar",
            lambda: self._open_side_panel_section("Atención")
        ))
        layout.addWidget(self._create_status_card(
            "Conocimiento Extra",
            self.faq_status_label,
            "Editar",
            lambda: self._open_side_panel_section("Conocimiento")
        ))

        self.card_note = QLabel("Usa estas tarjetas para abrir el panel lateral y ajustar cada sección sin saturar la vista.")
        self.card_note.setStyleSheet("color: #777777; font-size: 12px;")
        self.card_note.setWordWrap(True)
        layout.addWidget(self.card_note)

        layout.addStretch()

    def display_digested_context(self, data):
        self.digested_context_data = data or {}
        for i in reversed(range(self.aspect_layout.count())):
            widget = self.aspect_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        cards = {
            "Categoría": data.get('category', 'Sin datos'),
            "Nicho": data.get('niche', 'Sin datos'),
            "Productos/Servicios": data.get('products_services', 'Sin datos'),
            "Tono": data.get('tone', 'Sin datos'),
            "Ubicación": data.get('location', 'Sin datos'),
        }

        for key, value in cards.items():
            card = QPushButton(f"{key}: {value}")
            card.setObjectName("AspectCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.clicked.connect(lambda checked, k=key: self._edit_aspect(k))
            self.aspect_layout.addWidget(card)
            self.digested_context_data[key] = value

    def _edit_aspect(self, key):
        current = self.digested_context_data.get(key, '')
        text, ok = QInputDialog.getText(self, f"Editar {key}", f"Nuevo valor para {key}:", text=current)
        if ok and text:
            self.digested_context_data[key] = text
            self.display_digested_context(self.digested_context_data)

    def _edit_details(self):
        for key in ["Categoría", "Nicho", "Productos/Servicios", "Tono", "Ubicación"]:
            self._edit_aspect(key)

    def _create_info_panel_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Información y Direcciones")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Configura el contacto, la dirección, el sitio web, envíos y la información clave que el asistente debe conocer.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.txt_whatsapp_label = QLabel("¿A qué WhatsApp enviamos a los clientes (Ventas complejas)?")
        self.txt_whatsapp_label.setProperty("class", "QuestionLabel")
        self.txt_whatsapp_label.setWordWrap(True)
        layout.addWidget(self.txt_whatsapp_label)

        self.txt_whatsapp = QLineEdit()
        self.txt_whatsapp.setPlaceholderText("+58...")
        self.txt_whatsapp.setMaximumWidth(300)
        layout.addWidget(self.txt_whatsapp)

        self.txt_ubicacion_label = QLabel("¿Dónde está ubicado tu negocio?")
        self.txt_ubicacion_label.setProperty("class", "QuestionLabel")
        self.txt_ubicacion_label.setWordWrap(True)
        layout.addWidget(self.txt_ubicacion_label)

        self.txt_ubicacion = QLineEdit()
        self.txt_ubicacion.setPlaceholderText("Ej: Local 4, Centro Comercial X. (O 'Solo tienda virtual')")
        self.txt_ubicacion.setMaximumWidth(300)
        layout.addWidget(self.txt_ubicacion)

        self.txt_website_label = QLabel("¿Tienes sitio web o catálogo online?")
        self.txt_website_label.setProperty("class", "QuestionLabel")
        self.txt_website_label.setWordWrap(True)
        layout.addWidget(self.txt_website_label)

        self.txt_website = QLineEdit()
        self.txt_website.setPlaceholderText("Ej: https://miempresa.com")
        self.txt_website.setMaximumWidth(300)
        layout.addWidget(self.txt_website)

        self.location_frame = QFrame()
        self.location_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid #222222; border-radius: 16px;")
        self.location_frame.setMaximumWidth(250)
        location_layout = QVBoxLayout(self.location_frame)
        location_layout.setContentsMargins(16, 16, 16, 16)
        location_layout.setSpacing(14)

        self.txt_country_label = QLabel("¿En qué país opera tu negocio?")
        self.txt_country_label.setProperty("class", "QuestionLabel")
        self.txt_country_label.setWordWrap(True)
        location_layout.addWidget(self.txt_country_label)
        self.txt_country = QLineEdit()
        self.txt_country.setPlaceholderText("Ej: Venezuela")
        self.txt_country.setMaximumWidth(280)
        self.txt_country.addAction(qta.icon('fa5s.globe', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_country)

        self.txt_language_label = QLabel("¿Cuál es el idioma principal de atención?")
        self.txt_language_label.setProperty("class", "QuestionLabel")
        self.txt_language_label.setWordWrap(True)
        location_layout.addWidget(self.txt_language_label)
        self.txt_language = QLineEdit()
        self.txt_language.setPlaceholderText("Ej: es")
        self.txt_language.setMaximumWidth(280)
        self.txt_language.addAction(qta.icon('fa5s.language', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_language)

        self.txt_currency_symbol_label = QLabel("¿Cuál es el símbolo de tu moneda?")
        self.txt_currency_symbol_label.setProperty("class", "QuestionLabel")
        self.txt_currency_symbol_label.setWordWrap(True)
        location_layout.addWidget(self.txt_currency_symbol_label)
        self.txt_currency_symbol = QLineEdit()
        self.txt_currency_symbol.setPlaceholderText("Ej: Bs")
        self.txt_currency_symbol.setMaximumWidth(280)
        self.txt_currency_symbol.addAction(qta.icon('fa5s.money-bill-wave', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_currency_symbol)

        self.txt_currency_code_label = QLabel("¿Cuál es el código de la moneda local?")
        self.txt_currency_code_label.setProperty("class", "QuestionLabel")
        self.txt_currency_code_label.setWordWrap(True)
        location_layout.addWidget(self.txt_currency_code_label)
        self.txt_currency_code = QLineEdit()
        self.txt_currency_code.setPlaceholderText("Ej: COP")
        self.txt_currency_code.setMaximumWidth(280)
        self.txt_currency_code.addAction(qta.icon('fa5s.tag', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_currency_code)

        self.txt_currency_name_label = QLabel("¿Cómo llamas a la moneda local?")
        self.txt_currency_name_label.setProperty("class", "QuestionLabel")
        self.txt_currency_name_label.setWordWrap(True)
        location_layout.addWidget(self.txt_currency_name_label)
        self.txt_currency_name = QLineEdit()
        self.txt_currency_name.setPlaceholderText("Ej: Pesos colombianos")
        self.txt_currency_name.setMaximumWidth(280)
        self.txt_currency_name.addAction(qta.icon('fa5s.coins', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_currency_name)

        self.txt_rag_context_label = QLabel("Contexto adicional para respuestas (RAG)")
        self.txt_rag_context_label.setProperty("class", "QuestionLabel")
        self.txt_rag_context_label.setWordWrap(True)
        location_layout.addWidget(self.txt_rag_context_label)
        self.txt_rag_context = QTextEdit()
        self.txt_rag_context.setPlaceholderText("Describe información clave, productos destacados o datos que el bot debe usar como contexto adicional.")
        self.txt_rag_context.setMaximumWidth(280)
        self.txt_rag_context.setFixedHeight(100)
        location_layout.addWidget(self.txt_rag_context)

        layout.addWidget(self.location_frame)

        self.txt_envios_label = QLabel("¿Cómo manejas los envíos o el delivery?")
        self.txt_envios_label.setProperty("class", "QuestionLabel")
        self.txt_envios_label.setWordWrap(True)
        layout.addWidget(self.txt_envios_label)

        self.txt_envios = QLineEdit()
        self.txt_envios.setPlaceholderText("Ej: Delivery gratis en el centro, $3 a otras zonas.")
        self.txt_envios.setMaximumWidth(300)
        layout.addWidget(self.txt_envios)

        self.txt_info_eventos_label = QLabel("¿Tienes Lives, eventos, promociones o información adicional para el asistente?")
        self.txt_info_eventos_label.setProperty("class", "QuestionLabel")
        self.txt_info_eventos_label.setWordWrap(True)
        layout.addWidget(self.txt_info_eventos_label)

        self.txt_info_eventos = QTextEdit()
        self.txt_info_eventos.setPlaceholderText("Ej: Lives los viernes, descuentos especiales, reservaciones por WhatsApp y directrices de atención como ser amable y mencionar envíos.")
        self.txt_info_eventos.setFixedHeight(80)
        self.txt_info_eventos.setMaximumWidth(300)
        self.txt_info_eventos.setStyleSheet("background: #1A1A1A; border: none; border-bottom: 1px solid #444444; border-radius: 10px; color: #FFFFFF;")
        layout.addWidget(self.txt_info_eventos)

        self.page5_status = QLabel("Define las reglas operativas antes de continuar al resumen final.")
        self.page5_status.setStyleSheet("color: #a5b1c2; margin-top: 8px;")
        layout.addWidget(self.page5_status)

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setMaximumWidth(240)
        btn_save.clicked.connect(self._save_info_panel)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

        return page

    def _build_page6(self):
        layout = QVBoxLayout(self.page6)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setStyleSheet(
            "background-color: #121212;"
            "border-radius: 12px;"
            "border: 1px solid #333333;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(18)

        title = QLabel("Configuración Lista")
        title.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: bold;")
        card_layout.addWidget(title)

        subtitle = QLabel("Tu configuración está lista. Prueba al asistente antes de finalizar para asegurarte de que todo está en orden.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #A0A0A0; font-size: 13px;")
        card_layout.addWidget(subtitle)

        def build_info_cell(icon_name, title_text, value_label):
            cell = QFrame()
            cell.setStyleSheet(
                "QFrame {"
                "background-color: rgba(255,255,255,0.03);"
                "border-radius: 14px;"
                "}"
            )
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(14, 12, 14, 12)
            cell_layout.setSpacing(12)

            icon = QLabel()
            icon.setPixmap(qta.icon(icon_name, color='#00E5FF').pixmap(20, 20))
            icon.setFixedSize(22, 22)
            cell_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

            text_container = QWidget()
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(4)

            title = QLabel(title_text)
            title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
            value_label.setStyleSheet("color: #A0A0A0; font-size: 13px;")
            value_label.setWordWrap(True)

            text_layout.addWidget(title)
            text_layout.addWidget(value_label)
            cell_layout.addWidget(text_container)
            return cell

        self.lbl_resumen_nombre = QLabel(self.assistant_name_input.text().strip() or "No asignado")
        self.lbl_resumen_mision = QLabel(self.mission_selected)
        start_time_label = self.start_time.time().toString('HH:mm') if hasattr(self, 'start_time') else '08:00'
        end_time_label = self.end_time.time().toString('HH:mm') if hasattr(self, 'end_time') else '18:00'
        self.lbl_resumen_horario = QLabel(f"{start_time_label} - {end_time_label}")
        self.lbl_resumen_pais = QLabel(self.txt_country.text().strip() if hasattr(self, 'txt_country') else 'No definido')
        self.lbl_resumen_tipo = QLabel(self.business_type_combo.currentText() if hasattr(self, 'business_type_combo') else 'No definido')
        inventory_status = os.path.basename(self.csv_path) if self.csv_path else "No cargado"
        self.lbl_resumen_inventario = QLabel(inventory_status)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(build_info_cell('fa5s.user', 'Nombre', self.lbl_resumen_nombre), 0, 0)
        grid.addWidget(build_info_cell('fa5s.lightbulb', 'Misión', self.lbl_resumen_mision), 0, 1)
        grid.addWidget(build_info_cell('fa5s.clock', 'Horario', self.lbl_resumen_horario), 0, 2)
        grid.addWidget(build_info_cell('fa5s.globe', 'País', self.lbl_resumen_pais), 1, 0)
        grid.addWidget(build_info_cell('fa5s.store', 'Tipo', self.lbl_resumen_tipo), 1, 1)
        grid.addWidget(build_info_cell('fa5s.boxes', 'Inventario', self.lbl_resumen_inventario), 1, 2)
        card_layout.addLayout(grid)

        layout.addWidget(card)
        layout.addStretch()

    def goto_summary(self):
        self.update_role_logic()
        if self.end_time.time() <= self.start_time.time():
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
            return
        self.stacked.setCurrentIndex(self.stacked.count() - 1)

    def load_summary_page(self):
        self.get_data()
        self.update_role_logic()
        data = self.current_state

        self.lbl_resumen_nombre.setText(data.get('bot_name', 'No asignado'))
        self.lbl_resumen_mision.setText(data.get('bot_mission', 'No definida'))
        self.lbl_resumen_horario.setText(f"{data.get('start_time', '08:00')} - {data.get('end_time', '18:00')}")
        self.lbl_resumen_pais.setText(data.get('country', 'No definido'))
        self.lbl_resumen_tipo.setText(self.business_type_combo.currentText() if hasattr(self, 'business_type_combo') else 'No definido')

        inventory_path = data.get('inventory_path', '')
        if inventory_path:
            file_name = os.path.basename(inventory_path)
            self.lbl_resumen_inventario.setText(f"Inventario CSV: {file_name}")
            self.lbl_resumen_inventario.setStyleSheet("color: #22FF8A;")
        else:
            self.lbl_resumen_inventario.setText("Inventario CSV: No cargado")
            self.lbl_resumen_inventario.setStyleSheet("color: #FF5555;")

        self.summary_display.setPlainText(self.get_summary_text())
        if not self.preview_input.text().strip():
            self.preview_input.setPlaceholderText("Escribe o usa una pregunta aleatoria para probar al agente...")
        self.preview_output.setPlainText("")
        self.page6_status.setText("Revisa todo antes de guardar y prueba el estilo de respuesta.")

    def get_summary_text(self):
        payments = [item['method'] for item in self.payment_methods_data] if hasattr(self, 'payment_methods_data') else []
        payment_details = [
            f"{item['method']}: {item['detail']}"
            for item in self.payment_methods_data
            if item.get('detail')
        ]
        inventory = "Sí" if self.inventory_connected else "No"
        inventory_info = f"{self.inventory_rows} productos" if self.inventory_connected else "sin inventario"
        assistant = self.assistant_name_input.text().strip() or "No asignado"
        store = self.store_input.text().strip() or "No asignado"
        summary_lines = [
            f"Negocio: {store}",
            f"Asistente: {assistant}",
            f"Tipo de negocio: {self.business_type_combo.currentText() if hasattr(self, 'business_type_combo') else 'No definido'}",
            f"Personalidad elegida: {self.personality_selected}",
            f"Horario de atención: {self.start_time.time().toString('HH:mm')} - {self.end_time.time().toString('HH:mm')}",
            f"Inventario conectado: {inventory} ({inventory_info})",
            f"Ubicación: {self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else 'No definido'}",
            f"Sitio web: {self.txt_website.text().strip() if hasattr(self, 'txt_website') else 'No definido'}",
            f"País: {self.txt_country.text().strip() if hasattr(self, 'txt_country') else 'No definido'}",
            f"Idioma: {self.txt_language.text().strip() if hasattr(self, 'txt_language') else 'No definido'}",
            f"Símbolo de moneda: {self.txt_currency_symbol.text().strip() if hasattr(self, 'txt_currency_symbol') else 'No definido'}",
            f"WhatsApp de contacto: {self.txt_whatsapp.text().strip() if hasattr(self, 'txt_whatsapp') else 'No definido'}",
            f"Métodos de pago: {', '.join(payments) if payments else 'No definidos'}",
        ]
        if payment_details:
            summary_lines.append(f"Detalles de pago: {'; '.join(payment_details)}")
        summary_lines.extend([
            f"Lives / eventos / FAQ: {self.txt_info_eventos.toPlainText().strip() if hasattr(self, 'txt_info_eventos') else 'No definidos'}",
            "",
            "La configuración interna del asistente se guarda en segundo plano y no se muestra directamente aquí.",
        ])
        return "\n".join(summary_lines)

    def use_random_preview_prompt(self):
        examples = [
            "¿Tienen algún descuento disponible para este producto?",
            "¿Cuánto cuesta el envío al centro de la ciudad?",
            "Estoy interesado en saber si este artículo está disponible ahora mismo.",
            "¿Pueden enviar a otro estado?",
            "¿Qué medios de pago aceptan y cómo hago el pedido?",
        ]
        self.preview_input.setText(random.choice(examples))

    def on_page_changed(self, index):
        self.footer.setVisible(index != 0)
        self.footer_prev.setEnabled(index > 0)
        if index == self.stacked.count() - 1:
            self.footer_next.setText("Finalizar Configuración")
        last_page = index == self.stacked.count() - 1
        if last_page:
            self.footer_next.setText("Finalizar Configuración")
        else:
            self.footer_next.setText("Siguiente")

        if index == 0:
            self.page1_status.setText("Introduce tus credenciales y valida para continuar.")
        elif index == 1:
            self.page2_status.setText("Prepara la identidad de tu tienda.")
        elif index == 2:
            self.page3_status.setText("Selecciona la personalidad del asistente.")
        elif index == 3:
            self.update_role_logic()
        elif index == 4:
            self.page5_status.setText("Define las reglas operativas antes de continuar al resumen final.")
        elif index == self.stacked.count() - 1:
            self.load_summary_page()

        self._refresh_wizard_buttons()

    def _load_account_data(self, account_data):
        self.user_input.setText(account_data.get('insta_user', ''))
        self.pass_input.setText("")
        self.store_input.setText(account_data.get('store_name', ''))
        self.assistant_name_input.setText(
            account_data.get('assistant_name', account_data.get('bot_name', account_data.get('business_name', '')))
        )
        self.description_input.setPlainText(account_data.get('business_data', account_data.get('description', '')))
        self.personality_selected = account_data.get('bot_role', account_data.get('context_type', 'Vendedor Quirúrgico'))
        self.select_personality_card(self.personality_selected)
        if hasattr(self, 'mission_selected'):
            self.select_mission_card(account_data.get('bot_mission', 'Ventas'))
        self.start_time.setTime(QTime.fromString(account_data.get('schedule_start', '08:00'), 'HH:mm'))
        self.end_time.setTime(QTime.fromString(account_data.get('schedule_end', '18:00'), 'HH:mm'))
        self.hidden_prompt = account_data.get('system_prompt', '')
        self.csv_path = os.path.abspath(account_data.get('inventory_path', '')) if account_data.get('inventory_path') else ''
        self.inventory_connected = bool(self.csv_path)
        if self.inventory_connected:
            if hasattr(self, 'catalog_status_label'):
                self.catalog_status_label.setText(f"✅ {self.csv_path}")
            self.inventory_headers = account_data.get('inventory_metadata', {}).get('headers', [])
            self.inventory_rows = account_data.get('inventory_rows', 0)
        if hasattr(self, 'txt_whatsapp'):
            self.txt_whatsapp.setText(account_data.get('whatsapp_number', ''))
        if hasattr(self, 'txt_ubicacion'):
            self.txt_ubicacion.setText(account_data.get('location', account_data.get('ubicacion', '')))
        if hasattr(self, 'txt_website'):
            self.txt_website.setText(account_data.get('website', ''))
        self.config_country = account_data.get('country', account_data.get('config_country', 'Venezuela'))
        if hasattr(self, 'txt_country'):
            self.txt_country.setText(self.config_country)
        self.config_language = account_data.get('language', account_data.get('config_language', 'es'))
        if hasattr(self, 'txt_language'):
            self.txt_language.setText(self.config_language)
        if hasattr(self, 'txt_currency_symbol'):
            self.txt_currency_symbol.setText(account_data.get('currency_symbol', 'Bs'))
        if hasattr(self, 'txt_currency_code'):
            self.txt_currency_code.setText(account_data.get('currency_code', ''))
        if hasattr(self, 'txt_currency_name'):
            self.txt_currency_name.setText(account_data.get('currency_name', ''))
        if hasattr(self, 'txt_rag_context'):
            self.txt_rag_context.setPlainText(account_data.get('rag_context', ''))
        if hasattr(self, 'txt_envios'):
            self.txt_envios.setText(account_data.get('envios', ''))
        self.config_payments = account_data.get('payment_methods_text', account_data.get('config_payments', ''))
        self.side_payment_text = self.config_payments
        if hasattr(self, 'payment_methods_data'):
            raw_methods = account_data.get('payment_methods', [])
            raw_details = account_data.get('payment_method_details', {})
            if isinstance(raw_methods, str):
                try:
                    raw_methods = json.loads(raw_methods)
                except Exception:
                    raw_methods = []
            if isinstance(raw_details, str):
                try:
                    raw_details = json.loads(raw_details)
                except Exception:
                    raw_details = {}
            self.payment_methods_data = [
                {'method': method, 'detail': raw_details.get(method, '')}
                for method in (raw_methods or [])
            ]
        self.config_faq = account_data.get('info_eventos', account_data.get('config_faq', ''))
        if hasattr(self, 'txt_info_eventos'):
            self.txt_info_eventos.setPlainText(self.config_faq)
        if hasattr(self, 'business_type_combo'):
            business_type = account_data.get('type') or account_data.get('context_type')
            if business_type and self.business_type_combo.findText(business_type) >= 0:
                self.business_type_combo.setCurrentText(business_type)
            elif business_type:
                normalized = business_type.strip().lower()
                if 'retail' in normalized or 'vendedor' in normalized:
                    self.business_type_combo.setCurrentText('Comercio')
                elif 'profesional' in normalized or 'soporte' in normalized:
                    self.business_type_combo.setCurrentText('Profesional')
                elif 'booking' in normalized or 'cita' in normalized:
                    self.business_type_combo.setCurrentText('Reservas')
                elif 'marca' in normalized or 'personal' in normalized:
                    self.business_type_combo.setCurrentText('Marca Personal')
                else:
                    self.business_type_combo.setCurrentText('Corporativo')
        self.page1_status.setText("Edita los campos y guarda los cambios.")
        self.page2_status.setText("Revisa la identidad de la cuenta antes de guardar.")
        self.page3_status.setText("Ajusta la personalidad o continúa al horario.")

    def next_step(self):
        current = self.stacked.currentIndex()
        if current < self.stacked.count() - 1:
            self.stacked.setCurrentIndex(current + 1)
        else:
            self.finish_and_save()

    def prev_step(self):
        current = self.stacked.currentIndex()
        if self.is_edit_mode and current == 1:
            return
        if current > 0:
            self.stacked.setCurrentIndex(current - 1)

    def validate_credentials(self):
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not user or not password:
            self.page1_status.setText("Usuario y contraseña son obligatorios.")
            return
        self.page1_status.setText("Validando credenciales...")
        self.show_loading("Validando Instagram...")
        self.btn_validate.setEnabled(False)

        self.login_worker = LoginWorker(self.insta_service, user, password)
        self.login_worker.finished.connect(self.on_login_finished)
        self.login_worker.start()

    def on_login_finished(self, success, message):
        self.hide_loading()
        self.btn_validate.setEnabled(True)
        if success:
            self.page1_status.setText("Cuenta validada. Avanzando...")
            self.stacked.setCurrentIndex(1)
            self.page2_status.setText("Escaneando perfil automáticamente...")
            self.footer_next.setEnabled(False)
            self.start_profile_scan()
        else:
            self.page1_status.setText(message)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            'Confirmar Salida',
            '¿Estás seguro de que deseas cerrar el configurador?\n\nLos cambios no guardados se perderán.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.login_worker and self.login_worker.isRunning():
                self.login_worker.requestInterruption()
                self.login_worker.quit()
                self.login_worker.wait(500)
            if self.profile_worker and self.profile_worker.isRunning():
                self.profile_worker.requestInterruption()
                self.profile_worker.quit()
                self.profile_worker.wait(500)
            if hasattr(self, 'closed'):
                self.closed.emit()
            event.accept()
        else:
            event.ignore()

    def start_profile_scan(self):
        username = self.user_input.text().strip().lstrip('@')
        if not username:
            self.page2_status.setText("Debes validar el usuario antes de escanear.")
            self.footer_next.setEnabled(True)
            return

        self.page2_status.setText("Escaneando perfil de Instagram...")
        self.show_loading("Escaneando perfil...")
        self.profile_worker = ProfileScanWorker(self.insta_service, username)
        self.profile_worker.finished.connect(self.on_profile_scan_finished)
        self.profile_worker.error.connect(self.on_profile_scan_error)
        self.profile_worker.start()

    def on_profile_scan_finished(self, profile):
        self.hide_loading()
        self.footer_next.setEnabled(True)
        if not profile:
            self.page2_status.setText("No se pudo obtener el perfil. Completa la información manualmente.")
            return
        self.store_input.setText(profile.get('brand_name') or self.store_input.text())
        self.description_input.setPlainText(profile.get('value_proposition') or self.description_input.toPlainText())
        self.page2_status.setText("Identidad cargada. Revisa y pulsa Siguiente.")

    def on_profile_scan_error(self, message):
        self.hide_loading()
        self.footer_next.setEnabled(True)
        self.page2_status.setText(f"Error al escanear el perfil: {message}")

    def browse_inventory_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar inventario",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;Todos los archivos (*.*)",
        )
        if path:
            self.csv_path = os.path.abspath(path)
            self.inventory_connected = True
            self._analyze_inventory_file(self.csv_path)

    def _analyze_inventory_file(self, path):
        try:
            if not path.lower().endswith(('.csv', '.xlsx', '.xls')):
                QMessageBox.warning(self, "Formato Inválido", "Por favor selecciona un archivo CSV o Excel válido.")
                return

            if path.lower().endswith('.csv'):
                headers, rows = self._read_csv(path)
                self.inventory_type = 'CSV'
            else:
                headers, rows = self._read_excel(path)
                self.inventory_type = 'Excel'

            if not headers or not rows:
                QMessageBox.warning(self, "Archivo Vacío", "El archivo seleccionado parece estar vacío o dañado.")
                return

            headers_lower = [str(h).lower() for h in headers]
            palabras_clave = ["precio", "price", "producto", "product", "nombre"]
            if not any(palabra in " ".join(headers_lower) for palabra in palabras_clave):
                QMessageBox.critical(
                    self,
                    "Columnas Faltantes",
                    "¡Cuidado! El archivo no contiene columnas reconocibles de precios o productos.\n\n"
                    "Asegúrate de que la primera fila del Excel/CSV tenga títulos como 'Producto' o 'Precio_USD'."
                )
                return

            self.inventory_headers = headers
            self.inventory_rows = len(rows)
            self.current_state['inventory_path'] = path
            file_name = path.replace('\\', '/').split('/')[-1]
            if hasattr(self, 'catalog_status_label'):
                self.catalog_status_label.setText(f"✅ {file_name} cargado correctamente")
            if hasattr(self, 'lbl_file_path'):
                self.lbl_file_path.setText(file_name)
                self.lbl_file_path.setStyleSheet("color: #00E5FF;")
            self.page3_status.setText("Catálogo listo. Puedes continuar.")
            self.inventory_connected = True
            self.footer_next.setEnabled(True)
            if hasattr(self, '_update_status_cards'):
                self._update_status_cards()
        except Exception as e:
            self.inventory_connected = False
            self.inventory_headers = []
            self.inventory_rows = 0
            if hasattr(self, 'catalog_status_label'):
                self.catalog_status_label.setText(f"Error al analizar el archivo: {e}")
            self.page3_status.setText("No se pudo cargar el catálogo. Intenta con otro archivo.")
            self.footer_next.setEnabled(False)
            if hasattr(self, '_update_status_cards'):
                self._update_status_cards()

    def _read_csv(self, path):
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, [])
            rows = [row for row in reader if any(cell.strip() for cell in row)]
        return headers, rows

    def _read_excel(self, path):
        try:
            pd = importlib.import_module('pandas')
            df = pd.read_excel(path, engine='openpyxl' if path.lower().endswith('.xlsx') else None)
            headers = list(df.columns.astype(str))
            rows = df.dropna(how='all').values.tolist()
            return headers, rows
        except ModuleNotFoundError:
            if path.lower().endswith('.xlsx'):
                try:
                    openpyxl = importlib.import_module('openpyxl')
                    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                    sheet = wb.active
                    rows = list(sheet.iter_rows(values_only=True))
                    headers = [str(cell) if cell is not None else '' for cell in rows[0]] if rows else []
                    return headers, rows[1:]
                except Exception as excel_error:
                    raise ValueError(f'Error leyendo Excel: {excel_error}')
            if path.lower().endswith('.xls'):
                try:
                    xlrd = importlib.import_module('xlrd')
                    workbook = xlrd.open_workbook(path)
                    sheet = workbook.sheet_by_index(0)
                    headers = [str(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
                    rows = [sheet.row_values(row) for row in range(1, sheet.nrows)]
                    return headers, rows
                except Exception as excel_error:
                    raise ValueError(f'Error leyendo XLS: {excel_error}')
            raise ValueError('Pandas no está instalado y no se pudo leer el archivo Excel.')
        except Exception as e:
            raise ValueError(f'Error leyendo Excel: {e}')

    def skip_inventory(self):
        self.csv_path = ""
        self.inventory_connected = False
        self.inventory_headers = []
        self.inventory_rows = 0
        self.inventory_type = ""
        if hasattr(self, 'catalog_status_label'):
            self.catalog_status_label.setText("Continuar sin catálogo. El bot usará solo el contexto de la tienda.")
        self.page3_status.setText("Has decidido continuar sin catálogo.")
        self.footer_next.setEnabled(True)
        if hasattr(self, '_update_status_cards'):
            self._update_status_cards()

    def show_loading(self, text="Procesando..."):
        self.loading_overlay.setGeometry(self.rect())
        self.spinner_text.setText(text)
        self.loading_overlay.show()
        self.spinner_timer.start()
        self.loading_overlay.raise_()

    def hide_loading(self):
        if self.spinner_timer.isActive():
            self.spinner_timer.stop()
        self.loading_overlay.hide()

    def update_role_logic(self, _=None):
        tienda = self.store_input.text().strip() or "tu tienda"
        adn = self.description_input.toPlainText().strip() or "un negocio profesional"
        persona = self.personality_selected
        inventario = "sin inventario vinculado" if not self.inventory_connected else f"un catálogo con {self.inventory_rows} productos"

        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            start = self.start_time.time()
            end = self.end_time.time()
        else:
            start = QTime(8, 0)
            end = QTime(20, 0)

        horario_valido = end > start
        if not horario_valido:
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
        else:
            self.schedule_warning.setText("")

        if persona.startswith("Vendedor Quirúrgico"):
            self.personality_description.setText(
                "El asistente responde con enfoque comercial, prioriza cierres y sugiere productos de forma natural."
            )
        elif persona.startswith("Asistente Creativo"):
            self.personality_description.setText(
                "El asistente mantiene un tono cercano, dinámico y con respuestas imaginativas cuando es apropiado."
            )
        else:
            self.personality_description.setText(
                "El asistente responde con claridad, precisión y un estilo profesional adecuado para consultas serias."
            )

        prompt = (
            f"Eres un humano real, parte del equipo de atención de la empresa. "
            f"NUNCA admitas ser una IA, un bot o un asistente virtual. Si te preguntan, responde que eres el encargado digital de la tienda. "
            f"Tu única función es ser un asistente de la tienda. "
            f"No actúes como veterinario, médico, abogado, meteorólogo, técnico ni experto en temas ajenos a la tienda. "
            f"No inventes números largos, teléfonos, direcciones, códigos, datos personales ni información que no se encuentre en la descripción de la tienda o en el inventario. "
            f"Eres responsable de {tienda}. "
            f"ADN de la tienda: {adn}. Inventario: {inventario}. "
            f"Horario de atención: de {start.toString('HH:mm')} a {end.toString('HH:mm')}.")
        prompt += (
            " Usa un lenguaje natural, evita listas numeradas robóticas a menos que el cliente pida un catálogo. "
            "Si el cliente pregunta algo que no está en la descripción ni en el inventario, responde con naturalidad: "
            "'Lo siento, esa información no la tengo a mano; permíteme consultarlo con el encargado y te responderé con precisión.' "
            "No te desvíes a temas de salud, clima, mascotas, finanzas o cualquier otro asunto fuera del contexto de la tienda. "
            "No menciones que eres una IA ni digas que no puedes responder por ser un bot. "
            "Si hay stock, anima al cliente; si el stock es bajo (menos de 3), menciona que quedan pocas unidades para generar urgencia."
        )

        if self.inventory_connected:
            prompt += (
                f" Tienes un catálogo de productos. Usa la información de las columnas detectadas ({', '.join(self.inventory_headers)}) "
                "para dar respuestas precisas y humanas. Si el stock es 0, informa que no hay disponibilidad."
            )

        if persona.startswith("Vendedor Quirúrgico"):
            prompt += " Atiende con enfoque en ventas, sugiere ofertas y ayuda a cerrar compras con naturalidad."
        elif persona.startswith("Asistente Creativo"):
            prompt += " Responde con cercanía, energía y un toque dinámico, manteniendo siempre la claridad."
        elif persona.startswith("Soporte Profesional"):
            prompt += " Responde con seriedad, precisión y profesionalismo, enfocándote en la solución del cliente."

        self.hidden_prompt = prompt
        if hasattr(self, '_update_status_cards'):
            self._update_status_cards()

    def select_personality_card(self, name):
        self.personality_selected = name
        for card in self.personality_buttons:
            selected = card.text().startswith(name)
            card.setChecked(selected)
            card.setProperty("selected", selected)
            card.style().unpolish(card)
            card.style().polish(card)
        self.update_role_logic()

    def select_mission_card(self, name):
        self.mission_selected = name
        for card in self.mission_buttons:
            selected = card.text() == name
            card.setChecked(selected)
            card.setProperty("selected", selected)
            card.style().unpolish(card)
            card.style().polish(card)
        if hasattr(self, 'page2_status'):
            self.page2_status.setText(f"Misión seleccionada: {name}")


    def finish_and_save(self):
        self.update_role_logic()
        if self.end_time.time() <= self.start_time.time():
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
            return
        if hasattr(self, 'btn_finalize_save'):
            self.btn_finalize_save.setText("Guardando configuración...")
            self.btn_finalize_save.setEnabled(False)
        QTimer.singleShot(300, self._finish_save_commit)

    def _finish_save_commit(self):
        self.accept()

    def get_data(self):
        if hasattr(self, 'user_input') and self.user_input.text().strip():
            self.current_state['insta_user'] = self.user_input.text().strip()
        if hasattr(self, 'pass_input') and self.pass_input.text().strip():
            self.current_state['insta_pass'] = self.pass_input.text().strip()
        if hasattr(self, 'store_input'):
            self.current_state['store_name'] = self.store_input.text().strip()
        if hasattr(self, 'description_input'):
            self.current_state['description'] = self.description_input.toPlainText().strip()
        if hasattr(self, 'assistant_name_input'):
            self.current_state['bot_name'] = self.assistant_name_input.text().strip() or self.current_state.get('bot_name', 'Pegasus')
        if hasattr(self, 'mission_selected'):
            self.current_state['bot_mission'] = self.mission_selected
        if hasattr(self, 'personality_selected'):
            self.current_state['bot_role'] = self.personality_selected
        if hasattr(self, 'csv_path'):
            self.current_state['inventory_path'] = self.csv_path
        if hasattr(self, 'start_time'):
            self.current_state['start_time'] = self.start_time.time().toString('HH:mm')
        if hasattr(self, 'end_time'):
            self.current_state['end_time'] = self.end_time.time().toString('HH:mm')
        if hasattr(self, 'txt_whatsapp'):
            self.current_state['whatsapp_number'] = self.txt_whatsapp.text().strip()
        if hasattr(self, 'txt_ubicacion'):
            self.current_state['location'] = self.txt_ubicacion.text().strip()
        if hasattr(self, 'txt_website'):
            self.current_state['website'] = self.txt_website.text().strip()
        if hasattr(self, 'txt_currency_code'):
            self.current_state['currency_code'] = self.txt_currency_code.text().strip()
        if hasattr(self, 'txt_currency_name'):
            self.current_state['currency_name'] = self.txt_currency_name.text().strip()
        if hasattr(self, 'txt_rag_context'):
            self.current_state['rag_context'] = self.txt_rag_context.toPlainText().strip()
        if hasattr(self, 'txt_envios'):
            self.current_state['envios'] = self.txt_envios.text().strip()
        if hasattr(self, 'side_country_combo'):
            self.current_state['country'] = self.side_country_combo.currentText()
        if hasattr(self, 'side_language_input'):
            self.current_state['language'] = self.side_language_input.text().strip() or self.current_state.get('language', 'Español')
        if hasattr(self, 'business_hours_text_input'):
            self.current_state['business_hours_text'] = self.business_hours_text_input.text().strip()
        if hasattr(self, 'business_day_checkboxes'):
            self.current_state['business_days'] = [day for day, chk in self.business_day_checkboxes.items() if chk.isChecked()]

        if hasattr(self, 'business_type_combo'):
            self.current_state['type'] = self.business_type_combo.currentText()
        if hasattr(self, 'assistant_name_input'):
            assistant_name = self.assistant_name_input.text().strip()
            if assistant_name:
                self.current_state['business_name'] = assistant_name
            else:
                self.current_state['business_name'] = self.current_state.get('business_name', self.current_state.get('bot_name', ''))
            self.current_state['assistant_name'] = self.current_state['business_name']
            self.current_state['bot_name'] = self.current_state['business_name']
        if hasattr(self, 'payment_methods_data'):
            self.current_state['payment_methods'] = [p['method'] for p in self.payment_methods_data]
            self.current_state['payment_method_details'] = {p['method']: p['detail'] for p in self.payment_methods_data}
        if hasattr(self, 'start_time'):
            self.current_state['start'] = self.start_time.time().toString('HH:mm')
        if hasattr(self, 'end_time'):
            self.current_state['end'] = self.end_time.time().toString('HH:mm')

        self.current_state['user'] = self.current_state.get('insta_user', '')
        self.current_state['pass'] = self.current_state.get('insta_pass', '')
        self.current_state['prompt'] = self.current_state.get('system_prompt_final', self.current_state.get('system_prompt', ''))
        self.current_state['proxy'] = self.current_state.get('proxy', 'Auto')
        self.current_state['business_data'] = self.current_state.get('description', '')
        self.current_state['info_eventos'] = self.current_state.get('info_eventos', self.current_state.get('config_faq', ''))
        self.current_state['system_prompt_final'] = getattr(self, 'hidden_prompt', self.current_state.get('system_prompt', ''))
        return self.current_state
