import os
import sys
import re
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
from groq import Groq
from core.ai_engine import AIService, ROLE_DNA
from services.database_service import db
from views.dialogs.instagram_dialog import AddAccountDialog


class AIResponseWorker(QThread):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, ai_service, user_text, config, inventory_path, time_context, chat_history=None):
        super().__init__()
        self.ai = ai_service
        self.user_text = user_text
        self.config = config or {}
        self.inventory_path = inventory_path
        self.time_context = time_context
        self.chat_history = chat_history or []

    def run(self):
        try:
            if hasattr(self.ai, 'get_response'):
                inventory_rows = []
                if self.inventory_path and hasattr(self.ai, '_load_inventory_rows'):
                    inventory_rows = self.ai._load_inventory_rows(self.inventory_path)
                respuesta, _ = self.ai.get_response(
                    user_input=self.user_text,
                    config=self.config,
                    inventory_rows=inventory_rows,
                    time_context=self.time_context,
                    custom_training=self.config.get('system_prompt', ''),
                    current_state=self.config.get('current_state', 'CONSULTA'),
                    bot_mission=self.config.get('bot_mission', 'Ventas'),
                    chat_history=self.chat_history,
                )
            else:
                respuesta = self.ai.generate_response(
                    self.user_text,
                    self.config.get('system_prompt', ''),
                    bot_role=self.config.get('bot_role'),
                    business_profile=self.config.get('business_profile'),
                    inventory_path=self.inventory_path,
                    bot_name=self.config.get('bot_name'),
                    whatsapp_contacto=self.config.get('whatsapp_contacto'),
                    time_context=self.time_context,
                    location=self.config.get('location'),
                    website=self.config.get('website'),
                    exchange_rate=self.config.get('exchange_rate'),
                    chat_history=self.chat_history,
                )
            if respuesta is None:
                raise RuntimeError("No se obtuvo respuesta del motor.")
            self.finished.emit(respuesta)
        except Exception as exc:
            self.failed.emit(str(exc))


class LabPreset:
    def __init__(self, name, role, has_inventory, wa_link, bot_name='Pegasus', business_profile='', business_data='', country='Venezuela', language='es', currency_symbol='Bs'):
        self.name = name
        self.role = role
        self.has_inventory = has_inventory
        self.wa_link = wa_link
        self.bot_name = bot_name
        self.business_profile = business_profile
        self.business_data = business_data
        self.country = country
        self.language = language
        self.currency_symbol = currency_symbol
        self.inventory_path = None


LAB_PRESETS = [
    LabPreset(
        name="Vendedor Pro",
        role="VENDEDOR",
        has_inventory=True,
        wa_link="https://wa.me/584121234567",
        bot_name="Pegasus",
        business_profile="Actúa como un vendedor profesional con acceso a catálogo y promociones.",
        business_data="Catálogo actualizado, stock disponible y entregas rápidas en Caracas.",
        country="Venezuela",
        language="es",
        currency_symbol="Bs",
    ),
    LabPreset(
        name="Soporte Vacío",
        role="SOPORTE",
        has_inventory=False,
        wa_link="https://wa.me/584121234567",
        bot_name="Pegasus",
        business_profile="Actúa como soporte técnico, sin inventario disponible y con prioridad en resolver dudas.",
        business_data="Atención clara y profesional, enfócate en la resolución del cliente.",
        country="Venezuela",
        language="es",
        currency_symbol="Bs",
    ),
    LabPreset(
        name="Crisis de Reclamo",
        role="CONCILIADOR",
        has_inventory=False,
        wa_link="https://wa.me/584121234567",
        bot_name="Pegasus",
        business_profile="Actúa con máxima empatía y prioridad. Responde un reclamo serio con calma y ofrece solución inmediata.",
        business_data="Manejo de quejas, cambios y reembolsos. Si la situación lo requiere, deriva rápido a WhatsApp.",
        country="Venezuela",
        language="es",
        currency_symbol="Bs",
    ),
]

MANUAL_ACCOUNTS = [
    {
        'insta_user': 'manual_vendedor',
        'store_name': 'Demo Vendedor',
        'bot_role': 'VENDEDOR',
        'assistant_name': 'Carlos',
        'whatsapp_number': 'https://wa.me/584121234567',
        'business_data': 'Catálogo demo con stock disponible. Enfócate en cerrar ventas y promover ofertas.',
        'context_type': 'Vendedor Quirúrgico',
        'bot_name': 'Carlos',
        'inventory_path': os.path.abspath(os.path.join(ROOT_DIR, 'data', 'manual_vendor_inventory.csv')),
        'business_name': 'Tienda Demo Vendedor',
        'account_type': 'Tienda de ropa',
        'system_prompt': 'Usa este inventario demo para responder con detalle y exactitud en precios y stock.',
    },
    {
        'insta_user': 'manual_soporte',
        'store_name': 'Demo Soporte',
        'bot_role': 'SOPORTE',
        'assistant_name': 'Sofía',
        'whatsapp_number': 'https://wa.me/584121234567',
        'business_data': 'Soporte profesional sin inventario, enfocado en resolver dudas y derivar cuando haya problemas.',
        'context_type': 'Soporte Profesional',
        'bot_name': 'Sofía',
        'inventory_path': '',
        'business_name': 'Tienda Demo Soporte',
        'account_type': 'Consultorio',
        'system_prompt': 'No hay inventario real. Responde con claridad y prioriza la atención al cliente.',
    },
    {
        'insta_user': 'manual_influencer',
        'store_name': 'Demo Influencer',
        'bot_role': 'VENDEDOR',
        'assistant_name': 'Mía',
        'whatsapp_number': 'https://wa.me/584121234567',
        'business_data': 'Promociona productos con energía y cercanía. Crea confianza y destaca ofertas limitadas.',
        'context_type': 'Marca Personal',
        'bot_name': 'Mía',
        'inventory_path': '',
        'business_name': 'Influencer Demo',
        'account_type': 'Perfil de influencer',
        'system_prompt': 'Actúa como una influencer amigable y persuasiva, usando recomendaciones naturales y un tono cercano.',
    },
    {
        'insta_user': 'manual_servicios',
        'store_name': 'Demo Servicios',
        'bot_role': 'SOPORTE',
        'assistant_name': 'Andrés',
        'whatsapp_number': 'https://wa.me/584121234567',
        'business_data': 'Prestador de servicios con enfoque en calidad, tiempos y atención personalizada.',
        'context_type': 'Profesional',
        'bot_name': 'Andrés',
        'inventory_path': '',
        'business_name': 'Servicios Demo',
        'account_type': 'Prestador de servicios',
        'system_prompt': 'Responde como un prestador de servicios confiable. Explica procesos, confianza y cómo agendar citas.',
    },
    {
        'insta_user': 'manual_clinica',
        'store_name': 'Demo Clínica',
        'bot_role': 'SOPORTE',
        'assistant_name': 'Laura',
        'whatsapp_number': 'https://wa.me/584121234567',
        'business_data': 'Asesoría médica y consultas especializadas. Atiende con claridad y recomienda el siguiente paso.',
        'context_type': 'Consultas',
        'bot_name': 'Laura',
        'inventory_path': '',
        'business_name': 'Clínica Demo',
        'account_type': 'Perfil de clínica',
        'system_prompt': 'Asume el rol de asesora experta. Responde las consultas con precisión y guía hacia contacto directo si es necesario.',
    },
]


class PegasusLab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pegasus Lab")
        self.resize(980, 620)
        self.setStyleSheet(
            "QWidget { background-color: #080808; color: #FFFFFF; }"
            "QTextEdit, QLineEdit, QComboBox, QLabel { color: #FFFFFF; }"
            "QTextEdit { background-color: #101010; border: 1px solid #222222; }"
            "QLineEdit { background-color: #111111; border: 1px solid #222222; padding: 8px; }"
            "QPushButton { background-color: #00E5FF; color: #000000; border: none; padding: 10px 16px; border-radius: 10px; }"
            "QPushButton:hover { background-color: #00B3CC; }"
            "QComboBox { background-color: #111111; border: 1px solid #222222; padding: 6px; }"
        )

        self.ai = AIService()
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.ai.current_key = api_key
            self.ai.client = Groq(api_key=api_key)
        else:
            print('[ERROR] No se encontró la GROQ_API_KEY. Asegúrate de configurar tu archivo .env')
            self.ai.current_key = None
            self.ai.client = None
        self.account = None
        self.accounts = []
        self.manual_accounts = MANUAL_ACCOUNTS
        self.current_account_id = None
        self.selected_preset = None
        self.selected_role = None
        self.active_test_profile = None
        self.has_inventory = False
        self.message_buffer = []
        self.chat_history = []
        self.manual_mode = False
        self.last_message_was_image = False
        self.worker = None

        self._build_ui()
        self.cargar_roles()
        self._setup_alert_sound()
        self._refresh_account()

        self.buffer_timer = QTimer(self)
        self.buffer_timer.setInterval(4000)
        self.buffer_timer.setSingleShot(True)
        self.buffer_timer.timeout.connect(self._dispatch_buffer)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { min-width: 140px; padding: 10px; }"
            "QTabWidget::pane { border: 1px solid #222222; top: -1px; }"
        )

        interaction_tab = QWidget()
        interaction_layout = QVBoxLayout(interaction_tab)
        interaction_layout.setSpacing(10)

        label_chat = QLabel("Interacción")
        label_chat.setStyleSheet("font-weight: bold; font-size: 16px;")
        interaction_layout.addWidget(label_chat)

        self.chat_history_widget = QTextEdit()
        self.chat_history_widget.setReadOnly(True)
        self.chat_history_widget.setStyleSheet("font-size: 13px;")
        interaction_layout.addWidget(self.chat_history_widget, stretch=6)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input_message = QLineEdit()
        self.input_message.setPlaceholderText("Escribe tu mensaje aquí...")
        input_row.addWidget(self.input_message, stretch=3)

        self.btn_image = QPushButton("📷 Simular Imagen")
        self.btn_image.clicked.connect(self._on_simulate_image_clicked)
        input_row.addWidget(self.btn_image)

        self.btn_send = QPushButton("Enviar")
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self.btn_send)

        interaction_layout.addLayout(input_row)

        self.data_capture_box = QTextEdit()
        self.data_capture_box.setReadOnly(True)
        self.data_capture_box.setVisible(False)
        self.data_capture_box.setStyleSheet(
            "background-color: #0A2E0A; border: 1px solid #1F5A1F; color: #D4FFDF; padding: 10px;"
        )
        interaction_layout.addWidget(QLabel("Datos Capturados (JSON)"))
        interaction_layout.addWidget(self.data_capture_box, stretch=2)

        self.tabs.addTab(interaction_tab, "Interacción")

        profiles_tab = QWidget()
        profiles_layout = QVBoxLayout(profiles_tab)
        profiles_layout.setSpacing(10)

        label_profiles = QLabel("Perfiles de Prueba")
        label_profiles.setStyleSheet("font-weight: bold; font-size: 16px;")
        profiles_layout.addWidget(label_profiles)

        layout_selectores = QHBoxLayout()
        layout_selectores.setSpacing(12)

        label_cuenta = QLabel("1. Seleccionar Cuenta (Contexto)")
        label_cuenta.setStyleSheet("font-size: 12px; color: #DDDDDD;")
        layout_selectores.addWidget(label_cuenta)

        self.combo_cuentas = QComboBox()
        self.combo_cuentas.currentTextChanged.connect(self.cambiar_perfil)
        self.combo_cuentas.setStyleSheet("color: #FFFFFF; background-color: #111111; border: 1px solid #222222; padding: 6px;")
        layout_selectores.addWidget(self.combo_cuentas, stretch=2)

        self.btn_config_account = QPushButton("⚙️ Editar / Añadir Cuenta")
        self.btn_config_account.setStyleSheet(
            "background-color: #333333; color: white; padding: 5px 15px; border-radius: 4px; font-weight: bold;"
        )
        self.btn_config_account.clicked.connect(self._on_config_account)
        layout_selectores.addWidget(self.btn_config_account)

        label_rol = QLabel("2. Forzar Rol del Bot")
        label_rol.setStyleSheet("font-size: 12px; color: #DDDDDD;")
        layout_selectores.addWidget(label_rol)

        self.combo_roles = QComboBox()
        self.combo_roles.currentTextChanged.connect(self.select_role)
        self.combo_roles.setStyleSheet("color: #FFFFFF; background-color: #111111; border: 1px solid #222222; padding: 6px;")
        layout_selectores.addWidget(self.combo_roles, stretch=1)

        label_mision = QLabel("Misión del Bot")
        label_mision.setStyleSheet("font-size: 12px; color: #DDDDDD;")
        layout_selectores.addWidget(label_mision)

        self.combo_mission = QComboBox()
        self.combo_mission.addItems(["Ventas", "Soporte"])
        self.combo_mission.setStyleSheet("color: #FFFFFF; background-color: #111111; border: 1px solid #222222; padding: 6px;")
        layout_selectores.addWidget(self.combo_mission, stretch=1)

        label_estado = QLabel("Estado del Cliente")
        label_estado.setStyleSheet("font-size: 12px; color: #DDDDDD;")
        layout_selectores.addWidget(label_estado)

        self.combo_state = QComboBox()
        self.combo_state.addItems(["CONSULTA", "ESPERANDO_DATOS", "CERRADO_PENDIENTE_VALIDACION"])
        self.combo_state.setStyleSheet("color: #FFFFFF; background-color: #111111; border: 1px solid #222222; padding: 6px;")
        layout_selectores.addWidget(self.combo_state, stretch=1)

        self.btn_load_profile = QPushButton("Cargar Configuración")
        self.btn_load_profile.clicked.connect(self.aplicar_configuracion_prueba)
        layout_selectores.addWidget(self.btn_load_profile)

        profiles_layout.addLayout(layout_selectores)

        self.btn_vendedor_todo = QPushButton("Vendedor Pro")
        self.btn_vendedor_todo.clicked.connect(self._scenario_vendedor_con_todo)
        profiles_layout.addWidget(self.btn_vendedor_todo)

        self.btn_soporte_vacio = QPushButton("Soporte Vacío")
        self.btn_soporte_vacio.clicked.connect(self._scenario_soporte_vacio)
        profiles_layout.addWidget(self.btn_soporte_vacio)

        self.btn_crisis_reclamo = QPushButton("Crisis de Reclamo")
        self.btn_crisis_reclamo.clicked.connect(self._scenario_crisis_reclamo)
        profiles_layout.addWidget(self.btn_crisis_reclamo)

        profiles_layout.addWidget(QLabel("Escenarios Rápidos"))
        self.btn_interes_caliente = QPushButton("Interés Caliente")
        self.btn_interes_caliente.clicked.connect(self._scenario_interes_caliente)
        profiles_layout.addWidget(self.btn_interes_caliente)

        self.btn_reclamo_roto = QPushButton("Reclamo por Producto Roto")
        self.btn_reclamo_roto.clicked.connect(self._scenario_reclamo_producto_roto)
        profiles_layout.addWidget(self.btn_reclamo_roto)

        self.btn_duda_antiguedad = QPushButton("Duda de Antigüedad")
        self.btn_duda_antiguedad.clicked.connect(self._scenario_duda_antiguedad)
        profiles_layout.addWidget(self.btn_duda_antiguedad)

        profiles_layout.addWidget(QLabel("Identidad de la cuenta"))
        self.profile_identity_label = QLabel("Ninguna identidad seleccionada")
        self.profile_identity_label.setWordWrap(True)
        self.profile_identity_label.setStyleSheet("font-size: 12px; color: #DDDDDD; border: 1px solid #222222; padding: 8px; background-color: #0F0F0F;")
        profiles_layout.addWidget(self.profile_identity_label)

        self.profile_status_label = QLabel("Perfil: Ninguno seleccionado")
        self.profile_status_label.setWordWrap(True)
        self.profile_status_label.setStyleSheet("font-size: 12px; color: #DDDDDD; border: 1px solid #222222; padding: 8px; background-color: #0F0F0F;")
        profiles_layout.addWidget(QLabel("Status de Perfil"))
        profiles_layout.addWidget(self.profile_status_label)

        self.btn_refresh_account = QPushButton("Refrescar cuenta BD")
        self.btn_refresh_account.clicked.connect(self._refresh_account)
        profiles_layout.addWidget(self.btn_refresh_account)

        self.tabs.addTab(profiles_tab, "Perfiles de Prueba")

        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setSpacing(10)

        label_audit = QLabel("Logs y Stress")
        label_audit.setStyleSheet("font-weight: bold; font-size: 16px;")
        logs_layout.addWidget(label_audit)

        self.audit_log = QTextEdit()
        self.audit_log.setReadOnly(True)
        self.audit_log.setStyleSheet("font-size: 12px;")
        logs_layout.addWidget(self.audit_log, stretch=6)

        self.status_label = QLabel("Estado: MODO AUTOMÁTICO")
        self.status_label.setStyleSheet("font-size: 13px; color: #00E5FF;")
        logs_layout.addWidget(self.status_label)

        self.combo_time_context = QComboBox()
        self.combo_time_context.addItems(["CONTINUOUS", "RE_ENCOUNTER", "NEW_SESSION"])
        self.combo_time_context.setCurrentText("CONTINUOUS")
        logs_layout.addWidget(QLabel("Viaje en el tiempo"))
        logs_layout.addWidget(self.combo_time_context)

        self.btn_stress_queue = QPushButton("Stress Queue")
        self.btn_stress_queue.clicked.connect(self._on_stress_queue)
        logs_layout.addWidget(self.btn_stress_queue)

        self.btn_stress_roles = QPushButton("Stress Roles")
        self.btn_stress_roles.clicked.connect(self._on_stress_roles)
        logs_layout.addWidget(self.btn_stress_roles)

        self.tabs.addTab(logs_tab, "Logs y Stress")

        main_layout.addWidget(self.tabs)

    def cargar_roles(self):
        roles = [role if role != 'GENERICO' else 'GENÉRICO' for role in ROLE_DNA.keys()]
        self.combo_roles.clear()
        self.combo_roles.addItems(roles)
        self.combo_roles.setCurrentText(roles[0] if roles else '')
        self.selected_role = self.combo_roles.currentText()

    def cargar_cuentas_db(self):
        self.combo_cuentas.clear()
        try:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT id, insta_user, store_name FROM settings")
                rows = cursor.fetchall()
            for row in rows:
                label = row['insta_user'] or row['store_name'] or f"Cuenta {row['id']}"
                self.combo_cuentas.addItem(label, row['id'])
            self._append_log(f"[LAB] Cargadas {len(rows)} cuentas desde la BD.")
        except Exception as exc:
            self._append_log(f"[LAB] Error al cargar cuentas DB: {exc}")

    def _on_config_account(self):
        dialog = AddAccountDialog(self, account_data=self.account)
        if dialog.exec():
            new_data = dialog.get_data()
            account_id = self.account.get('id') if self.account else None
            if account_id:
                db.save_account(account_id, new_data)
                self._append_log(f"⚙️ [SISTEMA] Cuenta @{new_data.get('insta_user')} actualizada con éxito.")
            else:
                db.save_account(None, new_data)
                self._append_log(f"⚙️ [SISTEMA] Cuenta @{new_data.get('insta_user')} creada con éxito.")

            if hasattr(self, '_load_accounts'):
                self._load_accounts()
            self._refresh_account()

    def aplicar_configuracion_prueba(self):
        account_id = self.combo_cuentas.currentData()
        if account_id is None:
            self._append_log("[LAB] No hay cuenta seleccionada para cargar configuración.")
            return

        forced_role = self.combo_roles.currentText()
        try:
            with db.get_connection() as conn:
                row = conn.execute("SELECT * FROM settings WHERE id = ?", (account_id,)).fetchone()
            if not row:
                self._append_log(f"[LAB] No se encontró la cuenta con id {account_id}.")
                return

            self.active_test_profile = {
                'account_id': account_id,
                'insta_user': row['insta_user'],
                'bot_name': row.get('assistant_name') or row.get('bot_name') or row.get('business_name') or 'Alex',
                'system_prompt': row['system_prompt'] or '',
                'whatsapp_contacto': row.get('whatsapp_number') or row.get('whatsapp_contacto') or '',
                'inventory_path': row['inventory_path'] or None,
                'bot_role': forced_role,
                'business_profile': row.get('business_data') or row.get('description') or row.get('store_name') or '',
            }
            self.selected_role = forced_role
            self.profile_status_label.setText(
                f"Bot Name: {self.active_test_profile['bot_name']}\n"
                f"Rol actual: {forced_role}\n"
                f"WhatsApp: {self.active_test_profile['whatsapp_contacto'] or 'Sin WA'}\n"
                f"Inventario vinculado: {'Sí' if self.active_test_profile['inventory_path'] else 'No'}"
            )
            identity = row.get('context_type') or row.get('store_name') or 'Cuenta DB'
            self.profile_identity_label.setText(f"Identidad: {identity}")
            self._append_log(f"[LAB] Perfil cargado: Cuenta {row['insta_user']} | Rol Forzado: {forced_role}.")
        except Exception as exc:
            self._append_log(f"[LAB] Error aplicando configuración de prueba: {exc}")

    def _setup_alert_sound(self):
        self.alert_sound = None
        self.media_player = None
        self.alert_audio_output = None
        sound_file = os.path.abspath(os.path.join(ROOT_DIR, 'assets', 'sounds', 'alerta_venta.wav'))
        if not os.path.exists(sound_file):
            print(f"[DEBUG SONIDO] Archivo de sonido no existe: {sound_file}")
            self._append_log(f"[SONIDO] No se encontró alerta de venta: {sound_file}")
            return

        self.alert_sound = QSoundEffect(self)
        self.alert_sound.setSource(QUrl.fromLocalFile(sound_file))
        self.alert_sound.setLoopCount(1)
        self.alert_sound.setVolume(0.9)
        self.alert_sound.loadedChanged.connect(
            lambda loaded: self._append_log(
                f"[SONIDO] QSoundEffect loadedChanged={loaded} para {sound_file}"
            )
        )

        if not self.alert_sound.isLoaded():
            print(f"[DEBUG SONIDO] QSoundEffect no pudo cargar el archivo: {sound_file}")
            self._append_log(f"[SONIDO] QSoundEffect no pudo cargar el archivo: {sound_file}")
            self.alert_sound = None
            self._setup_media_player(sound_file)

    def _setup_media_player(self, sound_file):
        self.media_player = QMediaPlayer(self)
        self.alert_audio_output = QAudioOutput(self)
        self.alert_audio_output.setVolume(0.9)
        self.media_player.setAudioOutput(self.alert_audio_output)
        self.media_player.setSource(QUrl.fromLocalFile(sound_file))
        self.media_player.errorOccurred.connect(
            lambda error, error_string: self._append_log(
                f"[SONIDO] QMediaPlayer error={error} message={error_string} para {sound_file}"
            )
        )
        self.media_player.mediaStatusChanged.connect(
            lambda status: self._append_log(f"[SONIDO] QMediaPlayer status={status}")
        )

    def _play_alert_sound(self):
        if self.alert_sound and self.alert_sound.isLoaded():
            self.alert_sound.play()
            return

        if self.media_player:
            self.media_player.stop()
            self.media_player.play()
            return

        self._append_log("[SONIDO] Alerta de venta no está disponible para reproducir.")

    def _start_handoff_timer(self):
        if hasattr(self, '_handoff_timer') and self._handoff_timer.isActive():
            self._handoff_timer.stop()
        self._handoff_timer = QTimer(self)
        self._handoff_timer.setInterval(180000)
        self._handoff_timer.setSingleShot(True)
        self._handoff_timer.timeout.connect(self._on_handoff_timeout)
        self._handoff_timer.start()
        self._append_log("[HANDOFF] Temporizador de 3 minutos iniciado.")

    def _on_handoff_timeout(self):
        self._append_log("[HANDOFF] 3 minutos han pasado. Simulación de espera de humano finalizada.")

    def _apply_preset(self, preset):
        self.selected_preset = preset
        self.account = None
        self.has_inventory = preset.has_inventory
        self.selected_role = preset.role
        if hasattr(self, 'combo_roles'):
            self.combo_roles.blockSignals(True)
            self.combo_roles.setCurrentText(preset.role)
            self.combo_roles.blockSignals(False)
        self.profile_status_label.setText(
            f"Preset: {preset.name}\n"
            f"Rol: {preset.role}\n"
            f"WhatsApp: {preset.wa_link}\n"
            f"Inventario vinculado: {'Sí' if preset.has_inventory else 'No'}\n"
            f"{preset.business_profile}"
        )
        self.profile_identity_label.setText(f"Identidad: Preset de escenario")
        self._append_log(f"[PRESET] Se activó el preset '{preset.name}'.")

    def _clear_preset(self):
        self.selected_preset = None
        self._append_log("[PRESET] Se eliminó el preset activo. Usando cuenta DB si está disponible.")

    def select_role(self, role):
        self.selected_role = role
        if self.account:
            identity = self.account.get('account_type') or self.account.get('store_name') or 'Sin identidad'
            bot_name = self.account.get('assistant_name') or self.account.get('bot_name') or self.account.get('business_name') or 'Alex'
            whatsapp = self.account.get('whatsapp_number') or self.account.get('whatsapp_contacto') or 'Sin WA'
            inventario_text = 'Sí' if self.has_inventory else 'No'
            reglas = self.account.get('business_data') or self.account.get('system_prompt') or 'Sin reglas de negocio definidas.'
            regla_forzada = 'Se forzará PROHIBIDO DAR PRECIOS porque no hay inventario.' if not self.has_inventory else 'Inventario habilitado.'
            self.profile_status_label.setText(
                f"Bot Name: {bot_name}\n"
                f"Rol actual: {self.selected_role}\n"
                f"WhatsApp: {whatsapp}\n"
                f"Inventario vinculado: {inventario_text}\n"
                f"Reglas de negocio: {reglas}\n"
                f"{regla_forzada}"
            )
            self.profile_identity_label.setText(f"Identidad: {identity}")
        self._append_log(f"[ROL] Rol seleccionado: {role}.")

    def _refresh_account(self):
        cuentas = db.obtener_cuentas()
        self.accounts = cuentas or []
        self.combo_cuentas.blockSignals(True)
        self.combo_cuentas.clear()

        self.cargar_cuentas_db()
        if not self.combo_cuentas.count():
            self._append_log("[DB] No se encontró ninguna cuenta activa en BD.")
            self.account = None
            self.profile_status_label.setText("Perfil: Ninguno seleccionado")
            self.combo_cuentas.blockSignals(False)
            return

        self.combo_cuentas.blockSignals(False)
        if self.selected_preset:
            self._append_log(f"[DB] Cuentas recargadas pero se mantiene el preset '{self.selected_preset.name}'.")
            self._apply_preset(self.selected_preset)
        else:
            if self.combo_cuentas.currentIndex() < 0:
                self.combo_cuentas.setCurrentIndex(0)
            selected_username = self.combo_cuentas.currentText()
            self.cambiar_perfil(selected_username)
            if self.account:
                self._append_log(
                    f"[DB] Cuentas cargadas. Cuenta activa: {self.account.get('insta_user') or self.account.get('store_name', 'Sin nombre')}.")

    def cambiar_perfil(self, username):
        if self.selected_preset:
            self._clear_preset()

        if not username or (not self.accounts and not self.manual_accounts):
            self._append_log("[PERFIL] No se puede cambiar de perfil: no hay cuenta seleccionada.")
            self.account = None
            self.profile_status_label.setText("Perfil: Ninguno seleccionado")
            return

        account = next((c for c in self.accounts if (c.get('insta_user') or '').lower() == username.lower()), None)
        if not account:
            account = next((c for c in self.manual_accounts if (c.get('insta_user') or '').lower() == username.lower()), None)
            if account:
                self._append_log(f"[PERFIL] Cuenta manual seleccionada: {username}.")
        if not account:
            self._append_log(f"[PERFIL] No se encontró ninguna cuenta con el usuario {username}.")
            return

        self.account = account
        self.current_account_id = account.get('id') if account in self.accounts else None
        raw_inventory = account.get('inventory_path') or ''
        inventory_path = os.path.abspath(raw_inventory) if raw_inventory else ''
        self.has_inventory = bool(inventory_path and os.path.isfile(inventory_path))

        bot_name = account.get('assistant_name') or account.get('bot_name') or account.get('business_name') or 'Alex'
        bot_role = account.get('bot_role') or account.get('context_type') or 'SIN ROL'
        whatsapp = account.get('whatsapp_number') or account.get('whatsapp_contacto') or 'Sin WA'
        reglas = account.get('business_data') or account.get('system_prompt') or 'Sin reglas de negocio definidas.'
        inventario_text = 'Sí' if self.has_inventory else 'No'
        regla_forzada = 'Se forzará PROHIBIDO DAR PRECIOS porque no hay inventario.' if not self.has_inventory else 'Inventario habilitado.'

        selected_role = self.selected_role or bot_role
        self.profile_status_label.setText(
            f"Bot Name: {bot_name}\n"
            f"Rol actual: {selected_role}\n"
            f"WhatsApp: {whatsapp}\n"
            f"Inventario vinculado: {inventario_text}\n"
            f"Reglas de negocio: {reglas}\n"
            f"{regla_forzada}"
        )
        identity = account.get('account_type') or account.get('store_name') or 'Sin identidad'
        self.profile_identity_label.setText(f"Identidad: {identity}")
        if hasattr(self, 'combo_roles'):
            self.combo_roles.blockSignals(True)
            self.combo_roles.setCurrentText(selected_role)
            self.combo_roles.blockSignals(False)
        self._append_log(f"[PERFIL] Cambiado a {username}. Rol={selected_role}, inventario={inventario_text}.")

    def _append_chat(self, quien, mensaje):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.chat_history_widget.append(f"[{timestamp}] ({quien}) {mensaje}")

    def _append_log(self, mensaje):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.audit_log.append(f"[{timestamp}] {mensaje}")

    def _inject_system_marker(self, marker_text):
        self._append_chat("Sistema", marker_text)
        self._append_log(f"[SIMULACIÓN] Marcador de sistema inyectado: {marker_text}")
        self._enqueue_message(marker_text)

    def _on_simulate_image_clicked(self):
        system_message = "[SISTEMA: El cliente envió una imagen/captura]"
        self._append_chat("Sistema", system_message)
        self._append_log("[SIMULACIÓN] Imagen del cliente inyectada.")
        self.last_message_was_image = True
        self._enqueue_message(system_message)

    def _scenario_interes_caliente(self):
        preset = next((p for p in LAB_PRESETS if p.name == 'Vendedor Pro'), None)
        if preset:
            self._apply_preset(preset)
        self._append_chat("Cliente", "Hola")
        self._enqueue_message("Hola")
        self._inject_system_marker("[SISTEMA: El cliente compartió una publicación RECIENTE]")
        self._dispatch_buffer()

    def _scenario_reclamo_producto_roto(self):
        preset = next((p for p in LAB_PRESETS if p.name == 'Crisis de Reclamo'), None)
        if preset:
            self._apply_preset(preset)
        self._append_chat("Cliente", "El producto llegó dañado y no sirve.")
        self._enqueue_message("El producto llegó dañado y no sirve.")
        self._on_simulate_image_clicked()
        self._dispatch_buffer()

    def _scenario_duda_antiguedad(self):
        preset = next((p for p in LAB_PRESETS if p.name == 'Vendedor Pro'), None)
        if preset:
            self._apply_preset(preset)
        self._append_chat("Cliente", "Vi una publicación antigua y quiero saber si aún está disponible.")
        self._enqueue_message("Vi una publicación antigua y quiero saber si aún está disponible.")
        self._inject_system_marker("[SISTEMA: El cliente compartió una publicación ANTIGUA (+6 meses)]")
        self._dispatch_buffer()

    def _select_account_by_predicate(self, predicate, description):
        account = next((a for a in self.accounts if predicate(a)), None)
        source = 'DB'
        if not account:
            account = next((a for a in self.manual_accounts if predicate(a)), None)
            source = 'MANUAL' if account else 'DB'
        if not account:
            self._append_log(f"[ESCENARIO] No existe cuenta para: {description}")
            return None
        username = account.get('insta_user') or account.get('store_name') or ''
        index = self.combo_cuentas.findText(username)
        if index >= 0:
            self.combo_cuentas.setCurrentIndex(index)
        else:
            self.cambiar_perfil(username)
        self._append_log(f"[ESCENARIO] Cuenta seleccionada desde {source}: {username} para {description}.")
        return account

    def _scenario_vendedor_con_todo(self):
        self._append_log("[ESCENARIO] Buscando vendedor con inventario.")
        self._select_account_by_predicate(
            lambda a: (a.get('bot_role') or a.get('context_type') or '').upper().startswith('VENDEDOR')
                      and a.get('inventory_path')
                      and os.path.isfile(os.path.abspath(a.get('inventory_path'))),
            'Vendedor con todo'
        )

    def _scenario_soporte_vacio(self):
        self._append_log("[ESCENARIO] Buscando soporte sin inventario.")
        account = self._select_account_by_predicate(
            lambda a: (a.get('bot_role') or a.get('context_type') or '').upper().startswith('SOPORTE')
                      and not a.get('inventory_path'),
            'Soporte vacío'
        )
        if account:
            self._append_log("[ESCENARIO] Perfil de soporte seleccionado desde DB.")

    def _scenario_crisis_reclamo(self):
        preset = next((p for p in LAB_PRESETS if p.name == 'Crisis de Reclamo'), None)
        if preset:
            self._apply_preset(preset)
            self.input_message.setText("El producto llegó dañado y no quiero pagar.")
            self._append_log("[ESCENARIO] Crisis de reclamo simulada. Enviando mensaje de queja.")
            self._on_send_clicked()

    def _set_manual_mode(self, enabled):
        self.manual_mode = enabled
        if enabled:
            self.status_label.setText("Estado: MODO MANUAL")
            self.status_label.setStyleSheet("font-size: 13px; color: #FF8C00;")
        else:
            self.status_label.setText("Estado: MODO AUTOMÁTICO")
            self.status_label.setStyleSheet("font-size: 13px; color: #00E5FF;")

    def _on_send_clicked(self):
        texto = self.input_message.text().strip()
        if not texto:
            return
        self.input_message.clear()
        self._enqueue_message(texto)

    def _on_clear_chat(self):
        self.chat_history.append({'role': 'system', 'content': '[El chat ha sido reiniciado por el usuario]'})

    def _enqueue_message(self, texto):
        self.message_buffer.append(texto)
        self.chat_history.append({'role': 'user', 'content': texto})
        self._append_chat("Cliente", texto)
        self._append_log(f"[BUFFER] Añadido: \"{texto}\". Timer reiniciado.")
        self.buffer_timer.stop()
        self.buffer_timer.start()

    def _dispatch_buffer(self):
        if not self.message_buffer:
            return
        bundled = "\n".join(self.message_buffer)
        self.message_buffer = []
        self._append_log(f"[GROQ] Enviando prompt con contexto: {self.combo_time_context.currentText()}.")
        self._send_to_ai(bundled)

    def _send_to_ai(self, bundled_text):
        bot_name = "Alex"
        whatsapp_contacto = ""
        time_context = self.combo_time_context.currentText()
        system_prompt = ''
        bot_role = None
        business_profile = ''
        inventory_path = None

        source = {}
        if self.active_test_profile:
            profile = self.active_test_profile
            bot_name = profile.get('bot_name', 'Alex')
            whatsapp_contacto = profile.get('whatsapp_contacto', '')
            bot_role = profile.get('bot_role')
            business_profile = profile.get('business_profile', '')
            system_prompt = profile.get('system_prompt', '')
            inventory_path = profile.get('inventory_path')
            source = profile
            self._append_log(f"[LAB] Enviando IA con perfil activo: Cuenta {profile.get('insta_user')} | Rol forzado: {bot_role}.")
        elif self.selected_preset:
            preset = self.selected_preset
            bot_name = preset.bot_name
            whatsapp_contacto = preset.wa_link
            bot_role = self.selected_role or preset.role
            business_profile = preset.business_data or preset.business_profile
            system_prompt = preset.business_profile or ''
            self.has_inventory = preset.has_inventory
            inventory_path = preset.inventory_path if preset.has_inventory else None
            source = {
                'country': preset.country,
                'language': preset.language,
                'currency_symbol': preset.currency_symbol,
                'location': None,
                'website': None,
                'exchange_rate': None,
            }
            self._append_log(f"[PRESET] Enviando IA con preset {preset.name}: rol={bot_role}, inventario={self.has_inventory}.")
        else:
            if not self.account:
                self._append_chat("Pegasus", "No hay cuenta configurada en la base de datos ni preset activo.")
                return
            latest = db.get_account_by_id(self.account.get('id')) if self.current_account_id else None
            if latest:
                self.account = latest
                self._append_log("[DB] Se obtuvieron datos más recientes de BD antes de la llamada IA.")

            bot_name = self.account.get('assistant_name') or self.account.get('bot_name') or self.account.get('business_name') or "Alex"
            whatsapp_contacto = self.account.get('whatsapp_number') or self.account.get('whatsapp_contacto') or ""
            bot_role = self.selected_role or self.account.get('bot_role') or self.account.get('context_type')
            business_profile = self.account.get('business_data') or self.account.get('description') or self.account.get('store_name')
            system_prompt = self.account.get('system_prompt') or ''
            inventory_path = self.account.get('inventory_path') if self.has_inventory else None
            source = self.account
            self._append_log(f"[DB] Usando bot_name={bot_name}, whatsapp_contacto={whatsapp_contacto}, inventory_path={inventory_path}, rol={bot_role}.")

        if not self.has_inventory:
            system_prompt = (
                "CRÍTICO: Prohibido dar precios o simulaciones de precio. "
                "Esta cuenta no tiene inventario vinculado. Responde sin mencionar costos ni descuentos.\n" + system_prompt
            )

        config = {
            'country': source.get('country'),
            'language': source.get('language'),
            'currency_symbol': source.get('currency_symbol'),
            'location': source.get('location'),
            'website': source.get('website'),
            'exchange_rate': source.get('exchange_rate'),
            'bot_name': bot_name,
            'whatsapp_contacto': whatsapp_contacto,
            'bot_role': bot_role,
            'business_profile': business_profile,
            'system_prompt': system_prompt,
            'bot_mission': self.combo_mission.currentText() if hasattr(self, 'combo_mission') else 'Ventas',
            'current_state': self.combo_state.currentText() if hasattr(self, 'combo_state') else 'CONSULTA',
        }
        self.worker = AIResponseWorker(
            self.ai,
            bundled_text,
            config,
            inventory_path,
            time_context,
            chat_history=self.chat_history,
        )
        self.worker.finished.connect(self._on_ai_finished)
        self.worker.failed.connect(self._on_ai_failed)
        self.worker.start()

    def _on_ai_finished(self, respuesta):
        lower = respuesta.lower()
        should_trigger_handoff = self.last_message_was_image or "whatsapp" in lower or "wa.me" in lower or "api.whatsapp.com" in lower

        data_match = re.search(r"<DATA>(.*?)</DATA>", respuesta, re.DOTALL | re.IGNORECASE)
        if data_match:
            raw_data = data_match.group(1).strip()
            try:
                parsed = json.loads(raw_data)
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                self.data_capture_box.setPlainText(pretty)
                self.data_capture_box.setVisible(True)
                self._append_log("[DATA] Bloque <DATA> detectado y mostrado en la consola de datos capturados.")

                # --- NUEVA LÓGICA: INYECCIÓN AUTOMÁTICA A FINANZAS ---
                cliente = parsed.get("cliente", "Cliente Desconocido")
                referencia = parsed.get("referencia", "000000")
                banco = parsed.get("banco", "No especificado")

                # Limpiar el monto por si la IA le pone el símbolo $
                try:
                    monto = float(str(parsed.get("monto", 0)).replace('$', '').strip())
                except ValueError:
                    monto = 0.0

                # Solo lo enviamos a Finanzas si tiene referencia válida y monto mayor a 0
                if referencia and str(referencia) not in ["...", ""] and monto > 0:
                    account_id = self.account.get('id') if self.account else 0
                    db.insert_sale(account_id, cliente, str(referencia), banco, monto, "PENDIENTE")
                    self._append_log(f"💰 [SISTEMA] Pago capturado y enviado a Finanzas: {cliente} - {monto}$")
            except Exception as exc:
                self.data_capture_box.setPlainText(f"ERROR JSON: {exc}\n\n{raw_data}")
                self.data_capture_box.setVisible(True)
                self._append_log(f"[DATA] Bloque <DATA> detectado pero JSON inválido: {exc}")
        else:
            self.data_capture_box.clear()
            self.data_capture_box.setVisible(False)

        if should_trigger_handoff:
            self._append_log("[ALERTA] Handoff detectado. Ejecutando modo manual + alerta de imagen/handoff.")
            self._play_alert_sound()
            self._start_handoff_timer()
            self._set_manual_mode(True)
        else:
            self._append_log("[SANITIZER] Respuesta procesada sin activar handoff.")
            if self.manual_mode:
                self._set_manual_mode(False)
        self.last_message_was_image = False

        respuesta_limpia = re.sub(r'<DATA>.*?</DATA>', '', respuesta, flags=re.DOTALL).strip()
        self.chat_history.append({'role': 'assistant', 'content': respuesta_limpia})
        assistant_name = self.account.get('assistant_name', 'Pegasus') if self.account else 'Pegasus'
        self._append_chat(assistant_name, respuesta_limpia)

    def _on_ai_failed(self, error_text):
        self._append_log(f"[GROQ] Error: {error_text}")
        fallback = f"[SIMULACIÓN] {self.account.get('business_name') or 'Pegasus'} responde en modo test." 
        self._append_chat("Pegasus", fallback)

    def _on_stress_queue(self):
        self._append_log("[STRESS] Inyectando 5 mensajes en el buffer con 0.5s de diferencia.")
        for index in range(5):
            QTimer.singleShot(500 * index, lambda idx=index: self._enqueue_message(f"Stress message {idx + 1}"))

    def _on_stress_roles(self):
        if not self.account:
            self._append_log("[STRESS] No hay cuenta BD para cambiar el rol.")
            return
        account_id = self.account.get('id')
        db.update_settings(account_id, {'bot_role': 'SOPORTE'})
        self._refresh_account()
        self._append_log("[STRESS] Rol de la cuenta cambiado a SOPORTE.")
        self._enqueue_message("Tengo una queja sobre la última compra, no estoy satisfecho.")


def main():
    app = QApplication(sys.argv)
    ventana = PegasusLab()
    ventana.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
