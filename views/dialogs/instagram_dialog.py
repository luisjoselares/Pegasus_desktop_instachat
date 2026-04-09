import csv
import importlib
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
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QFrame,
    QInputDialog,
    QGridLayout,
    QLayout,
)
from PyQt6.QtGui import QTransform, QColor
from PyQt6.QtCore import Qt, QTime, QThread, pyqtSignal, QTimer, QPropertyAnimation
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
        self.is_edit_mode = bool(account_data)
        self.account_id = self.account_data.get('id') if self.is_edit_mode else None
        self.setWindowTitle("Configuración de Agente Pegasus" if not self.is_edit_mode else "Configuración de Cuenta")
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
        self.config_exchange = "1 USD = 36.5 Bs"
        self.config_payments = ""
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
                background-color: rgba(255, 255, 255, 0.02);
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px 10px;
                border: none;
                border-bottom: 1px solid #333333;
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
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(18)
        # Esto es la magia del Shrink-Wrap: La ventana se ajustará al panel
        self.main_layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)

        self.wizard_container = QFrame()
        self.wizard_container.setFixedSize(480, 580)
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
        self._build_page5()
        self._build_page6()

        self.stacked.addWidget(self.page1)
        self.stacked.addWidget(self.page2)
        self.stacked.addWidget(self.page3)
        self.stacked.addWidget(self.page4)
        self.stacked.addWidget(self.page5)
        self.stacked.addWidget(self.page6)
        self.stacked.currentChanged.connect(self.on_page_changed)

        self.fade_effect = QGraphicsOpacityEffect(self.stacked)
        self.stacked.setGraphicsEffect(self.fade_effect)

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
        self.main_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
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
        self.side_panel_container.setFixedWidth(0)
        self.side_panel_container.setMaximumWidth(300)
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
        self.side_panel_stack.addWidget(self._create_attention_panel_page())
        self.side_panel_stack.addWidget(self._create_faq_panel_page())

        self.side_panel_container.setVisible(False)
        self.main_layout.addWidget(self.side_panel_container)

    def _create_side_panel_page_header(self, title, description):
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        close_button = QPushButton(qta.icon('fa5s.arrow-left', color='#00E5FF'), "Cerrar")
        close_button.setObjectName("FlatBtn")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(lambda: self.toggle_side_panel(False))
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
            "Finanzas", "Ajusta país, idioma, tasa de cambio y métodos de pago."))

        self.side_country_combo = QComboBox()
        self.side_country_combo.addItems(["Venezuela", "México", "Colombia", "Argentina", "Chile", "Perú"])
        self.side_country_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_country_combo.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("País de operación"))
        layout.addWidget(self.side_country_combo)

        self.side_language_input = QLineEdit()
        self.side_language_input.setPlaceholderText("Ej: es")
        self.side_language_input.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("Idioma principal"))
        layout.addWidget(self.side_language_input)

        self.side_exchange_input = QLineEdit()
        self.side_exchange_input.setPlaceholderText("Ej: 1 USD = 3.600.000 Bs")
        self.side_exchange_input.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("Tasa de cambio"))
        layout.addWidget(self.side_exchange_input)

        self.side_payment_input = QTextEdit()
        self.side_payment_input.setPlaceholderText("Ej: Pago Móvil, Zelle, Binance, Efectivo")
        self.side_payment_input.setFixedHeight(120)
        self.side_payment_input.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        layout.addWidget(QLabel("Métodos de Pago"))
        layout.addWidget(self.side_payment_input)

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(lambda: self._save_finance_panel())
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return page

    def _create_faq_panel_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._create_side_panel_page_header(
            "FAQ / Lives", "Pega aquí todo el contenido extra que el asistente debe conocer."))

        self.side_faq_text = QTextEdit()
        self.side_faq_text.setPlaceholderText("Ej: Lives los viernes, promociones especiales, preguntas frecuentes, detalles de eventos...")
        self.side_faq_text.setStyleSheet("background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        self.side_faq_text.setMinimumHeight(260)
        layout.addWidget(self.side_faq_text)

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(lambda: self._save_faq_panel())
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return page

    def _create_catalog_panel_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._create_side_panel_page_header(
            "Catálogo", "Revisa y gestiona la información del inventario cargado."))

        self.side_catalog_info = QLabel()
        self.side_catalog_info.setStyleSheet("color: #A0A0A0; font-size: 13px;")
        self.side_catalog_info.setWordWrap(True)
        layout.addWidget(self.side_catalog_info)
        self._refresh_side_catalog_info()

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("PrimaryBtn")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(lambda: self.toggle_side_panel(False))
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return page

    def _create_attention_panel_page(self):
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self._create_side_panel_page_header(
            "Atención", "Ajusta el horario de atención y el estado activo."))

        self.side_attention_info = QLabel()
        self.side_attention_info.setStyleSheet("color: #A0A0A0; font-size: 13px;")
        self.side_attention_info.setWordWrap(True)
        layout.addWidget(self.side_attention_info)

        time_frame = QFrame()
        time_frame.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid #222222; border-radius: 12px;")
        time_layout = QHBoxLayout(time_frame)
        time_layout.setContentsMargins(12, 12, 12, 12)
        time_layout.setSpacing(12)

        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime(8, 0))
        self.start_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_time.setStyleSheet("background: transparent; color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        time_layout.addWidget(self.start_time)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime(20, 0))
        self.end_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.end_time.setStyleSheet("background: transparent; color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px;")
        time_layout.addWidget(self.end_time)

        layout.addWidget(time_frame)
        self._refresh_side_attention_info()

        btn_save = QPushButton("Listo")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_attention_panel)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return page

    def _refresh_side_catalog_info(self):
        csv_name = os.path.basename(self.csv_path) if self.csv_path else 'Sin catálogo cargado'
        self.side_catalog_info.setText(f"Archivo actual: {csv_name}")

    def _refresh_side_attention_info(self):
        if hasattr(self, 'start_time') and hasattr(self, 'end_time'):
            self.side_attention_info.setText(f"Horario actual: {self.start_time.time().toString('HH:mm')} - {self.end_time.time().toString('HH:mm')}")
        else:
            self.side_attention_info.setText("Activo 24/7")

    def _save_finance_panel(self):
        self.config_country = self.side_country_combo.currentText()
        self.config_language = self.side_language_input.text().strip() or self.config_language
        self.config_exchange = self.side_exchange_input.text().strip() or self.config_exchange
        self.config_payments = self.side_payment_input.toPlainText().strip()
        self.side_payment_text = self.config_payments
        self._update_status_cards()
        self.toggle_side_panel(False)

    def _save_faq_panel(self):
        self.config_faq = self.side_faq_text.toPlainText().strip()
        self.side_faq_text.setPlainText(self.config_faq)
        self._update_status_cards()
        self.toggle_side_panel(False)

    def _save_attention_panel(self):
        self._refresh_side_attention_info()
        self._update_status_cards()
        self.toggle_side_panel(False)

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
        button.setFixedWidth(110)
        card_layout.addWidget(button)

        return frame

    def _open_side_panel_section(self, section):
        mapping = {
            "Finanzas": 0,
            "Catálogo": 1,
            "Atención": 2,
            "Conocimiento": 3,
        }
        if section == "Finanzas":
            self.side_country_combo.setCurrentText(self.config_country)
            self.side_language_input.setText(self.config_language)
            self.side_exchange_input.setText(self.config_exchange)
            self.side_payment_input.setPlainText(self.config_payments)
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
                    f"{self.config_country} - {self.config_language} - Tasa: {self.config_exchange}",
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

    def toggle_side_panel(self, show=True):
        self.side_panel_container.setVisible(True)
        self.side_panel_animation.stop()
        self.side_panel_animation.setStartValue(self.side_panel_container.width())
        self.side_panel_animation.setEndValue(300 if show else 0)
        self.side_panel_animation.start()

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

        assistant_label = QLabel("¿Cómo se llama tu asistente? (Ej: Carlos, Sofía)")
        assistant_label.setProperty("class", "QuestionLabel")
        assistant_label.setStyleSheet("margin-top: 4px; margin-bottom: 4px; color: #8ea1b8; font-size: 12px;")
        layout.addWidget(assistant_label)

        self.assistant_name_input = QLineEdit()
        self.assistant_name_input.setPlaceholderText("Ej: Carlos, Sofía")
        self.assistant_name_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); color: #FFFFFF; font-size: 14px; padding: 10px 10px; border: none; border-bottom: 1px solid #333333; border-radius: 4px 4px 0 0;")
        layout.addWidget(self.assistant_name_input)

        self.business_type_label = QLabel("Tipo de negocio")
        self.business_type_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.business_type_label)
        self.business_type_combo = QComboBox()
        self.business_type_combo.setObjectName("BusinessTypeCombo")
        self.business_type_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.business_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.business_type_combo.setMinimumHeight(42)
        self.business_type_combo.addItems(["Comercio", "Profesional", "Reservas", "Marca Personal", "Corporativo"])
        self.business_type_combo.setStyleSheet(
            "QComboBox { background-color: rgba(255,255,255,0.03); color: #FFFFFF; border: 1px solid #333333; border-radius: 10px; padding: 10px 12px 10px 10px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox:focus { outline: none; }"
        )
        layout.addWidget(self.business_type_combo)

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

    def _apply_chip(self, text):
        current = self.custom_training_input.toPlainText().strip()
        if current:
            current += "\n"
        self.custom_training_input.setPlainText(current + text)

    def _build_page5(self):
        layout = QVBoxLayout(self.page5)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Configuración fija de IA")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Define la información clave que el asistente siempre debe conocer para evitar respuestas como 'no sé'.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.txt_whatsapp_label = QLabel("¿A qué WhatsApp enviamos a los clientes (Ventas complejas)?")
        self.txt_whatsapp_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_whatsapp_label)

        self.txt_whatsapp = QLineEdit()
        self.txt_whatsapp.setPlaceholderText("+58...")
        layout.addWidget(self.txt_whatsapp)

        self.txt_ubicacion_label = QLabel("¿Dónde está ubicado tu negocio?")
        self.txt_ubicacion_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_ubicacion_label)

        self.txt_ubicacion = QLineEdit()
        self.txt_ubicacion.setPlaceholderText("Ej: Local 4, Centro Comercial X. (O 'Solo tienda virtual')")
        layout.addWidget(self.txt_ubicacion)

        self.txt_website_label = QLabel("¿Tienes sitio web o catálogo online?")
        self.txt_website_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_website_label)

        self.txt_website = QLineEdit()
        self.txt_website.setPlaceholderText("Ej: https://miempresa.com")
        layout.addWidget(self.txt_website)

        self.location_frame = QFrame()
        self.location_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid #222222; border-radius: 16px;")
        location_layout = QVBoxLayout(self.location_frame)
        location_layout.setContentsMargins(16, 16, 16, 16)
        location_layout.setSpacing(14)

        self.txt_country_label = QLabel("¿En qué país opera tu negocio?")
        self.txt_country_label.setProperty("class", "QuestionLabel")
        location_layout.addWidget(self.txt_country_label)
        self.txt_country = QLineEdit()
        self.txt_country.setPlaceholderText("Ej: Venezuela")
        self.txt_country.addAction(qta.icon('fa5s.globe', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_country)

        self.txt_language_label = QLabel("¿Cuál es el idioma principal de atención?")
        self.txt_language_label.setProperty("class", "QuestionLabel")
        location_layout.addWidget(self.txt_language_label)
        self.txt_language = QLineEdit()
        self.txt_language.setPlaceholderText("Ej: es")
        self.txt_language.addAction(qta.icon('fa5s.language', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_language)

        self.txt_currency_symbol_label = QLabel("¿Cuál es el símbolo de tu moneda?")
        self.txt_currency_symbol_label.setProperty("class", "QuestionLabel")
        location_layout.addWidget(self.txt_currency_symbol_label)
        self.txt_currency_symbol = QLineEdit()
        self.txt_currency_symbol.setPlaceholderText("Ej: Bs")
        self.txt_currency_symbol.addAction(qta.icon('fa5s.money-bill-wave', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_currency_symbol)

        self.txt_tasa_cambio_label = QLabel("¿Cuál es tu tasa de cambio preferida?")
        self.txt_tasa_cambio_label.setProperty("class", "QuestionLabel")
        location_layout.addWidget(self.txt_tasa_cambio_label)
        self.txt_tasa_cambio = QLineEdit()
        self.txt_tasa_cambio.setPlaceholderText("Ej: 1 USD = 3.600.000 Bs")
        self.txt_tasa_cambio.addAction(qta.icon('fa5s.exchange-alt', color='#00E5FF'), QLineEdit.ActionPosition.LeadingPosition)
        location_layout.addWidget(self.txt_tasa_cambio)

        layout.addWidget(self.location_frame)

        self.txt_envios_label = QLabel("¿Cómo manejas los envíos o el delivery?")
        self.txt_envios_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_envios_label)

        self.txt_envios = QLineEdit()
        self.txt_envios.setPlaceholderText("Ej: Delivery gratis en el centro, $3 a otras zonas.")
        layout.addWidget(self.txt_envios)

        payment_label = QLabel("¿Qué métodos de pago aceptas?")
        payment_label.setProperty("class", "QuestionLabel")
        layout.addWidget(payment_label)

        payment_row = QHBoxLayout()
        payment_row.setSpacing(10)
        payment_row.setContentsMargins(0, 0, 0, 0)
        self.payment_buttons = []
        for method in ["Pago Móvil", "Zelle", "Binance", "Efectivo"]:
            payment_btn = QPushButton(method)
            payment_btn.setCheckable(True)
            payment_btn.setChecked(True)
            payment_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            payment_btn.setProperty("class", "PaymentTag")
            payment_btn.setFixedHeight(34)
            payment_row.addWidget(payment_btn)
            self.payment_buttons.append(payment_btn)

        layout.addLayout(payment_row)

        self.txt_info_eventos_label = QLabel("¿Tienes Lives, eventos o promociones especiales?")
        self.txt_info_eventos_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_info_eventos_label)

        self.txt_info_eventos = QTextEdit()
        self.txt_info_eventos.setPlaceholderText("Ej: Lives los viernes, descuentos en eventos especiales, reservaciones por WhatsApp.")
        self.txt_info_eventos.setFixedHeight(80)
        self.txt_info_eventos.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); border: 1px solid #222222; border-radius: 10px; color: #FFFFFF;")
        layout.addWidget(self.txt_info_eventos)

        self.custom_training_label = QLabel("Instrucciones adicionales para el asistente")
        self.custom_training_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.custom_training_label)
        self.custom_training_input = QTextEdit()
        self.custom_training_input.setPlaceholderText("Ej: Atiende con amabilidad, ofrece descuentos en paquetes y siempre menciona el envío.")
        self.custom_training_input.setMinimumHeight(100)
        self.custom_training_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); border: 1px solid #222222; border-radius: 10px; color: #FFFFFF;")
        layout.addWidget(self.custom_training_input)

        self.page5_status = QLabel("Define las reglas operativas antes de continuar al resumen final.")
        self.page5_status.setStyleSheet("color: #a5b1c2; margin-top: 8px;")
        layout.addWidget(self.page5_status)

        self.btn_finalizar = QPushButton("Ver resumen final")
        self.btn_finalizar.setObjectName("PrimaryBtn")
        self.btn_finalizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finalizar.setMaximumWidth(240)
        self.btn_finalizar.clicked.connect(self.goto_summary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.btn_finalizar)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _build_page6(self):
        layout = QVBoxLayout(self.page6)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Resumen y Prueba de Agente")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Revisa la configuración y haz una prueba rápida con el asistente.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setMinimumHeight(220)
        self.summary_display.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); color: #FFFFFF;")
        layout.addWidget(self.summary_display)

        self.summary_note = QLabel(
            "La configuración interna del asistente se genera y guarda de forma segura. "
            "Aquí ves solo lo esencial para revisar antes de activar."
        )
        self.summary_note.setWordWrap(True)
        self.summary_note.setStyleSheet("color: #777777; font-size: 12px;")
        layout.addWidget(self.summary_note)

        input_row = QHBoxLayout()
        self.preview_input = QLineEdit()
        self.preview_input.setPlaceholderText("Escribe una pregunta para probar al agente...")
        input_row.addWidget(self.preview_input)

        self.btn_preview = QPushButton("Probar agente")
        self.btn_preview.setObjectName("PrimaryBtn")
        self.btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview.clicked.connect(self.test_agent_response)
        input_row.addWidget(self.btn_preview)
        layout.addLayout(input_row)

        self.btn_random_prompt = QPushButton("Usar pregunta aleatoria")
        self.btn_random_prompt.setObjectName("FlatBtn")
        self.btn_random_prompt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_random_prompt.clicked.connect(self.use_random_preview_prompt)
        layout.addWidget(self.btn_random_prompt)

        self.preview_output = QTextEdit()
        self.preview_output.setReadOnly(True)
        self.preview_output.setMinimumHeight(160)
        self.preview_output.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); color: #FFFFFF;")
        layout.addWidget(self.preview_output)

        self.page6_status = QLabel("Revisa todo antes de guardar y prueba el estilo de respuesta.")
        self.page6_status.setStyleSheet("color: #a5b1c2; margin-top: 8px;")
        layout.addWidget(self.page6_status)

        self.btn_finalize_save = QPushButton("Finalizar y activar bot")
        self.btn_finalize_save.setObjectName("PrimaryBtn")
        self.btn_finalize_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finalize_save.setMaximumWidth(240)
        self.btn_finalize_save.clicked.connect(self.finish_and_save)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.btn_finalize_save)
        layout.addLayout(btn_row)

        layout.addStretch()

    def goto_summary(self):
        self.update_role_logic()
        if self.end_time.time() <= self.start_time.time():
            self.schedule_warning.setText("El horario de cierre debe ser posterior al de apertura")
            return
        self.stacked.setCurrentIndex(self.stacked.count() - 1)

    def load_summary_page(self):
        self.update_role_logic()
        self.summary_display.setPlainText(self.get_summary_text())
        if not self.preview_input.text().strip():
            self.preview_input.setPlaceholderText("Escribe o usa una pregunta aleatoria para probar al agente...")
        self.preview_output.setPlainText("")
        self.page6_status.setText("Revisa todo antes de guardar y prueba el estilo de respuesta.")

    def get_summary_text(self):
        payments = [btn.text() for btn in self.payment_buttons if btn.isChecked()] if hasattr(self, 'payment_buttons') else []
        custom = self.custom_training_input.toPlainText().strip() if hasattr(self, 'custom_training_input') else ""
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
            f"Tasa de cambio: {self.txt_tasa_cambio.text().strip() if hasattr(self, 'txt_tasa_cambio') else 'No definida'}",
            f"WhatsApp de contacto: {self.txt_whatsapp.text().strip() if hasattr(self, 'txt_whatsapp') else 'No definido'}",
            f"Métodos de pago: {', '.join(payments) if payments else 'No definidos'}",
            f"Lives / eventos: {self.txt_info_eventos.toPlainText().strip() if hasattr(self, 'txt_info_eventos') else 'No definidos'}",
            "",
            "Instrucciones personalizadas del asistente:",
            custom or "- Sin instrucciones adicionales -",
            "",
            "La configuración interna del asistente se guarda en segundo plano y no se muestra directamente aquí.",
        ]
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

    def test_agent_response(self):
        self.update_role_logic()
        question = self.preview_input.text().strip()
        if not question:
            self.page6_status.setText("Escribe una pregunta para probar al agente.")
            return
        self.page6_status.setText("Generando respuesta...")
        self.preview_output.setPlainText("Generando respuesta...")
        try:
            if hasattr(self.ai_service, 'get_response'):
                config = {
                    'country': self.txt_country.text().strip() if hasattr(self, 'txt_country') else 'Venezuela',
                    'language': self.txt_language.text().strip() if hasattr(self, 'txt_language') else 'es',
                    'currency_symbol': self.txt_currency_symbol.text().strip() if hasattr(self, 'txt_currency_symbol') else 'Bs',
                    'location': self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else '',
                    'website': self.txt_website.text().strip() if hasattr(self, 'txt_website') else '',
                    'exchange_rate': self.txt_tasa_cambio.text().strip() if hasattr(self, 'txt_tasa_cambio') else '',
                    'payment_methods': [btn.text() for btn in self.payment_buttons if btn.isChecked()] if hasattr(self, 'payment_buttons') else [],
                    'info_eventos': self.txt_info_eventos.toPlainText().strip() if hasattr(self, 'txt_info_eventos') else '',
                    'bot_name': self.assistant_name_input.text().strip(),
                    'whatsapp_contacto': self.txt_whatsapp.text().strip(),
                    'bot_role': self.personality_selected,
                    'business_profile': f"{self.store_input.text().strip()} - {self.description_input.toPlainText().strip()}",
                    'system_prompt': self.hidden_prompt,
                }
                inventory_rows = []
                if self.csv_path and hasattr(self.ai_service, '_load_inventory_rows'):
                    inventory_rows = self.ai_service._load_inventory_rows(self.csv_path)
                answer, _ = self.ai_service.get_response(
                    user_input=question,
                    config=config,
                    inventory_rows=inventory_rows,
                    time_context="CONTINUOUS",
                    custom_training=self.custom_training_input.toPlainText().strip(),
                    current_state=config.get('current_state', 'CONSULTA'),
                    bot_mission=config.get('bot_mission', 'Ventas'),
                )
            else:
                answer = self.ai_service.generate_response(
                    user_input=question,
                    system_prompt=self.hidden_prompt,
                    bot_role=self.personality_selected,
                    business_profile=f"{self.store_input.text().strip()} - {self.description_input.toPlainText().strip()}",
                    inventory_path=self.csv_path,
                    bot_name=self.assistant_name_input.text().strip(),
                    whatsapp_contacto=self.txt_whatsapp.text().strip(),
                    location=self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else '',
                    website=self.txt_website.text().strip() if hasattr(self, 'txt_website') else '',
                    exchange_rate=self.txt_tasa_cambio.text().strip() if hasattr(self, 'txt_tasa_cambio') else '',
                    currency_symbol=self.txt_currency_symbol.text().strip() if hasattr(self, 'txt_currency_symbol') else 'Bs',
                    payment_methods=[btn.text() for btn in self.payment_buttons if btn.isChecked()] if hasattr(self, 'payment_buttons') else [],
                    info_eventos=self.txt_info_eventos.toPlainText().strip() if hasattr(self, 'txt_info_eventos') else '',
                    time_context="CONTINUOUS",
                    custom_training=self.custom_training_input.toPlainText().strip(),
                )
            if answer is None:
                self.preview_output.setPlainText("No se pudo generar respuesta. Verifica la conexión de IA o la llave activa.")
            else:
                self.preview_output.setPlainText(answer)
                self.page6_status.setText("Prueba completada. Revisa la respuesta y guarda.")
        except Exception as e:
            self.preview_output.setPlainText(f"Error al generar la respuesta: {e}")
            self.page6_status.setText("No se pudo generar la prueba de agente.")

    def on_page_changed(self, index):
        self.footer.setVisible(index != 0)
        self.footer_prev.setEnabled(index > 0)
        if index == self.stacked.count() - 1:
            self.footer_next.setText("Activar asistente")
        last_page = index == self.stacked.count() - 1
        self.footer_next.setVisible(not last_page)
        if last_page:
            self.footer_next.setText("Activar asistente")
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

        self.animate_fade()

    def _load_account_data(self, account_data):
        self.user_input.setText(account_data.get('insta_user', ''))
        self.pass_input.setText("")
        self.store_input.setText(account_data.get('store_name', ''))
        self.assistant_name_input.setText(account_data.get('assistant_name', ''))
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
        self.config_exchange = account_data.get('exchange_rate', account_data.get('config_exchange', ''))
        if hasattr(self, 'txt_tasa_cambio'):
            self.txt_tasa_cambio.setText(self.config_exchange)
        if hasattr(self, 'txt_envios'):
            self.txt_envios.setText(account_data.get('envios', ''))
        self.config_payments = account_data.get('payment_methods_text', account_data.get('config_payments', ''))
        self.side_payment_text = self.config_payments
        if hasattr(self, 'side_payment_input'):
            self.side_payment_input.setPlainText(self.side_payment_text)
        if hasattr(self, 'payment_buttons'):
            selected_payments = set(account_data.get('payment_methods', []))
            for btn in self.payment_buttons:
                btn.setChecked(btn.text() in selected_payments)
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
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.requestInterruption()
            self.login_worker.quit()
            self.login_worker.wait(500)
        if self.profile_worker and self.profile_worker.isRunning():
            self.profile_worker.requestInterruption()
            self.profile_worker.quit()
            self.profile_worker.wait(500)
        super().closeEvent(event)

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
            lower = path.lower()
            if lower.endswith('.csv'):
                headers, rows = self._read_csv(path)
                self.inventory_type = 'CSV'
            elif lower.endswith('.xlsx') or lower.endswith('.xls'):
                headers, rows = self._read_excel(path)
                self.inventory_type = 'Excel'
            else:
                raise ValueError('Formato no soportado. Usa CSV, XLSX o XLS.')

            self.inventory_headers = headers
            self.inventory_rows = len(rows)
            file_name = path.replace('\\', '/').split('/')[-1]
            if hasattr(self, 'catalog_status_label'):
                self.catalog_status_label.setText(f"✅ {file_name} cargado correctamente")
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

    def animate_fade(self):
        animation = QPropertyAnimation(self.fade_effect, b"opacity", self)
        animation.setDuration(240)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

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
        inventory_summary = ", ".join(self.inventory_headers) if self.inventory_headers else "Sin encabezados detectados"
        personality = self.personality_selected if hasattr(self, 'personality_selected') else "Vendedor Quirúrgico"
        return {
            "user": self.user_input.text().strip(),
            "pass": self.pass_input.text().strip(),
            "store_name": self.store_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "business_name": self.store_input.text().strip(),
            "assistant_name": self.assistant_name_input.text().strip() if hasattr(self, 'assistant_name_input') else "",
            "business_data": self.description_input.toPlainText().strip(),
            "bot_role": personality,
            "structured_identity": {
                "name": self.store_input.text().strip(),
                "bio": self.description_input.toPlainText().strip(),
                "style": personality,
            },
            "inventory_path": self.csv_path,
            "inventory_connected": self.inventory_connected,
            "inventory_metadata": {
                "headers": self.inventory_headers,
                "summary": inventory_summary,
            },
            "inventory_rows": self.inventory_rows,
            "type": self.business_type_combo.currentText() if hasattr(self, 'business_type_combo') else personality,
            "start": self.start_time.time().toString("HH:mm") if hasattr(self, 'start_time') else "08:00",
            "end": self.end_time.time().toString("HH:mm") if hasattr(self, 'end_time') else "18:00",
            "proxy": "Auto",
            "prompt": self.custom_training_input.toPlainText().strip() if hasattr(self, 'custom_training_input') else "",
            "security_level": "High",
            "system_prompt_final": self.hidden_prompt,
            "whatsapp_number": self.txt_whatsapp.text().strip() if hasattr(self, 'txt_whatsapp') else "",
            "country": self.config_country,
            "language": self.config_language,
            "currency_symbol": self.txt_currency_symbol.text().strip() if hasattr(self, 'txt_currency_symbol') else "Bs",
            "location": self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else "",
            "website": self.txt_website.text().strip() if hasattr(self, 'txt_website') else "",
            "exchange_rate": self.config_exchange,
            "ubicacion": self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else "",
            "envios": self.txt_envios.text().strip() if hasattr(self, 'txt_envios') else "",
            "bot_mission": self.mission_selected if hasattr(self, 'mission_selected') else "Ventas",
            "payment_methods": [btn.text() for btn in self.payment_buttons if btn.isChecked()] if hasattr(self, 'payment_buttons') else [],
            "payment_methods_text": self.config_payments,
            "info_eventos": self.config_faq,
        }
