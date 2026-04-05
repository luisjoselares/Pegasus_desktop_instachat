import qtawesome as qta
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtCore import Qt


class ConversationDialog(QDialog):
    def __init__(self, parent=None, title="Conversación", history=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("ConversationDialog")
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header = QLabel(f"Conversación con {title}")
        header.setStyleSheet("color: #00E5FF; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setStyleSheet(
            "background-color: #121212; color: #FFFFFF; border: 1px solid #333; padding: 12px;"
        )
        layout.addWidget(self.history_text)

        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_close = QPushButton(qta.icon('fa5s.times-circle', color='#FFFFFF'), "Cerrar")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        footer.addWidget(self.btn_close)
        layout.addLayout(footer)

        self._load_history(history or [])

    def _load_history(self, history):
        if not history:
            self.history_text.setPlainText("No se encontró conversación completa para este hilo.")
            return

        lines = []
        for entry in history:
            lines.append(f"[{entry.get('timestamp', '')}] @{entry.get('title', '')}")
            lines.append(f"  Mensaje: {entry.get('last_message', '')}")
            response = entry.get('response', '')
            if response:
                lines.append(f"  Respuesta IA: {response}")
            lines.append("-")

        self.history_text.setPlainText("\n".join(lines))
