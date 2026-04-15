import qtawesome as qta
from PyQt6.QtWidgets import QFrame, QPushButton, QLineEdit, QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QDate, Qt, pyqtSignal


class PegasusCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pegasusCard")
        self.setStyleSheet(
            "QFrame#pegasusCard {"
            "background-color: #1a1a1a;"
            "border: none;"
            "border-radius: 14px;"
            "}"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.GlobalColor.black)
        self.setGraphicsEffect(shadow)


class PegasusPrimaryButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class PegasusTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pegasusTitleBar")
        self.setStyleSheet(
            "QWidget#pegasusTitleBar { background: transparent; }"
            "QPushButton { background: transparent; border: none; color: #00E5FF; }"
            "QPushButton:hover { background-color: rgba(0, 229, 255, 0.08); }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        self.lbl_logo = QLabel("Pegasus")
        self.lbl_logo.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        layout.addWidget(self.lbl_logo)
        layout.addStretch()

        self.btn_min = QPushButton(qta.icon('fa5s.minus', color='#00E5FF'), "")
        self.btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_min.setObjectName("titleBarButton")
        self.btn_min.setFixedSize(32, 32)
        layout.addWidget(self.btn_min)

        self.btn_max = QPushButton(qta.icon('fa5s.square', color='#00E5FF'), "")
        self.btn_max.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_max.setObjectName("titleBarButton")
        self.btn_max.setFixedSize(32, 32)
        layout.addWidget(self.btn_max)

        self.btn_close = QPushButton(qta.icon('fa5s.times', color='#00E5FF'), "")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setObjectName("closeButton")
        self.btn_close.setFixedSize(32, 32)
        layout.addWidget(self.btn_close)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_mouse_pos') and self._mouse_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._mouse_pos)
            event.accept()
        super().mouseMoveEvent(event)


class PegasusDialogBar(QWidget):
    def __init__(self, title: str = "Configuración de Instagram", parent=None):
        super().__init__(parent)
        self.setObjectName("dialogTitleBar")
        self._drag_position = None

        self.setStyleSheet(
            "QWidget#dialogTitleBar { background: transparent; }"
            "QPushButton { background: transparent; border: none; color: #FFFFFF; }"
            "QPushButton:hover { color: #FF4C4C; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.close_button = QPushButton(qta.icon("fa5s.times", color="#FFFFFF"), "")
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button.clicked.connect(lambda: self.window().close())
        layout.addWidget(self.close_button)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        return super().mouseMoveEvent(event)


class PegasusInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pegasusInput")
        self.setStyleSheet(
            "QLineEdit#pegasusInput {"
            "background: transparent;"
            "border: none;"
            "border-bottom: 1px solid #6c6c6c;"
            "color: #FFFFFF;"
            "padding: 6px 0;"
            "}"
            "QLineEdit#pegasusInput:focus {"
            "border-bottom: 1px solid #00E5FF;"
            "}"
        )


class PegasusCalendar(QWidget):
    dateChanged = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_date = QDate.currentDate()
        self.displayed_date = QDate(self.current_date.year(), self.current_date.month(), 1)

        self.setObjectName("pegasusCalendar")
        self.setStyleSheet("background: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_prev.setStyleSheet(
            "QPushButton { background: transparent; color: #00E5FF; font-size: 16px; font-weight: bold; border: none; }"
            "QPushButton:hover { background-color: #222222; }"
        )

        self.lbl_month_year = QLabel()
        self.lbl_month_year.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_month_year.setStyleSheet("color: white; font-weight: bold;")

        self.btn_next = QPushButton("➡")
        self.btn_next.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_next.setStyleSheet(
            "QPushButton { background: transparent; color: #00E5FF; font-size: 16px; font-weight: bold; border: none; }"
            "QPushButton:hover { background-color: #222222; }"
        )

        header_layout.addWidget(self.btn_prev)
        header_layout.addWidget(self.lbl_month_year, stretch=1)
        header_layout.addWidget(self.btn_next)

        main_layout.addLayout(header_layout)

        self.grid_days = QGridLayout()
        self.grid_days.setContentsMargins(5, 5, 5, 5)
        self.grid_days.setSpacing(2)

        week_days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for index, text in enumerate(week_days):
            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #888888;")
            self.grid_days.addWidget(label, 0, index)

        main_layout.addLayout(self.grid_days)

        self.btn_prev.clicked.connect(self._show_previous_month)
        self.btn_next.clicked.connect(self._show_next_month)

        self._populate_calendar(self.displayed_date)

    def _populate_calendar(self, date: QDate):
        self._clear_calendar_days()
        self.lbl_month_year.setText(date.toString("MMMM yyyy").capitalize())

        first_day = QDate(date.year(), date.month(), 1)
        start_column = first_day.dayOfWeek() - 1
        days_in_month = date.daysInMonth()

        row = 1
        column = start_column

        for day in range(1, days_in_month + 1):
            button_date = QDate(date.year(), date.month(), day)
            day_button = QPushButton(str(day))
            day_button.setFixedHeight(30)
            day_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            day_button.setStyleSheet(
                "QPushButton { background-color: transparent; color: white; border-radius: 4px; padding: 2px; font-weight: bold; }"
                "QPushButton:hover { background-color: #222; }"
            )
            if button_date == self.current_date:
                day_button.setStyleSheet(
                    "QPushButton { background-color: #00E5FF; color: black; border-radius: 4px; padding: 2px; font-weight: bold; }"
                    "QPushButton:hover { background-color: #222; }"
                )

            day_button.clicked.connect(lambda _, selected_date=button_date: self._select_date(selected_date))
            self.grid_days.addWidget(day_button, row, column)

            column += 1
            if column >= 7:
                column = 0
                row += 1

    def _clear_calendar_days(self):
        items_to_remove = []
        for index in range(self.grid_days.count()):
            item = self.grid_days.itemAt(index)
            if item is None:
                continue
            row, column, row_span, column_span = self.grid_days.getItemPosition(index)
            if row >= 1:
                widget = item.widget()
                if widget:
                    items_to_remove.append(widget)
                else:
                    items_to_remove.append(item)

        for item in items_to_remove:
            if isinstance(item, QWidget):
                self.grid_days.removeWidget(item)
                item.setParent(None)
                item.deleteLater()
            else:
                self.grid_days.removeItem(item)

    def _select_date(self, selected_date: QDate):
        self.current_date = selected_date
        self.displayed_date = QDate(selected_date.year(), selected_date.month(), 1)
        self._populate_calendar(self.displayed_date)
        self.dateChanged.emit(selected_date)

    def _show_previous_month(self):
        month = self.displayed_date.month() - 1
        year = self.displayed_date.year()
        if month < 1:
            month = 12
            year -= 1
        self.displayed_date = QDate(year, month, 1)
        self._populate_calendar(self.displayed_date)

    def _show_next_month(self):
        month = self.displayed_date.month() + 1
        year = self.displayed_date.year()
        if month > 12:
            month = 1
            year += 1
        self.displayed_date = QDate(year, month, 1)
        self._populate_calendar(self.displayed_date)


class PegasusChatItem(QFrame):
    def __init__(self, username: str = "Cliente", last_message: str = "", unread: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("pegasusChatItem")
        self.setStyleSheet(
            "QFrame#pegasusChatItem { background-color: #121212; border: 1px solid #222; border-radius: 14px; }"
            "QLabel { color: #FFFFFF; }"
            "QLabel.unread { color: #00E5FF; font-weight: bold; }"
            "QPushButton { background: transparent; border: none; color: #00E5FF; }"
            "QPushButton:hover { color: #7ef2ff; }"
        )

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_username = QLabel(username)
        self.lbl_username.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(self.lbl_username)

        if unread:
            unread_label = QLabel("Nuevo")
            unread_label.setObjectName("unread")
            unread_label.setStyleSheet("color: #00E5FF; font-size: 11px; font-weight: 700;")
            header_layout.addWidget(unread_label)

        header_layout.addStretch()
        text_layout.addLayout(header_layout)

        self.lbl_last_message = QLabel(last_message or "Sin mensajes recientes")
        self.lbl_last_message.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        self.lbl_last_message.setWordWrap(True)
        text_layout.addWidget(self.lbl_last_message)

        main_layout.addLayout(text_layout)

        self.btn_open_chat = QPushButton(qta.icon('fa5s.comment-dots', color='#00E5FF'), "")
        self.btn_open_chat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_chat.setToolTip("Abrir chat")
        self.btn_open_chat.setFixedSize(28, 28)
        main_layout.addWidget(self.btn_open_chat)


class PegasusNotificationCard(QFrame):
    def __init__(self, title: str, message: str, timestamp: str, critical: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("pegasusNotificationCard")
        self.setStyleSheet("background: transparent; border-bottom: 1px solid #222;")

        color = "#FF5C5C" if critical else "#00E5FF"

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        icon_label = QLabel("●")
        icon_label.setStyleSheet(f"color: {color}; font-size: 18px;")
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        self.lbl_titulo = QLabel(title)
        self.lbl_titulo.setStyleSheet("color: white; font-weight: bold;")

        self.lbl_mensaje = QLabel(message)
        self.lbl_mensaje.setWordWrap(True)
        self.lbl_mensaje.setStyleSheet("color: #CCCCCC;")

        text_layout.addWidget(self.lbl_titulo)
        text_layout.addWidget(self.lbl_mensaje)

        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet("color: #666666; font-size: 11px;")
        timestamp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        main_layout.addWidget(icon_label)
        main_layout.addWidget(text_container, stretch=1)
        main_layout.addWidget(timestamp_label)
