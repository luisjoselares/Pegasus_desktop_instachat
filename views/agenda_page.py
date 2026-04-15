import qtawesome as qta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QDate
from services.database_service import LocalDBService

from views.components import PegasusCard, PegasusPrimaryButton, PegasusCalendar
from views.dialogs.conversation_dialog import ConversationDialog


class AgendaPage(QWidget):
    def __init__(self, db_service=None, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaPage")
        self.db = db_service or LocalDBService()
        self._build_ui()
        self.load_citas()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = QLabel("Agenda de Citas")
        title.setObjectName("PageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.calendario = PegasusCalendar()
        self.calendario.setObjectName("agendaCalendar")
        self.calendario.dateChanged.connect(self.on_date_selected)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.calendario)

        content_card = PegasusCard()
        content_card.setObjectName("agendaContentCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        self.appointments_area = QScrollArea()
        self.appointments_area.setObjectName("agendaScrollArea")
        self.appointments_area.setWidgetResizable(True)
        self.appointments_area.setFrameShape(QFrame.Shape.NoFrame)
        self.appointments_area.setStyleSheet("background: transparent; border: none;")

        self.appointments_container = QWidget()
        self.appointments_container.setObjectName("appointmentsContainer")
        self.appointments_layout = QVBoxLayout(self.appointments_container)
        self.appointments_layout.setContentsMargins(0, 0, 0, 0)
        self.appointments_layout.setSpacing(16)
        self.appointments_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.appointments_area.setWidget(self.appointments_container)
        content_layout.addWidget(self.appointments_area)

        main_layout.addWidget(content_card, stretch=2)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.btn_new_cita = PegasusPrimaryButton(" Nueva Cita")
        self.btn_new_cita.setIcon(qta.icon('fa5s.plus', color='#000000'))
        self.btn_new_cita.setFixedHeight(44)
        self.btn_new_cita.setFixedWidth(180)
        action_layout.addWidget(self.btn_new_cita, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(action_layout)

    def on_date_selected(self, selected_date: QDate):
        self.selected_date = selected_date
        self.load_citas()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def load_citas(self):
        citas = self.db.get_upcoming_citas()
        self._clear_layout(self.appointments_layout)

        if not citas:
            empty_label = QLabel("No hay citas para hoy.")
            empty_label.setStyleSheet("color: #B0B0B0; font-size: 14px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.appointments_layout.addWidget(empty_label)
            self.appointments_layout.addStretch()
            return

        for cita in citas:
            card = PegasusCard()
            card.setObjectName("agendaItemCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(12)

            time_label = QLabel(cita.get('fecha_hora', ''))
            time_label.setStyleSheet("color: #00E5FF; font-size: 12px; font-weight: 700;")
            card_layout.addWidget(time_label)

            name_label = QLabel(cita.get('cliente_nombre', 'Cliente'))
            name_label.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 800;")
            card_layout.addWidget(name_label)

            service_label = QLabel(cita.get('servicio', 'Servicio no especificado'))
            service_label.setStyleSheet("color: #BBBBBB; font-size: 13px;")
            card_layout.addWidget(service_label)

            estado = cita.get('estado', 'Pendiente')
            badge_color = '#FFC107' if estado == 'Pendiente' else '#4CAF50' if estado == 'Confirmada' else '#F44336'
            status_badge = QLabel(estado)
            status_badge.setStyleSheet(
                f"background-color: {badge_color}; color: #000000; padding: 4px 10px; border-radius: 12px; font-size: 11px;"
            )
            status_badge.setFixedWidth(110)

            buttons_layout = QHBoxLayout()
            buttons_layout.setSpacing(10)
            buttons_layout.addWidget(status_badge)

            btn_ver_chat = PegasusPrimaryButton("💬 Ver Chat")
            btn_ver_chat.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ver_chat.setStyleSheet(
                "QPushButton { background-color: transparent; color: #00E5FF; border: 1px solid #00E5FF; border-radius: 8px; padding: 8px 14px; }"
                "QPushButton:hover { background-color: rgba(0, 229, 255, 0.1); }"
            )
            btn_ver_chat.clicked.connect(lambda _, c_id=cita.get('cliente_id'): self.open_chat_dialog(c_id))
            buttons_layout.addWidget(btn_ver_chat)

            buttons_layout.addStretch()

            btn_confirm = QPushButton("Confirmar")
            btn_confirm.setProperty("agenda_action", "confirm")
            btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_confirm.setStyleSheet(
                "QPushButton { background-color: #00E5FF; color: #000000; border-radius: 8px; padding: 8px 14px; }"
                "QPushButton:hover { background-color: #33b8ff; }"
            )
            btn_confirm.clicked.connect(lambda _, cid=cita['id']: self._update_cita_status(cid, 'Confirmada'))

            btn_cancel = QPushButton("Cancelar")
            btn_cancel.setProperty("agenda_action", "cancel")
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet(
                "QPushButton { background-color: #FF5555; color: #FFFFFF; border-radius: 8px; padding: 8px 14px; }"
                "QPushButton:hover { background-color: #ff7777; }"
            )
            btn_cancel.clicked.connect(lambda _, cid=cita['id']: self._update_cita_status(cid, 'Cancelada'))

            buttons_layout.addWidget(btn_confirm)
            buttons_layout.addWidget(btn_cancel)
            card_layout.addLayout(buttons_layout)

            self.appointments_layout.addWidget(card)

        self.appointments_layout.addStretch()

    def open_chat_dialog(self, cliente_id):
        if not cliente_id:
            return
        dialog = ConversationDialog(cliente_id=cliente_id, parent=self)
        dialog.exec()

    def _update_cita_status(self, cita_id, estado):
        self.db.update_cita_status(cita_id, estado)
        self.load_citas()
