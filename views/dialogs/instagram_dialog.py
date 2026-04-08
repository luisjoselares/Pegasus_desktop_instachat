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
    QGraphicsOpacityEffect,
    QFrame,
    QInputDialog,
)
from PyQt6.QtGui import QTransform
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
        self.resize(480, 580)
        self.setMinimumSize(450, 550)
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
        self.digested_context_data = {}
        self.ai_service = AIService()
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #080808;
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
                border-bottom: 2px solid #00E5FF;
            }
            QPushButton#GhostCard {
                background-color: transparent;
                border: 1px solid #333333;
                border-radius: 8px;
                color: #A0A0A0;
                padding: 15px;
                text-align: left;
            }
            QPushButton#GhostCard:hover {
                border-color: #00E5FF;
                color: #FFFFFF;
                background-color: rgba(0, 229, 255, 0.05);
            }
            QPushButton#GhostCard[selected="true"] {
                border: 2px solid #00E5FF;
                color: #FFFFFF;
                font-weight: bold;
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

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(0)

        self.stacked = QStackedWidget()
        self.page1 = QWidget()
        self.page2 = QWidget()
        self.page3 = QWidget()
        self.page4 = QWidget()
        self.page5 = QWidget()
        self.page6 = QWidget()

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

        self.on_page_changed(self.stacked.currentIndex())
        self._create_loading_overlay()
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

        layout.addStretch()

        self.btn_validate = QPushButton(qta.icon('fa5s.check', color='#00E5FF'), "VALIDAR Y CONTINUAR")
        self.btn_validate.setObjectName("PrimaryBtn")
        self.btn_validate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate.clicked.connect(self.validate_credentials)
        layout.addWidget(self.btn_validate)

        if self.is_edit_mode:
            self.btn_validate.setVisible(False)
            self.page1_status.setText("Modo edición: valida no es necesario.")

    def _build_page2(self):
        layout = QVBoxLayout(self.page2)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

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

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Propuesta de valor de tu tienda")
        self.description_input.setMinimumHeight(140)
        layout.addWidget(self.description_input)

        self.page2_status = QLabel("Estos campos alimentarán la personalidad del asistente.")
        self.page2_status.setStyleSheet("color: #a5b1c2;")
        layout.addWidget(self.page2_status)

    def _build_page3(self):
        layout = QVBoxLayout(self.page3)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Personalidad del asistente")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Elige el tono que deseas para las respuestas automáticas.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(12)

        self.personality_buttons = []
        self.personality_selected = "Vendedor Quirúrgico"

        def add_card(name, subtitle):
            card = QPushButton(name)
            card.setCheckable(True)
            card.setObjectName("GhostCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(subtitle)
            card.clicked.connect(lambda checked, key=name: self.select_personality_card(key))
            card.setMinimumHeight(55)
            card.setMaximumWidth(180)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 10, 10, 10)
            card_layout.setSpacing(4)
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("color: #a5b1c2; font-size: 11px;")
            card_layout.addWidget(QLabel(name))
            card_layout.addWidget(subtitle_label)
            self.personality_buttons.append(card)
            cards.addWidget(card)

        add_card("Vendedor Quirúrgico", "Enfocado en ventas")
        add_card("Asistente Creativo", "Cercano y dinámico")
        add_card("Soporte Profesional", "Serio y preciso")

        layout.addLayout(cards)

        self.personality_description = QLabel(
            "Escoge un estilo de comunicación y el asistente ajustará su tono al cliente."
        )
        self.personality_description.setWordWrap(True)
        self.personality_description.setStyleSheet("color: #FFFFFF; background-color: transparent; padding: 12px 0;")
        layout.addWidget(self.personality_description)

        self.page3_status = QLabel("Elige la personalidad que mejor represente tu marca.")
        self.page3_status.setStyleSheet("color: #a5b1c2;")
        layout.addWidget(self.page3_status)

        self.select_personality_card(self.personality_selected)

    def _build_page4(self):
        layout = QVBoxLayout(self.page4)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Operaciones")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Configura el horario de atención y sube tu inventario para respuestas mejores.")
        subtitle.setObjectName("StepSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        self.end_time = QTimeEdit(QTime(20, 0))
        self.end_time.setDisplayFormat("HH:mm")
        self.start_time.timeChanged.connect(self.update_role_logic)
        self.end_time.timeChanged.connect(self.update_role_logic)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        time_row.addWidget(self.start_time)
        time_row.addWidget(QLabel("-"))
        time_row.addWidget(self.end_time)
        layout.addLayout(time_row)

        self.schedule_warning = QLabel("")
        self.schedule_warning.setStyleSheet("color: #26de81; font-size: 12px;")
        layout.addWidget(self.schedule_warning)

        self.btn_upload_catalog = QPushButton("Subir Catálogo (Excel/CSV)")
        self.btn_upload_catalog.setObjectName("PrimaryBtn")
        self.btn_upload_catalog.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload_catalog.clicked.connect(self.browse_inventory_file)
        layout.addWidget(self.btn_upload_catalog)

        self.catalog_status = QLabel("Ningún catálogo cargado todavía.")
        self.catalog_status.setObjectName("CatalogStatus")
        self.catalog_status.setStyleSheet("color: #00E5FF;")
        layout.addWidget(self.catalog_status)

        layout.addWidget(QLabel("Tipo de Negocio"))
        self.business_type_combo = QComboBox()
        self.business_type_combo.addItems(["Retail", "Profesional", "Booking", "Marca Personal", "Corporativo"])
        self.business_type_combo.setCurrentText("Retail")
        self.business_type_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.business_type_combo)

        layout.addWidget(QLabel("Contexto Masticado"))
        self.aspect_frame = QFrame()
        self.aspect_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.aspect_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid #222222; border-radius: 14px;")
        self.aspect_layout = QVBoxLayout(self.aspect_frame)
        self.aspect_layout.setContentsMargins(12, 12, 12, 12)
        self.aspect_layout.setSpacing(10)
        layout.addWidget(self.aspect_frame)

        self.btn_edit_details = QPushButton("Editar Detalles")
        self.btn_edit_details.setObjectName("FlatBtn")
        self.btn_edit_details.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_details.clicked.connect(self._edit_details)
        layout.addWidget(self.btn_edit_details)

        layout.addWidget(QLabel("Instrucciones de Personalidad"))
        self.custom_training_input = QTextEdit()
        self.custom_training_input.setPlaceholderText("Añade aquí instrucciones de estilo, tono o personalidad...")
        self.custom_training_input.setMinimumHeight(120)
        layout.addWidget(self.custom_training_input)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        for chip_text in ["Hablar de 'tú'", "Muy formal", "Usar emojis", "Enfoque en ofertas"]:
            btn = QPushButton(chip_text)
            btn.setObjectName("FlatBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, text=chip_text: self._apply_chip(text))
            chips_row.addWidget(btn)
        layout.addLayout(chips_row)

        self.context_note = QLabel("Pegasus ya ha configurado los protocolos de seguridad y geolocalización de forma automática.")
        self.context_note.setStyleSheet("color: #777777; font-size: 12px;")
        self.context_note.setWordWrap(True)
        layout.addWidget(self.context_note)

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

        title = QLabel("Reglas del Juego.")
        title.setObjectName("StepTitle")
        layout.addWidget(title)

        subtitle = QLabel("Dale a tu asistente la información clave para cerrar ventas.")
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

        self.txt_country_label = QLabel("¿En qué país opera tu negocio?")
        self.txt_country_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_country_label)

        self.txt_country = QLineEdit()
        self.txt_country.setPlaceholderText("Ej: Venezuela")
        layout.addWidget(self.txt_country)

        self.txt_language_label = QLabel("¿Cuál es el idioma principal de atención?")
        self.txt_language_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_language_label)

        self.txt_language = QLineEdit()
        self.txt_language.setPlaceholderText("Ej: es")
        layout.addWidget(self.txt_language)

        self.txt_currency_symbol_label = QLabel("¿Cuál es el símbolo de tu moneda?")
        self.txt_currency_symbol_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_currency_symbol_label)

        self.txt_currency_symbol = QLineEdit()
        self.txt_currency_symbol.setPlaceholderText("Ej: Bs")
        layout.addWidget(self.txt_currency_symbol)

        self.txt_tasa_cambio_label = QLabel("¿Cuál es tu tasa de cambio preferida?")
        self.txt_tasa_cambio_label.setProperty("class", "QuestionLabel")
        layout.addWidget(self.txt_tasa_cambio_label)

        self.txt_tasa_cambio = QLineEdit()
        self.txt_tasa_cambio.setPlaceholderText("Ej: 1 USD = 3.600.000 Bs")
        layout.addWidget(self.txt_tasa_cambio)

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
        self.start_time.setTime(QTime.fromString(account_data.get('schedule_start', '08:00'), 'HH:mm'))
        self.end_time.setTime(QTime.fromString(account_data.get('schedule_end', '18:00'), 'HH:mm'))
        self.hidden_prompt = account_data.get('system_prompt', '')
        self.csv_path = os.path.abspath(account_data.get('inventory_path', '')) if account_data.get('inventory_path') else ''
        self.inventory_connected = bool(self.csv_path)
        if self.inventory_connected:
            self.catalog_status.setText(f"✅ {self.csv_path}")
            self.inventory_headers = account_data.get('inventory_metadata', {}).get('headers', [])
            self.inventory_rows = account_data.get('inventory_rows', 0)
        if hasattr(self, 'txt_whatsapp'):
            self.txt_whatsapp.setText(account_data.get('whatsapp_number', ''))
        if hasattr(self, 'txt_ubicacion'):
            self.txt_ubicacion.setText(account_data.get('location', account_data.get('ubicacion', '')))
        if hasattr(self, 'txt_website'):
            self.txt_website.setText(account_data.get('website', ''))
        if hasattr(self, 'txt_country'):
            self.txt_country.setText(account_data.get('country', 'Venezuela'))
        if hasattr(self, 'txt_language'):
            self.txt_language.setText(account_data.get('language', 'es'))
        if hasattr(self, 'txt_currency_symbol'):
            self.txt_currency_symbol.setText(account_data.get('currency_symbol', 'Bs'))
        if hasattr(self, 'txt_tasa_cambio'):
            self.txt_tasa_cambio.setText(account_data.get('exchange_rate', ''))
        if hasattr(self, 'txt_envios'):
            self.txt_envios.setText(account_data.get('envios', ''))
        if hasattr(self, 'payment_buttons'):
            selected_payments = set(account_data.get('payment_methods', []))
            for btn in self.payment_buttons:
                btn.setChecked(btn.text() in selected_payments)
        if hasattr(self, 'business_type_combo'):
            business_type = account_data.get('type') or account_data.get('context_type')
            if business_type and self.business_type_combo.findText(business_type) >= 0:
                self.business_type_combo.setCurrentText(business_type)
            elif business_type:
                normalized = business_type.strip().lower()
                if 'retail' in normalized or 'vendedor' in normalized:
                    self.business_type_combo.setCurrentText('Retail')
                elif 'profesional' in normalized or 'soporte' in normalized:
                    self.business_type_combo.setCurrentText('Profesional')
                elif 'booking' in normalized or 'cita' in normalized:
                    self.business_type_combo.setCurrentText('Booking')
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
            self.catalog_status.setText(f"✅ {file_name} cargado correctamente")
            self.page3_status.setText("Catálogo listo. Puedes continuar.")
            self.inventory_connected = True
            self.footer_next.setEnabled(True)
        except Exception as e:
            self.inventory_connected = False
            self.inventory_headers = []
            self.inventory_rows = 0
            self.catalog_status.setText(f"Error al analizar el archivo: {e}")
            self.page3_status.setText("No se pudo cargar el catálogo. Intenta con otro archivo.")
            self.footer_next.setEnabled(False)

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
        self.catalog_status.setText("Continuar sin catálogo. El bot usará solo el contexto de la tienda.")
        self.page3_status.setText("Has decidido continuar sin catálogo.")
        self.footer_next.setEnabled(True)

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

    def select_personality_card(self, name):
        self.personality_selected = name
        for card in self.personality_buttons:
            card.setChecked(card.text().startswith(name))
            card.setProperty("selected", card.text().startswith(name))
            card.style().unpolish(card)
            card.style().polish(card)
        self.update_role_logic()

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
            "country": self.txt_country.text().strip() if hasattr(self, 'txt_country') else "Venezuela",
            "language": self.txt_language.text().strip() if hasattr(self, 'txt_language') else "es",
            "currency_symbol": self.txt_currency_symbol.text().strip() if hasattr(self, 'txt_currency_symbol') else "Bs",
            "location": self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else "",
            "website": self.txt_website.text().strip() if hasattr(self, 'txt_website') else "",
            "exchange_rate": self.txt_tasa_cambio.text().strip() if hasattr(self, 'txt_tasa_cambio') else "",
            "ubicacion": self.txt_ubicacion.text().strip() if hasattr(self, 'txt_ubicacion') else "",
            "envios": self.txt_envios.text().strip() if hasattr(self, 'txt_envios') else "",
            "payment_methods": [btn.text() for btn in self.payment_buttons if btn.isChecked()] if hasattr(self, 'payment_buttons') else [],
        }
