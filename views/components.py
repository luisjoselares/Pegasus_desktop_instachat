from PyQt6.QtWidgets import QFrame, QPushButton, QLineEdit, QGraphicsDropShadowEffect
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt


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
