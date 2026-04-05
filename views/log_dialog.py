from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs del Bot Pegasus")
        self.setMinimumSize(640, 420)
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.layout = QVBoxLayout(self)
        self.log_console = QTextEdit(self)
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet(
            "background-color: #111; color: #EEE; border: 1px solid #222; padding: 12px;"
        )
        self.layout.addWidget(self.log_console)

        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.clicked.connect(self.clear)
        footer.addWidget(self.btn_clear)
        self.layout.addLayout(footer)

    def append_message(self, message: str):
        if not message:
            return
        self.log_console.append(message)

    def clear(self):
        self.log_console.clear()
