import qtawesome as qta
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame, 
                             QLabel, QScrollArea, QHBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, QSize
# Importamos el diálogo desde la nueva subcarpeta
from views.dialogs.instagram_dialog import AddAccountDialog
from views.dialogs.conversation_dialog import ConversationDialog

class ClickableFrame(QFrame):
    def __init__(self, callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback

    def mousePressEvent(self, event):
        if self.callback:
            self.callback(event)
        super().mousePressEvent(event)


class AccountCard(QFrame):
    def __init__(self, data, controller):
        super().__init__()
        self.account_id = data.get('id')
        self.controller = controller
        self.is_expanded = False
        self.setObjectName("ModernAccountCard")
        self.setStyleSheet(
            "QFrame#ModernAccountCard { background-color: #0A0A0A; border: 1px solid #222; border-radius: 16px; }"
        )

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

        state_icon_name = 'fa5s.robot' if self.current_state else 'fa5s.moon'
        state_color = '#00E5FF' if self.current_state else '#FF8A00'
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
        self.status_led.setStyleSheet(f"color: {'#00FFCC' if self.current_state else '#FF3366'}; font-size: 16px; margin-right: 8px;")
        header_layout.addWidget(self.status_led)

        self.status_label = QLabel("ENCENDIDO" if self.current_state else "APAGADO")
        self.status_label.setStyleSheet("color: #CCCCCC; font-size: 11px; font-weight: 700;")
        header_layout.addWidget(self.status_label)

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
        self.details_frame.setStyleSheet("background: #0A0A0A; border: none;")
        self.details_layout = QVBoxLayout(self.details_frame)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(14)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        stats_layout.addWidget(self._build_stat_card('fa5s.comment-dots', '#00E5FF', 'Atendidos Hoy', '0'))
        stats_layout.addWidget(self._build_stat_card('fa5s.broom', '#FF8A00', 'Ignorados (+24h)', '0'))
        stats_layout.addWidget(self._build_stat_card('fa5s.user-tie', '#FFFFFF', 'Rol', data.get('context_type', 'Vendedor de tienda')))
        self.details_layout.addLayout(stats_layout)

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
        row.setStyleSheet(
            "background-color: #1A1A1A; border: 1px solid #222; border-radius: 6px;"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 10, 10, 10)
        row_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.user', color='#00E5FF').pixmap(16, 16))
        row_layout.addWidget(icon_label)

        name = QLabel(conversation.get('title', conversation.get('username', 'Cliente')))
        name.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        row_layout.addWidget(name)

        row_layout.addStretch()

        status = QLabel("🤖 Gestionado por IA")
        status.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        row_layout.addWidget(status)

        btn_open = QPushButton(qta.icon('fa5s.eye', color='#00E5FF'), "")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedSize(QSize(32, 32))
        btn_open.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #00E5FF; }"
            "QPushButton:hover { background-color: rgba(0, 228, 255, 0.1); border-radius: 6px; }"
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
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); border-radius: 6px; }"
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
        self.controller.refresh()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

class InstagramAccountsPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
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
        
        header_layout.addWidget(self.lbl_page_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_add)
        self.main_layout.addLayout(header_layout)

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

    def load_accounts(self, accounts):
        """Pobla la lista de tarjetas dinámicamente."""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for acc in accounts:
            card = AccountCard(acc, self.controller)
            self.cards_layout.addWidget(card)
        
        # Stretch final para mantener las tarjetas en la parte superior
        self.cards_layout.addStretch()

        self.btn_add.setEnabled(not self._account_limit_reached())
        self.btn_add.setToolTip(
            "Ya existe una cuenta registrada. Solo se permite una cuenta por vista."
            if self._account_limit_reached() else "Añadir nueva cuenta de Instagram"
        )