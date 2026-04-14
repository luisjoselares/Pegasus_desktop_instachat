import qtawesome as qta
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame, 
                             QLabel, QScrollArea, QHBoxLayout, QMessageBox, QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QTime
from services.database_service import LocalDBService
# Importamos los diálogos desde la nueva subcarpeta
from views.dialogs.instagram_dialog import AddAccountDialog
from views.dialogs.conversation_dialog import ConversationDialog
from views.dialogs.alerts_dialog import AlertsDialog

class ClickableFrame(QFrame):
    def __init__(self, callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback

    def mousePressEvent(self, event):
        if self.callback:
            self.callback(event)
        super().mousePressEvent(event)


class AccountCard(QFrame):
    request_force_activate = pyqtSignal(object)
    request_edit_account = pyqtSignal(object)

    def __init__(self, data, controller):
        super().__init__()
        self.account_id = data.get('id')
        self.controller = controller
        self.db = LocalDBService()
        self.account_id = data.get('id')
        self.alert_count = self.db.get_alert_count(account_id=self.account_id)
        self.is_expanded = False
        self.setObjectName("ModernAccountCard")

        self.account_state = self._resolve_account_state(data)
        self.current_state = self.account_state == 'active'
        self.pause_until = self._get_pause_until(data)
        self.setProperty("accountState", self.account_state)
        self.setStyleSheet(
            "QFrame#ModernAccountCard {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0B0B0B, stop:1 #141A1F);"
            "border: 1px solid #1E2A35;"
            "border-radius: 18px;"
            "padding: 1px;"
            "}"
            "QFrame#ModernAccountCard:hover {"
            "border-color: #00E5FF;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0F1116, stop:1 #16212C);"
            "}"
            "QFrame#CardHeader {"
            "background: rgba(255,255,255,0.03);"
            "border-radius: 14px;"
            "}"
        )
        self.style().unpolish(self)
        self.style().polish(self)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        self.current_state = data.get('bot_enabled') == 1
        self.prompt_is_critical = self._prompt_has_critical_phase(data.get('system_prompt', ''))

        # --- CABECERA DE TARJETA ---
        self.header_frame = ClickableFrame(callback=self.toggle_details)
        self.header_frame.setObjectName("CardHeader")
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_frame.setStyleSheet("background: transparent;")

        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.avatar = QLabel()
        self.avatar.setFixedSize(40, 40)
        self.avatar.setPixmap(qta.icon('fa5s.user-circle', color='#00E5FF').pixmap(24, 24))
        self.avatar.setStyleSheet("background: #141414; border-radius: 20px;")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.avatar)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.lbl_name = QLabel(data.get('store_name', data.get('insta_user', 'Usuario')))
        self.lbl_name.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 800;")
        self.lbl_username = QLabel(f"@{data.get('insta_user', 'desconocido')}")
        self.lbl_username.setStyleSheet("color: #888888; font-size: 11px;")
        title_layout.addWidget(self.lbl_name)
        title_layout.addWidget(self.lbl_username)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        state_colors = {
            'active': ('fa5s.check-circle', '#3CE823'),
            'paused': ('fa5s.bell-slash', '#FFA500'),
            'inactive': ('fa5s.pause-circle', '#888888')
        }
        state_icon_name, state_color = state_colors.get(self.account_state, ('fa5s.check-circle', '#3CE823'))
        self.state_badge = QLabel(f" {data.get('context_type', 'Vendedor de tienda')} ")
        self.state_badge.setStyleSheet(
            f"background-color: #1A1A1A; color: {state_color}; border: 1px solid #222; border-radius: 12px; padding: 6px 10px;"
        )
        badge_icon = QLabel()
        badge_icon.setPixmap(qta.icon(state_icon_name, color=state_color).pixmap(14, 14))
        badge_icon.setStyleSheet("margin-right: 6px;")
        badge_layout = QHBoxLayout()
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(6)
        badge_layout.addWidget(badge_icon)
        badge_layout.addWidget(self.state_badge)
        badge_container = QFrame()
        badge_container.setLayout(badge_layout)
        badge_container.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(badge_container)

        self.status_led = QLabel("●")
        self.status_led.setObjectName("AccountStatusLed")
        self.status_led.setProperty("status", self.account_state)
        self.status_led.setStyleSheet("font-size: 16px; margin-right: 8px;")
        header_layout.addWidget(self.status_led)

        self.status_label = QLabel(self._get_state_label())
        self.status_label.setStyleSheet("color: #CCCCCC; font-size: 11px; font-weight: 700;")
        header_layout.addWidget(self.status_label)

        self.alert_badge = QLabel(str(self.alert_count) if self.alert_count else "")
        self.alert_badge.setFixedSize(QSize(24, 24))
        self.alert_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alert_badge.setStyleSheet(
            "background-color: #FF4C4C; color: #FFFFFF; border-radius: 12px; font-size: 11px; font-weight: 700;"
        )
        self.alert_badge.setToolTip(
            f"{self.alert_count} alerta(s) activa(s)" if self.alert_count else "Sin alertas"
        )
        self.alert_badge.setVisible(self.alert_count > 0)
        header_layout.addWidget(self.alert_badge)

        self.pause_timer_label = QLabel()
        self.pause_timer_label.setObjectName("AccountPauseInfo")
        self.pause_timer_label.setStyleSheet("color: #FFA500; font-size: 10px; margin-left: 8px;")
        self.pause_timer_label.setVisible(self.account_state == 'paused')
        header_layout.addWidget(self.pause_timer_label)

        if self.account_state == 'paused':
            self._refresh_pause_timer()

        self.btn_force_activate = QPushButton(qta.icon('fa5s.bolt', color='#00E5FF'), "")
        self.btn_force_activate.setObjectName("ForceActivateBtn")
        self.btn_force_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_force_activate.setFixedSize(QSize(32, 32))
        self.btn_force_activate.setToolTip("Forzar activación")
        self.btn_force_activate.setVisible(self.account_state == 'paused')
        self.btn_force_activate.clicked.connect(self._on_force_activate_clicked)
        header_layout.addWidget(self.btn_force_activate)

        self.btn_edit = QPushButton(qta.icon('fa5s.cog', color='#CCCCCC'), "")
        self.btn_edit.setObjectName("EditAccountBtn")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setFixedSize(QSize(32, 32))
        self.btn_edit.setToolTip("Editar configuración de la cuenta")
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        header_layout.addWidget(self.btn_edit)

        self.btn_alerts = QPushButton(qta.icon('fa5s.exclamation-triangle', color='#FFCC00'), "")
        self.btn_alerts.setObjectName("AlertsBtn")
        self.btn_alerts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_alerts.setFixedSize(QSize(32, 32))
        self.btn_alerts.setToolTip("Ver alertas de esta cuenta")
        self.btn_alerts.clicked.connect(self._on_alerts_clicked)
        header_layout.addWidget(self.btn_alerts)

        self.btn_toggle = QPushButton(qta.icon('fa5s.power-off', color='#FFFFFF'), "")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedSize(QSize(36, 36))
        self.btn_toggle.setStyleSheet(
            "QPushButton { background-color: #141414; border: 1px solid #222; border-radius: 12px; color: #FFFFFF; }"
            "QPushButton:hover { background-color: #1F1F1F; }"
        )
        self.btn_toggle.clicked.connect(self.toggle_bot)
        header_layout.addWidget(self.btn_toggle)

        self.main_layout.addWidget(self.header_frame)

        self.lbl_log = QLabel(data.get('last_log', 'Sistema listo.'))
        self.lbl_log.setStyleSheet("color: #00FFCC; font-size: 11px; margin-left: 6px;")
        self.main_layout.addWidget(self.lbl_log)

        self.details_frame = QFrame()
        self.details_frame.setVisible(False)
        self.details_frame.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(255,255,255,0.02), stop:1 rgba(255,255,255,0.04));"
            "border: 1px solid rgba(255,255,255,0.05);"
            "border-radius: 16px;"
        )
        self.details_layout = QVBoxLayout(self.details_frame)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(14)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        stats_layout.addWidget(self._build_stat_card('fa5s.comment-dots', '#00E5FF', 'Atendidos Hoy', '0'))
        stats_layout.addWidget(self._build_stat_card('fa5s.broom', '#FF8A00', 'Ignorados (+24h)', '0'))
        stats_layout.addWidget(self._build_stat_card('fa5s.comments', '#00E5FF', 'Chats detectados', str(data.get('active_chat_count', 0))))
        stats_layout.addWidget(self._build_stat_card('fa5s.clock', '#FFFFFF', 'Siguiente cambio', data.get('next_chat_avg', 'N/A')))
        self.details_layout.addLayout(stats_layout)

        self.task_label = QLabel(data.get('current_task', 'Esperando actividad...'))
        self.task_label.setWordWrap(True)
        self.task_label.setStyleSheet("color: #88DDFF; font-size: 11px; margin-top: 4px;")
        self.details_layout.addWidget(self._build_section_title('Estado Actual'))
        self.details_layout.addWidget(self.task_label)

        self.details_layout.addWidget(self._build_section_title('Conversaciones Recientes'))

        self.conversation_scroll = QScrollArea()
        self.conversation_scroll.setWidgetResizable(True)
        self.conversation_scroll.setStyleSheet("background: transparent; border: none;")
        self.conversation_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.conversation_container = QWidget()
        self.conversation_container.setStyleSheet("background: transparent;")
        self.conversation_layout = QVBoxLayout(self.conversation_container)
        self.conversation_layout.setContentsMargins(0, 0, 0, 0)
        self.conversation_layout.setSpacing(10)

        conversations = data.get('conversations', [])
        if conversations:
            for conv in conversations:
                self._build_conversation_row(conv)
        else:
            empty_label = QLabel("No hay conversaciones activas en este momento.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #AAA; font-size: 12px; padding: 20px;")
            self.conversation_layout.addWidget(empty_label)

        self.conversation_layout.addStretch()
        self.conversation_scroll.setWidget(self.conversation_container)
        self.details_layout.addWidget(self.conversation_scroll)

        self.btn_delete = QPushButton(qta.icon('fa5s.trash-alt', color='#FF3366'), " DESVINCULAR CUENTA")
        self.btn_delete.setObjectName("DeleteBtn")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #141414; border: 1px solid #222; border-radius: 10px; color: #FF3366; padding: 10px; }"
            "QPushButton:hover { background-color: #1F1F1F; }"
        )
        self.btn_delete.clicked.connect(self.delete_account)
        self.details_layout.addWidget(self.btn_delete)

        self.main_layout.addWidget(self.details_frame)

    def toggle_details(self, event=None):
        self.is_expanded = not self.is_expanded
        self.details_frame.setVisible(self.is_expanded)
        self.setProperty("expanded", self.is_expanded)
        self.style().unpolish(self)
        self.style().polish(self)

    def _resolve_account_state(self, data):
        if data.get('bot_enabled') != 1:
            return 'inactive'

        if data.get('pause_active') or data.get('status') in ('PAUSED', 'MANUAL'):
            return 'paused'

        paused_until = self._get_pause_until(data)
        if paused_until and paused_until > datetime.now():
            return 'paused'

        return 'active'

    def _get_pause_until(self, data):
        paused_until = data.get('paused_until') or data.get('pausedUntil') or data.get('pause_until')
        if not paused_until:
            return None
        try:
            return datetime.fromisoformat(paused_until)
        except Exception:
            return None

    def _get_state_label(self):
        return {
            'active': 'ACTIVO',
            'paused': 'SILENCIADO',
            'inactive': 'INACTIVO'
        }.get(self.account_state, 'ACTIVO')

    def _get_pause_remaining_text(self):
        if not self.pause_until:
            return "Reactivación pendiente"
        remaining = self.pause_until - datetime.now()
        if remaining.total_seconds() <= 0:
            return "Reactivación disponible"
        minutes = int(remaining.total_seconds() // 60)
        hours = minutes // 60
        minutes = minutes % 60
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")
        return "Reactivación en " + " ".join(parts)

    def _refresh_pause_timer(self):
        if self.account_state != 'paused':
            self.pause_timer_label.setVisible(False)
            return
        self.pause_timer_label.setText(self._get_pause_remaining_text())
        self.pause_timer_label.setVisible(True)
        if self.pause_until and self.pause_until > datetime.now():
            QTimer.singleShot(60000, self._refresh_pause_timer)

    def _on_force_activate_clicked(self):
        self.request_force_activate.emit(self.account_id)

    def _on_edit_clicked(self):
        self.request_edit_account.emit(self.account_id)

    def _build_stat_card(self, icon_name, color, title, value):
        card = QFrame()
        card.setStyleSheet(
            "background-color: #161616; border: 1px solid #222; border-radius: 8px;"
        )
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
        card_layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        label = QLabel(title)
        label.setStyleSheet("color: #BBBBBB; font-size: 10px; font-weight: 700;")
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800;")

        text_layout.addWidget(label)
        text_layout.addWidget(value_label)
        card_layout.addLayout(text_layout)

        return card

    def _build_section_title(self, text):
        title = QLabel(text)
        title.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: 800;")
        return title

    def _build_conversation_row(self, conversation):
        row = QFrame()
        row.setObjectName("ConversationRow")
        row.setStyleSheet(
            "QFrame#ConversationRow {"
            "background-color: #111419;"
            "border: 1px solid #1F2933;"
            "border-radius: 12px;"
            "}"
            "QFrame#ConversationRow:hover {"
            "border-color: #00E5FF;"
            "background-color: #151B21;"
            "}"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 12, 12, 12)
        row_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.user', color='#00E5FF').pixmap(16, 16))
        row_layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        name = QLabel(conversation.get('title', conversation.get('username', 'Cliente')))
        name.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        info_layout.addWidget(name)

        thread_id = conversation.get('thread_id', '')
        truncated_thread = thread_id[:12] + '...' if thread_id and len(thread_id) > 15 else thread_id
        subtitle = QLabel(f"{truncated_thread} • {conversation.get('last_message', '')}")
        subtitle.setStyleSheet("color: #888888; font-size: 10px;")
        subtitle.setWordWrap(True)
        info_layout.addWidget(subtitle)

        row_layout.addLayout(info_layout)
        row_layout.addStretch()

        status_text = "🤖 Gestionado por IA"
        status_color = "#CCCCCC"
        if conversation.get('status') == 'Manual':
            status_text = "✋ Manual"
            status_color = "#FFA500"

        status = QLabel(status_text)
        status.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        row_layout.addWidget(status)

        btn_open = QPushButton(qta.icon('fa5s.eye', color='#00E5FF'), "")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedSize(QSize(32, 32))
        btn_open.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #00E5FF; }"
            "QPushButton:hover { background-color: rgba(0, 228, 255, 0.12); border-radius: 6px; }"
        )
        btn_open.clicked.connect(lambda _, conv=conversation: self.open_conversation(conv))
        row_layout.addWidget(btn_open)

        thread_id = conversation.get('thread_id')
        btn_manual = QPushButton(qta.icon('fa5s.hand-paper', color='#CCCCCC'), "")
        btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manual.setFixedSize(QSize(32, 32))
        btn_manual.setToolTip("Pausar bot para este cliente")
        btn_manual.setProperty("manual", False)
        btn_manual.setProperty("muted_at", None)
        btn_manual.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #CCCCCC; }"
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); border-radius: 6px; }"
        )
        btn_manual.clicked.connect(lambda _, tid=thread_id, btn=btn_manual, lbl=status: self.toggle_manual_control(tid, btn, lbl))
        row_layout.addWidget(btn_manual)

        self.conversation_layout.addWidget(row)

    def open_conversation(self, conversation):
        history = []
        if hasattr(self.controller, 'get_conversation_history'):
            history = self.controller.get_conversation_history(conversation.get('thread_id'))
        dialog = ConversationDialog(self, title=conversation.get('title', 'Conversación'), history=history)
        dialog.exec()

    def toggle_manual_control(self, thread_id, toggle_btn, status_label):
        if not thread_id:
            return

        is_manual = bool(toggle_btn.property("manual"))
        if is_manual:
            self.controller.toggle_manual_thread(thread_id, enable=False)
            toggle_btn.setIcon(qta.icon('fa5s.hand-paper', color='#CCCCCC'))
            toggle_btn.setToolTip("Pausar bot para este cliente")
            toggle_btn.setProperty("manual", False)
            toggle_btn.setProperty("muted_at", None)
            status_label.setText("🤖 Gestionado por IA")
            status_label.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        else:
            self.controller.toggle_manual_thread(thread_id, enable=True)
            toggle_btn.setIcon(qta.icon('fa5s.play', color='#00E5FF'))
            toggle_btn.setToolTip("Reactivar bot")
            toggle_btn.setProperty("manual", True)
            muted_at = datetime.now().isoformat(sep=' ')
            toggle_btn.setProperty("muted_at", muted_at)
            status_label.setText(
                "✋ Modo Manual " \
                "(<span style=\"color:#BBBBBB; font-size:10px;\">Auto-reactivación en 12h</span>)"
            )
            status_label.setStyleSheet("color: #FFA500; font-size: 11px;")

    def delete_account(self):
        confirm = QMessageBox.question(
            self,
            "Confirmar desincronización",
            "¿Estás seguro de que deseas desincronizar esta cuenta de Instagram?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.controller.delete_account(self.account_id)

    def _on_alerts_clicked(self):
        dialog = AlertsDialog(self, account_id=self.account_id, account_name=self.lbl_name.text())
        dialog.exec()
        self.refresh_alert_badge()

    def refresh_alert_badge(self):
        self.alert_count = self.db.get_alert_count(account_id=self.account_id)
        self.alert_badge.setText(str(self.alert_count) if self.alert_count else "")
        self.alert_badge.setVisible(self.alert_count > 0)
        self.alert_badge.setToolTip(
            f"{self.alert_count} alerta(s) activa(s)" if self.alert_count else "Sin alertas"
        )

    def _prompt_has_critical_phase(self, prompt):
        return "consultar con mi supervisor" in prompt.lower()

    def update_status_ui(self):
        status_color = "#00FFCC" if self.current_state else "#FF3366"
        self.status_led.setStyleSheet(f"color: {status_color}; font-size: 18px; border: none;")
        self.status_label.setText("ENCENDIDO" if self.current_state else "APAGADO")
        self.btn_toggle.setText("APAGAR" if self.current_state else "ENCENDER")
        self.btn_toggle.setStyleSheet(
            "QPushButton { background-color: #222; color: #FFFFFF; border-radius: 6px; padding: 6px; }"
            "QPushButton:hover { background-color: #333; }"
        )
        if self.prompt_is_critical:
            self.setStyleSheet("border: 2px solid #FFB300; background-color: #0F0F12;")
            self.lbl_log.setStyleSheet("color: #FFB300;")
        elif "manual" in self.lbl_log.text().lower() or "modo manual" in self.lbl_log.text().lower():
            self.setStyleSheet("border: 2px solid #FF8A00; background-color: #0F0F12;")
            self.lbl_log.setStyleSheet("color: #FF8A00;")
        else:
            self.setStyleSheet("")

    def toggle_bot(self):
        desired_state = not self.current_state
        if desired_state and self.prompt_is_critical:
            self.controller.toggle_bot(self.account_id, False)
            self.current_state = False
            self.lbl_log.setText("› Alerta crítica en el prompt. El bot se mantiene apagado automáticamente.")
            self.update_status_ui()
            self.controller.refresh()
            return

        self.controller.toggle_bot(self.account_id, desired_state)
        self.current_state = desired_state
        self.update_status_ui()
        self.refresh_alert_badge()
        self.controller.refresh()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

class InstagramAccountsPage(QWidget):
    def __init__(self, controller, main_window=None):
        super().__init__()
        self.controller = controller
        self.main_window = main_window
        self.last_edit_unlock = None
        self.edit_grace_period = timedelta(minutes=5)
        self.setObjectName("InstagramAccountsPage")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(35, 35, 35, 35)

        # Cabecera de Página (Alto Contraste)
        header_layout = QHBoxLayout()
        self.lbl_page_title = QLabel("Cuentas de Instagram")
        self.lbl_page_title.setObjectName("PageTitle")
        
        self.btn_add = QPushButton(qta.icon('fa5s.plus', color='black'), " NUEVA CUENTA")
        self.btn_add.setObjectName("AddButtonModern")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.open_add_dialog)

        self.btn_view_all_alerts = QPushButton(qta.icon('fa5s.bell', color='#FFCC00'), " VER ALERTAS")
        self.btn_view_all_alerts.setObjectName("ViewAlertsBtn")
        self.btn_view_all_alerts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_all_alerts.setFixedHeight(40)
        self.btn_view_all_alerts.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; border: 1px solid #444; border-radius: 10px; color: #FFCC00; padding: 8px 14px; }"
            "QPushButton:hover { background-color: #222; }"
        )
        self.btn_view_all_alerts.clicked.connect(self.open_global_alerts_dialog)
        
        header_layout.addWidget(self.lbl_page_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_view_all_alerts)
        header_layout.addWidget(self.btn_add)
        self.main_layout.addLayout(header_layout)

        self.alert_summary_label = QLabel("")
        self.alert_summary_label.setStyleSheet(
            "color: #FFCC00; font-size: 12px; font-weight: 700; margin-bottom: 12px;"
        )
        self.alert_summary_label.setVisible(False)
        self.main_layout.addWidget(self.alert_summary_label)

        self.admin_status_label = QLabel("")
        self.admin_status_label.setStyleSheet("color: #00E5FF; font-size: 11px; margin-bottom: 8px;")
        self.admin_status_label.setVisible(False)
        self.main_layout.addWidget(self.admin_status_label)

        self.admin_status_timer = QTimer(self)
        self.admin_status_timer.setInterval(30000)
        self.admin_status_timer.timeout.connect(self.update_admin_status_label)
        self.admin_status_timer.start()
        self.update_admin_status_label()

        # Línea de acento Pegasus (Cian)
        accent_line = QFrame()
        accent_line.setFrameShape(QFrame.Shape.HLine)
        accent_line.setStyleSheet("background-color: #00E5FF; max-height: 2px; border: none; margin-bottom: 25px;")
        self.main_layout.addWidget(accent_line)

        # Contenedor de Scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(15)
        self.scroll_content.setLayout(self.cards_layout)
        
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

        if hasattr(self.controller, 'handoff_alert'):
            self.controller.handoff_alert.connect(self._on_alert_event)
        if hasattr(self.controller, 'signal_handoff_alert'):
            self.controller.signal_handoff_alert.connect(self._on_alert_event)
        if hasattr(self.controller, 'security_alert'):
            self.controller.security_alert.connect(self._on_alert_event)

    def _on_alert_event(self, *args):
        # Si el motor dispara una alerta/handoff, recargamos las tarjetas y la vista de alertas.
        self.controller.refresh(self.controller.cliente_id)
        self.update_alert_summary()

    def open_global_alerts_dialog(self):
        dialog = AlertsDialog(self, account_id=None, account_name=None)
        dialog.exec()

    def update_alert_summary(self):
        if not self.controller or not hasattr(self.controller, 'db'):
            return

        alert_count = self.controller.db.get_alert_count(cliente_id=self.controller.cliente_id)
        if alert_count:
            recent_alerts = self.controller.db.get_recent_alerts(cliente_id=self.controller.cliente_id, limit=1)
            latest = recent_alerts[0] if recent_alerts else None
            latest_text = ""
            if latest:
                latest_text = f" Última: {latest.get('alert_type', 'ALERTA')} @{latest.get('username', '')} ({latest.get('status', 'N/A')})."
            stats = self.controller.db.get_alert_stats(cliente_id=self.controller.cliente_id)
            failed = stats.get('FAILED', 0)
            pending = stats.get('PENDING', 0)
            summary_suffix = f" {failed} fallida(s)." if failed else ""
            self.alert_summary_label.setText(
                f"🔔 {alert_count} alerta(s) de seguridad registrada(s)." + latest_text + summary_suffix
            )
            self.alert_summary_label.setVisible(True)
            if hasattr(self, 'btn_view_all_alerts'):
                self.btn_view_all_alerts.setText(f"VER ALERTAS ({alert_count})")
        else:
            self.alert_summary_label.setVisible(False)
            if hasattr(self, 'btn_view_all_alerts'):
                self.btn_view_all_alerts.setText("VER ALERTAS")

    def _account_limit_reached(self):
        accounts = self.controller.db.obtener_cuentas(self.controller.cliente_id)
        return len(accounts) >= 1

    def open_add_dialog(self):
        if self._account_limit_reached():
            QMessageBox.warning(
                self,
                "Límite de cuentas",
                "Solo se permite registrar una cuenta de Instagram desde esta vista."
            )
            return

        dialog = AddAccountDialog(self)
        if dialog.exec() == AddAccountDialog.DialogCode.Accepted:
            self.controller.add_account(dialog.get_data())

    def on_card_force_activate(self, account_id):
        if hasattr(self.controller, 'force_activate_account'):
            restored = self.controller.force_activate_account(account_id)
            if restored:
                QMessageBox.information(
                    self,
                    "Activación Forzada",
                    f"Se reactivaron {restored} hilo(s) para la cuenta."
                )
                self.controller.refresh(self.controller.cliente_id)
        else:
            QMessageBox.warning(self, "Función no disponible", "No se puede forzar activación en este momento.")

    def on_card_edit_account(self, account_id):
        if not self._verify_admin_access():
            return
        self.open_edit_dialog(account_id)
        self.update_admin_status_label()

    def _is_edit_grace_active(self):
        if not self.last_edit_unlock:
            return False
        return (datetime.now() - self.last_edit_unlock) < self.edit_grace_period

    def _verify_admin_access(self):
        if self._is_edit_grace_active():
            return True

        expected_password = ''
        if self.main_window and getattr(self.main_window, 'cliente_data', None):
            expected_password = self.main_window.cliente_data.get('password', '')

        if not expected_password:
            QMessageBox.warning(self, 'Acceso restringido', 'No hay una contraseña de sesión válida configurada.')
            return False

        password, ok = QInputDialog.getText(
            self,
            'Verificación Administrativa',
            'Ingresa la contraseña de Pegasus:',
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return False

        verified = False
        if self.main_window and getattr(self.main_window, 'security_service', None):
            verified = self.main_window.security_service.verify_password(password, expected_password)
        else:
            verified = password == expected_password

        if verified:
            self.last_edit_unlock = datetime.now()
            return True

        QMessageBox.critical(self, 'Acceso Denegado', 'La contraseña ingresada es incorrecta.')
        if self.main_window and hasattr(self.main_window, 'append_log_message'):
            self.main_window.append_log_message('Intento de edición fallido: contraseña incorrecta.')
        return False

    def update_admin_status_label(self):
        if self._is_edit_grace_active():
            remaining = self.edit_grace_period - (datetime.now() - self.last_edit_unlock)
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            self.admin_status_label.setText(f"Acceso administrativo autorizado localmente. Expira en {minutes}m {seconds}s.")
            self.admin_status_label.setVisible(True)
            return

        if self.main_window and getattr(self.main_window, 'is_admin_clearance_active', None):
            try:
                if self.main_window.is_admin_clearance_active():
                    remaining = self.main_window.admin_session_duration - (datetime.now() - self.main_window.last_admin_unlock)
                    minutes = int(remaining.total_seconds() // 60)
                    seconds = int(remaining.total_seconds() % 60)
                    self.admin_status_label.setText(f"Sesión administrativa activa. Expira en {minutes}m {seconds}s.")
                    self.admin_status_label.setVisible(True)
                    return
            except Exception:
                pass

        self.admin_status_label.setVisible(False)

    def open_edit_dialog(self, account_id):
        account = None
        if hasattr(self.controller.db, 'get_account_by_id'):
            account = self.controller.db.get_account_by_id(account_id, self.controller.cliente_id)
        if not account:
            QMessageBox.warning(self, "Cuenta no encontrada", "No se pudo cargar la cuenta para edición.")
            return

        dialog = AddAccountDialog(self, account_data=account)

        if dialog.exec() == AddAccountDialog.DialogCode.Accepted:
            data = dialog.get_data()
            updated = self.controller.edit_account(account_id, data)
            if updated:
                self.controller.db.actualizar_log(account_id, "Configuración de cuenta actualizada.")
                self.controller.refresh(self.controller.cliente_id)
                QMessageBox.information(self, "Cuenta actualizada", "Los cambios se guardaron correctamente.")
            else:
                QMessageBox.warning(self, "No se guardaron cambios", "No se detectaron cambios o hubo un error al actualizar la cuenta.")

    def load_accounts(self, accounts):
        """Pobla la lista de tarjetas dinámicamente."""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for acc in accounts:
            card = AccountCard(acc, self.controller)
            card.request_force_activate.connect(self.on_card_force_activate)
            card.request_edit_account.connect(self.on_card_edit_account)
            self.cards_layout.addWidget(card)
        
        # Stretch final para mantener las tarjetas en la parte superior
        self.cards_layout.addStretch()
        self.update_admin_status_label()
        self.update_alert_summary()

        self.btn_add.setEnabled(not self._account_limit_reached())
        self.btn_add.setToolTip(
            "Ya existe una cuenta registrada. Solo se permite una cuenta por vista."
            if self._account_limit_reached() else "Añadir nueva cuenta de Instagram"
        )